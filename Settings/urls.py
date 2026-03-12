from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("lab2.urls")),
    path("", include("authapp.urls")),
]
