from django.shortcuts import render, get_object_or_404
from .models import DJProfile

def dj_storefront_view(request, slug):
    """DJ public storefront [Spec §3.2]."""
    dj = get_object_or_404(DJProfile, slug=slug, status='approved')

    # Don't show content if DJ store is paused [Spec §3.2]
    if dj.profile.store_paused:
        return render(request, 'dj/store_paused.html', {'dj': dj})

    tracks = dj.tracks.filter(is_active=True, is_deleted=False).order_by('-created_at')
    albums = dj.albums.filter(is_active=True, is_deleted=False).order_by('-created_at')

    # Fetch announcements [Imp 14]
    announcements = dj.announcements.filter(is_active=True).order_by('-created_at')[:5]

    from apps.core.seo_utils import get_dj_storefront_og_tags
    
    # [Missing Item 02] Record storefront view
    try:
        from apps.accounts.utils import record_dj_page_view
        record_dj_page_view(dj.id, 'storefront', request)
    except Exception:
        pass
    
    context = {
        'dj': dj,
        'tracks': tracks,
        'albums': albums,
        'announcements': announcements,
        'og_tags': get_dj_storefront_og_tags(dj),
    }
    return render(request, 'dj/profile.html', context)
