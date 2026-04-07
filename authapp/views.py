import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view

from authapp.dto import RegisterDTO, LoginDTO
from authapp.auth_service import register_user, login_user, get_current_user_from_access_token, refresh_user_tokens, logout_user, logout_all_user_sessions

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from authapp.serializers import (
    RegisterRequestSerializer,
    RegisterResponseSerializer,
    LoginRequestSerializer,
    LoginResponseSerializer,
    WhoAmIResponseSerializer,
    RefreshResponseSerializer,
    LogoutResponseSerializer,
    LogoutAllResponseSerializer,
    ErrorResponseSerializer,
)

from common.cache_service import cache_service

@extend_schema(
    tags=["Auth"],
    summary="Регистрация пользователя",
    description="Создаёт нового пользователя по email и паролю.",
    request=RegisterRequestSerializer,
    auth=[],
    responses={
        201: RegisterResponseSerializer,
        400: OpenApiResponse(response=ErrorResponseSerializer, description="Ошибка валидации или пользователь уже существует"),
    },
    examples=[
        OpenApiExample(
            "Пример запроса на регистрацию",
            value={
                "email": "user@example.com",
                "password": "strongPassword123",
                "phone": "+79990000000"
            },
            request_only=True,
        ),
        OpenApiExample(
            "Пример успешного ответа",
            value={
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com"
            },
            response_only=True,
            status_codes=["201"],
        ),
        OpenApiExample(
            "Пример ошибки",
            value={"error": "user already exists"},
            response_only=True,
            status_codes=["400"],
        ),
    ],
)
@api_view(["POST"])
@csrf_exempt
def register(request):
    try:
        body = json.loads(request.body)
        dto = RegisterDTO(body)
        user = register_user(dto)

        return JsonResponse({
            "id": str(user["_id"]),
            "email": user["email"],
        }, status=201)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

@extend_schema(
    tags=["Auth"],
    summary="Вход пользователя",
    description="Авторизует пользователя по email и паролю, устанавливает access_token и refresh_token в HttpOnly cookies.",
    request=LoginRequestSerializer,
    auth=[],
    responses={
        200: LoginResponseSerializer,
        400: OpenApiResponse(response=ErrorResponseSerializer, description="Неверные данные для входа"),
        405: OpenApiResponse(response=ErrorResponseSerializer, description="Метод не поддерживается"),
    },
    examples=[
        OpenApiExample(
            "Пример запроса на вход",
            value={
                "email": "user@example.com",
                "password": "strongPassword123"
            },
            request_only=True,
        ),
        OpenApiExample(
            "Пример успешного ответа",
            value={
                "message": "login successful",
                "email": "user@example.com"
            },
            response_only=True,
            status_codes=["200"],
        ),
        OpenApiExample(
            "Пример ошибки",
            value={"error": "invalid credentials"},
            response_only=True,
            status_codes=["400"],
        ),
    ],
)
@api_view(["POST"])
@csrf_exempt
def login(request):

    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    try:
        body = json.loads(request.body)

        dto = LoginDTO(body)

        user, access_token, refresh_token = login_user(
            dto.email,
            dto.password
        )

        response = JsonResponse({
            "message": "login successful",
            "email": user["email"]
        }, status=200)

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            samesite="Lax",
            max_age=15 * 60,
        )

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            samesite="Lax",
            max_age=7 * 24 * 60 * 60,
        )

        return response

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

@extend_schema(
    tags=["Auth"],
    summary="Получить текущего пользователя",
    description="Возвращает информацию о текущем пользователе по access_token.",
    responses={
        200: WhoAmIResponseSerializer,
        401: OpenApiResponse(response=ErrorResponseSerializer, description="Не авторизован"),
    },
)
@api_view(["GET"])
def whoami(request):

    if request.method != "GET":
        return JsonResponse({"error": "method not allowed"}, status=405)

    access_token = request.COOKIES.get("access_token")

    if not access_token:
        return JsonResponse({"error": "unauthorized"}, status=401)

    try:
        user = get_current_user_from_access_token(access_token)

        cache_key = f"wp:users:profile:{str(user['_id'])}"
        cached_data = cache_service.get(cache_key)

        if cached_data is not None:
            return JsonResponse(cached_data, status=200)

        response_data = {
            "id": str(user["_id"]),
            "email": user["email"],
            "phone": user.get("phone"),
        }

        cache_service.set(cache_key, response_data)

        return JsonResponse(response_data, status=200)

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=401)

@extend_schema(
    tags=["Auth"],
    summary="Обновление токенов",
    description="Обновляет access_token и refresh_token.",
    responses={
        200: RefreshResponseSerializer,
        401: OpenApiResponse(response=ErrorResponseSerializer, description="Неверный refresh token"),
    },
)
@api_view(["POST"])
@csrf_exempt
def refresh(request):

    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    refresh_token = request.COOKIES.get("refresh_token")

    if not refresh_token:
        return JsonResponse({"error": "refresh token missing"}, status=401)

    try:
        user, access_token, new_refresh_token = refresh_user_tokens(refresh_token)

        response = JsonResponse({
            "message": "tokens refreshed",
             "email": user["email"]
        }, status=200)

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            samesite="Lax",
            max_age=15 * 60,
        )

        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            samesite="Lax",
            max_age=7 * 24 * 60 * 60,
        )

        return response

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=401)

@extend_schema(
    tags=["Auth"],
    summary="Выход пользователя",
    description="Удаляет текущую сессию пользователя.",
    responses={
        200: LogoutResponseSerializer,
    },
)
@api_view(["POST"])
@csrf_exempt
def logout(request):

    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    access_token = request.COOKIES.get("access_token")

    if not access_token:
        return JsonResponse({"error": "not authenticated"}, status=401)

    logout_user(access_token)

    response = JsonResponse({
        "message": "logged out"
    })

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    return response

@extend_schema(
    tags=["Auth"],
    summary="Выход из всех устройств",
    description="Удаляет все сессии пользователя.",
    responses={
        200: LogoutAllResponseSerializer,
    },
)
@api_view(["POST"])
@csrf_exempt
def logout_all(request):

    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    access_token = request.COOKIES.get("access_token")

    if not access_token:
        return JsonResponse({"error": "not authenticated"}, status=401)

    try:
        logout_all_user_sessions(access_token)

        response = JsonResponse({
            "message": "logged out from all sessions"
        }, status=200)

        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        return response

    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=401)