from django.contrib.auth import logout
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponseNotAllowed
from django.urls import reverse_lazy

from .forms import CustomLoginForm


class CustomLoginView(LoginView):
    template_name = "users/login.html"
    authentication_form = CustomLoginForm

    # Иначе будет цикл /users/login -> /main -> /users/login
    redirect_authenticated_user = False

    def get_success_url(self):
        return reverse_lazy("main")

    def dispatch(self, request, *args, **kwargs):
        # Если пользователь уже залогинен и компания уже выбрана — сразу в main
        if request.user.is_authenticated and request.session.get("active_company_id"):
            return super().redirect_to_success_url()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        company = form.cleaned_data["company"]
        self.request.session["active_company_id"] = company.id
        return response


class CustomLogoutView(LogoutView):
    """
    Logout только через POST.
    Дополнительно чистим active_company_id.
    """

    next_page = reverse_lazy("home")

    def get(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(["POST"])

    def post(self, request, *args, **kwargs):
        # чистим сессию выбора компании
        request.session.pop("active_company_id", None)
        return super().post(request, *args, **kwargs)
