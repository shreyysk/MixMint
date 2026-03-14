from rest_framework import viewsets, filters, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Track
from .serializers import TrackSerializer
from apps.downloads.utils import DownloadManager
from apps.commerce.models import Purchase
from .utils import process_track_metadata


class TrackViewSet(viewsets.ModelViewSet):
    queryset = Track.objects.filter(is_active=True, is_deleted=False, dj__profile__store_paused=False)
    serializer_class = TrackSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['genre', 'dj', 'year', 'preview_type']
    search_fields = ['title', 'description', 'dj__dj_name']
    ordering_fields = ['created_at', 'price', 'download_count', 'popularity']
    throttle_scope = 'search'  # [Fix 16]

    def get_queryset(self):
        """
        Weighted search ranking [Gap 08].
        Prioritizes:
        1. Pro DJ status (+1000)
        2. Verified badge (+500)
        3. High popularity score
        4. Freshness (recency)
        """
        from django.db.models import Case, When, F, DecimalField, Value
        
        qs = super().get_queryset()
        
        # Apply weights for ranking
        qs = qs.annotate(
            rank_score=Case(
                When(dj__profile__is_pro_dj=True, then=Value(1000)),
                default=Value(0),
                output_field=DecimalField()
            ) + Case(
                When(dj__is_verified=True, then=Value(500)),
                default=Value(0),
                output_field=DecimalField()
            ) + F('dj__popularity_score')
        )
        
        # Default ordering by rank_score then recency
        if not self.request.query_params.get('ordering'):
            return qs.order_by('-rank_score', '-created_at')
            
        return qs

    def perform_create(self, serializer):
        """Process track metadata upon upload [Gap 04]."""
        track = serializer.save()
        process_track_metadata(track)

    @action(detail=True, methods=['post'], url_path='download-token',
            permission_classes=[permissions.IsAuthenticated])
    def get_download_token(self, request, pk=None):
        """
        Generate a secure download token.
        Ownership-based access only. 3 attempts per IP. Device fingerprint bound.
        [Spec §4]
        """
        track = self.get_object()
        profile = request.user.profile
        client_ip = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT')
        device_hash = request.data.get('device_hash') or request.META.get('HTTP_X_DEVICE_HASH')

        # 0. BanList check [Spec §4.6]
        is_banned, ban_msg = DownloadManager.check_ban_list(client_ip, device_hash)
        if is_banned:
            return Response({'error': ban_msg}, status=403)

        # 1. Ownership + single-download lock enforcement [Spec §2.2, §4.3]
        purchase = Purchase.objects.filter(
            user=profile,
            content_id=track.id,
            content_type='track',
            is_revoked=False,
            is_redownload=False,
        ).order_by('-created_at').first()

        if not purchase and track.price > 0:
            return Response({'error': 'You must purchase this track first.', 'price': str(track.price)}, status=403)

        access_source = 'purchase'
        if purchase and purchase.download_completed:
            # Insurance allows free re-downloads [Spec §4.3]
            if hasattr(purchase, 'insurance') and purchase.insurance.status == 'active':
                access_source = 'insurance'
            else:
                eligible, msg = DownloadManager.check_redownload_eligibility(profile, track.id, 'track')
                if eligible:
                    return Response({
                        'error': 'Re-download requires payment.',
                        'redownload_available': True,
                        'redownload_price': str(track.price * 0.5),
                        'message': msg,
                    }, status=403)
                return Response({'error': msg}, status=403)

        # 2. Check IP attempt limit [Spec §4.2: 3 per IP]
        allowed, msg, remaining = DownloadManager.check_ip_attempts(client_ip, track.id, 'track')
        if not allowed:
            eligible, redownload_msg = DownloadManager.check_redownload_eligibility(
                profile, track.id, 'track'
            )
            if eligible:
                return Response({
                    'error': msg,
                    'redownload_available': True,
                    'redownload_price': str(track.price * 0.5),
                    'message': 'You can re-download at 50% price.'
                }, status=403)
            return Response({'error': msg}, status=403)

        # 3. Generate token (IP + device bound)
        token = DownloadManager.generate_token(
            profile, track.id, 'track', access_source,
            client_ip, user_agent, device_hash
        )

        response_data = {'download_url': f"/api/v1/downloads/{token.token}/"}

        # 4. Add warning if 1 attempt remaining [Spec §4.2]
        if msg:
            response_data['warning'] = msg
        if remaining == 1:
            response_data['warning'] = "WARNING: This is your last download attempt from this IP."

        return Response(response_data)


    @action(detail=True, methods=['post'], url_path='report',
            permission_classes=[permissions.IsAuthenticated])
    def report_content(self, request, pk=None):
        """User-driven content flagging [Fix 08]."""
        track = self.get_object()
        report_type = request.data.get('report_type')
        reason = request.data.get('reason')

        if not report_type or not reason:
            return Response({'error': 'report_type and reason are required.'}, status=400)

        from apps.admin_panel.models import ContentReport
        ContentReport.objects.create(
            reporter=request.user.profile,
            content_type='track',
            content_id=track.id,
            report_type=report_type,
            reason=reason
        )

        return Response({'status': 'reported', 'message': 'Thank you for your report. Admin will review it.'})

    @action(detail=True, methods=['post'], url_path='rate',
            permission_classes=[permissions.IsAuthenticated])
    def rate_content(self, request, pk=None):
        """Unified rating system [Fix 09]."""
        track = self.get_object()
        stars = request.data.get('stars')
        review = request.data.get('review', '')

        if not stars or not (1 <= int(stars) <= 5):
            return Response({'error': 'stars (1-5) is required.'}, status=400)

        from .models import StarRating
        rating, created = StarRating.objects.update_or_create(
            user=request.user.profile,
            content_type='track',
            content_id=track.id,
            defaults={'stars': int(stars), 'review': review}
        )

        return Response({'status': 'rated', 'stars': rating.stars})

    @action(detail=False, methods=['post'], url_path='validate-preview',
            permission_classes=[permissions.IsAuthenticated])
    def validate_preview(self, request):
        """
        Imp 08: Preview Validation Tool.
        Validates if a YouTube/Instagram URL is valid and embeddable.
        """
        url = request.data.get('url', '').strip()
        preview_type = request.data.get('type', '')

        if not url:
            return Response({'error': 'URL is required.'}, status=400)

        import re
        is_valid = False
        embed_url = ""

        if preview_type == 'youtube':
            yt_match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([^?&/]+)', url)
            if yt_match:
                video_id = yt_match.group(1)
                is_valid = True
                embed_url = f"https://www.youtube.com/embed/{video_id}"
        
        elif preview_type == 'instagram':
            ig_match = re.search(r'instagram\.com/(?:reels|p|reel)/([^/?&]+)', url)
            if ig_match:
                shortcode = ig_match.group(1)
                is_valid = True
                embed_url = f"https://www.instagram.com/reels/{shortcode}/embed"

        if is_valid:
            return Response({
                'valid': True, 
                'embed_url': embed_url,
                'message': f'Valid {preview_type} link detected.'
            })
        
        return Response({
            'valid': False, 
            'error': f'Invalid {preview_type} URL. Please provide a direct link to the video/reel.'
        }, status=400)


    @action(detail=True, methods=['post'], url_path='convert-external',
            permission_classes=[permissions.IsAuthenticated])
    def convert_to_external_link(self, request, pk=None):
        """Phase 3 Feature 1: Convert an underperforming or free track to an external link."""
        from django.utils import timezone
        
        track = self.get_object()
        
        # Security: Only track owner can do this
        if request.user.profile.dj_profile != track.dj:
            return Response({'error': 'You do not have permission to modify this track.'}, status=403)

        url = request.data.get('external_link_url', '').strip()
        if not url:
            return Response({'error': 'external_link_url is required.'}, status=400)

        # Validate URL formats using the management command logic we wrote earlier
        try:
            from apps.tracks.management.commands.check_external_link_health import validate_external_link
            valid, error = validate_external_link(url)
            if not valid:
                return Response({'error': error}, status=400)
        except ImportError:
            # Fallback simple validation if module is un-importable for some reason
            if not ('drive.google.com' in url or 'mediafire.com' in url):
                 return Response({'error': 'Only Google Drive or MediaFire links are allowed.'}, status=400)

        provider = 'google_drive' if 'drive.google.com' in url else 'mediafire' if 'mediafire.com' in url else 'other'

        # Update track
        track.is_external_link = True
        track.external_link_url = url
        track.external_link_provider = provider
        track.external_link_broken = False
        track.external_link_error = None
        track.converted_at = timezone.now()
        
        # We don't delete `file_key` here. The file stays on R2 for users who already bought it.
        # But we DO need to mark the notification as complete.
        
        track.save()
        
        # Update offload notification status if exists
        from apps.commerce.models import OffloadNotification
        OffloadNotification.objects.filter(
            dj=track.dj, 
            content_id=track.id, 
            content_type='track'
        ).update(status='converted')

        return Response({
            'status': 'success', 
            'message': 'Track converted to external link successfully.'
        })
