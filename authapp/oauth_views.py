# authapp/oauth_views.py

from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import timedelta
import json

from .oauth_service import YandexOAuthService
from .jwt_utils import decode_access_token
from authapp.auth_service import get_current_user_from_access_token
from users.models import UserToken

@require_http_methods(["GET"])
def oauth_initiate(request, provider: str):
    """
    Инициация OAuth входа
    GET /auth/oauth/yandex
    """
    if provider.lower() != 'yandex':
        return JsonResponse({"error": "Неподдерживаемый провайдер"}, status=400)
    
    # ✅ Генерация state для защиты от CSRF
    state = YandexOAuthService.generate_state()
    request.session['oauth_state'] = state
    
    # ✅ Формирование URL для редиректа
    authorization_url = YandexOAuthService.get_authorization_url(state)
    
    # ✅ Редирект на Яндекс
    return HttpResponseRedirect(authorization_url)


@require_http_methods(["GET"])
def oauth_callback(request, provider: str):
    """
    Обработка callback от OAuth провайдера
    GET /auth/oauth/yandex/callback
    """
    if provider.lower() != 'yandex':
        return JsonResponse({"error": "Неподдерживаемый провайдер"}, status=400)
    
    # ✅ Получение параметров от Яндекс
    code = request.GET.get('code')
    state = request.GET.get('state')
    error = request.GET.get('error')
    
    # ✅ Проверка на ошибки от провайдера
    if error:
        return JsonResponse({"error": f"OAuth ошибка: {error}"}, status=400)
    
    if not code:
        return JsonResponse({"error": "Код авторизации не получен"}, status=400)
    
    # ✅ Проверка state (защита от CSRF)
    saved_state = request.session.get('oauth_state')

    if not state or not saved_state or state != saved_state:
        return JsonResponse({"error": "Неверный state-токен"}, status=403)

    del request.session['oauth_state']
    
    try:
        # ✅ Обмен кода на токен Яндекс
        token_data = YandexOAuthService.exchange_code_for_token(code)
        yandex_access_token = token_data.get('access_token')
        
        # ✅ Получение данных пользователя
        yandex_info = YandexOAuthService.get_user_info(yandex_access_token)
        print("YANDEX INFO:", yandex_info)
        
        # ✅ Поиск или создание пользователя в локальной БД
        user = YandexOAuthService.find_or_create_user(yandex_info)
        
        # ✅ Генерация локальных JWT токенов
        access_token, refresh_token = YandexOAuthService.create_local_session(user)
        
        # ✅ Установка HttpOnly cookies
        response = HttpResponseRedirect('http://localhost:3000/oauth-success')  # Редирект на фронтенд
        
        response.set_cookie(
            key='access_token',
            value=access_token,
            httponly=True,
            samesite='Lax',
            max_age=15 * 60,  # 15 минут
            secure=False,  # True для HTTPS
        )
        
        response.set_cookie(
            key='refresh_token',
            value=refresh_token,
            httponly=True,
            samesite='Lax',
            max_age=7 * 24 * 60 * 60,  # 7 дней
            secure=False,  # True для HTTPS
        )
        
        return response
        
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)