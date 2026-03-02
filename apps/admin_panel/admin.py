from django.contrib import admin
from .models import SystemSetting, AuditLog, FraudAlert, CopyrightReport, SupportTicket, BanList, KillSwitch, MaintenanceMode


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'updated_at')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('admin', 'action', 'created_at')
    list_filter = ('action',)


@admin.register(FraudAlert)
class FraudAlertAdmin(admin.ModelAdmin):
    list_display = ('user', 'alert_type', 'severity', 'status', 'created_at')
    list_filter = ('alert_type', 'severity', 'status')


@admin.register(CopyrightReport)
class CopyrightReportAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'priority', 'status', 'created_at')
    list_filter = ('priority', 'status')


@admin.register(BanList)
class BanListAdmin(admin.ModelAdmin):
    list_display = ('ban_type', 'value', 'is_active', 'created_at')
    list_filter = ('ban_type', 'is_active')


@admin.register(KillSwitch)
class KillSwitchAdmin(admin.ModelAdmin):
    list_display = ('is_active', 'activated_by', 'reason', 'activated_at')


@admin.register(MaintenanceMode)
class MaintenanceModeAdmin(admin.ModelAdmin):
    list_display = ('mode', 'message', 'activated_by', 'updated_at')
    list_filter = ('mode',)
