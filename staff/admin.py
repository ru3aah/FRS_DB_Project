from django.contrib import admin

from .models import (
    Position,
    Shift,
    ShiftType,
    StaffingPlan,
    StaffingPlanItem,
    StaffEmployment,
    StaffingAssignment,
)


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = (
        "position_id",
        "company",
        "name_long",
        "name_short",
        "type",
        "is_active",
        "updated_at",
    )
    list_filter = ("company", "type", "is_active")
    search_fields = ("name_long", "name_short")
    ordering = ("company", "name_long")
    list_per_page = 50
    readonly_fields = ("created_at", "updated_at")


@admin.register(ShiftType)
class ShiftTypeAdmin(admin.ModelAdmin):
    list_display = (
        "shift_type_id",
        "company",
        "shift_type_short",
        "shift_type_name",
        "shift_days_on",
        "shift_days_off",
        "is_active",
        "updated_at",
    )
    list_filter = ("company", "is_active")
    search_fields = ("shift_type_short", "shift_type_name")
    ordering = ("company", "shift_type_short")
    list_per_page = 50
    readonly_fields = ("created_at", "updated_at")


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = (
        "shift_id",
        "company",
        "shift_number",
        "shift_type",
        "is_active",
        "updated_at",
    )
    list_filter = ("company", "is_active", "shift_type")
    search_fields = (
        "shift_number",
        "shift_type__shift_type_short",
        "shift_type__shift_type_name",
    )
    ordering = ("company", "shift_number", "shift_type__shift_type_short")
    list_per_page = 50
    readonly_fields = ("created_at", "updated_at")


class StaffingPlanItemInline(admin.TabularInline):
    model = StaffingPlanItem
    extra = 1
    fields = ("position", "position_qty", "shift_type")
    autocomplete_fields = ("position", "shift_type")


@admin.register(StaffingPlan)
class StaffingPlanAdmin(admin.ModelAdmin):
    list_display = ("staffing_plan_id", "company", "is_active", "updated_at")
    list_filter = ("company", "is_active")
    ordering = ("company", "-is_active", "-updated_at")
    readonly_fields = ("created_at", "updated_at")
    inlines = [StaffingPlanItemInline]


@admin.register(StaffEmployment)
class StaffEmploymentAdmin(admin.ModelAdmin):
    list_display = (
        "employment_id",
        "company",
        "person",
        "is_active",
        "hired_on",
        "terminated_on",
        "updated_at",
    )
    list_filter = ("company", "is_active")
    search_fields = ("person__first_name", "person__family_name", "company__name")
    ordering = ("company", "-is_active", "person")
    readonly_fields = ("created_at", "updated_at")


@admin.register(StaffingAssignment)
class StaffingAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "staffing_assignment_id",
        "company",
        "staffing_plan_item",
        "person",
        "is_active",
        "assigned_at",
        "released_at",
    )
    list_filter = ("company", "is_active")
    search_fields = ("person__first_name", "person__family_name")
    ordering = ("company", "-is_active", "-assigned_at")
