from __future__ import annotations

from rq import Queue, Retry

from app.services.redis_client import get_redis_bytes
from app.settings import get_settings


def get_queue() -> Queue:
    settings = get_settings()
    return Queue(
        name=settings.RQ_QUEUE_NAME,
        connection=get_redis_bytes(),
        default_timeout=900,
    )


def default_retry() -> Retry:
    # Max attempts: 4; backoff schedule seconds: 0, 60, 300, 900
    return Retry(max=4, interval=[0, 60, 300, 900])



