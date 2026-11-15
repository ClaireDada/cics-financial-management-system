
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Sum

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


def get_user_role(user):
    if not user.is_authenticated or not user.is_active:
        raise PermissionDenied("Your account is not active.")

    if not user.role:
        raise PermissionDenied("Your account has no assigned role.")

    return user.role.role_name


def write_audit_log(user, action, module, record_id, description):
    """
    Creates a permanent audit record for a system activity.
    Call this inside the business operation's transaction.
    """
    return AuditLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        module=module,
        record_id=str(record_id),
        description=description,
    )


@transaction.atomic
def submit_fund_request(request_id, user):
    role = get_user_role(user)

    if role != "Officer":
        raise PermissionDenied("Only Officers can submit fund requests.")

    fund_request = FundRequest.objects.select_for_update().get(
        request_id=request_id
    )

    if fund_request.requested_by_id != user.pk:
        raise PermissionDenied("You can only submit your own request.")

    if fund_request.status != FundRequest.RequestStatus.DRAFT:
        raise ValidationError("Only Draft requests can be submitted.")

    fund_request.status = FundRequest.RequestStatus.SUBMITTED
    fund_request.save(update_fields=["status"])

    write_audit_log(
        user,
        AuditLog.ActionType.SUBMIT,
        "Fund Request",
        fund_request.request_id,
        f"Officer submitted Fund Request #{fund_request.request_id} "
        f"for PHP {fund_request.amount}.",
    )

    return fund_request


@transaction.atomic
def adviser_review_request(request_id, user, decision, remarks=""):
    role = get_user_role(user)

    if role != "Adviser":
        raise PermissionDenied("Only the Adviser can review this request.")

    if decision not in [
        Approval.Decision.APPROVED,
        Approval.Decision.REJECTED,
    ]:
        raise ValidationError("Invalid approval decision.")

    fund_request = FundRequest.objects.select_for_update().get(
        request_id=request_id
    )

    if fund_request.status != FundRequest.RequestStatus.SUBMITTED:
        raise ValidationError(
            "Only submitted requests can be reviewed by the Adviser."
        )

    Approval.objects.create(
        request=fund_request,
        approver=user,
        approval_stage=Approval.ApprovalStage.ADVISER,
        decision=decision,
        remarks=remarks,
    )

    if decision == Approval.Decision.APPROVED:
        fund_request.status = FundRequest.RequestStatus.ADVISER_APPROVED
        action = AuditLog.ActionType.APPROVE
    else:
        fund_request.status = FundRequest.RequestStatus.REJECTED
        action = AuditLog.ActionType.REJECT

    fund_request.save(update_fields=["status"])

    write_audit_log(
        user,
        action,
        "Fund Request",
        fund_request.request_id,
        f"Adviser {decision.lower()} Fund Request "
        f"#{fund_request.request_id}. Remarks: {remarks or 'None'}",
    )

    return fund_request


