"""
MixMint 2.0 — Unit Tests
Tests individual functions, model methods, and validators in isolation.
Covers: Functional Testing, Unit Testing categories.
"""
import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError


# ============================================================
# 1. VALIDATOR TESTS
# ============================================================

class TestEmailDomainValidator:
    """Tests for validate_email_domain() [Spec §13]."""

    def test_blocks_disposable_domains(self):
        from apps.accounts.validators import validate_email_domain
        blocked = [
            'user@mailinator.com', 'hacker@guerrillamail.com',
            'spam@yopmail.com', 'temp@tempmail.com',
            'x@throwaway.email', 'a@10minutemail.com',
        ]
        for email in blocked:
            with pytest.raises(ValidationError):
                validate_email_domain(email)

    def test_allows_legitimate_domains(self):
        from apps.accounts.validators import validate_email_domain
        valid = [
            'user@gmail.com', 'user@outlook.com',
            'user@company.co.in', 'dj@mixmint.site',
        ]
        for email in valid:
            validate_email_domain(email)  # Should not raise

    def test_rejects_missing_at_sign(self):
        from apps.accounts.validators import validate_email_domain
        with pytest.raises(ValidationError):
            validate_email_domain('noemailhere')

    def test_rejects_empty_string(self):
        from apps.accounts.validators import validate_email_domain
        with pytest.raises(ValidationError):
            validate_email_domain('')

    def test_rejects_none(self):
        from apps.accounts.validators import validate_email_domain
        with pytest.raises(ValidationError):
            validate_email_domain(None)


class TestStrongPasswordValidator:
    """Tests for validate_strong_password() [Spec §11]."""

    def test_rejects_short_password(self):
        from apps.accounts.validators import validate_strong_password
        with pytest.raises(ValidationError):
            validate_strong_password('Aa1!')

    def test_rejects_no_uppercase(self):
        from apps.accounts.validators import validate_strong_password
        with pytest.raises(ValidationError):
            validate_strong_password('alllowercase1!')

    def test_rejects_no_lowercase(self):
        from apps.accounts.validators import validate_strong_password
        with pytest.raises(ValidationError):
            validate_strong_password('ALLUPPERCASE1!')

    def test_rejects_no_digit(self):
        from apps.accounts.validators import validate_strong_password
        with pytest.raises(ValidationError):
            validate_strong_password('NoDigitsHere!')

    def test_rejects_no_special(self):
        from apps.accounts.validators import validate_strong_password
        with pytest.raises(ValidationError):
            validate_strong_password('NoSpecial123')

    def test_accepts_strong_password(self):
        from apps.accounts.validators import validate_strong_password
        validate_strong_password('StrongPass123!')  # Should not raise

    def test_accepts_various_specials(self):
        from apps.accounts.validators import validate_strong_password
        for p in ['Pass123@', 'Pass123#', 'Pass123$', 'Pass123%']:
            validate_strong_password(p)


# ============================================================
# 2. MODEL TESTS
# ============================================================

@pytest.mark.django_db
class TestUserModel:
    """Tests for custom User model."""

    def test_create_user(self):
        from apps.accounts.models import User
        u = User.objects.create_user(email='test@example.com', password='Test123!')
        assert u.email == 'test@example.com'
        assert u.check_password('Test123!')
        assert not u.is_staff
        assert not u.is_superuser

    def test_create_superuser(self):
        from apps.accounts.models import User
        u = User.objects.create_superuser(email='admin@test.com', password='Admin123!')
        assert u.is_staff
        assert u.is_superuser

    def test_email_is_unique(self):
        from apps.accounts.models import User
        from django.db import IntegrityError
        User.objects.create_user(email='dup@example.com', password='Pass123!')
        with pytest.raises(IntegrityError):
            User.objects.create_user(email='dup@example.com', password='Pass123!')

    def test_uuid_primary_key(self):
        from apps.accounts.models import User
        import uuid
        u = User.objects.create_user(email='uuid@example.com', password='Pass123!')
        assert isinstance(u.id, uuid.UUID)

    def test_create_user_without_email_fails(self):
        from apps.accounts.models import User
        with pytest.raises(ValueError):
            User.objects.create_user(email='', password='Pass123!')

    def test_profile_auto_created_via_signal(self):
        from apps.accounts.models import User
        u = User.objects.create_user(email='signal@example.com', password='Pass123!')
        assert hasattr(u, 'profile')
        assert u.profile is not None


