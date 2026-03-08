from apps.core.seo_utils import get_default_og_tags

def seo_context(request):
    """Provide default OG tags to all templates."""
    return {
        'og_tags': get_default_og_tags()
    }
