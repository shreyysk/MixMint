from django.shortcuts import render, get_object_or_404
from .models import DJProfile

def dj_storefront_view(request, slug):
    """DJ public storefront [Spec §3.2]."""
    dj = get_object_or_404(DJProfile, slug=slug, status='approved')

    # Don't show content if DJ store is paused [Spec §3.2]
    if dj.store_paused:
        return render(request, 'dj/store_paused.html', {'dj': dj})

    tracks = dj.tracks.filter(is_active=True, is_deleted=False).order_by('-created_at')
    albums = dj.albums.filter(is_active=True, is_deleted=False).order_by('-created_at')

    context = {
        'dj': dj,
        'tracks': tracks,
        'albums': albums,
    }
    return render(request, 'dj/profile.html', context)
