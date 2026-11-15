
from django.contrib import admin

from .models import (
    FundRequest,
    Approval,
    ApprovalNotification,
    Disbursement,
    Liquidation,
    LiquidationReceipt,
    FundReturn,
    AuditLog,
)


@admin.register(FundRequest)
class FundRequestAdmin(admin.ModelAdmin):
    list_display = (
        "request_id", "requested_by", "item",
        "amount", "status", "requested_at"
    )
    list_filter = ("status", "requested_at")
    search_fields = ("purpose", "requested_by__username")


@admin.register(Approval)
class ApprovalAdmin(admin.ModelAdmin):
    list_display = (
        "approval_id", "request", "approver",
        "approval_stage", "decision",
        "adviser_bypassed", "decided_at"
    )
    list_filter = ("approval_stage", "decision", "adviser_bypassed")
    search_fields = ("remarks", "bypass_reason")


@admin.register(ApprovalNotification)
class ApprovalNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "notification_id", "request", "recipient",
        "is_read", "created_at"
    )
    list_filter = ("is_read", "created_at")
    search_fields = ("message", "recipient__username")


@admin.register(Disbursement)
class DisbursementAdmin(admin.ModelAdmin):
    list_display = (
        "disbursement_id", "request", "released_by",
        "received_by", "amount_released",
        "voucher_number", "released_at"
    )
    search_fields = ("voucher_number",)


@admin.register(Liquidation)
class LiquidationAdmin(admin.ModelAdmin):
    list_display = (
        "liquidation_id", "disbursement", "recorded_by",
        "expense_description", "amount_spent", "expense_date"
    )
    list_filter = ("expense_date",)
    search_fields = ("expense_description",)


@admin.register(LiquidationReceipt)
class LiquidationReceiptAdmin(admin.ModelAdmin):
    list_display = (
        "receipt_id", "liquidation", "receipt_number",
        "receipt_date", "vendor_name"
    )
    search_fields = ("receipt_number", "vendor_name")


@admin.register(FundReturn)
class FundReturnAdmin(admin.ModelAdmin):
    list_display = (
        "return_id", "disbursement", "returned_by",
        "received_by", "amount_returned", "return_date"
    )
    list_filter = ("return_date",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "log_id", "user", "action",
        "module", "record_id", "timestamp"
    )
    list_filter = ("action", "module", "timestamp")
    search_fields = (
        "description", "module", "record_id",
        "user__username"
    )
    readonly_fields = (
        "user", "action", "module", "record_id",
        "description", "timestamp"
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
