from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Prefetch, Q
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
    Position,
    RosterOverride,
    Shift,
    ShiftMembership,
    ShiftType,
    StaffAbsence,
    StaffingAssignment,
    StaffingPlan,
    StaffingPlanItem,
)


class ActiveCompanyMixin:
    def get_active_company(self) -> Company | None:
        company_id = self.request.session.get("active_company_id")
        if not company_id:
            return None
        return Company.objects.filter(pk=company_id).first()


class StaffHomeView(LoginRequiredMixin, TemplateView):
    template_name = "staff/index.html"


def _plan_is_effective_on_day(plan: StaffingPlan, day: date) -> bool:
    if plan.active_from and day < plan.active_from:
        return False
    if plan.active_to and day > plan.active_to:
        return False
    return True


def _plan_is_effective_today(plan: StaffingPlan) -> bool:
    return _plan_is_effective_on_day(plan, timezone.localdate())


def _deactivate_out_of_range_plans(company: Company) -> None:
    today = timezone.localdate()

    outdated_qs = StaffingPlan.objects.filter(company=company, is_active=True).filter(
        Q(active_from__gt=today) | Q(active_to__lt=today)
    )

    if outdated_qs.exists():
        outdated_qs.update(is_active=False)


def _get_active_plan(company: Company) -> StaffingPlan | None:
    _deactivate_out_of_range_plans(company)
    today = timezone.localdate()

    return (
        StaffingPlan.objects.filter(company=company, is_active=True)
        .filter(Q(active_from__isnull=True) | Q(active_from__lte=today))
        .filter(Q(active_to__isnull=True) | Q(active_to__gte=today))
        .order_by("-active_from", "-updated_at")
        .first()
    )


def _dt_to_local_date(dt) -> date | None:
    if not dt:
        return None
    if timezone.is_aware(dt):
        return timezone.localtime(dt).date()
    return dt.date()


