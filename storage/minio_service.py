import uuid
from minio import Minio
from minio.error import S3Error
from django.conf import settings

class MinioService:
    def __init__(self):
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL,
        )
        self.bucket = settings.MINIO_BUCKET

    def ensure_bucket_exists(self):
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def upload_file(self, file_obj, original_name: str, content_type: str, user_id: str):
        self.ensure_bucket_exists()

        object_key = f"{user_id}/{uuid.uuid4()}-{original_name}"

        file_size = file_obj.size
        file_obj.seek(0)

        self.client.put_object(
            bucket_name=self.bucket,
            object_name=object_key,
            data=file_obj,
            length=file_size,
            content_type=content_type,
        )

        return {
            "bucket": self.bucket,
            "object_key": object_key,
            "size": file_size,
            "original_name": original_name,
            "mimetype": content_type,
        }

    def get_file_stream(self, object_key: str):
        return self.client.get_object(self.bucket, object_key)

    def delete_file(self, object_key: str):
        self.client.remove_object(self.bucket, object_key)

    def file_exists(self, object_key: str) -> bool:
        try:
            self.client.stat_object(self.bucket, object_key)
            return True
        except S3Error:
            return False

minio_service = MinioService()