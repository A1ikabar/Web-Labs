from django.db import models
import uuid
from users.models import User

class Work(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # Уникальный идентификатор произведения
    title = models.CharField(max_length=255)  # Название работы
    description = models.TextField()  # Описание или аннотация
    author_name = models.CharField(max_length=255)  # Имя автора
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='works', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)  # Дата создания
    updated_at = models.DateTimeField(auto_now=True)  # Дата последнего обновления
    deleted_at = models.DateTimeField(null=True, blank=True)  # Дата мягкого удаления

    def __str__(self):
        return self.title