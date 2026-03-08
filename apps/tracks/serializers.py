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

    def validate_file_key(self, value):
        """Enforce file format standards [Gap 10]."""
        ext = value.split('.')[-1].lower()
        if ext not in settings.SUPPORTED_AUDIO_FORMATS:
            raise serializers.ValidationError(
                f'Unsupported file format .{ext}. Supported: {", ".join(settings.SUPPORTED_AUDIO_FORMATS)}'
            )
        return value

    def validate(self, data):
        """Ensure preview is provided [Spec §2.1: Preview mandatory]."""
        preview_type = data.get('preview_type', getattr(self.instance, 'preview_type', None))
        if preview_type == 'youtube' and not data.get('youtube_url', getattr(self.instance, 'youtube_url', None)):
            raise serializers.ValidationError({'youtube_url': 'YouTube URL required for YouTube preview.'})
        if preview_type == 'instagram' and not data.get('instagram_url', getattr(self.instance, 'instagram_url', None)):
            raise serializers.ValidationError({'instagram_url': 'Instagram URL required for Instagram preview.'})
        return data

    def update(self, instance, validated_data):
        # Phase 3 Feature 1: Immediate offload prompt when DJ sets track price to ₹0
        previous_price = instance.price
        new_price = validated_data.get('price', instance.price)
        
        track = super().update(instance, validated_data)
        
        if previous_price > 0 and new_price == 0 and not track.is_external_link:
            from apps.commerce.models import OffloadNotification
            OffloadNotification.objects.get_or_create(
                dj=track.dj,
                content_id=track.id,
                content_type='track',
                defaults={
                    'reason': 'free_on_r2',
                    'storage_mb': (track.file_size or 0) // (1024 * 1024),
                    'status': 'pending'
                }
            )
            
        return track
