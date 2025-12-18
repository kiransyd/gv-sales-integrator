from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.services.redis_client import get_redis_str
from app.settings import get_settings


@dataclass(frozen=True)
class AcquireResult:
    acquired: bool
    existing_event_id: str = ""


def try_acquire_idempotency_key(*, idempotency_key: str, event_id: str) -> AcquireResult:
    """
    Atomically acquire an idempotency key for a new event record.

    If already acquired, returns the existing event_id (if present).
    TTL is set to prevent unbounded Redis growth.
    """
    settings = get_settings()
    r = get_redis_str()
    idx_key = f"event_by_idem:{idempotency_key}"
    # Set with NX (only if not exists) and EX (expiry in seconds)
    ok = r.set(idx_key, event_id, nx=True, ex=settings.IDEMPOTENCY_TTL_SECONDS)
    if ok:
        return AcquireResult(acquired=True)
    existing = r.get(idx_key) or ""
    return AcquireResult(acquired=False, existing_event_id=existing)


def get_event_id_for_key(idempotency_key: str) -> str:
    r = get_redis_str()
    return r.get(f"event_by_idem:{idempotency_key}") or ""


def release_idempotency_key(idempotency_key: str) -> None:
    r = get_redis_str()
    r.delete(f"event_by_idem:{idempotency_key}")


def processed_marker_key(idempotency_key: str) -> str:
    return f"idem:processed:{idempotency_key}"


def mark_processed(idempotency_key: str) -> None:
    """
    Mark an idempotency key as processed with TTL to prevent unbounded Redis growth.
    """
    settings = get_settings()
    r = get_redis_str()
    r.set(processed_marker_key(idempotency_key), "1", ex=settings.IDEMPOTENCY_TTL_SECONDS)


def is_processed(idempotency_key: str) -> bool:
    r = get_redis_str()
    return r.exists(processed_marker_key(idempotency_key)) == 1


def get_processed_value(idempotency_key: str) -> Optional[str]:
    r = get_redis_str()
    return r.get(processed_marker_key(idempotency_key))



