from __future__ import annotations

from datetime import date

from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory

from persons.models import Person

from .models import (
    Position,
    ShiftType,
    Shift,
    StaffingPlan,
    StaffingPlanItem,
    StaffEmployment,
    StaffingAssignment,
    ShiftMembership,
    StaffAbsence,
    RosterOverride,
)


class PositionForm(forms.ModelForm):
    class Meta:
        model = Position
        fields = ["name_long", "name_short", "type", "is_active"]
        widgets = {
            "name_long": forms.TextInput(attrs={"class": "form-control"}),
            "name_short": forms.TextInput(attrs={"class": "form-control"}),
            "type": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ShiftTypeForm(forms.ModelForm):
    class Meta:
        model = ShiftType
        fields = [
            "shift_type_name",
            "shift_type_short",
            "shift_days_on",
            "shift_days_off",
            "anchor_date",
            "is_active",
        ]
        widgets = {
            "shift_type_name": forms.TextInput(attrs={"class": "form-control"}),
            "shift_type_short": forms.TextInput(attrs={"class": "form-control"}),
            "shift_days_on": forms.NumberInput(
                attrs={"class": "form-control", "min": 1}
            ),
            "shift_days_off": forms.NumberInput(
                attrs={"class": "form-control", "min": 0}
            ),
            "anchor_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = ["shift_number", "shift_type", "is_active"]
        widgets = {
            "shift_number": forms.TextInput(attrs={"class": "form-control"}),
            "shift_type": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class StaffingPlanForm(forms.ModelForm):
    class Meta:
        model = StaffingPlan
        fields = ["staffing_plan_name", "is_active"]
        widgets = {
            "staffing_plan_name": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class StaffingPlanItemForm(forms.ModelForm):
    class Meta:
        model = StaffingPlanItem
        fields = ["position", "position_qty", "shift_type"]
        widgets = {
            "position": forms.Select(attrs={"class": "form-select"}),
            "position_qty": forms.NumberInput(
                attrs={"class": "form-control", "min": 1}
            ),
            "shift_type": forms.Select(attrs={"class": "form-select"}),
        }


StaffingPlanItemFormSet = inlineformset_factory(
    StaffingPlan,
    StaffingPlanItem,
    form=StaffingPlanItemForm,
    extra=0,
    can_delete=True,
)


class AssignmentCreateForm(forms.Form):
    person = forms.ModelChoiceField(
        queryset=Person.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="Select person…",
        required=True,
    )

    assigned_on = forms.DateField(
        required=False,
        initial=date.today,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        label="Assigned on",
    )

    def __init__(
        self, *args, company=None, item: StaffingPlanItem | None = None, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.company = company
        self.item = item
        self.fields["person"].queryset = Person.objects.all().order_by(
            "first_name", "family_name"
        )

    def clean(self):
        cleaned = super().clean()
        person: Person | None = cleaned.get("person")

        if self.company is None or self.item is None or person is None:
            return cleaned

        active_employment = (
            StaffEmployment.objects.filter(person=person, is_active=True)
            .select_related("company")
            .first()
        )
        if (
            active_employment is not None
            and active_employment.company_id != self.company.id
        ):
            company_name = (
                active_employment.company.name_short or active_employment.company.name
            )
            raise ValidationError(
                f"This person is already actively employed by {company_name}."
            )

        # Position.type: "local" / "expat" / "any"
        # Person.residency_status: "LOCAL" / "EXPAT"
        pos_type = (self.item.position.type or "").strip().lower()

        if pos_type in ("local", "expat"):
            required_status = "LOCAL" if pos_type == "local" else "EXPAT"
            if person.residency_status != required_status:
                raise ValidationError(
                    f"This position requires {required_status} staff."
                )

        occupied = StaffingAssignment.objects.filter(
            staffing_plan_item=self.item,
            is_active=True,
        ).count()
        if occupied >= self.item.position_qty:
            raise ValidationError("No vacant slots for this position/shift type.")

        if StaffingAssignment.objects.filter(
            staffing_plan_item=self.item,
            person=person,
            is_active=True,
        ).exists():
            raise ValidationError("This person is already assigned to this slot.")

        if StaffingAssignment.objects.filter(person=person, is_active=True).exists():
            raise ValidationError(
                "This person already has an active assignment and cannot be assigned again."
            )

        return cleaned

    def save(self) -> StaffingAssignment:
        if self.company is None or self.item is None:
            raise ValueError("company and item are required")

        person: Person = self.cleaned_data["person"]

        emp, _created = StaffEmployment.objects.update_or_create(
            company=self.company,
            person=person,
            defaults={"is_active": True, "terminated_on": None},
        )
        if emp.hired_on is None:
            emp.hired_on = date.today()
            emp.save(update_fields=["hired_on"])

        assignment, _ = StaffingAssignment.objects.update_or_create(
            staffing_plan_item=self.item,
            person=person,
            defaults={
                "company": self.company,
                "is_active": True,
                "released_at": None,
            },
        )
        return assignment


# =========================
# Base distribution by shifts (A/B/C)
# =========================
class ShiftMembershipForm(forms.ModelForm):
    class Meta:
        model = ShiftMembership
        fields = ["person", "shift", "is_active"]
        widgets = {
            "person": forms.Select(attrs={"class": "form-select"}),
            "shift": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        if company is not None:
            self.fields["shift"].queryset = Shift.objects.filter(
                company=company,
                is_active=True,
            )
        self.fields["person"].queryset = Person.objects.all().order_by(
            "family_name",
            "first_name",
            "second_name",
        )


# =========================
# Absences (sick/vac/off)
# =========================
class StaffAbsenceForm(forms.ModelForm):
    class Meta:
        model = StaffAbsence
        fields = ["person", "absence_type", "date_from", "date_to", "note", "is_active"]
        widgets = {
            "person": forms.Select(attrs={"class": "form-select"}),
            "absence_type": forms.Select(attrs={"class": "form-select"}),
            "date_from": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "date_to": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "note": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["person"].queryset = Person.objects.all().order_by(
            "family_name",
            "first_name",
            "second_name",
        )

    def clean(self):
        cleaned = super().clean()
        df = cleaned.get("date_from")
        dt = cleaned.get("date_to")
        if df and dt and dt < df:
            raise ValidationError("date_to must be >= date_from.")
        return cleaned


# =========================
# Roster override (one-day replacement)
# =========================
class RosterOverrideForm(forms.ModelForm):
    class Meta:
        model = RosterOverride
        fields = [
            "day",
            "staffing_plan_item",
            "replaced_person",
            "replacement_person",
            "note",
            "is_active",
        ]
        widgets = {
            "day": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "staffing_plan_item": forms.Select(attrs={"class": "form-select"}),
            "replaced_person": forms.Select(attrs={"class": "form-select"}),
            "replacement_person": forms.Select(attrs={"class": "form-select"}),
            "note": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["replacement_person"].queryset = Person.objects.all().order_by(
            "family_name",
            "first_name",
            "second_name",
        )
        self.fields["replaced_person"].queryset = Person.objects.all().order_by(
            "family_name",
            "first_name",
            "second_name",
        )

        if company is not None:
            self.fields["staffing_plan_item"].queryset = (
                StaffingPlanItem.objects.filter(
                    staffing_plan__company=company
                ).select_related("position", "shift_type", "staffing_plan")
            )
