from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Sum, Q
from django.utils import timezone

from .models import (
    FeeType,
    CollectionCampaign,
    CampaignObligation,
    CollectionTurnover,
    Collection,
)
from fund_management.services import write_audit_log
from fund_management.models import AuditLog


def get_role_name(user):
    return user.role.role_name if user.role else "Unassigned"


@login_required
def collections_list(request):
    role = get_role_name(request.user)
    if role not in ["Admin", "Governor", "Treasurer", "Auditor", "Officer"]:
        messages.error(request, "Unauthorized access to collections.")
        return redirect("dashboard")

    campaign_filter = request.GET.get("campaign", "")
    search_query = request.GET.get("q", "").strip()

    collections_qs = Collection.objects.select_related(
        "obligation",
        "obligation__student",
        "obligation__campaign",
        "collected_by",
        "turnover",
    ).order_by("-payment_date", "-collection_id")

    if campaign_filter:
        collections_qs = collections_qs.filter(obligation__campaign_id=campaign_filter)

    if search_query:
        collections_qs = collections_qs.filter(
            Q(or_number__icontains=search_query)
            | Q(obligation__student__full_name__icontains=search_query)
            | Q(obligation__student__student_no__icontains=search_query)
            | Q(collected_by__username__icontains=search_query)
        )

    total_amount = collections_qs.aggregate(total=Sum("amount"))["total"] or 0

    context = {
        "role_name": role,
        "collections": collections_qs,
        "total_amount": total_amount,
        "campaigns": CollectionCampaign.objects.all(),
        "selected_campaign": campaign_filter,
        "search_query": search_query,
    }
    return render(request, "finance_collections/collections_list.html", context)


@login_required
def record_payment_view(request):
    role = get_role_name(request.user)
    if role not in ["Treasurer", "Admin"]:
        messages.error(request, "Only Treasurers can record collection payments.")
        return redirect("collections_list")

    obligations = CampaignObligation.objects.select_related(
        "student", "campaign"
    ).filter(campaign__status=CollectionCampaign.CampaignStatus.ACTIVE)

    if request.method == "POST":
        obligation_id = request.POST.get("obligation")
        amount_raw = request.POST.get("amount", "0")
        or_number = request.POST.get("or_number", "").strip()
        payment_date = request.POST.get("payment_date") or timezone.localdate().isoformat()

        try:
            amount = Decimal(amount_raw)
            if amount <= 0:
                raise ValidationError("Payment amount must be greater than zero.")

            obligation = get_object_or_404(CampaignObligation, pk=obligation_id)

            if amount > obligation.remaining_balance:
                raise ValidationError(
                    f"Payment cannot exceed remaining balance of PHP {obligation.remaining_balance:.2f}."
                )

            collection = Collection.objects.create(
                obligation=obligation,
                collected_by=request.user,
                amount=amount,
                or_number=or_number,
                payment_date=payment_date,
            )

            write_audit_log(
                request.user,
                AuditLog.ActionType.RECORD,
                "Collection",
                collection.collection_id,
                f"Treasurer recorded payment of PHP {amount} for {obligation.student.full_name} "
                f"under campaign '{obligation.campaign.campaign_name}'. OR: {or_number or 'None'}.",
            )

            messages.success(request, f"Payment of PHP {amount} recorded for {obligation.student.full_name}!")
            return redirect("collections_list")

        except Exception as e:
            messages.error(request, f"Error recording payment: {e}")

    context = {
        "role_name": role,
        "obligations": obligations,
        "today": timezone.localdate().isoformat(),
    }
    return render(request, "finance_collections/record_payment.html", context)


