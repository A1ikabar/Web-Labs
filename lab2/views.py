import json
from math import ceil

from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample, OpenApiParameter
from lab2.serializers import (
    WorkSerializer,
    WorkCreateRequestSerializer,
    WorkUpdateRequestSerializer,
    WorkPatchRequestSerializer,
    WorkListResponseSerializer,
    ErrorResponseSerializer,
)

from authapp.auth_service import get_current_user_from_access_token

from .models import Work

def get_authenticated_user(request):
    access_token = request.COOKIES.get("access_token")

    if not access_token:
        return None

    try:
        return get_current_user_from_access_token(access_token)
    except ValueError:
        return None

def work_to_dict(work):
    return {
        "id": str(work.id),
        "title": work.title,
        "description": work.description,
        "author_name": work.author_name,
        "created_at": work.created_at.isoformat() if work.created_at else None,
        "updated_at": work.updated_at.isoformat() if work.updated_at else None,
    }

def get_active_work_or_none(work_id):
    try:
        return Work.objects.get(id=work_id, deleted_at__isnull=True)
    except Work.DoesNotExist:
        return None

@extend_schema(
    tags=["Works"],
    summary="Список работ и создание работы",
    description="GET возвращает список работ с пагинацией. POST создаёт новую работу. Требуется авторизация.",
    parameters=[
        OpenApiParameter(name="page", type=int, location=OpenApiParameter.QUERY, description="Номер страницы"),
        OpenApiParameter(name="limit", type=int, location=OpenApiParameter.QUERY, description="Количество элементов на странице"),
    ],
    request=WorkCreateRequestSerializer,
    responses={
        200: WorkListResponseSerializer,
        201: WorkSerializer,
        400: OpenApiResponse(response=ErrorResponseSerializer, description="Неверный JSON или некорректная пагинация"),
        401: OpenApiResponse(response=ErrorResponseSerializer, description="Пользователь не авторизован"),
        405: OpenApiResponse(response=ErrorResponseSerializer, description="Метод не поддерживается"),
    },
    examples=[
        OpenApiExample(
            "Пример создания работы",
            value={
                "title": "Мастер и Маргарита",
                "description": "Роман о добре и зле",
                "author_name": "Михаил Булгаков"
            },
            request_only=True,
        ),
        OpenApiExample(
            "Пример успешного создания",
            value={
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Мастер и Маргарита",
                "description": "Роман о добре и зле",
                "author_name": "Михаил Булгаков",
                "created_at": "2026-03-18T11:30:00Z",
                "updated_at": "2026-03-18T11:30:00Z"
            },
            response_only=True,
            status_codes=["201"],
        ),
        OpenApiExample(
            "Пример списка работ",
            value={
                "data": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "title": "Мастер и Маргарита",
                        "description": "Роман о добре и зле",
                        "author_name": "Михаил Булгаков",
                        "created_at": "2026-03-18T11:30:00Z",
                        "updated_at": "2026-03-18T11:30:00Z"
                    }
                ],
                "meta": {
                    "total": 1,
                    "page": 1,
                    "limit": 10,
                    "totalPages": 1
                }
            },
            response_only=True,
            status_codes=["200"],
        ),
        OpenApiExample(
            "Ошибка авторизации",
            value={"error": "unauthorized"},
            response_only=True,
            status_codes=["401"],
        ),
    ],
)
@api_view(["GET", "POST"])
@csrf_exempt
def works_list(request):
    user = get_authenticated_user(request)

    if not user:
        return JsonResponse({"error": "unauthorized"}, status=401)

    if request.method == "GET":
        page = request.GET.get("page", "1")
        limit = request.GET.get("limit", "10")

        try:
            page = int(page)
            limit = int(limit)

            if page < 1 or limit < 1 or limit > 100:
                return JsonResponse({"error": "Invalid pagination"}, status=400)

        except ValueError:
            return JsonResponse({"error": "Pagination must be numbers"}, status=400)

        queryset = Work.objects.filter(deleted_at__isnull=True).order_by("created_at")
        total = queryset.count()
        total_pages = ceil(total / limit) if total > 0 else 1
        offset = (page - 1) * limit
        works = queryset[offset:offset + limit]

        return JsonResponse({
            "data": [work_to_dict(work) for work in works],
            "meta": {
                "total": total,
                "page": page,
                "limit": limit,
                "totalPages": total_pages
            }
        }, status=200)

    if request.method == "POST":
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        title = body.get("title")
        description = body.get("description")
        author_name = body.get("author_name")

        if not title or not description or not author_name:
            return JsonResponse(
                {"error": "title, description and author_name are required"},
                status=400
            )

        work = Work.objects.create(
            title=title,
            description=description,
            author_name=author_name,
            owner=user
        )

        return JsonResponse(work_to_dict(work), status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)

