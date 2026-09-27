"""Gateway selection. One place decides which gateway handles a new order."""

import logging

from django.conf import settings

logger = logging.getLogger("mixmint")

SUPPORTED_GATEWAYS = ("phonepe", "razorpay")


def active_gateway_name():
    """Admin toggle (SystemSetting) wins over the DEFAULT_PAYMENT_GATEWAY env var."""
    try:
        from apps.admin_panel.models import SystemSetting

        row = SystemSetting.objects.filter(key="active_payment_gateway").first()
        name = (row.value or {}).get("gateway") if row else None
        if name in SUPPORTED_GATEWAYS:
            return name
    except Exception:  # table missing during migrations, etc.
        pass
    name = getattr(settings, "DEFAULT_PAYMENT_GATEWAY", "phonepe")
    return name if name in SUPPORTED_GATEWAYS else "phonepe"


def get_gateway(gateway_name=None):
    """Instantiate a gateway. Unknown/empty names fall back to the active gateway."""
    name = gateway_name if gateway_name in SUPPORTED_GATEWAYS else active_gateway_name()
    if name == "razorpay":
        from .razorpay_gateway import RazorpayGateway

        return RazorpayGateway()
    from .phonepe import PhonePeGateway

    return PhonePeGateway()
