from django import forms
from django.http import Http404
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from companies.models import Company
from transport.models import TransportUnit, TransportUnitModel, TransportUnitType


class TransportHomeView(TemplateView):
    template_name = "transport/index.html"
    extra_context = {"active_company_id": None}


class TransportUnitListView(ListView):
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
        else:
            queryset = queryset.none()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_company_id"] = self.request.session.get("active_company_id")
        return context


class TransportUnitCreateView(CreateView):
    active_company_id: int | None = None
    model = TransportUnit
    template_name = "transport/unit_form.html"
    fields = ["name", "model", "identifier", "description", "is_active"]
    success_url = reverse_lazy("transport:unit_list")

    def dispatch(self, request, *args, **kwargs):
        self.active_company_id = request.session.get("active_company_id")
        if not self.active_company_id:
            raise Http404("Active company is not selected.")
        return super().dispatch(request, *args, **kwargs)

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
        return context


class TransportUnitUpdateView(UpdateView):
    active_company_id: int | None = None
    model = TransportUnit
    template_name = "transport/unit_form.html"
    fields = ["name", "model", "identifier", "description", "is_active"]
    success_url = reverse_lazy("transport:unit_list")

    def dispatch(self, request, *args, **kwargs):
        self.active_company_id = request.session.get("active_company_id")
        if not self.active_company_id:
            raise Http404("Active company is not selected.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return TransportUnit.objects.filter(
            company_id=self.active_company_id
        ).select_related("model", "model__type")

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
        form.instance.company_id = self.active_company_id
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_company_id"] = self.active_company_id
        context["is_edit"] = True
        return context


class TransportUnitTypeListView(ListView):
    model = TransportUnitType
    template_name = "transport/type_list.html"
    context_object_name = "types"

    def get_queryset(self):
        active_company_id = self.request.session.get("active_company_id")

        queryset = TransportUnitType.objects.all().order_by("name")

        if active_company_id:
            queryset = queryset.filter(company_id=active_company_id)
        else:
            queryset = queryset.none()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_company_id"] = self.request.session.get("active_company_id")
        return context


class TransportUnitTypeCreateView(CreateView):
    active_company_id: int | None = None
    model = TransportUnitType
    template_name = "transport/type_form.html"
    fields = ["code", "name", "description", "is_active"]
    success_url = reverse_lazy("transport:type_list")

    def dispatch(self, request, *args, **kwargs):
        self.active_company_id = request.session.get("active_company_id")
        if not self.active_company_id:
            raise Http404("Active company is not selected.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.company_id = self.active_company_id
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_company_id"] = self.active_company_id
        return context


class TransportUnitTypeUpdateView(UpdateView):
    active_company_id: int | None = None
    model = TransportUnitType
    template_name = "transport/type_form.html"
    fields = ["code", "name", "description", "is_active"]
    success_url = reverse_lazy("transport:type_list")

    def dispatch(self, request, *args, **kwargs):
        self.active_company_id = request.session.get("active_company_id")
        if not self.active_company_id:
            raise Http404("Active company is not selected.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return TransportUnitType.objects.filter(company_id=self.active_company_id)

    def form_valid(self, form):
        form.instance.company_id = self.active_company_id
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_company_id"] = self.active_company_id
        context["is_edit"] = True
        return context


class TransportUnitModelListView(ListView):
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
        else:
            queryset = queryset.none()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_company_id"] = self.request.session.get("active_company_id")
        return context


class TransportUnitModelCreateView(CreateView):
    active_company_id: int | None = None
    model = TransportUnitModel
    template_name = "transport/model_form.html"
    fields = ["type", "name", "code", "description", "is_active"]
    success_url = reverse_lazy("transport:model_list")

    def dispatch(self, request, *args, **kwargs):
        self.active_company_id = request.session.get("active_company_id")
        if not self.active_company_id:
            raise Http404("Active company is not selected.")
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        field = form.fields["type"]
        assert isinstance(field, forms.ModelChoiceField)
        field.queryset = TransportUnitType.objects.filter(
            company_id=self.active_company_id,
            is_active=True,
        ).order_by("name")
        return form

    def form_valid(self, form):
        form.instance.company_id = self.active_company_id
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_company_id"] = self.active_company_id
        return context


class TransportUnitModelUpdateView(UpdateView):
    active_company_id: int | None = None
    model = TransportUnitModel
    template_name = "transport/model_form.html"
    fields = ["type", "name", "code", "description", "is_active"]
    success_url = reverse_lazy("transport:model_list")

    def dispatch(self, request, *args, **kwargs):
        self.active_company_id = request.session.get("active_company_id")
        if not self.active_company_id:
            raise Http404("Active company is not selected.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return TransportUnitModel.objects.filter(
            company_id=self.active_company_id
        ).select_related("type")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        field = form.fields["type"]
        assert isinstance(field, forms.ModelChoiceField)
        field.queryset = TransportUnitType.objects.filter(
            company_id=self.active_company_id,
            is_active=True,
        ).order_by("name")
        return form

    def form_valid(self, form):
        form.instance.company_id = self.active_company_id
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_company_id"] = self.active_company_id
        context["is_edit"] = True
        return context