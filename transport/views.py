from django.urls import reverse_lazy
from django.views.generic import ListView, TemplateView  # noqa: I001

from transport.models import TransportUnit, TransportUnitType


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
            TransportUnit.objects.select_related("company", "type")
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


class TransportUnitTypeListView(ListView):
    model = TransportUnitType
    template_name = "transport/type_list.html"
    context_object_name = "types"
    queryset = TransportUnitType.objects.all().order_by("name")


class TransportUnitTypeCreateView(TemplateView):
    model = TransportUnitType
    template_name = "transport/type_form.html"
    fields = ["code", "name", "description", "is_active"]
    extra_context = {"active_company_id": None}
    success_url = reverse_lazy("transport:type-list")