from django.urls import path
from authapp.views import register, login, whoami, refresh, logout, logout_all

urlpatterns = [
    path("auth/register", register),
    path("auth/login", login),
    path("auth/whoami", whoami),
    path("auth/refresh", refresh),
    path("auth/logout", logout),
    path("auth/logout-all", logout_all),
]