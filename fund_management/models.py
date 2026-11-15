
from django.conf import settings
from django.db import models
from django.db.models import Q, Sum


class FundRequest(models.Model):
    class RequestStatus(models.TextChoices):
        DRAFT = "Draft", "Draft"
        SUBMITTED = "Submitted", "Submitted"
        ADVISER_APPROVED = "Adviser Approved", "Adviser Approved"
        GOVERNOR_APPROVED = "Governor Approved", "Governor Approved"
        REJECTED = "Rejected", "Rejected"
        RELEASED = "Released", "Released"
        CANCELLED = "Cancelled", "Cancelled"

    request_id = models.AutoField(primary_key=True)

    item = models.ForeignKey(
        "finance_budget.BudgetItem",
        on_delete=models.PROTECT,
        related_name="fund_requests",
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="fund_requests",
    )

    purpose = models.TextField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(
        max_length=30,
        choices=RequestStatus.choices,
        default=RequestStatus.DRAFT,
    )

    requested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fund_requests"
        ordering = ["-requested_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="fund_request_amount_positive",
            )
        ]

    def __str__(self):
        return f"Request #{self.request_id} - {self.amount}"


class Approval(models.Model):
    class ApprovalStage(models.TextChoices):
        ADVISER = "Adviser", "Adviser"
        GOVERNOR = "Governor", "Governor"

    class Decision(models.TextChoices):
        APPROVED = "Approved", "Approved"
        REJECTED = "Rejected", "Rejected"

    approval_id = models.AutoField(primary_key=True)

    request = models.ForeignKey(
        FundRequest,
        on_delete=models.PROTECT,
        related_name="approvals",
    )

    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="fund_approvals",
    )

    approval_stage = models.CharField(
        max_length=20,
        choices=ApprovalStage.choices,
    )

    decision = models.CharField(
        max_length=20,
        choices=Decision.choices,
    )

    remarks = models.TextField(blank=True)
    adviser_bypassed = models.BooleanField(default=False)
    bypass_reason = models.TextField(blank=True)
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "approvals"
        ordering = ["decided_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(adviser_bypassed=False)
                    | (
                        Q(approval_stage="Governor")
                        & Q(bypass_reason__gt="")
                    )
                ),
                name="governor_bypass_requires_reason",
            )
        ]

    def __str__(self):
        return f"{self.approval_stage} - {self.decision}"


class ApprovalNotification(models.Model):
    notification_id = models.AutoField(primary_key=True)

    request = models.ForeignKey(
        FundRequest,
        on_delete=models.PROTECT,
        related_name="approval_notifications",
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approval_notifications",
    )

    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        db_table = "approval_notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification for Request #{self.request.request_id}"


class Disbursement(models.Model):
    disbursement_id = models.AutoField(primary_key=True)

    request = models.OneToOneField(
        FundRequest,
        on_delete=models.PROTECT,
        related_name="disbursement",
    )

    released_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="released_disbursements",
    )

    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="received_disbursements",
    )

    amount_released = models.DecimalField(max_digits=12, decimal_places=2)
    voucher_number = models.CharField(max_length=50, unique=True)
    released_at = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "disbursements"
        ordering = ["-released_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount_released__gt=0),
                name="disbursement_amount_positive",
            )
        ]

    def __str__(self):
        return f"Disbursement #{self.disbursement_id}"


class Liquidation(models.Model):
    liquidation_id = models.AutoField(primary_key=True)

    disbursement = models.ForeignKey(
        Disbursement,
        on_delete=models.PROTECT,
        related_name="liquidations",
    )

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recorded_liquidations",
    )

    expense_description = models.CharField(max_length=200)
    amount_spent = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField()
    remarks = models.TextField(blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "liquidations"
        ordering = ["-expense_date"]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount_spent__gt=0),
                name="liquidation_amount_positive",
            )
        ]

    def __str__(self):
        return f"{self.expense_description} - {self.amount_spent}"


class LiquidationReceipt(models.Model):
    receipt_id = models.AutoField(primary_key=True)

    liquidation = models.ForeignKey(
        Liquidation,
        on_delete=models.PROTECT,
        related_name="receipts",
    )

    receipt_number = models.CharField(max_length=100)
    receipt_date = models.DateField()
    vendor_name = models.CharField(max_length=150, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "liquidation_receipts"
        ordering = ["-receipt_date"]

    def __str__(self):
        return self.receipt_number


class FundReturn(models.Model):
    return_id = models.AutoField(primary_key=True)

    disbursement = models.ForeignKey(
        Disbursement,
        on_delete=models.PROTECT,
        related_name="fund_returns",
    )

    returned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_fund_returns",
    )

    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="received_fund_returns",
    )

    amount_returned = models.DecimalField(max_digits=12, decimal_places=2)
    return_date = models.DateField()
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "fund_returns"
        ordering = ["-return_date"]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount_returned__gt=0),
                name="fund_return_amount_positive",
            )
        ]

    def __str__(self):
        return f"Return #{self.return_id} - {self.amount_returned}"


class AuditLog(models.Model):
    class ActionType(models.TextChoices):
        CREATE = "CREATE", "Create"
        UPDATE = "UPDATE", "Update"
        DELETE = "DELETE", "Delete"
        SUBMIT = "SUBMIT", "Submit"
        APPROVE = "APPROVE", "Approve"
        REJECT = "REJECT", "Reject"
        RELEASE = "RELEASE", "Release"
        RECORD = "RECORD", "Record"
        RETURN = "RETURN", "Return"

    log_id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    action = models.CharField(
        max_length=20,
        choices=ActionType.choices,
    )

    module = models.CharField(max_length=100)
    record_id = models.CharField(max_length=50)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(
                fields=["user", "timestamp"],
                name="audit_user_time_idx",
            ),
            models.Index(
                fields=["module", "timestamp"],
                name="audit_module_time_idx",
            ),
        ]

    def __str__(self):
        return f"{self.action} - {self.module} - {self.record_id}"
