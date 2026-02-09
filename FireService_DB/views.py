# FireService_DB/views.py
from django.contrib.auth import logout
from django.views.generic import TemplateView


class HomeView(TemplateView):
    template_name = "home.html"

    def dispatch(self, request, *args, **kwargs):
        # Полностью завершить сессию при заходе на home (/)
        if request.user.is_authenticated:
            logout(request)
        # flush убивает session key и очищает все session data (включая active_company_id)
        request.session.flush()
        return super().dispatch(request, *args, **kwargs)


class MainView(TemplateView):
    template_name = "main.html"


class UnderConstructionView(TemplateView):
    template_name = "under_construction.html"
