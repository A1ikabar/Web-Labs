import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from authapp.auth_service import get_current_user_from_access_token
from common.cache_service import cache_service
from common.mongo import get_users_collection
from storage.mongo_service import find_active_file_by_id

from users.serializers import (
    ProfileResponseSerializer,
    ProfileUpdateRequestSerializer,
    ErrorResponseSerializer,
)

def get_authenticated_user(request):
    access_token = request.COOKIES.get("access_token")

    if not access_token:
        return None

    try:
        return get_current_user_from_access_token(access_token)
    except ValueError:
        return None

def get_user_id(user):
    if not user:
        return None
    return user.get("_id") or user.get("id")

def build_profile_response(user_doc: dict):
    return {
        "id": str(user_doc["_id"]),
        "email": user_doc["email"],
        "phone": user_doc.get("phone"),
        "displayName": user_doc.get("display_name"),
        "bio": user_doc.get("bio"),
        "avatarFileId": user_doc.get("avatar_file_id"),
    }

@extend_schema(
    tags=["Profile"],
    summary="Получение текущего профиля",
    description="Возвращает профиль текущего авторизованного пользователя.",
    responses={
        200: ProfileResponseSerializer,
        401: OpenApiResponse(response=ErrorResponseSerializer, description="Пользователь не авторизован"),
        404: OpenApiResponse(response=ErrorResponseSerializer, description="Пользователь не найден"),
    },
)
@extend_schema(
    tags=["Profile"],
    summary="Обновление текущего профиля",
    description="Обновляет профиль текущего пользователя, включая avatarFileId.",
    request=ProfileUpdateRequestSerializer,
    responses={
        200: ProfileResponseSerializer,
        400: OpenApiResponse(response=ErrorResponseSerializer, description="Некорректные данные"),
        401: OpenApiResponse(response=ErrorResponseSerializer, description="Пользователь не авторизован"),
        403: OpenApiResponse(response=ErrorResponseSerializer, description="Файл не принадлежит пользователю"),
        404: OpenApiResponse(response=ErrorResponseSerializer, description="Пользователь или файл не найден"),
    },
    methods=["POST"],
    examples=[
        OpenApiExample(
            "Пример обновления профиля",
            value={
                "displayName": "Ksenia",
                "bio": "Student backend developer",
                "avatarFileId": "550e8400-e29b-41d4-a716-446655440000"
            },
            request_only=True,
        ),
    ],
)
@api_view(["GET", "POST"])
@csrf_exempt
def profile_view(request):
    user = get_authenticated_user(request)

    if not user:
        return JsonResponse({"error": "unauthorized"}, status=401)

    user_id = get_user_id(user)

    if not user_id:
        return JsonResponse({"error": "user id not found"}, status=500)

    users_collection = get_users_collection()
    cache_key = f"wp:users:profile:{str(user_id)}"

    user_doc = users_collection.find_one({"_id": user_id})

    if user_doc is None:
        return JsonResponse({"error": "user not found"}, status=404)

    if request.method == "GET":
        cached_profile = cache_service.get(cache_key)

        if cached_profile is not None:
            return JsonResponse(cached_profile, status=200)

        response_data = build_profile_response(user_doc)
        cache_service.set(cache_key, response_data)

        return JsonResponse(response_data, status=200)

    if request.method == "POST":
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "invalid json"}, status=400)

        update_data = {}

        if "displayName" in body:
            update_data["display_name"] = body.get("displayName")

        if "bio" in body:
            update_data["bio"] = body.get("bio")

        if "avatarFileId" in body:
            avatar_file_id = body.get("avatarFileId")

            if avatar_file_id:
                file_doc = find_active_file_by_id(avatar_file_id)

                if file_doc is None:
                    return JsonResponse({"error": "file not found"}, status=404)

                if file_doc["user_id"] != str(user_id):
                    return JsonResponse({"error": "forbidden"}, status=403)

                if file_doc["mimetype"] not in ["image/png", "image/jpeg", "image/jpg"]:
                    return JsonResponse({"error": "invalid avatar file type"}, status=400)

                update_data["avatar_file_id"] = avatar_file_id
            else:
                update_data["avatar_file_id"] = None

        if update_data:
            users_collection.update_one(
                {"_id": user_id},
                {"$set": update_data}
            )

        updated_user_doc = users_collection.find_one({"_id": user_id})
        response_data = build_profile_response(updated_user_doc)

        cache_service.delete(cache_key)
        cache_service.set(cache_key, response_data)

        return JsonResponse(response_data, status=200)

    return JsonResponse({"error": "method not allowed"}, status=405)