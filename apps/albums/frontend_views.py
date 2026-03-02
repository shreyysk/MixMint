from django.shortcuts import render, get_object_or_404
from .models import AlbumPack

def album_detail_view(request, pk):
    album = get_object_or_404(AlbumPack, pk=pk)
    tracks = album.tracks.all().order_by('track_order')
    
    context = {
        'album': album,
        'tracks': tracks,
    }
    return render(request, 'albums/detail.html', context)
