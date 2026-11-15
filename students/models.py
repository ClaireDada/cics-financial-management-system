
from django.db import models


class AcademicTerm(models.Model):
    term_id = models.AutoField(primary_key=True)
    school_year = models.CharField(max_length=20)
    semester = models.CharField(max_length=30)
    is_current = models.BooleanField(default=False)

    class Meta:
        db_table = "academic_terms"
        ordering = ["-school_year", "semester"]
        constraints = [
            models.UniqueConstraint(
                fields=["school_year", "semester"],
                name="unique_academic_term"
            )
        ]

    def __str__(self):
        return f"{self.school_year} - {self.semester}"


class Student(models.Model):
    student_id = models.AutoField(primary_key=True)
    student_no = models.CharField(max_length=30, unique=True)
    full_name = models.CharField(max_length=150)
    program = models.CharField(max_length=100)
    year_level = models.PositiveSmallIntegerField()
    section = models.CharField(max_length=30, blank=True)

    class Meta:
        db_table = "students"
        ordering = ["full_name"]
        constraints = [
            models.CheckConstraint(
    condition=models.Q(year_level__gte=1, year_level__lte=4),
    name="valid_student_year_level"
)
            
        ]

    def __str__(self):
        return f"{self.student_no} - {self.full_name}"
