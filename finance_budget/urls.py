from django.urls import path
from . import views

urlpatterns = [
    path("", views.budget_list, name="budget_list"),
    path("<int:budget_id>/", views.budget_detail, name="budget_detail"),
]
