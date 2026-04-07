from django.urls import path
from .views import works_list, work_detail

urlpatterns = [
    path("works", works_list, name="works_list"),
    path("works/<str:work_id>", work_detail, name="work_detail"),
]
