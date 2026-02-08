from __future__ import annotations

from django.views.generic import TemplateView

from companies.models import Company


class HomeView(TemplateView):
    template_name = "home.html"


class UnderConstructionView(TemplateView):
    template_name = "under_construction.html"


class MainView(TemplateView):
    template_name = "main.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        user = self.request.user

        # Linked person is optional
        ctx["person"] = getattr(user, "person", None) if user.is_authenticated else None

        company_id = self.request.session.get("active_company_id")
        ctx["company"] = (
            Company.objects.filter(id=company_id, is_active=True).first()
            if company_id
            else None
        )

        return ctx
