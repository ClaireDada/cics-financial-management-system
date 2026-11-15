
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q

from students.models import Student, AcademicTerm
from finance_collections.models import (
    Collection,
    CollectionCampaign,
    CampaignObligation,
    CollectionTurnover,
)
from finance_budget.models import Budget, BudgetItem
from fund_management.models import (
    FundRequest,
    Approval,
    ApprovalNotification,
    Disbursement,
    Liquidation,
    FundReturn,
    AuditLog,
)


User = get_user_model()


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            if not user.is_active:
                messages.error(
                    request,
                    "Your account is inactive. Please contact the administrator."
                )
                return redirect("login")

            login(request, user)
            messages.success(
                request,
                f"Welcome, {user.get_full_name() or user.username}!"
            )
            return redirect("dashboard")

        messages.error(
            request,
            "Invalid username or password. Please try again."
        )

    return render(request, "accounts/login.html")


@login_required
def logout_view(request):
    if request.method == "POST":
        logout(request)
        messages.success(request, "You have successfully logged out.")
        return redirect("login")

    return redirect("dashboard")


@login_required
def dashboard_view(request):
    user = request.user

    role_name = (
        user.role.role_name
        if user.role
        else "Unassigned"
    )

    dashboard_templates = {
        "Admin": "accounts/dashboards/admin.html",
        "Governor": "accounts/dashboards/governor.html",
        "Treasurer": "accounts/dashboards/treasurer.html",
        "Auditor": "accounts/dashboards/auditor.html",
        "Officer": "accounts/dashboards/officer.html",
        "Adviser": "accounts/dashboards/adviser.html",
        "Student": "accounts/dashboards/student.html",
    }

    template_name = dashboard_templates.get(
        role_name,
        "accounts/dashboards/unassigned.html"
    )

    context = {
        "user": user,
        "role_name": role_name,
        "current_term": AcademicTerm.objects.filter(is_current=True).first(),
    }

    # ==========================
    # 1. ADMIN DASHBOARD
    # ==========================
    if role_name == "Admin":
        total_collected = Collection.objects.aggregate(total=Sum("amount"))["total"] or 0
        total_budget = Budget.objects.aggregate(total=Sum("total_amount"))["total"] or 0
        total_released = Disbursement.objects.aggregate(total=Sum("amount_released"))["total"] or 0
        total_expenses = Liquidation.objects.aggregate(total=Sum("amount_spent"))["total"] or 0
        total_returns = FundReturn.objects.aggregate(total=Sum("amount_returned"))["total"] or 0
        pending_requests = FundRequest.objects.filter(
            status__in=[
                FundRequest.RequestStatus.SUBMITTED,
                FundRequest.RequestStatus.ADVISER_APPROVED,
            ]
        ).count()

        context.update({
            "total_users": User.objects.count(),
            "active_users": User.objects.filter(is_active=True).count(),
            "total_students": Student.objects.count(),
            "total_terms": AcademicTerm.objects.count(),
            "total_campaigns": CollectionCampaign.objects.count(),
            "active_campaigns": CollectionCampaign.objects.filter(
                status=CollectionCampaign.CampaignStatus.ACTIVE
            ).count(),
            "total_collections": Collection.objects.count(),
            "total_collected": total_collected,
            "pending_turnovers": CollectionTurnover.objects.filter(
                status=CollectionTurnover.TurnoverStatus.PENDING
            ).count(),
            "disputed_turnovers": CollectionTurnover.objects.filter(
                status=CollectionTurnover.TurnoverStatus.DISPUTED
            ).count(),
            "total_budgets": Budget.objects.count(),
            "active_budgets": Budget.objects.filter(
                status=Budget.BudgetStatus.ACTIVE
            ).count(),
            "total_budget": total_budget,
            "total_fund_requests": FundRequest.objects.count(),
            "pending_requests": pending_requests,
            "total_disbursements": Disbursement.objects.count(),
            "total_released": total_released,
            "total_expenses": total_expenses,
            "total_returns": total_returns,
            "recent_activities": AuditLog.objects.select_related("user")[:8],
        })

    # ==========================
    # 2. GOVERNOR DASHBOARD
    # ==========================
    elif role_name == "Governor":
        adviser_approved = FundRequest.objects.filter(
            status=FundRequest.RequestStatus.ADVISER_APPROVED
        ).select_related("requested_by", "item", "item__budget")

        submitted_requests = FundRequest.objects.filter(
            status=FundRequest.RequestStatus.SUBMITTED
        ).select_related("requested_by", "item", "item__budget")

        total_released = Disbursement.objects.aggregate(total=Sum("amount_released"))["total"] or 0
        total_budget = Budget.objects.filter(status=Budget.BudgetStatus.ACTIVE).aggregate(total=Sum("total_amount"))["total"] or 0

        context.update({
            "pending_governor_count": adviser_approved.count(),
            "adviser_approved_requests": adviser_approved[:5],
            "submitted_requests": submitted_requests[:5],
            "submitted_count": submitted_requests.count(),
            "total_authorized_requests": FundRequest.objects.filter(
                status__in=[FundRequest.RequestStatus.GOVERNOR_APPROVED, FundRequest.RequestStatus.RELEASED]
            ).count(),
            "total_active_budgets": Budget.objects.filter(status=Budget.BudgetStatus.ACTIVE).count(),
            "total_budget": total_budget,
            "total_released": total_released,
            "recent_approvals": Approval.objects.filter(approver=user).select_related("request")[:5],
        })

    # ==========================
    # 3. TREASURER DASHBOARD
    # ==========================
    elif role_name == "Treasurer":
        total_collected = Collection.objects.aggregate(total=Sum("amount"))["total"] or 0
        total_released = Disbursement.objects.aggregate(total=Sum("amount_released"))["total"] or 0
        total_returned = FundReturn.objects.aggregate(total=Sum("amount_returned"))["total"] or 0
        pending_releases = FundRequest.objects.filter(
            status=FundRequest.RequestStatus.GOVERNOR_APPROVED
        ).select_related("requested_by", "item")

        context.update({
            "total_collected": total_collected,
            "total_released": total_released,
            "total_returned": total_returned,
            "pending_releases_count": pending_releases.count(),
            "pending_releases": pending_releases[:5],
            "pending_turnovers": CollectionTurnover.objects.filter(
                status=CollectionTurnover.TurnoverStatus.PENDING
            ).count(),
            "disputed_turnovers": CollectionTurnover.objects.filter(
                status=CollectionTurnover.TurnoverStatus.DISPUTED
            ).count(),
            "recent_turnovers": CollectionTurnover.objects.select_related("submitted_by", "received_by")[:5],
            "recent_disbursements": Disbursement.objects.select_related("received_by", "request")[:5],
        })

    # ==========================
    # 4. AUDITOR DASHBOARD
    # ==========================
    elif role_name == "Auditor":
        total_collected = Collection.objects.aggregate(total=Sum("amount"))["total"] or 0
        total_budget = Budget.objects.filter(status=Budget.BudgetStatus.ACTIVE).aggregate(total=Sum("total_amount"))["total"] or 0
        total_released = Disbursement.objects.aggregate(total=Sum("amount_released"))["total"] or 0
        total_expenses = Liquidation.objects.aggregate(total=Sum("amount_spent"))["total"] or 0
        total_returns = FundReturn.objects.aggregate(total=Sum("amount_returned"))["total"] or 0
        remaining_cash = total_released - total_expenses - total_returns

        context.update({
            "total_collected": total_collected,
            "total_budget": total_budget,
            "total_released": total_released,
            "total_expenses": total_expenses,
            "total_returns": total_returns,
            "remaining_cash": remaining_cash,
            "disputed_turnovers_count": CollectionTurnover.objects.filter(
                status=CollectionTurnover.TurnoverStatus.DISPUTED
            ).count(),
            "recent_audit_logs": AuditLog.objects.select_related("user")[:10],
            "total_logs_count": AuditLog.objects.count(),
        })

    # ==========================
    # 5. OFFICER DASHBOARD
    # ==========================
    elif role_name == "Officer":
        my_requests = FundRequest.objects.filter(requested_by=user).select_related("item", "item__budget")
        my_disbursements = Disbursement.objects.filter(received_by=user).select_related("request")

        my_total_released = my_disbursements.aggregate(total=Sum("amount_released"))["total"] or 0
        my_total_expenses = Liquidation.objects.filter(recorded_by=user).aggregate(total=Sum("amount_spent"))["total"] or 0
        my_total_returns = FundReturn.objects.filter(returned_by=user).aggregate(total=Sum("amount_returned"))["total"] or 0
        my_remaining_cash = my_total_released - my_total_expenses - my_total_returns

        context.update({
            "my_requests_count": my_requests.count(),
            "my_drafts_count": my_requests.filter(status=FundRequest.RequestStatus.DRAFT).count(),
            "my_pending_count": my_requests.filter(
                status__in=[FundRequest.RequestStatus.SUBMITTED, FundRequest.RequestStatus.ADVISER_APPROVED]
            ).count(),
            "my_approved_count": my_requests.filter(
                status__in=[FundRequest.RequestStatus.GOVERNOR_APPROVED, FundRequest.RequestStatus.RELEASED]
            ).count(),
            "my_total_released": my_total_released,
            "my_total_expenses": my_total_expenses,
            "my_total_returns": my_total_returns,
            "my_remaining_cash": my_remaining_cash,
            "my_recent_requests": my_requests[:5],
            "my_disbursements": my_disbursements[:5],
        })

    # ==========================
    # 6. ADVISER DASHBOARD
    # ==========================
    elif role_name == "Adviser":
        pending_requests = FundRequest.objects.filter(
            status=FundRequest.RequestStatus.SUBMITTED
        ).select_related("requested_by", "item", "item__budget")

        notifications = ApprovalNotification.objects.filter(
            recipient=user
        ).select_related("request")

        context.update({
            "pending_requests_count": pending_requests.count(),
            "pending_requests": pending_requests[:5],
            "approved_by_me": Approval.objects.filter(
                approver=user, decision=Approval.Decision.APPROVED
            ).count(),
            "rejected_by_me": Approval.objects.filter(
                approver=user, decision=Approval.Decision.REJECTED
            ).count(),
            "notifications": notifications[:5],
            "unread_notifications_count": notifications.filter(is_read=False).count(),
        })

    # ==========================
    # 7. STUDENT DASHBOARD
    # ==========================
    elif role_name == "Student":
        student_obj = (
            Student.objects.filter(student_no__iexact=user.username).first()
            or Student.objects.filter(full_name__icontains=user.get_full_name()).first()
            or Student.objects.first()
        )

        obligations = []
        payments = []
        total_obligations_amount = 0
        total_paid_amount = 0
        remaining_balance = 0
        is_compliant = False

        if student_obj:
            obligations = CampaignObligation.objects.filter(student=student_obj).select_related(
                "campaign", "campaign__fee_type", "campaign__term"
            )
            payments = Collection.objects.filter(
                obligation__student=student_obj
            ).select_related("obligation__campaign", "collected_by")[:5]

            total_obligations_amount = sum(o.required_amount for o in obligations)
            total_paid_amount = sum(o.total_paid for o in obligations)
            remaining_balance = max(total_obligations_amount - total_paid_amount, 0)
            is_compliant = bool(obligations and remaining_balance == 0)

        context.update({
            "student_record": student_obj,
            "obligations": obligations,
            "total_obligations_amount": total_obligations_amount,
            "total_paid_amount": total_paid_amount,
            "remaining_balance": remaining_balance,
            "is_compliant": is_compliant,
            "payments": payments,
        })

    return render(request, template_name, context)


