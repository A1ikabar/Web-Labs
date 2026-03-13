from django.urls import path
from authapp.views import register, login, whoami, refresh, logout, logout_all
from django.urls import path
from .oauth_views import oauth_initiate, oauth_callback

urlpatterns = [
    path("auth/register", register),
    path("auth/login", login),
    path("auth/whoami", whoami),
    path("auth/refresh", refresh),
    path("auth/logout", logout),
    path("auth/logout-all", logout_all),
    path('auth/oauth/<str:provider>', oauth_initiate, name='oauth-initiate'),
    path('auth/oauth/<str:provider>/callback', oauth_callback, name='oauth-callback'),
]