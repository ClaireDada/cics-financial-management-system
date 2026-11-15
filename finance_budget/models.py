
from django.conf import settings
from django.db import models
from django.db.models import Q, Sum


class Budget(models.Model):

    class BudgetStatus(models.TextChoices):
        DRAFT = "Draft", "Draft"
        ACTIVE = "Active", "Active"
        COMPLETED = "Completed", "Completed"
        ARCHIVED = "Archived", "Archived"

    budget_id = models.AutoField(primary_key=True)

    term = models.ForeignKey(
        "students.AcademicTerm",
        on_delete=models.PROTECT,
        related_name="budgets"
    )

    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="prepared_budgets"
    )

    title = models.CharField(max_length=150)

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20,
        choices=BudgetStatus.choices,
        default=BudgetStatus.DRAFT
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "budgets"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(total_amount__gte=0),
                name="budget_total_nonnegative"
            )
        ]

    @property
    def total_allocated(self):
        total = self.items.aggregate(
            total=Sum("allocated_amount")
        )["total"]

        return total or 0

    @property
    def unallocated_amount(self):
        return self.total_amount - self.total_allocated

    @property
    def is_overallocated(self):
        return self.total_allocated > self.total_amount

    def __str__(self):
        return self.title


class ExpenseCategory(models.Model):

    category_id = models.AutoField(primary_key=True)

    category_name = models.CharField(
        max_length=100,
        unique=True
    )

    description = models.TextField(blank=True)

    class Meta:
        db_table = "expense_categories"
        ordering = ["category_name"]
        verbose_name = "Expense Category"
        verbose_name_plural = "Expense Categories"

    def __str__(self):
        return self.category_name


class BudgetItem(models.Model):

    item_id = models.AutoField(primary_key=True)

    budget = models.ForeignKey(
        Budget,
        on_delete=models.PROTECT,
        related_name="items"
    )

    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name="budget_items"
    )

    description = models.CharField(max_length=200)

    allocated_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    class Meta:
        db_table = "budget_items"
        ordering = ["category__category_name", "description"]
        constraints = [
            models.CheckConstraint(
                condition=Q(allocated_amount__gte=0),
                name="budget_item_allocation_nonnegative"
            )
        ]

    def __str__(self):
        return f"{self.description} - {self.budget.title}"
