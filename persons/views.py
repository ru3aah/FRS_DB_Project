from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from companies.models import Company
from .forms import IDTypeForm, PersonForm, PersonIDForm, PersonIDScanForm
from .models import IDType, Person, PersonID, PersonIDScan


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
# Duplicate check helpers
# -----------------------
def _find_duplicate_person(
    *,
    first_name: str,
    second_name: str,
    family_name: str,
    dob,
    exclude_person_id: int | None = None,
) -> Person | None:
    """
    Returns existing Person with same (first+second+family+dob), or None.
    Case-insensitive for names.
    """
    first_name = (first_name or "").strip()
    second_name = (second_name or "").strip()
    family_name = (family_name or "").strip()

    if not (first_name and second_name and family_name and dob):
        return None

    qs = Person.objects.filter(
        first_name__iexact=first_name,
        second_name__iexact=second_name,
        family_name__iexact=family_name,
        dob=dob,
    )
    if exclude_person_id:
        qs = qs.exclude(person_id=exclude_person_id)

    return qs.first()


# -----------------------
# Persons
# -----------------------
class PersonListView(NavbarContextMixin, HRAccessMixin, ListView):
    model = Person
    template_name = "persons/index.html"
    context_object_name = "persons"
    paginate_by = 25

    def get_queryset(self):
        qs = Person.objects.select_related("company", "nationality").order_by(
            "family_name",
            "first_name",
            "second_name",
            "person_id",
        )

        show_mode = (self.request.GET.get("show") or "").strip().lower()
        active_company_id = self.request.session.get("active_company_id")

        if show_mode != "all" and active_company_id:
            qs = qs.filter(company_id=active_company_id)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["can_manage_hr"] = user.is_superuser or user.has_perm("persons.hr_manager")
        ctx["show_all"] = (self.request.GET.get("show") or "").strip().lower() == "all"
        return ctx


class PersonDetailView(NavbarContextMixin, HRAccessMixin, DetailView):
    model = Person
    template_name = "persons/detail.html"
    context_object_name = "person"

    def get_queryset(self):
        return Person.objects.select_related("company", "nationality")


class PersonCreateView(NavbarContextMixin, HRAccessMixin, CreateView):
    model = Person
    template_name = "persons/form.html"
    form_class = PersonForm

    def form_valid(self, form):
        cd = form.cleaned_data

        existing = _find_duplicate_person(
            first_name=cd.get("first_name"),
            second_name=cd.get("second_name"),
            family_name=cd.get("family_name"),
            dob=cd.get("dob"),
            exclude_person_id=None,
        )

        dup_confirm = (self.request.POST.get("dup_confirm") or "").strip() == "1"

        # Duplicate found, not confirmed -> show modal, do NOT save
        if existing is not None and not dup_confirm:
            ctx = self.get_context_data(form=form)
            ctx["dup_person"] = existing
            ctx["show_dup_modal"] = True
            return self.render_to_response(ctx)

        active_company_id = self.request.session.get("active_company_id")
        if active_company_id:
            form.instance.company_id = active_company_id

        response = super().form_valid(form)
        messages.success(self.request, "Person created and saved.")
        return response

    def get_success_url(self):
        return reverse("persons:edit", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
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

    def get_queryset(self):
        return Person.objects.select_related("company", "nationality")

    def form_valid(self, form):
        cd = form.cleaned_data
        exclude_id = getattr(self.object, "person_id", None)

        existing = _find_duplicate_person(
            first_name=cd.get("first_name"),
            second_name=cd.get("second_name"),
            family_name=cd.get("family_name"),
            dob=cd.get("dob"),
            exclude_person_id=exclude_id,
        )

        dup_confirm = (self.request.POST.get("dup_confirm") or "").strip() == "1"

        # Duplicate found, not confirmed -> show modal, do NOT save
        if existing is not None and not dup_confirm:
            ctx = self.get_context_data(form=form)
            ctx["dup_person"] = existing
            ctx["show_dup_modal"] = True
            return self.render_to_response(ctx)

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

        ctx["person_docs"] = docs_page_obj.object_list
        ctx["docs_page_obj"] = docs_page_obj
        ctx["docs_is_paginated"] = docs_page_obj.has_other_pages()
        ctx["docs_page_param"] = self.DOCS_PAGE_PARAM

        return ctx


# -----------------------
# PersonID (Documents) CRUD
# -----------------------
class PersonIDBaseMixin(NavbarContextMixin, HRAccessMixin):
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

    SCANS_PER_PAGE = 9
    SCANS_PAGE_PARAM = "scans_page"

    def get_queryset(self):
        return PersonID.objects.filter(person=self.person_obj)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        scans_qs = PersonIDScan.objects.filter(person_id=self.object).order_by(
            "-uploaded_at"
        )

        paginator = Paginator(scans_qs, self.SCANS_PER_PAGE)
        page_number = self.request.GET.get(self.SCANS_PAGE_PARAM) or 1
        scans_page_obj = paginator.get_page(page_number)

        ctx["scans_page_obj"] = scans_page_obj
        ctx["scans_is_paginated"] = scans_page_obj.has_other_pages()
        ctx["scans_page_param"] = self.SCANS_PAGE_PARAM
        ctx["scans"] = scans_page_obj.object_list

        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)

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
# Scans create / update / delete
# -----------------------
class PersonIDScanBaseMixin(PersonIDBaseMixin):
    doc_obj: PersonID

    def dispatch(self, request, *args, **kwargs):
        self.person_obj = get_object_or_404(Person, pk=kwargs["person_pk"])
        self.doc_obj = get_object_or_404(
            PersonID, pk=kwargs["doc_pk"], person=self.person_obj
        )
        return super(PersonIDBaseMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["doc_obj"] = self.doc_obj
        return ctx


class PersonIDScanCreateView(PersonIDScanBaseMixin, CreateView):
    model = PersonIDScan
    form_class = PersonIDScanForm
    template_name = "persons/scan_form.html"

    def form_valid(self, form):
        form.instance.person_id = self.doc_obj
        response = super().form_valid(form)
        messages.success(self.request, "Scan uploaded.")
        return response

    def get_success_url(self):
        return reverse(
            "persons:doc_edit",
            kwargs={"person_pk": self.person_obj.pk, "doc_pk": self.doc_obj.pk},
        )


class PersonIDScanUpdateView(PersonIDScanBaseMixin, UpdateView):
    model = PersonIDScan
    form_class = PersonIDScanForm
    template_name = "persons/scan_form.html"
    pk_url_kwarg = "scan_pk"

    def get_queryset(self):
        return PersonIDScan.objects.filter(person_id=self.doc_obj)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Scan updated.")
        return response

    def get_success_url(self):
        return reverse(
            "persons:doc_edit",
            kwargs={"person_pk": self.person_obj.pk, "doc_pk": self.doc_obj.pk},
        )


class PersonIDScanDeleteView(PersonIDBaseMixin, DeleteView):
    model = PersonIDScan
    pk_url_kwarg = "scan_pk"
    template_name = "persons/scan_confirm_delete.html"

    def get_queryset(self):
        return PersonIDScan.objects.filter(person_id_id=self.kwargs["doc_pk"])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
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
        next_url = self.request.POST.get("next") or self.request.GET.get("next")
        if next_url:
            return next_url
        return reverse_lazy("persons:index")
