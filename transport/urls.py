from django.urls import path

from .views import (
    TransportHomeView,
    TransportUnitCreateView,
    TransportUnitDeleteView,
    TransportUnitListView,
    TransportUnitModelCreateView,
    TransportUnitModelDeleteView,
    TransportUnitModelListView,
    TransportUnitModelUpdateView,
    TransportUnitTypeCreateView,
    TransportUnitTypeDeleteView,
    TransportUnitTypeListView,
    TransportUnitTypeUpdateView,
    TransportUnitUpdateView,
)

app_name = "transport"

urlpatterns = [
    path("", TransportHomeView.as_view(), name="index"),
    path("units/", TransportUnitListView.as_view(), name="unit_list"),
    path("units/create/", TransportUnitCreateView.as_view(), name="unit_create"),
    path("units/<int:pk>/edit/", TransportUnitUpdateView.as_view(), name="unit_edit"),
    path(
        "units/<int:pk>/delete/", TransportUnitDeleteView.as_view(), name="unit_delete"
    ),
    path("types/", TransportUnitTypeListView.as_view(), name="type_list"),
    path("types/create/", TransportUnitTypeCreateView.as_view(), name="type_create"),
    path(
        "types/<int:pk>/edit/", TransportUnitTypeUpdateView.as_view(), name="type_edit"
    ),
    path(
        "types/<int:pk>/delete/",
        TransportUnitTypeDeleteView.as_view(),
        name="type_delete",
    ),
    path("models/", TransportUnitModelListView.as_view(), name="model_list"),
    path("models/create/", TransportUnitModelCreateView.as_view(), name="model_create"),
    path(
        "models/<int:pk>/edit/",
        TransportUnitModelUpdateView.as_view(),
        name="model_edit",
    ),
    path(
        "models/<int:pk>/delete/",
        TransportUnitModelDeleteView.as_view(),
        name="model_delete",
    ),
]