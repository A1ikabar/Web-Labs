# lab2/models.py
# Модели данных для сущности Work (произведение/работа)

from django.db import models  # ORM Django
import uuid  # Генерация UUID для первичных ключей
from users.models import User  # Модель пользователя (владелец работы)


class Work(models.Model):
    """
    Модель произведения (Work).
    Представляет сущность предметной области (книга, статья, работа и т.д.).
    
    Особенности:
    - UUID в качестве первичного ключа (безопасность)
    - Владелец (owner) — связь с пользователем
    - Soft Delete (мягкое удаление через deleted_at)
    - Проверка владельца при редактировании/удалении
    
    Поля:
    - id: UUID первичный ключ
    - title: название работы
    - description: описание/аннотация
    - author_name: имя автора (текстовое поле)
    - owner: внешний ключ на пользователя (создателя)
    - created_at: дата создания
    - updated_at: дата обновления
    - deleted_at: дата мягкого удаления
    """
    # Первичный ключ: UUID (генерируется автоматически, не редактируется)
    # editable=False — поле нельзя изменить через формы
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Название работы (максимум 255 символов)
    title = models.CharField(max_length=255)
    
    # Описание или аннотация (текст произвольной длины)
    description = models.TextField()
    
    # Имя автора (строка, не связана с моделью User)
    author_name = models.CharField(max_length=255)
    
    # Владелец работы (пользователь, создавший запись)
    # on_delete=models.CASCADE — при удалении пользователя работы удаляются
    # null=True, blank=True — разрешаем создание без владельца (для старых записей)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='works', null=True, blank=True)

    # Дата создания (auto_now_add=True — устанавливается только при создании)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Дата обновления (auto_now=True — обновляется при каждом save)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Дата мягкого удаления (null = запись активна)
    # При удалении устанавливается в текущее время, запись скрывается из выборок
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        # Строковое представление (отображается в админке и отладке)
        return self.title