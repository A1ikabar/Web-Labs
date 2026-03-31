import json
import logging

import redis
from django.conf import settings

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        self.client = None
        try:
            self.client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
            )
            self.client.ping()
        except Exception as e:
            logger.warning(f"Redis unavailable: {e}")
            self.client = None

    def get(self, key: str):
        if not self.client:
            return None

        try:
            value = self.client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            logger.warning(f"Redis GET failed for key={key}: {e}")
            return None

    def set(self, key: str, value, ttl: int = None):
        if not self.client:
            return

        try:
            ttl = ttl or settings.CACHE_TTL_DEFAULT
            self.client.set(key, json.dumps(value), ex=ttl)
        except Exception as e:
            logger.warning(f"Redis SET failed for key={key}: {e}")

    def delete(self, key: str):
        if not self.client:
            return

        try:
            self.client.delete(key)
        except Exception as e:
            logger.warning(f"Redis DELETE failed for key={key}: {e}")

    def delete_by_pattern(self, pattern: str):
        if not self.client:
            return

        try:
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
        except Exception as e:
            logger.warning(f"Redis delete_by_pattern failed for pattern={pattern}: {e}")

cache_service = CacheService()