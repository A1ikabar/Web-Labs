from django.conf import settings
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import serializers

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiExample,
    inline_serializer,
)

from authapp.auth_service import get_current_user_from_access_token
from common.cache_service import cache_service
from storage.minio_service import minio_service
from storage.mongo_service import (
    create_file_metadata,
    find_active_file_by_id,
    find_active_file_by_id_for_user,
    soft_delete_file,
)
from storage.serializers import (
    FileUploadResponseSerializer,
    FileMetadataResponseSerializer,
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

def file_doc_to_response(file_doc: dict):
    return {
        "fileId": file_doc["_id"],
        "originalName": file_doc["original_name"],
        "size": file_doc["size"],
        "mimetype": file_doc["mimetype"],
        "createdAt": file_doc["created_at"].isoformat() if hasattr(file_doc["created_at"], "isoformat") else file_doc["created_at"],
    }

@extend_schema(
    tags=["Files"],
    summary="Загрузка файла",
    description="Загружает новый файл в MinIO и сохраняет метаданные в MongoDB.",
    request=inline_serializer(
        name="FileUploadRequest",
        fields={
            "file": serializers.FileField()
        }
    ),
    responses={
        201: FileUploadResponseSerializer,
        400: OpenApiResponse(response=ErrorResponseSerializer, description="Некорректный файл"),
        401: OpenApiResponse(response=ErrorResponseSerializer, description="Пользователь не авторизован"),
        500: OpenApiResponse(response=ErrorResponseSerializer, description="Внутренняя ошибка сервера"),
    },
    examples=[
        OpenApiExample(
            "Пример успешного ответа",
            value={
                "fileId": "550e8400-e29b-41d4-a716-446655440000",
                "originalName": "avatar.png",
                "size": 123456,
                "mimetype": "image/png",
                "createdAt": "2026-04-14T12:00:00Z"
            },
            response_only=True,
            status_codes=["201"],
        ),
    ],
)
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@csrf_exempt
def upload_file(request):
    user = get_authenticated_user(request)

    if not user:
        return JsonResponse({"error": "unauthorized"}, status=401)

    uploaded_file = request.FILES.get("file")

    if not uploaded_file:
        return JsonResponse({"error": "file is required"}, status=400)

    if uploaded_file.size > settings.MAX_FILE_SIZE:
        return JsonResponse({"error": "file is too large"}, status=400)

    try:
        user_id = get_user_id(user)

        if not user_id:
            return JsonResponse({"error": "user id not found"}, status=500)

        file_data = minio_service.upload_file(
            file_obj=uploaded_file,
            original_name=uploaded_file.name,
            content_type=uploaded_file.content_type,
            user_id=str(user_id),
        )

        saved_file = create_file_metadata(
            user_id=str(user_id),
            original_name=file_data["original_name"],
            object_key=file_data["object_key"],
            size=file_data["size"],
            mimetype=file_data["mimetype"],
            bucket=file_data["bucket"],
        )

        return JsonResponse(file_doc_to_response(saved_file), status=201)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@extend_schema(
    tags=["Files"],
    summary="Получение файла по ID",
    description="Скачивает файл по ID. Доступ только у владельца.",
    responses={
        200: OpenApiResponse(description="Файл успешно скачан"),
        401: OpenApiResponse(response=ErrorResponseSerializer, description="Пользователь не авторизован"),
        403: OpenApiResponse(response=ErrorResponseSerializer, description="Нет доступа к файлу"),
        404: OpenApiResponse(response=ErrorResponseSerializer, description="Файл не найден"),
    },
)
@extend_schema(
    tags=["Files"],
    summary="Удаление файла по ID",
    description="Мягко удаляет запись о файле и удаляет объект из MinIO. Доступ только у владельца.",
    responses={
        204: OpenApiResponse(description="Файл успешно удалён"),
        401: OpenApiResponse(response=ErrorResponseSerializer, description="Пользователь не авторизован"),
        403: OpenApiResponse(response=ErrorResponseSerializer, description="Нет доступа к файлу"),
        404: OpenApiResponse(response=ErrorResponseSerializer, description="Файл не найден"),
    },
    methods=["DELETE"],
)
@api_view(["GET", "DELETE"])
@csrf_exempt
def file_detail(request, file_id):
    user = get_authenticated_user(request)

    if not user:
        return JsonResponse({"error": "unauthorized"}, status=401)

    user_id = get_user_id(user)

    if not user_id:
        return JsonResponse({"error": "user id not found"}, status=500)

    cache_key = f"wp:files:{file_id}:meta"

    if request.method == "GET":
        cached_file = cache_service.get(cache_key)

        if cached_file is not None:
            file_doc = cached_file
        else:
            file_doc = find_active_file_by_id(file_id)

            if file_doc is None:
                return JsonResponse({"error": "file not found"}, status=404)

            cache_service.set(cache_key, {
                "_id": file_doc["_id"],
                "user_id": file_doc["user_id"],
                "original_name": file_doc["original_name"],
                "object_key": file_doc["object_key"],
                "size": file_doc["size"],
                "mimetype": file_doc["mimetype"],
                "bucket": file_doc["bucket"],
                "created_at": file_doc["created_at"].isoformat() if hasattr(file_doc["created_at"], "isoformat") else file_doc["created_at"],
            })

        if file_doc["user_id"] != str(user_id):
            return JsonResponse({"error": "forbidden"}, status=403)

        try:
            file_stream = minio_service.get_file_stream(file_doc["object_key"])

            response = StreamingHttpResponse(
                streaming_content=file_stream.stream(32 * 1024),
                content_type=file_doc["mimetype"],
                status=200,
            )
            response["Content-Disposition"] = f'attachment; filename="{file_doc["original_name"]}"'
            response["Content-Length"] = str(file_doc["size"])

            return response

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    if request.method == "DELETE":
        file_doc = find_active_file_by_id(file_id)

        if file_doc is None:
            return JsonResponse({"error": "file not found"}, status=404)

        if file_doc["user_id"] != str(user_id):
            return JsonResponse({"error": "forbidden"}, status=403)

        try:
            soft_delete_file(file_id)
            minio_service.delete_file(file_doc["object_key"])
            cache_service.delete(cache_key)
            return HttpResponse(status=204)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "method not allowed"}, status=405)