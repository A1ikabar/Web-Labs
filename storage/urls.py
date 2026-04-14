from django.urls import path
from storage.views import upload_file, file_detail

urlpatterns = [
    path("files", upload_file, name="upload_file"),
    path("files/<str:file_id>", file_detail, name="file_detail"),
]