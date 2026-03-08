from django.conf import settings

def get_r2_bucket(is_public=False):
    """Return the correct R2 bucket based on visibility [Gap 07]."""
    if is_public:
        return settings.R2_PUBLIC_BUCKET
    return settings.R2_PRIVATE_BUCKET
