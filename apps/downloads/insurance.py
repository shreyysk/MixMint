"""
MixMint Download Insurance Model & Logic [Spec §4.3].

Optional add-on that allows unlimited re-downloads for a specific
purchase. Available after 24 hours from original purchase.
"""

from django.db import models
from apps.accounts.models import Profile
from apps.commerce.models import Purchase


class DownloadInsurance(models.Model):
    """Optional download insurance — unlimited re-downloads [Spec §4.3]."""
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('claimed', 'Claimed'),
    )
    purchase = models.OneToOneField(Purchase, on_delete=models.CASCADE, related_name='insurance')
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='download_insurances')
    content_id = models.PositiveBigIntegerField()
    content_type = models.CharField(max_length=20)
    insurance_price = models.DecimalField(max_digits=10, decimal_places=2)
    payment_id = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    claims_used = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Insurance for Purchase #{self.purchase_id}"
