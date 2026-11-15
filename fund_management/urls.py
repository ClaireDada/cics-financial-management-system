from django.urls import path
from . import views

urlpatterns = [
    path("requests/", views.fund_requests_list, name="fund_requests_list"),
    path("requests/create/", views.fund_request_create, name="fund_request_create"),
    path("requests/<int:request_id>/", views.fund_request_detail, name="fund_request_detail"),
    path("requests/<int:request_id>/submit/", views.fund_request_submit, name="fund_request_submit"),
    path("requests/<int:request_id>/adviser-review/", views.fund_request_adviser_review, name="fund_request_adviser_review"),
    path("requests/<int:request_id>/governor-review/", views.fund_request_governor_review, name="fund_request_governor_review"),
    path("requests/<int:request_id>/release/", views.fund_request_release, name="fund_request_release"),
    path("disbursements/", views.disbursements_list, name="disbursements_list"),
    path("disbursements/<int:disbursement_id>/liquidate/", views.record_liquidation_view, name="record_liquidation"),
    path("disbursements/<int:disbursement_id>/return/", views.record_fund_return_view, name="record_fund_return"),
    path("liquidations/", views.liquidations_list, name="liquidations_list"),
    path("returns/", views.returns_list, name="returns_list"),
    path("approvals/", views.approvals_list, name="approvals_list"),
    path("notifications/", views.notifications_list, name="notifications_list"),
    path("audit-logs/", views.audit_logs_view, name="audit_logs"),
]
