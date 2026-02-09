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
        fields = ["is_active"]
        widgets = {
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"})
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

    def __init__(
        self, *args, company=None, item: StaffingPlanItem | None = None, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.company = company
        self.item = item
        self.fields["person"].queryset = Person.objects.all().order_by(
            "family_name", "first_name"
        )

    def clean(self):
        cleaned = super().clean()
        person: Person | None = cleaned.get("person")

        if self.company is None or self.item is None or person is None:
            return cleaned

        occupied = StaffingAssignment.objects.filter(
            staffing_plan_item=self.item, is_active=True
        ).count()
        if occupied >= self.item.position_qty:
            raise ValidationError("No vacant slots for this position/shift type.")

        if StaffingAssignment.objects.filter(
            staffing_plan_item=self.item, person=person, is_active=True
        ).exists():
            raise ValidationError("This person is already assigned to this slot.")

        return cleaned

    def save(self) -> StaffingAssignment:
        if self.company is None or self.item is None:
            raise ValueError("company and item are required")

        person: Person = self.cleaned_data["person"]

        # Employment: update_or_create (не затираем hired_on если уже есть)
        emp, created = StaffEmployment.objects.update_or_create(
            company=self.company,
            person=person,
            defaults={"is_active": True, "terminated_on": None},
        )
        if created and emp.hired_on is None:
            emp.hired_on = date.today()
            emp.save(update_fields=["hired_on"])
        elif (not created) and emp.hired_on is None:
            emp.hired_on = date.today()
            emp.save(update_fields=["hired_on"])

        # Assignment: update_or_create по UNIQUE(item, person)
        assignment, _ = StaffingAssignment.objects.update_or_create(
            staffing_plan_item=self.item,
            person=person,
            defaults={"company": self.company, "is_active": True, "released_at": None},
        )
        return assignment
