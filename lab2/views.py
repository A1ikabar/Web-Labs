# lab2/views.py
# Контроллеры (views) для CRUD операций с сущностью Work
# Все эндпоинты защищены аутентификацией через JWT access-токен

import json  # Парсинг JSON из тела запроса
from math import ceil  # Округление для пагинации

from django.http import JsonResponse, HttpResponse  # Типы HTTP-ответов
from django.utils import timezone  # Текущее время для soft delete
from django.views.decorators.csrf import csrf_exempt  # Отключение CSRF для API

from authapp.auth_service import get_current_user_from_access_token  # Валидация токена


from .models import Work  # Модель Work


def get_authenticated_user(request):
    """
    Извлечение аутентифицированного пользователя из request.
    Получает access-токен из cookies, валидирует его через сервис аутентификации.
    
    Возвращает:
    - Объект User, если токен валиден
    - None, если токен отсутствует или невалиден
    """
    # Получаем access-токен из HttpOnly cookies
    access_token = request.COOKIES.get("access_token")

    # Если токен отсутствует — пользователь не аутентифицирован
    if not access_token:
        return None

    try:
        # Валидируем токен и получаем пользователя
        return get_current_user_from_access_token(access_token)
    except ValueError:
        # Токен невалиден или истёк
        return None


def work_to_dict(work):
    """
    Преобразование модели Work в словарь для JSON-ответа.
    Фильтрует чувствительные данные (не возвращает owner_id, deleted_at).
    
    Возвращает dict с полями: id, title, description, author_name, created_at, updated_at.
    """
    return {
        "id": str(work.id),  # UUID → строка для JSON
        "title": work.title,
        "description": work.description,
        "author_name": work.author_name,
        "created_at": work.created_at.isoformat() if work.created_at else None,  # datetime → ISO 8601
        "updated_at": work.updated_at.isoformat() if work.updated_at else None,
    }


def get_active_work_or_none(work_id):
    """
    Поиск активной (не удалённой) работы по ID.
    Возвращает объект Work или None, если не найдена/удалена.
    """
    try:
        # Фильтр: deleted_at__isnull=True = только активные записи
        return Work.objects.get(id=work_id, deleted_at__isnull=True)
    except Work.DoesNotExist:
        return None


