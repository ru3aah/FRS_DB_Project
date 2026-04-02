from django.contrib import admin

from .models import TransportUnit, TransportUnitType


@admin.register(TransportUnitType)
class TransportUnitTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    search_fields = ("name", "code")
    list_filter = ("is_active",)
    ordering = ("name",)


@admin.register(TransportUnit)
class TransportUnitAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "type", "identifier", "is_active", "created_at")
    search_fields = ("name", "identifier", "company__name", "type__name", "type__code")
    list_filter = ("company", "type", "is_active")
    ordering = ("name",)