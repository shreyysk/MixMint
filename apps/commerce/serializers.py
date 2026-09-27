from rest_framework import serializers
from .models import DJWallet, Purchase, LedgerEntry, Cart, CartItem


class DJWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = DJWallet
        fields = "__all__"
        read_only_fields = [f.name for f in DJWallet._meta.fields]


class PurchaseSerializer(serializers.ModelSerializer):
    """Buyer-facing purchase row. Gateway payloads and DJ source links are never exposed."""

    title = serializers.SerializerMethodField()
    content_title = serializers.SerializerMethodField()
    dj_name = serializers.CharField(source="seller.dj_name", read_only=True)
    invoice_id = serializers.SerializerMethodField()
    has_insurance = serializers.SerializerMethodField()
    has_download_insurance = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = Purchase
        fields = [
            "id",
            "content_type",
            "content_id",
            "title",
            "content_title",
            "cover_url",
            "dj_name",
            "original_price",
            "price_paid",
            "platform_fee",
            "discount_applied",
            "status",
            "paid_at",
            "created_at",
            "is_redownload",
            "download_completed",
            "is_revoked",
            "gateway_order_id",
            "invoice_id",
            "has_insurance",
            "has_download_insurance",
        ]
        read_only_fields = fields

    def get_title(self, obj):
        content = obj.get_content_object
        return getattr(content, "title", None) or f"{obj.content_type.title()} #{obj.content_id}"

    def get_content_title(self, obj):
        return self.get_title(obj)

    def get_cover_url(self, obj):
        content = obj.get_content_object
        url = getattr(content, "cover_url", None) or getattr(content, "cover_image", None)
        return str(url) if url else None

    def get_has_download_insurance(self, obj):
        return self.get_has_insurance(obj)

    def get_invoice_id(self, obj):
        invoice = getattr(obj, "invoice", None)
        return invoice.id if invoice else None

    def get_has_insurance(self, obj):
        ins = getattr(obj, "insurance", None)
        return bool(ins and ins.status == "active")


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = "__all__"


class CartItemSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    dj_name = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ["id", "content_type", "content_id", "price", "added_at", "title", "dj_name", "image_url"]

    def get_title(self, obj):
        try:
            if obj.content_type == "track":
                from apps.tracks.models import Track

                return Track.objects.get(id=obj.content_id).title
            elif obj.content_type == "album":
                from apps.albums.models import AlbumPack

                return AlbumPack.objects.get(id=obj.content_id).title
        except Exception:
            pass
        return "Unknown Item"

    def get_dj_name(self, obj):
        try:
            if obj.content_type == "track":
                from apps.tracks.models import Track

                return Track.objects.get(id=obj.content_id).dj.dj_name
            elif obj.content_type == "album":
                from apps.albums.models import AlbumPack

                return AlbumPack.objects.get(id=obj.content_id).dj.dj_name
        except Exception:
            pass
        return "Unknown Artist"

    def get_image_url(self, obj):
        try:
            if obj.content_type == "track":
                from apps.tracks.models import Track

                track = Track.objects.get(id=obj.content_id)
                return track.cover_url
            elif obj.content_type == "album":
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
    discount_percentage = serializers.ReadOnlyField()
    final_total = serializers.ReadOnlyField()
    payable_total = serializers.SerializerMethodField()
    next_tier_info = serializers.ReadOnlyField()

    def get_payable_total(self, obj):
        """What checkout will actually charge (paise): discounted items + buyer platform fee."""
        from apps.payments.views import _buyer_fee

        return obj.final_total + int(_buyer_fee() * 100) if obj.total_items else 0

    class Meta:
        model = Cart
        fields = [
            "id",
            "items",
            "total_items",
            "subtotal",
            "discount_amount",
            "discount_percentage",
            "final_total",
            "payable_total",
            "next_tier_info",
            "updated_at",
        ]
