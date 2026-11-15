
from django.conf import settings
from django.db import models
from django.db.models import Q, Sum


class FeeType(models.Model):
    fee_type_id = models.AutoField(primary_key=True)
    fee_name = models.CharField(max_length=100, unique=True)
    default_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "fee_types"
        ordering = ["fee_name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(default_amount__gte=0),
                name="fee_default_amount_nonnegative"
            )
        ]

    def __str__(self):
        return self.fee_name


class CollectionCampaign(models.Model):

    class CampaignStatus(models.TextChoices):
        DRAFT = "Draft", "Draft"
        ACTIVE = "Active", "Active"
        COMPLETED = "Completed", "Completed"
        CANCELLED = "Cancelled", "Cancelled"

    campaign_id = models.AutoField(primary_key=True)

    fee_type = models.ForeignKey(
        FeeType,
        on_delete=models.PROTECT,
        related_name="campaigns"
    )

    term = models.ForeignKey(
        "students.AcademicTerm",
        on_delete=models.PROTECT,
        related_name="campaigns"
    )

    campaign_name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=CampaignStatus.choices,
        default=CampaignStatus.DRAFT
    )

    class Meta:
        db_table = "collection_campaigns"
        ordering = ["-start_date"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")),
                name="campaign_valid_date_range"
            )
        ]

    def __str__(self):
        return self.campaign_name


class CampaignObligation(models.Model):

    obligation_id = models.AutoField(primary_key=True)

    campaign = models.ForeignKey(
        CollectionCampaign,
        on_delete=models.PROTECT,
        related_name="obligations"
    )

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="campaign_obligations"
    )

    required_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    class Meta:
        db_table = "campaign_obligations"
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "student"],
                name="unique_student_campaign_obligation"
            ),
            models.CheckConstraint(
                condition=Q(required_amount__gt=0),
                name="obligation_amount_positive"
            )
        ]

    @property
    def total_paid(self):
        total = self.payments.aggregate(
            total=Sum("amount")
        )["total"]

        return total or 0

    @property
    def remaining_balance(self):
        balance = self.required_amount - self.total_paid
        return max(balance, 0)

    @property
    def compliance_status(self):
        if self.total_paid >= self.required_amount:
            return "Complied"

        return "Not Complied"

    def __str__(self):
        return f"{self.student} - {self.campaign}"


class CollectionTurnover(models.Model):

    class TurnoverStatus(models.TextChoices):
        PENDING = "Pending", "Pending"
        RECEIVED = "Received", "Received"
        DISPUTED = "Disputed", "Disputed"

    turnover_id = models.AutoField(primary_key=True)

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_turnovers"
    )

    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="received_turnovers"
    )

    declared_amount = models.DecimalField(
        max_digits=12, decimal_places=2
    )

    received_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )

    submitted_at = models.DateTimeField(auto_now_add=True)
    received_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=TurnoverStatus.choices,
        default=TurnoverStatus.PENDING
    )

    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "collection_turnovers"
        ordering = ["-submitted_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(declared_amount__gt=0),
                name="turnover_declared_amount_positive"
            ),
            models.CheckConstraint(
                condition=Q(received_amount__isnull=True)
                | Q(received_amount__gte=0),
                name="turnover_received_amount_nonnegative"
            )
        ]

    def __str__(self):
        return f"Turnover #{self.turnover_id} - {self.status}"


class Collection(models.Model):

    collection_id = models.AutoField(primary_key=True)

    obligation = models.ForeignKey(
        CampaignObligation,
        on_delete=models.PROTECT,
        related_name="payments"
    )

    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recorded_collections"
    )

    turnover = models.ForeignKey(
        CollectionTurnover,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="collections"
    )

    or_number = models.CharField(max_length=50, blank=True)

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    payment_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "collections"
        ordering = ["-payment_date", "-collection_id"]
        indexes = [
            models.Index(
                fields=["payment_date"],
                name="collection_payment_date_idx"
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="collection_amount_positive"
            )
        ]

    def __str__(self):
        return f"Payment #{self.collection_id} - {self.amount}"
