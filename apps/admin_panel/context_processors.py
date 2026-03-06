from apps.admin_panel.models import PlatformSettings, PromotionalOffer

def global_settings(request):
    """
    Injects global platform settings and the active promotional offer into all templates.
    [Spec P3 v3]
    """
    settings = PlatformSettings.load()
    active_offer = PromotionalOffer.objects.filter(is_active=True).first()
    
    return {
        'platform_settings': settings,
        'active_promotional_offer': active_offer
    }
