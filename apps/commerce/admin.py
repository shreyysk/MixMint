from django.contrib import admin
from .models import DJWallet, Purchase, LedgerEntry, Invoice, TaxRecord, Payout, DJApplicationFee, AdRevenueLog


@admin.register(DJWallet)
class DJWalletAdmin(admin.ModelAdmin):
    list_display = ('dj', 'total_earnings', 'pending_earnings', 'escrow_amount', 'available_for_payout')


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_type', 'content_id', 'original_price', 'price_paid', 'commission', 'is_redownload', 'download_completed', 'created_at')
    list_filter = ('content_type', 'is_redownload', 'download_completed', 'is_completed', 'is_revoked')


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'amount', 'entry_type', 'created_at')
    list_filter = ('entry_type',)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'user', 'dj', 'total_amount', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(TaxRecord)
class TaxRecordAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'tax_type', 'tax_rate', 'tax_amount')


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ('dj', 'amount', 'status', 'auto_retry_count', 'created_at', 'processed_at')
    list_filter = ('status',)


@admin.register(DJApplicationFee)
class DJApplicationFeeAdmin(admin.ModelAdmin):
    list_display = ('dj', 'amount', 'status', 'created_at', 'paid_at')
    list_filter = ('status',)


@admin.register(AdRevenueLog)
class AdRevenueLogAdmin(admin.ModelAdmin):
    list_display = ('dj', 'content_id', 'ad_impression_value', 'created_at')

from .models import TransactionAlert, EarningsHold, AdminAuditLog, OffloadNotification

@admin.register(TransactionAlert)
class TransactionAlertAdmin(admin.ModelAdmin):
    list_display = ('id', 'purchase', 'user', 'alert_type', 'severity', 'reviewed', 'created_at')
    list_filter = ('severity', 'reviewed', 'alert_type')

@admin.register(EarningsHold)
class EarningsHoldAdmin(admin.ModelAdmin):
    list_display = ('dj', 'amount', 'hold_type', 'status', 'created_at')
    list_filter = ('hold_type', 'status')

@admin.register(AdminAuditLog)
class AdminAuditLogAdmin(admin.ModelAdmin):
    list_display = ('admin', 'action', 'target_dj', 'created_at')
    list_filter = ('action',)

@admin.register(OffloadNotification)
class OffloadNotificationAdmin(admin.ModelAdmin):
    list_display = ('dj', 'content_type', 'reason', 'status', 'email_sent', 'created_at')
    list_filter = ('status', 'reason', 'content_type', 'email_sent')
    search_fields = ('dj__dj_name', 'content_id')
