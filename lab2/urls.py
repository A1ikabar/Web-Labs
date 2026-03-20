# lab2/urls.py
# Маршрутизация (URL routing) для CRUD операций с сущностью Work

from django.urls import path  # Функция для определения URL-паттернов
from .views import works_list, work_detail  # View-функции для работы со списком и деталями

# Список URL-паттернов приложения lab2
urlpatterns = [
    # Список работ (GET) и создание новой работы (POST)
    # GET /works?page=1&limit=10
    # POST /works
    path("works", works_list, name="works_list"),
    
    # Детальная операция с работой по ID
    # GET /works/<uuid> — получение работы
    # PUT /works/<uuid> — полное обновление
    # PATCH /works/<uuid> — частичное обновление
    # DELETE /works/<uuid> — мягкое удаление
    # <uuid:work_id> — Django автоматически валидирует UUID формат
    path("works/<uuid:work_id>", work_detail, name="work_detail"),
]
