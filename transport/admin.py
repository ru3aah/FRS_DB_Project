from django.contrib import admin

from .models import TransportUnit, TransportUnitModel, TransportUnitType


@admin.register(TransportUnitType)
class TransportUnitTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "code", "is_active")
    search_fields = ("name", "code", "company__name")
    list_filter = ("company", "is_active")
    ordering = ("company__name", "name")


@admin.register(TransportUnitModel)
class TransportUnitModelAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "type", "code", "is_active")
    search_fields = ("name", "code", "company__name", "type__name", "type__code")
    list_filter = ("company", "type", "is_active")
    ordering = ("company__name", "type__name", "name")


@admin.register(TransportUnit)
class TransportUnitAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "model", "identifier", "is_active", "created_at")
    search_fields = (
        "name",
        "identifier",
        "company__name",
        "model__name",
        "model__code",
        "model__type__name",
        "model__type__code",
    )
    list_filter = ("company", "model", "is_active")
    ordering = ("company__name", "name")