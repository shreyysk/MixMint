"""Account settings for every user: name, password, sessions, data export, delete account."""

from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from .validators import validate_strong_password


def _other_sessions(user, current_key):
    from django.contrib.sessions.models import Session
    from django.utils import timezone

    keys = []
    for s in Session.objects.filter(expire_date__gte=timezone.now()).iterator():
        try:
            if s.get_decoded().get("_auth_user_id") == str(user.pk) and s.session_key != current_key:
                keys.append(s.session_key)
        except Exception:
            continue
    return keys


@login_required
def account_settings_view(request):
    user, profile = request.user, request.user.profile
    has_password = user.has_usable_password()
    google = user.social_auth.filter(provider="google-oauth2").exists() if hasattr(user, "social_auth") else False

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "name":
            name = (request.POST.get("full_name") or "").strip()[:120]
            if not name:
                messages.error(request, "Your name can't be empty.")
            else:
                profile.full_name = name
                profile.save(update_fields=["full_name"])
                messages.success(request, "Name saved.")

        elif action == "password":
            current = request.POST.get("current_password") or ""
            new, again = request.POST.get("new_password") or "", request.POST.get("confirm_password") or ""
            if has_password and not user.check_password(current):
                messages.error(request, "Your current password is wrong.")
            elif new != again:
                messages.error(request, "The new passwords don't match.")
            else:
                try:
                    validate_strong_password(new)
                except ValidationError as exc:
                    messages.error(request, exc.messages[0])
                else:
                    user.set_password(new)
                    user.save(update_fields=["password"])
                    update_session_auth_hash(request, user)  # stay logged in here
                    messages.success(request, "Password changed." if has_password else "Password set. You can now log in with email too.")

        elif action == "logout_others":
            from django.contrib.sessions.models import Session

            keys = _other_sessions(user, request.session.session_key)
            Session.objects.filter(session_key__in=keys).delete()
            messages.success(request, f"Logged out of {len(keys)} other device{'s' if len(keys) != 1 else ''}.")

        elif action == "delete":
            ok = user.check_password(request.POST.get("confirm") or "") if has_password else (
                (request.POST.get("confirm") or "").strip().upper() == "DELETE"
            )
            if not ok:
                messages.error(request, "Account not deleted: " + ("the password was wrong." if has_password else "type DELETE to confirm."))
            elif user.is_staff:
                messages.error(request, "Admin accounts can't be deleted from here.")
            else:
                _request_deletion(request)
                logout(request)
                messages.success(request, "Your account is closed. Everything is removed within 30 days.")
                return redirect("home")
        return redirect("account_settings")

    return render(
        request,
        "dashboard/account_settings.html",
        {"profile": profile, "has_password": has_password, "google": google, "other_sessions": len(_other_sessions(user, request.session.session_key))},
    )


def _request_deletion(request):
    from apps.admin_panel.models import AuditLog
    from apps.core.net import get_client_ip

    profile = request.user.profile
    profile.is_banned = True  # blocks login immediately
    profile.store_paused = True
    profile.save(update_fields=["is_banned", "store_paused"])
    try:
        AuditLog.objects.create(admin=None, action=f"User {request.user.email} deleted their account.", ip_address=get_client_ip(request))
    except Exception:
        pass
    try:
        from apps.admin_panel.telegram import notify_admins

        notify_admins(f"🗑 {request.user.email} closed their account. Remove their data within 30 days.")
    except Exception:
        pass
