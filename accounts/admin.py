from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Role, User


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("role_id", "role_name", "description")
    search_fields = ("role_name",)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_active",
        "is_staff",
    )

    fieldsets = UserAdmin.fieldsets + (
        ("CICS System Information", {
            "fields": ("role",)
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ("CICS System Information", {
            "fields": ("email", "role")
        }),
    )