@login_required
def financial_overview_view(request):
    allowed_roles = ["Admin", "Governor", "Treasurer", "Auditor"]
    role_name = request.user.role.role_name if request.user.role else "Unassigned"

    if role_name not in allowed_roles:
        messages.error(
            request,
            "You are not authorized to access the Financial Overview."
        )
        return redirect("dashboard")

    total_collected = Collection.objects.aggregate(total=Sum("amount"))["total"] or 0
    total_budget = Budget.objects.filter(status=Budget.BudgetStatus.ACTIVE).aggregate(total=Sum("total_amount"))["total"] or 0
    total_released = Disbursement.objects.aggregate(total=Sum("amount_released"))["total"] or 0
    total_expenses = Liquidation.objects.aggregate(total=Sum("amount_spent"))["total"] or 0
    total_returns = FundReturn.objects.aggregate(total=Sum("amount_returned"))["total"] or 0
    remaining_cash = total_released - total_expenses - total_returns
    net_treasury_balance = total_collected + total_returns - total_released

    context = {
        "role_name": role_name,
        "current_term": AcademicTerm.objects.filter(is_current=True).first(),
        "total_collected": total_collected,
        "total_budget": total_budget,
        "total_released": total_released,
        "total_expenses": total_expenses,
        "total_returns": total_returns,
        "remaining_cash": remaining_cash,
        "net_treasury_balance": net_treasury_balance,
        "active_budgets": Budget.objects.filter(status=Budget.BudgetStatus.ACTIVE).prefetch_related("items"),
        "campaigns": CollectionCampaign.objects.select_related("fee_type", "term")[:8],
        "recent_disbursements": Disbursement.objects.select_related("received_by", "request")[:8],
    }

    return render(request, "accounts/financial_overview.html", context)


@login_required
def user_management_view(request):
    role_name = request.user.role.role_name if request.user.role else ("Admin" if request.user.is_superuser else "Unassigned")
    if role_name != "Admin" and not request.user.is_superuser:
        messages.error(request, "Access restricted to Administrators.")
        return redirect("dashboard")

    role_filter = request.GET.get("role", "").strip()
    search_query = request.GET.get("q", "").strip()

    users_qs = User.objects.select_related("role").order_by("role__role_name", "username")

    if role_filter:
        users_qs = users_qs.filter(role__role_name=role_filter)

    if search_query:
        users_qs = users_qs.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    from accounts.models import Role
    all_roles = Role.objects.all().order_by("role_name")

    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    student_users = User.objects.filter(role__role_name="Student").count()
    staff_users = User.objects.filter(is_staff=True).count()

    context = {
        "role_name": role_name,
        "users": users_qs,
        "all_roles": all_roles,
        "selected_role": role_filter,
        "search_query": search_query,
        "total_users": total_users,
        "active_users": active_users,
        "student_users": student_users,
        "staff_users": staff_users,
    }
    return render(request, "accounts/user_management.html", context)