@extend_schema(
    tags=["Works"],
    summary="Работа по ID",
    description="Получение, обновление, частичное обновление и удаление работы по UUID. Требуется авторизация.",
    request=WorkUpdateRequestSerializer,
    responses={
        200: WorkSerializer,
        204: OpenApiResponse(description="Работа успешно удалена"),
        400: OpenApiResponse(response=ErrorResponseSerializer, description="Неверный JSON или некорректные данные"),
        401: OpenApiResponse(response=ErrorResponseSerializer, description="Пользователь не авторизован"),
        403: OpenApiResponse(response=ErrorResponseSerializer, description="Нет прав на изменение или удаление"),
        404: OpenApiResponse(response=ErrorResponseSerializer, description="Работа не найдена"),
        405: OpenApiResponse(response=ErrorResponseSerializer, description="Метод не поддерживается"),
    },
    examples=[
        OpenApiExample(
            "Пример успешного ответа",
            value={
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Мастер и Маргарита",
                "description": "Роман о добре и зле",
                "author_name": "Михаил Булгаков",
                "created_at": "2026-03-18T11:30:00Z",
                "updated_at": "2026-03-18T11:30:00Z"
            },
            response_only=True,
            status_codes=["200"],
        ),
        OpenApiExample(
            "Пример ошибки доступа",
            value={"error": "forbidden"},
            response_only=True,
            status_codes=["403"],
        ),
        OpenApiExample(
            "Пример ошибки не найдено",
            value={"error": "Work not found"},
            response_only=True,
            status_codes=["404"],
        ),
    ],
)
@api_view(["GET", "PUT", "PATCH", "DELETE"])
@csrf_exempt
def work_detail(request, work_id):
    work = get_active_work_or_none(work_id)

    user = get_authenticated_user(request)

    if not user:
        return JsonResponse({"error": "unauthorized"}, status=401)

    if work is None:
        return JsonResponse({"error": "Work not found"}, status=404)

    if request.method == "GET":
        return JsonResponse(work_to_dict(work), status=200)

    if request.method == "PUT":

        if work.owner_id != user.id:
            return JsonResponse({"error": "forbidden"}, status=403)

        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        title = body.get("title")
        description = body.get("description")
        author_name = body.get("author_name")

        if not title or not description or not author_name:
            return JsonResponse(
                {"error": "title, description and author_name are required"},
                status=400
            )

        work.title = title
        work.description = description
        work.author_name = author_name
        work.save()

        return JsonResponse(work_to_dict(work), status=200)

    if request.method == "PATCH":

        if work.owner_id != user.id:
            return JsonResponse({"error": "forbidden"}, status=403)

        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        if "title" in body:
            if not body["title"]:
                return JsonResponse({"error": "title cannot be empty"}, status=400)
            work.title = body["title"]

        if "description" in body:
            if not body["description"]:
                return JsonResponse({"error": "description cannot be empty"}, status=400)
            work.description = body["description"]

        if "author_name" in body:
            if not body["author_name"]:
                return JsonResponse({"error": "author_name cannot be empty"}, status=400)
            work.author_name = body["author_name"]

        work.save()
        return JsonResponse(work_to_dict(work), status=200)

    if request.method == "DELETE":
        if work.owner_id != user.id:
            return JsonResponse({"error": "forbidden"}, status=403)
        work.deleted_at = timezone.now()
        work.save()
        return HttpResponse(status=204)

    return JsonResponse({"error": "Method not allowed"}, status=405)