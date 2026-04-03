from django.urls import path

from .views import (
    TransportHomeView,
    TransportUnitListView,
    TransportUnitTypeCreateView,
    TransportUnitTypeListView,
)

app_name = "transport"

urlpatterns = [
    path("", TransportHomeView.as_view(), name="index"),
    path("units/", TransportUnitListView.as_view(), name="unit_list"),
    path("types/", TransportUnitTypeListView.as_view(), name="type_list"),
    path("types/create/", TransportUnitTypeCreateView.as_view(), name="type_create"),
]