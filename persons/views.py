from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView

from companies.models import Company
from .forms import PersonForm
from .models import Person


class NavbarContextMixin:
    """
    Adds common context variables used by includes/navbar.html:
      - person: request.user.person (if set)
      - company: Company from session["active_company_id"] (if set)
    """

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        user = getattr(self.request, "user", None)
        ctx["person"] = (
            getattr(user, "person", None) if user and user.is_authenticated else None
        )

        company_id = self.request.session.get("active_company_id")
        ctx["company"] = (
            Company.objects.filter(id=company_id).first() if company_id else None
        )

        return ctx


class HRAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Allow access only for:
    - superuser
    - users with persons.hr_manager permission
    """

    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.has_perm("persons.hr_manager")


class PersonListView(NavbarContextMixin, HRAccessMixin, ListView):
    model = Person
    template_name = "persons/index.html"
    context_object_name = "persons"
    paginate_by = 25

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["can_manage_hr"] = user.is_superuser or user.has_perm("persons.hr_manager")
        return ctx


class PersonDetailView(NavbarContextMixin, HRAccessMixin, DetailView):
    model = Person
    template_name = "persons/detail.html"
    context_object_name = "person"


class PersonCreateView(NavbarContextMixin, HRAccessMixin, CreateView):
    model = Person
    template_name = "persons/form.html"
    form_class = PersonForm
    success_url = reverse_lazy("persons:index")


class PersonUpdateView(NavbarContextMixin, HRAccessMixin, UpdateView):
    model = Person
    template_name = "persons/form.html"
    form_class = PersonForm
    success_url = reverse_lazy("persons:index")
