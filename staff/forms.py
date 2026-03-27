from __future__ import annotations

from datetime import date, timedelta

from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from django.db import models


from persons.models import Person

from .models import (
    LeaveType,
    Position,
    RosterOverride,
    Shift,
    ShiftMembership,
    ShiftType,
    StaffAbsence,
    StaffingAssignment,
    StaffingPlan,
    StaffingPlanItem,
    TemporaryCover,
)


def _next_free_code_letter(existing_codes: list[str]) -> str:
    existing = {str(code or "").strip().upper() for code in existing_codes if code}

    def index_to_code(index: int) -> str:
        result = ""
        n = index
        while True:
            n, rem = divmod(n, 26)
            result = chr(65 + rem) + result
            if n == 0:
                break
            n -= 1
        return result

    i = 0
    while True:
        code = index_to_code(i)
        if code not in existing:
            return code
        i += 1


def evaluate_shift_pattern(
    *,
    company,
    days_on,
    days_off,
    exclude_pk: int | None = None,
) -> dict:
    result = {
        "pattern": "",
        "error": "",
        "duplicate_message": "",
        "duplicate_kind": "",
        "existing_obj": None,
    }

    if company is None:
        return result

    if days_on in (None, "") or days_off in (None, ""):
        return result

    try:
        days_on = int(days_on)
        days_off = int(days_off)
    except (TypeError, ValueError):
        result["error"] = "Days on/off must be integers."
        return result

    if days_on <= 0:
        result["error"] = "Days on must be greater than 0."
        return result

    if days_off < 0:
        result["error"] = "Days off must be 0 or greater."
        return result

    result["pattern"] = f"{days_on}/{days_off}"

    if days_off % days_on != 0:
        result["error"] = "Days off must be divisible by days on."
        return result

    qs = ShiftType.objects.filter(
        company=company,
        shift_days_on=days_on,
        shift_days_off=days_off,
    )
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    existing = qs.order_by("-is_active", "code_letter", "shift_type_name").first()
    if existing is not None:
        result["existing_obj"] = existing
        if existing.is_active:
            result["duplicate_kind"] = "active"
            result["duplicate_message"] = (
                f"Shift type already exists and is active: "
                f"{existing.code_letter} — {existing.shift_type_name} "
                f"({existing.shift_type_short})."
            )
        else:
            result["duplicate_kind"] = "inactive"
            result["duplicate_message"] = (
                f"Matching shift type already exists but is inactive: "
                f"{existing.code_letter} — {existing.shift_type_name} "
                f"({existing.shift_type_short}). "
                f"You can activate the existing record instead of creating a new one."
            )

    return result


class PersonAssignmentChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj: Person) -> str:
        full_name = " ".join(
            part for part in [obj.first_name, obj.second_name, obj.family_name] if part
        ).strip()
        residency = (obj.residency_status or "").strip()
        return f"{obj.person_id} | {full_name} | {residency}"


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
            "code_letter",
            "shift_type_name",
            "shift_type_short",
            "shift_days_on",
            "shift_days_off",
            "is_active",
        ]
        widgets = {
            "code_letter": forms.TextInput(attrs={"class": "form-control"}),
            "shift_type_name": forms.TextInput(attrs={"class": "form-control"}),
            "shift_type_short": forms.TextInput(
                attrs={"class": "form-control", "readonly": "readonly"}
            ),
            "shift_days_on": forms.NumberInput(
                attrs={"class": "form-control", "min": 1}
            ),
            "shift_days_off": forms.NumberInput(
                attrs={"class": "form-control", "min": 0}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(
        self,
        *args,
        company=None,
        is_create=False,
        preview_url: str = "",
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.company = company
        self.is_create = is_create
        self.pattern_feedback = {
            "pattern": "",
            "error": "",
            "duplicate_message": "",
            "duplicate_kind": "",
            "existing_obj": None,
        }

        # Это вычисляемое поле, не требуем его от пользователя в POST
        self.fields["shift_type_short"].required = False

        if self.is_create:
            existing_codes = list(
                ShiftType.objects.filter(company=company).values_list(
                    "code_letter", flat=True
                )
            )
            next_code = _next_free_code_letter(existing_codes)
            self.fields["code_letter"].initial = next_code
            self.fields["code_letter"].required = False
            self.fields["code_letter"].widget = forms.HiddenInput()

        if preview_url:
            hx_attrs = {
                "hx-post": preview_url,
                "hx-trigger": "input changed delay:300ms",
                "hx-target": "#pattern-preview-block",
                "hx-swap": "outerHTML",
                "hx-include": "closest form",
            }
            self.fields["shift_days_on"].widget.attrs.update(hx_attrs)
            self.fields["shift_days_off"].widget.attrs.update(hx_attrs)

    def clean(self):
        cleaned = super().clean()

        company = self.company
        days_on = cleaned.get("shift_days_on")
        days_off = cleaned.get("shift_days_off")
        shift_type_name = (cleaned.get("shift_type_name") or "").strip()

        if self.is_create and company is not None:
            existing_codes = list(
                ShiftType.objects.filter(company=company).values_list(
                    "code_letter", flat=True
                )
            )
            cleaned["code_letter"] = _next_free_code_letter(existing_codes)

        feedback = evaluate_shift_pattern(
            company=company,
            days_on=days_on,
            days_off=days_off,
            exclude_pk=self.instance.pk if self.instance.pk else None,
        )
        self.pattern_feedback = feedback

        # Ключевой момент: вычисляем pattern серверно и кладём в cleaned_data
        cleaned["shift_type_short"] = feedback["pattern"]
        cleaned["shift_type_name"] = shift_type_name

        if feedback["error"]:
            self.add_error("shift_days_off", feedback["error"])

        if feedback["duplicate_kind"] == "active":
            self.add_error(None, feedback["duplicate_message"])

        if feedback["duplicate_kind"] == "inactive" and not self.is_create:
            self.add_error(None, feedback["duplicate_message"])

        return cleaned


class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = ["shift_type", "shift_no", "anchor_date", "is_active"]
        widgets = {
            "shift_type": forms.Select(attrs={"class": "form-select"}),
            "shift_no": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "anchor_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ShiftPackageCreateForm(forms.Form):
    shift_type = forms.ModelChoiceField(
        queryset=ShiftType.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        required=True,
        label="Shift type",
    )

    first_anchor_date = forms.DateField(
        required=True,
        initial=date.today,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        label="First shift duty date",
    )

    is_active = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Active",
    )

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company

        if company is not None:
            self.fields["shift_type"].queryset = ShiftType.objects.filter(
                company=company,
                is_active=True,
            ).order_by("code_letter", "shift_type_short")

    def clean(self):
        cleaned = super().clean()
        shift_type: ShiftType | None = cleaned.get("shift_type")
        first_anchor_date = cleaned.get("first_anchor_date")

        if self.company is None or shift_type is None or first_anchor_date is None:
            return cleaned

        if shift_type.company_id != self.company.id:
            raise ValidationError(
                "Selected shift type does not belong to active company."
            )

        existing_qs = Shift.objects.filter(
            company=self.company,
            shift_type=shift_type,
        )
        if existing_qs.exists():
            raise ValidationError(
                f"Shift package for pattern {shift_type.code_letter} "
                f"({shift_type.shift_type_short}) already exists."
            )

        return cleaned

    def build_shifts_data(self) -> list[dict]:
        shift_type: ShiftType = self.cleaned_data["shift_type"]
        first_anchor_date: date = self.cleaned_data["first_anchor_date"]
        is_active: bool = bool(self.cleaned_data.get("is_active"))

        data: list[dict] = []
        for shift_no in range(1, shift_type.package_size + 1):
            anchor_date = first_anchor_date + timedelta(
                days=(shift_no - 1) * shift_type.shift_days_on
            )
            data.append(
                {
                    "company": self.company,
                    "shift_type": shift_type,
                    "shift_no": shift_no,
                    "shift_number": f"{shift_type.code_letter}{shift_no}",
                    "anchor_date": anchor_date,
                    "is_active": is_active,
                }
            )
        return data


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
        fields = ["position", "position_qty"]
        widgets = {
            "position": forms.Select(attrs={"class": "form-select"}),
            "position_qty": forms.NumberInput(
                attrs={"class": "form-control", "min": 1}
            ),
        }


StaffingPlanItemFormSet = inlineformset_factory(
    StaffingPlan,
    StaffingPlanItem,
    form=StaffingPlanItemForm,
    extra=0,
    can_delete=True,
)


class AssignmentCreateForm(forms.Form):
    person = PersonAssignmentChoiceField(
        queryset=Person.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="Select person…",
        required=True,
    )

    assigned_on = forms.DateField(
        required=True,
        initial=date.today,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        label="Assigned on",
    )

    released_on = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        label="Release on",
    )

    def __init__(
        self, *args, company=None, item: StaffingPlanItem | None = None, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.company = company
        self.item = item
        self.interval_conflicts: list[StaffingAssignment] = []

        qs = Person.objects.all()
        if self.company is not None:
            qs = qs.filter(company=self.company)

        self.fields["person"].queryset = qs.order_by(
            "person_id", "family_name", "first_name", "second_name"
        )

    def _intervals_overlap(
        self,
        start1: date,
        end1: date | None,
        start2: date,
        end2: date | None,
    ) -> bool:
        left_end = end1 or date.max
        right_end = end2 or date.max
        return start1 <= right_end and start2 <= left_end

    def _get_assignment_interval(
        self,
        assignment: StaffingAssignment,
    ) -> tuple[date, date | None]:
        start = assignment.assigned_at.date()
        end = assignment.released_at.date() if assignment.released_at else None
        return start, end

    def get_interval_conflicts(
        self,
        *,
        person: Person,
        start: date,
        end: date | None,
    ) -> list[StaffingAssignment]:
        qs = (
            StaffingAssignment.objects.filter(person=person)
            .select_related(
                "staffing_plan_item__position",
                "staffing_plan_item__staffing_plan",
            )
            .order_by("assigned_at", "pk")
        )

        conflicts: list[StaffingAssignment] = []
        for assignment in qs:
            a_start, a_end = self._get_assignment_interval(assignment)
            if self._intervals_overlap(start, end, a_start, a_end):
                conflicts.append(assignment)

        return conflicts

    def clean(self):
        cleaned = super().clean()
        person: Person | None = cleaned.get("person")
        assigned_on: date | None = cleaned.get("assigned_on")
        released_on: date | None = cleaned.get("released_on")

        if assigned_on and released_on and released_on < assigned_on:
            self.add_error(
                "released_on",
                "Release date cannot be earlier than assignment date.",
            )

        if (
            self.company is None
            or self.item is None
            or person is None
            or assigned_on is None
        ):
            return cleaned

        if person.company_id != self.company.id:
            raise ValidationError(
                "You can assign only persons created under the active company."
            )

        pos_type = (self.item.position.type or "").strip().lower()

        if pos_type in ("local", "expat"):
            required_status = "LOCAL" if pos_type == "local" else "EXPAT"
            if person.residency_status != required_status:
                raise ValidationError(
                    f"This position requires {required_status} staff."
                )

        self.interval_conflicts = self.get_interval_conflicts(
            person=person,
            start=assigned_on,
            end=released_on,
        )

        if self.interval_conflicts:
            raise ValidationError(
                "This person already has assignment(s) overlapping with the selected period."
            )

        return cleaned

    def save(self, commit: bool = True) -> StaffingAssignment:
        if self.company is None or self.item is None:
            raise ValueError("company and item are required")

        person: Person = self.cleaned_data["person"]

        assignment = StaffingAssignment(
            staffing_plan_item=self.item,
            person=person,
            company=self.company,
            is_active=True,
            released_at=None,
        )

        if commit:
            assignment.save()

        return assignment


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
                company=company, is_active=True
            ).select_related("shift_type")
        self.fields["person"].queryset = Person.objects.all().order_by(
            "family_name", "first_name", "second_name"
        )


class StaffAbsenceForm(forms.ModelForm):
    class Meta:
        model = StaffAbsence
        fields = ["person", "leave_type", "date_from", "date_to", "note", "is_active"]
        widgets = {
            "person": forms.Select(attrs={"class": "form-select"}),
            "leave_type": forms.Select(attrs={"class": "form-select"}),
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
            "family_name", "first_name", "second_name"
        )
        self.fields["leave_type"].queryset = LeaveType.objects.filter(
            is_active=True
        ).order_by("name")

    def clean(self):
        cleaned = super().clean()
        df = cleaned.get("date_from")
        dt = cleaned.get("date_to")
        if df and dt and dt < df:
            raise ValidationError("date_to must be >= date_from.")
        return cleaned


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
            "family_name", "first_name", "second_name"
        )
        self.fields["replaced_person"].queryset = Person.objects.all().order_by(
            "family_name", "first_name", "second_name"
        )

        if company is not None:
            self.fields["staffing_plan_item"].queryset = (
                StaffingPlanItem.objects.filter(
                    staffing_plan__company=company
                ).select_related("position", "staffing_plan")
            )


class TemporaryCoverForm(forms.ModelForm):
    class AbsenceChoiceField(forms.ModelChoiceField):
        def __init__(self, *args, company=None, **kwargs):
            super().__init__(*args, **kwargs)
            self.company = company

        def label_from_instance(self, obj: StaffAbsence) -> str:
            full_name = " ".join(
                part
                for part in [
                    obj.person.first_name,
                    obj.person.second_name,
                    obj.person.family_name,
                ]
                if part
            ).strip()

            leave_code = obj.leave_type.leave_code if obj.leave_type_id else "—"
            period = f"{obj.date_from:%d.%m.%Y} – {obj.date_to:%d.%m.%Y}"

            position_name = "No position"
            shift_label = "No shift"

            if self.company is not None:
                assignment = (
                    StaffingAssignment.objects.filter(
                        company=self.company,
                        person=obj.person,
                        assigned_at__date__lte=obj.date_to,
                    )
                    .filter(
                        models.Q(released_at__isnull=True)
                        | models.Q(released_at__date__gte=obj.date_from)
                    )
                    .select_related("staffing_plan_item__position")
                    .order_by("-assigned_at")
                    .first()
                )
                if (
                    assignment
                    and assignment.staffing_plan_item
                    and assignment.staffing_plan_item.position
                ):
                    position_name = (
                        assignment.staffing_plan_item.position.name_short
                        or assignment.staffing_plan_item.position.name_long
                    )

                membership = (
                    ShiftMembership.objects.filter(
                        company=self.company,
                        person=obj.person,
                        is_active=True,
                    )
                    .select_related("shift")
                    .order_by("-assigned_at")
                    .first()
                )
                if membership and membership.shift:
                    shift_label = membership.shift.shift_number

            return (
                f"{full_name} | {leave_code} | {period} | "
                f"{position_name} | {shift_label}"
            )

    class CoveringPersonChoiceField(forms.ModelChoiceField):
        def __init__(self, *args, company=None, **kwargs):
            super().__init__(*args, **kwargs)
            self.company = company

        def label_from_instance(self, obj: Person) -> str:
            full_name = " ".join(
                part
                for part in [obj.first_name, obj.second_name, obj.family_name]
                if part
            ).strip()

            position_name = "No position"
            shift_label = "No shift"

            if self.company is not None:
                assignment = (
                    StaffingAssignment.objects.filter(
                        company=self.company,
                        person=obj,
                        is_active=True,
                    )
                    .select_related("staffing_plan_item__position")
                    .order_by("-assigned_at")
                    .first()
                )
                if (
                    assignment
                    and assignment.staffing_plan_item
                    and assignment.staffing_plan_item.position
                ):
                    position_name = (
                        assignment.staffing_plan_item.position.name_short
                        or assignment.staffing_plan_item.position.name_long
                    )

                membership = (
                    ShiftMembership.objects.filter(
                        company=self.company,
                        person=obj,
                        is_active=True,
                    )
                    .select_related("shift")
                    .order_by("-assigned_at")
                    .first()
                )
                if membership and membership.shift:
                    shift_label = membership.shift.shift_number

            return f"{full_name} | {position_name} | {shift_label}"

    class Meta:
        model = TemporaryCover
        fields = [
            "absence",
            "date_from",
            "date_to",
            "covering_person",
            "note",
            "is_active",
        ]
        widgets = {
            "date_from": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "date_to": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "note": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company

        self.fields["absence"] = self.AbsenceChoiceField(
            queryset=StaffAbsence.objects.none(),
            widget=forms.Select(attrs={"class": "form-select"}),
            required=True,
            label="Absence",
            company=company,
        )

        self.fields["covering_person"] = self.CoveringPersonChoiceField(
            queryset=Person.objects.none(),
            widget=forms.Select(attrs={"class": "form-select"}),
            required=True,
            label="Covering person",
            company=company,
        )

        if company is not None:
            self.fields["absence"].queryset = (
                StaffAbsence.objects.filter(company=company)
                .select_related("person", "leave_type")
                .order_by(
                    "-date_from",
                    "-date_to",
                    "person__family_name",
                    "person__first_name",
                )
            )

            self.fields["covering_person"].queryset = Person.objects.filter(
                company=company
            ).order_by("family_name", "first_name", "second_name")

        absence = None
        if self.is_bound:
            absence_raw = (self.data.get("absence") or "").strip()
            if absence_raw.isdigit() and company is not None:
                absence = (
                    StaffAbsence.objects.filter(company=company, pk=int(absence_raw))
                    .select_related("person", "leave_type")
                    .first()
                )
        else:
            absence = self.initial.get("absence")

        if isinstance(absence, StaffAbsence):
            if not self.initial.get("date_from"):
                self.initial["date_from"] = absence.date_from
            if not self.initial.get("date_to"):
                self.initial["date_to"] = absence.date_to

    def _find_staffing_plan_item(
        self,
        *,
        absence: StaffAbsence,
        date_from: date,
        date_to: date,
    ) -> StaffingPlanItem | None:
        assignment = (
            StaffingAssignment.objects.filter(
                company=self.company,
                person=absence.person,
                assigned_at__date__lte=date_to,
            )
            .filter(
                models.Q(released_at__isnull=True)
                | models.Q(released_at__date__gte=date_from)
            )
            .select_related("staffing_plan_item", "staffing_plan_item__position")
            .order_by("-assigned_at")
            .first()
        )

        if assignment:
            return assignment.staffing_plan_item
        return None

    def clean(self):
        cleaned = super().clean()

        absence = cleaned.get("absence")
        date_from = cleaned.get("date_from")
        date_to = cleaned.get("date_to")
        covering_person = cleaned.get("covering_person")

        if self.company is None:
            raise ValidationError("Active company is not selected.")

        if absence and absence.company_id != self.company.id:
            self.add_error(
                "absence", "Selected absence does not belong to active company."
            )

        if covering_person and covering_person.company_id != self.company.id:
            self.add_error(
                "covering_person",
                "Selected person does not belong to active company.",
            )

        if date_from and date_to and date_to < date_from:
            self.add_error(
                "date_to",
                "Cover end date cannot be earlier than cover start date.",
            )

        if absence and date_from and date_to:
            if date_from < absence.date_from or date_to > absence.date_to:
                self.add_error(
                    "date_from",
                    "Cover period must be inside linked absence period.",
                )
                self.add_error(
                    "date_to",
                    "Cover period must be inside linked absence period.",
                )

            staffing_plan_item = self._find_staffing_plan_item(
                absence=absence,
                date_from=date_from,
                date_to=date_to,
            )
            if staffing_plan_item is None:
                raise ValidationError(
                    "Cannot determine staffing plan position for the selected absence period."
                )

            cleaned["staffing_plan_item"] = staffing_plan_item

        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.company is not None:
            obj.company = self.company
        obj.staffing_plan_item = self.cleaned_data["staffing_plan_item"]
        if commit:
            obj.save()
        return obj