from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Prefetch
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from companies.models import Company
from persons.models import Person

from .forms import (
    AssignmentCreateForm,
    ShiftPackageCreateForm,
    ShiftTypeForm,
    StaffingPlanForm,
    StaffingPlanItemFormSet,
    evaluate_shift_pattern,
)
from .models import (
    ExtraWork,
    LeaveType,
    Position,
    Shift,
    ShiftMembership,
    ShiftType,
    StaffAbsence,
    StaffAbsenceDocument,
    StaffingAssignment,
    StaffingPlan,
    StaffingPlanItem,
    TemporaryCover,
)


class ActiveCompanyMixin:
    def get_active_company(self) -> Company | None:
        company_id = self.request.session.get("active_company_id")
        if not company_id:
            return None
        return Company.objects.filter(pk=company_id).first()


class StaffHomeView(LoginRequiredMixin, TemplateView):
    template_name = "staff/index.html"


def _get_active_plan(company: Company) -> StaffingPlan | None:
    return (
        StaffingPlan.objects.filter(company=company, is_active=True)
        .order_by("-updated_at")
        .first()
    )


def _dt_to_local_date(dt) -> date | None:
    if not dt:
        return None
    if timezone.is_aware(dt):
        return timezone.localtime(dt).date()
    return dt.date()


def _assignment_is_effective_on_day(
    assignment: StaffingAssignment,
    target_day: date,
) -> bool:
    start_day = _dt_to_local_date(assignment.assigned_at)
    end_day = _dt_to_local_date(assignment.released_at)

    if start_day is None:
        return False

    if target_day < start_day:
        return False

    if end_day is not None and target_day > end_day:
        return False

    return True


def _assignment_status_on_day(
    assignment: StaffingAssignment,
    target_day: date,
) -> str:
    start_day = _dt_to_local_date(assignment.assigned_at)
    end_day = _dt_to_local_date(assignment.released_at)

    if start_day is None:
        return "Closed"

    if start_day > target_day:
        return "Future"

    if end_day is not None and end_day < target_day:
        return "Closed"

    return "Active"


def _get_people_from_active_plan(
    company: Company, plan: StaffingPlan
) -> tuple[list[dict], set[int]]:
    assignments = list(
        StaffingAssignment.objects.filter(
            company=company,
            is_active=True,
            staffing_plan_item__staffing_plan=plan,
        )
        .select_related("person", "staffing_plan_item__position")
        .order_by(
            "staffing_plan_item__position__name_long",
            "person__family_name",
            "person__first_name",
            "person__second_name",
        )
    )

    person_ids: set[int] = set()
    person_to_position: dict[int, Position] = {}
    person_to_assignment: dict[int, StaffingAssignment] = {}
    person_to_person: dict[int, Person] = {}

    for a in assignments:
        pid = a.person_id
        if pid in person_ids:
            continue
        person_ids.add(pid)
        person_to_position[pid] = a.staffing_plan_item.position
        person_to_assignment[pid] = a
        person_to_person[pid] = a.person

    memberships = list(
        ShiftMembership.objects.filter(
            company=company, is_active=True, person_id__in=person_ids
        ).select_related("shift", "shift__shift_type")
    )
    person_to_membership: dict[int, ShiftMembership] = {
        m.person_id: m for m in memberships
    }

    rows: list[dict] = []
    for a in assignments:
        pid = a.person_id
        p = person_to_person.get(pid)
        if p is None:
            continue
        rows.append(
            {
                "person": p,
                "position": person_to_position.get(pid),
                "assignment": person_to_assignment.get(pid),
                "membership": person_to_membership.get(pid),
            }
        )

    return rows, person_ids


class StaffShiftMembershipView(LoginRequiredMixin, ActiveCompanyMixin, TemplateView):
    template_name = "staff/staff.html"

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            messages.error(request, "Active company is not selected.")
            return redirect("staff:staff_members")

        plan = (
            StaffingPlan.objects.filter(company=company, is_active=True)
            .order_by("-updated_at")
            .first()
        )
        if plan is None:
            messages.error(request, "No active staffing plan found.")
            return redirect("staff:staff_members")

        person_id_raw = (request.POST.get("person_id") or "").strip()
        shift_id_raw = (request.POST.get("shift_id") or "").strip()

        try:
            person_id = int(person_id_raw)
        except ValueError:
            messages.error(request, "Invalid person.")
            return redirect("staff:staff_members")

        in_plan = StaffingAssignment.objects.filter(
            company=company,
            is_active=True,
            staffing_plan_item__staffing_plan=plan,
            person_id=person_id,
        ).exists()
        if not in_plan:
            messages.error(
                request, "This person is not assigned in the active staffing plan."
            )
            return redirect("staff:staff_members")

        shift = None
        if shift_id_raw:
            try:
                shift_id = int(shift_id_raw)
            except ValueError:
                messages.error(request, "Invalid shift.")
                return redirect("staff:staff_members")

            shift = get_object_or_404(Shift, pk=shift_id, company=company)

        now_dt = timezone.now()

        with transaction.atomic():
            ShiftMembership.objects.filter(
                company=company,
                person_id=person_id,
                is_active=True,
            ).update(is_active=False, released_at=now_dt)

            if shift is not None:
                ShiftMembership.objects.create(
                    company=company,
                    person_id=person_id,
                    shift=shift,
                    is_active=True,
                )

        if shift is None:
            messages.success(request, "Shift assignment cleared.")
        else:
            messages.success(request, f"Assigned to shift {shift.shift_number}.")

        return redirect("staff:staff_members")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        company = self.get_active_company()
        ctx["active_company"] = company

        if company is None:
            ctx["plan"] = None
            ctx["shift_groups"] = []
            ctx["unassigned_rows"] = []
            ctx["shifts"] = []
            return ctx

        plan = _get_active_plan(company)
        ctx["plan"] = plan
        if plan is None:
            ctx["shift_groups"] = []
            ctx["unassigned_rows"] = []
            ctx["shifts"] = []
            return ctx

        shifts = list(
            Shift.objects.filter(company=company, is_active=True)
            .select_related("shift_type")
            .order_by("shift_type__code_letter", "shift_no")
        )
        ctx["shifts"] = shifts

        rows, _person_ids = _get_people_from_active_plan(company, plan)

        assigned_rows: list[dict] = []
        unassigned_rows: list[dict] = []
        for r in rows:
            m = r.get("membership")
            if m is not None and m.shift_id:
                assigned_rows.append(r)
            else:
                unassigned_rows.append(r)

        def _row_sort_key(r: dict):
            p: Person = r["person"]
            pos: Position | None = r.get("position")
            return (
                ((pos.name_long or "") if pos else "").lower(),
                (p.family_name or "").lower(),
                (p.first_name or "").lower(),
                (p.second_name or "").lower(),
            )

        shift_groups = []
        for sh in shifts:
            group_rows = [
                r
                for r in assigned_rows
                if r.get("membership") is not None
                and r["membership"].shift_id == sh.shift_id
            ]
            if not group_rows:
                continue

            shift_groups.append(
                {
                    "shift": sh,
                    "rows": sorted(group_rows, key=_row_sort_key),
                }
            )

        ctx["shift_groups"] = shift_groups
        ctx["unassigned_rows"] = sorted(unassigned_rows, key=_row_sort_key)
        return ctx


