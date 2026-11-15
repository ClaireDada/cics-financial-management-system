from django.urls import path
from . import views

urlpatterns = [
    path("", views.collections_list, name="collections_list"),
    path("record-payment/", views.record_payment_view, name="record_payment"),
    path("turnovers/", views.turnovers_list, name="turnovers_list"),
    path("turnovers/submit/", views.turnover_submit_view, name="turnover_submit"),
    path("turnovers/<int:turnover_id>/verify/", views.turnover_verify_view, name="turnover_verify"),
    path("campaigns/", views.campaigns_list, name="campaigns_list"),
]
