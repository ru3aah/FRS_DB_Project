from __future__ import annotations

from django.db import models
from django.db.models import Q

from companies.models import Company
from persons.models import Person


class Position(models.Model):
    """
    Reference table for staff positions.
    """

    POSITION_TYPE_CHOICES = (
        ("expat", "Expat"),
        ("local", "Local"),
        ("any", "Any"),
    )

    position_id = models.BigAutoField(primary_key=True)

    # Company scope (nullable for painless migration; later can be made required)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="staff_positions",
        null=True,
        blank=True,
        help_text="Company this position belongs to",
    )

    name_long = models.CharField(
        max_length=255,
        help_text="Full position name (e.g. Fire Chief, Senior Firefighter)",
    )

    name_short = models.CharField(
        max_length=64,
        help_text="Short position name (e.g. Chief, FF)",
    )

    type = models.CharField(
        max_length=5,
        choices=POSITION_TYPE_CHOICES,
        default="any",
        help_text="Allowed staff type for this position",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Whether this position is active and selectable",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "staff_positions"
        ordering = ["name_long"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name_long"],
                name="uq_staff_position_company_name_long",
            ),
            models.UniqueConstraint(
                fields=["company", "name_short"],
                name="uq_staff_position_company_name_short",
            ),
        ]

    def __str__(self) -> str:
        return self.name_long


class ShiftType(models.Model):
    """
    Reference table for shift patterns/types.
    Example: 14/14, 28/28, 7/7 etc.
    """

    shift_type_id = models.BigAutoField(primary_key=True)

    # Company scope (nullable for painless migration; later can be made required)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="staff_shift_types",
        null=True,
        blank=True,
        help_text="Company this shift type belongs to",
    )

    shift_type_name = models.CharField(
        max_length=255,
        help_text="Long name for this shift type (e.g. Rotation 14/14, Night Shift)",
    )

    shift_type_short = models.CharField(
        max_length=10,
        help_text="Short code up to 10 chars (letters/digits/signs), e.g. 14/14, NGT, D1",
    )

    shift_days_on = models.PositiveSmallIntegerField(
        help_text="Number of consecutive work days"
    )

    shift_days_off = models.PositiveSmallIntegerField(
        help_text="Number of consecutive off days after the shift"
    )

    # NEW: anchor date for rotation calculations
    # Used by roster to know "who is on duty today".
    anchor_date = models.DateField(
        blank=True,
        null=True,
        help_text="Rotation anchor date (first day when shift #1 is on duty).",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Whether this shift type is active and selectable",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "staff_shift_types"
        ordering = ["shift_type_short"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "shift_type_short"],
                name="uq_staff_shift_type_company_short",
            ),
            models.UniqueConstraint(
                fields=["company", "shift_type_name"],
                name="uq_staff_shift_type_company_name",
            ),
            models.UniqueConstraint(
                fields=[
                    "company",
                    "shift_days_on",
                    "shift_days_off",
                    "shift_type_short",
                ],
                name="uq_shift_type_pattern_short_company",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.shift_type_short} ({self.shift_days_on}/{self.shift_days_off})"


class Shift(models.Model):
    """
    Reference table for actual shifts (e.g., A/B/C) that use a shift type pattern.
    Example: Shift A uses type 14/14.
    """

    shift_id = models.BigAutoField(primary_key=True)

    # Company scope (nullable for painless migration; later can be made required)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="staff_shifts",
        null=True,
        blank=True,
        help_text="Company this shift belongs to",
    )

    shift_number = models.CharField(
        max_length=2,
        help_text="Manual code (2 chars): letters or digits, e.g. A1, 01, B2",
    )

    shift_type = models.ForeignKey(
        ShiftType,
        on_delete=models.PROTECT,
        related_name="shifts",
        help_text="Link to shift type (pattern)",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Whether this shift is active and selectable",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "staff_shifts"
        ordering = ["shift_number", "shift_type__shift_type_short"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "shift_number", "shift_type"],
                name="uq_staff_shift_company_number_type_fk",
            ),
        ]

    def __str__(self) -> str:
        st = self.shift_type
        return f"{self.shift_number} — {st.shift_type_short} ({st.shift_days_on}/{st.shift_days_off})"


class StaffingPlan(models.Model):
    """
    Staffing plan header (for a company).
    """

    staffing_plan_id = models.BigAutoField(primary_key=True)

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="staffing_plans",
        help_text="Company this staffing plan belongs to",
    )

    staffing_plan_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Human-readable staffing plan name",
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "staff_staffing_plans"
        ordering = ["-is_active", "-updated_at"]

    def __str__(self) -> str:
        name = (self.staffing_plan_name or "").strip()
        if name:
            return f"{name} ({self.company})"
        return f"Staffing plan #{self.staffing_plan_id} ({self.company})"


