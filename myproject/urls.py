from django.urls import include, path

urlpatterns = [
    path('', include('info.urls')),
]