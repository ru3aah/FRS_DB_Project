# persons/admin.py

from django.contrib import admin
from .models import Person


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = (
        "person_id",
        "first_name",
        "second_name",
        "family_name",
        "dob",
        "gender",
        "created_at",
        "updated_at",
    )
    list_display_links = ("person_id",)
    search_fields = ("dob", "first_name", "second_name", "family_name", "gender")
    ordering = ("family_name", "first_name", "dob")
