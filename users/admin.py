from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from companies.models import Company, CompanyMembership
from .models import CustomUser


# ---------- Inline: user ↔ company ----------
class CompanyMembershipInline(admin.TabularInline):
    model = CompanyMembership
    extra = 0
    autocomplete_fields = ("company",)


# ---------- Forms ----------
class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ("email", "person")


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = (
            "email",
            "person",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )


# ---------- Custom filter by company ----------
class CompanyFilter(admin.SimpleListFilter):
    title = _("Company")
    parameter_name = "company"

    def lookups(self, request, model_admin):
        return [(c.id, c.name) for c in Company.objects.filter(is_active=True)]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                company_memberships__company_id=self.value(),
                company_memberships__is_active=True,
            )
        return queryset


# ---------- Admin ----------
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    ordering = ("email",)

    # --- list view ---
    list_display = (
        "email",
        "person_first_name",
        "person_second_name",
        "person_family_name",
        "person_dob",
        "companies_list",
        "is_staff",
        "is_superuser",
        "is_active",
    )

    list_filter = (
        CompanyFilter,  # ← фильтр по компании
        "is_staff",
        "is_superuser",
        "is_active",
        "groups",
    )

    search_fields = (
        "email",
        "person__first_name",
        "person__second_name",
        "person__family_name",
        "person__dob",
    )

    # --- edit form ---
    fieldsets = (
        (None, {"fields": ("email", "password", "person")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "person",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_superuser",
                    "is_active",
                ),
            },
        ),
    )

    autocomplete_fields = ("person",)
    inlines = (CompanyMembershipInline,)

    # ---------- computed columns ----------
    @admin.display(description="First name")
    def person_first_name(self, obj):
        return obj.person.first_name if obj.person else ""

    @admin.display(description="Second name")
    def person_second_name(self, obj):
        return obj.person.second_name if obj.person else ""

    @admin.display(description="Family name")
    def person_family_name(self, obj):
        return obj.person.family_name if obj.person else ""

    @admin.display(description="DOB")
    def person_dob(self, obj):
        return obj.person.dob if obj.person else None

    @admin.display(description="Companies")
    def companies_list(self, obj):
        qs = obj.company_memberships.select_related("company").filter(is_active=True)
        return ", ".join(m.company.name for m in qs)

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("person")
        return qs.prefetch_related("company_memberships__company")
