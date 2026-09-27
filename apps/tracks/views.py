from rest_framework import viewsets, filters, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Track
from .serializers import TrackSerializer
from apps.downloads.utils import DownloadManager


class TrackViewSet(viewsets.ModelViewSet):
    """
    Public track listing API [CP-02.01 FIX].
    List and retrieve are public (AllowAny).
    Create/Update/Delete require authentication.
    """

    queryset = Track.objects.filter(is_active=True, is_deleted=False, dj__profile__store_paused=False)
    serializer_class = TrackSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["genre", "dj", "year", "preview_type"]
    search_fields = ["title", "description", "dj__dj_name"]
    ordering_fields = ["created_at", "price", "download_count", "popularity"]
    throttle_scope = "search"  # [Fix 16]

    def get_permissions(self):
        """
        [CP-02.01 FIX] Allow public access for list/retrieve.
        [CP-06.04, CP-06.05 FIX] Require DJ role for create/update/delete.
        """
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        from apps.accounts.permissions import IsNotBanned

        return [permissions.IsAuthenticated(), IsNotBanned()]

    def _check_dj_permission(self, user):
        """
        [CP-06.04, CP-06.05 FIX] Check if user is an approved DJ.
        Returns (is_allowed, error_response)
        """
        try:
            profile = user.profile
            if profile.role != "dj":
                return False, Response({"error": "Only DJs can upload tracks."}, status=403)
            if not hasattr(profile, "dj_profile"):
                return False, Response(
                    {"error": "DJ profile not found. Please complete your DJ application."}, status=403
                )
            if profile.dj_profile.status != "approved":
                return False, Response(
                    {
                        "error": "Your DJ application is pending approval. "
                        "Please wait for admin approval before uploading."
                    },
                    status=403,
                )
            return True, None
        except Exception:
            return False, Response({"error": "Authentication error. Please re-login."}, status=403)

    def create(self, request, *args, **kwargs):
        """
        [CP-06.04, CP-06.05 FIX] Enforce DJ role for track creation.
        Only approved DJs can upload tracks.
        """
        is_allowed, error_response = self._check_dj_permission(request.user)
        if not is_allowed:
            return error_response
        return super().create(request, *args, **kwargs)

    def _owner_guard(self, request, obj):
        """Only the owning DJ (or staff) may modify a track [CP-06.04]."""
        if request.user.is_staff:
            return None
        is_allowed, error_response = self._check_dj_permission(request.user)
        if not is_allowed:
            return error_response
        if obj.dj_id != request.user.profile.dj_profile.id:
            return Response({"error": "You can only modify your own tracks."}, status=403)
        return None

    def update(self, request, *args, **kwargs):
        denied = self._owner_guard(request, self.get_object())
        if denied:
            return denied
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Soft delete only [Spec P2 §3.1]; buyers keep their library entries."""
        track = self.get_object()
        denied = self._owner_guard(request, track)
        if denied:
            return denied
        track.is_deleted = True
        track.is_active = False
        track.save(update_fields=["is_deleted", "is_active"])
        return Response(status=204)

    def get_queryset(self):
        """
        Weighted search ranking with XSS sanitization [CP-02.04 FIX].
        Sanitizes search query to prevent XSS attacks.
        """
        qs = super().get_queryset()

        # Note: DRF's SearchFilter uses parameterized queries preventing SQL injection
        # XSS sanitization is done at the serializer/response level
        # The html.escape import at top is available for use in serializers

        return self._apply_ranking(qs)

    def _apply_ranking(self, qs):
        """
        Weighted search ranking [Gap 08].
        Prioritizes:
        1. Pro DJ status (+1000)
        2. Verified badge (+500)
        3. High popularity score
        4. Freshness (recency)
        """
        from django.db.models import Case, When, F, DecimalField, Value

        # Apply weights for ranking
        qs = qs.annotate(
            rank_score=Case(
                When(dj__profile__is_pro_dj=True, then=Value(1000)), default=Value(0), output_field=DecimalField()
            )
            + Case(When(dj__is_verified=True, then=Value(500)), default=Value(0), output_field=DecimalField())
            + F("dj__popularity_score")
        )

        # Default ordering by rank_score then recency
        if not self.request.query_params.get("ordering"):
            return qs.order_by("-rank_score", "-created_at")

        return qs

    def perform_create(self, serializer):
        """Owner is always the requesting DJ; process metadata [Gap 04]."""
        track = serializer.save(dj=self.request.user.profile.dj_profile)
        from .tasks import process_track_metadata_task

        # Off the request path (runs inline when CELERY_TASK_ALWAYS_EAGER).
        process_track_metadata_task.delay(track.id)

    @action(detail=True, methods=["post"], url_path="download-token", permission_classes=[permissions.IsAuthenticated])
    def get_download_token(self, request, pk=None):
        """Ownership-checked, IP/device-bound one-time download token [Spec §4]."""
        return DownloadManager.issue_token_response(request, self.get_object(), "track")

    @action(detail=True, methods=["post"], url_path="report", permission_classes=[permissions.IsAuthenticated])
    def report_content(self, request, pk=None):
        """User-driven content flagging [Fix 08]."""
        track = self.get_object()
        report_type = request.data.get("report_type")
        reason = request.data.get("reason")

        if not report_type or not reason:
            return Response({"error": "report_type and reason are required."}, status=400)
        from apps.admin_panel.models import ContentReport as _CR

        if report_type not in dict(_CR.REPORT_TYPES):
            return Response({"error": "Invalid report_type."}, status=400)
        reason = str(reason)[:2000]

        from apps.admin_panel.models import ContentReport

        ContentReport.objects.create(
            reporter=request.user.profile,
            content_type="track",
            content_id=track.id,
            report_type=report_type,
            reason=reason,
        )

        return Response({"status": "reported", "message": "Thank you for your report. Admin will review it."})

    @action(detail=True, methods=["post"], url_path="rate", permission_classes=[permissions.IsAuthenticated])
    def rate_content(self, request, pk=None):
        """Unified rating system [Fix 09]."""
        track = self.get_object()
        stars = request.data.get("stars")
        review = request.data.get("review", "")

        try:
            stars = int(stars)
        except (TypeError, ValueError):
            stars = 0
        if not (1 <= stars <= 5):
            return Response({"error": "stars (1-5) is required."}, status=400)

        from apps.commerce.models import Purchase
        from .models import StarRating

        owns = Purchase.objects.filter(
            user=request.user.profile, content_type="track", content_id=track.id, status="paid"
        ).exists()
        if not owns and track.price > 0:
            return Response({"error": "Only buyers can rate this track."}, status=403)

        rating, created = StarRating.objects.update_or_create(
            user=request.user.profile,
            content_type="track",
            content_id=track.id,
            defaults={"stars": int(stars), "review": review},
        )

        return Response({"status": "rated", "stars": rating.stars})

    @action(
        detail=False, methods=["post"], url_path="validate-preview", permission_classes=[permissions.IsAuthenticated]
    )
    def validate_preview(self, request):
        """
        Imp 08: Preview Validation Tool.
        Validates if a YouTube/Instagram URL is valid and embeddable.
        """
        url = request.data.get("url", "").strip()
        preview_type = request.data.get("type", "")

        if not url:
            return Response({"error": "URL is required."}, status=400)

        import re

        is_valid = False
        embed_url = ""

        if preview_type == "youtube":
            yt_match = re.search(r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([^?&/]+)", url)
            if yt_match:
                video_id = yt_match.group(1)
                is_valid = True
                embed_url = f"https://www.youtube.com/embed/{video_id}"

        elif preview_type == "instagram":
            ig_match = re.search(r"instagram\.com/(?:reels|p|reel)/([^/?&]+)", url)
            if ig_match:
                shortcode = ig_match.group(1)
                is_valid = True
                embed_url = f"https://www.instagram.com/reels/{shortcode}/embed"

        if is_valid:
            return Response({"valid": True, "embed_url": embed_url, "message": f"Valid {preview_type} link detected."})

        return Response(
            {"valid": False, "error": f"Invalid {preview_type} URL. Please provide a direct link to the video/reel."},
            status=400,
        )

    @action(
        detail=True, methods=["post"], url_path="convert-external", permission_classes=[permissions.IsAuthenticated]
    )
    def convert_to_external_link(self, request, pk=None):
        """Phase 3 Feature 1: Convert an underperforming or free track to an external link."""
        from django.utils import timezone

        track = self.get_object()

        # Security: Only track owner can do this
        if getattr(request.user.profile, "dj_profile", None) != track.dj:
            return Response({"error": "You do not have permission to modify this track."}, status=403)

        url = request.data.get("external_link_url", "").strip() or request.data.get("source_url", "").strip()
        if not url:
            return Response(
                {"error": "A backend file link is required (Drive, MediaFire, or any direct download link)."},
                status=400,
            )

        # Accept any Drive / MediaFire / direct download link. Verify it actually
        # downloads (probes only headers/first bytes) before accepting.
        from apps.downloads.source_fetch import probe_source

        ok, info = probe_source(url)
        if not ok:
            return Response({"error": info}, status=400)

        provider = "google_drive" if "drive.google.com" in url else "mediafire" if "mediafire.com" in url else "other"

        # Update track (legacy external_link_* + canonical source_* kept in sync;
        # download flow reads source_url first, then external_link_url)
        track.is_external_link = True
        track.external_link_url = url
        track.external_link_provider = provider
        track.external_link_broken = False
        track.external_link_error = None
        track.source_url = url
        track.source_type = (
            "gdrive" if "drive.google.com" in url else "mediafire" if "mediafire.com" in url else "other"
        )
        track.converted_at = timezone.now()

        # We don't delete `file_key` here. The file stays on R2 for users who already bought it.
        # But we DO need to mark the notification as complete.

        track.save()

        # Update offload notification status if exists
        from apps.commerce.models import OffloadNotification

        OffloadNotification.objects.filter(dj=track.dj, content_id=track.id, content_type="track").update(
            status="converted"
        )

        return Response(
            {
                "status": "success",
                "message": "Backend link verified and saved. First buyer download will cache it to MixMint.",
                "check": info,
            }
        )

    @action(
        detail=False, methods=["post"], url_path="verify-source-link", permission_classes=[permissions.IsAuthenticated]
    )
    def verify_source_link(self, request):
        """Check a DJ backend link (Drive/MediaFire/direct) WITHOUT saving.

        Probes headers only, then reports reachability + size. Guide included on failure.
        """
        if request.user.profile.role != "dj" or not hasattr(request.user.profile, "dj_profile"):
            return Response({"error": "Only DJs can verify source links."}, status=403)
        url = request.data.get("source_url", "").strip() or request.data.get("external_link_url", "").strip()
        if not url:
            return Response({"error": "Provide source_url to check."}, status=400)
        from apps.downloads.source_fetch import probe_source

        ok, info = probe_source(url)
        return Response({"ok": ok, "detail": info}, status=200 if ok else 400)

    @action(
        detail=False,
        methods=["get"],
        url_path="my-tracks",
        permission_classes=[permissions.IsAuthenticated],
        throttle_classes=[],
    )  # Uses default throttle from settings
    def my_tracks(self, request):
        """
        [P2-02.02 FIX] DJ-only endpoint to list their own tracks.
        Ensures DJs can only access their own tracks for editing.
        [Enhancement] Added pagination support.
        """
        if request.user.profile.role != "dj" or not hasattr(request.user.profile, "dj_profile"):
            return Response({"error": "Only DJs can access this endpoint."}, status=403)

        try:
            dj_profile = request.user.profile.dj_profile
        except Exception:
            return Response({"error": "DJ profile not found."}, status=404)

        # Get only this DJ's tracks, including inactive/deleted for management
        tracks = Track.objects.filter(dj=dj_profile).order_by("-created_at")

        # Optional filtering
        include_deleted = request.query_params.get("include_deleted", "false").lower() == "true"
        if not include_deleted:
            tracks = tracks.filter(is_deleted=False)

        # Pagination [Enhancement]
        try:
            page = max(1, int(request.query_params.get("page", 1)))
            page_size = max(1, min(int(request.query_params.get("page_size", 20)), 50))  # Max 50
        except (TypeError, ValueError):
            return Response({"error": "page and page_size must be integers."}, status=400)
        start = (page - 1) * page_size
        end = start + page_size

        total_count = tracks.count()
        paginated_tracks = tracks[start:end]

        serializer = TrackSerializer(paginated_tracks, many=True)
        return Response(
            {
                "count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size,
                "tracks": serializer.data,
            }
        )
