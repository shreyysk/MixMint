from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout as auth_logout
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from .models import User, Profile, LoginHistory
from .validators import validate_email_domain, validate_strong_password


def _get_client_ip(request):
    """Extract real client IP from request."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def signup_view(request):
    """User registration with Profile creation [Spec §3.1, §13]."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        is_dj = request.POST.get('is_dj') == 'on'

        # Validate temp email domains [Spec §13]
        try:
            validate_email_domain(email)
        except ValidationError as e:
            messages.error(request, e.message)
            return render(request, 'auth/signup.html')

        # Validate strong password [Spec §11]
        try:
            validate_strong_password(password)
        except ValidationError as e:
            messages.error(request, e.message)
            return render(request, 'auth/signup.html')

        if not full_name:
            messages.error(request, 'Full name is required.')
            return render(request, 'auth/signup.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'An account with this email already exists.')
            return render(request, 'auth/signup.html')

        with transaction.atomic():
            # Create User
            user = User.objects.create_user(
                email=email,
                password=password,
                role='dj' if is_dj else 'user',
                first_name=full_name.split(' ')[0] if ' ' in full_name else full_name,
                last_name=full_name.split(' ', 1)[1] if ' ' in full_name else ''
            )

            # Create Profile [CRITICAL: was missing, caused downstream crashes]
            Profile.objects.create(
                user=user,
                full_name=full_name,
            )

            login(request, user)

            # Bind IP to session [Spec §13]
            request.session['bound_ip'] = _get_client_ip(request)

            # Record login history [Spec §13]
            device_hash = request.headers.get('X-Device-Hash') or request.POST.get('device_hash', '')
            
            LoginHistory.objects.create(
                user=user,
                ip_address=_get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                location_data={'device_hash': device_hash} if device_hash else {},
            )

            messages.success(request, f'Welcome to MixMint, {full_name}!')
            return redirect('dashboard')

    return render(request, 'auth/signup.html')


def login_view(request):
    """User login with login history recording [Spec §13]."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        email = request.POST.get('username', '').strip().lower()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)

        if user is not None:
            # Check if account is frozen [Spec §11]
            try:
                if user.profile.is_frozen:
                    messages.error(request, 'Your account has been frozen. Contact support.')
                    return render(request, 'auth/login.html')
                if user.profile.is_banned:
                    messages.error(request, 'Your account has been banned.')
                    return render(request, 'auth/login.html')
            except Profile.DoesNotExist:
                # Create profile if missing (legacy accounts)
                Profile.objects.create(
                    user=user,
                    full_name=f'{user.first_name} {user.last_name}'.strip() or user.email,
                )

            login(request, user)

            # Bind IP to session [Spec §13]
            request.session['bound_ip'] = _get_client_ip(request)

            # Record login history [Spec §13]
            device_hash = request.headers.get('X-Device-Hash') or request.POST.get('device_hash', '')
            
            LoginHistory.objects.create(
                user=user,
                ip_address=_get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                location_data={'device_hash': device_hash} if device_hash else {},
            )

            # Also ensure device is registered [Spec §13]
            if device_hash:
                from .models import UserDevice
                UserDevice.objects.update_or_create(
                    user=user,
                    fingerprint=device_hash,
                    defaults={'last_ip': _get_client_ip(request)}
                )

            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'auth/login.html')


@login_required
def logout_view(request):
    """User logout [Spec §13]."""
    auth_logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('home')


class HomeView:
    @staticmethod
    def as_view():
        def view(request):
            return render(request, 'home.html')
        return view


class ExploreView:
    @staticmethod
    def as_view():
        def view(request):
            return render(request, 'explore.html')
        return view
