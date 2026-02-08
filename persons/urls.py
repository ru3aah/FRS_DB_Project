from django.urls import path

from .views import (
    PersonListView,
    PersonDetailView,
    PersonCreateView,
    PersonUpdateView,
    PersonIDCreateView,
    PersonIDUpdateView,
    PersonIDDeleteView,
    PersonIDScanDeleteView,
    IDTypeCreateView,
)

app_name = "persons"

urlpatterns = [
    path("", PersonListView.as_view(), name="index"),
    path("create/", PersonCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", PersonUpdateView.as_view(), name="edit"),
    path("<int:pk>/", PersonDetailView.as_view(), name="detail"),
    # Documents
    path(
        "<int:person_pk>/docs/create/", PersonIDCreateView.as_view(), name="doc_create"
    ),
    path(
        "<int:person_pk>/docs/<int:doc_pk>/edit/",
        PersonIDUpdateView.as_view(),
        name="doc_edit",
    ),
    path(
        "<int:person_pk>/docs/<int:doc_pk>/delete/",
        PersonIDDeleteView.as_view(),
        name="doc_delete",
    ),
    # Scans (files) delete
    path(
        "<int:person_pk>/docs/<int:doc_pk>/scans/<int:scan_pk>/delete/",
        PersonIDScanDeleteView.as_view(),
        name="scan_delete",
    ),
    # Reference
    path("idtypes/create/", IDTypeCreateView.as_view(), name="idtype_create"),
]
