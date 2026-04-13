from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User, Profile


class AdminViewTests(TestCase):
    def setUp(self):
        # Create a superuser (Profile auto-created via signal)
        self.admin_user = User.objects.create_superuser(
            email='admin@mixmint.site',
            password='password123'
        )
        self.admin_user.profile.role = 'admin'
        self.admin_user.profile.save(update_fields=['role'])

        # Create a regular user (Profile auto-created via signal)
        self.regular_user = User.objects.create_user(
            email='user@mixmint.site',
            password='password123'
        )

        self.client = Client()

    def test_admin_dashboard_access(self):
        """Test that only admins can access the dashboard."""
        url = reverse('admin_dashboard')

        # Unauthorized access
        response = self.client.get(url)
        self.assertIn(response.status_code, [302, 403])

        # Regular user access
        self.client.login(email='user@mixmint.site', password='password123')
        response = self.client.get(url)
        self.assertIn(response.status_code, [302, 403])
        self.client.logout()

        # Admin access
        self.client.login(email='admin@mixmint.site', password='password123')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_offers_pricing_access(self):
        """Test admin access to offers & pricing."""
        url = reverse('admin_offers_pricing')
        self.client.login(email='admin@mixmint.site', password='password123')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_investor_report_access(self):
        """Test admin access to investor report."""
        url = reverse('admin_investor_report')
        self.client.login(email='admin@mixmint.site', password='password123')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_health_dashboard_access(self):
        """Test admin access to health dashboard."""
        url = reverse('admin_health')
        self.client.login(email='admin@mixmint.site', password='password123')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