def _parse_date_from_post(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _combine_date_as_day_start(chosen_date):
    if chosen_date is None:
        chosen_date = timezone.localdate()

    dt = datetime(
        year=chosen_date.year,
        month=chosen_date.month,
        day=chosen_date.day,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    return timezone.make_aware(dt, timezone.get_current_timezone())


def _combine_date_as_day_end(chosen_date):
    if chosen_date is None:
        chosen_date = timezone.localdate()

    dt = datetime(
        year=chosen_date.year,
        month=chosen_date.month,
        day=chosen_date.day,
        hour=23,
        minute=59,
        second=59,
        microsecond=999999,
    )
    return timezone.make_aware(dt, timezone.get_current_timezone())


def _get_month_start_end(month_str: str | None) -> tuple[date, date]:
    today = timezone.localdate()
    if month_str:
        try:
            y, m = month_str.split("-")
            first = date(int(y), int(m), 1)
        except Exception:
            first = date(today.year, today.month, 1)
    else:
        first = date(today.year, today.month, 1)

    last_day = monthrange(first.year, first.month)[1]
    last = date(first.year, first.month, last_day)
    return first, last


def _is_absent(
    absences_by_person: dict[int, list[tuple[date, date]]], person_id: int, day: date
) -> bool:
    for d1, d2 in absences_by_person.get(person_id, []):
        if d1 <= day <= d2:
            return True
    return False


def _get_leave_code_for_day(
    absences_by_person: dict[int, list[dict]], person_id: int, day: date
) -> str | None:
    for item in absences_by_person.get(person_id, []):
        date_from = item.get("date_from")
        date_to = item.get("date_to")
        leave_code = item.get("leave_code")

        if date_from and date_to and date_from <= day <= date_to and leave_code:
            return leave_code

    return None


def _get_work_override_code_for_day(
    *,
    company_id: int | None,
    person_id: int | None,
    day: date | None,
) -> str | None:
    if not company_id or not person_id or not day:
        return None

    temp_cover = (
        TemporaryCover.objects.filter(
            company_id=company_id,
            day=day,
            covering_person_id=person_id,
            is_active=True,
        )
        .select_related("staffing_plan_item__position")
        .first()
    )
    if (
        temp_cover
        and temp_cover.staffing_plan_item
        and temp_cover.staffing_plan_item.position
    ):
        return temp_cover.staffing_plan_item.position.roster_code or None

    extra_work = (
        ExtraWork.objects.filter(
            company_id=company_id,
            day=day,
            person_id=person_id,
            is_active=True,
        )
        .select_related("staffing_plan_item__position")
        .first()
    )
    if (
        extra_work
        and extra_work.staffing_plan_item
        and extra_work.staffing_plan_item.position
    ):
        return extra_work.staffing_plan_item.position.roster_code or None

    return None


class StaffRosterView(LoginRequiredMixin, ActiveCompanyMixin, TemplateView):
    template_name = "staff/roster.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        company = self.get_active_company()
        ctx["active_company"] = company

        month_str = self.request.GET.get("month")
        month_start, month_end = _get_month_start_end(month_str)
        ctx["month_start"] = month_start
        ctx["month_end"] = month_end
        ctx["month_param"] = f"{month_start.year:04d}-{month_start.month:02d}"

        prev_month = (month_start.replace(day=1) - timedelta(days=1)).replace(day=1)
        next_month = (month_end + timedelta(days=1)).replace(day=1)

        ctx["prev_month_param"] = f"{prev_month.year:04d}-{prev_month.month:02d}"
        ctx["next_month_param"] = f"{next_month.year:04d}-{next_month.month:02d}"

        if company is None:
            ctx["plan"] = None
            ctx["days"] = []
            ctx["day_headers"] = []
            ctx["shift_groups"] = []
            return ctx

        plan = (
            StaffingPlan.objects.filter(company=company, is_active=True)
            .order_by("-updated_at")
            .first()
        )
        ctx["plan"] = plan

        if plan is None:
            ctx["days"] = []
            ctx["day_headers"] = []
            ctx["shift_groups"] = []
            return ctx

        days = []
        d = month_start
        while d <= month_end:
            days.append(d)
            d += timedelta(days=1)
        ctx["days"] = days

        weekend_days = set(getattr(settings, "WEEKEND_DAYS", (5, 6)))

        day_headers = []
        for day in days:
            weekday_short = day.strftime("%a")[:2]
            day_headers.append(
                {
                    "date": day,
                    "weekday_short": weekday_short,
                    "day_num": day.day,
                    "is_weekend": day.weekday() in weekend_days,
                }
            )
        ctx["day_headers"] = day_headers

        assignments = list(
            StaffingAssignment.objects.filter(
                company=company,
                staffing_plan_item__staffing_plan=plan,
            )
            .select_related("person", "staffing_plan_item__position")
            .order_by(
                "staffing_plan_item__position__name_long",
                "person__family_name",
                "person__first_name",
                "person__second_name",
                "assigned_at",
            )
        )

        effective_assignments = []
        for a in assignments:
            start_day = _dt_to_local_date(a.assigned_at)
            end_day = _dt_to_local_date(a.released_at)

            if start_day is None:
                continue
            if start_day > month_end:
                continue
            if end_day is not None and end_day < month_start:
                continue

            effective_assignments.append(a)

        memberships = list(
            ShiftMembership.objects.filter(company=company)
            .select_related("shift", "shift__shift_type", "person")
            .order_by("-assigned_at")
        )

        person_to_membership: dict[int, ShiftMembership] = {}
        for m in memberships:
            if m.person_id not in person_to_membership:
                person_to_membership[m.person_id] = m

        absences = list(
            StaffAbsence.objects.filter(
                company=company,
                is_active=True,
                date_from__lte=month_end,
                date_to__gte=month_start,
            ).select_related("person", "leave_type")
        )
        absences_by_person: dict[int, list[dict]] = {}
        for ab in absences:
            absences_by_person.setdefault(ab.person_id, []).append(
                {
                    "date_from": ab.date_from,
                    "date_to": ab.date_to,
                    "leave_code": (
                        ab.leave_type.leave_code
                        if ab.leave_type_id and ab.leave_type
                        else None
                    ),
                }
            )

        shifts = list(
            Shift.objects.filter(company=company, is_active=True)
            .select_related("shift_type")
            .order_by("shift_type__code_letter", "shift_no")
        )

        day_to_shift_codes: dict[date, list[str]] = {}
        for shift in shifts:
            for day in days:
                if shift.anchor_date and shift.is_on_duty(day):
                    day_to_shift_codes.setdefault(day, []).append(shift.shift_number)

        grouped: dict[str, list[dict]] = {}

        seq = 1
        for a in effective_assignments:
            person = a.person
            position = a.staffing_plan_item.position
            membership = person_to_membership.get(person.person_id)
            shift = membership.shift if membership else None

            start_day = _dt_to_local_date(a.assigned_at)
            end_day = _dt_to_local_date(a.released_at)

            cells = []
            for day in days:
                if start_day and day < start_day:
                    cells.append("--")
                    continue

                if end_day is not None and day > end_day:
                    cells.append("--")
                    continue

                leave_code = _get_leave_code_for_day(
                    absences_by_person, person.person_id, day
                )
                if leave_code:
                    cells.append(leave_code)
                    continue

                work_override_code = _get_work_override_code_for_day(
                    company_id=company.pk,
                    person_id=person.person_id,
                    day=day,
                )
                if work_override_code:
                    cells.append(work_override_code)
                    continue

                if shift is None or shift.anchor_date is None:
                    cells.append("--")
                    continue

                if shift.is_on_duty(day):
                    cells.append("WD")
                else:
                    cells.append("NN")

            shift_label = shift.shift_number if shift else "No shift"

            grouped.setdefault(shift_label, []).append(
                {
                    "seq": seq,
                    "person": person,
                    "position": position.name_long if position else "",
                    "shift": shift_label,
                    "cells": cells,
                }
            )
            seq += 1

        shift_groups = []
        for shift_label in sorted(grouped.keys()):
            shift_groups.append(
                {
                    "shift_label": shift_label,
                    "rows": grouped[shift_label],
                }
            )

        ctx["shift_groups"] = shift_groups
        ctx["day_to_shift_codes"] = day_to_shift_codes
        ctx["absences_by_person"] = absences_by_person
        return ctx


class PositionListView(LoginRequiredMixin, ActiveCompanyMixin, ListView):
    model = Position
    template_name = "staff/positions_list.html"
    context_object_name = "positions"
    paginate_by = 10

    def get_queryset(self):
        company = self.get_active_company()
        if company is None:
            return Position.objects.none()
        qs = Position.objects.filter(company=company)
        if self.request.GET.get("show") != "all":
            qs = qs.filter(is_active=True)
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["active_company"] = self.get_active_company()
        show_all = self.request.GET.get("show") == "all"
        ctx["show_all"] = show_all
        if show_all:
            ctx["toggle_filter_url"] = reverse("staff:positions_list")
            ctx["toggle_filter_label"] = "Show only active"
        else:
            ctx["toggle_filter_url"] = f"{reverse('staff:positions_list')}?show=all"
            ctx["toggle_filter_label"] = "Show all"
        return ctx


class PositionCreateView(LoginRequiredMixin, ActiveCompanyMixin, CreateView):
    model = Position
    template_name = "staff/positions_form.html"
    fields = ["name_long", "name_short", "roster_code", "type", "is_active"]
    success_url = reverse_lazy("staff:positions_list")

    def form_valid(self, form):
        company = self.get_active_company()
        if company is None:
            messages.error(self.request, "Active company is not selected.")
            return redirect("staff:positions_list")
        form.instance.company = company
        messages.success(self.request, "Position created.")
        return super().form_valid(form)


class PositionUpdateView(LoginRequiredMixin, ActiveCompanyMixin, UpdateView):
    model = Position
    template_name = "staff/positions_form.html"
    fields = ["name_long", "name_short", "roster_code", "type", "is_active"]
    success_url = reverse_lazy("staff:positions_list")

    def get_queryset(self):
        company = self.get_active_company()
        if company is None:
            return Position.objects.none()
        return Position.objects.filter(company=company)

    def form_valid(self, form):
        messages.success(self.request, "Position updated.")
        return super().form_valid(form)


class PositionDeactivateView(LoginRequiredMixin, ActiveCompanyMixin, View):
    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            messages.error(self.request, "Active company is not selected.")
            return redirect("staff:positions_list")

        obj = get_object_or_404(Position, pk=pk, company=company)
        if obj.is_active:
            obj.is_active = False
            obj.save(update_fields=["is_active"])
            messages.success(request, "Position deactivated (soft delete).")
        else:
            messages.info(request, "Position is already inactive.")

        if request.GET.get("show") == "all":
            return redirect(f"{reverse('staff:positions_list')}?show=all")
        return redirect("staff:positions_list")


class ShiftTypeListView(LoginRequiredMixin, ActiveCompanyMixin, ListView):
    model = ShiftType
    template_name = "staff/shift_types_list.html"
    context_object_name = "shift_types"
    paginate_by = 10

    def get_queryset(self):
        company = self.get_active_company()
        if company is None:
            return ShiftType.objects.none()
        qs = ShiftType.objects.filter(company=company)
        if self.request.GET.get("show") != "all":
            qs = qs.filter(is_active=True)
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["active_company"] = self.get_active_company()
        show_all = self.request.GET.get("show") == "all"
        ctx["show_all"] = show_all
        if show_all:
            ctx["toggle_filter_url"] = reverse("staff:shift_types_list")
            ctx["toggle_filter_label"] = "Show only active"
        else:
            ctx["toggle_filter_url"] = f"{reverse('staff:shift_types_list')}?show=all"
            ctx["toggle_filter_label"] = "Show all"
        return ctx


class ShiftTypePatternPreviewView(LoginRequiredMixin, ActiveCompanyMixin, View):
    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        company = self.get_active_company()

        days_on = request.POST.get("shift_days_on")
        days_off = request.POST.get("shift_days_off")
        shift_type_id_raw = (request.POST.get("shift_type_id") or "").strip()

        exclude_pk = None
        if shift_type_id_raw.isdigit():
            exclude_pk = int(shift_type_id_raw)

        feedback = evaluate_shift_pattern(
            company=company,
            days_on=days_on,
            days_off=days_off,
            exclude_pk=exclude_pk,
        )

        form = ShiftTypeForm(
            company=company,
            is_create=exclude_pk is None,
            preview_url=reverse("staff:shift_types_pattern_preview"),
        )

        return render(
            request,
            "staff/includes/shift_type_pattern_feedback.html",
            {
                "form": form,
                "pattern_value": feedback["pattern"],
                "preview_error": feedback["error"],
                "duplicate_message": feedback["duplicate_message"],
                "duplicate_kind": feedback["duplicate_kind"],
            },
        )


class ShiftTypeCreateView(LoginRequiredMixin, ActiveCompanyMixin, CreateView):
    model = ShiftType
    form_class = ShiftTypeForm
    template_name = "staff/shift_types_form.html"
    success_url = reverse_lazy("staff:shift_types_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["company"] = self.get_active_company()
        kwargs["is_create"] = True
        kwargs["preview_url"] = reverse("staff:shift_types_pattern_preview")
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["active_company"] = self.get_active_company()
        return ctx

    def form_valid(self, form):
        company = self.get_active_company()
        if company is None:
            messages.error(self.request, "Active company is not selected.")
            return redirect("staff:shift_types_list")

        feedback = form.pattern_feedback
        existing = feedback.get("existing_obj")
        duplicate_kind = feedback.get("duplicate_kind")

        if duplicate_kind == "inactive" and existing is not None:
            if self.request.POST.get("activate_existing") == "1":
                existing.is_active = True
                existing.save(update_fields=["is_active"])
                messages.success(
                    self.request,
                    f"Existing shift type activated: "
                    f"{existing.code_letter} — {existing.shift_type_name}.",
                )
                return redirect("staff:shift_types_edit", pk=existing.pk)

            return self.form_invalid(form)

        form.instance.company = company
        response = super().form_valid(form)
        messages.success(self.request, "Shift type created.")
        return response


class ShiftTypeUpdateView(LoginRequiredMixin, ActiveCompanyMixin, UpdateView):
    model = ShiftType
    form_class = ShiftTypeForm
    template_name = "staff/shift_types_form.html"
    success_url = reverse_lazy("staff:shift_types_list")

    def get_queryset(self):
        company = self.get_active_company()
        if company is None:
            return ShiftType.objects.none()
        return ShiftType.objects.filter(company=company)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["company"] = self.get_active_company()
        kwargs["is_create"] = False
        kwargs["preview_url"] = reverse("staff:shift_types_pattern_preview")
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["active_company"] = self.get_active_company()
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Shift type updated.")
        return response


class ShiftTypeActivateView(LoginRequiredMixin, ActiveCompanyMixin, View):
    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            messages.error(request, "Active company is not selected.")
            return redirect("staff:shift_types_list")

        obj = get_object_or_404(ShiftType, pk=pk, company=company)

        if obj.is_active:
            messages.info(request, "Shift type is already active.")
        else:
            obj.is_active = True
            obj.save(update_fields=["is_active"])
            messages.success(request, "Shift type activated.")

        if request.GET.get("show") == "all":
            return redirect(f"{reverse('staff:shift_types_list')}?show=all")
        return redirect("staff:shift_types_list")


class ShiftTypeDeactivateView(LoginRequiredMixin, ActiveCompanyMixin, View):
    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            messages.error(request, "Active company is not selected.")
            return redirect("staff:shift_types_list")

        obj = get_object_or_404(ShiftType, pk=pk, company=company)
        if obj.is_active:
            obj.is_active = False
            obj.save(update_fields=["is_active"])
            messages.success(request, "Shift type deactivated (soft delete).")
        else:
            messages.info(request, "Shift type is already inactive.")

        if request.GET.get("show") == "all":
            return redirect(f"{reverse('staff:shift_types_list')}?show=all")
        return redirect("staff:shift_types_list")


class ShiftListView(LoginRequiredMixin, ActiveCompanyMixin, ListView):
    model = Shift
    template_name = "staff/shifts_list.html"
    context_object_name = "shifts"
    paginate_by = 10

    def get_queryset(self):
        company = self.get_active_company()
        if company is None:
            return Shift.objects.none()
        qs = Shift.objects.filter(company=company).select_related("shift_type")
        if self.request.GET.get("show") != "all":
            qs = qs.filter(is_active=True)
        return qs.order_by("shift_type__code_letter", "shift_no")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["active_company"] = self.get_active_company()
        show_all = self.request.GET.get("show") == "all"
        ctx["show_all"] = show_all
        if show_all:
            ctx["toggle_filter_url"] = reverse("staff:shifts_list")
            ctx["toggle_filter_label"] = "Show only active"
        else:
            ctx["toggle_filter_url"] = f"{reverse('staff:shifts_list')}?show=all"
            ctx["toggle_filter_label"] = "Show all"
        ctx["package_create_url"] = reverse("staff:shifts_package_add")
        return ctx


class ShiftPackageCreateView(LoginRequiredMixin, ActiveCompanyMixin, View):
    template_name = "staff/shifts_package_form.html"

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            messages.error(request, "Active company is not selected.")
            return redirect("staff:shifts_list")

        form = ShiftPackageCreateForm(company=company)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "active_company": company,
            },
        )

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            messages.error(request, "Active company is not selected.")
            return redirect("staff:shifts_list")

        form = ShiftPackageCreateForm(request.POST, company=company)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "active_company": company,
                },
            )

        shifts_data = form.build_shifts_data()

        try:
            with transaction.atomic():
                for row in shifts_data:
                    Shift.objects.create(**row)
        except (IntegrityError, ValidationError) as e:
            if isinstance(e, ValidationError) and hasattr(e, "message_dict"):
                for field, errors in e.message_dict.items():
                    if field == "__all__":
                        for err in errors:
                            form.add_error(None, err)
                    else:
                        for err in errors:
                            form.add_error(field, err)
            else:
                form.add_error(
                    None,
                    "Failed to create shift package due to duplicate or invalid data.",
                )

            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "active_company": company,
                },
            )

        shift_type = form.cleaned_data["shift_type"]
        messages.success(
            request,
            f"Shift package created: {shift_type.code_letter}1..{shift_type.code_letter}{shift_type.package_size}.",
        )
        return redirect("staff:shifts_list")


