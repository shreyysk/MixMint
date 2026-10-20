"""Go-live reset: clear test sales and money records, and remove test accounts, without touching real DJs' music.

Used from Admin → Settings → "Launch: clear test data". Two separate actions, each needs the admin to type RESET:

  reset_sales()          every order, invoice, ledger line, payout, refund, dispute, cart and webhook log is deleted,
                         every DJ wallet goes to ₹0, and sale / download / view counters go back to 0.
                         Accounts, DJ stores, tracks, albums, bundles, settings and files stay.
  delete_accounts(ids)   the chosen non-admin accounts and everything they own (their music, orders, wallet).
"""

from django.db import transaction
from django.db.models import Q

TEST_HINTS = ("@example.", "@test.", "+test", "test@", "demo", "dummy", "fake", "mailinator", "yopmail", "@mixmint.test")


def _models():
    from apps.commerce import models as cm

    out = [cm.PurchaseDispute, cm.TransactionAlert, cm.RefundRequest, cm.Invoice, cm.TaxRecord, cm.LedgerEntry,
           cm.EarningsHold, cm.Payout, cm.BundlePurchase, cm.CartItem, cm.Cart, cm.WebhookLog, cm.AdRevenueLog,
           cm.OffloadNotification, cm.ProSubscriptionEvent, cm.StorageOverage, cm.DJApplicationFee, cm.Purchase]
    try:
        from apps.commerce.dj_conversion import DJMilestoneReward

        out.insert(0, DJMilestoneReward)
    except Exception:
        pass
    try:
        from apps.admin_panel.models import VaultNotify

        out.append(VaultNotify)
    except Exception:
        pass
    return out


def preview():
    from apps.accounts.models import User
    from apps.commerce.models import DJWallet, Purchase

    paid = Purchase.objects.filter(status="paid")
    return {
        "orders": Purchase.objects.count(),
        "paid_orders": paid.count(),
        "records": sum(m.objects.count() for m in _models()),
        "wallets": DJWallet.objects.exclude(total_earnings=0, available_for_payout=0, pending_earnings=0, escrow_amount=0).count(),
        "accounts": User.objects.exclude(_admin_q()).count(),
        "suspects": suspects(),
    }


def _admin_q():
    return Q(is_superuser=True) | Q(is_staff=True) | Q(profile__role="admin")


def suspects(limit=200):
    """Non-admin accounts that look like test accounts (shown pre-ticked) plus everyone else (unticked)."""
    from apps.accounts.models import User

    rows = []
    for u in User.objects.exclude(_admin_q()).select_related("profile").order_by("date_joined")[:limit]:
        email = (u.email or "").lower()
        dj = getattr(getattr(u, "profile", None), "dj_profile", None)
        rows.append({"id": u.pk, "email": u.email, "role": getattr(getattr(u, "profile", None), "role", ""),
                     "dj": dj.dj_name if dj else "", "joined": u.date_joined, "test": any(h in email for h in TEST_HINTS)})
    rows.sort(key=lambda r: (not r["test"], r["joined"]))
    return rows


@transaction.atomic
def reset_sales():
    from apps.accounts.models import DJProfile
    from apps.albums.models import AlbumPack
    from apps.commerce.models import DJWallet
    from apps.tracks.models import Track

    deleted = 0
    for m in _models():
        n, _ = m.objects.all().delete()
        deleted += n
    DJWallet.objects.update(total_earnings=0, pending_earnings=0, escrow_amount=0, available_for_payout=0)
    Track.objects.update(download_count=0, sales_last_7_days=0)
    for f in ("download_count", "sales_last_7_days"):
        if any(x.name == f for x in AlbumPack._meta.fields):
            AlbumPack.objects.update(**{f: 0})
    DJProfile.objects.update(total_revenue=0, weekly_views=0, popularity_score=0)
    _clear_cache()
    return deleted


@transaction.atomic
def delete_accounts(ids):
    from apps.accounts.models import User

    qs = User.objects.filter(pk__in=list(ids)).exclude(_admin_q())
    n = qs.count()
    qs.delete()  # cascades: profile, DJ store, music, orders, wallet
    _clear_cache()
    return n


def _clear_cache():
    from django.core.cache import cache

    try:
        cache.clear()
    except Exception:
        pass
