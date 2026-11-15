from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError, PermissionDenied
from django.db.models import Q, Sum
from django.utils import timezone

from finance_budget.models import Budget, BudgetItem
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
from . import services

User = get_user_model()


def get_role_name(user):
    return user.role.role_name if user.role else "Unassigned"


@login_required
def fund_requests_list(request):
    role = get_role_name(request.user)
    if role not in ["Admin", "Governor", "Treasurer", "Auditor", "Officer", "Adviser"]:
        messages.error(request, "You do not have permission to view fund requests.")
        return redirect("dashboard")

    filter_type = request.GET.get("filter", "all")
    status_filter = request.GET.get("status", "")
    search_query = request.GET.get("q", "").strip()

    requests_qs = FundRequest.objects.select_related(
        "requested_by", "item", "item__budget", "item__category"
    )

    # Role-based default scopes
    if role == "Officer":
        # Officers default to seeing their own requests
        if filter_type != "all_college":
            requests_qs = requests_qs.filter(requested_by=request.user)
    elif role == "Adviser":
        if filter_type == "pending_adviser":
            requests_qs = requests_qs.filter(status=FundRequest.RequestStatus.SUBMITTED)
        elif filter_type == "reviewed_adviser":
            requests_qs = requests_qs.filter(
                approvals__approver=request.user,
                approvals__approval_stage=Approval.ApprovalStage.ADVISER
            ).distinct()
    elif role == "Governor":
        if filter_type == "pending_governor":
            requests_qs = requests_qs.filter(status=FundRequest.RequestStatus.ADVISER_APPROVED)
    elif role == "Treasurer":
        if filter_type == "ready_to_release":
            requests_qs = requests_qs.filter(status=FundRequest.RequestStatus.GOVERNOR_APPROVED)

    if status_filter:
        requests_qs = requests_qs.filter(status=status_filter)

    if search_query:
        requests_qs = requests_qs.filter(
            Q(purpose__icontains=search_query)
            | Q(requested_by__username__icontains=search_query)
            | Q(requested_by__first_name__icontains=search_query)
            | Q(requested_by__last_name__icontains=search_query)
            | Q(item__description__icontains=search_query)
        )

    context = {
        "role_name": role,
        "fund_requests": requests_qs,
        "filter_type": filter_type,
        "status_filter": status_filter,
        "search_query": search_query,
        "statuses": FundRequest.RequestStatus.choices,
    }
    return render(request, "fund_management/fund_requests_list.html", context)


@login_required
def fund_request_create(request):
    role = get_role_name(request.user)
    if role != "Officer":
        messages.error(request, "Only Officers can create and submit fund requests.")
        return redirect("dashboard")

    budget_items = BudgetItem.objects.filter(
        budget__status=Budget.BudgetStatus.ACTIVE
    ).select_related("budget", "category")

    if request.method == "POST":
        item_id = request.POST.get("item")
        purpose = request.POST.get("purpose", "").strip()
        amount_raw = request.POST.get("amount", "0")
        submit_action = request.POST.get("submit_action", "submit")

        try:
            amount = Decimal(amount_raw)
            if amount <= 0:
                raise ValidationError("Amount must be greater than zero.")

            item = get_object_or_404(BudgetItem, pk=item_id)

            fund_request = FundRequest.objects.create(
                item=item,
                requested_by=request.user,
                purpose=purpose,
                amount=amount,
                status=FundRequest.RequestStatus.DRAFT,
            )

            services.write_audit_log(
                request.user,
                AuditLog.ActionType.CREATE,
                "Fund Request",
                fund_request.request_id,
                f"Officer drafted Fund Request #{fund_request.request_id} for PHP {amount}.",
            )

            if submit_action == "submit_now":
                services.submit_fund_request(fund_request.request_id, request.user)
                messages.success(
                    request,
                    f"Fund Request #{fund_request.request_id} created and submitted to Adviser for review!"
                )
            else:
                messages.success(
                    request,
                    f"Fund Request #{fund_request.request_id} saved as Draft."
                )

            return redirect("fund_request_detail", request_id=fund_request.request_id)

        except (ValidationError, Exception) as e:
            messages.error(request, f"Error creating fund request: {e}")

    context = {
        "role_name": role,
        "budget_items": budget_items,
    }
    return render(request, "fund_management/fund_request_create.html", context)