@transaction.atomic
def governor_review_request(
    request_id,
    user,
    decision,
    remarks="",
    bypass_adviser=False,
    bypass_reason="",
):
    role = get_user_role(user)

    if role != "Governor":
        raise PermissionDenied("Only the Governor can review this request.")

    if decision not in [
        Approval.Decision.APPROVED,
        Approval.Decision.REJECTED,
    ]:
        raise ValidationError("Invalid approval decision.")

    if bypass_adviser and not bypass_reason.strip():
        raise ValidationError(
            "A reason is required when bypassing the Adviser."
        )

    fund_request = FundRequest.objects.select_for_update().get(
        request_id=request_id
    )

    if not bypass_adviser:
        if fund_request.status != (
            FundRequest.RequestStatus.ADVISER_APPROVED
        ):
            raise ValidationError(
                "The Adviser must approve this request first."
            )
    else:
        if fund_request.status != FundRequest.RequestStatus.SUBMITTED:
            raise ValidationError(
                "Only submitted requests can bypass Adviser approval."
            )

        User = get_user_model()

        advisers = User.objects.filter(
            role__role_name="Adviser",
            is_active=True,
        )

        if not advisers.exists():
            raise ValidationError(
                "No active Adviser account exists to receive the notification."
            )

    Approval.objects.create(
        request=fund_request,
        approver=user,
        approval_stage=Approval.ApprovalStage.GOVERNOR,
        decision=decision,
        remarks=remarks,
        adviser_bypassed=bypass_adviser,
        bypass_reason=bypass_reason if bypass_adviser else "",
    )

    if decision == Approval.Decision.APPROVED:
        fund_request.status = FundRequest.RequestStatus.GOVERNOR_APPROVED
        action = AuditLog.ActionType.APPROVE
    else:
        fund_request.status = FundRequest.RequestStatus.REJECTED
        action = AuditLog.ActionType.REJECT

    fund_request.save(update_fields=["status"])

    if bypass_adviser:
        for adviser in advisers:
            ApprovalNotification.objects.create(
                request=fund_request,
                recipient=adviser,
                message=(
                    f"The Governor reviewed Fund Request "
                    f"#{fund_request.request_id} without Adviser approval. "
                    f"Reason: {bypass_reason}"
                ),
            )

    description = (
        f"Governor {decision.lower()} Fund Request "
        f"#{fund_request.request_id}."
    )

    if bypass_adviser:
        description += (
            f" Adviser approval was bypassed. Reason: {bypass_reason}"
        )

    description += f" Remarks: {remarks or 'None'}"

    write_audit_log(
        user,
        action,
        "Fund Request",
        fund_request.request_id,
        description,
    )

    return fund_request


@transaction.atomic
def release_fund_request(
    request_id,
    user,
    voucher_number,
    remarks="",
):
    role = get_user_role(user)

    if role != "Treasurer":
        raise PermissionDenied(
            "Only the Treasurer can release funds."
        )

    if not voucher_number or not voucher_number.strip():
        raise ValidationError("A voucher number is required.")

    fund_request = FundRequest.objects.select_for_update().get(
        request_id=request_id
    )

    if fund_request.status != (
        FundRequest.RequestStatus.GOVERNOR_APPROVED
    ):
        raise ValidationError(
            "Only Governor-approved requests can be released."
        )

    if Disbursement.objects.filter(request=fund_request).exists():
        raise ValidationError(
            "This request has already been released."
        )

    if (
        not fund_request.requested_by.role
        or fund_request.requested_by.role.role_name != "Officer"
    ):
        raise ValidationError(
            "Funds can only be released to the requesting Officer."
        )

    disbursement = Disbursement.objects.create(
        request=fund_request,
        released_by=user,
        received_by=fund_request.requested_by,
        amount_released=fund_request.amount,
        voucher_number=voucher_number.strip(),
        remarks=remarks,
    )

    fund_request.status = FundRequest.RequestStatus.RELEASED
    fund_request.save(update_fields=["status"])

    write_audit_log(
        user,
        AuditLog.ActionType.RELEASE,
        "Disbursement",
        disbursement.disbursement_id,
        f"Treasurer released PHP {disbursement.amount_released} "
        f"to {disbursement.received_by} for Fund Request "
        f"#{fund_request.request_id}. "
        f"Voucher: {disbursement.voucher_number}.",
    )

    return disbursement


@transaction.atomic
def record_liquidation(
    disbursement_id,
    user,
    expense_description,
    amount_spent,
    expense_date,
    remarks="",
):
    role = get_user_role(user)

    if role != "Officer":
        raise PermissionDenied(
            "Only Officers can record liquidation expenses."
        )

    if not expense_description.strip():
        raise ValidationError("Expense description is required.")

    disbursement = Disbursement.objects.select_for_update().get(
        disbursement_id=disbursement_id
    )

    if disbursement.received_by_id != user.pk:
        raise PermissionDenied(
            "You can only record expenses for funds received by you."
        )

    liquidation = Liquidation.objects.create(
        disbursement=disbursement,
        recorded_by=user,
        expense_description=expense_description.strip(),
        amount_spent=amount_spent,
        expense_date=expense_date,
        remarks=remarks,
    )

    write_audit_log(
        user,
        AuditLog.ActionType.RECORD,
        "Liquidation",
        liquidation.liquidation_id,
        f"Officer recorded expense '{liquidation.expense_description}' "
        f"amounting to PHP {liquidation.amount_spent} "
        f"under Disbursement #{disbursement.disbursement_id}.",
    )

    return liquidation


