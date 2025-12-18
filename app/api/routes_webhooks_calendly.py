from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.settings import Settings, get_settings
from app.services.event_store_service import new_event_id, set_event_status, store_incoming_event
from app.services.idempotency_service import release_idempotency_key, try_acquire_idempotency_key
from app.services.ingest_helpers import (
    derive_calendly_event_type_for_processing,
    extract_calendly_event_type,
    extract_calendly_event_type_uri,
    extract_calendly_external_id,
)
from app.services.rq_service import default_retry, get_queue
from app.util.security import verify_calendly_signature

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhooks/calendly")
async def calendly_webhook(request: Request, settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    raw = await request.body()

    sig_header = (
        request.headers.get("Calendly-Webhook-Signature")
        or request.headers.get("calendly-webhook-signature")
        or request.headers.get("X-Calendly-Signature")
    )
    check = verify_calendly_signature(signing_key=settings.CALENDLY_SIGNING_KEY, header_value=sig_header, raw_body=raw)
    if not check.ok:
        raise HTTPException(status_code=401, detail=f"Invalid signature: {check.reason}")

    try:
        payload = json.loads(raw.decode("utf-8") if raw else "{}")
    except Exception as e:  # noqa: BLE001
        logger.error("Calendly webhook: Invalid JSON. Error: %s, Body preview: %s", e, raw[:500] if raw else "empty")
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}") from e

    # Log full payload structure for debugging
    logger.debug("Calendly webhook payload structure: top_keys=%s", list(payload.keys()) if isinstance(payload, dict) else "not_dict")
    if isinstance(payload, dict) and "payload" in payload:
        payload_data = payload.get("payload", {})
        if isinstance(payload_data, dict):
            logger.debug("Calendly webhook payload.payload keys: %s", list(payload_data.keys()))
            if "invitee" in payload_data:
                invitee = payload_data.get("invitee", {})
                logger.debug("Calendly webhook invitee keys: %s", list(invitee.keys()) if isinstance(invitee, dict) else "not_dict")

    raw_event_type = extract_calendly_event_type(payload)
    event_type = derive_calendly_event_type_for_processing(payload, raw_event_type)
    external_id = extract_calendly_external_id(payload)
    event_type_uri = extract_calendly_event_type_uri(payload)

    logger.debug("Calendly webhook: event_type=%s, external_id=%s, event_type_uri=%s", raw_event_type, external_id, event_type_uri)

    # Filter to only main demo event type if configured.
    if settings.CALENDLY_EVENT_TYPE_URI and event_type_uri and event_type_uri != settings.CALENDLY_EVENT_TYPE_URI:
        logger.info("Calendly webhook ignored: event_type_uri mismatch. expected=%s, got=%s", settings.CALENDLY_EVENT_TYPE_URI, event_type_uri)
        return {"ok": True, "ignored": True, "reason": "event_type_uri_mismatch"}

    if not raw_event_type or not external_id:
        logger.error("Calendly webhook: Missing required fields. event_type=%s, external_id=%s, payload_keys=%s", 
                    raw_event_type, external_id, list(payload.keys()) if isinstance(payload, dict) else "not_dict")
        raise HTTPException(status_code=400, detail="Missing event_type or external_id in Calendly payload")

    idem_key = f"calendly:{event_type}:{external_id}"
    event_id = new_event_id()

    acquired = try_acquire_idempotency_key(idempotency_key=idem_key, event_id=event_id)
    if not acquired.acquired:
        return {"ok": True, "duplicate": True, "event_id": acquired.existing_event_id}

    store_incoming_event(
        event_id=event_id,
        source="calendly",
        event_type=event_type,
        external_id=external_id,
        idempotency_key=idem_key,
        payload=payload,
    )

    # Enqueue by string path to avoid importing job modules at API startup time.
    if event_type == "invitee.created":
        func = "app.jobs.calendly_jobs.process_calendly_invitee_created"
    elif event_type == "invitee.canceled":
        func = "app.jobs.calendly_jobs.process_calendly_invitee_canceled"
    elif event_type == "invitee.rescheduled":
        func = "app.jobs.calendly_jobs.process_calendly_invitee_rescheduled"
    else:
        # Unknown event types are accepted but not processed.
        set_event_status(event_id, "ignored", last_error=f"Unknown Calendly event_type: {event_type}")
        return {"ok": True, "ignored": True, "reason": "unsupported_event_type", "event_type": event_type}

    try:
        q = get_queue()
        q.enqueue(func, event_id, job_id=idem_key, retry=default_retry())
        set_event_status(event_id, "queued")
    except Exception as e:  # noqa: BLE001
        # If enqueue fails, release idempotency key so Calendly can retry safely.
        release_idempotency_key(idem_key)
        set_event_status(event_id, "failed", last_error=f"enqueue_failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to enqueue job") from e

    return {"ok": True, "queued": True, "event_id": event_id, "idempotency_key": idem_key}