class StaffingPlanItem(models.Model):
    """
    Staffing plan line:
      - position
      - qty
      - shift_type
    """

    staffing_plan_item_id = models.BigAutoField(primary_key=True)

    staffing_plan = models.ForeignKey(
        StaffingPlan,
        on_delete=models.CASCADE,
        related_name="items",
    )

    position = models.ForeignKey(
        Position,
        on_delete=models.PROTECT,
        related_name="staffing_plan_items",
    )

    position_qty = models.PositiveSmallIntegerField()

    shift_type = models.ForeignKey(
        ShiftType,
        on_delete=models.PROTECT,
        related_name="staffing_plan_items",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "staff_staffing_plan_items"
        ordering = ["position__name_long", "shift_type__shift_type_short"]
        constraints = [
            models.UniqueConstraint(
                fields=["staffing_plan", "position", "shift_type"],
                name="uq_staffing_plan_item_plan_position_shifttype",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.staffing_plan} | {self.position} x {self.position_qty} | {self.shift_type}"


# =========================
# Employment / Assignments
# =========================


class StaffEmployment(models.Model):
    """
    Marks that a Person is hired by Company (employment history).
    """

    employment_id = models.BigAutoField(primary_key=True)

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="staff_employments",
    )

    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="employments",
    )

    hired_on = models.DateField(blank=True, null=True)
    terminated_on = models.DateField(blank=True, null=True)

    is_active = models.BooleanField(
        default=True,
        help_text="Active employment (person is currently hired by this company).",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "staff_employments"
        ordering = ["-is_active", "company", "person"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "person"],
                condition=Q(is_active=True),
                name="uq_staff_employment_company_person_active",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.person} @ {self.company} ({'active' if self.is_active else 'inactive'})"


class StaffingAssignment(models.Model):
    """
    Occupies a slot inside a StaffingPlanItem with a concrete Person.
    """

    staffing_assignment_id = models.BigAutoField(primary_key=True)

    staffing_plan_item = models.ForeignKey(
        StaffingPlanItem,
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    person = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        related_name="staffing_assignments",
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="staffing_assignments",
        help_text="Redundant but удобный фильтр и контроль консистентности.",
    )

    is_active = models.BooleanField(default=True)

    assigned_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "staff_staffing_assignments"
        ordering = ["-is_active", "-assigned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["staffing_plan_item", "person"],
                name="uq_staffing_assignment_item_person",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.person} -> {self.staffing_plan_item} ("
            f"{'active' if self.is_active else 'inactive'})"
        )


# =========================
# Base distribution by shifts (A/B/C)
# =========================


class ShiftMembership(models.Model):
    """
    Base distribution: Person belongs to ONE Shift (A/B/C...) within Company.
    Used later to generate monthly roster.
    """

    shift_membership_id = models.BigAutoField(primary_key=True)

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="shift_memberships",
    )

    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="shift_memberships",
    )

    shift = models.ForeignKey(
        Shift,
        on_delete=models.PROTECT,
        related_name="memberships",
    )

    is_active = models.BooleanField(default=True)

    assigned_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "staff_shift_memberships"
        ordering = ["-is_active", "-assigned_at"]
        constraints = [
            # Only one active membership for (company, person)
            models.UniqueConstraint(
                fields=["company", "person"],
                condition=Q(is_active=True),
                name="uq_shift_membership_company_person_active",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.person} -> {self.shift} ({'active' if self.is_active else 'inactive'})"


class StaffAbsence(models.Model):
    """
    Absences for roster (sick leave / vacation / day-off etc.).
    """

    ABSENCE_TYPE_CHOICES = (
        ("sick", "Sick leave"),
        ("vac", "Vacation"),
        ("off", "Day off"),
        ("other", "Other"),
    )

    absence_id = models.BigAutoField(primary_key=True)

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="staff_absences",
    )

    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="absences",
    )

    absence_type = models.CharField(
        max_length=8,
        choices=ABSENCE_TYPE_CHOICES,
        default="other",
    )

    date_from = models.DateField()
    date_to = models.DateField()

    note = models.CharField(max_length=255, blank=True, default="")

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "staff_absences"
        ordering = ["-is_active", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(date_to__gte=models.F("date_from")),
                name="ck_absence_date_to_gte_from",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.person} absence {self.date_from}..{self.date_to}"


class RosterOverride(models.Model):
    """
    One-day replacement / override for roster (temporary change).
    Example: on 2026-03-10 person A replaced by person B for a plan item.
    """

    override_id = models.BigAutoField(primary_key=True)

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="roster_overrides",
    )

    day = models.DateField(db_index=True)

    staffing_plan_item = models.ForeignKey(
        StaffingPlanItem,
        on_delete=models.CASCADE,
        related_name="roster_overrides",
    )

    replaced_person = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        related_name="roster_overrides_replaced",
        blank=True,
        null=True,
        help_text="Optional: who is replaced (can be empty)",
    )

    replacement_person = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        related_name="roster_overrides_replacement",
        help_text="Who works instead",
    )

    note = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "staff_roster_overrides"
        ordering = ["-is_active", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "day", "staffing_plan_item", "replacement_person"],
                name="uq_roster_override_company_day_item_person",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.day} | {self.staffing_plan_item} -> {self.replacement_person}"
