"""Pre-warm the shared R2 cache for external-source tracks.

Why: on serverless hosts (Vercel, 300s limit) a first buyer must never pay a
slow Drive fetch inside their request. This command fetches a small bounded
batch of not-yet-cached tracks into R2 ahead of time. Trigger it on a timer
(e.g. cron-job.org every 30 min hitting /cron/warm-cache/).

Bounds (serverless-safe): max 3 tracks per run, skips files over
WARM_MAX_MB (probe only reads headers). Never re-warms fresh cache.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

WARM_BATCH = 3
WARM_MAX_MB = 150


class Command(BaseCommand):
    help = "Pre-cache external-source tracks to shared R2 (bounded, serverless-safe)"

    def handle(self, *args, **kwargs):
        from apps.downloads import external_cache
        from apps.downloads.source_fetch import fetch_from_source, probe_source
        from apps.tracks.models import Track
        import os

        if not external_cache.is_configured():
            self.stdout.write("R2 not configured — nothing to warm.")
            return

        warmed, skipped = 0, 0
        tracks = Track.objects.filter(is_active=True, is_deleted=False).exclude(source_url="").order_by("id")[:50]
        tracks = [t for t in tracks if t.source_url or t.external_link_url]
        for track in tracks:
            if warmed >= WARM_BATCH:
                break
            source_url = track.source_url or track.external_link_url
            if external_cache.get_fresh_key(track.id, source_url):
                continue  # already warm
            try:
                ok, info = probe_source(source_url)
            except Exception as exc:
                self.stdout.write(f"Track {track.id}: probe crashed ({exc}). Skipping.")
                skipped += 1
                continue
            if not ok:
                self.stdout.write(f"Track {track.id}: not reachable. Skipping.")
                skipped += 1
                continue
            try:
                local = fetch_from_source(
                    source_url, track.source_type or "other", f"warm_{track.id}_{timezone.now():%Y%m%d%H%M}"
                )
                if os.path.getsize(local) > WARM_MAX_MB * 1024 * 1024:
                    os.remove(local)
                    self.stdout.write(f"Track {track.id}: too big for warm batch. Skipping.")
                    skipped += 1
                    continue
                external_cache.upload_file(local, track.id, source_url)
                try:
                    os.remove(local)
                except OSError:
                    pass
                warmed += 1
                self.stdout.write(f"Track {track.id}: warmed.")
            except Exception as exc:
                self.stdout.write(f"Track {track.id}: warm failed ({exc}). Skipping.")
                skipped += 1
        self.stdout.write(self.style.SUCCESS(f"Warmed {warmed}, skipped {skipped}."))