class ShiftCreateView(LoginRequiredMixin, ActiveCompanyMixin, CreateView):
    model = Shift
    template_name = "staff/shifts_form.html"
    fields = ["shift_type", "shift_no", "anchor_date", "is_active"]
    success_url = reverse_lazy("staff:shifts_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        company = self.get_active_company()
        if company is not None:
            form.instance.company = company
            if "shift_type" in form.fields:
                form.fields["shift_type"].queryset = ShiftType.objects.filter(
                    company=company
                )
        return form

    def form_valid(self, form):
        company = self.get_active_company()
        if company is None:
            messages.error(self.request, "Active company is not selected.")
            return redirect("staff:shifts_list")

        form.instance.company = company

        try:
            response = super().form_valid(form)
        except ValidationError as e:
            if hasattr(e, "message_dict"):
                for field, errors in e.message_dict.items():
                    if field == "__all__":
                        for err in errors:
                            form.add_error(None, err)
                    else:
                        for err in errors:
                            form.add_error(field, err)
            else:
                form.add_error(None, str(e))
            return self.render_to_response(self.get_context_data(form=form))

        messages.success(self.request, "Shift created.")
        return response


class ShiftUpdateView(LoginRequiredMixin, ActiveCompanyMixin, UpdateView):
    model = Shift
    template_name = "staff/shifts_form.html"
    fields = ["shift_type", "shift_no", "anchor_date", "is_active"]
    success_url = reverse_lazy("staff:shifts_list")

    def get_queryset(self):
        company = self.get_active_company()
        if company is None:
            return Shift.objects.none()
        return Shift.objects.filter(company=company)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        company = self.get_active_company()
        if company is not None and "shift_type" in form.fields:
            form.fields["shift_type"].queryset = ShiftType.objects.filter(
                company=company
            )
        return form

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ValidationError as e:
            if hasattr(e, "message_dict"):
                for field, errors in e.message_dict.items():
                    if field == "__all__":
                        for err in errors:
                            form.add_error(None, err)
                    else:
                        for err in errors:
                            form.add_error(field, err)
            else:
                form.add_error(None, str(e))
            return self.render_to_response(self.get_context_data(form=form))

        messages.success(self.request, "Shift updated.")
        return response


class ShiftDeactivateView(LoginRequiredMixin, ActiveCompanyMixin, View):
    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            messages.error(request, "Active company is not selected.")
            return redirect("staff:shifts_list")

        obj = get_object_or_404(Shift, pk=pk, company=company)
        if obj.is_active:
            obj.is_active = False
            obj.save(update_fields=["is_active"])
            messages.success(request, "Shift deactivated (soft delete).")
        else:
            messages.info(request, "Shift is already inactive.")

        if request.GET.get("show") == "all":
            return redirect(f"{reverse('staff:shifts_list')}?show=all")
        return redirect("staff:shifts_list")


def _plan_has_active_assignments(plan: StaffingPlan) -> bool:
    return StaffingAssignment.objects.filter(
        is_active=True,
        staffing_plan_item__staffing_plan=plan,
    ).exists()


class StaffingPlanListView(LoginRequiredMixin, ActiveCompanyMixin, ListView):
    model = StaffingPlan
    template_name = "staff/staffing_plans_list.html"
    context_object_name = "staffing_plans"
    paginate_by = 10

    def get_queryset(self):
        company = self.get_active_company()
        if company is None:
            return StaffingPlan.objects.none()

        qs = StaffingPlan.objects.filter(company=company)
        if self.request.GET.get("show") != "all":
            qs = qs.filter(is_active=True)

        return qs.order_by("-is_active", "-updated_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["active_company"] = self.get_active_company()
        show_all = self.request.GET.get("show") == "all"
        ctx["show_all"] = show_all
        if show_all:
            ctx["toggle_filter_url"] = reverse("staff:staffing_plans_list")
            ctx["toggle_filter_label"] = "Show only active"
        else:
            ctx["toggle_filter_url"] = (
                f"{reverse('staff:staffing_plans_list')}?show=all"
            )
            ctx["toggle_filter_label"] = "Show all"
        return ctx


class StaffingPlanBaseMixin(ActiveCompanyMixin):
    model = StaffingPlan
    form_class = StaffingPlanForm
    template_name = "staff/staffing_plans_form.html"
    success_url = reverse_lazy("staff:staffing_plans_list")

    def _build_formset(self, plan: StaffingPlan | None = None):
        company = self.get_active_company()
        kwargs = {}
        if self.request.method == "POST":
            kwargs["data"] = self.request.POST

        formset = StaffingPlanItemFormSet(instance=plan, **kwargs)

        if company is not None:
            for f in formset.forms:
                if "position" in f.fields:
                    f.fields["position"].queryset = Position.objects.filter(
                        company=company, is_active=True
                    )
        return formset

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["active_company"] = self.get_active_company()
        if "items_formset" not in ctx:
            ctx["items_formset"] = self._build_formset(
                plan=getattr(self, "object", None)
            )
        return ctx

    def form_valid(self, form):
        company = self.get_active_company()
        if company is None:
            messages.error(self.request, "Active company is not selected.")
            return redirect("staff:staffing_plans_list")

        plan: StaffingPlan = form.instance
        plan.company = company

        items_formset = self._build_formset(plan=plan)
        if not items_formset.is_valid():
            return self.render_to_response(
                self.get_context_data(form=form, items_formset=items_formset)
            )

        with transaction.atomic():
            self.object = form.save()
            items_formset.instance = self.object
            items_formset.save()

            desired_active = bool(self.object.is_active)

            if desired_active:
                other_active = (
                    StaffingPlan.objects.filter(company=company, is_active=True)
                    .exclude(pk=self.object.pk)
                    .order_by("-updated_at")
                    .first()
                )
                if other_active and _plan_has_active_assignments(other_active):
                    StaffingPlan.objects.filter(pk=self.object.pk).update(
                        is_active=False
                    )
                    self.object.is_active = False
                    form.add_error(
                        "is_active",
                        "Cannot activate this plan: current active plan has assignments.",
                    )
                    transaction.set_rollback(True)
                    return self.render_to_response(
                        self.get_context_data(form=form, items_formset=items_formset)
                    )

                StaffingPlan.objects.filter(company=company, is_active=True).exclude(
                    pk=self.object.pk
                ).update(is_active=False)

            else:
                if _plan_has_active_assignments(self.object):
                    StaffingPlan.objects.filter(pk=self.object.pk).update(
                        is_active=True
                    )
                    self.object.is_active = True
                    form.add_error(
                        "is_active",
                        "Cannot deactivate this plan: it has active assignments.",
                    )
                    transaction.set_rollback(True)
                    return self.render_to_response(
                        self.get_context_data(form=form, items_formset=items_formset)
                    )

        messages.success(self.request, "Staffing plan saved.")
        return redirect("staff:staffing_plans_list")


class StaffingPlanCreateView(LoginRequiredMixin, StaffingPlanBaseMixin, CreateView):
    def get(self, request, *args, **kwargs):
        self.object = None
        return super().get(request, *args, **kwargs)


class StaffingPlanUpdateView(LoginRequiredMixin, StaffingPlanBaseMixin, UpdateView):
    def get_queryset(self):
        company = self.get_active_company()
        if company is None:
            return StaffingPlan.objects.none()
        return StaffingPlan.objects.filter(company=company)


class StaffingPlanActivateView(LoginRequiredMixin, ActiveCompanyMixin, View):
    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            messages.error(request, "Active company is not selected.")
            return redirect("staff:staffing_plans_list")

        target = get_object_or_404(StaffingPlan, pk=pk, company=company)

        if target.is_active:
            messages.info(request, "This staffing plan is already active.")
            return redirect("staff:staffing_plans_list")

        current_active = (
            StaffingPlan.objects.filter(company=company, is_active=True)
            .order_by("-updated_at")
            .first()
        )
        if current_active and _plan_has_active_assignments(current_active):
            messages.error(
                request,
                "Cannot activate another plan: current active plan has assignments.",
            )
            return redirect("staff:staffing_plans_list")

        with transaction.atomic():
            StaffingPlan.objects.filter(company=company, is_active=True).update(
                is_active=False
            )
            StaffingPlan.objects.filter(pk=target.pk).update(is_active=True)

        messages.success(request, "Staffing plan activated.")
        return redirect("staff:staffing_plans_list")


class StaffingPlanDeactivateView(LoginRequiredMixin, ActiveCompanyMixin, View):
    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            messages.error(request, "Active company is not selected.")
            return redirect("staff:staffing_plans_list")

        obj = get_object_or_404(StaffingPlan, pk=pk, company=company)

        if not obj.is_active:
            messages.info(request, "Staffing plan is already inactive.")
            if request.GET.get("show") == "all":
                return redirect(f"{reverse('staff:staffing_plans_list')}?show=all")
            return redirect("staff:staffing_plans_list")

        if _plan_has_active_assignments(obj):
            messages.error(request, "Cannot deactivate: plan has active assignments.")
            if request.GET.get("show") == "all":
                return redirect(f"{reverse('staff:staffing_plans_list')}?show=all")
            return redirect("staff:staffing_plans_list")

        obj.is_active = False
        obj.save(update_fields=["is_active"])
        messages.success(request, "Staffing plan deactivated (soft delete).")

        if request.GET.get("show") == "all":
            return redirect(f"{reverse('staff:staffing_plans_list')}?show=all")
        return redirect("staff:staffing_plans_list")


class AssignmentsView(LoginRequiredMixin, ActiveCompanyMixin, TemplateView):
    template_name = "staff/assignments.html"

    def _get_assignment_status(
        self, assignment: StaffingAssignment, ref_day: date
    ) -> str:
        start_day = assignment.assigned_at.date()

        if assignment.released_at is None:
            end_day = None
        else:
            end_day = assignment.released_at.date()

        if start_day > ref_day:
            return "Future"

        if end_day is not None and end_day < ref_day:
            return "Closed"

        return "Active"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company = self.get_active_company()
        ctx["active_company"] = company

        if company is None:
            ctx["plan"] = None
            ctx["rows"] = []
            ctx["reference_date"] = timezone.localdate()
            return ctx

        reference_date = timezone.localdate()
        ctx["reference_date"] = reference_date

        plan = (
            StaffingPlan.objects.filter(company=company, is_active=True)
            .order_by("-updated_at")
            .first()
            or StaffingPlan.objects.filter(company=company)
            .order_by("-updated_at")
            .first()
        )

        ctx["plan"] = plan
        if plan is None:
            ctx["rows"] = []
            return ctx

        all_assignments_qs = StaffingAssignment.objects.select_related(
            "person"
        ).order_by("assigned_at", "pk")

        items_qs = (
            StaffingPlanItem.objects.filter(staffing_plan=plan)
            .select_related("position")
            .prefetch_related(Prefetch("assignments", queryset=all_assignments_qs))
            .order_by("position__name_long")
        )

        rows = []
        for item in items_qs:
            visible_assignments = []
            occupied = 0

            for assignment in item.assignments.all():
                status = self._get_assignment_status(assignment, reference_date)

                # на этом экране показываем только текущие и будущие
                if status == "Closed":
                    continue

                assignment.derived_status = status
                visible_assignments.append(assignment)

                if status == "Active":
                    occupied += 1

            item.occupied = occupied
            item.vacant = max(0, int(item.position_qty) - int(occupied))

            rows.append(
                {
                    "item": item,
                    "assignments": visible_assignments,
                }
            )

        ctx["rows"] = rows
        return ctx


class AssignmentCreateView(LoginRequiredMixin, ActiveCompanyMixin, View):
    template_name = "staff/assignment_form.html"

    def _build_return_url(
        self,
        *,
        item_pk: int,
        assigned_on: str | None,
        released_on: str | None,
        person_id: str | None,
    ) -> str:
        base_url = reverse("staff:assignment_add", kwargs={"item_pk": item_pk})
        params = {}
        if assigned_on:
            params["assigned_on"] = assigned_on
        if released_on:
            params["released_on"] = released_on
        if person_id:
            params["person"] = person_id

        if params:
            return f"{base_url}?{urlencode(params)}"
        return base_url

    def get(self, request: HttpRequest, item_pk: int) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            messages.error(request, "Active company is not selected.")
            return redirect("staff:assignments")

        item = get_object_or_404(
            StaffingPlanItem.objects.select_related("position", "staffing_plan"),
            pk=item_pk,
            staffing_plan__company=company,
        )

        initial = {
            "assigned_on": request.GET.get("assigned_on") or date.today().isoformat(),
            "released_on": request.GET.get("released_on") or "",
        }
        person_raw = (request.GET.get("person") or "").strip()
        if person_raw.isdigit():
            initial["person"] = int(person_raw)

        form = AssignmentCreateForm(
            company=company,
            item=item,
            initial=initial,
        )

        return render(
            request,
            self.template_name,
            {
                "active_company": company,
                "item": item,
                "form": form,
                "interval_conflicts": [],
                "selected_person": None,
                "return_url": self._build_return_url(
                    item_pk=item.pk,
                    assigned_on=str(initial.get("assigned_on") or ""),
                    released_on=str(initial.get("released_on") or ""),
                    person_id=person_raw,
                ),
            },
        )

    def post(self, request: HttpRequest, item_pk: int) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            messages.error(request, "Active company is not selected.")
            return redirect("staff:assignments")

        item = get_object_or_404(
            StaffingPlanItem.objects.select_related("position", "staffing_plan"),
            pk=item_pk,
            staffing_plan__company=company,
        )

        form = AssignmentCreateForm(
            request.POST,
            company=company,
            item=item,
        )

        selected_person = None
        person_raw = (request.POST.get("person") or "").strip()
        if person_raw.isdigit():
            selected_person = Person.objects.filter(
                pk=int(person_raw),
                company=company,
            ).first()

        assigned_on_raw = (request.POST.get("assigned_on") or "").strip()
        released_on_raw = (request.POST.get("released_on") or "").strip()

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "active_company": company,
                    "item": item,
                    "form": form,
                    "selected_person": selected_person,
                    "interval_conflicts": getattr(form, "interval_conflicts", []),
                    "return_url": self._build_return_url(
                        item_pk=item.pk,
                        assigned_on=assigned_on_raw,
                        released_on=released_on_raw,
                        person_id=person_raw,
                    ),
                },
            )

        assigned_on = form.cleaned_data.get("assigned_on")
        released_on = form.cleaned_data.get("released_on")

        assigned_at_dt = (
            _combine_date_as_day_start(assigned_on) if assigned_on else timezone.now()
        )
        released_at_dt = _combine_date_as_day_end(released_on) if released_on else None

        try:
            with transaction.atomic():
                # нулевой интервал не создаём
                if assigned_on and released_on and assigned_on == released_on:
                    messages.warning(
                        request,
                        "Assignment with same start and end date is ignored (zero-length).",
                    )
                    return redirect("staff:assignments")

                assignment = form.save(commit=False)
                assignment.assigned_at = assigned_at_dt
                assignment.released_at = released_at_dt
                assignment.is_active = (
                    True  # пока временно, позже переведём на расчёт по интервалу
                )
                assignment.save()
        except IntegrityError:
            messages.error(request, "Failed to create assignment.")
            return render(
                request,
                self.template_name,
                {
                    "active_company": company,
                    "item": item,
                    "form": form,
                    "selected_person": selected_person,
                    "interval_conflicts": getattr(form, "interval_conflicts", []),
                    "return_url": self._build_return_url(
                        item_pk=item.pk,
                        assigned_on=assigned_on_raw,
                        released_on=released_on_raw,
                        person_id=person_raw,
                    ),
                },
            )
        except ValidationError as e:
            form.add_error(None, e)
            return render(
                request,
                self.template_name,
                {
                    "active_company": company,
                    "item": item,
                    "form": form,
                    "selected_person": selected_person,
                    "interval_conflicts": getattr(form, "interval_conflicts", []),
                    "return_url": self._build_return_url(
                        item_pk=item.pk,
                        assigned_on=assigned_on_raw,
                        released_on=released_on_raw,
                        person_id=person_raw,
                    ),
                },
            )

        messages.success(request, "Assigned.")
        return redirect("staff:assignments")


