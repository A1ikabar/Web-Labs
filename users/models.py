import uuid
from django.db import models

class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, null=True, blank=True)

    password_hash = models.CharField(max_length=255)
    password_salt = models.CharField(max_length=255)

    yandex_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    vk_id = models.CharField(max_length=255, null=True, blank=True, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.email

class UserToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tokens')

    token_hash = models.CharField(max_length=255)
    token_salt = models.CharField(max_length=255)

    token_type = models.CharField(max_length=20)  # access или refresh

    expires_at = models.DateTimeField()
    revoked = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)