from __future__ import annotations

from django.shortcuts import redirect
from django.urls import reverse

from companies.models import Company


class ActiveCompanyRequiredMiddleware:
    """
    Requires selected active company for most pages.
    Makes request.active_company available everywhere.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Public / system paths
        if (
            path == "/"
            or path.startswith("/users/login/")
            or path.startswith("/users/logout/")
            or path.startswith("/admin/")
            or path.startswith("/static/")
            or path.startswith("/media/")
            or path.startswith("/under-construction/")
        ):
            return self.get_response(request)

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return self.get_response(request)

        company_id = request.session.get("active_company_id")
        if not company_id:
            return redirect(reverse("users:login"))

        company = Company.objects.filter(
            pk=company_id,
            is_active=True,
        ).first()

        if not company:
            # cleanup broken session
            request.session.pop("active_company_id", None)
            return redirect(reverse("users:login"))

        # attach to request
        request.active_company = company

        return self.get_response(request)
