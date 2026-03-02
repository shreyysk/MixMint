from django.shortcuts import render, get_object_or_404
from .models import Track

def track_detail_view(request, pk):
    track = get_object_or_404(Track, pk=pk)
    previews = track.previews.filter(is_active=True)
    versions = track.versions.all()
    
    context = {
        'track': track,
        'previews': previews,
        'versions': versions,
    }
    return render(request, 'tracks/detail.html', context)
