from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from companies.models import Company, CompanyMembership


class CustomLoginForm(AuthenticationForm):
    company = forms.ModelChoiceField(
        queryset=Company.objects.filter(is_active=True).order_by("name"),
        required=True,
        label="Company",
        empty_label="Select a company",
    )

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)

        # AuthenticationForm использует поле "username" (даже если USERNAME_FIELD=email)
        self.fields["username"].label = "Email"
        self.fields["username"].widget.attrs.update({"autocomplete": "email"})
        self.fields["password"].widget.attrs.update(
            {"autocomplete": "current-password"}
        )

    def clean(self):
        cleaned_data = super().clean()

        user = self.get_user()
        company = cleaned_data.get("company")

        if not user or not company:
            return cleaned_data

        # superuser имеет доступ ко всем
        if user.is_superuser:
            return cleaned_data

        has_access = CompanyMembership.objects.filter(
            user=user,
            company=company,
            is_active=True,
            company__is_active=True,
        ).exists()

        if not has_access:
            raise ValidationError("You do not have access to the selected company.")

        return cleaned_data
