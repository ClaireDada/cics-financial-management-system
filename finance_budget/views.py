from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum

from .models import Budget, BudgetItem, ExpenseCategory
from fund_management.models import FundRequest


def get_role_name(user):
    return user.role.role_name if user.role else "Unassigned"


@login_required
def budget_list(request):
    role = get_role_name(request.user)
    budgets = Budget.objects.select_related("term", "prepared_by").prefetch_related("items", "items__category")

    total_active_budget = Budget.objects.filter(
        status=Budget.BudgetStatus.ACTIVE
    ).aggregate(total=Sum("total_amount"))["total"] or 0

    context = {
        "role_name": role,
        "budgets": budgets,
        "total_active_budget": total_active_budget,
    }
    return render(request, "finance_budget/budget_list.html", context)


@login_required
def budget_detail(request, budget_id):
    role = get_role_name(request.user)
    budget = get_object_or_404(
        Budget.objects.select_related("term", "prepared_by").prefetch_related("items__category"),
        pk=budget_id
    )

    items = budget.items.select_related("category").all()
    item_rows = []
    for item in items:
        # Sum released/approved requests against this item
        spent_or_released = item.fund_requests.filter(
            status__in=[
                FundRequest.RequestStatus.GOVERNOR_APPROVED,
                FundRequest.RequestStatus.RELEASED,
            ]
        ).aggregate(total=Sum("amount"))["total"] or 0

        item_rows.append({
            "item": item,
            "allocated": item.allocated_amount,
            "committed": spent_or_released,
            "remaining": max(item.allocated_amount - spent_or_released, 0),
        })

    context = {
        "role_name": role,
        "budget": budget,
        "item_rows": item_rows,
    }
    return render(request, "finance_budget/budget_detail.html", context)
