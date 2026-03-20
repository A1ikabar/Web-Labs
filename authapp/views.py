# authapp/views.py
# Контроллеры (views) для аутентификации и авторизации
# Реализуют endpoints: register, login, whoami, refresh, logout, logout-all

import json  # Парсинг JSON из тела запроса
from django.http import JsonResponse  # HTTP-ответ в формате JSON
from django.views.decorators.csrf import csrf_exempt  # Отключение CSRF для API endpoints

from authapp.dto import RegisterDTO, LoginDTO  # DTO для валидации входных данных

from authapp.auth_service import (  # Сервисный слой бизнес-логики
    register_user,      # Регистрация
    login_user,         # Вход
    get_current_user_from_access_token,  # Получение пользователя из токена
    refresh_user_tokens,  # Обновление пары токенов
    logout_user,        # Завершение текущей сессии
    logout_all_user_sessions,  # Завершение всех сессий
)


@csrf_exempt
def register(request):
    """
    Регистрация нового пользователя.
    POST /auth/register
    
    Тело запроса (JSON):
    {
        "email": "user@example.com",
        "password": "securePassword123",
        "phone": "+79991234567"  # опционально
    }
    
    Возвращает:
    201 Created: {"id": "uuid", "email": "user@example.com"}
    400 Bad Request: {"error": "описание ошибки"}
    """
    try:
        # Парсим JSON из тела запроса
        body = json.loads(request.body)
        # Создаём DTO с валидацией данных
        dto = RegisterDTO(body)
        # Вызываем сервисный слой для регистрации
        user = register_user(dto)

        # Возвращаем успешный ответ с данными пользователя
        return JsonResponse({
            "id": str(user.id),  # UUID → строка для JSON
            "email": user.email,
        }, status=201)

    except ValueError as e:
        # Ошибка валидации (email занят, слабый пароль и т.д.)
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def login(request):
    """
    Аутентификация пользователя (вход).
    POST /auth/login
    
    Тело запроса (JSON):
    {
        "email": "user@example.com",
        "password": "securePassword123"
    }
    
    Возвращает:
    200 OK: {"message": "login successful", "email": "user@example.com"}
    Устанавливает HttpOnly cookies: access_token (15 мин), refresh_token (7 дней)
    
    400 Bad Request: {"error": "описание ошибки"}
    405 Method Not Allowed: если метод не POST
    """
    # Проверяем, что запрос методом POST
    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    try:
        # Парсим JSON из тела запроса
        body = json.loads(request.body)

        # Создаём DTO с валидацией
        dto = LoginDTO(body)

        # Вызываем сервис аутентификации
        # Возвращает: (user, access_token, refresh_token)
        user, access_token, refresh_token = login_user(
            dto.email,
            dto.password
        )

        # Создаём HTTP-ответ с успешным сообщением
        response = JsonResponse({
            "message": "login successful",
            "email": user.email
        }, status=200)

        # Устанавливаем access_token в HttpOnly cookie
        # httponly=True — JavaScript не имеет доступа (защита от XSS)
        # samesite="Lax" — защита от CSRF (cookie не отправляется на чужие сайты)
        # max_age=15*60 — время жизни 15 минут в секундах
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            samesite="Lax",
            max_age=15 * 60,
        )

        # Устанавливаем refresh_token в HttpOnly cookie
        # max_age=7*24*60*60 — время жизни 7 дней в секундах
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            samesite="Lax",
            max_age=7 * 24 * 60 * 60,
        )

        return response

    except ValueError as e:
        # Ошибка аутентификации (неверный email/пароль)
        return JsonResponse({"error": str(e)}, status=400)


def whoami(request):
    """
    Проверка текущего аутентифицированного пользователя.
    GET /auth/whoami
    
    Поскольку JavaScript не имеет доступа к HttpOnly cookies,
    фронтенд использует этот endpoint для определения:
    - Авторизован ли пользователь
    - Данные текущего пользователя
    
    Возвращает:
    200 OK: {"id": "uuid", "email": "user@example.com", "phone": "..."}
    401 Unauthorized: если токен отсутствует или невалиден
    405 Method Not Allowed: если метод не GET
    """
    # Проверяем, что запрос методом GET
    if request.method != "GET":
        return JsonResponse({"error": "method not allowed"}, status=405)

    # Получаем access-токен из cookies
    access_token = request.COOKIES.get("access_token")

    # Если токен отсутствует — возвращаем 401
    if not access_token:
        return JsonResponse({"error": "unauthorized"}, status=401)

    try:
        # Валидируем токен и получаем пользователя
        user = get_current_user_from_access_token(access_token)

        # Возвращаем профиль пользователя (без чувствительных данных)
        return JsonResponse({
            "id": str(user.id),
            "email": user.email,
            "phone": user.phone,
        }, status=200)

    except ValueError as e:
        # Токен невалиден, истёк или отозван
        return JsonResponse({"error": str(e)}, status=401)


