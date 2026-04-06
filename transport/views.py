from django import forms
from django.db.models import Q
from django.forms import inlineformset_factory
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from companies.models import Company
from transport.models import (
    TransportModelTechnicalParameter,
    TransportTechnicalParameter,
    TransportUnit,
    TransportUnitModel,
    TransportUnitType,
)

TransportModelTechnicalParameterFormSet = inlineformset_factory(
    TransportUnitModel,
    TransportModelTechnicalParameter,
    fields=(
        "parameter",
        "display_order",
        "is_required",
        "value_integer",
        "value_decimal",
        "value_text",
        "value_boolean",
    ),
    extra=1,
    can_delete=True,
)


class TransportHomeView(TemplateView):
    template_name = "transport/index.html"
    extra_context = {"active_company_id": None}


class ActiveCompanyMixin:
    active_company_id: int | None = None

    def dispatch(self, request, *args, **kwargs):
        self.active_company_id = request.session.get("active_company_id")
        if not self.active_company_id:
            raise Http404("Active company is not selected.")
        return super().dispatch(request, *args, **kwargs)


class ActiveOnlyToggleListMixin:
    show_all_param = "show"

    def is_show_all(self):
        return self.request.GET.get(self.show_all_param) == "all"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_company_id = self.request.session.get("active_company_id")
        show_all = self.is_show_all()

        context["active_company_id"] = active_company_id
        context["show_all"] = show_all
        context["show_all_url"] = f"{self.request.path}?show=all"
        context["show_active_url"] = self.request.path
        return context


class TransportUnitListView(ActiveOnlyToggleListMixin, ListView):
    model = TransportUnit
    template_name = "transport/unit_list.html"
    context_object_name = "units"

    def get_queryset(self):
        active_company_id = self.request.session.get("active_company_id")

        queryset = (
            TransportUnit.objects.select_related(
                "company",
                "model",
                "model__type",
            )
            .all()
            .order_by("name")
        )

        if active_company_id:
            queryset = queryset.filter(company_id=active_company_id)
            if not self.is_show_all():
                queryset = queryset.filter(is_active=True)
        else:
            queryset = queryset.none()

        return queryset


