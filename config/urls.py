
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

from accounts import views
from fund_management.views import audit_logs_view

# Customize Django Admin Header and Titles
admin.site.site_header = "CICS SG Financial Administration"
admin.site.site_title = "CICS Finance Admin"
admin.site.index_title = "System & Database Administration"


def home_redirect(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    return redirect("login")


urlpatterns = [
    path("", home_redirect, name="home"),
    path("admin/", admin.site.urls),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("users/", views.user_management_view, name="user_management"),
    path(
        "financial-overview/",
        views.financial_overview_view,
        name="financial_overview"
    ),
    path("audit-logs/", audit_logs_view, name="audit_logs"),

    # Application Modules
    path("fund-management/", include("fund_management.urls")),
    path("collections/", include("finance_collections.urls")),
    path("budget/", include("finance_budget.urls")),
    path("student/", include("students.urls")),
]
