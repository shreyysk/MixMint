from rest_framework import serializers
from django.conf import settings
from decimal import Decimal
from .models import Track, TrackPreview, TrackVersion


class TrackPreviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackPreview
        fields = '__all__'


class TrackVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackVersion
        fields = '__all__'


class TrackSerializer(serializers.ModelSerializer):
    previews = TrackPreviewSerializer(many=True, read_only=True)
    versions = TrackVersionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Track
        fields = '__all__'

    def validate_price(self, value):
        """Enforce minimum ₹19 for paid tracks [Spec §3.2]. Free (₹0) allowed."""
        if value > 0 and value < Decimal(str(settings.MIN_TRACK_PRICE)):
            raise serializers.ValidationError(
                f'Minimum price for paid tracks is ₹{settings.MIN_TRACK_PRICE}. '
                f'Set to ₹0 for free tracks.'
            )
        return value

    def validate(self, data):
        """Ensure preview is provided [Spec §2.1: Preview mandatory]."""
        preview_type = data.get('preview_type')
        if preview_type == 'youtube' and not data.get('youtube_url'):
            raise serializers.ValidationError({'youtube_url': 'YouTube URL required for YouTube preview.'})
        if preview_type == 'instagram' and not data.get('instagram_url'):
            raise serializers.ValidationError({'instagram_url': 'Instagram URL required for Instagram preview.'})
        return data
