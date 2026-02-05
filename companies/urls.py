from django.urls import path
from .views import SelectCompanyView

app_name = "companies"

urlpatterns = [
    path("select/", SelectCompanyView.as_view(), name="select_company"),
]
