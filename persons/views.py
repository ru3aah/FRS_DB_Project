from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)

from companies.models import Company
from .forms import PersonForm, PersonIDForm, IDTypeForm
from .models import Person, PersonID, PersonIDScan, IDType

# -----------------------
# Common mixins
# -----------------------


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
    - staff with persons.hr_manager permission
    """

    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.has_perm("persons.hr_manager")


# -----------------------
# Persons
# -----------------------


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

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Person created and saved.")
        return response

    def get_success_url(self):
        return reverse("persons:edit", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # docs disabled until person exists
        ctx["docs_page_obj"] = None
        ctx["docs_is_paginated"] = False
        ctx["docs_page_param"] = "docs_page"
        return ctx


class PersonUpdateView(NavbarContextMixin, HRAccessMixin, UpdateView):
    model = Person
    template_name = "persons/form.html"
    form_class = PersonForm

    DOCS_PER_PAGE = 10
    DOCS_PAGE_PARAM = "docs_page"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Changes saved.")
        return response

    def get_success_url(self):
        return reverse("persons:edit", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        qs = (
            PersonID.objects.filter(person=self.object)
            .select_related("id_type", "issued_country")
            .order_by("id_type__name", "id_number")
        )

        paginator = Paginator(qs, self.DOCS_PER_PAGE)
        page_number = self.request.GET.get(self.DOCS_PAGE_PARAM) or 1
        docs_page_obj = paginator.get_page(page_number)

        # backward compat (если где-то ещё используется person_docs)
        ctx["person_docs"] = docs_page_obj.object_list

        # pagination vars for template
        ctx["docs_page_obj"] = docs_page_obj
        ctx["docs_is_paginated"] = docs_page_obj.has_other_pages()
        ctx["docs_page_param"] = self.DOCS_PAGE_PARAM

        return ctx


# -----------------------
# PersonID (Documents) CRUD
# -----------------------


class PersonIDBaseMixin(NavbarContextMixin, HRAccessMixin):
    """
    Ensures we always work within a specific Person.
    URL contains: person_pk
    """

    person_obj: Person

    def dispatch(self, request, *args, **kwargs):
        self.person_obj = get_object_or_404(Person, pk=kwargs["person_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["person_obj"] = self.person_obj
        return ctx


class PersonIDCreateView(PersonIDBaseMixin, CreateView):
    model = PersonID
    form_class = PersonIDForm
    template_name = "persons/doc_form.html"

    def form_valid(self, form):
        form.instance.person = self.person_obj
        response = super().form_valid(form)

        # Save uploaded scans (multi)
        for f in self.request.FILES.getlist("scans"):
            PersonIDScan.objects.create(person_id=self.object, file=f)

        messages.success(self.request, "Document saved.")
        return response

    def get_success_url(self):
        return reverse(
            "persons:doc_edit",
            kwargs={"person_pk": self.person_obj.pk, "doc_pk": self.object.pk},
        )


class PersonIDUpdateView(PersonIDBaseMixin, UpdateView):
    model = PersonID
    form_class = PersonIDForm
    template_name = "persons/doc_form.html"
    pk_url_kwarg = "doc_pk"

    def get_queryset(self):
        return PersonID.objects.filter(person=self.person_obj)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # existing scans list for UI
        ctx["scans"] = PersonIDScan.objects.filter(person_id=self.object).order_by(
            "-uploaded_at"
        )
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)

        # Save uploaded scans (multi)
        for f in self.request.FILES.getlist("scans"):
            PersonIDScan.objects.create(person_id=self.object, file=f)

        messages.success(self.request, "Changes saved.")
        return response

    def get_success_url(self):
        return reverse(
            "persons:doc_edit",
            kwargs={"person_pk": self.person_obj.pk, "doc_pk": self.object.pk},
        )


class PersonIDDeleteView(PersonIDBaseMixin, DeleteView):
    model = PersonID
    template_name = "persons/doc_confirm_delete.html"
    pk_url_kwarg = "doc_pk"

    def get_queryset(self):
        return PersonID.objects.filter(person=self.person_obj)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Document deleted.")
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("persons:edit", kwargs={"pk": self.person_obj.pk})


# -----------------------
# Scans delete
# -----------------------


class PersonIDScanDeleteView(PersonIDBaseMixin, DeleteView):
    model = PersonIDScan
    pk_url_kwarg = "scan_pk"
    template_name = "persons/scan_confirm_delete.html"

    def get_queryset(self):
        # Limit by current document (doc_pk from URL)
        return PersonIDScan.objects.filter(person_id_id=self.kwargs["doc_pk"])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # IMPORTANT: pass doc_pk to template to build correct links
        ctx["doc_pk"] = int(self.kwargs["doc_pk"])
        return ctx

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Scan deleted.")
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(
            "persons:doc_edit",
            kwargs={
                "person_pk": int(self.kwargs["person_pk"]),
                "doc_pk": int(self.kwargs["doc_pk"]),
            },
        )


# -----------------------
# Reference: IDType
# -----------------------


class IDTypeCreateView(NavbarContextMixin, HRAccessMixin, CreateView):
    model = IDType
    form_class = IDTypeForm
    template_name = "persons/idtype_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Document type saved.")
        return response

    def get_success_url(self):
        next_url = self.request.GET.get("next")
        if next_url:
            return next_url
        return reverse_lazy("persons:index")
