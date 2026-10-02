"""Automatic DJ payouts: send a payout to the DJ's UPI ID or bank account through a payouts provider.

PhonePe only collects payments; it has no API for sending money out, so payouts use a second provider:

* Cashfree Payouts (recommended on Vercel): 2FA with a public key (x-cf-signature), so no fixed
  server IP is needed. Env: CASHFREE_PAYOUT_CLIENT_ID, CASHFREE_PAYOUT_CLIENT_SECRET,
  CASHFREE_PAYOUT_PUBLIC_KEY (the .pem text), CASHFREE_PAYOUT_ENV=sandbox|production.
* RazorpayX: needs the server IP allowlisted with Razorpay. Env: RAZORPAYX_KEY_ID,
  RAZORPAYX_KEY_SECRET, RAZORPAYX_ACCOUNT_NUMBER, RAZORPAYX_WEBHOOK_SECRET.

Admin -> Settings -> Automatic payouts switches it on, picks the provider and sets the most that is
sent without an admin tap. Everything else stays the manual flow (Admin -> Payouts).

Money safety:
* One transfer per payout, keyed by the payout ID (provider idempotency): a retry can't pay twice.
* A timeout or 5xx leaves the payout "processing" and its status is checked later; it is never re-sent.
* A definite failure (rejected, failed, reversed) returns the money to the DJ's balance.
"""

import base64
import hashlib
import hmac
import json
import logging
import re
import time
from decimal import Decimal

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger("mixmint")
TIMEOUT = 8  # keep well inside the serverless request limit; unknown results are checked later


class PayoutError(Exception):
    """The provider definitely refused the payout (safe to return the money)."""


class PayoutUnknown(Exception):
    """We don't know whether the provider accepted it (timeout / 5xx). Check status later; never re-send."""


# ───────────────────────────── settings ─────────────────────────────
def config():
    from apps.admin_panel.models import SystemSetting

    row = SystemSetting.objects.filter(key="auto_payouts").first()
    v = (row.value or {}) if row and isinstance(row.value, dict) else {}
    return {
        "enabled": bool(v.get("enabled")),
        "provider": v.get("provider") if v.get("provider") in PROVIDERS else "cashfree",
        "auto_limit": Decimal(str(v.get("auto_limit") or 10000)),
        "first_needs_approval": v.get("first_needs_approval", True) is not False,
    }


def provider_ready(name):
    p = PROVIDERS.get(name)
    return bool(p and p.configured())


def active_provider():
    """The provider to use right now, or None (manual mode)."""
    c = config()
    if not c["enabled"]:
        return None
    p = PROVIDERS[c["provider"]]
    return p if p.configured() else None


def destination(dj):
    """(mode, details) for the DJ's saved payout method, or raises PayoutError."""
    method = (dj.payout_details or {}).get("method") or ("upi" if dj.upi_id else "bank" if dj.bank_account_number else "")
    if method == "upi" and (dj.upi_id or "").strip():
        return "upi", {"vpa": dj.upi_id.strip()}
    if (dj.bank_account_number or "").strip() and (dj.bank_ifsc_code or "").strip():
        return "bank", {"account": dj.bank_account_number.strip(), "ifsc": dj.bank_ifsc_code.strip().upper()}
    raise PayoutError("No UPI ID or bank account saved.")


def clean_name(dj):
    raw = (dj.payout_details or {}).get("account_name") or dj.dj_name or "MixMint DJ"
    name = re.sub(r"[^A-Za-z ]+", " ", raw)
    name = re.sub(r"\s+", " ", name).strip()
    return (name or "MixMint DJ")[:100]


