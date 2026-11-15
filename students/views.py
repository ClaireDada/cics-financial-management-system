from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q

from .models import Student, AcademicTerm
from finance_collections.models import CampaignObligation, Collection, CollectionCampaign
from finance_budget.models import Budget
from fund_management.models import Disbursement, Liquidation, FundReturn


def get_role_name(user):
    return user.role.role_name if user.role else "Unassigned"


@login_required
def student_payment_status(request):
    role = get_role_name(request.user)

    # Determine which student record to view
    target_student_id = request.GET.get("student_id")
    if target_student_id and role in ["Admin", "Treasurer", "Auditor"]:
        student = get_object_or_404(Student, pk=target_student_id)
    else:
        # Match logged-in user
        student = (
            Student.objects.filter(student_no__iexact=request.user.username).first()
            or Student.objects.filter(full_name__icontains=request.user.get_full_name()).first()
            or Student.objects.first()
        )

    obligations = []
    payments = []
    total_required = 0
    total_paid = 0
    remaining_balance = 0
    is_compliant = False

    if student:
        obligations = CampaignObligation.objects.filter(student=student).select_related(
            "campaign", "campaign__fee_type", "campaign__term"
        )
        payments = Collection.objects.filter(obligation__student=student).select_related(
            "obligation__campaign", "collected_by"
        ).order_by("-payment_date")

        total_required = sum(o.required_amount for o in obligations)
        total_paid = sum(o.total_paid for o in obligations)
        remaining_balance = max(total_required - total_paid, 0)
        is_compliant = bool(obligations and remaining_balance == 0)

    context = {
        "role_name": role,
        "student": student,
        "obligations": obligations,
        "payments": payments,
        "total_required": total_required,
        "total_paid": total_paid,
        "remaining_balance": remaining_balance,
        "is_compliant": is_compliant,
    }
    return render(request, "students/payment_status.html", context)


@login_required
def student_summary(request):
    role = get_role_name(request.user)
    current_term = AcademicTerm.objects.filter(is_current=True).first()

    total_collected = Collection.objects.aggregate(total=Sum("amount"))["total"] or 0
    total_budget = Budget.objects.filter(status=Budget.BudgetStatus.ACTIVE).aggregate(total=Sum("total_amount"))["total"] or 0
    total_released = Disbursement.objects.aggregate(total=Sum("amount_released"))["total"] or 0
    total_expenses = Liquidation.objects.aggregate(total=Sum("amount_spent"))["total"] or 0
    total_returns = FundReturn.objects.aggregate(total=Sum("amount_returned"))["total"] or 0

    campaigns = CollectionCampaign.objects.filter(
        status__in=[CollectionCampaign.CampaignStatus.ACTIVE, CollectionCampaign.CampaignStatus.COMPLETED]
    ).select_related("fee_type", "term")

    active_budgets = Budget.objects.filter(
        status=Budget.BudgetStatus.ACTIVE
    ).prefetch_related("items", "items__category")

    context = {
        "role_name": role,
        "current_term": current_term,
        "total_collected": total_collected,
        "total_budget": total_budget,
        "total_released": total_released,
        "total_expenses": total_expenses,
        "total_returns": total_returns,
        "campaigns": campaigns,
        "active_budgets": active_budgets,
    }
    return render(request, "students/student_summary.html", context)


@login_required
def student_list(request):
    role = get_role_name(request.user)
    if role not in ["Admin", "Treasurer", "Auditor", "Officer", "Governor"]:
        messages.error(request, "Unauthorized access.")
        return redirect("dashboard")

    search_query = request.GET.get("q", "").strip()
    students_qs = Student.objects.all().order_by("full_name")

    if search_query:
        students_qs = students_qs.filter(
            Q(student_no__icontains=search_query)
            | Q(full_name__icontains=search_query)
            | Q(program__icontains=search_query)
            | Q(section__icontains=search_query)
        )

    context = {
        "role_name": role,
        "students": students_qs,
        "search_query": search_query,
    }
    return render(request, "students/student_list.html", context)
