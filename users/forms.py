from __future__ import annotations

from django import forms
from django.contrib.auth.forms import AuthenticationForm

from companies.models import Company


class EmailCompanyAuthenticationForm(AuthenticationForm):
    company = forms.ModelChoiceField(
        queryset=Company.objects.filter(is_active=True).order_by("name"),
        required=True,
        empty_label="Select company…",
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Company",
    )

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)

        if "username" in self.fields:
            self.fields["username"].widget.attrs.update(
                {"class": "form-control", "placeholder": "Email"}
            )
        if "password" in self.fields:
            self.fields["password"].widget.attrs.update(
                {"class": "form-control", "placeholder": "Password"}
            )
