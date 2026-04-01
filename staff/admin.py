from django.contrib import admin

from .models import (
    ExtraWork,
    ExtraWorkDocument,
    LeaveType,
    Position,
    RosterOverride,
    Shift,
    ShiftMembership,
    ShiftType,
    StaffAbsence,
    StaffAbsenceDocument,
    StaffingAssignment,
    StaffingPlan,
    StaffingPlanItem,
    TemporaryCover,
    TemporaryCoverDocument,
)


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = (
        "position_id",
        "company",
        "name_long",
        "name_short",
        "roster_code",
        "type",
        "is_active",
        "updated_at",
    )
    list_filter = ("company", "type", "is_active")
    search_fields = ("name_long", "name_short", "roster_code")
    ordering = ("company", "name_long")
    list_per_page = 50
    readonly_fields = ("created_at", "updated_at")


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = (
        "leave_type_id",
        "company",
        "leave_code",
        "name",
        "description",
        "is_active",
        "updated_at",
    )
    list_filter = ("company", "is_active")
    search_fields = ("leave_code", "name", "description")
    ordering = ("company", "name")
    list_per_page = 50
    readonly_fields = ("created_at", "updated_at")


@admin.register(ShiftType)
class ShiftTypeAdmin(admin.ModelAdmin):
    list_display = (
        "shift_type_id",
        "company",
        "code_letter",
        "shift_type_short",
        "shift_type_name",
        "shift_days_on",
        "shift_days_off",
        "package_size",
        "is_active",
        "updated_at",
    )
    list_filter = ("company", "is_active")
    search_fields = ("code_letter", "shift_type_short", "shift_type_name")
    ordering = ("company", "code_letter", "shift_type_short")
    list_per_page = 50
    readonly_fields = ("created_at", "updated_at")


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = (
        "shift_id",
        "company",
        "shift_number",
        "shift_type",
        "shift_no",
        "anchor_date",
        "is_active",
        "updated_at",
    )
    list_filter = ("company", "is_active", "shift_type")
    search_fields = (
        "shift_number",
        "shift_type__code_letter",
        "shift_type__shift_type_short",
        "shift_type__shift_type_name",
    )
    ordering = ("company", "shift_type__code_letter", "shift_no")
    list_per_page = 50
    readonly_fields = ("created_at", "updated_at")


class StaffingPlanItemInline(admin.TabularInline):
    model = StaffingPlanItem
    extra = 1
    fields = ("position", "position_qty")
    autocomplete_fields = ("position",)


@admin.register(StaffingPlan)
class StaffingPlanAdmin(admin.ModelAdmin):
    list_display = (
        "staffing_plan_id",
        "company",
        "staffing_plan_name",
        "active_from",
        "active_to",
        "is_active",
        "updated_at",
    )
    list_filter = ("company", "is_active", "active_from", "active_to")
    search_fields = ("staffing_plan_name",)
    ordering = ("company", "-is_active", "-updated_at")
    readonly_fields = ("created_at", "updated_at")
    inlines = [StaffingPlanItemInline]


@admin.register(StaffingPlanItem)
class StaffingPlanItemAdmin(admin.ModelAdmin):
    list_display = (
        "staffing_plan_item_id",
        "staffing_plan",
        "position",
        "position_qty",
        "created_at",
        "updated_at",
    )
    list_filter = ("staffing_plan__company", "position")
    search_fields = (
        "staffing_plan__staffing_plan_name",
        "position__name_long",
        "position__name_short",
        "position__roster_code",
    )
    ordering = ("staffing_plan__company", "staffing_plan", "position__name_long")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("staffing_plan", "position")


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
    search_fields = (
        "person__first_name",
        "person__second_name",
        "person__family_name",
        "staffing_plan_item__position__name_long",
    )
    ordering = ("company", "-assigned_at")
    autocomplete_fields = ("staffing_plan_item", "person")


@admin.register(ShiftMembership)
class ShiftMembershipAdmin(admin.ModelAdmin):
    list_display = (
        "shift_membership_id",
        "company",
        "person",
        "shift",
        "is_active",
        "assigned_at",
        "released_at",
    )
    list_filter = ("company", "is_active", "shift")
    search_fields = (
        "person__first_name",
        "person__second_name",
        "person__family_name",
        "shift__shift_number",
    )
    ordering = ("company", "-assigned_at")
    readonly_fields = ("assigned_at",)
    autocomplete_fields = ("person", "shift")


class StaffAbsenceDocumentInline(admin.TabularInline):
    model = StaffAbsenceDocument
    extra = 0
    fields = ("document_name", "file", "uploaded_at")
    readonly_fields = ("uploaded_at",)


@admin.register(StaffAbsence)
class StaffAbsenceAdmin(admin.ModelAdmin):
    list_display = (
        "absence_id",
        "company",
        "person",
        "leave_type",
        "date_from",
        "date_to",
        "is_active",
        "created_at",
    )
    list_filter = ("company", "leave_type", "is_active")
    search_fields = (
        "person__first_name",
        "person__second_name",
        "person__family_name",
        "note",
    )
    ordering = ("company", "-created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("person", "leave_type")
    inlines = [StaffAbsenceDocumentInline]


class TemporaryCoverDocumentInline(admin.TabularInline):
    model = TemporaryCoverDocument
    extra = 0
    fields = ("document_name", "file", "uploaded_at")
    readonly_fields = ("uploaded_at",)


@admin.register(TemporaryCover)
class TemporaryCoverAdmin(admin.ModelAdmin):
    list_display = (
        "temporary_cover_id",
        "company",
        "date_from",
        "date_to",
        "absence",
        "covering_person",
        "is_active",
        "created_at",
    )
    list_filter = ("company", "date_from", "date_to", "is_active")
    search_fields = (
        "covering_person__first_name",
        "covering_person__family_name",
        "absence__person__first_name",
        "absence__person__family_name",
        "note",
    )
    ordering = ("company", "-date_from", "-created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("absence", "staffing_plan_item", "covering_person")
    inlines = [TemporaryCoverDocumentInline]


class ExtraWorkDocumentInline(admin.TabularInline):
    model = ExtraWorkDocument
    extra = 0
    fields = ("document_name", "file", "uploaded_at")
    readonly_fields = ("uploaded_at",)


@admin.register(ExtraWork)
class ExtraWorkAdmin(admin.ModelAdmin):
    list_display = (
        "extra_work_id",
        "company",
        "person",
        "date_from",
        "date_to",
        "position",
        "is_active",
        "created_at",
    )
    list_filter = ("company", "date_from", "date_to", "is_active")
    search_fields = (
        "person__first_name",
        "person__second_name",
        "person__family_name",
        "position__name_long",
        "position__name_short",
        "note",
    )
    ordering = ("company", "-date_from", "-created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("person", "position")
    inlines = [ExtraWorkDocumentInline]


@admin.register(RosterOverride)
class RosterOverrideAdmin(admin.ModelAdmin):
    list_display = (
        "override_id",
        "company",
        "day",
        "staffing_plan_item",
        "replaced_person",
        "replacement_person",
        "is_active",
        "created_at",
    )
    list_filter = ("company", "day", "is_active")
    search_fields = (
        "replacement_person__first_name",
        "replacement_person__second_name",
        "replacement_person__family_name",
        "replaced_person__first_name",
        "replaced_person__second_name",
        "replaced_person__family_name",
        "note",
    )
    ordering = ("company", "-created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = (
        "staffing_plan_item",
        "replaced_person",
        "replacement_person",
    )