from django.contrib import admin

from .models import Country, IDType, Person, PersonID, PersonIDScan


class PersonIDScanInline(admin.TabularInline):
    """
    Scans/files attached to a specific PersonID.
    """
    model = PersonIDScan
    extra = 0
    fields = ("file", "uploaded_at")
    readonly_fields = ("uploaded_at",)


class PersonIDInline(admin.TabularInline):
    """
    Identity documents attached to a Person.
    """
    model = PersonID
    extra = 0

    # Use autocomplete to avoid huge dropdowns
    autocomplete_fields = ("id_type", "issued_country")

    # Keep list compact but useful
    fields = (
        "id_type",
        "id_number",
        "issued_country",
        "issued_on",
        "valid_till",
        "id_std_sequence",
        "created_at",
        "updated_at",
    )
    readonly_fields = ("created_at", "updated_at")

    show_change_link = True


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    """
    Person admin with inline identity documents.
    """
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
    list_display_links = ("person_id", "family_name")
    search_fields = ("dob", "first_name", "second_name", "family_name", "gender")
    list_filter = ("gender",)
    ordering = ("family_name", "first_name", "dob")

    inlines = (PersonIDInline,)


@admin.register(PersonID)
class PersonIDAdmin(admin.ModelAdmin):
    """
    Separate admin page for documents (handy for auditing).
    """
    list_display = (
        "id",
        "person",
        "id_type",
        "id_number",
        "issued_country",
        "issued_on",
        "valid_till",
        "created_at",
    )
    list_display_links = ("id", "id_number")
    list_filter = ("id_type", "issued_country")
    search_fields = (
        "id_number",
        "id_std_sequence",
        "person__first_name",
        "person__second_name",
        "person__family_name",
        "person__dob",
        "issued_country__code3",
        "issued_country__short_name",
        "issued_country__full_name",
        "id_type__code",
        "id_type__name",
    )
    autocomplete_fields = ("person", "id_type", "issued_country")
    ordering = ("person", "id_type", "id_number")

    inlines = (PersonIDScanInline,)


@admin.register(PersonIDScan)
class PersonIDScanAdmin(admin.ModelAdmin):
    """
    Separate admin page for scans/files.
    """
    list_display = ("id", "person_id", "uploaded_at", "file")
    list_filter = ("uploaded_at",)
    search_fields = (
        "person_id__id_number",
        "person_id__person__first_name",
        "person_id__person__second_name",
        "person_id__person__family_name",
    )
    autocomplete_fields = ("person_id",)
    ordering = ("-uploaded_at",)


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    """
    Country reference table (used for issued_country).
    """
    list_display = ("code3", "short_name", "full_name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code3", "short_name", "full_name")
    ordering = ("code3",)


@admin.register(IDType)
class IDTypeAdmin(admin.ModelAdmin):
    """
    ID document types reference table.
    """
    list_display = ("code", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    ordering = ("code",)