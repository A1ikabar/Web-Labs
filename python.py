import os
import sys
from datetime import date

from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY="lab1-secret-key",
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=["*"],
        MIDDLEWARE=[],
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
        ],
        DATABASES={},

        USE_TZ=True,
        TIME_ZONE="UTC",
    )

import django
django.setup()

from django.http import JsonResponse
from django.urls import path

def info(request):
    today = date.today()
    next_new_year = date(today.year + 1, 1, 1)
    return JsonResponse({"days_before_new_year": (next_new_year - today).days})

urlpatterns = [
    path("info", info),
]

if __name__ == "__main__":
    from django.core.management import execute_from_command_line
    argv = sys.argv
    if len(argv) == 1:
        argv = [argv[0], "runserver", "0.0.0.0:4200"]
    execute_from_command_line(argv)