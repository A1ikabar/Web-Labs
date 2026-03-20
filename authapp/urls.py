# authapp/urls.py
# Маршрутизация (URL routing) для endpoints аутентификации

from django.urls import path  # Функция для определения URL-паттернов
from authapp.views import register, login, whoami, refresh, logout, logout_all  # Views для auth
from django.urls import path  # Импортируем повторно (можно убрать дублирование)
from .oauth_views import oauth_initiate, oauth_callback  # Views для OAuth

# Список URL-паттернов приложения authapp
# Каждый паттерн связывает URL с view-функцией
urlpatterns = [
    # Регистрация нового пользователя
    # POST /auth/register
    path("auth/register", register),
    
    # Вход пользователя (получение токенов)
    # POST /auth/login
    path("auth/login", login),
    
    # Проверка текущего авторизованного пользователя
    # GET /auth/whoami
    path("auth/whoami", whoami),
    
    # Обновление пары токенов (access + refresh)
    # POST /auth/refresh
    path("auth/refresh", refresh),
    
    # Завершение текущей сессии (logout)
    # POST /auth/logout
    path("auth/logout", logout),
    
    # Завершение всех сессий пользователя (logout from all devices)
    # POST /auth/logout-all
    path("auth/logout-all", logout_all),
    
    # Инициация OAuth входа (редирект на Яндекс)
    # GET /auth/oauth/yandex
    path('auth/oauth/<str:provider>', oauth_initiate, name='oauth-initiate'),
    
    # Callback от OAuth провайдера (обработка возврата)
    # GET /auth/oauth/yandex/callback
    path('auth/oauth/<str:provider>/callback', oauth_callback, name='oauth-callback'),
]