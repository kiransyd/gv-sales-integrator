from __future__ import annotations

from redis import Redis

from app.settings import get_settings


_redis_str: Redis | None = None
_redis_bytes: Redis | None = None


def get_redis_str() -> Redis:
    """
    Redis client that decodes responses to Python strings.
    Use for our own keys (event store, idempotency markers).
    """
    global _redis_str
    if _redis_str is None:
        settings = get_settings()
        _redis_str = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_str


def get_redis_bytes() -> Redis:
    """
    Redis client that returns raw bytes.
    Required for RQ, which stores pickled binary blobs in Redis.
    """
    global _redis_bytes
    if _redis_bytes is None:
        settings = get_settings()
        _redis_bytes = Redis.from_url(settings.REDIS_URL, decode_responses=False)
    return _redis_bytes



