from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.settings import Settings, get_settings
from app.services.event_store_service import load_event
from app.services.idempotency_service import get_processed_value

router = APIRouter(prefix="/debug")


def _require_debug(settings: Settings = Depends(get_settings)) -> Settings:
    if not settings.ALLOW_DEBUG_ENDPOINTS:
        raise HTTPException(status_code=404, detail="Not found")
    return settings


@router.get("/ping")
def ping(_: Settings = Depends(_require_debug)) -> dict:
    return {"ok": True}


@router.get("/info")
def info(settings: Settings = Depends(_require_debug)) -> dict[str, Any]:
    # Avoid leaking secrets; this is intentionally small.
    return {
        "env": settings.ENV,
        "dry_run": settings.DRY_RUN,
        "redis_url": settings.REDIS_URL,
        "rq_queue_name": settings.RQ_QUEUE_NAME,
        "llm_provider": settings.LLM_PROVIDER,
    }


@router.get("/echo_json")
def echo_json(raw: str, _: Settings = Depends(_require_debug)) -> dict[str, Any]:
    try:
        return json.loads(raw)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/events/{event_id}")
def debug_event(event_id: str, _: Settings = Depends(_require_debug)) -> dict[str, Any]:
    ev = load_event(event_id)
    if ev is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return {
        "id": ev.event_id,
        "source": ev.source,
        "event_type": ev.event_type,
        "external_id": ev.external_id,
        "idempotency_key": ev.idempotency_key,
        "received_at": ev.received_at,
        "status": ev.status,
        "attempts": ev.attempts,
        "last_error": ev.last_error,
        "payload": ev.payload,
    }


@router.get("/idem/{idempotency_key}")
def debug_idem(idempotency_key: str, _: Settings = Depends(_require_debug)) -> dict[str, Any]:
    v = get_processed_value(idempotency_key)
    return {"idempotency_key": idempotency_key, "processed": v == "1", "value": v}


