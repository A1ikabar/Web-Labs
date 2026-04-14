from rest_framework import serializers

class ProfileResponseSerializer(serializers.Serializer):
    id = serializers.CharField()
    email = serializers.EmailField()
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    displayName = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    bio = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    avatarFileId = serializers.CharField(required=False, allow_blank=True, allow_null=True)

class ProfileUpdateRequestSerializer(serializers.Serializer):
    displayName = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    bio = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    avatarFileId = serializers.CharField(required=False, allow_blank=True, allow_null=True)

class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField(default="unauthorized")