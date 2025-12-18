from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.settings import Settings, get_settings
from app.services.event_store_service import new_event_id, set_event_status, store_incoming_event
from app.services.idempotency_service import release_idempotency_key, try_acquire_idempotency_key
from app.services.ingest_helpers import extract_readai_event_type, extract_readai_meeting_id
from app.services.rq_service import default_retry, get_queue
from app.util.security import verify_shared_secret

router = APIRouter()


@router.post("/webhooks/readai")
async def readai_webhook(request: Request, settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    raw = await request.body()

    provided = request.headers.get("X-ReadAI-Secret")
    check = verify_shared_secret(expected=settings.READAI_SHARED_SECRET, provided=provided)
    if not check.ok:
        raise HTTPException(status_code=401, detail=f"Unauthorized: {check.reason}")

    try:
        payload = json.loads(raw.decode("utf-8") if raw else "{}")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}") from e

    meeting_id = extract_readai_meeting_id(payload)
    if not meeting_id:
        raise HTTPException(status_code=400, detail="Missing meeting_id in Read.ai payload")

    event_type = extract_readai_event_type(payload)
    # Read.ai docs currently: trigger == meeting_end
    if event_type and event_type != "meeting_end":
        return {"ok": True, "ignored": True, "reason": "unsupported_trigger", "trigger": event_type}
    idem_key = f"readai:meeting_completed:{meeting_id}"
    event_id = new_event_id()

    acquired = try_acquire_idempotency_key(idempotency_key=idem_key, event_id=event_id)
    if not acquired.acquired:
        return {"ok": True, "duplicate": True, "event_id": acquired.existing_event_id}

    store_incoming_event(
        event_id=event_id,
        source="readai",
        event_type=event_type,
        external_id=meeting_id,
        idempotency_key=idem_key,
        payload=payload,
    )

    try:
        q = get_queue()
        q.enqueue("app.jobs.readai_jobs.process_readai_meeting_completed", event_id, job_id=idem_key, retry=default_retry())
        set_event_status(event_id, "queued")
    except Exception as e:  # noqa: BLE001
        release_idempotency_key(idem_key)
        set_event_status(event_id, "failed", last_error=f"enqueue_failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to enqueue job") from e

    return {"ok": True, "queued": True, "event_id": event_id, "idempotency_key": idem_key}


