from rest_framework import serializers
from .models import DownloadLog

class DownloadLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DownloadLog
        fields = ['id', 'content_id', 'content_type', 'ip_address', 'device_hash', 'attempt_number', 'completed', 'checksum_verified', 'bytes_delivered', 'created_at']
        read_only_fields = fields