@pytest.mark.django_db
class TestDJProfileModel:
    """Tests for DJProfile model methods."""

    def test_auto_slug_generation(self):
        from apps.accounts.models import User, DJProfile
        u = User.objects.create_user(email='slugtest@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(
            profile=u.profile,
            dj_name='DJ Awesome',
            status='approved',
        )
        assert dj.slug == 'dj-awesome'

    def test_duplicate_slug_generates_unique(self):
        from apps.accounts.models import User, DJProfile
        u1 = User.objects.create_user(email='dj1@example.com', password='Pass123!')
        u1.profile.role = 'dj'
        u1.profile.save(update_fields=['role'])
        DJProfile.objects.create(profile=u1.profile, dj_name='Same Name', status='approved')

        u2 = User.objects.create_user(email='dj2@example.com', password='Pass123!')
        u2.profile.role = 'dj'
        u2.profile.save(update_fields=['role'])
        dj2 = DJProfile.objects.create(profile=u2.profile, dj_name='Same Name', status='approved')
        assert dj2.slug == 'same-name-1'

    def test_soft_delete_moves_funds_to_escrow(self):
        from apps.accounts.models import User, DJProfile
        from apps.commerce.models import DJWallet
        u = User.objects.create_user(email='softdel@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=u.profile, dj_name='Delete Me', slug='delete-me', status='approved')
        wallet, _ = DJWallet.objects.get_or_create(dj=dj)
        wallet.available_for_payout = Decimal('500.00')
        wallet.save()

        dj.soft_delete()

        wallet.refresh_from_db()
        assert wallet.available_for_payout == Decimal('0.00')
        assert wallet.escrow_amount == Decimal('500.00')
        assert dj.is_deleted
        assert dj.status == 'rejected'

    def test_str_returns_dj_name(self):
        from apps.accounts.models import User, DJProfile
        u = User.objects.create_user(email='str@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        dj = DJProfile.objects.create(profile=u.profile, dj_name='DJ String', slug='dj-string', status='approved')
        assert str(dj) == 'DJ String'


@pytest.mark.django_db
class TestTrackModel:
    """Tests for Track model validation."""

    def _make_dj(self):
        from apps.accounts.models import User, DJProfile
        u = User.objects.create_user(email='trackdj@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.save(update_fields=['role'])
        return DJProfile.objects.create(profile=u.profile, dj_name='Track DJ', slug='track-dj', status='approved')

    def test_free_track_price_zero(self):
        from apps.tracks.models import Track
        dj = self._make_dj()
        t = Track(dj=dj, title='Free', price=Decimal('0.00'), file_key='t.wav',
                  preview_type='youtube', youtube_url='https://youtube.com/watch?v=x')
        t.full_clean()  # Should not raise

    def test_paid_track_below_minimum_rejected(self):
        from apps.tracks.models import Track
        dj = self._make_dj()
        t = Track(dj=dj, title='Cheap', price=Decimal('10.00'), file_key='t.wav',
                  preview_type='youtube', youtube_url='https://youtube.com/watch?v=x')
        with pytest.raises(ValidationError):
            t.full_clean()

    def test_paid_track_at_minimum_accepted(self):
        from apps.tracks.models import Track
        dj = self._make_dj()
        t = Track(dj=dj, title='Min Price', price=Decimal('19.00'), file_key='t.wav',
                  preview_type='youtube', youtube_url='https://youtube.com/watch?v=x')
        t.full_clean()  # Should not raise

    def test_missing_preview_type_rejected(self):
        from apps.tracks.models import Track
        dj = self._make_dj()
        t = Track(dj=dj, title='No Preview', price=Decimal('50.00'), file_key='t.wav')
        with pytest.raises(ValidationError):
            t.full_clean()

    def test_youtube_preview_without_url_rejected(self):
        from apps.tracks.models import Track
        dj = self._make_dj()
        t = Track(dj=dj, title='No URL', price=Decimal('50.00'), file_key='t.wav',
                  preview_type='youtube')
        with pytest.raises(ValidationError):
            t.full_clean()


@pytest.mark.django_db
class TestCartDiscountTiers:
    """Tests for Cart tiered discount calculations [Phase 3 Feature 3]."""

    def _create_cart_with_items(self, count, price_paise=10000):
        from apps.accounts.models import User
        from apps.commerce.models import Cart, CartItem
        u = User.objects.create_user(email=f'cart{count}@example.com', password='Pass123!')
        cart = Cart.objects.create(user=u.profile)
        for i in range(count):
            CartItem.objects.create(
                cart=cart, content_type='track', content_id=i + 1, price=price_paise
            )
        return cart

    def test_no_discount_under_3_items(self):
        cart = self._create_cart_with_items(2)
        assert cart.discount_percentage == 0

    def test_5_percent_at_3_items(self):
        cart = self._create_cart_with_items(3)
        assert cart.discount_percentage == 5

    def test_10_percent_at_5_items(self):
        cart = self._create_cart_with_items(5)
        assert cart.discount_percentage == 10

    def test_20_percent_at_10_items(self):
        cart = self._create_cart_with_items(10)
        assert cart.discount_percentage == 20

    def test_30_percent_at_15_items(self):
        cart = self._create_cart_with_items(15)
        assert cart.discount_percentage == 30

    def test_next_tier_info_below_3(self):
        cart = self._create_cart_with_items(1)
        info = cart.next_tier_info
        assert info['needed'] == 2
        assert info['discount'] == 5


# ============================================================
# 3. REVENUE ENGINE TESTS
# ============================================================

@pytest.mark.django_db
class TestRevenueEngine:
    """Tests for calculate_revenue_split() [Spec P3 §1]."""

    def _setup_dj(self, is_pro=False):
        from apps.accounts.models import User, DJProfile
        from apps.admin_panel.models import PlatformSettings
        PlatformSettings.load()  # Ensure settings exist
        u = User.objects.create_user(email=f'rev{"pro" if is_pro else "std"}@example.com', password='Pass123!')
        u.profile.role = 'dj'
        u.profile.is_pro_dj = is_pro
        u.profile.save(update_fields=['role', 'is_pro_dj'])
        dj = DJProfile.objects.create(profile=u.profile, dj_name='Rev DJ', slug=f'rev-dj-{"pro" if is_pro else "std"}', status='approved')
        return dj

    def test_standard_15_percent_commission(self):
        from apps.commerce.revenue_engine import calculate_revenue_split
        dj = self._setup_dj(is_pro=False)
        split = calculate_revenue_split(Decimal('100.00'), dj)
        assert split['commission'] == Decimal('15.00')
        assert split['dj_earnings'] == Decimal('85.00')

    def test_pro_dj_8_percent_commission(self):
        from apps.commerce.revenue_engine import calculate_revenue_split
        dj = self._setup_dj(is_pro=True)
        split = calculate_revenue_split(Decimal('100.00'), dj)
        assert split['commission'] == Decimal('8.00')
        assert split['dj_earnings'] == Decimal('92.00')

    def test_insurance_fee_added_when_requested(self):
        from apps.commerce.revenue_engine import calculate_revenue_split
        dj = self._setup_dj()
        split = calculate_revenue_split(Decimal('100.00'), dj, with_insurance=True)
        assert split['insurance_fee'] == Decimal('15.00')

    def test_no_insurance_by_default(self):
        from apps.commerce.revenue_engine import calculate_revenue_split
        dj = self._setup_dj()
        split = calculate_revenue_split(Decimal('100.00'), dj)
        assert split['insurance_fee'] == Decimal('0.00')
