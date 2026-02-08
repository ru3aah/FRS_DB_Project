from django.contrib import admin

from .models import Position, Shift, ShiftType


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = (
        "position_id",
        "name_long",
        "name_short",
        "type",
        "is_active",
        "updated_at",
    )
    list_filter = ("type", "is_active")
    search_fields = ("name_long", "name_short")
    ordering = ("name_long",)
    list_per_page = 50
    readonly_fields = ("created_at", "updated_at")


@admin.register(ShiftType)
class ShiftTypeAdmin(admin.ModelAdmin):
    list_display = (
        "shift_type_id",
        "shift_type_short",
        "shift_type_name",
        "shift_days_on",
        "shift_days_off",
        "is_active",
        "updated_at",
    )
    list_filter = ("is_active",)
    search_fields = ("shift_type_short", "shift_type_name")
    ordering = ("shift_type_short",)
    list_per_page = 50
    readonly_fields = ("created_at", "updated_at")


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = (
        "shift_id",
        "shift_number",
        "shift_type",
        "is_active",
        "updated_at",
    )
    list_filter = ("is_active", "shift_type")
    search_fields = (
        "shift_number",
        "shift_type__shift_type_short",
        "shift_type__shift_type_name",
    )
    ordering = ("shift_number", "shift_type__shift_type_short")
    list_per_page = 50
    readonly_fields = ("created_at", "updated_at")
