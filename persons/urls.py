from django.urls import path

from .views import (
    PersonListView,
    PersonDetailView,
    PersonCreateView,
    PersonUpdateView,
)

app_name = "persons"

urlpatterns = [
    path("", PersonListView.as_view(), name="index"),
    path("create/", PersonCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", PersonUpdateView.as_view(), name="edit"),
    path("<int:pk>/", PersonDetailView.as_view(), name="detail"),
]
