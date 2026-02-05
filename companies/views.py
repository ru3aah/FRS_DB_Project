from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from .models import Company, CompanyMembership

SESSION_COMPANY_ID_KEY = "active_company_id"


class SelectCompanyView(LoginRequiredMixin, View):
    template_name = "companies/select_company.html"

    def get_available_companies(self, user):
        if user.is_superuser:
            return Company.objects.filter(is_active=True).order_by("name")

        return (
            Company.objects.filter(
                is_active=True,
                memberships__user=user,
                memberships__is_active=True,
            )
            .distinct()
            .order_by("name")
        )

    def get(self, request):
        companies = self.get_available_companies(request.user)

        # если компания уже выбрана — можно не показывать экран выбора
        if request.session.get(SESSION_COMPANY_ID_KEY) is not None:
            return redirect("home")

        return render(request, self.template_name, {"companies": companies})

    def post(self, request):
        raw_company_id = (request.POST.get("company_id") or "").strip()

        # для суперпользователя разрешим режим "все компании"
        if request.user.is_superuser and raw_company_id == "all":
            request.session[SESSION_COMPANY_ID_KEY] = None
            messages.success(request, "Режим: все компании.")
            return redirect("home")

        try:
            company_id = int(raw_company_id)
        except (TypeError, ValueError):
            messages.error(request, "Выбери компанию.")
            return redirect("companies:select_company")

        # проверка доступа
        if request.user.is_superuser:
            company = Company.objects.filter(id=company_id, is_active=True).first()
        else:
            company = (
                Company.objects.filter(
                    id=company_id,
                    is_active=True,
                    memberships__user=request.user,
                    memberships__is_active=True,
                )
                .distinct()
                .first()
            )

        if not company:
            messages.error(request, "Нет доступа к выбранной компании.")
            return redirect("companies:select_company")

        request.session[SESSION_COMPANY_ID_KEY] = company.id
        messages.success(request, f"Выбрана компания: {company.name}")
        return redirect("home")
