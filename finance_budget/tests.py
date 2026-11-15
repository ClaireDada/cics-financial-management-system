from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from accounts.models import Role
from students.models import AcademicTerm
from finance_budget.models import Budget, BudgetItem, ExpenseCategory

User = get_user_model()


class BudgetTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_role = Role.objects.create(role_name="Admin")
        self.user = User.objects.create_user(
            username="admin_b", email="b@cics.edu", password="admin123", role=self.admin_role
        )
        self.term = AcademicTerm.objects.create(
            school_year="2026-2027", semester="1st Semester", is_current=True
        )
        self.budget = Budget.objects.create(
            term=self.term,
            prepared_by=self.user,
            title="Operational Budget",
            total_amount=Decimal("30000.00"),
            status=Budget.BudgetStatus.ACTIVE,
        )
        self.category = ExpenseCategory.objects.create(
            category_name="Logistics", description="Transport and supplies"
        )
        self.item = BudgetItem.objects.create(
            budget=self.budget,
            category=self.category,
            description="Vehicle rent",
            allocated_amount=Decimal("10000.00"),
        )

    def test_budget_properties(self):
        self.assertEqual(self.budget.total_allocated, Decimal("10000.00"))
        self.assertEqual(self.budget.unallocated_amount, Decimal("20000.00"))
        self.assertFalse(self.budget.is_overallocated)

    def test_budget_list_and_detail_views(self):
        self.client.force_login(self.user)
        res_list = self.client.get(reverse("budget_list"))
        self.assertEqual(res_list.status_code, 200)
        self.assertContains(res_list, "Operational Budget")

        res_detail = self.client.get(reverse("budget_detail", kwargs={"budget_id": self.budget.budget_id}))
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, "Vehicle rent")
