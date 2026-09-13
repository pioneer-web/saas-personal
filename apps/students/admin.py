from django.contrib import admin
from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "phone",
        "status",
        "organization",
    )

    list_filter = (
        "status",
        "organization",
    )

    search_fields = (
        "name",
        "email",
        "cpf",
        "phone",
    )
