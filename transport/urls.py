from django.urls import path

from .views import TransportHomeView

app_name = "transport"

urlpatterns = [
    path("", TransportHomeView.as_view(), name="index"),
]