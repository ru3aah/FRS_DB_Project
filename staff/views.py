from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from persons.views import NavbarContextMixin


class StaffHomeView(NavbarContextMixin, LoginRequiredMixin, TemplateView):
    template_name = "staff/index.html"
