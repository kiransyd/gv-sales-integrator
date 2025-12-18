from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field

from app.services.event_store_service import new_event_id, set_event_status, store_incoming_event
from app.services.rq_service import default_retry, get_queue
from app.settings import Settings, get_settings

logger = logging.getLogger(__name__)
router = APIRouter()


class EnrichLeadRequest(BaseModel):
    """Request to enrich a lead"""
    lead_id: str = Field(default="", description="Zoho Lead ID (optional if email provided)")
    email: str = Field(description="Lead email address (required)")


@router.post("/enrich/lead")
async def enrich_lead(
    request: EnrichLeadRequest,
    x_enrich_secret: str = Header(None, alias="X-Enrich-Secret"),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """
    Manual lead enrichment endpoint.

    Called by Zoho button click or API integrations.
    Enriches lead with Apollo + Website intelligence.
    """
    # Verify secret key
    if settings.ENRICH_SECRET_KEY and x_enrich_secret != settings.ENRICH_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid enrichment secret key")

    if not request.email:
        raise HTTPException(status_code=400, detail="Email is required")

    # Create event for tracking
    event_id = new_event_id()
    idempotency_key = f"enrich:{request.email.lower()}"

    payload = {
        "email": request.email,
        "lead_id": request.lead_id,
    }

    store_incoming_event(
        event_id=event_id,
        source="manual_enrich",
        event_type="enrich_lead",
        external_id=request.email,
        idempotency_key=idempotency_key,
        payload=payload,
    )

    # Enqueue enrichment job
    try:
        q = get_queue()
        q.enqueue(
            "app.jobs.enrich_jobs.process_manual_enrich_job",
            event_id,
            job_id=f"{idempotency_key}:{event_id}",  # Unique job ID
            retry=default_retry(),
        )
        set_event_status(event_id, "queued")
    except Exception as e:  # noqa: BLE001
        set_event_status(event_id, "failed", last_error=f"enqueue_failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to enqueue enrichment job") from e

    logger.info("Enrichment queued for: %s (event_id: %s)", request.email, event_id)

    return {
        "ok": True,
        "queued": True,
        "event_id": event_id,
        "message": f"Lead enrichment queued for {request.email}. Check back in 30-60 seconds.",
    }
