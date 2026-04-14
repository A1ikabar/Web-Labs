from rest_framework import serializers

class FileUploadResponseSerializer(serializers.Serializer):
    fileId = serializers.CharField()
    originalName = serializers.CharField()
    size = serializers.IntegerField()
    mimetype = serializers.CharField()
    createdAt = serializers.DateTimeField()

class FileMetadataResponseSerializer(serializers.Serializer):
    fileId = serializers.CharField()
    originalName = serializers.CharField()
    size = serializers.IntegerField()
    mimetype = serializers.CharField()
    createdAt = serializers.DateTimeField()

class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField(default="unauthorized")