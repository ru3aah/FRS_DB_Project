from django.shortcuts import render

# Create your views here.
from django.contrib.auth.views import LoginView

from .forms import CustomLoginForm


class CustomLoginView(LoginView):
    template_name = "users/login.html"
    authentication_form = CustomLoginForm

    def form_valid(self, form):
        response = super().form_valid(form)

        company = form.cleaned_data["company"]
        self.request.session["active_company_id"] = company.id

        return response
