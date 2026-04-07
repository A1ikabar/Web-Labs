from rest_framework import serializers

class WorkSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField(help_text="Название работы")
    description = serializers.CharField(help_text="Описание работы")
    author_name = serializers.CharField(help_text="Имя автора")
    created_at = serializers.DateTimeField(help_text="Дата создания")
    updated_at = serializers.DateTimeField(help_text="Дата обновления")

class WorkCreateRequestSerializer(serializers.Serializer):
    title = serializers.CharField(help_text="Название работы", default="Мастер и Маргарита")
    description = serializers.CharField(help_text="Описание работы", default="Роман о добре и зле")
    author_name = serializers.CharField(help_text="Имя автора", default="Михаил Булгаков")

class WorkUpdateRequestSerializer(serializers.Serializer):
    title = serializers.CharField(help_text="Название работы", default="Обновлённое название")
    description = serializers.CharField(help_text="Описание работы", default="Обновлённое описание")
    author_name = serializers.CharField(help_text="Имя автора", default="Обновлённый автор")

class WorkPatchRequestSerializer(serializers.Serializer):
    title = serializers.CharField(help_text="Название работы", required=False, default="Новое название")
    description = serializers.CharField(help_text="Описание работы", required=False, default="Новое описание")
    author_name = serializers.CharField(help_text="Имя автора", required=False, default="Новый автор")

class PaginationMetaSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    page = serializers.IntegerField()
    limit = serializers.IntegerField()
    totalPages = serializers.IntegerField()

class WorkListResponseSerializer(serializers.Serializer):
    data = WorkSerializer(many=True)
    meta = PaginationMetaSerializer()

class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField(default="unauthorized")