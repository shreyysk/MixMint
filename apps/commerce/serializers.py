from rest_framework import serializers
from .models import DJWallet, Purchase, LedgerEntry, Cart, CartItem


class DJWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = DJWallet
        fields = '__all__'


class PurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Purchase
        fields = '__all__'


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = '__all__'


class CartItemSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    dj_name = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'content_type', 'content_id', 'price', 'added_at', 'title', 'dj_name', 'image_url']

    def get_title(self, obj):
        try:
            if obj.content_type == 'track':
                from apps.tracks.models import Track
                return Track.objects.get(id=obj.content_id).title
            elif obj.content_type == 'album':
                from apps.albums.models import AlbumPack
                return AlbumPack.objects.get(id=obj.content_id).title
        except Exception:
            pass
        return "Unknown Item"

    def get_dj_name(self, obj):
        try:
            if obj.content_type == 'track':
                from apps.tracks.models import Track
                return Track.objects.get(id=obj.content_id).dj.dj_name
            elif obj.content_type == 'album':
                from apps.albums.models import AlbumPack
                return AlbumPack.objects.get(id=obj.content_id).dj.dj_name
        except Exception:
            pass
        return "Unknown Artist"

    def get_image_url(self, obj):
        try:
            if obj.content_type == 'track':
                from apps.tracks.models import Track
                track = Track.objects.get(id=obj.content_id)
                return track.cover_url
            elif obj.content_type == 'album':
                from apps.albums.models import AlbumPack
                album = AlbumPack.objects.get(id=obj.content_id)
                return album.cover_image
        except Exception:
            pass
        return None


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.ReadOnlyField()
    subtotal = serializers.ReadOnlyField()
    discount_amount = serializers.ReadOnlyField()
    final_total = serializers.ReadOnlyField()

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_items', 'subtotal', 'discount_amount', 'final_total', 'updated_at']