# ───────────────────────────── Cashfree ─────────────────────────────
class Cashfree:
    name = "cashfree"
    label = "Cashfree Payouts"

    @staticmethod
    def _env():
        return {
            "id": getattr(settings, "CASHFREE_PAYOUT_CLIENT_ID", ""),
            "secret": getattr(settings, "CASHFREE_PAYOUT_CLIENT_SECRET", ""),
            "pem": getattr(settings, "CASHFREE_PAYOUT_PUBLIC_KEY", ""),
            "base": "https://api.cashfree.com/payout" if getattr(settings, "CASHFREE_PAYOUT_ENV", "sandbox") == "production"
            else "https://sandbox.cashfree.com/payout",
        }

    @classmethod
    def configured(cls):
        e = cls._env()
        return bool(e["id"] and e["secret"])

    @classmethod
    def _signature(cls):
        """x-cf-signature: RSA-OAEP(SHA-1) of "<client id>.<unix time>" with Cashfree's public key, base64. Valid 5 min."""
        e = cls._env()
        if not e["pem"]:
            return None
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding

        pem = e["pem"].replace("\\n", "\n").encode()
        key = serialization.load_pem_public_key(pem)
        data = f"{e['id']}.{int(time.time())}".encode()
        enc = key.encrypt(data, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA1()), algorithm=hashes.SHA1(), label=None))
        return base64.b64encode(enc).decode()

    @classmethod
    def _headers(cls):
        e = cls._env()
        h = {"x-client-id": e["id"], "x-client-secret": e["secret"], "x-api-version": "2024-01-01",
             "Content-Type": "application/json"}
        sig = cls._signature()
        if sig:
            h["x-cf-signature"] = sig
        return h

    @staticmethod
    def transfer_id(payout):
        return f"MMPO_{payout.id}"

    @classmethod
    def send(cls, payout):
        dj = payout.dj
        mode, dest = destination(dj)
        instrument = {"vpa": dest["vpa"]} if mode == "upi" else {"bank_account_number": dest["account"], "bank_ifsc": dest["ifsc"]}
        body = {
            "transfer_id": cls.transfer_id(payout),
            "transfer_amount": float(payout.amount),
            "transfer_currency": "INR",
            "transfer_mode": "upi" if mode == "upi" else "imps",
            "beneficiary_details": {
                "beneficiary_id": f"MMDJ_{dj.pk}",
                "beneficiary_name": clean_name(dj),
                "beneficiary_instrument_details": instrument,
                "beneficiary_contact_details": {"beneficiary_email": dj.profile.user.email},
            },
            "transfer_remarks": f"MixMint payout {payout.id}",
        }
        try:
            r = requests.post(f"{cls._env()['base']}/transfers", headers=cls._headers(), data=json.dumps(body), timeout=TIMEOUT)
        except requests.RequestException as exc:
            raise PayoutUnknown(f"Cashfree did not answer: {exc}") from exc
        return cls._parse(r)

    @classmethod
    def fetch(cls, payout):
        try:
            r = requests.get(f"{cls._env()['base']}/transfers", params={"transfer_id": cls.transfer_id(payout)},
                             headers=cls._headers(), timeout=TIMEOUT)
        except requests.RequestException as exc:
            raise PayoutUnknown(str(exc)) from exc
        return cls._parse(r)

    @staticmethod
    def _parse(r):
        if r.status_code >= 500:
            raise PayoutUnknown(f"Cashfree error {r.status_code}")
        try:
            d = r.json()
        except ValueError as exc:
            raise PayoutUnknown("Cashfree sent an unreadable reply") from exc
        if r.status_code >= 400:
            msg = d.get("message") or d.get("status_description") or f"HTTP {r.status_code}"
            if d.get("code") in ("transfer_id_already_exists",):
                raise PayoutUnknown(msg)  # it was sent before: look it up instead
            raise PayoutError(msg)
        status = (d.get("status") or "").upper()
        state = {"SUCCESS": "paid", "FAILED": "failed", "REJECTED": "failed", "REVERSED": "failed",
                 "MANUALLY_REJECTED": "failed"}.get(status, "processing")
        if status == "SUCCESS" and (d.get("status_code") or "COMPLETED").upper() != "COMPLETED":
            state = "processing"
        return {"state": state, "ref": d.get("cf_transfer_id") or "", "utr": d.get("transfer_utr") or "",
                "message": d.get("status_description") or status.title()}

    @classmethod
    def verify_webhook(cls, raw, headers):
        ts = headers.get("x-webhook-timestamp", "")
        sig = headers.get("x-webhook-signature", "")
        secret = cls._env()["secret"]
        if not (ts and sig and secret):
            return False
        mac = base64.b64encode(hmac.new(secret.encode(), (ts + raw.decode("utf-8")).encode(), hashlib.sha256).digest()).decode()
        return hmac.compare_digest(mac, sig)

    @staticmethod
    def parse_webhook(payload):
        """-> (payout_id, result) or (None, None) for events we don't act on."""
        t = (payload.get("type") or "").upper()
        d = payload.get("data") or {}
        tid = str(d.get("transfer_id") or "")
        if not tid.startswith("MMPO_") or not tid[5:].isdigit():
            return None, None
        state = {"TRANSFER_SUCCESS": "paid", "TRANSFER_FAILED": "failed", "TRANSFER_REVERSED": "failed",
                 "TRANSFER_REJECTED": "failed"}.get(t)
        if not state:
            return None, None
        return int(tid[5:]), {"state": state, "ref": d.get("cf_transfer_id") or "", "utr": d.get("transfer_utr") or "",
                              "message": d.get("status_description") or t.replace("_", " ").title()}


