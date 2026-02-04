from django.shortcuts import render, get_object_or_404
from .models import Person


def index(request):
    persons = Person.objects.all()
    return render(request, "persons/index.html", {"persons": persons})


def person_detail(request, pk):
    person = get_object_or_404(Person, pk=pk)
    return render(request, "persons/detail.html", {"person": person})
