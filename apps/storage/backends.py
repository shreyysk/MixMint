from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings

class R2Storage(S3Boto3Storage):
    """Private R2 storage — no public access [Spec §5: No Public Files]."""
    location = ''
    default_acl = 'private'  # CRITICAL: All files private, served via secure proxy only
    file_overwrite = False
    custom_domain = None  # No public domain — all access via proxy [Spec §5]

    def __init__(self, *args, **kwargs):
        kwargs['endpoint_url'] = settings.AWS_S3_ENDPOINT_URL
        super().__init__(*args, **kwargs)
