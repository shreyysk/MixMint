from django import template

register = template.Library()


@register.filter(name="split")
def split(value, arg):
    return value.split(arg)


@register.filter(name="money")
def money(value):
    """₹1,299 for whole rupees, ₹49.50 otherwise."""
    try:
        amount = float(value)
    except (ValueError, TypeError):
        return value
    if abs(amount - round(amount)) < 0.005:
        return f"₹{round(amount):,}"
    return f"₹{amount:,.2f}"


@register.filter(name="price_label")
def price_label(value):
    """'Free' for zero-priced items, otherwise the money format."""
    try:
        if float(value) <= 0:
            return "Free"
    except (ValueError, TypeError):
        return value
    return money(value)


@register.filter(name="initials")
def initials(value):
    """'Aurora Pulse' -> 'AP' (for avatar placeholders)."""
    parts = [p for p in str(value or "").replace("_", " ").split() if p[:1].isalnum()]
    return ("".join(p[0] for p in parts[:2]) or "?").upper()


@register.filter(name="duration")
def duration(value):
    """Formats seconds to MM:SS"""
    try:
        seconds = int(value)
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins}:{secs:02d}"
    except (ValueError, TypeError):
        return "00:00"


@register.filter(name="left")
def left(item, kind="track"):
    """Copies left for a limited drop, or None when the item isn't limited."""
    if hasattr(item, "copies_left_cached"):
        return item.copies_left_cached
    from apps.core.catalog import copies_left

    return copies_left(item, kind)


@register.filter(name="off")
def off(item):
    """Discount percent vs the item's 'was' price (compare_at_price), 0 when none."""
    from apps.core.catalog import savings_percent

    return savings_percent(getattr(item, "price", 0), getattr(item, "compare_at_price", None))


@register.filter(name="preview")
def preview(item):
    """The release's own preview: {'embed', 'link', 'kind'} from its YouTube / Instagram link, or None.
    Bundles use their first track that has one."""
    from apps.core.embeds import instagram_code, youtube_id

    candidates = [item]
    if hasattr(item, "live_tracks"):
        candidates = item.live_tracks()
    for obj in candidates:
        order = ["instagram", "youtube"] if getattr(obj, "preview_type", "") == "instagram" else ["youtube", "instagram"]
        for kind in order:
            if kind == "youtube":
                vid = youtube_id(getattr(obj, "youtube_url", None))
                if vid:
                    return {"kind": "youtube", "link": obj.youtube_url,
                            "embed": f"https://www.youtube-nocookie.com/embed/{vid}?autoplay=1&rel=0&playsinline=1"}
            else:
                code = instagram_code(getattr(obj, "instagram_url", None))
                if code:
                    return {"kind": "instagram", "link": obj.instagram_url,
                            "embed": f"https://www.instagram.com/reel/{code}/embed"}
    return None
