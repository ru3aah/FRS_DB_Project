from django.conf import settings
from django.db import models


class Company(models.Model):
    id = models.BigAutoField(primary_key=True)

    name = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "companies"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class CompanyMembership(models.Model):
    id = models.BigAutoField(primary_key=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="company_memberships",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "company_memberships"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "company"],
                name="uq_user_company_membership",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} -> {self.company}"
