"""
Catalogue helpers shared by pages and checkout: limited drops (copy counts), discounts, types.

Limited drop = a track or album with `copies_limit`. A copy counts as taken when it's paid (and
not refunded/revoked), or when a checkout for it started in the last 15 minutes (so two
buyers can't both pay for the last copy).
"""

from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

HOLD_MINUTES = 15


def _taken_q():
    recent = timezone.now() - timedelta(minutes=HOLD_MINUTES)
    return Q(status="paid", is_revoked=False, is_redownload=False) | Q(status="pending", created_at__gte=recent)


def copies_taken(kind, ids):
    """{content_id: copies taken} for many items in one query."""
    from apps.commerce.models import Purchase

    ids = [i for i in ids if i is not None]
    if not ids:
        return {}
    rows = (
        Purchase.objects.filter(_taken_q(), content_type=kind, content_id__in=ids)
        .values("content_id")
        .annotate(n=Count("id"))
    )
    return {r["content_id"]: r["n"] for r in rows}


def copies_left(item, kind):
    if not getattr(item, "copies_limit", None):
        return None
    taken = copies_taken(kind, [item.id]).get(item.id, 0)
    return max(item.copies_limit - taken, 0)


def sold_out(item, kind):
    left = copies_left(item, kind)
    return left is not None and left <= 0


def attach_stock(items, kind):
    """Set item.copies_left_cached on a list of tracks/albums (None when unlimited)."""
    limited = [i for i in items if getattr(i, "copies_limit", None)]
    taken = copies_taken(kind, [i.id for i in limited])
    for i in items:
        i.copies_left_cached = max(i.copies_limit - taken.get(i.id, 0), 0) if getattr(i, "copies_limit", None) else None
    return items


def savings_percent(price, was):
    try:
        price, was = float(price), float(was or 0)
    except (TypeError, ValueError):
        return 0
    return int(round((1 - price / was) * 100)) if was > price > 0 else 0
