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
    queryset = Track.objects.filter(is_active=True, is_deleted=False, dj__store_paused=False)
    serializer_class = TrackSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['genre', 'dj', 'year', 'preview_type']
    search_fields = ['title', 'description', 'dj__dj_name']
    ordering_fields = ['created_at', 'price', 'download_count']

    def perform_create(self, serializer):
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

        # 1. Check purchase ownership [Spec §2.2]
        has_purchased = Purchase.objects.filter(
            user=profile,
            content_id=track.id,
            content_type='track',
            is_revoked=False,
        ).exists()

        if not has_purchased:
            if track.price <= 0:
                pass  # Free tracks don't require purchase
            else:
                return Response({
                    'error': 'You must purchase this track first.',
                    'price': str(track.price)
                }, status=403)

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
            profile, track.id, 'track', 'purchase',
            client_ip, user_agent, device_hash
        )

        response_data = {'download_url': f"/api/v1/downloads/{token.token}/"}

        # 4. Add warning if 1 attempt remaining [Spec §4.2]
        if msg:
            response_data['warning'] = msg
        if remaining == 1:
            response_data['warning'] = "WARNING: This is your last download attempt from this IP."

        return Response(response_data)
