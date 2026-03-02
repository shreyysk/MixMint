from rest_framework import serializers
from .models import DJWallet, Purchase, LedgerEntry


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
