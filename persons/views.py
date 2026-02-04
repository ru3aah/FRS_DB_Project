from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView

from .models import Person


class PersonListView(LoginRequiredMixin, ListView):
    model = Person
    template_name = "persons/index.html"
    context_object_name = "persons"


class PersonDetailView(LoginRequiredMixin, DetailView):
    model = Person
    template_name = "persons/detail.html"
    context_object_name = "person"


class PersonCreateView(LoginRequiredMixin, CreateView):
    model = Person
    template_name = "persons/form.html"
    fields = "__all__"
    success_url = reverse_lazy("persons:index")


class PersonUpdateView(LoginRequiredMixin, UpdateView):
    model = Person
    template_name = "persons/form.html"
    fields = "__all__"
    success_url = reverse_lazy("persons:index")