def get_disbursement_balance(disbursement_id):
    disbursement = Disbursement.objects.get(
        disbursement_id=disbursement_id
    )

    total_expenses = (
        disbursement.liquidations.aggregate(
            total=Sum("amount_spent")
        )["total"] or 0
    )

    total_returns = (
        disbursement.fund_returns.aggregate(
            total=Sum("amount_returned")
        )["total"] or 0
    )

    remaining_cash = (
        disbursement.amount_released
        - total_expenses
        - total_returns
    )

    return {
        "amount_released": disbursement.amount_released,
        "total_expenses": total_expenses,
        "total_returns": total_returns,
        "remaining_cash": remaining_cash,
        "is_over_budget": remaining_cash < 0,
    }


@transaction.atomic
def record_fund_return(
    disbursement_id,
    user,
    treasurer,
    amount_returned,
    return_date,
    remarks="",
):
    role = get_user_role(user)

    if role != "Officer":
        raise PermissionDenied(
            "Only Officers can return unused funds."
        )

    if not treasurer.is_authenticated or not treasurer.is_active:
        raise ValidationError("The receiving Treasurer account is inactive.")

    if not treasurer.role or treasurer.role.role_name != "Treasurer":
        raise ValidationError(
            "Returned funds must be received by a Treasurer."
        )

    disbursement = Disbursement.objects.select_for_update().get(
        disbursement_id=disbursement_id
    )

    if disbursement.received_by_id != user.pk:
        raise PermissionDenied(
            "You can only return funds assigned to you."
        )

    if amount_returned <= 0:
        raise ValidationError("The returned amount must be greater than zero.")

    balance = get_disbursement_balance(disbursement_id)

    if amount_returned > balance["remaining_cash"]:
        raise ValidationError(
            "The returned amount cannot exceed the remaining cash."
        )

    fund_return = FundReturn.objects.create(
        disbursement=disbursement,
        returned_by=user,
        received_by=treasurer,
        amount_returned=amount_returned,
        return_date=return_date,
        remarks=remarks,
    )

    write_audit_log(
        user,
        AuditLog.ActionType.RETURN,
        "Fund Return",
        fund_return.return_id,
        f"Officer returned PHP {fund_return.amount_returned} "
        f"to Treasurer {treasurer} for Disbursement "
        f"#{disbursement.disbursement_id}.",
    )

    return fund_return


@transaction.atomic
def record_liquidation_receipt(
    liquidation_id,
    user,
    receipt_number,
    receipt_date,
    vendor_name="",
    remarks="",
):
    role = get_user_role(user)

    if role != "Officer":
        raise PermissionDenied(
            "Only Officers can record liquidation receipts."
        )

    if not receipt_number or not receipt_number.strip():
        raise ValidationError("Receipt number is required.")

    liquidation = Liquidation.objects.select_for_update().get(
        liquidation_id=liquidation_id
    )

    if liquidation.recorded_by_id != user.pk:
        raise PermissionDenied(
            "You can only add receipts to expenses recorded by you."
        )

    receipt = LiquidationReceipt.objects.create(
        liquidation=liquidation,
        receipt_number=receipt_number.strip(),
        receipt_date=receipt_date,
        vendor_name=vendor_name.strip(),
        remarks=remarks,
    )

    write_audit_log(
        user,
        AuditLog.ActionType.RECORD,
        "Liquidation Receipt",
        receipt.receipt_id,
        f"Officer recorded receipt {receipt.receipt_number} "
        f"for Liquidation #{liquidation.liquidation_id}. "
        f"Vendor: {receipt.vendor_name or 'Not specified'}.",
    )

    return receipt