@login_required
def fund_request_detail(request, request_id):
    role = get_role_name(request.user)
    fund_request = get_object_or_404(
        FundRequest.objects.select_related(
            "requested_by", "item", "item__budget", "item__category"
        ),
        pk=request_id
    )

    approvals = fund_request.approvals.select_related("approver").order_by("decided_at")
    disbursement = getattr(fund_request, "disbursement", None)

    disbursement_balance = None
    liquidations = []
    fund_returns = []
    if disbursement:
        disbursement_balance = services.get_disbursement_balance(disbursement.disbursement_id)
        liquidations = disbursement.liquidations.prefetch_related("receipts").order_by("-expense_date")
        fund_returns = disbursement.fund_returns.select_related("received_by").order_by("-return_date")

    context = {
        "role_name": role,
        "fund_request": fund_request,
        "approvals": approvals,
        "disbursement": disbursement,
        "disbursement_balance": disbursement_balance,
        "liquidations": liquidations,
        "fund_returns": fund_returns,
        "treasurers": User.objects.filter(role__role_name="Treasurer", is_active=True),
    }
    return render(request, "fund_management/fund_request_detail.html", context)


@login_required
def fund_request_submit(request, request_id):
    if request.method != "POST":
        return redirect("fund_request_detail", request_id=request_id)

    try:
        services.submit_fund_request(request_id, request.user)
        messages.success(request, f"Fund Request #{request_id} has been submitted for Adviser review.")
    except Exception as e:
        messages.error(request, f"Submission failed: {e}")

    return redirect("fund_request_detail", request_id=request_id)


@login_required
def fund_request_adviser_review(request, request_id):
    if request.method != "POST":
        return redirect("fund_request_detail", request_id=request_id)

    decision = request.POST.get("decision")
    remarks = request.POST.get("remarks", "").strip()

    try:
        services.adviser_review_request(request_id, request.user, decision, remarks)
        messages.success(request, f"Fund Request #{request_id} has been marked as {decision}.")
    except Exception as e:
        messages.error(request, f"Adviser review failed: {e}")

    return redirect("fund_request_detail", request_id=request_id)


@login_required
def fund_request_governor_review(request, request_id):
    if request.method != "POST":
        return redirect("fund_request_detail", request_id=request_id)

    decision = request.POST.get("decision")
    remarks = request.POST.get("remarks", "").strip()
    bypass_adviser = request.POST.get("bypass_adviser") == "on"
    bypass_reason = request.POST.get("bypass_reason", "").strip()

    try:
        services.governor_review_request(
            request_id=request_id,
            user=request.user,
            decision=decision,
            remarks=remarks,
            bypass_adviser=bypass_adviser,
            bypass_reason=bypass_reason,
        )
        if bypass_adviser:
            messages.warning(
                request,
                f"Fund Request #{request_id} {decision} with Adviser Bypass. Adviser was notified."
            )
        else:
            messages.success(request, f"Fund Request #{request_id} has been {decision} by Governor.")
    except Exception as e:
        messages.error(request, f"Governor review failed: {e}")

    return redirect("fund_request_detail", request_id=request_id)


@login_required
def fund_request_release(request, request_id):
    if request.method != "POST":
        return redirect("fund_request_detail", request_id=request_id)

    voucher_number = request.POST.get("voucher_number", "").strip()
    remarks = request.POST.get("remarks", "").strip()

    try:
        disbursement = services.release_fund_request(
            request_id=request_id,
            user=request.user,
            voucher_number=voucher_number,
            remarks=remarks,
        )
        messages.success(
            request,
            f"Funds for Request #{request_id} released successfully! Disbursement #{disbursement.disbursement_id} generated."
        )
    except Exception as e:
        messages.error(request, f"Fund release failed: {e}")

    return redirect("fund_request_detail", request_id=request_id)


