from django.urls import path

from .views import (
    TransportHomeView,
    TransportUnitCreateView,
    TransportUnitListView,
    TransportUnitModelCreateView,
    TransportUnitModelListView,
    TransportUnitModelUpdateView,
    TransportUnitTypeCreateView,
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
    path("types/", TransportUnitTypeListView.as_view(), name="type_list"),
    path("types/create/", TransportUnitTypeCreateView.as_view(), name="type_create"),
    path(
        "types/<int:pk>/edit/", TransportUnitTypeUpdateView.as_view(), name="type_edit"
    ),
    path("models/", TransportUnitModelListView.as_view(), name="model_list"),
    path("models/create/", TransportUnitModelCreateView.as_view(), name="model_create"),
    path(
        "models/<int:pk>/edit/",
        TransportUnitModelUpdateView.as_view(),
        name="model_edit",
    ),
]