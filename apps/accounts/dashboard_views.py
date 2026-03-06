from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


@login_required
def dashboard_view(request):
    """User dashboard — shows all owned tracks and albums [Spec §3.1, §9]."""
    profile = request.user.profile
    
    # Fetch all completed purchases
    purchases = profile.purchases.filter(
        is_completed=True,
    ).order_by('-created_at')

    # Resolve content objects (Tracks / Albums)
    # This avoids hitting the DB in a loop in the template
    tracks = []
    albums = []
    
    for purchase in purchases:
        try:
            if purchase.content_type == 'track':
                from apps.tracks.models import Track
                content = Track.objects.get(id=purchase.content_id)
                tracks.append({'purchase': purchase, 'content': content})
            elif purchase.content_type in ('album', 'zip'):
                from apps.albums.models import AlbumPack
                content = AlbumPack.objects.get(id=purchase.content_id)
                albums.append({'purchase': purchase, 'content': content})
        except Exception:
            # Skip if content is fully deleted/missing
            continue

    is_dj = profile.role == 'dj'
    wallet = None
    if is_dj:
        try:
            wallet = profile.dj_profile.wallet
        except Exception:
            pass

    context = {
        'profile': profile,
        'tracks': tracks,
        'albums': albums,
        'wallet': wallet,
        'is_dj': is_dj,
    }
    return render(request, 'dashboard/index.html', context)


@login_required
def dj_apply_view(request):
    """View to render the DJ application form."""
    profile = request.user.profile
    if profile.role == 'dj':
        return redirect('dj_dashboard')
    
    # Check if a DJProfile already exists (meaning they already applied)
    try:
        dj_profile = profile.dj_profile
        if dj_profile.status == 'pending_payment':
            # They need to pay the application fee
            fee = getattr(dj_profile, 'application_fee', None)
            context = {
                'dj_profile': dj_profile,
                'fee_amount': fee.amount if fee else 99.00,
                'status': 'pending_payment'
            }
            return render(request, 'dashboard/dj_apply_status.html', context)
        elif dj_profile.status == 'pending_review' or dj_profile.status == 'pending':
            context = {'status': 'pending_review'}
            return render(request, 'dashboard/dj_apply_status.html', context)
        elif dj_profile.status == 'rejected':
            context = {'status': 'rejected'}
            return render(request, 'dashboard/dj_apply_status.html', context)
    except Exception:
        pass
    
    return render(request, 'dashboard/dj_apply.html')


@login_required
def upload_track_view(request):
    """View to render the DJ upload form [Spec P3 §4]."""
    if request.user.profile.role != 'dj':
        return redirect('dashboard')
    
    return render(request, 'dashboard/upload.html')


@login_required
def dj_dashboard_view(request):
    """DJ-specific dashboard with earnings [Spec §3.2]."""
    if request.user.profile.role != 'dj':
        return redirect('dashboard')

    profile = request.user.profile
    try:
        dj_profile = profile.dj_profile
        wallet = dj_profile.wallet
    except Exception:
        wallet = None
        dj_profile = None

    context = {
        'profile': profile,
        'dj_profile': dj_profile,
        'wallet': wallet,
    }
    return render(request, 'dashboard/dj_content.html', context)
