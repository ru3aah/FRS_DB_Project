from __future__ import annotations

import re
from datetime import date

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from companies.models import Company
from persons.models import Person


def _person_has_nonbase_day_override(
    *,
    company_id: int | None,
    person_id: int | None,
    day: date | None,
    exclude_temporary_cover_id: int | None = None,
    exclude_extra_work_id: int | None = None,
) -> bool:
    if not company_id or not person_id or not day:
        return False

    temp_cover_qs = TemporaryCover.objects.filter(
        company_id=company_id,
        covering_person_id=person_id,
        is_active=True,
        date_from__lte=day,
        date_to__gte=day,
    )
    if exclude_temporary_cover_id:
        temp_cover_qs = temp_cover_qs.exclude(pk=exclude_temporary_cover_id)

    if temp_cover_qs.exists():
        return True

    extra_work_qs = ExtraWork.objects.filter(
        company_id=company_id,
        person_id=person_id,
        day=day,
        is_active=True,
    )
    if exclude_extra_work_id:
        extra_work_qs = extra_work_qs.exclude(pk=exclude_extra_work_id)

    if extra_work_qs.exists():
        return True

    leave_qs = StaffAbsence.objects.filter(
        company_id=company_id,
        person_id=person_id,
        is_active=True,
        date_from__lte=day,
        date_to__gte=day,
    )

    return leave_qs.exists()


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

    roster_code = models.CharField(
        max_length=2,
        null=True,
        blank=True,
        help_text="Two-letter roster code for this position, e.g. TL, CR, DO, ME, FF, MT.",
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
            models.UniqueConstraint(
                fields=["company", "roster_code"],
                name="uq_staff_position_company_roster_code",
                condition=Q(roster_code__isnull=False),
            ),
        ]

    def clean(self):
        super().clean()

        self.roster_code = (self.roster_code or "").strip().upper()

        if not self.roster_code:
            return

        if not re.fullmatch(r"[A-Z]{2}", self.roster_code):
            raise ValidationError(
                {
                    "roster_code": (
                        "Roster code must contain exactly 2 uppercase Latin letters."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.roster_code = (self.roster_code or "").strip().upper()
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name_long


class LeaveType(models.Model):
    """
    Reference table for leave / non-duty status types used in roster.
    """

    leave_type_id = models.BigAutoField(primary_key=True)

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="staff_leave_types",
        null=True,
        blank=True,
        help_text="Company this leave type belongs to",
    )

    leave_code = models.CharField(
        max_length=2,
        help_text="Two-letter leave code.",
    )

    name = models.CharField(
        max_length=100,
        help_text="Full leave type name.",
    )

    description = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Optional explanation / note shown in UI.",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Whether this leave type is active and selectable.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "staff_leave_types"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "leave_code"],
                name="uq_staff_leave_type_company_code",
            ),
            models.UniqueConstraint(
                fields=["company", "name"],
                name="uq_staff_leave_type_company_name",
            ),
        ]

    def clean(self):
        super().clean()

        self.leave_code = (self.leave_code or "").strip().upper()

        if not re.fullmatch(r"[A-Z]{2}", self.leave_code):
            raise ValidationError(
                {
                    "leave_code": (
                        "Leave code must contain exactly 2 uppercase Latin letters."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.leave_code = (self.leave_code or "").strip().upper()
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.leave_code} | {self.name}"


class ShiftType(models.Model):
    """
    Shift pattern / rotation type.
    """

    shift_type_id = models.BigAutoField(primary_key=True)

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="staff_shift_types",
        null=True,
        blank=True,
        help_text="Company this shift type belongs to",
    )

    code_letter = models.CharField(
        max_length=2,
        help_text="Letter code of pattern, e.g. A, B, C",
    )

    shift_type_name = models.CharField(
        max_length=255,
        help_text="Long name for this shift type (e.g. Rotation 7/14)",
    )

    shift_type_short = models.CharField(
        max_length=10,
        help_text="Short pattern text, e.g. 7/14, 28/28, 2/2",
    )

    shift_days_on = models.PositiveSmallIntegerField(
        help_text="Number of consecutive work days",
    )

    shift_days_off = models.PositiveSmallIntegerField(
        help_text="Number of consecutive off days after work block",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Whether this shift type is active and selectable",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "staff_shift_types"
        ordering = ["code_letter", "shift_type_short"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code_letter"],
                name="uq_staff_shift_type_company_code_letter",
            ),
            models.UniqueConstraint(
                fields=["company", "shift_type_short"],
                name="uq_staff_shift_type_company_short",
            ),
            models.UniqueConstraint(
                fields=["company", "shift_type_name"],
                name="uq_staff_shift_type_company_name",
            ),
            models.UniqueConstraint(
                fields=["company", "shift_days_on", "shift_days_off"],
                name="uq_staff_shift_type_company_pattern",
            ),
        ]

    def clean(self):
        super().clean()

        if not self.code_letter:
            raise ValidationError({"code_letter": "Pattern code letter is required."})

        self.code_letter = (self.code_letter or "").strip().upper()
        if len(self.code_letter) > 2:
            raise ValidationError(
                {"code_letter": "Pattern code letter must be 1 or 2 characters."}
            )

        if self.shift_days_on <= 0:
            raise ValidationError({"shift_days_on": "Work days must be > 0."})

        if self.shift_days_off < 0:
            raise ValidationError({"shift_days_off": "Off days must be >= 0."})

        if self.shift_days_off % self.shift_days_on != 0:
            raise ValidationError(
                {
                    "shift_days_off": (
                        "Off days must be divisible by work days so the full cycle "
                        "can be completed by an integer number of sibling shifts."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.code_letter = (self.code_letter or "").strip().upper()
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def cycle_days(self) -> int:
        return int(self.shift_days_on) + int(self.shift_days_off)

    @property
    def package_size(self) -> int:
        return self.cycle_days // int(self.shift_days_on)

    def __str__(self) -> str:
        return (
            f"{self.code_letter} | {self.shift_type_short} "
            f"({self.shift_days_on}/{self.shift_days_off})"
        )


class Shift(models.Model):
    """
    Concrete shift inside one shift pattern package.
    """

    shift_id = models.BigAutoField(primary_key=True)

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="staff_shifts",
        null=True,
        blank=True,
        help_text="Company this shift belongs to",
    )

    shift_type = models.ForeignKey(
        ShiftType,
        on_delete=models.PROTECT,
        related_name="shifts",
        help_text="Link to shift type (pattern)",
    )

    shift_no = models.PositiveSmallIntegerField(
        help_text="Sequential number inside pattern package: 1, 2, 3 ...",
    )

    shift_number = models.CharField(
        max_length=8,
        help_text="Full shift code, generated from pattern code + shift_no, e.g. A1, A2, B1",
    )

    anchor_date = models.DateField(
        blank=True,
        null=True,
        help_text="First day when this concrete shift starts its duty block.",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Whether this shift is active and selectable",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "staff_shifts"
        ordering = ["shift_type__code_letter", "shift_no"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "shift_type", "shift_no"],
                name="uq_staff_shift_company_type_no",
            ),
            models.UniqueConstraint(
                fields=["company", "shift_number"],
                name="uq_staff_shift_company_number",
            ),
        ]

    def clean(self):
        super().clean()

        if self.shift_no <= 0:
            raise ValidationError(
                {"shift_no": "Shift number inside package must be > 0."}
            )

        if self.shift_type_id:
            max_no = self.shift_type.package_size
            if self.shift_no > max_no:
                raise ValidationError(
                    {
                        "shift_no": (
                            f"Shift number cannot exceed package size {max_no} "
                            f"for pattern {self.shift_type.shift_type_short}."
                        )
                    }
                )

            self.shift_number = f"{self.shift_type.code_letter}{self.shift_no}"

    def save(self, *args, **kwargs):
        if self.shift_type_id and self.shift_no:
            self.shift_number = f"{self.shift_type.code_letter}{self.shift_no}"
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def cycle_days(self) -> int:
        return self.shift_type.cycle_days

    @property
    def days_on(self) -> int:
        return int(self.shift_type.shift_days_on)

    @property
    def days_off(self) -> int:
        return int(self.shift_type.shift_days_off)

    def is_on_duty(self, day: date) -> bool:
        if not self.anchor_date:
            return False

        delta_days = (day - self.anchor_date).days
        return (delta_days % self.cycle_days) < self.days_on

    def __str__(self) -> str:
        return (
            f"{self.shift_number} — {self.shift_type.shift_type_short} "
            f"({self.shift_type.shift_days_on}/{self.shift_type.shift_days_off})"
        )


class StaffingPlan(models.Model):
    """
    Staffing plan header (for a company).
    Contains only positions and quantities.
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

    active_from = models.DateField(
        blank=True,
        null=True,
        help_text="Date from which this staffing plan becomes effective.",
    )

    active_to = models.DateField(
        blank=True,
        null=True,
        help_text="Date until which this staffing plan is effective.",
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "staff_staffing_plans"
        ordering = ["-is_active", "-updated_at"]

    def clean(self):
        super().clean()

        if self.active_from and self.active_to and self.active_to < self.active_from:
            raise ValidationError(
                {"active_to": "Active to date cannot be earlier than active from date."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "staff_staffing_plan_items"
        ordering = ["position__name_long"]
        constraints = [
            models.UniqueConstraint(
                fields=["staffing_plan", "position"],
                name="uq_staffing_plan_item_plan_position",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.staffing_plan} | {self.position} x {self.position_qty}"


class StaffingAssignment(models.Model):
    """
    Employment fact = assignment to a concrete staffing plan position.
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
    )

    is_active = models.BooleanField(default=True)

    assigned_at = models.DateTimeField()
    released_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "staff_staffing_assignments"
        ordering = ["-assigned_at"]

    def clean(self):
        super().clean()

        if (
            self.staffing_plan_item_id
            and self.company_id
            and self.staffing_plan_item.staffing_plan.company_id != self.company_id
        ):
            raise ValidationError(
                {"company": "Assignment company must match staffing plan company."}
            )

        if (
            self.released_at
            and self.assigned_at
            and self.released_at < self.assigned_at
        ):
            raise ValidationError(
                {
                    "released_at": "Release datetime cannot be earlier than assigned datetime."
                }
            )

        if not self.person_id or not self.assigned_at:
            return

        overlap_qs = StaffingAssignment.objects.filter(person_id=self.person_id)

        if self.pk:
            overlap_qs = overlap_qs.exclude(pk=self.pk)

        if self.released_at is None:
            overlap_qs = overlap_qs.filter(
                Q(released_at__isnull=True) | Q(released_at__gte=self.assigned_at)
            )
        else:
            overlap_qs = overlap_qs.filter(assigned_at__lte=self.released_at).filter(
                Q(released_at__isnull=True) | Q(released_at__gte=self.assigned_at)
            )

        if overlap_qs.exists():
            raise ValidationError(
                {
                    "person": (
                        "This person already has another assignment overlapping "
                        "with this assignment period."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.person} -> {self.staffing_plan_item}"


class ShiftMembership(models.Model):
    """
    Base distribution: Person belongs to ONE concrete Shift inside Company.
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
        ordering = ["-assigned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "person"],
                condition=Q(is_active=True),
                name="uq_shift_membership_company_person_active",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.person} -> {self.shift}"


class StaffAbsence(models.Model):
    """
    Temporary absence from work.
    """

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

    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name="absences",
        help_text="Structured leave / non-duty type from LeaveType directory.",
    )

    date_from = models.DateField()
    date_to = models.DateField()

    note = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "staff_absences"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(date_to__gte=models.F("date_from")),
                name="ck_absence_date_to_gte_from",
            ),
        ]

    def clean(self):
        super().clean()

        if self.date_to < self.date_from:
            raise ValidationError(
                {"date_to": "Absence end date cannot be earlier than start date."}
            )

        if (
            self.leave_type_id
            and self.company_id
            and self.leave_type.company_id != self.company_id
        ):
            raise ValidationError(
                {"leave_type": "Leave type company must match absence company."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.person} absence {self.date_from}..{self.date_to}"


class StaffAbsenceDocument(models.Model):
    absence_document_id = models.BigAutoField(primary_key=True)

    absence = models.ForeignKey(
        StaffAbsence,
        on_delete=models.CASCADE,
        related_name="documents",
    )

    document_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Optional document name shown in UI.",
    )

    file = models.FileField(
        upload_to="staff/absences/documents/",
        help_text="Supporting document for absence.",
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "staff_absence_documents"
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return f"Absence doc for {self.absence_id} ({self.uploaded_at:%Y-%m-%d})"


class TemporaryCover(models.Model):
    temporary_cover_id = models.BigAutoField(primary_key=True)

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="temporary_covers",
    )

    absence = models.ForeignKey(
        StaffAbsence,
        on_delete=models.PROTECT,
        related_name="temporary_covers",
        help_text="Leave/absence that this cover is closing.",
    )

    date_from = models.DateField(db_index=True)
    date_to = models.DateField(db_index=True)

    staffing_plan_item = models.ForeignKey(
        StaffingPlanItem,
        on_delete=models.CASCADE,
        related_name="temporary_covers",
    )

    covering_person = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        related_name="temporary_covers_as_covering",
        help_text="Person who covers the duty.",
    )

    note = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "staff_temporary_covers"
        ordering = ["-date_from", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "company",
                    "date_from",
                    "date_to",
                    "staffing_plan_item",
                    "covering_person",
                ],
                name="uq_temp_cover_company_period_item_covering_person",
            ),
            models.CheckConstraint(
                condition=Q(date_to__gte=models.F("date_from")),
                name="ck_temp_cover_date_to_gte_from",
            ),
        ]

    def clean(self):
        super().clean()

        if not self.absence_id:
            raise ValidationError(
                {"absence": "Temporary cover must be linked to an existing absence."}
            )

        if self.date_from and self.date_to and self.date_to < self.date_from:
            raise ValidationError(
                {"date_to": "Cover end date cannot be earlier than cover start date."}
            )

        if (
            self.staffing_plan_item_id
            and self.company_id
            and self.staffing_plan_item.staffing_plan.company_id != self.company_id
        ):
            raise ValidationError(
                {"company": "Temporary cover company must match staffing plan company."}
            )

        if (
            self.absence_id
            and self.company_id
            and self.absence.company_id != self.company_id
        ):
            raise ValidationError(
                {"absence": "Absence company must match temporary cover company."}
            )

        if self.date_from and self.date_to:
            if (
                self.date_from < self.absence.date_from
                or self.date_to > self.absence.date_to
            ):
                raise ValidationError(
                    {
                        "date_from": "Temporary cover period must be inside linked absence period.",
                        "date_to": "Temporary cover period must be inside linked absence period.",
                    }
                )

        if self.absence.person_id == self.covering_person_id:
            raise ValidationError(
                {
                    "covering_person": "Covering person cannot be the same as absent person."
                }
            )

        if not self.covering_person_id or not self.date_from or not self.date_to:
            return

        overlap_qs = TemporaryCover.objects.filter(
            company_id=self.company_id,
            covering_person_id=self.covering_person_id,
            is_active=True,
            date_from__lte=self.date_to,
            date_to__gte=self.date_from,
        )
        if self.pk:
            overlap_qs = overlap_qs.exclude(pk=self.pk)

        if overlap_qs.exists():
            raise ValidationError(
                {
                    "covering_person": (
                        "This person already has another temporary cover overlapping "
                        "with the selected cover period."
                    )
                }
            )

        extra_work_overlap_qs = ExtraWork.objects.filter(
            company_id=self.company_id,
            person_id=self.covering_person_id,
            is_active=True,
            day__gte=self.date_from,
            day__lte=self.date_to,
        )
        if self.pk:
            extra_work_overlap_qs = extra_work_overlap_qs.exclude(
                pk=self.pk  # harmless safeguard if ids ever overlap by queryset reuse
            )

        if extra_work_overlap_qs.exists():
            raise ValidationError(
                {
                    "covering_person": (
                        "This person already has extra work within the selected cover period."
                    )
                }
            )

        leave_overlap_qs = StaffAbsence.objects.filter(
            company_id=self.company_id,
            person_id=self.covering_person_id,
            is_active=True,
            date_from__lte=self.date_to,
            date_to__gte=self.date_from,
        )
        if leave_overlap_qs.exists():
            raise ValidationError(
                {
                    "covering_person": (
                        "This person already has leave overlapping with the selected cover period."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return (
            f"{self.date_from}..{self.date_to} | "
            f"{self.covering_person} covers {self.absence.person}"
        )


class TemporaryCoverDocument(models.Model):
    temporary_cover_document_id = models.BigAutoField(primary_key=True)

    temporary_cover = models.ForeignKey(
        TemporaryCover,
        on_delete=models.CASCADE,
        related_name="documents",
    )

    document_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Optional document name shown in UI.",
    )

    file = models.FileField(
        upload_to="staff/temporary_covers/documents/",
        help_text="Supporting document for temporary cover.",
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "staff_temporary_cover_documents"
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return (
            f"Temporary cover doc for {self.temporary_cover_id} "
            f"({self.uploaded_at:%Y-%m-%d})"
        )


class ExtraWork(models.Model):
    extra_work_id = models.BigAutoField(primary_key=True)

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="extra_works",
    )

    person = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        related_name="extra_works",
    )

    day = models.DateField(db_index=True)

    position = models.ForeignKey(
        Position,
        on_delete=models.PROTECT,
        related_name="extra_works",
        blank=True,
        null=True,
        help_text="Position worked on this extra day. This is outside staffing plan slots.",
    )

    note = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "staff_extra_works"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "person", "day"],
                name="uq_extra_work_company_person_day",
            ),
        ]

    def clean(self):
        super().clean()

        if (
            self.position_id
            and self.company_id
            and self.position.company_id != self.company_id
        ):
            raise ValidationError(
                {"position": "Extra day position company must match extra day company."}
            )

        if _person_has_nonbase_day_override(
            company_id=self.company_id,
            person_id=self.person_id,
            day=self.day,
            exclude_extra_work_id=self.pk,
        ):
            raise ValidationError(
                {
                    "person": (
                        "This person already has another day override on this day "
                        "(temporary cover, extra work, or leave)."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.person} extra work on {self.day}"


class ExtraWorkDocument(models.Model):
    extra_work_document_id = models.BigAutoField(primary_key=True)

    extra_work = models.ForeignKey(
        ExtraWork,
        on_delete=models.CASCADE,
        related_name="documents",
    )

    document_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Optional document name shown in UI.",
    )

    file = models.FileField(
        upload_to="staff/extra_work/documents/",
        help_text="Supporting document for extra work.",
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "staff_extra_work_documents"
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return f"Extra work doc for {self.extra_work_id} ({self.uploaded_at:%Y-%m-%d})"


class RosterOverride(models.Model):
    """
    Legacy one-day replacement / override for roster.
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
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "day", "staffing_plan_item", "replacement_person"],
                name="uq_roster_override_company_day_item_person",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.day} | {self.staffing_plan_item} -> {self.replacement_person}"