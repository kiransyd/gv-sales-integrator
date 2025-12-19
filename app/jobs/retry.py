from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional, TypeVar

import httpx
from rq import get_current_job

from app.services.event_store_service import increment_attempts, load_event, set_event_status
from app.services.idempotency_service import is_processed, mark_processed
from app.services.slack_service import send_slack_alert
from app.services.ingest_helpers import best_effort_extract_email
from app.services.llm_service import LLMTransientError
from app.services.zoho_service import ZohoTransientError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class TransientJobError(Exception):
    """An error that should be retried with backoff."""


class PermanentJobError(Exception):
    """An error that should not be retried."""


@dataclass(frozen=True)
class JobContext:
    event_id: str
    idempotency_key: str
    source: str
    event_type: str
    external_id: str
    lead_email: str


def _is_transient_exc(exc: BaseException) -> bool:
    if isinstance(exc, TransientJobError):
        return True
    if isinstance(exc, PermanentJobError):
        return False
    if isinstance(exc, LLMTransientError):
        return True
    if isinstance(exc, ZohoTransientError):
        return True
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code == 429 or 500 <= code <= 599
    return False


def _retries_left() -> Optional[int]:
    job = get_current_job()
    if not job:
        return None
    # rq exposes retries_left when Retry is used; keep defensive fallback.
    return getattr(job, "retries_left", None)


def _build_context(event_id: str) -> JobContext:
    ev = load_event(event_id)
    if ev is None:
        raise PermanentJobError(f"Event not found: {event_id}")
    lead_email = best_effort_extract_email(ev.payload) or ""
    return JobContext(
        event_id=ev.event_id,
        idempotency_key=ev.idempotency_key,
        source=ev.source,
        event_type=ev.event_type,
        external_id=ev.external_id,
        lead_email=lead_email,
    )


def run_event_job(event_id: str, handler: Callable[[JobContext], T]) -> T:
    """
    Wrapper providing:
    - Attempts tracking
    - Status transitions
    - Idempotency guard (processed marker)
    - Slack alert on terminal failure
    - Respecting RQ Retry: raise to retry on transient errors
    """
    ctx = _build_context(event_id)

    if is_processed(ctx.idempotency_key):
        logger.info("Idempotency already processed; skipping. key=%s event_id=%s", ctx.idempotency_key, ctx.event_id)
        set_event_status(ctx.event_id, "processed")
        # type: ignore[return-value]
        return None

    attempt = increment_attempts(ctx.event_id)
    set_event_status(ctx.event_id, "processing")
    logger.info(
        "Processing event. attempt=%s source=%s event_type=%s external_id=%s event_id=%s",
        attempt,
        ctx.source,
        ctx.event_type,
        ctx.external_id,
        ctx.event_id,
    )

    try:
        result = handler(ctx)
        mark_processed(ctx.idempotency_key)
        # Preserve any handler-set status such as 'ignored'.
        latest = load_event(ctx.event_id)
        if latest is None or latest.status not in ("ignored", "failed"):
            set_event_status(ctx.event_id, "processed")
        return result
    except Exception as e:  # noqa: BLE001
        transient = _is_transient_exc(e)
        retries_left = _retries_left()
        logger.exception("Job error. transient=%s retries_left=%s event_id=%s", transient, retries_left, ctx.event_id)

        # Transient failures should remain eligible for retry; keep status as queued.
        if transient:
            set_event_status(ctx.event_id, "queued", last_error=str(e))
            # Alert only when retries are exhausted.
            if retries_left == 0:
                msg = (
                    f"*❌ Job Failed (Terminal After Retries)*\n\n"
                    f"*Source*: {ctx.source}\n"
                    f"*Event Type*: {ctx.event_type}\n"
                    f"*External ID*: {ctx.external_id}\n"
                    f"*Event ID*: {ctx.event_id}\n"
                    f"*Lead Email*: {ctx.lead_email or 'unknown'}\n"
                    f"*Error*: {e}"
                )
                send_slack_alert(text=msg)
            raise

        # Permanent failure: mark failed, alert, and DO NOT raise (prevents RQ Retry from rescheduling).
        set_event_status(ctx.event_id, "failed", last_error=str(e))
        msg = (
            f"*❌ Job Failed (Permanent Error)*\n\n"
            f"*Source*: {ctx.source}\n"
            f"*Event Type*: {ctx.event_type}\n"
            f"*External ID*: {ctx.external_id}\n"
            f"*Event ID*: {ctx.event_id}\n"
            f"*Lead Email*: {ctx.lead_email or 'unknown'}\n"
            f"*Error*: {e}"
        )
        send_slack_alert(text=msg)
        # type: ignore[return-value]
        return None


