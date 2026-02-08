from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from .views import HomeView, UnderConstructionView, MainView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("admin/", admin.site.urls),
    path("main/", MainView.as_view(), name="main"),
    path("persons/", include("persons.urls", namespace="persons")),
    path("users/", include("users.urls", namespace="users")),
    path("companies/", include("companies.urls", namespace="companies")),
    path("staff/", include("staff.urls", namespace="staff")),
    path(
        "under-construction/",
        UnderConstructionView.as_view(),
        name="under_construction",
    ),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
