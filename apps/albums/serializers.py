from rest_framework import serializers
from django.conf import settings
from decimal import Decimal
from .models import AlbumPack, AlbumTrack


class AlbumTrackSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlbumTrack
        fields = '__all__'


class AlbumPackSerializer(serializers.ModelSerializer):
    tracks = AlbumTrackSerializer(many=True, read_only=True)

    class Meta:
        model = AlbumPack
        fields = '__all__'

    def validate_price(self, value):
        """Enforce minimum ₹49 for albums [Spec §3.2]."""
        if value < Decimal(str(settings.MIN_ALBUM_PRICE)):
            raise serializers.ValidationError(
                f'Minimum album price is ₹{settings.MIN_ALBUM_PRICE}.'
            )
        return value