class TransportUnitCreateView(ActiveCompanyMixin, CreateView):
    model = TransportUnit
    template_name = "transport/unit_form.html"
    fields = [
        "name",
        "model",
        "identifier",
        "technical_status",
        "description",
        "is_active",
    ]
    success_url = reverse_lazy("transport:unit_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        field = form.fields["model"]
        assert isinstance(field, forms.ModelChoiceField)
        field.queryset = (
            TransportUnitModel.objects.filter(
                company_id=self.active_company_id,
                is_active=True,
                type__is_active=True,
            )
            .select_related("type")
            .order_by("type__name", "name")
        )
        return form

    def form_valid(self, form):
        company = Company.objects.get(pk=self.active_company_id)
        form.instance.company = company
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_company_id"] = self.active_company_id
        context["is_edit"] = False
        context["form_title"] = "Create Transport Unit"
        return context


class TransportUnitUpdateView(ActiveCompanyMixin, UpdateView):
    model = TransportUnit
    template_name = "transport/unit_form.html"
    fields = [
        "name",
        "model",
        "identifier",
        "technical_status",
        "description",
        "is_active",
    ]
    success_url = reverse_lazy("transport:unit_list")

    def get_queryset(self):
        return TransportUnit.objects.filter(
            company_id=self.active_company_id
        ).select_related("model", "model__type")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        field = form.fields["model"]
        assert isinstance(field, forms.ModelChoiceField)
        current_model_id = self.object.model_id

        field.queryset = (
            TransportUnitModel.objects.filter(
                Q(
                    company_id=self.active_company_id,
                    is_active=True,
                    type__is_active=True,
                )
                | Q(pk=current_model_id, company_id=self.active_company_id)
            )
            .select_related("type")
            .distinct()
            .order_by("type__name", "name")
        )
        return form

    def form_valid(self, form):
        form.instance.company_id = self.active_company_id
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_company_id"] = self.active_company_id
        context["is_edit"] = True
        context["form_title"] = "Edit Transport Unit"
        context["delete_url"] = reverse_lazy(
            "transport:unit_delete", kwargs={"pk": self.object.pk}
        )
        return context


class TransportUnitDeleteView(ActiveCompanyMixin, View):
    success_url = reverse_lazy("transport:unit_list")

    def post(self, request, *args, **kwargs):
        obj = TransportUnit.objects.filter(
            pk=kwargs["pk"],
            company_id=self.active_company_id,
        ).first()
        if not obj:
            raise Http404("Transport unit not found.")
        obj.is_active = False
        obj.save(update_fields=["is_active", "updated_at"])
        return HttpResponseRedirect(self.success_url)


class TransportUnitTypeListView(ActiveOnlyToggleListMixin, ListView):
    model = TransportUnitType
    template_name = "transport/type_list.html"
    context_object_name = "types"

    def get_queryset(self):
        active_company_id = self.request.session.get("active_company_id")

        queryset = TransportUnitType.objects.all().order_by("name")

        if active_company_id:
            queryset = queryset.filter(company_id=active_company_id)
            if not self.is_show_all():
                queryset = queryset.filter(is_active=True)
        else:
            queryset = queryset.none()

        return queryset


class TransportUnitTypeCreateView(ActiveCompanyMixin, CreateView):
    model = TransportUnitType
    template_name = "transport/type_form.html"
    fields = ["code", "name", "description", "is_active"]
    success_url = reverse_lazy("transport:type_list")

    def form_valid(self, form):
        form.instance.company_id = self.active_company_id
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_company_id"] = self.active_company_id
        context["is_edit"] = False
        context["form_title"] = "Create Transport Unit Type"
        return context


class TransportUnitTypeUpdateView(ActiveCompanyMixin, UpdateView):
    model = TransportUnitType
    template_name = "transport/type_form.html"
    fields = ["code", "name", "description", "is_active"]
    success_url = reverse_lazy("transport:type_list")

    def get_queryset(self):
        return TransportUnitType.objects.filter(company_id=self.active_company_id)

    def form_valid(self, form):
        form.instance.company_id = self.active_company_id
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_company_id"] = self.active_company_id
        context["is_edit"] = True
        context["form_title"] = "Edit Transport Unit Type"
        context["delete_url"] = reverse_lazy(
            "transport:type_delete", kwargs={"pk": self.object.pk}
        )
        return context


class TransportUnitTypeDeleteView(ActiveCompanyMixin, View):
    success_url = reverse_lazy("transport:type_list")

    def post(self, request, *args, **kwargs):
        obj = TransportUnitType.objects.filter(
            pk=kwargs["pk"],
            company_id=self.active_company_id,
        ).first()
        if not obj:
            raise Http404("Transport unit type not found.")
        obj.is_active = False
        obj.save(update_fields=["is_active"])
        return HttpResponseRedirect(self.success_url)


class TransportUnitModelListView(ActiveOnlyToggleListMixin, ListView):
    model = TransportUnitModel
    template_name = "transport/model_list.html"
    context_object_name = "models"

    def get_queryset(self):
        active_company_id = self.request.session.get("active_company_id")

        queryset = (
            TransportUnitModel.objects.select_related("company", "type")
            .all()
            .order_by("type__name", "name")
        )

        if active_company_id:
            queryset = queryset.filter(company_id=active_company_id)
            if not self.is_show_all():
                queryset = queryset.filter(is_active=True)
        else:
            queryset = queryset.none()

        return queryset


class TransportUnitModelCreateView(ActiveCompanyMixin, CreateView):
    model = TransportUnitModel
    template_name = "transport/model_form.html"
    fields = ["type", "name", "code", "description", "is_active"]
    success_url = reverse_lazy("transport:model_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        field = form.fields["type"]
        assert isinstance(field, forms.ModelChoiceField)
        field.queryset = TransportUnitType.objects.filter(
            company_id=self.active_company_id,
            is_active=True,
        ).order_by("name")
        return form

    def get_technical_formset(self, data=None):
        formset = TransportModelTechnicalParameterFormSet(
            data=data,
            instance=self.object,
            prefix="technical",
        )
        for form in formset.forms:
            if "parameter" in form.fields:
                form.fields["parameter"].queryset = (
                    TransportTechnicalParameter.objects.filter(
                        company_id=self.active_company_id,
                        is_active=True,
                    ).order_by("name")
                )
        return formset

    def get(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        technical_formset = self.get_technical_formset()
        return self.render_to_response(
            self.get_context_data(form=form, technical_formset=technical_formset)
        )

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        technical_formset = self.get_technical_formset(data=request.POST)

        if form.is_valid() and technical_formset.is_valid():
            return self.forms_valid(form, technical_formset)

        return self.render_to_response(
            self.get_context_data(form=form, technical_formset=technical_formset)
        )

    def forms_valid(self, form, technical_formset):
        form.instance.company_id = self.active_company_id
        self.object = form.save()
        technical_formset.instance = self.object
        technical_formset.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_company_id"] = self.active_company_id
        context["is_edit"] = False
        context["form_title"] = "Create Transport Unit Model"
        context.setdefault("technical_formset", self.get_technical_formset())
        return context


class TransportUnitModelUpdateView(ActiveCompanyMixin, UpdateView):
    model = TransportUnitModel
    template_name = "transport/model_form.html"
    fields = ["type", "name", "code", "description", "is_active"]
    success_url = reverse_lazy("transport:model_list")

    def get_queryset(self):
        return TransportUnitModel.objects.filter(
            company_id=self.active_company_id
        ).select_related("type")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        field = form.fields["type"]
        assert isinstance(field, forms.ModelChoiceField)
        current_type_id = self.object.type_id

        field.queryset = (
            TransportUnitType.objects.filter(
                Q(company_id=self.active_company_id, is_active=True)
                | Q(pk=current_type_id, company_id=self.active_company_id)
            )
            .distinct()
            .order_by("name")
        )
        return form

    def get_technical_formset(self, data=None):
        formset = TransportModelTechnicalParameterFormSet(
            data=data,
            instance=self.object,
            prefix="technical",
        )
        for form in formset.forms:
            if "parameter" in form.fields:
                current_parameter_id = form.instance.parameter_id
                form.fields["parameter"].queryset = (
                    TransportTechnicalParameter.objects.filter(
                        Q(company_id=self.active_company_id, is_active=True)
                        | Q(pk=current_parameter_id, company_id=self.active_company_id)
                    )
                    .distinct()
                    .order_by("name")
                )
        return formset

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        technical_formset = self.get_technical_formset()
        return self.render_to_response(
            self.get_context_data(form=form, technical_formset=technical_formset)
        )

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        technical_formset = self.get_technical_formset(data=request.POST)

        if form.is_valid() and technical_formset.is_valid():
            return self.forms_valid(form, technical_formset)

        return self.render_to_response(
            self.get_context_data(form=form, technical_formset=technical_formset)
        )

    def forms_valid(self, form, technical_formset):
        form.instance.company_id = self.active_company_id
        self.object = form.save()
        technical_formset.instance = self.object
        technical_formset.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_company_id"] = self.active_company_id
        context["is_edit"] = True
        context["form_title"] = "Edit Transport Unit Model"
        context["delete_url"] = reverse_lazy(
            "transport:model_delete", kwargs={"pk": self.object.pk}
        )
        context.setdefault("technical_formset", self.get_technical_formset())
        return context


class TransportUnitModelDeleteView(ActiveCompanyMixin, View):
    success_url = reverse_lazy("transport:model_list")

    def post(self, request, *args, **kwargs):
        obj = TransportUnitModel.objects.filter(
            pk=kwargs["pk"],
            company_id=self.active_company_id,
        ).first()
        if not obj:
            raise Http404("Transport unit model not found.")
        obj.is_active = False
        obj.save(update_fields=["is_active"])
        return HttpResponseRedirect(self.success_url)


class TransportUnitOperationalValueInlineDummy:
    pass