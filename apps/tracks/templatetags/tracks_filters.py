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
