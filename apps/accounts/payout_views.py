"""DJ payouts page: where to send the money, 2FA, balance, history and "request payout"."""

import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

UPI_RE = re.compile(r"^[a-zA-Z0-9._-]{2,256}@[a-zA-Z][a-zA-Z0-9]{1,64}$")
IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def _mask(value, keep=4):
    value = (value or "").strip()
    return ("•" * max(len(value) - keep, 0)) + value[-keep:] if value else ""


@login_required
def dj_payouts_view(request):
    profile = request.user.profile
    dj = getattr(profile, "dj_profile", None) if hasattr(profile, "dj_profile") else None
    if profile.role != "dj" or dj is None:
        return redirect("dashboard")

    if request.method == "POST":
        method = request.POST.get("method")
        pan = (request.POST.get("pan_number") or "").strip().upper()
        errors = []
        if pan and not PAN_RE.match(pan):
            errors.append("PAN should look like ABCDE1234F.")
        if method == "upi":
            upi = (request.POST.get("upi_id") or "").strip()
            if not UPI_RE.match(upi):
                errors.append("Enter a UPI ID like yourname@okhdfcbank.")
        elif method == "bank":
            acct = re.sub(r"\s+", "", request.POST.get("bank_account_number") or "")
            ifsc = (request.POST.get("bank_ifsc_code") or "").strip().upper()
            name = (request.POST.get("account_name") or "").strip()[:120]
            if not (acct.isdigit() and 6 <= len(acct) <= 20):
                errors.append("Enter your bank account number (digits only).")
            if not IFSC_RE.match(ifsc):
                errors.append("Enter a valid IFSC code, e.g. HDFC0001234.")
            if not name:
                errors.append("Enter the name on the bank account.")
        else:
            errors.append("Choose UPI or bank transfer.")
        has_method = bool((dj.upi_id or "").strip() or (dj.bank_account_number or "").strip())
        if has_method and not errors:  # changing where money goes needs the emailed code
            from .payout_auth import verify_email_code

            ok, msg = verify_email_code(dj, request.POST.get("code"), "details")
            if not ok:
                errors.append(msg)
        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, "dashboard/dj_payouts.html", {**_ctx(dj), "keep_editing": True}, status=400)

        details = dict(dj.payout_details or {})
        if method == "upi":
            dj.upi_id = upi
            details["method"] = "upi"
        else:
            dj.bank_account_number, dj.bank_ifsc_code = acct, ifsc
            details.update(method="bank", account_name=name)
        if pan and pan != dj.pan_number:
            dj.pan_number, dj.is_pan_verified = pan, False
        dj.payout_details = details
        dj.save(update_fields=["upi_id", "bank_account_number", "bank_ifsc_code", "payout_details", "pan_number", "is_pan_verified"])
        messages.success(request, "Payout details saved.")
        return redirect("dj_payouts")

    return render(request, "dashboard/dj_payouts.html", _ctx(dj))


def _ctx(dj):
    from datetime import timedelta

    from django.utils import timezone

    from apps.commerce.models import DJWallet, Payout

    wallet, _ = DJWallet.objects.get_or_create(dj=dj)
    method = (dj.payout_details or {}).get("method") or ("upi" if dj.upi_id else "bank" if dj.bank_account_number else "")
    last = Payout.objects.filter(dj=dj).exclude(status="failed").order_by("-created_at").first()
    next_at = (last.created_at + timedelta(days=7)) if last else None
    ctx = {
        "dj_profile": dj,
        "wallet": wallet,
        "method": method,
        "has_method": bool((dj.upi_id or "").strip() or ((dj.bank_account_number or "").strip() and dj.bank_ifsc_code)),
        "masked_account": _mask(dj.bank_account_number),
        "account_name": (dj.payout_details or {}).get("account_name", ""),
        "threshold": settings.MIN_PAYOUT_THRESHOLD,
        "payouts": Payout.objects.filter(dj=dj).order_by("-created_at")[:20],
        "next_withdraw_at": next_at if next_at and next_at > timezone.now() else None,
    }
    return ctx


@login_required
@require_POST
def payout_code_view(request):
    """Email the DJ a 6-digit code for a withdrawal or for changing payout details."""
    profile = request.user.profile
    dj = getattr(profile, "dj_profile", None)
    if profile.role != "dj" or dj is None:
        return JsonResponse({"error": "Only DJs can do this."}, status=403)
    import json

    try:
        purpose = (json.loads(request.body or b"{}").get("purpose") or "withdraw")
    except ValueError:
        purpose = "withdraw"
    if purpose not in ("withdraw", "details"):
        purpose = "withdraw"
    from .payout_auth import send_payout_code

    ok, msg = send_payout_code(dj, purpose)
    return JsonResponse({"ok": ok, "message": msg} if ok else {"error": msg}, status=200 if ok else 429)
