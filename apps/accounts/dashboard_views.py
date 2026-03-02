from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


@login_required
def dashboard_view(request):
    """User dashboard — shows recent purchases [Spec §3.1]."""
    profile = request.user.profile
    # Only show completed purchases with successful downloads [Spec §3.1]
    purchases = profile.purchases.filter(
        is_completed=True,
        download_completed=True,
    ).order_by('-created_at')[:5]

    is_dj = request.user.role == 'dj'
    wallet = None
    if is_dj:
        try:
            wallet = profile.dj_profile.wallet
        except Exception:
            pass

    context = {
        'profile': profile,
        'purchases': purchases,
        'wallet': wallet,
        'is_dj': is_dj,
    }
    return render(request, 'dashboard/index.html', context)


@login_required
def dj_dashboard_view(request):
    """DJ-specific dashboard with earnings [Spec §3.2]."""
    if request.user.role != 'dj':
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