@login_required
def disbursements_list(request):
    role = get_role_name(request.user)
    if role not in ["Admin", "Governor", "Treasurer", "Auditor", "Officer"]:
        messages.error(request, "You do not have permission to view disbursements.")
        return redirect("dashboard")

    disbursements_qs = Disbursement.objects.select_related(
        "request", "released_by", "received_by", "request__item"
    )

    if role == "Officer":
        disbursements_qs = disbursements_qs.filter(received_by=request.user)

    search_query = request.GET.get("q", "").strip()
    if search_query:
        disbursements_qs = disbursements_qs.filter(
            Q(voucher_number__icontains=search_query)
            | Q(received_by__username__icontains=search_query)
            | Q(request__purpose__icontains=search_query)
        )

    disbursement_rows = []
    for d in disbursements_qs:
        bal = services.get_disbursement_balance(d.disbursement_id)
        disbursement_rows.append({
            "disbursement": d,
            "balance": bal,
        })

    pending_releases = None
    if role == "Treasurer":
        pending_releases = FundRequest.objects.filter(
            status=FundRequest.RequestStatus.GOVERNOR_APPROVED
        ).select_related("requested_by", "item")

    context = {
        "role_name": role,
        "disbursement_rows": disbursement_rows,
        "pending_releases": pending_releases,
        "search_query": search_query,
    }
    return render(request, "fund_management/disbursements_list.html", context)


@login_required
def record_liquidation_view(request, disbursement_id):
    role = get_role_name(request.user)
    if role != "Officer":
        messages.error(request, "Only Officers can record liquidations.")
        return redirect("dashboard")

    disbursement = get_object_or_404(Disbursement, pk=disbursement_id)
    if disbursement.received_by_id != request.user.pk:
        messages.error(request, "You can only record expenses for funds released to you.")
        return redirect("disbursements_list")

    if request.method == "POST":
        expense_description = request.POST.get("expense_description", "").strip()
        amount_spent_raw = request.POST.get("amount_spent", "0")
        expense_date = request.POST.get("expense_date") or timezone.localdate().isoformat()
        remarks = request.POST.get("remarks", "").strip()

        # Receipt info
        receipt_number = request.POST.get("receipt_number", "").strip()
        vendor_name = request.POST.get("vendor_name", "").strip()

        try:
            amount_spent = Decimal(amount_spent_raw)
            if amount_spent <= 0:
                raise ValidationError("Amount spent must be greater than zero.")

            liquidation = services.record_liquidation(
                disbursement_id=disbursement_id,
                user=request.user,
                expense_description=expense_description,
                amount_spent=amount_spent,
                expense_date=expense_date,
                remarks=remarks,
            )

            if receipt_number:
                services.record_liquidation_receipt(
                    liquidation_id=liquidation.liquidation_id,
                    user=request.user,
                    receipt_number=receipt_number,
                    receipt_date=expense_date,
                    vendor_name=vendor_name,
                    remarks=remarks,
                )

            messages.success(request, f"Liquidation expense of PHP {amount_spent} recorded successfully!")
            return redirect("fund_request_detail", request_id=disbursement.request_id)

        except Exception as e:
            messages.error(request, f"Failed to record liquidation: {e}")

    balance = services.get_disbursement_balance(disbursement_id)
    context = {
        "role_name": role,
        "disbursement": disbursement,
        "balance": balance,
        "today": timezone.localdate().isoformat(),
    }
    return render(request, "fund_management/record_liquidation.html", context)


@login_required
def record_fund_return_view(request, disbursement_id):
    role = get_role_name(request.user)
    if role != "Officer":
        messages.error(request, "Only Officers can return funds.")
        return redirect("dashboard")

    disbursement = get_object_or_404(Disbursement, pk=disbursement_id)
    if disbursement.received_by_id != request.user.pk:
        messages.error(request, "You can only return funds assigned to you.")
        return redirect("disbursements_list")

    treasurers = User.objects.filter(role__role_name="Treasurer", is_active=True)

    if request.method == "POST":
        treasurer_id = request.POST.get("treasurer")
        amount_raw = request.POST.get("amount_returned", "0")
        return_date = request.POST.get("return_date") or timezone.localdate().isoformat()
        remarks = request.POST.get("remarks", "").strip()

        try:
            treasurer = get_object_or_404(User, pk=treasurer_id)
            amount_returned = Decimal(amount_raw)

            fund_return = services.record_fund_return(
                disbursement_id=disbursement_id,
                user=request.user,
                treasurer=treasurer,
                amount_returned=amount_returned,
                return_date=return_date,
                remarks=remarks,
            )

            messages.success(
                request,
                f"Successfully returned PHP {amount_returned} to Treasurer {treasurer.get_full_name() or treasurer.username}!"
            )
            return redirect("fund_request_detail", request_id=disbursement.request_id)

        except Exception as e:
            messages.error(request, f"Failed to record fund return: {e}")

    balance = services.get_disbursement_balance(disbursement_id)
    context = {
        "role_name": role,
        "disbursement": disbursement,
        "balance": balance,
        "treasurers": treasurers,
        "today": timezone.localdate().isoformat(),
    }
    return render(request, "fund_management/record_return.html", context)


