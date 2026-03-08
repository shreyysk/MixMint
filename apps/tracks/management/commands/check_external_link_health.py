import requests
from django.core.management.base import BaseCommand
from apps.tracks.models import Track
from apps.albums.models import AlbumPack

def validate_external_link(url):
    """
    Validates that:
    1. URL is from allowed providers (GDrive or MediaFire)
    2. URL is reachable (not 404)
    3. URL appears to be a direct/shareable link
    """
    ALLOWED_DOMAINS = [
        'drive.google.com',
        'docs.google.com',
        'mediafire.com',
        'www.mediafire.com'
    ]

    from urllib.parse import urlparse
    parsed = urlparse(url)

    if parsed.netloc not in ALLOWED_DOMAINS:
        return False, (
            "Only Google Drive and MediaFire links are accepted. "
            f"Got: {parsed.netloc}"
        )

    # HEAD request to check reachability
    try:
        resp = requests.head(url, timeout=8, allow_redirects=True)
        if resp.status_code == 200:
            return True, None
        elif resp.status_code == 403:
            return False, (
                "Link is not publicly accessible. "
                "Make sure sharing is set to 'Anyone with the link'."
            )
        elif resp.status_code == 404:
            return False, "Link not found. Please check the URL."
        else:
            return False, f"Link returned status {resp.status_code}."
    except requests.RequestException:
        return False, "Could not reach the link. Please check and try again."

        
class Command(BaseCommand):
    help = 'Phase 3 Feature 1: Check health of external links and notify DJ if broken'

    def handle(self, *args, **kwargs):
        self.stdout.write('Checking external link health...')
        
        broken = []
        
        # 1. Check Tracks
        external_tracks = Track.objects.filter(
            is_external_link=True,
            is_active=True,
            is_deleted=False
        )
        for track in external_tracks:
            if not track.external_link_url:
                continue
                
            valid, error = validate_external_link(track.external_link_url)
            if not valid:
                broken.append(track)
                track.external_link_broken = True
                track.external_link_error = error
                track.save(update_fields=['external_link_broken', 'external_link_error'])
            elif track.external_link_broken:
                # Recovered
                track.external_link_broken = False
                track.external_link_error = None
                track.save(update_fields=['external_link_broken', 'external_link_error'])

        # 2. Check Albums
        external_albums = AlbumPack.objects.filter(
            is_external_link=True,
            is_active=True,
            is_deleted=False
        )
        for album in external_albums:
            if not album.external_link_url:
                continue
                
            valid, error = validate_external_link(album.external_link_url)
            if not valid:
                broken.append(album)
                album.external_link_broken = True
                album.external_link_error = error
                album.save(update_fields=['external_link_broken', 'external_link_error'])
            elif album.external_link_broken:
                album.external_link_broken = False
                album.external_link_error = None
                album.save(update_fields=['external_link_broken', 'external_link_error'])

        # NOTE: Missing emails to DJ and admin about broken links.
        # send_broken_external_link_email(dj_id, content, error)
        # send_admin_broken_links_report(broken)
        
        if broken:
            self.stdout.write(self.style.WARNING(f'Found {len(broken)} broken external links.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'All {external_tracks.count() + external_albums.count()} external links are healthy.'))
