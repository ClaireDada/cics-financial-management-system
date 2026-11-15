from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from accounts.models import Role
from students.models import Student, AcademicTerm
from finance_collections.models import (
    FeeType,
    CollectionCampaign,
    CampaignObligation,
    CollectionTurnover,
    Collection,
)

User = get_user_model()


class CollectionsTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.treasurer_role = Role.objects.create(role_name="Treasurer")
        self.officer_role = Role.objects.create(role_name="Officer")

        self.treasurer = User.objects.create_user(
            username="treas1", email="t1@cics.edu", password="admin123", role=self.treasurer_role
        )
        self.officer = User.objects.create_user(
            username="off1", email="o1@cics.edu", password="admin123", role=self.officer_role
        )

        self.term = AcademicTerm.objects.create(
            school_year="2026-2027", semester="1st Semester", is_current=True
        )

        self.fee_type = FeeType.objects.create(
            fee_name="Membership Fee", default_amount=Decimal("150.00")
        )

        self.campaign = CollectionCampaign.objects.create(
            campaign_name="1st Sem Membership Drive",
            fee_type=self.fee_type,
            term=self.term,
            start_date="2026-08-01",
            end_date="2026-12-15",
            status=CollectionCampaign.CampaignStatus.ACTIVE,
        )

        self.student = Student.objects.create(
            student_no="2026-0001",
            full_name="Alex Santos",
            program="BSCS",
            year_level=2,
            section="A",
        )

        self.obligation = CampaignObligation.objects.create(
            campaign=self.campaign,
            student=self.student,
            required_amount=Decimal("150.00"),
        )

    def test_record_payment_and_compliance(self):
        self.assertEqual(self.obligation.compliance_status, "Not Complied")
        self.assertEqual(self.obligation.remaining_balance, Decimal("150.00"))

        # Pay partial: 50.00
        payment1 = Collection.objects.create(
            obligation=self.obligation,
            collected_by=self.treasurer,
            amount=Decimal("50.00"),
            or_number="OR-001",
            payment_date="2026-11-13",
        )
        self.assertEqual(self.obligation.total_paid, Decimal("50.00"))
        self.assertEqual(self.obligation.remaining_balance, Decimal("100.00"))
        self.assertEqual(self.obligation.compliance_status, "Not Complied")

        # Pay remaining: 100.00
        payment2 = Collection.objects.create(
            obligation=self.obligation,
            collected_by=self.treasurer,
            amount=Decimal("100.00"),
            or_number="OR-002",
            payment_date="2026-11-13",
        )
        self.assertEqual(self.obligation.total_paid, Decimal("150.00"))
        self.assertEqual(self.obligation.remaining_balance, Decimal("0.00"))
        self.assertEqual(self.obligation.compliance_status, "Complied")

    def test_turnover_matching_and_disputed(self):
        self.client.force_login(self.treasurer)

        # 1. Matching turnover -> Received
        turnover1 = CollectionTurnover.objects.create(
            submitted_by=self.officer,
            declared_amount=Decimal("1000.00"),
            status=CollectionTurnover.TurnoverStatus.PENDING,
        )

        res = self.client.post(
            reverse("turnover_verify", kwargs={"turnover_id": turnover1.turnover_id}),
            {"received_amount": "1000.00", "remarks": "Count matched perfectly"}
        )
        self.assertEqual(res.status_code, 302)
        turnover1.refresh_from_db()
        self.assertEqual(turnover1.status, CollectionTurnover.TurnoverStatus.RECEIVED)
        self.assertEqual(turnover1.received_amount, Decimal("1000.00"))

        # 2. Mismatching turnover -> Disputed
        turnover2 = CollectionTurnover.objects.create(
            submitted_by=self.officer,
            declared_amount=Decimal("1000.00"),
            status=CollectionTurnover.TurnoverStatus.PENDING,
        )

        res2 = self.client.post(
            reverse("turnover_verify", kwargs={"turnover_id": turnover2.turnover_id}),
            {"received_amount": "900.00", "remarks": "Shortage of 100 pesos"}
        )
        self.assertEqual(res2.status_code, 302)
        turnover2.refresh_from_db()
        self.assertEqual(turnover2.status, CollectionTurnover.TurnoverStatus.DISPUTED)
        self.assertEqual(turnover2.received_amount, Decimal("900.00"))
