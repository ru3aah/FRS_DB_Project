from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView

from .forms import EmailAuthenticationForm

app_name = "users"

urlpatterns = [
    path(
        "login/",
        LoginView.as_view(
            template_name="users/login.html",
            authentication_form=EmailAuthenticationForm,
        ),
        name="login",
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
]
