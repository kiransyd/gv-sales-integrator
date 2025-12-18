from __future__ import annotations

import logging

from rq import Queue, Worker

from app.logging import configure_logging
from app.services.redis_client import get_redis_bytes
from app.settings import get_settings

logger = logging.getLogger(__name__)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)

    # Validate configuration and fail fast if critical errors found
    settings.validate_and_fail_fast()

    redis = get_redis_bytes()
    queue = Queue(name=settings.RQ_QUEUE_NAME, connection=redis)
    worker = Worker([queue], connection=redis)
    logger.info("Starting RQ worker. queue=%s redis=%s", settings.RQ_QUEUE_NAME, settings.REDIS_URL)
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()



