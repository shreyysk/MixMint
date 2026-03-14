from django import template

register = template.Library()

@register.filter(name='split')
def split(value, arg):
    return value.split(arg)

@register.filter(name='money')
def money(value):
    """Formats decimal to ₹XX.XX"""
    try:
        return f"₹{float(value):,.2f}"
    except (ValueError, TypeError):
        return value

@register.filter(name='duration')
def duration(value):
    """Formats seconds to MM:SS"""
    try:
        seconds = int(value)
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins}:{secs:02d}"
    except (ValueError, TypeError):
        return "00:00"
