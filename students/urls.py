from django.urls import path
from . import views

urlpatterns = [
    path("payments/", views.student_payment_status, name="student_payment_status"),
    path("summary/", views.student_summary, name="student_summary"),
    path("list/", views.student_list, name="student_list"),
]