@csrf_exempt
def works_list(request):
    """
    Контроллер для работы со списком работ.
    
    GET /works?page=1&limit=10
        Возвращает пагинированный список всех активных работ.
    
    POST /works
        Создаёт новую работу (требуется аутентификация).
    
    Доступ: только для аутентифицированных пользователей.
    """
    # Получаем текущего пользователя (проверка аутентификации)
    user = get_authenticated_user(request)

    # Если пользователь не аутентифицирован — возвращаем 401
    if not user:
        return JsonResponse({"error": "unauthorized"}, status=401)

    # Обработка GET-запроса (список работ с пагинацией)
    if request.method == "GET":
        # Получаем параметры пагинации из query string
        page = request.GET.get("page", "1")  # Номер страницы (по умолчанию 1)
        limit = request.GET.get("limit", "10")  # Количество на странице (по умолчанию 10)

        try:
            # Преобразуем в целые числа
            page = int(page)
            limit = int(limit)

            # Валидация: страница >= 1, лимит от 1 до 100
            if page < 1 or limit < 1 or limit > 100:
                return JsonResponse({"error": "Invalid pagination"}, status=400)

        except ValueError:
            # Если не удалось преобразовать в число
            return JsonResponse({"error": "Pagination must be numbers"}, status=400)

        # Получаем queryset всех активных работ, сортируем по дате создания
        queryset = Work.objects.filter(deleted_at__isnull=True).order_by("created_at")
        # Общее количество записей
        total = queryset.count()
        # Общее количество страниц (округляем вверх)
        total_pages = ceil(total / limit) if total > 0 else 1
        # Вычисляем смещение (offset) для пагинации
        offset = (page - 1) * limit
        # Получаем срез записей для текущей страницы
        works = queryset[offset:offset + limit]

        # Возвращаем JSON с данными и мета-информацией
        return JsonResponse({
            "data": [work_to_dict(work) for work in works],
            "meta": {
                "total": total,  # Всего записей
                "page": page,  # Текущая страница
                "limit": limit,  # Записей на странице
                "totalPages": total_pages  # Всего страниц
            }
        }, status=200)

    # Обработка POST-запроса (создание работы)
    if request.method == "POST":
        # Парсим JSON из тела запроса
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        # Извлекаем поля из запроса
        title = body.get("title")
        description = body.get("description")
        author_name = body.get("author_name")

        # Валидация: все три поля обязательны
        if not title or not description or not author_name:
            return JsonResponse(
                {"error": "title, description and author_name are required"},
                status=400
            )

        # Создаём новую запись в БД с текущим пользователем в качестве владельца
        work = Work.objects.create(
            title=title,
            description=description,
            author_name=author_name,
            owner=user
        )

        # Возвращаем созданную работу в формате JSON
        return JsonResponse(work_to_dict(work), status=201)

    # Метод не разрешён
    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def work_detail(request, work_id):
    """
    Контроллер для операций с конкретной работой.
    
    GET /works/<uuid>
        Возвращает работу по ID.
    
    PUT /works/<uuid>
        Полное обновление работы (требуется владение).
    
    PATCH /works/<uuid>
        Частичное обновление работы (требуется владение).
    
    DELETE /works/<uuid>
        Мягкое удаление работы (требуется владение).
    
    Доступ: только для аутентифицированных пользователей.
    Редактирование/удаление: только владелец.
    """
    # Находим работу (или None, если не найдена/удалена)
    work = get_active_work_or_none(work_id)

    # Получаем текущего пользователя
    user = get_authenticated_user(request)

    # Если пользователь не аутентифицирован — возвращаем 401
    if not user:
        return JsonResponse({"error": "unauthorized"}, status=401)

    # Если работа не найдена — возвращаем 404
    if work is None:
        return JsonResponse({"error": "Work not found"}, status=404)

    # Обработка GET-запроса (получение работы)
    if request.method == "GET":
        return JsonResponse(work_to_dict(work), status=200)

    # Обработка PUT-запроса (полное обновление)
    if request.method == "PUT":
        # Проверяем владение: только владелец может редактировать
        if work.owner_id != user.id:
            return JsonResponse({"error": "forbidden"}, status=403)

        # Парсим JSON из тела запроса
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        # Извлекаем поля
        title = body.get("title")
        description = body.get("description")
        author_name = body.get("author_name")

        # Валидация: все поля обязательны
        if not title or not description or not author_name:
            return JsonResponse(
                {"error": "title, description and author_name are required"},
                status=400
            )

        # Обновляем поля
        work.title = title
        work.description = description
        work.author_name = author_name
        work.save()

        # Возвращаем обновлённую работу
        return JsonResponse(work_to_dict(work), status=200)

    # Обработка PATCH-запроса (частичное обновление)
    if request.method == "PATCH":
        # Проверяем владение
        if work.owner_id != user.id:
            return JsonResponse({"error": "forbidden"}, status=403)

        # Парсим JSON
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        # Обновляем только указанные поля
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

        # Сохраняем изменения
        work.save()
        return JsonResponse(work_to_dict(work), status=200)

    # Обработка DELETE-запроса (мягкое удаление)
    if request.method == "DELETE":
        # Проверяем владение
        if work.owner_id != user.id:
            return JsonResponse({"error": "forbidden"}, status=403)
        
        # Устанавливаем deleted_at = текущее время (soft delete)
        work.deleted_at = timezone.now()
        work.save()
        
        # Возвращаем 204 No Content (успешное удаление без тела ответа)
        return HttpResponse(status=204)

    # Метод не разрешён
    return JsonResponse({"error": "Method not allowed"}, status=405)