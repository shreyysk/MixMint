"""Current commission rates (Admin → Offers & pricing), formatted for copy and reports."""


def _fmt(v):
    v = float(v)
    return int(v) if v == int(v) else round(v, 1)


def rates():
    """(standard %, pro %) as numbers, e.g. (20, 12). Pro never exceeds standard."""
    from apps.admin_panel.models import PlatformSettings

    ps = PlatformSettings.load()
    std = _fmt(ps.platform_commission_rate)
    return std, _fmt(min(ps.pro_commission_rate, ps.platform_commission_rate))


def commission_label(is_pro):
    std, pro = rates()
    return f"{pro if is_pro else std}%"
