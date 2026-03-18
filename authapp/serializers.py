from rest_framework import serializers

class RegisterRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(help_text="Email пользователя", default="user@example.com")
    password = serializers.CharField(help_text="Пароль пользователя", default="strongPassword123")
    phone = serializers.CharField(help_text="Телефон пользователя", default="+79990000000", required=False)

class RegisterResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="UUID пользователя")
    email = serializers.EmailField(help_text="Email зарегистрированного пользователя")

class LoginRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(help_text="Email пользователя", default="user@example.com")
    password = serializers.CharField(help_text="Пароль пользователя", default="strongPassword123")

class LoginResponseSerializer(serializers.Serializer):
    message = serializers.CharField(default="login successful")
    email = serializers.EmailField(default="user@example.com")

class WhoAmIResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="UUID пользователя")
    email = serializers.EmailField(help_text="Email текущего пользователя")
    phone = serializers.CharField(help_text="Телефон текущего пользователя", allow_blank=True, required=False)

class RefreshResponseSerializer(serializers.Serializer):
    message = serializers.CharField(default="tokens refreshed")
    email = serializers.EmailField(default="user@example.com")

class LogoutResponseSerializer(serializers.Serializer):
    message = serializers.CharField(default="logged out")

class LogoutAllResponseSerializer(serializers.Serializer):
    message = serializers.CharField(default="logged out from all sessions")

class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField(default="unauthorized")