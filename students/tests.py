from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from accounts.models import Role
from students.models import Student, AcademicTerm
from finance_collections.models import FeeType, CollectionCampaign, CampaignObligation, Collection

User = get_user_model()


class StudentsAppTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student_role = Role.objects.create(role_name="Student")
        self.student_user = User.objects.create_user(
            username="TEST-2026-101",
            email="maria@cics.edu",
            password="admin123",
            role=self.student_role,
        )
        self.student_record = Student.objects.create(
            student_no="TEST-2026-101",
            full_name="Maria Clara",
            program="BSCS",
            year_level=1,
            section="A",
        )
        self.term = AcademicTerm.objects.create(
            school_year="2026-2027", semester="1st Semester", is_current=True
        )
        self.fee = FeeType.objects.create(fee_name="CSC Fee", default_amount=Decimal("100.00"))
        self.camp = CollectionCampaign.objects.create(
            campaign_name="CSC Semester Fee",
            fee_type=self.fee,
            term=self.term,
            start_date="2026-08-01",
            end_date="2026-12-15",
            status=CollectionCampaign.CampaignStatus.ACTIVE,
        )
        self.ob = CampaignObligation.objects.create(
            campaign=self.camp, student=self.student_record, required_amount=Decimal("100.00")
        )

    def test_student_payment_status_view(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse("student_payment_status"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Maria Clara")
        self.assertContains(response, "CSC Semester Fee")
        self.assertContains(response, "NOT CLEARED")

    def test_student_summary_view(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse("student_summary"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Transparency Report")