class AssignmentConflictResolveView(LoginRequiredMixin, ActiveCompanyMixin, View):
    template_name = "staff/assignment_conflict_resolve.html"

    def get(self, request: HttpRequest, assignment_pk: int) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            messages.error(request, "Active company is not selected.")
            return redirect("staff:assignments")

        conflict_assignment = get_object_or_404(
            StaffingAssignment.objects.select_related(
                "person",
                "staffing_plan_item__position",
                "staffing_plan_item__staffing_plan",
            ),
            pk=assignment_pk,
            company=company,
        )

        item_pk_raw = (request.GET.get("item_pk") or "").strip()
        person_raw = (request.GET.get("person") or "").strip()
        assigned_on_raw = (request.GET.get("assigned_on") or "").strip()
        released_on_raw = (request.GET.get("released_on") or "").strip()

        if not item_pk_raw.isdigit():
            messages.error(request, "Invalid target staffing plan item.")
            return redirect("staff:assignments")

        new_item = get_object_or_404(
            StaffingPlanItem.objects.select_related("position", "staffing_plan"),
            pk=int(item_pk_raw),
            staffing_plan__company=company,
        )

        selected_person = None
        if person_raw.isdigit():
            selected_person = Person.objects.filter(
                pk=int(person_raw),
                company=company,
            ).first()

        assigned_on = _parse_date_from_post(assigned_on_raw)
        released_on = _parse_date_from_post(released_on_raw)

        default_trim_date = None
        if assigned_on is not None:
            default_trim_date = assigned_on - timedelta(days=1)

        return render(
            request,
            self.template_name,
            {
                "active_company": company,
                "conflict_assignment": conflict_assignment,
                "new_item": new_item,
                "selected_person": selected_person,
                "assigned_on": assigned_on,
                "released_on": released_on,
                "assigned_on_raw": assigned_on_raw,
                "released_on_raw": released_on_raw,
                "default_trim_date": default_trim_date,
            },
        )

    def post(self, request: HttpRequest, assignment_pk: int) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            messages.error(request, "Active company is not selected.")
            return redirect("staff:assignments")

        conflict_assignment = get_object_or_404(
            StaffingAssignment.objects.select_related(
                "person",
                "staffing_plan_item__position",
                "staffing_plan_item__staffing_plan",
            ),
            pk=assignment_pk,
            company=company,
        )

        item_pk_raw = (request.POST.get("item_pk") or "").strip()
        person_raw = (request.POST.get("person") or "").strip()
        assigned_on_raw = (request.POST.get("assigned_on") or "").strip()
        released_on_raw = (request.POST.get("released_on") or "").strip()
        resolution = (request.POST.get("resolution") or "").strip()
        trim_to_raw = (request.POST.get("trim_to") or "").strip()

        if not item_pk_raw.isdigit():
            messages.error(request, "Invalid target staffing plan item.")
            return redirect("staff:assignments")

        if not person_raw.isdigit():
            messages.error(request, "Invalid person.")
            return redirect("staff:assignments")

        new_item = get_object_or_404(
            StaffingPlanItem.objects.select_related("position", "staffing_plan"),
            pk=int(item_pk_raw),
            staffing_plan__company=company,
        )

        selected_person = get_object_or_404(
            Person,
            pk=int(person_raw),
            company=company,
        )

        assigned_on = _parse_date_from_post(assigned_on_raw)
        released_on = _parse_date_from_post(released_on_raw)
        trim_to = _parse_date_from_post(trim_to_raw)

        if assigned_on is None:
            messages.error(request, "Assigned on date is required.")
            return redirect("staff:assignments")

        if released_on is not None and released_on < assigned_on:
            messages.error(
                request, "Release date cannot be earlier than assignment date."
            )
            return redirect("staff:assignments")

        if resolution not in {"trim_create", "delete_create", "keep_existing"}:
            messages.error(request, "Please select a valid resolution.")
            return redirect(
                request.path
                + "?"
                + urlencode(
                    {
                        "item_pk": new_item.pk,
                        "person": selected_person.pk,
                        "assigned_on": assigned_on_raw,
                        "released_on": released_on_raw,
                    }
                )
            )

        if resolution == "keep_existing":
            messages.info(
                request, "Existing assignment was kept. New assignment was not created."
            )
            return redirect("staff:assignments")

        assigned_at_dt = _combine_date_as_day_start(assigned_on)
        released_at_dt = _combine_date_as_day_end(released_on) if released_on else None

        try:
            with transaction.atomic():
                if resolution == "delete_create":
                    conflict_assignment.delete()

                elif resolution == "trim_create":
                    if trim_to is None:
                        trim_to = assigned_on - timedelta(days=1)

                    conflict_start = _dt_to_local_date(conflict_assignment.assigned_at)

                    if conflict_start and trim_to < conflict_start:
                        conflict_assignment.delete()
                    else:
                        conflict_assignment.released_at = _combine_date_as_day_end(
                            trim_to
                        )
                        conflict_assignment.is_active = False
                        conflict_assignment.save(
                            update_fields=["released_at", "is_active"]
                        )

                if released_on is not None and released_on == assigned_on:
                    messages.warning(
                        request,
                        "New assignment was not created because start and end dates are the same.",
                    )
                    return redirect("staff:assignments")

                new_assignment = StaffingAssignment(
                    staffing_plan_item=new_item,
                    person=selected_person,
                    company=company,
                    assigned_at=assigned_at_dt,
                    released_at=released_at_dt,
                    is_active=True,
                )
                new_assignment.save()

        except ValidationError as e:
            messages.error(request, f"Could not resolve conflict: {e}")
            return redirect("staff:assignments")
        except IntegrityError:
            messages.error(request, "Database error while resolving conflict.")
            return redirect("staff:assignments")

        messages.success(request, "Conflict resolved and new assignment created.")
        return redirect("staff:assignments")