# ───────────────────────────── RazorpayX ─────────────────────────────
class RazorpayX:
    name = "razorpayx"
    label = "RazorpayX"
    base = "https://api.razorpay.com/v1"

    @staticmethod
    def _env():
        return {
            "id": getattr(settings, "RAZORPAYX_KEY_ID", ""),
            "secret": getattr(settings, "RAZORPAYX_KEY_SECRET", ""),
            "account": getattr(settings, "RAZORPAYX_ACCOUNT_NUMBER", ""),
            "hook": getattr(settings, "RAZORPAYX_WEBHOOK_SECRET", ""),
        }

    @classmethod
    def configured(cls):
        e = cls._env()
        return bool(e["id"] and e["secret"] and e["account"])

    @classmethod
    def send(cls, payout):
        e = cls._env()
        dj = payout.dj
        mode, dest = destination(dj)
        contact = {"name": clean_name(dj)[:50], "email": dj.profile.user.email, "type": "vendor", "reference_id": f"dj-{dj.pk}"}
        fund = ({"account_type": "vpa", "vpa": {"address": dest["vpa"]}, "contact": contact} if mode == "upi" else
                {"account_type": "bank_account", "bank_account": {"name": clean_name(dj), "ifsc": dest["ifsc"],
                                                                  "account_number": dest["account"]}, "contact": contact})
        body = {
            "account_number": e["account"],
            "amount": int((payout.amount * 100).to_integral_value()),
            "currency": "INR",
            "mode": "UPI" if mode == "upi" else "IMPS",
            "purpose": "payout",
            "fund_account": fund,
            "queue_if_low_balance": True,
            "reference_id": f"payout-{payout.id}",
            "narration": "MixMint DJ payout",
            "notes": {"payout_id": str(payout.id)},
        }
        headers = {"Content-Type": "application/json", "X-Payout-Idempotency": f"mixmint-payout-{payout.id}"}
        try:
            r = requests.post(f"{cls.base}/payouts", auth=(e["id"], e["secret"]), headers=headers, data=json.dumps(body), timeout=TIMEOUT)
        except requests.RequestException as exc:
            raise PayoutUnknown(f"RazorpayX did not answer: {exc}") from exc
        return cls._parse(r)

    @classmethod
    def fetch(cls, payout):
        e = cls._env()
        if not payout.provider_ref:
            raise PayoutUnknown("No RazorpayX payout ID saved yet.")
        try:
            r = requests.get(f"{cls.base}/payouts/{payout.provider_ref}", auth=(e["id"], e["secret"]), timeout=TIMEOUT)
        except requests.RequestException as exc:
            raise PayoutUnknown(str(exc)) from exc
        return cls._parse(r)

    @staticmethod
    def _parse(r):
        if r.status_code >= 500:
            raise PayoutUnknown(f"RazorpayX error {r.status_code}")
        try:
            d = r.json()
        except ValueError as exc:
            raise PayoutUnknown("RazorpayX sent an unreadable reply") from exc
        if r.status_code >= 400:
            raise PayoutError(((d.get("error") or {}).get("description")) or f"HTTP {r.status_code}")
        return RazorpayX._state(d)

    @staticmethod
    def _state(d):
        st = (d.get("status") or "").lower()
        state = {"processed": "paid", "failed": "failed", "reversed": "failed", "rejected": "failed",
                 "cancelled": "failed"}.get(st, "processing")
        reason = (d.get("status_details") or {}).get("description") or (d.get("failure_reason") or "") or st.title()
        return {"state": state, "ref": d.get("id") or "", "utr": d.get("utr") or "", "message": reason}

    @classmethod
    def verify_webhook(cls, raw, headers):
        secret = cls._env()["hook"]
        sig = headers.get("x-razorpay-signature", "")
        if not (secret and sig):
            return False
        return hmac.compare_digest(hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest(), sig)

    @staticmethod
    def parse_webhook(payload):
        ent = ((payload.get("payload") or {}).get("payout") or {}).get("entity") or {}
        pid = str((ent.get("notes") or {}).get("payout_id") or "")
        if not pid.isdigit() or not (payload.get("event") or "").startswith("payout."):
            return None, None
        res = RazorpayX._state(ent)
        if res["state"] == "processing":
            return None, None
        return int(pid), res


