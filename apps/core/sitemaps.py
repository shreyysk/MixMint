from django.contrib.sitemaps import Sitemap

from apps.accounts.models import DJProfile
from apps.albums.models import AlbumPack
from apps.tracks.models import Track


class TrackSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    limit = 5000

    def items(self):
        return Track.objects.filter(is_active=True, is_deleted=False, dj__profile__store_paused=False).order_by("-id")

    def lastmod(self, obj):
        return obj.converted_at or obj.created_at

    def location(self, obj):
        return f"/tracks/{obj.id}/"


class AlbumSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return AlbumPack.objects.filter(is_active=True, is_deleted=False, dj__profile__store_paused=False).order_by(
            "-id"
        )

    def lastmod(self, obj):
        return obj.created_at

    def location(self, obj):
        return f"/albums/{obj.id}/"


class DJStorefrontSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return DJProfile.objects.filter(status="approved", is_deleted=False).order_by("-id")

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f"/dj/{obj.slug}/"


class StaticSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return ["/", "/explore/", "/djs/", "/legal/about/", "/legal/faq/", "/contact/"]

    def location(self, item):
        return item


SITEMAPS = {
    "static": StaticSitemap,
    "tracks": TrackSitemap,
    "albums": AlbumSitemap,
    "dj_storefronts": DJStorefrontSitemap,
}
