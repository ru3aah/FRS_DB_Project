from django import forms
from django.forms import inlineformset_factory

from .models import Position, ShiftType, Shift, StaffingPlan, StaffingPlanItem


# -------------------------
# Positions
# -------------------------
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


# -------------------------
# Shift Types
# -------------------------
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


# -------------------------
# Shifts
# -------------------------
class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = ["shift_number", "shift_type", "is_active"]
        widgets = {
            "shift_number": forms.TextInput(attrs={"class": "form-control"}),
            "shift_type": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


# -------------------------
# Staffing plan
# -------------------------
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
    extra=0,  # строки добавляем кнопкой (JS)
    can_delete=True,
)
