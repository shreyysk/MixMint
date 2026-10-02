"""{% icon "name" %} → an inline Lucide SVG that inherits the text colour. Works with no {% load %} (builtin)."""

from django import template
from django.utils.html import format_html, mark_safe

from apps.core.icons_data import ICONS

register = template.Library()


def svg(name, size="1.15em", cls="", label=""):
    inner = ICONS.get(name)
    if inner is None:
        return ""
    a11y = format_html(' role="img" aria-label="{}"', label) if label else mark_safe(' aria-hidden="true"')
    return format_html(
        '<svg class="mm-icon {}" width="{}" height="{}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round" focusable="false"{}>{}</svg>',
        cls, size, size, a11y, mark_safe(inner),
    )


@register.simple_tag
def icon(name, size="1.15em", cls="", label=""):
    return svg(name, size, cls, label)