PROVIDERS = {"cashfree": Cashfree, "razorpayx": RazorpayX}


# ───────────────────────────── the flow ─────────────────────────────
def needs_approval(payout, cfg=None):
    from apps.commerce.models import Payout

    cfg = cfg or config()
    if payout.amount > cfg["auto_limit"]:
        return f"Above the automatic limit of ₹{cfg['auto_limit']:,.0f}"
    if cfg["first_needs_approval"] and not Payout.objects.filter(dj=payout.dj, status="completed").exists():
        return "First payout to this DJ"
    return ""


def dispatch(payout_id, approved_by=None):
    """Send a pending payout now if automatic payouts are on. Returns a short status string."""
    from apps.commerce.models import Payout

    provider = active_provider()
    if provider is None:
        return "manual"
    with transaction.atomic():
        payout = Payout.objects.select_for_update().select_related("dj__profile__user").get(pk=payout_id)
        if payout.status != "pending":
            return payout.status
        if not approved_by:
            why = needs_approval(payout)
            if why:
                if payout.hold_reason != f"Waiting for admin approval: {why}":
                    payout.hold_reason = f"Waiting for admin approval: {why}"
                    payout.save(update_fields=["hold_reason"])
                    transaction.on_commit(lambda: _admin_alert(f"Payout #{payout.id} (₹{payout.amount}, {payout.dj.dj_name}) needs your OK: {why}. Admin → Payouts."))
                return "approval"
        payout.status, payout.provider, payout.sent_at, payout.hold_reason = "processing", provider.name, timezone.now(), None
        payout.save(update_fields=["status", "provider", "sent_at", "hold_reason"])
    try:
        result = provider.send(payout)
    except PayoutError as exc:
        reverse_payout(payout.id, f"{provider.label}: {exc}")
        return "failed"
    except PayoutUnknown as exc:
        logger.warning("Payout %s status unknown after send: %s", payout.id, exc)
        Payout.objects.filter(pk=payout.id).update(failure_reason=f"Checking status: {exc}"[:500])
        return "processing"
    except Exception as exc:  # anything unexpected: treat as unknown, never re-send blindly
        logger.exception("Payout %s send crashed", payout.id)
        Payout.objects.filter(pk=payout.id).update(failure_reason=f"Checking status: {exc}"[:500])
        return "processing"
    apply_result(payout.id, result)
    return result["state"]


def apply_result(payout_id, result):
    """Record what the provider says. Idempotent: webhooks and status checks may repeat."""
    from apps.commerce.models import Payout

    state = result.get("state")
    with transaction.atomic():
        payout = Payout.objects.select_for_update().select_related("dj__profile__user").get(pk=payout_id)
        if payout.status in ("completed", "failed"):
            return payout.status
        if result.get("ref"):
            payout.provider_ref = result["ref"][:100]
        if state == "paid":
            payout.status = "completed"
            payout.processed_at = timezone.now()
            payout.utr = (result.get("utr") or "")[:64]
            payout.payment_reference = f"{payout.provider or 'auto'} · UTR {payout.utr}" if payout.utr else f"{payout.provider or 'auto'} · {payout.provider_ref}"
            payout.failure_reason = None
            payout.save(update_fields=["status", "processed_at", "utr", "payment_reference", "provider_ref", "failure_reason"])
            transaction.on_commit(lambda: _paid_notice(payout))
            return "completed"
        payout.save(update_fields=["provider_ref"])
    if state == "failed":
        reverse_payout(payout_id, result.get("message") or "Transfer failed")
        return "failed"
    return "processing"


