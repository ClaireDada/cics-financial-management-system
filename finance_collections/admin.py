
from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
from .models import (
    FeeType,
    CollectionCampaign,
    CampaignObligation,
    CollectionTurnover,
    Collection,
)


@admin.register(FeeType)
class FeeTypeAdmin(admin.ModelAdmin):
    list_display = (
        "fee_name",
        "default_amount",
        "is_active",
    )
    search_fields = ("fee_name",)
    list_filter = ("is_active",)


@admin.register(CollectionCampaign)
class CollectionCampaignAdmin(admin.ModelAdmin):
    list_display = (
        "campaign_name",
        "fee_type",
        "term",
        "start_date",
        "end_date",
        "status",
    )
    search_fields = ("campaign_name",)
    list_filter = ("status", "term", "fee_type")


@admin.register(CampaignObligation)
class CampaignObligationAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "campaign",
        "required_amount",
        "display_total_paid",
        "display_remaining_balance",
        "display_compliance_status",
    )
    search_fields = (
        "student__full_name",
        "student__student_no",
        "campaign__campaign_name",
    )
    list_filter = ("campaign",)

    @admin.display(description="Total Paid")
    def display_total_paid(self, obj):
        return f"PHP {obj.total_paid:,.2f}"

    @admin.display(description="Remaining Balance")
    def display_remaining_balance(self, obj):
        return f"PHP {obj.remaining_balance:,.2f}"

    @admin.display(description="Compliance Status")
    def display_compliance_status(self, obj):
        return obj.compliance_status



class CollectionTurnoverForm(forms.ModelForm):

    class Meta:
        model = CollectionTurnover
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        declared = cleaned_data.get("declared_amount")
        received = cleaned_data.get("received_amount")
        receiver = cleaned_data.get("received_by")
        remarks = cleaned_data.get("remarks")

        if received is not None and not receiver:
            self.add_error(
                "received_by",
                "Select the Treasurer who received the money."
            )

        if receiver and received is None:
            self.add_error(
                "received_amount",
                "Enter the actual amount received."
            )

        if declared is not None and received is not None:
            if declared != received and not (remarks or "").strip():
                self.add_error(
                    "remarks",
                    "Remarks are required when the amounts do not match."
                )

        return cleaned_data


@admin.register(CollectionTurnover)
class CollectionTurnoverAdmin(admin.ModelAdmin):

    form = CollectionTurnoverForm

    list_display = (
        "turnover_id",
        "submitted_by",
        "received_by",
        "declared_amount",
        "received_amount",
        "status",
        "submitted_at",
        "received_at",
    )

    list_filter = ("status",)

    search_fields = (
        "submitted_by__username",
        "received_by__username",
    )

    readonly_fields = (
        "submitted_at",
        "received_at",
    )

    def save_model(self, request, obj, form, change):
        from django.utils import timezone

        if obj.received_amount is not None and obj.received_by:
            if obj.received_amount == obj.declared_amount:
                obj.status = CollectionTurnover.TurnoverStatus.RECEIVED
            else:
                obj.status = CollectionTurnover.TurnoverStatus.DISPUTED

            if not obj.received_at:
                obj.received_at = timezone.now()

        else:
            obj.status = CollectionTurnover.TurnoverStatus.PENDING
            obj.received_at = None

        super().save_model(request, obj, form, change)


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = (
        "collection_id",
        "obligation",
        "amount",
        "or_number",
        "payment_date",
        "collected_by",
        "turnover",
    )
    list_filter = ("payment_date",)
    search_fields = (
        "or_number",
        "obligation__student__full_name",
        "obligation__student__student_no",
    )
