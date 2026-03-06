from django.db import models
from apps.accounts.models import Profile, DJProfile

# Checkout service fee range [Spec P3 §1.3]
DEFAULT_CHECKOUT_FEE = 5.00  # ₹5


class DJWallet(models.Model):
    """DJ earnings wallet with breakdown [Spec P2 §9]"""
    dj = models.OneToOneField(DJProfile, on_delete=models.CASCADE, primary_key=True, related_name='wallet')
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    pending_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    escrow_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)  # Chargeback reserve
    available_for_payout = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.dj.dj_name}'s Wallet"


class Purchase(models.Model):
    CONTENT_TYPES = (
        ('track', 'Track'),
        ('album', 'Album'),
    )
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='purchases')
    content_id = models.PositiveBigIntegerField()
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    original_price = models.DecimalField(max_digits=10, decimal_places=2)  # Pre-discount price [Spec P2 §5]
    checkout_fee = models.DecimalField(max_digits=10, decimal_places=2, default=5.00)  # Platform service fee [Spec P3 §1.3]
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # 15% platform commission
    # Canonical per spec is dj_revenue; keep dj_earnings for backwards compatibility.
    dj_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # 85% DJ revenue [Spec P2 §5]
    dj_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Back-compat alias
    ad_revenue_allocated = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Ad revenue share
    price_paid = models.DecimalField(max_digits=10, decimal_places=2)  # Final amount charged to buyer
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_id = models.CharField(max_length=255, unique=True)
    payment_order_id = models.CharField(max_length=255, null=True, blank=True)
    seller = models.ForeignKey(DJProfile, on_delete=models.CASCADE, related_name='sales')
    is_redownload = models.BooleanField(default=False)  # Re-download at 50% price [Spec §5]
    is_completed = models.BooleanField(default=False)  # Payment verified [Spec P2 §5]
    download_completed = models.BooleanField(default=False)  # Byte verification [Spec §4.4]
    is_revoked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['payment_id']),
            models.Index(fields=['payment_order_id']),
            models.Index(fields=['user', 'is_completed', 'download_completed']),
        ]


class LedgerEntry(models.Model):
    TYPE_CHOICES = (
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    )
    wallet = models.ForeignKey(DJWallet, on_delete=models.CASCADE, related_name='ledger_entries')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    entry_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Invoice(models.Model):
    purchase = models.OneToOneField(Purchase, on_delete=models.SET_NULL, null=True, related_name='invoice')
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='invoices')
    dj = models.ForeignKey(DJProfile, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=100, unique=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(max_length=20, default='issued')
    created_at = models.DateTimeField(auto_now_add=True)


class TaxRecord(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='tax_records')
    tax_type = models.CharField(max_length=50, default='GST')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2)
    jurisdiction = models.CharField(max_length=100, default='India')
    created_at = models.DateTimeField(auto_now_add=True)


class Payout(models.Model):
    """Weekly DJ payout tracking [Spec P2 §9]"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('held', 'Held'),  # Admin hold for fraud/legal
    )
    dj = models.ForeignKey(DJProfile, on_delete=models.CASCADE, related_name='payouts')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_reference = models.CharField(max_length=255, null=True, blank=True)
    hold_reason = models.TextField(null=True, blank=True)
    auto_retry_count = models.IntegerField(default=0)  # Auto retry on failure [Spec P2 §9]
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)


class DJApplicationFee(models.Model):
    """₹99 application fee tracking [Spec §7]"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('waived', 'Waived'),
        ('refunded', 'Refunded'),
    )
    dj = models.OneToOneField(DJProfile, on_delete=models.CASCADE, related_name='application_fee')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=99.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)


class AdRevenueLog(models.Model):
    """Ad revenue tracking per DJ content [Spec P2 §8]"""
    dj = models.ForeignKey(DJProfile, on_delete=models.CASCADE, related_name='ad_revenue_logs')
    content_id = models.PositiveBigIntegerField()
    ad_impression_value = models.DecimalField(max_digits=10, decimal_places=4)
    created_at = models.DateTimeField(auto_now_add=True)


class LegalAgreement(models.Model):
    """Tracking legal agreement acceptance [Spec §9]."""
    version = models.CharField(max_length=20)
    title = models.CharField(max_length=255)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} (v{self.version})"


class UserAgreementAcceptance(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='legal_acceptances')
    agreement = models.ForeignKey(LegalAgreement, on_delete=models.CASCADE)
    accepted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()

    class Meta:
        unique_together = ('user', 'agreement')
