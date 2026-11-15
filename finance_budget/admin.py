
from django.contrib import admin
from .models import Budget, ExpenseCategory, BudgetItem


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "term",
        "total_amount",
        "display_total_allocated",
        "display_unallocated",
        "status",
        "created_at",
    )

    list_filter = ("status", "term")
    search_fields = ("title",)

    @admin.display(description="Total Allocated")
    def display_total_allocated(self, obj):
        return f"PHP {obj.total_allocated:,.2f}"

    @admin.display(description="Unallocated Amount")
    def display_unallocated(self, obj):
        return f"PHP {obj.unallocated_amount:,.2f}"


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):

    list_display = (
        "category_name",
        "description",
    )

    search_fields = ("category_name",)


@admin.register(BudgetItem)
class BudgetItemAdmin(admin.ModelAdmin):

    list_display = (
        "description",
        "budget",
        "category",
        "allocated_amount",
    )

    list_filter = ("category", "budget")
    search_fields = ("description",)
