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

    def acquire_lock(self, key: str, value: str, ttl: int = 30):
        if not self.client:
            return None

        try:
            return bool(
                self.client.set(
                    key,
                    value,
                    ex=ttl,
                    nx=True,
                )
            )
        except Exception as e:
            logger.warning(f"Redis acquire_lock failed for key={key}: {e}")
            return None

    def release_lock(self, key: str, value: str):
        if not self.client:
            return None

        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        try:
            return self.client.eval(script, 1, key, value) == 1
        except Exception as e:
            logger.warning(f"Redis release_lock failed for key={key}: {e}")
            return None

cache_service = CacheService()