def _parse_date_from_post(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _combine_date_with_now_time(chosen_date, now_dt):
    if chosen_date is None:
        chosen_date = now_dt.date()

    dt = datetime(
        year=chosen_date.year,
        month=chosen_date.month,
        day=chosen_date.day,
        hour=now_dt.hour,
        minute=now_dt.minute,
        second=now_dt.second,
        microsecond=now_dt.microsecond,
    )
    if timezone.is_aware(now_dt):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


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


def _plan_has_active_assignments(plan: StaffingPlan) -> bool:
    return StaffingAssignment.objects.filter(
        is_active=True,
        staffing_plan_item__staffing_plan=plan,
    ).exists()


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

        plan = _get_active_plan(company)
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

        if company is None:
            ctx["days"] = []
            ctx["rows"] = []
            return ctx

        plan = _get_active_plan(company)
        ctx["plan"] = plan
        if plan is None:
            ctx["days"] = []
            ctx["rows"] = []
            return ctx

        items = list(
            StaffingPlanItem.objects.filter(staffing_plan=plan)
            .select_related("position")
            .order_by("position__name_long")
        )

        active_assignments = list(
            StaffingAssignment.objects.filter(
                staffing_plan_item__staffing_plan=plan,
                company=company,
                is_active=True,
            ).select_related("person", "staffing_plan_item")
        )

        persons_by_item: dict[int, list[Person]] = {}
        for a in active_assignments:
            persons_by_item.setdefault(a.staffing_plan_item_id, []).append(a.person)

        mem_qs = ShiftMembership.objects.filter(
            company=company,
            is_active=True,
        ).select_related("shift", "person", "shift__shift_type")
        person_shift: dict[int, Shift] = {m.person_id: m.shift for m in mem_qs}

        abs_qs = StaffAbsence.objects.filter(company=company, is_active=True)
        absences_by_person: dict[int, list[tuple[date, date]]] = {}
        for ab in abs_qs:
            absences_by_person.setdefault(ab.person_id, []).append(
                (ab.date_from, ab.date_to)
            )

        ov_qs = RosterOverride.objects.filter(
            company=company, is_active=True, day__gte=month_start, day__lte=month_end
        ).select_related("replacement_person", "staffing_plan_item")
        overrides: dict[tuple[date, int], list[Person]] = {}
        for ov in ov_qs:
            overrides.setdefault((ov.day, ov.staffing_plan_item_id), []).append(
                ov.replacement_person
            )

        days = []
        d = month_start
        while d <= month_end:
            days.append(d)
            d += timedelta(days=1)
        ctx["days"] = days

        rows = []
        for day in days:
            day_entries = []
            for it in items:
                base_people = persons_by_item.get(it.staffing_plan_item_id, [])

                filtered: list[dict] = []
                anchor_missing = False

                for p in base_people:
                    sh = person_shift.get(p.person_id)
                    if sh is None:
                        continue

                    if sh.anchor_date is None:
                        anchor_missing = True
                        continue

                    if not sh.is_on_duty(day):
                        continue

                    if _is_absent(absences_by_person, p.person_id, day):
                        continue

                    filtered.append({"person": p, "shift": sh})

                ov_people = overrides.get((day, it.staffing_plan_item_id), [])
                if ov_people:
                    final_people = []
                    for p in ov_people:
                        final_people.append(
                            {
                                "person": p,
                                "shift": person_shift.get(p.person_id),
                            }
                        )
                else:
                    final_people = filtered

                day_entries.append(
                    {
                        "item": it,
                        "people": final_people,
                        "is_anchor_missing": anchor_missing,
                    }
                )

            rows.append({"day": day, "entries": day_entries})

        ctx["rows"] = rows
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
    fields = ["name_long", "name_short", "type", "is_active"]
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
    fields = ["name_long", "name_short", "type", "is_active"]
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


class StaffingPlanListView(LoginRequiredMixin, ActiveCompanyMixin, ListView):
    model = StaffingPlan
    template_name = "staff/staffing_plans_list.html"
    context_object_name = "staffing_plans"
    paginate_by = 10

    def get_queryset(self):
        company = self.get_active_company()
        if company is None:
            return StaffingPlan.objects.none()

        _deactivate_out_of_range_plans(company)

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

        _deactivate_out_of_range_plans(company)

        plan: StaffingPlan = form.instance
        plan.company = company

        items_formset = self._build_formset(plan=plan)
        if not items_formset.is_valid():
            return self.render_to_response(
                self.get_context_data(form=form, items_formset=items_formset)
            )

        today = timezone.localdate()

        with transaction.atomic():
            self.object = form.save()
            items_formset.instance = self.object
            items_formset.save()

            desired_active = bool(self.object.is_active)

            if desired_active:
                if not _plan_is_effective_on_day(self.object, today):
                    StaffingPlan.objects.filter(pk=self.object.pk).update(
                        is_active=False
                    )
                    self.object.is_active = False
                    form.add_error(
                        "is_active",
                        "Cannot activate this plan: today's date is outside the plan period.",
                    )
                    transaction.set_rollback(True)
                    return self.render_to_response(
                        self.get_context_data(form=form, items_formset=items_formset)
                    )

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

        _deactivate_out_of_range_plans(company)

        target = get_object_or_404(StaffingPlan, pk=pk, company=company)

        if target.is_active:
            messages.info(request, "This staffing plan is already active.")
            return redirect("staff:staffing_plans_list")

        if not _plan_is_effective_today(target):
            messages.error(
                request,
                "Cannot activate this plan: today's date is outside the plan period.",
            )
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

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company = self.get_active_company()
        ctx["active_company"] = company

        if company is None:
            ctx["plan"] = None
            ctx["rows"] = []
            return ctx

        plan = _get_active_plan(company)
        ctx["plan"] = plan
        if plan is None:
            ctx["rows"] = []
            return ctx

        active_assignments_qs = StaffingAssignment.objects.filter(
            is_active=True
        ).select_related("person")

        items_qs = (
            StaffingPlanItem.objects.filter(staffing_plan=plan)
            .select_related("position")
            .annotate(
                occupied=Count("assignments", filter=Q(assignments__is_active=True))
            )
            .prefetch_related(Prefetch("assignments", queryset=active_assignments_qs))
            .order_by("position__name_long")
        )

        items = []
        today_str = date.today().isoformat()
        now_dt = timezone.now()

        for it in items_qs:
            it.vacant = max(0, int(it.position_qty) - int(it.occupied or 0))
            for a in it.assignments.all():
                a.is_future_assignment = bool(a.assigned_at and a.assigned_at > now_dt)
                a.is_past_closed_assignment = bool(
                    (not a.is_active) and a.assigned_at and a.assigned_at <= now_dt
                )
            items.append(it)

        ctx["items"] = items
        ctx["rows"] = [
            {
                "item": it,
                "form": AssignmentCreateForm(
                    company=company,
                    item=it,
                    initial={"assigned_on": today_str},
                ),
            }
            for it in items
        ]
        return ctx


class AssignmentModalView(LoginRequiredMixin, ActiveCompanyMixin, View):
    def get(self, request: HttpRequest, item_pk: int) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            return HttpResponse("")

        item = get_object_or_404(
            StaffingPlanItem.objects.select_related("staffing_plan"),
            pk=item_pk,
            staffing_plan__company=company,
        )

        form = AssignmentCreateForm(
            company=company,
            item=item,
        )

        return render(
            request,
            "staff/includes/assignment_modal.html",
            {
                "form": form,
                "item": item,
            },
        )


class AssignmentPersonOptionsView(LoginRequiredMixin, ActiveCompanyMixin, View):
    def post(self, request: HttpRequest, item_pk: int) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            return HttpResponse("")

        item = get_object_or_404(
            StaffingPlanItem.objects.select_related("staffing_plan"),
            pk=item_pk,
            staffing_plan__company=company,
        )

        assigned_on = (
            request.POST.get("assigned_on")
            or request.POST.get(f"assigned_on_{item_pk}")
            or date.today().isoformat()
        )

        form = AssignmentCreateForm(
            company=company,
            item=item,
            initial={"assigned_on": assigned_on},
        )

        return render(
            request,
            "staff/includes/assignment_person_select.html",
            {
                "form": form,
                "item": item,
            },
        )


class AssignmentCreateView(LoginRequiredMixin, ActiveCompanyMixin, View):
    def post(self, request: HttpRequest, item_pk: int) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            messages.error(request, "Active company is not selected.")
            return redirect("staff:assignments")

        item = get_object_or_404(
            StaffingPlanItem.objects.select_related("staffing_plan"),
            pk=item_pk,
            staffing_plan__company=company,
        )

        form = AssignmentCreateForm(
            request.POST,
            company=company,
            item=item,
        )

        if not form.is_valid():
            return render(
                request,
                "staff/includes/assignment_modal.html",
                {"form": form, "item": item},
            )

        person = form.cleaned_data["person"]
        assigned_on = form.cleaned_data["assigned_on"]

        future_assignments = StaffingAssignment.objects.filter(
            person=person,
            assigned_at__date__gt=assigned_on,
        )

        if future_assignments.exists() and "force" not in request.POST:
            messages.warning(
                request,
                f"{person} already has future assignments. "
                f"Press Assign again to delete them and continue.",
            )

            return render(
                request,
                "staff/includes/assignment_modal.html",
                {
                    "form": form,
                    "item": item,
                    "force": True,
                },
            )

        if "force" in request.POST:
            future_assignments.delete()

        now_dt = timezone.now()
        assigned_at_dt = _combine_date_with_now_time(assigned_on, now_dt)

        assignment = form.save(commit=False)
        assignment.company = company
        assignment.staffing_plan_item = item
        assignment.assigned_at = assigned_at_dt
        assignment.save()

        messages.success(request, f"{person} assigned successfully.")
        return redirect("staff:assignments")


class AssignmentReleaseView(LoginRequiredMixin, ActiveCompanyMixin, View):
    def post(self, request: HttpRequest, assignment_pk: int) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            messages.error(request, "Active company is not selected.")
            return redirect("staff:assignments")

        a = get_object_or_404(StaffingAssignment, pk=assignment_pk, company=company)

        released_on = _parse_date_from_post(request.POST.get("released_on"))
        now_dt = timezone.now()
        released_at_dt = (
            _combine_date_with_now_time(released_on, now_dt) if released_on else now_dt
        )

        assigned_date = _dt_to_local_date(a.assigned_at)
        release_date = _dt_to_local_date(released_at_dt)

        if assigned_date and release_date and release_date < assigned_date:
            messages.error(
                request,
                "Release date cannot be earlier than assignment date.",
            )
            return redirect("staff:assignments")

        if a.is_active:
            a.is_active = False
            a.released_at = released_at_dt
            a.save(update_fields=["is_active", "released_at"])
            messages.success(request, "Released.")
        else:
            messages.info(request, "Already inactive.")

        return redirect("staff:assignments")


class AssignmentDeleteView(LoginRequiredMixin, ActiveCompanyMixin, View):
    CONFIRM_VALUE = "YES_DELETE"

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

        confirm_value = (request.POST.get("confirm_delete") or "").strip()
        if confirm_value != self.CONFIRM_VALUE:
            messages.error(
                request,
                "Deletion was not confirmed.",
            )
            return redirect("staff:assignments")

        now_dt = timezone.now()

        is_future = bool(assignment.assigned_at and assignment.assigned_at > now_dt)
        is_closed_past = bool(
            (not assignment.is_active)
            and assignment.assigned_at
            and assignment.assigned_at <= now_dt
        )

        if not (is_future or is_closed_past):
            messages.error(
                request,
                "You can delete only future assignments or already closed past assignments.",
            )
            return redirect("staff:assignments")

        assignment.delete()
        messages.success(request, "Assignment deleted permanently.")
        return redirect("staff:assignments")


class AssignmentDeleteFutureView(AssignmentDeleteView):
    pass


class AssignmentReleaseAllView(LoginRequiredMixin, ActiveCompanyMixin, View):
    def post(self, request: HttpRequest) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            messages.error(request, "Active company is not selected.")
            return redirect("staff:assignments")

        plan = _get_active_plan(company)
        if plan is None:
            messages.error(request, "No active staffing plan found.")
            return redirect("staff:assignments")

        released_on = _parse_date_from_post(request.POST.get("released_on"))
        now_dt = timezone.now()
        released_at_dt = (
            _combine_date_with_now_time(released_on, now_dt) if released_on else now_dt
        )

        qs = StaffingAssignment.objects.filter(
            company=company,
            is_active=True,
            staffing_plan_item__staffing_plan=plan,
        )

        if (
            released_on is not None
            and qs.filter(assigned_at__date__gt=released_on).exists()
        ):
            messages.error(
                request,
                "Release date cannot be earlier than assignment date for one or more assignments.",
            )
            return redirect("staff:assignments")

        with transaction.atomic():
            updated = qs.update(is_active=False, released_at=released_at_dt)

        if updated:
            messages.success(request, f"Released all ({updated}).")
        else:
            messages.info(request, "No active assignments to release.")

        return redirect("staff:assignments")
