from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import AlbumPack
from .serializers import AlbumPackSerializer
from apps.downloads.utils import DownloadManager
from apps.commerce.models import Purchase


class AlbumPackViewSet(viewsets.ModelViewSet):
    queryset = AlbumPack.objects.filter(is_active=True, is_deleted=False, dj__profile__store_paused=False)
    serializer_class = AlbumPackSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['dj', 'processing_status']

    @action(detail=True, methods=['post'], url_path='download-token',
            permission_classes=[permissions.IsAuthenticated])
    def get_download_token(self, request, pk=None):
        """
        Generate a secure download token for album/ZIP.
        Ownership-based access only. 3 attempts per IP.
        """
        album = self.get_object()
        profile = request.user.profile
        client_ip = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT')

        # 1. Check purchase ownership [Spec §2.2]
        has_purchased = Purchase.objects.filter(
            user=profile,
            content_id=album.id,
            content_type='album',
            is_revoked=False,
        ).exists()

        if not has_purchased:
            return Response({
                'error': 'You must purchase this album first.',
                'price': str(album.price)
            }, status=403)

        # 2. Check IP attempt limit [Spec §5: 3 per IP]
        allowed, msg, remaining = DownloadManager.check_ip_attempts(client_ip, album.id, 'album')
        if not allowed:
            eligible, redownload_msg = DownloadManager.check_redownload_eligibility(
                profile, album.id, 'album'
            )
            if eligible:
                return Response({
                    'error': msg,
                    'redownload_available': True,
                    'redownload_price': str(album.price * 0.5),
                    'message': 'You can re-download at 50% price.'
                }, status=403)
            return Response({'error': msg}, status=403)

        # 3. Generate token
        token = DownloadManager.generate_token(
            profile, album.id, 'album', 'purchase', client_ip, user_agent
        )
        response_data = {'download_url': f"/api/v1/downloads/{token.token}/"}
        if msg:
            response_data['warning'] = msg
        if remaining == 1:
            response_data['warning'] = "WARNING: This is your last download attempt from this IP."

        return Response(response_data)
