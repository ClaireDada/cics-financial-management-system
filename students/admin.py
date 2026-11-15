from django.contrib import admin
from .models import Student, AcademicTerm


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "student_no",
        "full_name",
        "program",
        "year_level",
        "section",
    )
    search_fields = ("student_no", "full_name")
    list_filter = ("program", "year_level")


@admin.register(AcademicTerm)
class AcademicTermAdmin(admin.ModelAdmin):
    list_display = (
        "term_id",
        "school_year",
        "semester",
        "is_current",
    )
    list_filter = ("school_year", "semester", "is_current")