"""
MixMint 2.0 — Shared test fixtures for comprehensive test suite.
Provides reusable factories for User, Profile, DJProfile, Track, Album, Cart, etc.
"""
import pytest
from decimal import Decimal
from django.test import Client


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def user_data():
    return {
        'email': 'buyer@example.com',
        'password': 'StrongPass123!',
        'full_name': 'Test Buyer',
    }


@pytest.fixture
def user(db):
    """Create a standard buyer user with auto-created Profile."""
    from apps.accounts.models import User
    u = User.objects.create_user(email='buyer@example.com', password='StrongPass123!')
    u.profile.full_name = 'Test Buyer'
    u.profile.role = 'user'
    u.profile.save(update_fields=['full_name', 'role'])
    return u


@pytest.fixture
def second_user(db):
    """Second buyer for isolation tests."""
    from apps.accounts.models import User
    u = User.objects.create_user(email='buyer2@example.com', password='StrongPass123!')
    u.profile.full_name = 'Buyer Two'
    u.profile.save(update_fields=['full_name'])
    return u


@pytest.fixture
def admin_user(db):
    """Create an admin/superuser with auto-created Profile."""
    from apps.accounts.models import User
    u = User.objects.create_superuser(email='admin@mixmint.site', password='AdminPass123!')
    u.profile.role = 'admin'
    u.profile.full_name = 'Platform Admin'
    u.profile.save(update_fields=['role', 'full_name'])
    return u


@pytest.fixture
def dj_user(db):
    """Create a DJ user with DJProfile and auto-created Profile."""
    from apps.accounts.models import User, DJProfile
    u = User.objects.create_user(email='dj@example.com', password='DJPass123!')
    u.profile.full_name = 'Test DJ'
    u.profile.role = 'dj'
    u.profile.save(update_fields=['full_name', 'role'])
    dj = DJProfile.objects.create(
        profile=u.profile,
        dj_name='Test DJ',
        slug='test-dj',
        status='approved',
        location='Mumbai, India',
    )
    return u, dj


@pytest.fixture
def pro_dj_user(db):
    """Create a Pro DJ user."""
    from apps.accounts.models import User, DJProfile
    u = User.objects.create_user(email='prodj@example.com', password='ProDJ123!')
    u.profile.full_name = 'Pro DJ'
    u.profile.role = 'dj'
    u.profile.is_pro_dj = True
    u.profile.save(update_fields=['full_name', 'role', 'is_pro_dj'])
    dj = DJProfile.objects.create(
        profile=u.profile,
        dj_name='Pro DJ',
        slug='pro-dj',
        status='approved',
    )
    return u, dj


@pytest.fixture
def track(dj_user):
    """Create a standard track."""
    from apps.tracks.models import Track
    _, dj = dj_user
    return Track.objects.create(
        dj=dj,
        title='Test Track',
        price=Decimal('100.00'),
        file_key='tracks/test-track.wav',
        preview_type='youtube',
        youtube_url='https://youtube.com/watch?v=test123',
        genre='EDM',
        bpm=128,
    )


@pytest.fixture
def free_track(dj_user):
    """Create a free track."""
    from apps.tracks.models import Track
    _, dj = dj_user
    return Track.objects.create(
        dj=dj,
        title='Free Track',
        price=Decimal('0.00'),
        file_key='tracks/free-track.wav',
        preview_type='youtube',
        youtube_url='https://youtube.com/watch?v=free123',
    )


@pytest.fixture
def album(dj_user):
    """Create a standard album."""
    from apps.albums.models import AlbumPack
    _, dj = dj_user
    return AlbumPack.objects.create(
        dj=dj,
        title='Test Album',
        price=Decimal('499.00'),
        file_key='albums/test-album.zip',
        preview_type='youtube',
        youtube_url='https://youtube.com/watch?v=album123',
    )


@pytest.fixture
def platform_settings(db):
    """Create default PlatformSettings singleton."""
    from apps.admin_panel.models import PlatformSettings
    return PlatformSettings.load()


@pytest.fixture
def cart(user):
    """Create a shopping cart for user."""
    from apps.commerce.models import Cart
    return Cart.objects.create(user=user.profile)


@pytest.fixture
def purchase(user, track, dj_user):
    """Create a completed purchase."""
    from apps.commerce.models import Purchase
    _, dj = dj_user
    return Purchase.objects.create(
        user=user.profile,
        content_id=track.id,
        content_type='track',
        original_price=track.price,
        price_paid=Decimal('105.00'),
        checkout_fee=Decimal('5.00'),
        commission=Decimal('15.00'),
        dj_revenue=Decimal('85.00'),
        dj_earnings=Decimal('85.00'),
        seller=dj,
        status='paid',
        is_completed=True,
    )
