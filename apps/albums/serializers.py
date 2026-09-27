from rest_framework import serializers
from django.conf import settings
from decimal import Decimal
from .models import AlbumPack, AlbumTrack


class AlbumTrackSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlbumTrack
        # original_file_key / processed_filename are private storage paths.
        fields = ["id", "track_order", "title", "duration", "file_size", "format"]


class AlbumPackSerializer(serializers.ModelSerializer):
    tracks = AlbumTrackSerializer(many=True, read_only=True)

    class Meta:
        model = AlbumPack
        # SECURITY: backend storage/source fields are write-only (DJ can set on
        # upload, but they are never readable). Buyers download via MixMint's
        # own signed endpoints only.
        fields = [
            "id",
            "dj",
            "title",
            "description",
            "price",
            "file_key",
            "cover_image",
            "preview_type",
            "youtube_url",
            "instagram_url",
            "is_active",
            "is_deleted",
            "is_external_link",
            "external_link_url",
            "external_link_broken",
            "converted_at",
            "upload_method",
            "original_file_key",
            "processing_status",
            "processing_completed_at",
            "track_count",
            "total_duration",
            "file_size",
            "created_at",
            "tracks",
        ]
        read_only_fields = [
            "dj",
            "track_count",
            "total_duration",
            "file_size",
            "converted_at",
            "created_at",
            "is_deleted",
            "is_external_link",
            "external_link_broken",
            "processing_status",
            "processing_completed_at",
        ]
        extra_kwargs = {
            "file_key": {"write_only": True},
            "original_file_key": {"write_only": True},
            "external_link_url": {"write_only": True},
        }

    def validate_price(self, value):
        """Enforce minimum ₹49 for albums [Spec §3.2]."""
        if value < Decimal(str(settings.MIN_ALBUM_PRICE)):
            raise serializers.ValidationError(f"Minimum album price is ₹{settings.MIN_ALBUM_PRICE}.")
        return value

    def validate_file_key(self, value):
        """Reject path traversal in R2 keys (plain relative paths only)."""
        if value and (".." in value or value.startswith(("/", "\\")) or "\\" in value or "\x00" in value):
            raise serializers.ValidationError("Invalid file path.")
        return value
