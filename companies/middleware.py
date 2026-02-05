from __future__ import annotations

from django.shortcuts import redirect
from django.urls import reverse


class ActiveCompanyRequiredMiddleware:
    """
    Требует выбранную компанию (active_company_id в session) для большинства страниц.
    Home (/) остаётся доступным всегда.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Разрешаем всегда (публичные страницы/служебные пути)
        if (
            path == "/"  # Home должен открываться всегда
            or path.startswith("/users/login/")
            or path.startswith("/users/logout/")
            or path.startswith("/admin/")
            or path.startswith("/static/")
            or path.startswith("/media/")
            or path.startswith("/under-construction/")
        ):
            return self.get_response(request)

        # Если пользователь не залогинен — пусть работает стандартная логика
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return self.get_response(request)

        # Для остальных страниц требуем выбранную компанию
        active_company_id = request.session.get("active_company_id")
        if not active_company_id:
            return redirect(reverse("users:login"))

        return self.get_response(request)