class AssignmentReleaseView(LoginRequiredMixin, ActiveCompanyMixin, View):
    def post(self, request: HttpRequest, assignment_pk: int) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            messages.error(request, "Active company is not selected.")
            return redirect("staff:assignments")

        assignment = get_object_or_404(
            StaffingAssignment,
            pk=assignment_pk,
            company=company,
        )

        clip_before_start = _parse_date_from_post(request.POST.get("clip_before_start"))
        released_on = _parse_date_from_post(request.POST.get("released_on"))

        # сценарий: release из формы конфликта
        if clip_before_start is not None:
            assigned_date = _dt_to_local_date(assignment.assigned_at)
            release_date = clip_before_start - timedelta(days=1)

            if assigned_date and release_date < assigned_date:
                assignment.delete()
                messages.success(
                    request,
                    "Conflicting assignment was removed because it would end before it starts.",
                )
            else:
                assignment.released_at = _combine_date_as_day_end(release_date)
                assignment.save(update_fields=["released_at"])
                messages.success(request, "Conflicting assignment was clipped.")

            next_url = (request.POST.get("next") or "").strip()
            return redirect(next_url or "staff:assignments")

        # обычный release из assignments
        released_at_dt = (
            _combine_date_as_day_end(released_on) if released_on else timezone.now()
        )

        assigned_date = _dt_to_local_date(assignment.assigned_at)
        release_date = _dt_to_local_date(released_at_dt)

        if assigned_date and release_date and release_date < assigned_date:
            messages.error(
                request,
                "Release date cannot be earlier than assignment date.",
            )
            next_url = (request.POST.get("next") or "").strip()
            return redirect(next_url or "staff:assignments")

        if assigned_date and release_date and release_date == assigned_date:
            assignment.delete()
            messages.success(
                request,
                "Assignment was removed because assign and release dates are the same.",
            )
            next_url = (request.POST.get("next") or "").strip()
            return redirect(next_url or "staff:assignments")

        assignment.released_at = released_at_dt
        assignment.save(update_fields=["released_at"])

        next_url = (request.POST.get("next") or "").strip()
        return redirect(next_url or "staff:assignments")


