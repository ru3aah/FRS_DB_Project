from django.urls import path

from .views import StaffHomeView

app_name = "staff"

urlpatterns = [
    path("", StaffHomeView.as_view(), name="index"),
]
