from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import AlbumPack
from .serializers import AlbumPackSerializer
from apps.downloads.utils import DownloadManager
from apps.accounts.permissions import IsNotBanned


class AlbumPackViewSet(viewsets.ModelViewSet):
    """Public browse; only approved DJs create, only the owning DJ edits/deletes."""

    queryset = AlbumPack.objects.filter(is_active=True, is_deleted=False, dj__profile__store_paused=False)
    serializer_class = AlbumPackSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["dj", "processing_status"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsNotBanned()]

    def _approved_dj(self, request):
        profile = getattr(request.user, "profile", None)
        dj = getattr(profile, "dj_profile", None) if profile else None
        if not profile or profile.role != "dj" or dj is None or dj.status != "approved":
            return None
        return dj

    def create(self, request, *args, **kwargs):
        if not self._approved_dj(request):
            return Response({"error": "Only approved DJs can upload albums."}, status=403)
        return super().create(request, *args, **kwargs)

    def _owner_guard(self, request, album):
        if request.user.is_staff:
            return None
        dj = self._approved_dj(request)
        if not dj or album.dj_id != dj.id:
            return Response({"error": "You can only modify your own albums."}, status=403)
        return None

    def update(self, request, *args, **kwargs):
        denied = self._owner_guard(request, self.get_object())
        return denied or super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        album = self.get_object()
        denied = self._owner_guard(request, album)
        if denied:
            return denied
        album.is_deleted = True
        album.is_active = False
        album.save(update_fields=["is_deleted", "is_active"])
        return Response(status=204)

    def perform_create(self, serializer):
        """Owner is the requesting DJ; process album ZIP upon upload [Spec §5]."""
        album = serializer.save(dj=self.request.user.profile.dj_profile)
        from .tasks import process_album_task

        process_album_task.delay(album.id)

    @action(detail=True, methods=["post"], url_path="download-token", permission_classes=[permissions.IsAuthenticated])
    def get_download_token(self, request, pk=None):
        """Ownership-checked, IP/device-bound one-time download token [Spec §4]."""
        return DownloadManager.issue_token_response(request, self.get_object(), "album")