class AssignmentReleaseAllView(LoginRequiredMixin, ActiveCompanyMixin, View):
    def post(self, request: HttpRequest) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            messages.error(request, "Active company is not selected.")
            return redirect("staff:assignments")

        plan = (
            StaffingPlan.objects.filter(company=company, is_active=True)
            .order_by("-updated_at")
            .first()
        )
        if plan is None:
            messages.error(request, "No active staffing plan found.")
            return redirect("staff:assignments")

        release_day = (
            _parse_date_from_post(request.POST.get("released_on"))
            or timezone.localdate()
        )
        release_at_dt = _combine_date_as_day_end(release_day)

        qs = (
            StaffingAssignment.objects.filter(
                company=company,
                staffing_plan_item__staffing_plan=plan,
            )
            .select_related("person", "staffing_plan_item__position")
            .order_by("assigned_at", "pk")
        )

        delete_ids: list[int] = []
        update_ids: list[int] = []

        for assignment in qs:
            start_day = _dt_to_local_date(assignment.assigned_at)
            end_day = _dt_to_local_date(assignment.released_at)

            if start_day is None:
                continue

            # Уже полностью в прошлом относительно даты release-all
            if end_day is not None and end_day < release_day:
                continue

            # Полностью в будущем -> удаляем
            if start_day > release_day:
                delete_ids.append(assignment.pk)
                continue

            # start == release_day -> после обрезки получится нулевой интервал -> удаляем
            if start_day == release_day:
                delete_ids.append(assignment.pk)
                continue

            # Пересекает дату release-all -> обрезаем
            # (открытое или заканчивается позже выбранной даты)
            if end_day is None or end_day >= release_day:
                update_ids.append(assignment.pk)

        with transaction.atomic():
            deleted_count = 0
            clipped_count = 0

            if delete_ids:
                deleted_count = StaffingAssignment.objects.filter(
                    pk__in=delete_ids
                ).delete()[0]

            if update_ids:
                clipped_count = StaffingAssignment.objects.filter(
                    pk__in=update_ids
                ).update(
                    released_at=release_at_dt,
                )

        if deleted_count:
            messages.warning(
                request,
                f"{deleted_count} future or zero-length assignment(s) were deleted.",
            )

        if clipped_count:
            messages.success(
                request,
                f"{clipped_count} assignment(s) were clipped to {release_day.strftime('%d.%m.%y')}.",
            )

        if not deleted_count and not clipped_count:
            messages.info(request, "No assignments required changes.")

        return redirect("staff:assignments")


