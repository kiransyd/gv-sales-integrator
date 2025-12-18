from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from app.services.redis_client import get_redis_str


@dataclass(frozen=True)
class StoredEvent:
    event_id: str
    source: str
    event_type: str
    external_id: str
    idempotency_key: str
    payload: dict[str, Any]
    received_at: str
    status: str
    attempts: int
    last_error: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_event_id() -> str:
    return str(uuid4())


def store_incoming_event(
    *,
    event_id: str,
    source: str,
    event_type: str,
    external_id: str,
    idempotency_key: str,
    payload: dict[str, Any],
) -> None:
    r = get_redis_str()
    key = f"event:{event_id}"
    r.hset(
        key,
        mapping={
            "id": event_id,
            "source": source,
            "event_type": event_type,
            "external_id": external_id,
            "idempotency_key": idempotency_key,
            "payload_json": json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
            "received_at": _now_iso(),
            "status": "received",
            "attempts": "0",
            "last_error": "",
        },
    )


def set_event_status(event_id: str, status: str, *, last_error: str = "") -> None:
    r = get_redis_str()
    mapping: dict[str, str] = {"status": status}
    if last_error:
        mapping["last_error"] = last_error
    r.hset(f"event:{event_id}", mapping=mapping)


def increment_attempts(event_id: str) -> int:
    r = get_redis_str()
    return int(r.hincrby(f"event:{event_id}", "attempts", 1))


def load_event(event_id: str) -> Optional[StoredEvent]:
    r = get_redis_str()
    data = r.hgetall(f"event:{event_id}")
    if not data:
        return None
    payload_json = data.get("payload_json") or "{}"
    try:
        payload = json.loads(payload_json)
    except Exception:  # noqa: BLE001
        payload = {"_unparseable_payload_json": payload_json}
    return StoredEvent(
        event_id=data.get("id", event_id),
        source=data.get("source", ""),
        event_type=data.get("event_type", ""),
        external_id=data.get("external_id", ""),
        idempotency_key=data.get("idempotency_key", ""),
        payload=payload,
        received_at=data.get("received_at", ""),
        status=data.get("status", ""),
        attempts=int(data.get("attempts", "0") or "0"),
        last_error=data.get("last_error", "") or "",
    )



