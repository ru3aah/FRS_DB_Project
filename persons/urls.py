from django.urls import path
from . import views

app_name = "persons"

urlpatterns = urlpatterns = [
    path("", views.index, name="index"),
    path("<int:pk>/", views.person_detail, name="detail"),
]