@login_required
def turnovers_list(request):
    role = get_role_name(request.user)
    if role not in ["Admin", "Governor", "Treasurer", "Auditor", "Officer"]:
        messages.error(request, "Unauthorized access to turnovers.")
        return redirect("dashboard")

    status_filter = request.GET.get("status", "")
    turnovers_qs = CollectionTurnover.objects.select_related(
        "submitted_by", "received_by"
    ).order_by("-submitted_at")

    if role == "Officer":
        turnovers_qs = turnovers_qs.filter(submitted_by=request.user)

    if status_filter:
        turnovers_qs = turnovers_qs.filter(status=status_filter)

    pending_count = CollectionTurnover.objects.filter(status=CollectionTurnover.TurnoverStatus.PENDING).count()
    disputed_count = CollectionTurnover.objects.filter(status=CollectionTurnover.TurnoverStatus.DISPUTED).count()

    context = {
        "role_name": role,
        "turnovers": turnovers_qs,
        "status_filter": status_filter,
        "pending_count": pending_count,
        "disputed_count": disputed_count,
        "statuses": CollectionTurnover.TurnoverStatus.choices,
    }
    return render(request, "finance_collections/turnovers_list.html", context)


@login_required
def turnover_submit_view(request):
    role = get_role_name(request.user)
    if role not in ["Officer", "Treasurer", "Admin"]:
        messages.error(request, "Unauthorized access.")
        return redirect("turnovers_list")

    if request.method == "POST":
        amount_raw = request.POST.get("declared_amount", "0")
        remarks = request.POST.get("remarks", "").strip()

        try:
            declared_amount = Decimal(amount_raw)
            if declared_amount <= 0:
                raise ValidationError("Declared amount must be greater than zero.")

            turnover = CollectionTurnover.objects.create(
                submitted_by=request.user,
                declared_amount=declared_amount,
                status=CollectionTurnover.TurnoverStatus.PENDING,
                remarks=remarks,
            )

            write_audit_log(
                request.user,
                AuditLog.ActionType.SUBMIT,
                "Collection Turnover",
                turnover.turnover_id,
                f"{role} submitted Collection Turnover #{turnover.turnover_id} declaring PHP {declared_amount}.",
            )

            messages.success(
                request,
                f"Turnover #{turnover.turnover_id} for PHP {declared_amount} submitted successfully! Awaiting Treasurer verification."
            )
            return redirect("turnovers_list")

        except Exception as e:
            messages.error(request, f"Error submitting turnover: {e}")

    context = {
        "role_name": role,
    }
    return render(request, "finance_collections/turnover_submit.html", context)


@login_required
def turnover_verify_view(request, turnover_id):
    role = get_role_name(request.user)
    if role not in ["Treasurer", "Admin"]:
        messages.error(request, "Only Treasurers can verify and receive turnovers.")
        return redirect("turnovers_list")

    turnover = get_object_or_404(CollectionTurnover, pk=turnover_id)

    if request.method == "POST":
        received_raw = request.POST.get("received_amount", "0")
        remarks = request.POST.get("remarks", "").strip()

        try:
            received_amount = Decimal(received_raw)
            if received_amount < 0:
                raise ValidationError("Received amount cannot be negative.")

            if received_amount != turnover.declared_amount and not remarks:
                raise ValidationError("Remarks are required when received amount differs from declared amount.")

            turnover.received_amount = received_amount
            turnover.received_by = request.user
            turnover.received_at = timezone.now()

            if received_amount == turnover.declared_amount:
                turnover.status = CollectionTurnover.TurnoverStatus.RECEIVED
            else:
                turnover.status = CollectionTurnover.TurnoverStatus.DISPUTED

            if remarks:
                turnover.remarks = remarks

            turnover.save()

            write_audit_log(
                request.user,
                AuditLog.ActionType.UPDATE,
                "Collection Turnover",
                turnover.turnover_id,
                f"Treasurer verified Turnover #{turnover.turnover_id}. Declared: PHP {turnover.declared_amount}, "
                f"Received: PHP {received_amount}. Status: {turnover.status}.",
            )

            messages.success(request, f"Turnover #{turnover.turnover_id} successfully verified as {turnover.status}!")
            return redirect("turnovers_list")

        except Exception as e:
            messages.error(request, f"Verification failed: {e}")

    context = {
        "role_name": role,
        "turnover": turnover,
    }
    return render(request, "finance_collections/turnover_verify.html", context)


@login_required
def campaigns_list(request):
    role = get_role_name(request.user)
    campaigns = CollectionCampaign.objects.select_related("fee_type", "term").prefetch_related("obligations")

    context = {
        "role_name": role,
        "campaigns": campaigns,
    }
    return render(request, "finance_collections/campaigns_list.html", context)
