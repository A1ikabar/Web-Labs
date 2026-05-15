from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from common.health_views import health, health_ready, health_live

urlpatterns = [
    path("admin/", admin.site.urls),

    path("health", health, name="health"),
    path("health/ready", health_ready, name="health_ready"),
    path("health/live", health_live, name="health_live"),

    path("", include("lab2.urls")),
    path("", include("authapp.urls")),
    path("", include("storage.urls")),
    path("", include("users.urls")),
]

if settings.DEBUG:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    ]