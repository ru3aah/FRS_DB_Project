from __future__ import annotations

from typing import Any

from companies.models import Company


def active_company_and_person(request) -> dict[str, Any]:
    """
    Adds active company (from session) and linked person to every template context.

    - company: Company | None
    - person: Person | None
    """
    user = getattr(request, "user", None)

    person = None
    if user and getattr(user, "is_authenticated", False):
        # CustomUser.person is optional; avoid RelatedObjectDoesNotExist
        person = getattr(user, "person", None)

    company = None
    company_id = request.session.get("active_company_id")
    if company_id:
        company = Company.objects.filter(id=company_id, is_active=True).first()

    return {
        "company": company,
        "person": person,
    }
