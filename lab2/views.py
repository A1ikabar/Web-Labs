import json
from math import ceil

from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import Work

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

@csrf_exempt
def works_list(request):
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
            author_name=author_name
        )

        return JsonResponse(work_to_dict(work), status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
def work_detail(request, work_id):
    work = get_active_work_or_none(work_id)

    if work is None:
        return JsonResponse({"error": "Work not found"}, status=404)

    if request.method == "GET":
        return JsonResponse(work_to_dict(work), status=200)

    if request.method == "PUT":
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
        work.deleted_at = timezone.now()
        work.save()
        return HttpResponse(status=204)

    return JsonResponse({"error": "Method not allowed"}, status=405)