def reverse_payout(payout_id, reason, by_admin=False):
    """Mark the payout failed and put the money back in the DJ's balance (once)."""
    from apps.commerce.models import DJWallet, LedgerEntry, Payout

    with transaction.atomic():
        payout = Payout.objects.select_for_update().select_related("dj__profile__user").get(pk=payout_id)
        if payout.status in ("completed", "failed"):
            return False
        wallet = DJWallet.objects.select_for_update().get(dj=payout.dj)
        wallet.available_for_payout += payout.amount
        wallet.pending_earnings += payout.amount
        wallet.save(update_fields=["available_for_payout", "pending_earnings", "updated_at"])
        LedgerEntry.objects.create(
            wallet=wallet, amount=payout.amount, entry_type="credit",
            description=f"Payout #{payout.id} failed - returned to balance",
            metadata={"payout_id": payout.id, "type": "payout_reversal", "reason": str(reason)[:200]},
        )
        payout.status = "failed"
        payout.failure_reason = str(reason)[:500]
        payout.hold_reason = payout.failure_reason if by_admin else payout.hold_reason
        payout.auto_retry_count = 99  # money is back in the balance: never auto-retry this one
        payout.save(update_fields=["status", "failure_reason", "hold_reason", "auto_retry_count"])
        transaction.on_commit(lambda: _failed_notice(payout))
    return True


def sync_processing(max_items=50, dj=None):
    """Ask the provider about payouts still in flight (missed webhooks, timeouts)."""
    from datetime import timedelta

    from apps.commerce.models import Payout

    done = {"checked": 0, "paid": 0, "failed": 0}
    cutoff = timezone.now() - timedelta(minutes=5)
    qs = Payout.objects.filter(status="processing", provider__in=list(PROVIDERS), sent_at__lt=cutoff).select_related("dj")
    if dj is not None:
        qs = qs.filter(dj=dj)
    for p in qs[:max_items]:
        provider = PROVIDERS[p.provider]
        if not provider.configured():
            continue
        done["checked"] += 1
        try:
            res = provider.fetch(p)
        except PayoutError as exc:  # e.g. the provider never received it
            if "not found" in str(exc).lower() or "does not exist" in str(exc).lower():
                reverse_payout(p.id, f"{provider.label} has no record of this transfer")
                done["failed"] += 1
            continue
        except PayoutUnknown:
            continue
        out = apply_result(p.id, res)
        if out == "completed":
            done["paid"] += 1
        elif out == "failed":
            done["failed"] += 1
    return done


def send_pending(max_items=100):
    """Send every pending payout that doesn't need approval (used after switching automatic payouts on)."""
    from apps.commerce.models import Payout

    out = {}
    for pid in Payout.objects.filter(status="pending").order_by("created_at").values_list("id", flat=True)[:max_items]:
        r = dispatch(pid)
        out[r] = out.get(r, 0) + 1
    return out


# ───────────────────────────── notices ─────────────────────────────
def _admin_alert(text):
    try:
        from apps.admin_panel.telegram import notify_admins

        notify_admins(text)
    except Exception:
        pass


def _paid_notice(payout):
    _admin_alert(f"Paid automatically: payout #{payout.id}, ₹{payout.amount} to {payout.dj.dj_name} ({payout.payment_reference}).")
    try:
        from django.utils.html import escape

        from apps.admin_panel.email_utils import send_email

        send_email(
            payout.dj.profile.user.email,
            f"MixMint payout sent: ₹{payout.amount}",
            f"<p>Hi {escape(payout.dj.dj_name)},</p><p>We sent <b>₹{payout.amount}</b> to your "
            f"{'UPI ID' if (payout.dj.payout_details or {}).get('method') == 'upi' else 'bank account'}.</p>"
            + (f"<p>Bank reference (UTR): <b>{escape(payout.utr)}</b></p>" if payout.utr else "")
            + "<p>It usually shows within minutes. You can see every payout on your Payouts page.</p>",
        )
    except Exception:
        logger.exception("Paid email failed for payout %s", payout.id)


def _failed_notice(payout):
    _admin_alert(f"Payout #{payout.id} to {payout.dj.dj_name} failed: {payout.failure_reason}. The ₹{payout.amount} is back in their balance.")
    try:
        from django.utils.html import escape

        from apps.admin_panel.email_utils import send_email

        send_email(
            payout.dj.profile.user.email,
            "Your MixMint payout didn't go through",
            f"<p>Hi {escape(payout.dj.dj_name)},</p><p>Your payout of <b>₹{payout.amount}</b> couldn't be sent "
            f"({escape(payout.failure_reason or 'the bank declined it')}). The money is back in your MixMint balance.</p>"
            "<p>Please check your UPI ID or bank details on the Payouts page, then withdraw again.</p>",
        )
    except Exception:
        logger.exception("Failed-payout email failed for payout %s", payout.id)
