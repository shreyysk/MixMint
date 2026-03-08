from django.db import models
from uuid import uuid4
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
        ('bundle', 'Bundle'),
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
    # Gateway-agnostic payment fields
    payment_gateway = models.CharField(max_length=20, default='phonepe')
    gateway_order_id = models.CharField(max_length=100, null=True, blank=True)
    gateway_payment_id = models.CharField(max_length=100, null=True, blank=True)
    gateway_refund_id = models.CharField(max_length=100, null=True, blank=True)
    gateway_response = models.JSONField(null=True, blank=True)
    amount_paise = models.IntegerField(null=True, blank=True)
    
    status = models.CharField(max_length=20, default='pending')  # pending | paid | failed | refunded | disputed
    paid_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)

    seller = models.ForeignKey(DJProfile, on_delete=models.CASCADE, related_name='sales')
    is_redownload = models.BooleanField(default=False)  # Re-download at 50% price [Spec §5]
    has_download_insurance = models.BooleanField(default=False)  # Unlimited free re-downloads [Spec §4.3]
    is_escrow_released = models.BooleanField(default=False)  # Moves from escrow to available [Spec P2 §9]
    is_completed = models.BooleanField(default=False)  # Legacy back-compat
    download_completed = models.BooleanField(default=False)  # Byte verification [Spec §4.4]
    is_revoked = models.BooleanField(default=False)
    
    # [Phase 3] External Link / Offload System & Cart
    download_method = models.CharField(max_length=20, default='mixmint') # 'mixmint' | 'external_link'
    external_link_url = models.URLField(max_length=1000, null=True, blank=True)
    cart_id = models.UUIDField(null=True, blank=True)
    discount_applied = models.IntegerField(default=0)
    final_price = models.IntegerField(null=True, blank=True)
    buyer_role = models.CharField(max_length=10, default='user') # 'user' | 'dj' | 'admin'
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['gateway_payment_id']),
            models.Index(fields=['gateway_order_id']),
            models.Index(fields=['user', 'status']),
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


class WebhookLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    gateway = models.CharField(max_length=20)
    transaction_id = models.CharField(max_length=100, unique=True)
    payload = models.JSONField()
    status = models.CharField(max_length=50)
    processed = models.BooleanField(default=False)
    error = models.TextField(null=True, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

class Bundle(models.Model):
    """Imp 12: DJ-created discounted track packages."""
    dj = models.ForeignKey(DJProfile, on_delete=models.CASCADE, related_name='bundles')
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # In Rupees (converted to Paise in DB if needed, but keeping decimal for consistency)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class BundleTrack(models.Model):
    """Links tracks to a bundle."""
    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE, related_name='bundle_tracks')
    track = models.ForeignKey('tracks.Track', on_delete=models.CASCADE)
    display_order = models.IntegerField(default=0)

    class Meta:
        unique_together = ('bundle', 'track')

class BundlePurchase(models.Model):
    """Imp 12: Tracks a successful bundle sale."""
    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE, related_name='sales')
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='bundle_purchases')
    gateway_payment_id = models.CharField(max_length=255)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    dj_revenue = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

class Wishlist(models.Model):
    """Imp 13: Buyer wishlist for tracks."""
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='wishlist_items')
    track = models.ForeignKey('tracks.Track', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'track')
        ordering = ['-created_at']


class ProSubscriptionEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    dj = models.ForeignKey(DJProfile, on_delete=models.CASCADE, related_name='subscription_events')
    event_type = models.CharField(max_length=50)  # trial_start | payment_initiated | payment_success | ...
    plan_type = models.CharField(max_length=10)   # monthly | annual
    amount_paise = models.IntegerField()
    gateway = models.CharField(max_length=20, default='phonepe')
    gateway_order_id = models.CharField(max_length=100)
    gateway_payment_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class StorageOverage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    dj = models.ForeignKey(DJProfile, on_delete=models.CASCADE, related_name='overages')
    billing_month = models.DateField() # First day of the month being billed
    usage_bytes = models.BigIntegerField()
    overage_bytes = models.BigIntegerField()
    amount_paise = models.IntegerField()
    
    status = models.CharField(max_length=20, default='pending') # pending | paid | failed
    gateway_order_id = models.CharField(max_length=100, null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('dj', 'billing_month')


class RefundRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('processed', 'Processed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    purchase = models.OneToOneField(Purchase, on_delete=models.CASCADE, related_name='refund_request')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(null=True, blank=True)
    
    is_automated = models.BooleanField(default=False) # True if eligible for auto-refund
    eligible_for_auto_refund = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)


class PurchaseDispute(models.Model):
    """Purchase dispute ticketing system [Imp 01]."""
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    )
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='disputes')
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='disputes_opened')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    admin_notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class TransactionAlert(models.Model):
    """Missing Item 04: High-Value Transaction Alerts"""
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    purchase = models.ForeignKey('Purchase', on_delete=models.CASCADE, related_name='alerts')
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='transaction_alerts')
    alert_type = models.CharField(max_length=50)
    message = models.TextField()
    severity = models.CharField(max_length=10, choices=(('HIGH', 'High'), ('MEDIUM', 'Medium'), ('LOW', 'Low')))
    reviewed = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_tx_alerts')
    outcome = models.CharField(max_length=30, null=True, blank=True, choices=(('safe', 'Safe'), ('frozen', 'Frozen'), ('refunded_blocked', 'Refunded & Blocked')))
    created_at = models.DateTimeField(auto_now_add=True)


class EarningsHold(models.Model):
    """Missing Item 05: Hold Earnings / Payouts"""
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    dj = models.ForeignKey(DJProfile, on_delete=models.CASCADE, related_name='earnings_holds')
    amount = models.IntegerField()  # in paise
    hold_type = models.CharField(max_length=30, choices=(
        ('legal_review', 'Legal Review'), ('chargeback', 'Chargeback'),
        ('dispute', 'Dispute'), ('fraud_investigation', 'Fraud Investigation'), ('admin_manual', 'Admin Manual')
    ))
    reason = models.TextField()
    status = models.CharField(max_length=20, default='active', choices=(
        ('active', 'Active'), ('released', 'Released'), ('forfeited', 'Forfeited')
    ))
    placed_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='holds_placed')
    resolved_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='holds_resolved')
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AdminAuditLog(models.Model):
    """Missing Item 05: Immutable audit trail of all admin financial actions"""
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    admin = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name='financial_audit_logs')
    action = models.CharField(max_length=100)
    target_dj = models.ForeignKey(DJProfile, on_delete=models.SET_NULL, null=True, related_name='audit_logs_targeted')
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class OffloadNotification(models.Model):
    """Phase 3 Feature 1: Notifies DJs about underperforming or free tracks that can be offloaded."""
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    dj = models.ForeignKey(DJProfile, on_delete=models.CASCADE, related_name='offload_notifications')
    content_id = models.PositiveBigIntegerField()
    content_type = models.CharField(max_length=10) # 'track' | 'album'
    reason = models.CharField(max_length=20, default='underperforming') # 'underperforming' | 'free_on_r2'
    storage_mb = models.IntegerField(null=True, blank=True)
    sales_in_period = models.IntegerField(null=True, blank=True)
    period_days = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, default='pending') # 'pending' | 'converted' | 'kept' | 'dismissed'
    email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Offload {self.content_type} {self.content_id} for {self.dj}"

BULK_DISCOUNT_PERCENTAGE = 20  # 20% discount for 5+ items [Phase 3 Feature 3]

class Cart(models.Model):
    """Shopping Cart for multi-item checkout [Phase 3 Feature 3]."""
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='cart_items')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_items(self):
        return self.items.count()

    @property
    def subtotal(self):
        return sum(item.price for item in self.items.all())

    @property
    def discount_amount(self):
        if self.total_items >= 5:
            return round(self.subtotal * (BULK_DISCOUNT_PERCENTAGE / 100))
        return 0

    @property
    def final_total(self):
        return self.subtotal - self.discount_amount

class CartItem(models.Model):
    """Individual items within a Cart."""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    content_type = models.CharField(max_length=10, choices=Purchase.CONTENT_TYPES)
    content_id = models.PositiveBigIntegerField()
    price = models.IntegerField(help_text="Price at time of adding to cart")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'content_type', 'content_id')
