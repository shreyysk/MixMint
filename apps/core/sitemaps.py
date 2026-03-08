from django.contrib.sitemaps import Sitemap
from apps.tracks.models import Track
from apps.accounts.models import DJProfile

class TrackSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Track.objects.filter(
            is_active=True,
            is_deleted=False
        )

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f'/tracks/{obj.id}'


class DJStorefrontSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.9

    def items(self):
        return DJProfile.objects.filter(
            status='approved'
        )

    def location(self, obj):
        return f'/dj/{obj.dj_name}'

SITEMAPS = {
    'tracks': TrackSitemap,
    'dj_storefronts': DJStorefrontSitemap,
}
