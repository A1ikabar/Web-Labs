# authapp/oauth_views.py
# Контроллеры (views) для OAuth 2.0 входа через Яндекс

from django.http import JsonResponse, HttpResponseRedirect  # Типы ответов HTTP
from django.views.decorators.csrf import csrf_exempt  # Отключение CSRF для API
from django.views.decorators.http import require_http_methods  # Ограничение HTTP-методов
from django.utils import timezone
from datetime import timedelta
import json
from django.views.decorators.csrf import csrf_exempt
from .oauth_service import YandexOAuthService  # Сервис OAuth-логики
from .jwt_utils import decode_access_token  # Утилиты JWT
from authapp.auth_service import get_current_user_from_access_token  # Валидация токена
from users.models import UserToken  # Модель токенов


@require_http_methods(["GET"])
def oauth_initiate(request, provider: str):
    """
    Инициация OAuth входа.
    GET /auth/oauth/yandex
    
    Этапы:
    1. Проверяем, что провайдер поддерживается (только yandex)
    2. Генерируем state-токен для CSRF-защиты
    3. Формируем URL для редиректа на Яндекс
    4. Перенаправляем пользователя на Яндекс OAuth
    
    Возвращает: 302 Redirect на Яндекс
    """
    # Проверяем, что провайдер поддерживается (в данном случае только yandex)
    if provider.lower() != 'yandex':
        return JsonResponse({"error": "Неподдерживаемый провайдер"}, status=400)

    # Генерируем уникальный state-токен для защиты от CSRF-атак
    state = YandexOAuthService.generate_state()

    # Формируем полный URL для редиректа на Яндекс OAuth
    authorization_url = YandexOAuthService.get_authorization_url(state)

    # Перенаправляем пользователя на Яндекс (авторизация)
    return HttpResponseRedirect(authorization_url)


@require_http_methods(["GET"])
@csrf_exempt
def oauth_callback(request, provider: str):
    """
    Обработка callback от OAuth провайдера.
    GET /auth/oauth/yandex/callback?code={code}&state={state}
    
    Этапы:
    1. Получаем code и state из query-параметров
    2. Проверяем наличие ошибок от провайдера
    3. Валидируем state (CSRF-защита)
    4. Обмениваем code на access_token Яндекс
    5. Получаем данные пользователя от Яндекс
    6. Находим или создаём пользователя в локальной БД
    7. Генерируем локальные JWT-токены
    8. Устанавливаем токены в HttpOnly cookies
    9. Перенаправляем на фронтенд (или возвращаем успех)
    
    Возвращает: 302 Redirect или JSON с токенами
    """
    # Проверяем, что провайдер поддерживается
    if provider.lower() != 'yandex':
        return JsonResponse({"error": "Неподдерживаемый провайдер"}, status=400)

    # Получаем параметры от Яндекс (code, state, error)
    code = request.GET.get('code')  # Код авторизации для обмена на токен
    state = request.GET.get('state')  # CSRF-токен для проверки
    error = request.GET.get('error')  # Код ошибки от Яндекс

    # Проверяем наличие ошибок от провайдера
    if error:
        return JsonResponse({"error": f"OAuth ошибка: {error}"}, status=400)

    # Проверяем, что код авторизации получен
    if not code:
        return JsonResponse({"error": "Код авторизации не получен"}, status=400)

    # Проверяем state-токен (защита от CSRF-атак)
    if not state or not YandexOAuthService.validate_state(state):
        return JsonResponse({"error": "Неверный state-токен"}, status=403)

    try:
        # Обмен кода авторизации на access-токен Яндекс
        token_data = YandexOAuthService.exchange_code_for_token(code)
        yandex_access_token = token_data.get('access_token')

        # Получение данных пользователя от Яндекс (email, yandex_id)
        yandex_info = YandexOAuthService.get_user_info(yandex_access_token)

        # Поиск существующего пользователя или создание нового
        user = YandexOAuthService.find_or_create_user(yandex_info)

        # Генерация локальных JWT-токенов (access + refresh)
        access_token, refresh_token = YandexOAuthService.create_local_session(user)

    except ValueError as e:
        # Ошибка валидации или OAuth
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        # Внутренняя ошибка сервера
        return JsonResponse({"error": "Внутренняя ошибка сервера"}, status=500)