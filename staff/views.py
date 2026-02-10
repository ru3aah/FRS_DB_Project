# staff/views.py
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError, transaction
from django.db.models import Count, Prefetch, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from companies.models import Company
from .forms import AssignmentCreateForm, StaffingPlanForm, StaffingPlanItemFormSet
from .models import (
    Position,
    Shift,
    ShiftType,
    StaffingPlan,
    StaffingPlanItem,
    StaffingAssignment,
)


class ActiveCompanyMixin:
    def get_active_company(self) -> Company | None:
        company_id = self.request.session.get("active_company_id")
        if not company_id:
            return None
        return Company.objects.filter(pk=company_id, is_active=True).first()


class StaffHomeView(LoginRequiredMixin, TemplateView):
    template_name = "staff/index.html"


# =========================
# Positions
# =========================
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
            messages.error(request, "Active company is not selected.")
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


# =========================
# Shift types
# =========================
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


class ShiftTypeCreateView(LoginRequiredMixin, ActiveCompanyMixin, CreateView):
    model = ShiftType
    template_name = "staff/shift_types_form.html"
    fields = [
        "shift_type_name",
        "shift_type_short",
        "shift_days_on",
        "shift_days_off",
        "is_active",
    ]
    success_url = reverse_lazy("staff:shift_types_list")

    def form_valid(self, form):
        company = self.get_active_company()
        if company is None:
            messages.error(self.request, "Active company is not selected.")
            return redirect("staff:shift_types_list")
        form.instance.company = company
        messages.success(self.request, "Shift type created.")
        return super().form_valid(form)


class ShiftTypeUpdateView(LoginRequiredMixin, ActiveCompanyMixin, UpdateView):
    model = ShiftType
    template_name = "staff/shift_types_form.html"
    fields = [
        "shift_type_name",
        "shift_type_short",
        "shift_days_on",
        "shift_days_off",
        "is_active",
    ]
    success_url = reverse_lazy("staff:shift_types_list")

    def get_queryset(self):
        company = self.get_active_company()
        if company is None:
            return ShiftType.objects.none()
        return ShiftType.objects.filter(company=company)

    def form_valid(self, form):
        messages.success(self.request, "Shift type updated.")
        return super().form_valid(form)


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


# =========================
# Shifts
# =========================
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
        return qs.order_by("-created_at")

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
        return ctx


class ShiftCreateView(LoginRequiredMixin, ActiveCompanyMixin, CreateView):
    model = Shift
    template_name = "staff/shifts_form.html"
    fields = ["shift_number", "shift_type", "is_active"]
    success_url = reverse_lazy("staff:shifts_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        company = self.get_active_company()
        if company is not None and "shift_type" in form.fields:
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
        messages.success(self.request, "Shift created.")
        return super().form_valid(form)


class ShiftUpdateView(LoginRequiredMixin, ActiveCompanyMixin, UpdateView):
    model = Shift
    template_name = "staff/shifts_form.html"
    fields = ["shift_number", "shift_type", "is_active"]
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
        messages.success(self.request, "Shift updated.")
        return super().form_valid(form)


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


# =========================
# Staffing Plans (with rules)
# =========================
def _plan_has_active_assignments(plan: StaffingPlan) -> bool:
    """
    True if there is at least one active StaffingAssignment linked to this plan.
    """
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

        # показать только активные если show != all
        if self.request.GET.get("show") != "all":
            qs = qs.filter(is_active=True)

        # Требование: активный всегда первым, остальные по updated_at desc
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
                if "shift_type" in f.fields:
                    f.fields["shift_type"].queryset = ShiftType.objects.filter(
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
            # сохраняем план и items
            self.object = form.save()
            items_formset.instance = self.object
            items_formset.save()

            # ---------
            # Правила активности (после сохранения, но в одной транзакции)
            # ---------
            desired_active = bool(self.object.is_active)

            if desired_active:
                # хотим сделать этот план активным -> надо выключить другие активные,
                # но если "текущий активный другой" имеет назначения — запрещаем переключение
                other_active = (
                    StaffingPlan.objects.filter(company=company, is_active=True)
                    .exclude(pk=self.object.pk)
                    .order_by("-updated_at")
                    .first()
                )
                if other_active and _plan_has_active_assignments(other_active):
                    # откатываем активность обратно
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

                # можно активировать — деактивируем остальные
                StaffingPlan.objects.filter(company=company, is_active=True).exclude(
                    pk=self.object.pk
                ).update(is_active=False)

            else:
                # хотим сделать план неактивным -> запрещаем, если есть активные назначения
                if _plan_has_active_assignments(self.object):
                    # вернуть активность как была (если план был активным до запроса — пользователь пытался снять)
                    # безопасно: просто оставим is_active=True
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
    """
    Activate a plan for the company:
    - only one active plan allowed
    - if current active plan has assignments -> block (because it would be deactivated)
    """

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
    """
    Deactivate (soft) a staffing plan:
    - запрещено, если у плана есть активные назначения
    """

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

        # ключевой фикс: считаем только АКТИВНЫЕ назначения по этому плану
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


# =========================
# Assignments
# =========================
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

        active_assignments_qs = StaffingAssignment.objects.filter(
            is_active=True
        ).select_related("person")

        items_qs = (
            StaffingPlanItem.objects.filter(staffing_plan=plan)
            .select_related("position", "shift_type")
            .annotate(
                occupied=Count("assignments", filter=Q(assignments__is_active=True))
            )
            .prefetch_related(Prefetch("assignments", queryset=active_assignments_qs))
            .order_by("position__name_long", "shift_type__shift_type_short")
        )

        items = []
        for it in items_qs:
            it.vacant = max(0, int(it.position_qty) - int(it.occupied or 0))
            items.append(it)

        ctx["items"] = items
        ctx["rows"] = [
            {"item": it, "form": AssignmentCreateForm(company=company, item=it)}
            for it in items
        ]
        return ctx


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

        form = AssignmentCreateForm(request.POST, company=company, item=item)
        if not form.is_valid():
            for err in form.errors.get("__all__", []):
                messages.error(request, err)
            return redirect("staff:assignments")

        try:
            with transaction.atomic():
                form.save()
        except IntegrityError:
            messages.error(request, "This person is already assigned to this slot.")
            return redirect("staff:assignments")

        messages.success(request, "Assigned.")
        return redirect("staff:assignments")


class AssignmentReleaseView(LoginRequiredMixin, ActiveCompanyMixin, View):
    def post(self, request: HttpRequest, assignment_pk: int) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            messages.error(request, "Active company is not selected.")
            return redirect("staff:assignments")

        a = get_object_or_404(StaffingAssignment, pk=assignment_pk, company=company)
        if a.is_active:
            a.is_active = False
            a.released_at = timezone.now()
            a.save(update_fields=["is_active", "released_at"])
            messages.success(request, "Released.")
        else:
            messages.info(request, "Already inactive.")

        return redirect("staff:assignments")
