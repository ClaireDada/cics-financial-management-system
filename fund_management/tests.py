from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied

from accounts.models import Role
from students.models import AcademicTerm
from finance_budget.models import Budget, BudgetItem, ExpenseCategory
from fund_management.models import (
    FundRequest,
    Approval,
    ApprovalNotification,
    Disbursement,
    Liquidation,
    FundReturn,
    AuditLog,
)
from fund_management import services

User = get_user_model()


class FundManagementTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.officer_role = Role.objects.create(role_name="Officer")
        self.adviser_role = Role.objects.create(role_name="Adviser")
        self.governor_role = Role.objects.create(role_name="Governor")
        self.treasurer_role = Role.objects.create(role_name="Treasurer")
        self.auditor_role = Role.objects.create(role_name="Auditor")

        self.officer = User.objects.create_user(
            username="officer1", email="off1@cics.edu", password="admin123", role=self.officer_role
        )
        self.adviser = User.objects.create_user(
            username="adviser1", email="adv1@cics.edu", password="admin123", role=self.adviser_role
        )
        self.governor = User.objects.create_user(
            username="governor1", email="gov1@cics.edu", password="admin123", role=self.governor_role
        )
        self.treasurer = User.objects.create_user(
            username="treasurer1", email="treas1@cics.edu", password="admin123", role=self.treasurer_role
        )
        self.auditor = User.objects.create_user(
            username="auditor1", email="audit1@cics.edu", password="admin123", role=self.auditor_role
        )

        self.term = AcademicTerm.objects.create(
            school_year="2026-2027", semester="1st Semester", is_current=True
        )

        self.budget = Budget.objects.create(
            term=self.term,
            prepared_by=self.treasurer,
            title="CICS Budget 2026-2027",
            total_amount=Decimal("50000.00"),
            status=Budget.BudgetStatus.ACTIVE,
        )

        self.category = ExpenseCategory.objects.create(
            category_name="Event Supplies",
            description="Supplies for student events"
        )

        self.item = BudgetItem.objects.create(
            budget=self.budget,
            category=self.category,
            description="Paper and ID badges",
            allocated_amount=Decimal("10000.00"),
        )

    def test_full_lifecycle_standard(self):
        # 1. Officer creates a draft fund request
        req = FundRequest.objects.create(
            item=self.item,
            requested_by=self.officer,
            purpose="Badge printing for orientation",
            amount=Decimal("1200.00"),
            status=FundRequest.RequestStatus.DRAFT,
        )
        self.assertEqual(req.status, FundRequest.RequestStatus.DRAFT)

        # 2. Officer submits the request
        services.submit_fund_request(req.request_id, self.officer)
        req.refresh_from_db()
        self.assertEqual(req.status, FundRequest.RequestStatus.SUBMITTED)

        # 3. Adviser reviews and approves
        services.adviser_review_request(
            req.request_id,
            self.adviser,
            decision=Approval.Decision.APPROVED,
            remarks="Recommended for funding."
        )
        req.refresh_from_db()
        self.assertEqual(req.status, FundRequest.RequestStatus.ADVISER_APPROVED)

        # 4. Governor reviews and approves
        services.governor_review_request(
            req.request_id,
            self.governor,
            decision=Approval.Decision.APPROVED,
            remarks="Approved by Governor."
        )
        req.refresh_from_db()
        self.assertEqual(req.status, FundRequest.RequestStatus.GOVERNOR_APPROVED)

        # 5. Treasurer releases funds
        disbursement = services.release_fund_request(
            req.request_id,
            self.treasurer,
            voucher_number="VOUCHER-TEST-001",
            remarks="Cash released."
        )
        req.refresh_from_db()
        self.assertEqual(req.status, FundRequest.RequestStatus.RELEASED)
        self.assertEqual(disbursement.amount_released, Decimal("1200.00"))

        # 6. Officer records liquidation
        liquidation = services.record_liquidation(
            disbursement.disbursement_id,
            self.officer,
            expense_description="Paper and toner cartridge",
            amount_spent=Decimal("950.00"),
            expense_date="2026-11-13",
            remarks="Receipt attached",
        )
        services.record_liquidation_receipt(
            liquidation.liquidation_id,
            self.officer,
            receipt_number="RECEIPT-001",
            receipt_date="2026-11-13",
            vendor_name="National Bookstore",
        )

        # 7. Officer returns unspent balance
        balance_before = services.get_disbursement_balance(disbursement.disbursement_id)
        self.assertEqual(balance_before["remaining_cash"], Decimal("250.00"))

        fund_return = services.record_fund_return(
            disbursement.disbursement_id,
            self.officer,
            self.treasurer,
            amount_returned=Decimal("250.00"),
            return_date="2026-11-13",
            remarks="Full remaining balance returned",
        )
        self.assertEqual(fund_return.amount_returned, Decimal("250.00"))

        # 8. Check final balance is zero
        balance_after = services.get_disbursement_balance(disbursement.disbursement_id)
        self.assertEqual(balance_after["remaining_cash"], Decimal("0.00"))

        # 9. Verify AuditLog entries were generated
        logs = AuditLog.objects.filter(record_id=str(req.request_id))
        self.assertTrue(logs.exists())

    def test_governor_bypass_protocol(self):
        # 1. Officer creates and submits request
        req = FundRequest.objects.create(
            item=self.item,
            requested_by=self.officer,
            purpose="Emergency supplies",
            amount=Decimal("500.00"),
            status=FundRequest.RequestStatus.SUBMITTED,
        )

        # 2. Governor bypasses Adviser with justification
        services.governor_review_request(
            request_id=req.request_id,
            user=self.governor,
            decision=Approval.Decision.APPROVED,
            remarks="Approved urgently",
            bypass_adviser=True,
            bypass_reason="Adviser attending academic conference; immediate procurement required.",
        )
        req.refresh_from_db()
        self.assertEqual(req.status, FundRequest.RequestStatus.GOVERNOR_APPROVED)

        # 3. Verify notification created for Adviser
        notif = ApprovalNotification.objects.filter(
            request=req, recipient=self.adviser
        ).first()
        self.assertIsNotNone(notif)
        self.assertIn("Adviser attending academic conference", notif.message)

    def test_governor_bypass_requires_reason(self):
        req = FundRequest.objects.create(
            item=self.item,
            requested_by=self.officer,
            purpose="Emergency supplies",
            amount=Decimal("500.00"),
            status=FundRequest.RequestStatus.SUBMITTED,
        )

        with self.assertRaises(ValidationError):
            services.governor_review_request(
                request_id=req.request_id,
                user=self.governor,
                decision=Approval.Decision.APPROVED,
                remarks="Approved",
                bypass_adviser=True,
                bypass_reason="",  # Empty reason must raise ValidationError
            )

    def test_fund_return_cannot_exceed_remaining_cash(self):
        req = FundRequest.objects.create(
            item=self.item,
            requested_by=self.officer,
            purpose="General supplies",
            amount=Decimal("1000.00"),
            status=FundRequest.RequestStatus.GOVERNOR_APPROVED,
        )
        disb = services.release_fund_request(
            req.request_id, self.treasurer, voucher_number="VR-TEST-ERR"
        )
        services.record_liquidation(
            disb.disbursement_id,
            self.officer,
            "Supplies",
            Decimal("800.00"),
            "2026-11-13"
        )
        # Remaining cash is 200.00. Attempting to return 300.00 must fail.
        with self.assertRaises(ValidationError):
            services.record_fund_return(
                disb.disbursement_id,
                self.officer,
                self.treasurer,
                Decimal("300.00"),
                "2026-11-13"
            )
