from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from accounts.models import Role
from students.models import AcademicTerm, Student

User = get_user_model()


class AccountsViewTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Roles
        self.admin_role = Role.objects.create(role_name="Admin")
        self.governor_role = Role.objects.create(role_name="Governor")
        self.treasurer_role = Role.objects.create(role_name="Treasurer")
        self.auditor_role = Role.objects.create(role_name="Auditor")
        self.officer_role = Role.objects.create(role_name="Officer")
        self.adviser_role = Role.objects.create(role_name="Adviser")
        self.student_role = Role.objects.create(role_name="Student")

        # Users
        self.admin_user = User.objects.create_user(
            username="admin_test",
            email="admin_test@cics.edu",
            password="admin123",
            role=self.admin_role,
        )
        self.governor_user = User.objects.create_user(
            username="gov_test",
            email="gov_test@cics.edu",
            password="admin123",
            role=self.governor_role,
        )
        self.treasurer_user = User.objects.create_user(
            username="treas_test",
            email="treas_test@cics.edu",
            password="admin123",
            role=self.treasurer_role,
        )
        self.auditor_user = User.objects.create_user(
            username="audit_test",
            email="audit_test@cics.edu",
            password="admin123",
            role=self.auditor_role,
        )
        self.officer_user = User.objects.create_user(
            username="off_test",
            email="off_test@cics.edu",
            password="admin123",
            role=self.officer_role,
        )
        self.adviser_user = User.objects.create_user(
            username="adv_test",
            email="adv_test@cics.edu",
            password="admin123",
            role=self.adviser_role,
        )
        self.student_user = User.objects.create_user(
            username="TEST-2026-999",
            email="stud_test@cics.edu",
            password="admin123",
            role=self.student_role,
        )

        self.student_record = Student.objects.create(
            student_no="TEST-2026-999",
            full_name="Maria Santos",
            program="BSIT",
            year_level=3,
            section="B",
        )

        self.term = AcademicTerm.objects.create(
            school_year="2026-2027",
            semester="1st Semester",
            is_current=True,
        )

    def test_login_success(self):
        response = self.client.post(
            reverse("login"),
            {"username": "admin_test", "password": "admin123"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("dashboard"))

    def test_login_invalid_credentials(self):
        response = self.client.post(
            reverse("login"),
            {"username": "admin_test", "password": "wrongpassword"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username or password")

    def test_home_redirects_to_login_for_anonymous(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("login"))

    def test_home_redirects_to_dashboard_for_authenticated(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("dashboard"))

    def test_dashboard_renders_for_all_seven_roles(self):
        roles_users = [
            (self.admin_user, "Admin"),
            (self.governor_user, "Governor"),
            (self.treasurer_user, "Treasurer"),
            (self.auditor_user, "Auditor"),
            (self.officer_user, "Officer"),
            (self.adviser_user, "Adviser"),
            (self.student_user, "Student"),
        ]

        for user, role_name in roles_users:
            self.client.force_login(user)
            response = self.client.get(reverse("dashboard"))
            self.assertEqual(
                response.status_code,
                200,
                f"Dashboard failed to render with 200 for role: {role_name}"
            )
            self.assertContains(response, role_name)

    def test_financial_overview_access_control(self):
        # Admin: Allowed
        self.client.force_login(self.admin_user)
        res = self.client.get(reverse("financial_overview"))
        self.assertEqual(res.status_code, 200)

        # Governor: Allowed
        self.client.force_login(self.governor_user)
        res = self.client.get(reverse("financial_overview"))
        self.assertEqual(res.status_code, 200)

        # Treasurer: Allowed
        self.client.force_login(self.treasurer_user)
        res = self.client.get(reverse("financial_overview"))
        self.assertEqual(res.status_code, 200)

        # Auditor: Allowed
        self.client.force_login(self.auditor_user)
        res = self.client.get(reverse("financial_overview"))
        self.assertEqual(res.status_code, 200)

        # Student: Not allowed (redirects to dashboard with message)
        self.client.force_login(self.student_user)
        res = self.client.get(reverse("financial_overview"))
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, reverse("dashboard"))
