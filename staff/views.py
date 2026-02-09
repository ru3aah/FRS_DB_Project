from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from companies.models import Company
from .models import Position, Shift, ShiftType, StaffingPlan
from .forms import StaffingPlanForm, StaffingPlanItemFormSet


class ActiveCompanyMixin:
    """
    Берём active_company_id из session (как в companies app).
    """

    def get_active_company(self) -> Company | None:
        company_id = self.request.session.get("active_company_id")
        if not company_id:
            return None
        try:
            return Company.objects.get(pk=company_id)
        except Company.DoesNotExist:
            return None


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

        show_all = self.request.GET.get("show") == "all"
        if not show_all:
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

        show = request.GET.get("show")
        if show == "all":
            return redirect(f"{reverse('staff:positions_list')}?show=all")
        return redirect("staff:positions_list")


# =========================
# Shift Types
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

        show_all = self.request.GET.get("show") == "all"
        if not show_all:
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

        show = request.GET.get("show")
        if show == "all":
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

        show_all = self.request.GET.get("show") == "all"
        if not show_all:
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

        show = request.GET.get("show")
        if show == "all":
            return redirect(f"{reverse('staff:shifts_list')}?show=all")
        return redirect("staff:shifts_list")


# =========================
# Staffing Plans (SAVE HEADER + ITEMS)
# =========================


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

        show_all = self.request.GET.get("show") == "all"
        if not show_all:
            qs = qs.filter(is_active=True)

        # ВАЖНО: никаких order_by('id') — у модели PK не 'id'
        return qs.order_by("-updated_at")

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
    """
    Общая логика для Create/Update: form + inline formset.
    """

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

        # Ограничим choices по active company
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

        # ВАЖНО: сначала валидируем formset
        plan: StaffingPlan = form.instance
        plan.company = company

        items_formset = self._build_formset(plan=plan)

        if not items_formset.is_valid():
            # Рендерим страницу обратно с ошибками
            return self.render_to_response(
                self.get_context_data(form=form, items_formset=items_formset)
            )

        with transaction.atomic():
            self.object = form.save()  # сохраняем StaffingPlan
            items_formset.instance = self.object
            items_formset.save()  # сохраняем items

        messages.success(self.request, "Staffing plan saved.")
        return redirect(self.get_success_url())


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


class StaffingPlanDeactivateView(LoginRequiredMixin, ActiveCompanyMixin, View):
    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        company = self.get_active_company()
        if company is None:
            messages.error(request, "Active company is not selected.")
            return redirect("staff:staffing_plans_list")

        obj = get_object_or_404(StaffingPlan, pk=pk, company=company)
        if obj.is_active:
            obj.is_active = False
            obj.save(update_fields=["is_active"])
            messages.success(request, "Staffing plan deactivated (soft delete).")
        else:
            messages.info(request, "Staffing plan is already inactive.")

        show = request.GET.get("show")
        if show == "all":
            return redirect(f"{reverse('staff:staffing_plans_list')}?show=all")
        return redirect("staff:staffing_plans_list")
