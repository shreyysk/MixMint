from rest_framework import serializers
from django.conf import settings
from decimal import Decimal
from .models import Track, TrackPreview, TrackVersion


class TrackPreviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackPreview
        fields = "__all__"


class TrackVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackVersion
        fields = "__all__"


class TrackSerializer(serializers.ModelSerializer):
    previews = TrackPreviewSerializer(many=True, read_only=True)
    versions = TrackVersionSerializer(many=True, read_only=True)

    class Meta:
        model = Track
        # SECURITY: never expose backend source fields (source_url/source_type)
        # or legacy external_link_* URLs. Buyers download via MixMint's own
        # signed endpoint only.
        fields = [
            "id",
            "dj",
            "title",
            "description",
            "price",
            "file_key",
            "cover_url",
            "duration_sec",
            "bpm",
            "genre",
            "year",
            "checksum",
            "file_size",
            "file_format",
            "preview_type",
            "youtube_url",
            "instagram_url",
            "is_active",
            "is_deleted",
            "download_count",
            "sales_last_7_days",
            "is_external_link",
            "external_link_broken",
            "converted_at",
            "created_at",
            "previews",
            "versions",
        ]
        read_only_fields = ["download_count", "sales_last_7_days", "converted_at", "created_at"]

    def validate_price(self, value):
        """Enforce minimum ₹19 for paid tracks [Spec §3.2]. Free (₹0) allowed."""
        if value > 0 and value < Decimal(str(settings.MIN_TRACK_PRICE)):
            raise serializers.ValidationError(
                f"Minimum price for paid tracks is ₹{settings.MIN_TRACK_PRICE}. " f"Set to ₹0 for free tracks."
            )
        return value

    def validate_description(self, value):
        if not value:
            return value
        try:
            import bleach

            ALLOWED_TAGS = ["b", "i", "em", "strong", "a", "br"]
            return bleach.clean(value, tags=ALLOWED_TAGS, strip=True)
        except ImportError:
            from django.utils.html import strip_tags

            return strip_tags(value)

    def validate_file_key(self, value):
        """Enforce file format standards [Gap 10]. Blank allowed for external-only tracks."""
        if not value:
            return value
        ext = value.split(".")[-1].lower()
        if ext not in settings.SUPPORTED_AUDIO_FORMATS:
            raise serializers.ValidationError(
                f'Unsupported file format .{ext}. Supported: {", ".join(settings.SUPPORTED_AUDIO_FORMATS)}'
            )
        return value

    def validate(self, data):
        """Ensure at least one DJ embed preview is provided (YouTube and/or Reel)."""
        preview_type = data.get("preview_type", getattr(self.instance, "preview_type", None))
        yt = data.get("youtube_url", getattr(self.instance, "youtube_url", None))
        ig = data.get("instagram_url", getattr(self.instance, "instagram_url", None))
        if not (yt or ig):
            raise serializers.ValidationError(
                {"youtube_url": "At least one preview is required (YouTube and/or Instagram Reel)."}
            )
        if preview_type == "youtube" and not yt:
            raise serializers.ValidationError({"youtube_url": "YouTube URL required for YouTube preview."})
        if preview_type == "instagram" and not ig:
            raise serializers.ValidationError({"instagram_url": "Instagram URL required for Instagram preview."})
        return data

    def update(self, instance, validated_data):
        # Offload prompts removed: catalog is now link->temp-cache by design,
        # so "free on R2" nudges no longer apply.
        return super().update(instance, validated_data)
