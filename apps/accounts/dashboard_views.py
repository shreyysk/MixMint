from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json


@login_required
def dashboard_view(request):
    """User dashboard — shows all owned tracks and albums [Spec §3.1, §9]."""
    profile = request.user.profile
    
    # Fetch all completed purchases
    purchases = profile.purchases.filter(
        status='paid',
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

    # Fetch wishlist items [Imp 13]
    wishlist_tracks = profile.wishlist_items.select_related('track', 'track__dj')

    # [P2-01.02 FIX] Get wallet info for buyer
    wallet = None
    if hasattr(profile, 'dj_profile'):
        try:
            wallet = profile.dj_profile.wallet
        except Exception:
            pass

    # Check if user is a DJ
    is_dj = profile.role == 'dj'

    context = {
        'profile': profile,
        'tracks': tracks,
        'albums': albums,
        'wishlist_tracks': wishlist_tracks,
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

    # Calculate Storage Usage
    total_bytes = 0
    forecast = None
    if dj_profile:
        from apps.tracks.models import Track
        from apps.albums.models import AlbumPack
        from django.db.models import Sum
        from apps.commerce.analytics import calculate_earnings_forecast

        track_storage = Track.objects.filter(dj=dj_profile, is_deleted=False).aggregate(total=Sum('file_size'))['total'] or 0
        album_storage = AlbumPack.objects.filter(dj=dj_profile, is_deleted=False).aggregate(total=Sum('file_size'))['total'] or 0
        total_bytes = track_storage + album_storage
        
        # Calculate earnings forecast [Imp 11]
        try:
            forecast = calculate_earnings_forecast(dj_profile.id)
        except Exception:
            pass
            
        # Fetch Offload Notifications (Phase 3 Feature 1)
        from apps.commerce.models import OffloadNotification
        offload_notifications = OffloadNotification.objects.filter(dj=dj_profile).order_by('-created_at')
        
        # Fetch Recent Sales for DJ Dashboard (Phase 3 Feature 2)
        from apps.commerce.models import Purchase
        recent_sales = Purchase.objects.filter(seller=dj_profile, status='paid').select_related('user', 'user__dj_profile').order_by('-created_at')[:10]
    else:
        offload_notifications = []
        recent_sales = []

    storage_used_mb = total_bytes / (1024 * 1024)
    storage_quota_mb = profile.storage_quota_mb
    storage_percent = (storage_used_mb / storage_quota_mb) * 100 if storage_quota_mb > 0 else 0

    context = {
        'profile': profile,
        'dj_profile': dj_profile,
        'wallet': wallet,
        'storage_used_mb': round(storage_used_mb, 2),
        'storage_quota_mb': storage_quota_mb,
        'storage_percent': min(round(storage_percent, 1), 100),
        'is_pro': profile.is_pro_dj,
        'forecast': forecast,
        'offload_notifications': offload_notifications,
        'recent_sales': recent_sales,
    }
    return render(request, 'dashboard/dj_content.html', context)


@login_required
@require_POST
def add_custom_domain(request):
    """Pro feature: Connect a custom domain [Section C Fix 02]."""
    profile = request.user.profile
    if not profile.is_pro_dj:
        return JsonResponse({'error': 'Pro subscription required.'}, status=403)
    
    try:
        data = json.loads(request.body)
        domain = data.get('domain', '').lower().strip()
    except:
        return JsonResponse({'error': 'Invalid request.'}, status=400)

    if not domain:
        return JsonResponse({'error': 'Domain name is required.'}, status=400)

    from .vercel import VercelManager
    vm = VercelManager()
    
    try:
        vm.add_domain(domain)
        dj_profile = profile.dj_profile
        dj_profile.custom_domain = domain
        dj_profile.save()
        return JsonResponse({'status': 'success', 'message': f'Domain {domain} added. Please update your DNS.'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
@login_required
def enable_2fa(request):
    """Pro feature / DJ Security: Initiate TOTP setup [Fix 06]."""
    profile = request.user.profile
    if profile.role != 'dj':
        return JsonResponse({'error': 'DJs only.'}, status=403)
    
    dj_profile = profile.dj_profile
    from .payout_auth import get_totp_uri
    uri = get_totp_uri(dj_profile)
    
    return JsonResponse({
        'status': 'success',
        'totp_uri': uri,
        'secret': dj_profile.payout_otp_secret # Also show secret for manual entry
    })

@login_required
@require_POST
def verify_2fa_setup(request):
    """Verify and lock in 2FA setup."""
    profile = request.user.profile
    try:
        data = json.loads(request.body)
        code = data.get('code')
    except:
        return JsonResponse({'error': 'Invalid request.'}, status=400)

    dj_profile = profile.dj_profile
    from .payout_auth import verify_totp
    success, message = verify_totp(dj_profile, code)
    
    if success:
        # 2FA is now active
        return JsonResponse({'status': 'success', 'message': '2FA successfully enabled.'})
    return JsonResponse({'error': message}, status=400)@login_required
def dj_onboarding(request):
    """DJ Onboarding Wizard [Fix 07]."""
    profile = request.user.profile
    if profile.role != 'dj':
        return redirect('dashboard')
    
    dj_profile = profile.dj_profile
    if dj_profile.is_onboarding_complete:
        return redirect('dj_dashboard')

    context = {
        'dj_profile': dj_profile,
        'step': dj_profile.onboarding_step,
    }
    return render(request, 'dashboard/dj_onboarding.html', context)

@login_required
@require_POST
def update_onboarding_step(request):
    """Moves the DJ to the next onboarding step."""
    profile = request.user.profile
    dj_profile = profile.dj_profile
    
    try:
        data = json.loads(request.body)
        step = data.get('step')
    except:
        return JsonResponse({'error': 'Invalid request.'}, status=400)

    # Basic step progression
    steps = ['profile_setup', 'payout_setup', 'first_track', 'completed']
    if step not in steps:
        return JsonResponse({'error': 'Invalid step.'}, status=400)

    dj_profile.onboarding_step = step
    if step == 'completed':
        dj_profile.is_onboarding_complete = True
    dj_profile.save()

    return JsonResponse({'status': 'success', 'next_step': step})


@login_required
def export_user_data(request):
    """GDPR-compliant data export [Imp 02]."""
    profile = request.user.profile
    
    data = {
        'profile': {
            'full_name': profile.full_name,
            'role': profile.role,
            'is_pro': profile.is_pro_dj,
            'joined_at': profile.created_at.isoformat(),
        },
        'purchases': [
            {
                'id': p.id,
                'content_type': p.content_type,
                'content_id': p.content_id,
                'price_paid': str(p.price_paid),
                'date': p.created_at.isoformat()
            } for p in profile.purchases.all()
        ],
        'ratings': [
            {
                'content_type': r.content_type,
                'content_id': r.content_id,
                'stars': r.stars,
                'review': r.review,
                'date': r.created_at.isoformat()
            } for r in profile.ratings_given.all()
        ],
        'disputes': [
            {
                'id': d.id,
                'reason': d.reason,
                'status': d.status,
                'date': d.created_at.isoformat()
            } for d in profile.disputes_opened.all()
        ]
    }
    
    response = JsonResponse(data, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = 'attachment; filename="mixmint_data_export.json"'
    return response

@login_required
@require_POST
def request_account_deletion(request):
    """Soft-delete account and mark for permanent deletion [Imp 02]."""
    profile = request.user.profile
    profile.is_banned = True # Prevent login
    profile.store_paused = True
    profile.save()
    
    # Log the request for admin
    from apps.admin_panel.models import AuditLog
    AuditLog.objects.create(
        admin=None, # User-initiated
        action=f"User {request.user.email} requested account deletion.",
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    return JsonResponse({'status': 'success', 'message': 'Account deletion requested. Your account will be removed within 30 days.'})


@login_required
def active_sessions(request):
    """List active user sessions [Imp 05]."""
    from django.contrib.sessions.models import Session
    from django.utils import timezone
    
    sessions = Session.objects.filter(expire_date__gte=timezone.now())
    user_sessions = []
    
    for session in sessions:
        decoded = session.get_decoded()
        if decoded.get('_auth_user_id') == str(request.user.id):
            user_sessions.append({
                'session_key': session.session_key,
                'expire_date': session.expire_date.isoformat(),
                'is_current': session.session_key == request.session.session_key
            })
            
    return render(request, 'dashboard/sessions.html', {'sessions': user_sessions})

@login_required
@require_POST
def logout_device(request):
    """Terminate a specific session [Imp 05]."""
    session_key = json.loads(request.body).get('session_key')
    from django.contrib.sessions.models import Session
    
    try:
        session = Session.objects.get(session_key=session_key)
        if session.get_decoded().get('_auth_user_id') == str(request.user.id):
            session.delete()
            return JsonResponse({'status': 'success'})
    except:
        pass
    
    return JsonResponse({'status': 'error', 'message': 'Session not found.'}, status=404)

@login_required
def check_custom_domain_status(request):
    """Check DNS and SSL status via Vercel API."""
    profile = request.user.profile
    dj_profile = profile.dj_profile
    domain = dj_profile.custom_domain

    if not domain:
        return JsonResponse({'error': 'No custom domain configured.'}, status=404)

    from .vercel import VercelManager
    vm = VercelManager()
    status = vm.get_domain_status(domain)
    
    if status:
        return JsonResponse({'status': 'success', 'data': status})
    return JsonResponse({'error': 'Could not fetch status.'}, status=500)

@login_required
def bundle_management_view(request):
    """Imp 12: View and manage track bundles."""
    if request.user.profile.role != 'dj':
        return redirect('dashboard')
    
    dj_profile = request.user.profile.dj_profile
    bundles = dj_profile.bundles.filter(is_deleted=False).prefetch_related('bundle_tracks__track')
    tracks = dj_profile.tracks.filter(is_deleted=False, is_active=True)
    
    context = {
        'bundles': bundles,
        'tracks': tracks,
    }
    return render(request, 'dashboard/bundles.html', context)

@login_required
@require_POST
def create_bundle_view(request):
    """Create a new discounted track bundle."""
    from apps.commerce.models import Bundle, BundleTrack
    dj_profile = request.user.profile.dj_profile
    
    title = request.POST.get('title')
    price = request.POST.get('price')
    selected_tracks = request.POST.getlist('tracks') # track IDs
    
    if not title or not price or not selected_tracks:
        return redirect('bundle_management')
        
    bundle = Bundle.objects.create(
        dj=dj_profile,
        title=title,
        price=price
    )
    
    for track_id in selected_tracks:
        BundleTrack.objects.create(bundle=bundle, track_id=track_id)
        
    return redirect('bundle_management')

    return redirect('bundle_management')

@login_required
def announcement_management_view(request):
    """Imp 14: View and manage DJ announcements."""
    if request.user.profile.role != 'dj':
        return redirect('dashboard')
    
    dj_profile = request.user.profile.dj_profile
    announcements = dj_profile.announcements.all()
    
    return render(request, 'dashboard/announcements.html', {'announcements': announcements})

@login_required
@require_POST
def create_announcement_view(request):
    """Post a new update to the storefront."""
    from .models import DJAnnouncement
    dj_profile = request.user.profile.dj_profile
    
    title = request.POST.get('title')
    content = request.POST.get('content')
    
    if title and content:
        DJAnnouncement.objects.create(
            dj=dj_profile,
            title=title,
            content=content
        )
        
    return redirect('announcement_management')

@login_required
@require_POST
def delete_announcement_view(request, announcement_id):
    """Delete an announcement."""
    dj_profile = request.user.profile.dj_profile
    try:
        announcement = dj_profile.announcements.get(id=announcement_id)
        announcement.delete()
    except:
        pass
    return redirect('announcement_management')

@login_required
def ambassador_management_view(request):
    """Imp 15: DJ Ambassador Program management."""
    if request.user.profile.role != 'dj':
        return redirect('dashboard')
    
    dj_profile = request.user.profile.dj_profile
    ambassador = getattr(dj_profile, 'ambassador_code', None)
    
    referrals = dj_profile.referrals.select_related('profile__user').order_by('-created_at')[:20]
    
    context = {
        'ambassador': ambassador,
        'referrals': referrals,
        'referral_url': f"{request.build_absolute_uri('/')}?ref={ambassador.code}" if ambassador else None
    }
    return render(request, 'dashboard/ambassador.html', context)

@login_required
@require_POST
def generate_ambassador_code_view(request):
    """Generate a unique referral code for the DJ."""
    from .models import AmbassadorCode
    import random
    import string
    
    dj_profile = request.user.profile.dj_profile
    if hasattr(dj_profile, 'ambassador_code'):
        return redirect('ambassador_management')
    
    # Generate unique 8-char code
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    while AmbassadorCode.objects.filter(code=code).exists():
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
    AmbassadorCode.objects.create(dj=dj_profile, code=code)
    return redirect('ambassador_management')