@login_required
def liquidations_list(request):
    role = get_role_name(request.user)
    if role not in ["Admin", "Governor", "Treasurer", "Auditor", "Officer"]:
        messages.error(request, "Unauthorized access.")
        return redirect("dashboard")

    liquidations_qs = Liquidation.objects.select_related(
        "disbursement", "recorded_by", "disbursement__request"
    ).prefetch_related("receipts").order_by("-expense_date")

    if role == "Officer":
        liquidations_qs = liquidations_qs.filter(recorded_by=request.user)

    context = {
        "role_name": role,
        "liquidations": liquidations_qs,
    }
    return render(request, "fund_management/liquidations_list.html", context)


@login_required
def returns_list(request):
    role = get_role_name(request.user)
    if role not in ["Admin", "Governor", "Treasurer", "Auditor", "Officer"]:
        messages.error(request, "Unauthorized access.")
        return redirect("dashboard")

    returns_qs = FundReturn.objects.select_related(
        "disbursement", "returned_by", "received_by", "disbursement__request"
    ).order_by("-return_date")

    if role == "Officer":
        returns_qs = returns_qs.filter(returned_by=request.user)

    context = {
        "role_name": role,
        "returns": returns_qs,
    }
    return render(request, "fund_management/returns_list.html", context)


@login_required
def approvals_list(request):
    role = get_role_name(request.user)
    if role not in ["Admin", "Governor", "Auditor", "Adviser"]:
        messages.error(request, "Unauthorized access.")
        return redirect("dashboard")

    approvals_qs = Approval.objects.select_related(
        "request", "approver", "request__requested_by"
    ).order_by("-decided_at")

    if role in ["Governor", "Adviser"]:
        approvals_qs = approvals_qs.filter(approval_stage=role)

    context = {
        "role_name": role,
        "approvals": approvals_qs,
    }
    return render(request, "fund_management/approvals_list.html", context)


@login_required
def notifications_list(request):
    role = get_role_name(request.user)
    if role not in ["Adviser", "Admin"]:
        messages.error(request, "Unauthorized access.")
        return redirect("dashboard")

    notifications_qs = ApprovalNotification.objects.filter(
        recipient=request.user
    ).select_related("request").order_by("-created_at")

    if request.method == "POST":
        notif_id = request.POST.get("notification_id")
        if notif_id:
            ApprovalNotification.objects.filter(pk=notif_id, recipient=request.user).update(is_read=True)
            messages.success(request, "Notification marked as read.")
        elif request.POST.get("mark_all_read"):
            ApprovalNotification.objects.filter(recipient=request.user).update(is_read=True)
            messages.success(request, "All notifications marked as read.")
        return redirect("notifications_list")

    context = {
        "role_name": role,
        "notifications": notifications_qs,
    }
    return render(request, "fund_management/notifications_list.html", context)


@login_required
def audit_logs_view(request):
    role = get_role_name(request.user)
    if role not in ["Admin", "Auditor"]:
        messages.error(request, "Audit logs are only accessible to Administrators and Auditors.")
        return redirect("dashboard")

    action_filter = request.GET.get("action", "")
    module_filter = request.GET.get("module", "")
    search_query = request.GET.get("q", "").strip()

    logs_qs = AuditLog.objects.select_related("user").order_by("-timestamp")

    if action_filter:
        logs_qs = logs_qs.filter(action=action_filter)
    if module_filter:
        logs_qs = logs_qs.filter(module=module_filter)
    if search_query:
        logs_qs = logs_qs.filter(
            Q(description__icontains=search_query)
            | Q(record_id__icontains=search_query)
            | Q(user__username__icontains=search_query)
            | Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
        )

    context = {
        "role_name": role,
        "audit_logs": logs_qs[:100],
        "action_choices": AuditLog.ActionType.choices,
        "modules": AuditLog.objects.values_list("module", flat=True).distinct(),
        "action_filter": action_filter,
        "module_filter": module_filter,
        "search_query": search_query,
        "total_count": logs_qs.count(),
    }
    return render(request, "fund_management/audit_logs.html", context)
