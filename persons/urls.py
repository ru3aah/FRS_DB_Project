from django.urls import path
from . import views

app_name = "persons"
urlpatterns = [
    path("", views.index, name="index"),  # список всех Person
    path("person/<int:pk>/", views.person_detail, name="detail"),
]