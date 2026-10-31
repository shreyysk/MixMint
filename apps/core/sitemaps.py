from django.contrib.sitemaps import Sitemap

from apps.accounts.models import DJProfile
from apps.albums.models import AlbumPack
from apps.tracks.models import Track


class TrackSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    limit = 5000

    def items(self):
        return Track.objects.filter(is_active=True, is_deleted=False, dj__status="approved", dj__profile__store_paused=False).order_by("-id")

    def lastmod(self, obj):
        return obj.converted_at or obj.created_at

    def location(self, obj):
        return f"/tracks/{obj.id}/"


class AlbumSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return AlbumPack.objects.filter(is_active=True, is_deleted=False, dj__status="approved", dj__profile__store_paused=False).order_by(
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
        return ["/", "/releases/", "/new-releases/", "/sample-packs/", "/bundles/", "/drops/", "/djs/", "/sell/", "/pro/",
                "/legal/tutorials/", "/legal/how-it-works/", "/legal/sell-guide/",
                "/legal/about/", "/legal/faq/", "/contact/"]

    def location(self, item):
        return item




class GenreSitemap(Sitemap):
    """/genre/<slug>/ landing pages for every genre that has at least one live track."""

    changefreq = "daily"
    priority = 0.8

    def items(self):
        from apps.core.catalog_views import genre_slug
        from apps.core.genres import GENRES

        live = set(Track.objects.filter(is_active=True, is_deleted=False, dj__status="approved", dj__profile__store_paused=False)
                   .exclude(genre__isnull=True).values_list("genre", flat=True).distinct())
        return [genre_slug(g) for g in GENRES if g in live and g != "Other"]

    def location(self, slug):
        return f"/genre/{slug}/"


SITEMAPS = {
    "static": StaticSitemap,
    "tracks": TrackSitemap,
    "albums": AlbumSitemap,
    "dj_storefronts": DJStorefrontSitemap,
    "genres": GenreSitemap,
}
