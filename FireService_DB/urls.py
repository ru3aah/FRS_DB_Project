from django.contrib import admin
from django.urls import include, path

from .views import HomeView, MainView, UnderConstructionView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("main/", MainView.as_view(), name="main"),
    path(
        "under-construction/",
        UnderConstructionView.as_view(),
        name="under_construction",
    ),
    path("admin/", admin.site.urls),
    path("companies/", include(("companies.urls", "companies"), namespace="companies")),
    path("persons/", include(("persons.urls", "persons"), namespace="persons")),
    path("users/", include(("users.urls", "users"), namespace="users")),
    path("staff/", include(("staff.urls", "staff"), namespace="staff")),
]
