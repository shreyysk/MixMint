from apps.core.seo_utils import get_default_og_tags


FOOTER_GENRES = [(g.lower().replace(" ", "-").replace("&", "and").replace("--", "-"), g) for g in (
    "Tulu", "Kannada", "Mangalore", "Konkani", "Tamil", "Telugu", "Malayalam", "Hindi", "Marathi", "Punjabi",
    "Bollywood", "Bollywood Remix", "House", "Techno", "EDM", "Hip-Hop")]


def seo_context(request):
    """Default link-preview tags for every page (pages with their own tags override them), and the
    site-wide structured data (Organization + search box) on the home page."""
    tags = get_default_og_tags()
    try:
        tags["og:url"] = request.build_absolute_uri(request.path)
    except Exception:
        pass
    ctx = {"og_tags": tags, "footer_genres": FOOTER_GENRES}
    if request.path == "/":
        from apps.core.seo_utils import site_ld

        ctx["site_ld_json"] = site_ld()
    return ctx
