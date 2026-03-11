from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy

from companies.models import CompanyMembership
from .forms import EmailCompanyAuthenticationForm


class CustomLoginView(LoginView):
    template_name = "users/login.html"
    authentication_form = EmailCompanyAuthenticationForm

    def form_valid(self, form):
        user = form.get_user()
        company = form.cleaned_data["company"]

        if not getattr(user, "is_superuser", False):
            ok = CompanyMembership.objects.filter(
                user=user,
                company=company,
                is_active=True,
            ).exists()
            if not ok:
                form.add_error("company", "You do not have access to this company.")
                return self.form_invalid(form)

        response = super().form_valid(form)

        self.request.session["active_company_id"] = company.id
        self.request.session.modified = True

        messages.success(self.request, "Welcome!")
        return response


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy("home")

    def get(self, request, *args, **kwargs):
        return redirect("home")

    def post(self, request, *args, **kwargs):
        request.session.pop("active_company_id", None)
        messages.info(request, "Logged out.")
        return super().post(request, *args, **kwargs)
