from __future__ import annotations

from typing import Any

from companies.models import Company


def active_company_and_person(request) -> dict[str, Any]:
    user = getattr(request, "user", None)

    person = None
    if user and getattr(user, "is_authenticated", False):
        person = getattr(user, "person", None)

    company = None
    company_id = request.session.get("active_company_id")
    if company_id:
        company = Company.objects.filter(id=company_id, is_active=True).first()

    return {
        # legacy/current name used in navbar
        "company": company,
        # NEW alias used in staff templates
        "active_company": company,
        # optional (can be useful in templates/debug)
        "active_company_id": company_id,
        "person": person,
    }
