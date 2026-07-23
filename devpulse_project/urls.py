from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path("admin/", admin.site.urls),

    path("login/", TemplateView.as_view(template_name="login.html"), name="login"),
    path("dashboard/", TemplateView.as_view(template_name="dashboard.html"), name="dashboard"),

    path("api/auth/", include("accounts.urls")),
    path("api/", include("teams.urls")),
    path("api/", include("github_integration.urls")),
    path("api/metrics/", include("metrics.urls")),

    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