@csrf_exempt
def refresh(request):
    """
    Обновление пары токенов по refresh-токену.
    POST /auth/refresh
    
    Используется, когда access-токен истёк (15 минут).
    Фронтенд автоматически вызывает этот endpoint при получении 401.
    
    Возвращает:
    200 OK: {"message": "tokens refreshed", "email": "..."}
    Устанавливает новые cookies: access_token, refresh_token
    
    401 Unauthorized: если refresh-токен отсутствует, невалиден или отозван
    405 Method Not Allowed: если метод не POST
    """
    # Проверяем, что запрос методом POST
    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    # Получаем refresh-токен из cookies
    refresh_token = request.COOKIES.get("refresh_token")

    # Если refresh-токен отсутствует — возвращаем 401
    if not refresh_token:
        return JsonResponse({"error": "refresh token missing"}, status=401)

    try:
        # Вызываем сервис обновления токенов
        # Возвращает: (user, new_access_token, new_refresh_token)
        user, access_token, new_refresh_token = refresh_user_tokens(refresh_token)

        # Создаём ответ с успешным сообщением
        response = JsonResponse({
            "message": "tokens refreshed",
            "email": user.email
        }, status=200)

        # Устанавливаем новый access-токен в cookie
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            samesite="Lax",
            max_age=15 * 60,
        )

        # Устанавливаем новый refresh-токен в cookie
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            samesite="Lax",
            max_age=7 * 24 * 60 * 60,
        )

        return response

    except ValueError as e:
        # Refresh-токен невалиден, истёк или отозван
        return JsonResponse({"error": str(e)}, status=401)


@csrf_exempt
def logout(request):
    """
    Завершение текущей сессии (logout).
    POST /auth/logout
    
    Находит access-токен в БД и помечает его как отозванный (revoked=True).
    Удаляет cookies access_token и refresh_token.
    
    Возвращает:
    200 OK: {"message": "logged out"}
    401 Unauthorized: если access-токен отсутствует
    405 Method Not Allowed: если метод не POST
    """
    # Проверяем, что запрос методом POST
    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    # Получаем access-токен из cookies
    access_token = request.COOKIES.get("access_token")

    # Если токен отсутствует — возвращаем 401
    if not access_token:
        return JsonResponse({"error": "not authenticated"}, status=401)

    # Вызываем сервис завершения сессии (отзыв токена в БД)
    logout_user(access_token)

    # Создаём ответ с успешным сообщением
    response = JsonResponse({
        "message": "logged out"
    })

    # Удаляем cookies (устанавливаем max_age=0)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    return response


@csrf_exempt
def logout_all(request):
    """
    Завершение ВСЕХ сессий пользователя (logout from all devices).
    POST /auth/logout-all
    
    Находит пользователя по access-токену и отзывает ВСЕ его токены
    (и access, и refresh) во всех сессиях.
    
    Возвращает:
    200 OK: {"message": "logged out from all sessions"}
    401 Unauthorized: если access-токен отсутствует
    405 Method Not Allowed: если метод не POST
    """
    # Проверяем, что запрос методом POST
    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    # Получаем access-токен из cookies
    access_token = request.COOKIES.get("access_token")

    # Если токен отсутствует — возвращаем 401
    if not access_token:
        return JsonResponse({"error": "not authenticated"}, status=401)

    try:
        # Вызываем сервис завершения всех сессий
        logout_all_user_sessions(access_token)

        # Создаём ответ с успешным сообщением
        response = JsonResponse({
            "message": "logged out from all sessions"
        }, status=200)

        # Удаляем cookies текущей сессии
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        return response

    except ValueError as e:
        # Ошибка валидации токена
        return JsonResponse({"error": str(e)}, status=401)