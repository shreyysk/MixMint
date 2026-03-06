from django.test import TestCase
from decimal import Decimal
from apps.accounts.models import User, Profile, DJProfile
from apps.tracks.models import Track, TrackCollaborator
from apps.commerce.revenue_engine import calculate_revenue_split

class RevenueEngineTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='password')
        # Profile is auto-created via accounts.signals
        self.profile = self.user.profile
        self.profile.full_name = 'Test User'
        self.profile.save(update_fields=['full_name'])
        
        self.dj_user = User.objects.create_user(email='dj@example.com', password='password')
        self.dj_profile = self.dj_user.profile
        self.dj_profile.full_name = 'Test DJ'
        self.dj_profile.role = 'dj'
        self.dj_profile.save(update_fields=['full_name', 'role'])
        self.dj = DJProfile.objects.create(profile=self.dj_profile, dj_name='Test DJ', slug='test-dj', status='approved')
        
        self.track = Track.objects.create(
            dj=self.dj,
            title='Test Track',
            price=Decimal('100.00'),
            preview_type='youtube',
            youtube_url='https://youtube.com/watch?v=123'
        )

    def test_standard_commission(self):
        """Test standard 15% commission calculation."""
        split = calculate_revenue_split(self.track.price, self.dj)
        self.assertEqual(split['commission'], Decimal('15.00'))
        self.assertEqual(split['dj_earnings'], Decimal('85.00'))
        self.assertEqual(split['total_buyer_pays'], Decimal('105.00')) # 100 + 5 fee

    def test_pro_dj_commission(self):
        """Test Pro DJ 8% commission calculation."""
        # Pro flag lives on Profile, not DJProfile
        self.dj_profile.is_pro_dj = True
        self.dj_profile.save(update_fields=['is_pro_dj'])
        
        split = calculate_revenue_split(self.track.price, self.dj)
        self.assertEqual(split['commission'], Decimal('8.00'))
        self.assertEqual(split['dj_earnings'], Decimal('92.00'))

    def test_collaborator_split(self):
        """Test revenue split among collaborators."""
        collab_user = User.objects.create_user(email='collab@example.com', password='password')
        collab_profile = collab_user.profile
        collab_profile.full_name = 'Collab DJ'
        collab_profile.role = 'dj'
        collab_profile.save(update_fields=['full_name', 'role'])
        collab_dj = DJProfile.objects.create(profile=collab_profile, dj_name='Collab DJ', slug='collab-dj', status='approved')
        
        # 50/50 split
        TrackCollaborator.objects.create(track=self.track, dj=self.dj, revenue_percentage=Decimal('50.00'))
        TrackCollaborator.objects.create(track=self.track, dj=collab_dj, revenue_percentage=Decimal('50.00'))
        
        split = calculate_revenue_split(self.track.price, self.dj, content=self.track, content_type='track')
        
        # 85.00 / 2 = 42.50 each
        self.assertEqual(len(split['collaborator_splits']), 2)
        self.assertEqual(split['collaborator_splits'][0]['amount'], Decimal('42.50'))
        self.assertEqual(split['collaborator_splits'][1]['amount'], Decimal('42.50'))
