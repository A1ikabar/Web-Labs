import pika

import os
import redis

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from common.cache_service import cache_service
from common.mongo import get_mongo_client
from storage.minio_service import minio_service

def dependency_result(ok: bool, error: str = None):
    result = {"ok": ok}

    if error:
        result["error"] = error

    return result

def check_mongo():
    try:
        client = get_mongo_client()
        client.admin.command("ping")
        return dependency_result(True)
    except Exception as e:
        return dependency_result(False, str(e))

def check_redis():
    try:
        if cache_service.client is None:
            cache_service.client = redis.Redis(
                host=os.getenv("REDIS_HOST", "redis"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                password=os.getenv("REDIS_PASSWORD") or None,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )

        cache_service.client.ping()
        return dependency_result(True)

    except Exception as e:
        return dependency_result(False, str(e))

def check_rabbitmq():
    connection = None

    try:
        credentials = pika.PlainCredentials(
            settings.RABBITMQ_USER,
            settings.RABBITMQ_PASS,
        )

        parameters = pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            credentials=credentials,
            heartbeat=30,
            blocked_connection_timeout=5,
            socket_timeout=5,
        )

        connection = pika.BlockingConnection(parameters)
        return dependency_result(True)

    except Exception as e:
        return dependency_result(False, str(e))

    finally:
        if connection and not connection.is_closed:
            connection.close()

def check_minio():
    try:
        minio_service.client.list_buckets()
        return dependency_result(True)
    except Exception as e:
        return dependency_result(False, str(e))

@require_GET
def health(request):
    return JsonResponse(
        {
            "status": "ok",
            "service": "wp-labs-api",
        },
        status=200,
    )

@require_GET
def health_live(request):
    return JsonResponse(
        {
            "status": "alive",
        },
        status=200,
    )

@require_GET
def health_ready(request):
    dependencies = {
        "mongo": check_mongo(),
        "redis": check_redis(),
        "rabbitmq": check_rabbitmq(),
        "minio": check_minio(),
    }

    is_ready = all(item["ok"] for item in dependencies.values())

    return JsonResponse(
        {
            "status": "ready" if is_ready else "not_ready",
            "dependencies": dependencies,
        },
        status=200 if is_ready else 503,
    )