class LeaveListView(LoginRequiredMixin, ActiveCompanyMixin, ListView):
    model = StaffAbsence
    template_name = "staff/leaves_list.html"
    context_object_name = "leaves"
    paginate_by = 10

    def get_queryset(self):
        company = self.get_active_company()
        if company is None:
            return StaffAbsence.objects.none()

        qs = StaffAbsence.objects.filter(company=company).select_related(
            "person",
            "leave_type",
        )

        if self.request.GET.get("show") != "all":
            qs = qs.filter(is_active=True)

        return qs.order_by("-date_from", "-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["active_company"] = self.get_active_company()

        show_all = self.request.GET.get("show") == "all"
        ctx["show_all"] = show_all

        if show_all:
            ctx["toggle_filter_url"] = reverse("staff:leaves_list")
            ctx["toggle_filter_label"] = "Show only active"
        else:
            ctx["toggle_filter_url"] = f"{reverse('staff:leaves_list')}?show=all"
            ctx["toggle_filter_label"] = "Show all"

        return ctx


class LeaveDetailView(LoginRequiredMixin, ActiveCompanyMixin, TemplateView):
    template_name = "staff/leave_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        company = self.get_active_company()
        ctx["active_company"] = company

        if company is None:
            ctx["leave"] = None
            ctx["documents"] = []
            return ctx

        leave = get_object_or_404(
            StaffAbsence.objects.select_related(
                "person",
                "leave_type",
                "company",
            ).prefetch_related("documents"),
            pk=self.kwargs["pk"],
            company=company,
        )

        ctx["leave"] = leave
        ctx["documents"] = leave.documents.all().order_by("-uploaded_at")
        return ctx


class LeaveCreateView(LoginRequiredMixin, ActiveCompanyMixin, CreateView):
    model = StaffAbsence
    template_name = "staff/leave_form.html"
    fields = ["person", "leave_type", "date_from", "date_to", "note", "is_active"]
    success_url = reverse_lazy("staff:leaves_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        company = self.get_active_company()

        if company is not None:
            if "person" in form.fields:
                form.fields["person"].queryset = Person.objects.filter(
                    company=company
                ).order_by("family_name", "first_name", "second_name")

            if "leave_type" in form.fields:
                form.fields["leave_type"].queryset = LeaveType.objects.filter(
                    company=company,
                    is_active=True,
                ).order_by("name")

        return form

    def form_valid(self, form):
        company = self.get_active_company()
        if company is None:
            messages.error(self.request, "Active company is not selected.")
            return redirect("staff:leaves_list")

        form.instance.company = company
        messages.success(self.request, "Leave created.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("staff:leaves_detail", kwargs={"pk": self.object.pk})


class LeaveUpdateView(LoginRequiredMixin, ActiveCompanyMixin, UpdateView):
    model = StaffAbsence
    template_name = "staff/leave_form.html"
    fields = ["person", "leave_type", "date_from", "date_to", "note", "is_active"]
    success_url = reverse_lazy("staff:leaves_list")

    def get_queryset(self):
        company = self.get_active_company()
        if company is None:
            return StaffAbsence.objects.none()

        return StaffAbsence.objects.filter(company=company)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        company = self.get_active_company()

        if company is not None:
            if "person" in form.fields:
                form.fields["person"].queryset = Person.objects.filter(
                    company=company
                ).order_by("family_name", "first_name", "second_name")

            if "leave_type" in form.fields:
                form.fields["leave_type"].queryset = LeaveType.objects.filter(
                    company=company,
                    is_active=True,
                ).order_by("name")

        return form

    def form_valid(self, form):
        messages.success(self.request, "Leave updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("staff:leaves_detail", kwargs={"pk": self.object.pk})


class LeaveDeleteView(LoginRequiredMixin, ActiveCompanyMixin, View):
    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            messages.error(request, "Active company is not selected.")
            return redirect("staff:leaves_list")

        leave = get_object_or_404(
            StaffAbsence,
            pk=pk,
            company=company,
        )

        leave.delete()
        messages.success(request, "Leave deleted.")

        return redirect("staff:leaves_list")


class LeaveDocumentUploadView(LoginRequiredMixin, ActiveCompanyMixin, View):
    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            messages.error(request, "Active company is not selected.")
            return redirect("staff:leaves_list")

        leave = get_object_or_404(
            StaffAbsence,
            pk=pk,
            company=company,
        )

        uploaded_file = request.FILES.get("file")
        document_name = (request.POST.get("document_name") or "").strip()

        if not uploaded_file:
            messages.error(request, "Please choose a file.")
            return redirect("staff:leaves_detail", pk=leave.pk)

        StaffAbsenceDocument.objects.create(
            absence=leave,
            document_name=document_name,
            file=uploaded_file,
        )

        messages.success(request, "Document uploaded.")
        return redirect("staff:leaves_detail", pk=leave.pk)


class LeaveTypeListView(LoginRequiredMixin, ActiveCompanyMixin, ListView):
    model = LeaveType
    template_name = "staff/leave_types_list.html"
    context_object_name = "leave_types"
    paginate_by = 10

    def get_queryset(self):
        company = self.get_active_company()
        if company is None:
            return LeaveType.objects.none()

        qs = LeaveType.objects.filter(company=company)
        if self.request.GET.get("show") != "all":
            qs = qs.filter(is_active=True)

        return qs.order_by("name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["active_company"] = self.get_active_company()

        show_all = self.request.GET.get("show") == "all"
        ctx["show_all"] = show_all

        if show_all:
            ctx["toggle_filter_url"] = reverse("staff:leave_types_list")
            ctx["toggle_filter_label"] = "Show only active"
        else:
            ctx["toggle_filter_url"] = f"{reverse('staff:leave_types_list')}?show=all"
            ctx["toggle_filter_label"] = "Show all"

        return ctx


class LeaveTypeCreateView(LoginRequiredMixin, ActiveCompanyMixin, CreateView):
    model = LeaveType
    template_name = "staff/leave_types_form.html"
    fields = ["leave_code", "name", "description", "is_active"]
    success_url = reverse_lazy("staff:leave_types_list")

    def form_valid(self, form):
        company = self.get_active_company()
        if company is None:
            messages.error(self.request, "Active company is not selected.")
            return redirect("staff:leave_types_list")

        form.instance.company = company
        messages.success(self.request, "Leave type created.")
        return super().form_valid(form)


class LeaveTypeUpdateView(LoginRequiredMixin, ActiveCompanyMixin, UpdateView):
    model = LeaveType
    template_name = "staff/leave_types_form.html"
    fields = ["leave_code", "name", "description", "is_active"]
    success_url = reverse_lazy("staff:leave_types_list")

    def get_queryset(self):
        company = self.get_active_company()
        if company is None:
            return LeaveType.objects.none()
        return LeaveType.objects.filter(company=company)

    def form_valid(self, form):
        messages.success(self.request, "Leave type updated.")
        return super().form_valid(form)


class LeaveTypeDeactivateView(LoginRequiredMixin, ActiveCompanyMixin, View):
    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            messages.error(request, "Active company is not selected.")
            return redirect("staff:leave_types_list")

        obj = get_object_or_404(LeaveType, pk=pk, company=company)

        if obj.is_active:
            obj.is_active = False
            obj.save(update_fields=["is_active"])
            messages.success(request, "Leave type deactivated.")
        else:
            messages.info(request, "Leave type is already inactive.")

        if request.GET.get("show") == "all":
            return redirect(f"{reverse('staff:leave_types_list')}?show=all")

        return redirect("staff:leave_types_list")


class LeaveDocumentDeleteView(LoginRequiredMixin, ActiveCompanyMixin, View):
    def post(self, request: HttpRequest, pk: int, doc_pk: int) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            messages.error(request, "Active company is not selected.")
            return redirect("staff:leaves_list")

        leave = get_object_or_404(
            StaffAbsence,
            pk=pk,
            company=company,
        )

        document = get_object_or_404(
            StaffAbsenceDocument,
            pk=doc_pk,
            absence=leave,
        )

        document.delete()
        messages.success(request, "Document deleted.")

        return redirect("staff:leaves_detail", pk=leave.pk)