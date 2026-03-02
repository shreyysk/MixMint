from django.test import TestCase
from decimal import Decimal
from apps.accounts.models import User, Profile, DJProfile
from apps.tracks.models import Track, TrackCollaborator
from apps.commerce.revenue_engine import calculate_revenue_split

class RevenueEngineTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='password')
        self.profile = Profile.objects.create(user=self.user, full_name='Test User')
        
        self.dj_user = User.objects.create_user(email='dj@example.com', password='password', role='dj')
        self.dj_profile = Profile.objects.create(user=self.dj_user, full_name='Test DJ')
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
        self.dj.is_pro_dj = True
        self.dj.save()
        
        # Note: settings.PRO_DJ_COMMISSION_RATE needs to be 0.08 in test env or mocked
        split = calculate_revenue_split(self.track.price, self.dj)
        # Assuming PRO_DJ_COMMISSION_RATE is 0.08
        self.assertEqual(split['commission'], Decimal('8.00'))
        self.assertEqual(split['dj_earnings'], Decimal('92.00'))

    def test_collaborator_split(self):
        """Test revenue split among collaborators."""
        collab_user = User.objects.create_user(email='collab@example.com', password='password', role='dj')
        collab_profile = Profile.objects.create(user=collab_user, full_name='Collab DJ')
        collab_dj = DJProfile.objects.create(profile=collab_profile, dj_name='Collab DJ', slug='collab-dj', status='approved')
        
        # 50/50 split
        TrackCollaborator.objects.create(track=self.track, dj=self.dj, revenue_percentage=Decimal('50.00'))
        TrackCollaborator.objects.create(track=self.track, dj=collab_dj, revenue_percentage=Decimal('50.00'))
        
        split = calculate_revenue_split(self.track.price, self.dj, content=self.track, content_type='track')
        
        # 85.00 / 2 = 42.50 each
        self.assertEqual(len(split['collaborator_splits']), 2)
        self.assertEqual(split['collaborator_splits'][0]['amount'], Decimal('42.50'))
        self.assertEqual(split['collaborator_splits'][1]['amount'], Decimal('42.50'))
