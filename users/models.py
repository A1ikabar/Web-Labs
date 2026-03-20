# users/models.py
# Модели данных для пользователей и токенов

import uuid  # Генерация UUID для первичных ключей
from django.db import models  # ORM Django


class User(models.Model):
    """
    Модель пользователя.
    Расширенная версия с поддержкой:
    - UUID в качестве первичного ключа (безопасность, не последовательный ID)
    - Хешированных паролей с солью (bcrypt)
    - OAuth-идентификаторов (Яндекс, VK)
    - Soft Delete (мягкое удаление через deleted_at)
    
    Поля:
    - id: UUID, первичный ключ
    - email: уникальный email для входа
    - phone: опционально номер телефона
    - password_hash: хеш пароля (bcrypt)
    - password_salt: соль для пароля
    - yandex_id: ID пользователя в Яндекс OAuth
    - vk_id: ID пользователя в VK OAuth
    - created_at: дата создания записи
    - updated_at: дата последнего обновления
    - deleted_at: дата мягкого удаления (null = активен)
    """
    # Первичный ключ: UUID (генерируется автоматически, не редактируется)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Уникальный email для аутентификации
    email = models.EmailField(unique=True)
    
    # Опциональный номер телефона (может быть null или пустым)
    phone = models.CharField(max_length=20, null=True, blank=True)

    # Хеш пароля (результат bcrypt.hashpw, хранится с солью в формате $2b$...)
    password_hash = models.CharField(max_length=255)
    
    # Соль для пароля (используется при верификации)
    password_salt = models.CharField(max_length=255)

    # OAuth-идентификаторы (null, пока пользователь не привязал OAuth)
    yandex_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    vk_id = models.CharField(max_length=255, null=True, blank=True, unique=True)

    # Автоматические временные метки
    created_at = models.DateTimeField(auto_now_add=True)  # Дата создания (только при создании)
    updated_at = models.DateTimeField(auto_now=True)  # Дата обновления (при каждом save)
    deleted_at = models.DateTimeField(null=True, blank=True)  # Soft Delete: null = активен

    def __str__(self):
        # Строковое представление (отображается в админке Django)
        return self.email


class UserToken(models.Model):
    """
    Модель для хранения JWT-токенов в БД.
    Используется для управления сессиями и отзыва токенов.
    
    Зачем хранить токены в БД:
    - Возможность отзыва (logout, logout-all)
    - Проверка актуальности токена при каждом запросе
    - Безопасность: храним хеш токена, а не сам токен
    
    Поля:
    - id: UUID первичный ключ
    - user: связь с пользователем (один ко многим)
    - token_hash: хеш токена (SHA256 с солью)
    - token_salt: соль для хеширования токена
    - token_type: 'access' или 'refresh'
    - expires_at: время истечения токена
    - revoked: флаг отзыва токена
    - created_at: дата создания записи
    """
    # Первичный ключ: UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Внешний ключ на пользователя (CASCADE: при удалении пользователя токены удаляются)
    # related_name='tokens' позволяет обращаться: user.tokens.all()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tokens')

    # Хеш токена (не сам токен! вычисляется как SHA256(token + salt))
    token_hash = models.CharField(max_length=255)
    
    # Соль для хеширования токена (уникальна для каждого токена)
    token_salt = models.CharField(max_length=255)

    # Тип токена: 'access' (15 мин) или 'refresh' (7 дней)
    token_type = models.CharField(max_length=20)

    # Время истечения токена (сравнивается с timezone.now())
    expires_at = models.DateTimeField()
    
    # Флаг отзыва: True = токен недействителен (logout)
    revoked = models.BooleanField(default=False)

    # Дата создания записи в БД
    created_at = models.DateTimeField(auto_now_add=True)