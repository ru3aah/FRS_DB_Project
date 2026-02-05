from django.contrib import admin
from .models import Company, CompanyMembership


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active", "created_at")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(CompanyMembership)
class CompanyMembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "company", "is_active", "created_at")
    search_fields = ("user__username", "user__email", "company__name")
    list_filter = ("company", "is_active")
