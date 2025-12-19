from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.settings import Settings, get_settings
from app.services.event_store_service import new_event_id, set_event_status, store_incoming_event
from app.services.idempotency_service import release_idempotency_key, try_acquire_idempotency_key
from app.services.rq_service import default_retry, get_queue

logger = logging.getLogger(__name__)
router = APIRouter()


def verify_intercom_signature(
    webhook_secret: str,
    raw_body: bytes,
    signature_header: str | None,
) -> bool:
    """
    Verify Intercom webhook signature.
    Returns True if valid or if webhook_secret is not configured.

    Intercom uses HMAC SHA256 with the webhook secret.
    Header: X-Intercom-Signature or X-Hub-Signature
    """
    if not webhook_secret:
        # No secret configured, skip verification
        logger.warning("INTERCOM_WEBHOOK_SECRET not configured - skipping signature verification")
        return True

    if not signature_header:
        logger.warning("Intercom webhook signature header missing")
        return False

    # Compute expected signature
    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    # Intercom sends signature as hex string
    received = signature_header.strip()

    # Constant-time comparison
    return hmac.compare_digest(expected, received)


@router.post("/webhooks/intercom")
async def intercom_webhook(request: Request, settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    """
    Handle Intercom webhooks.
    Currently supports: contact.lead.tag.created, contact.user.tag.created
    """
    raw = await request.body()

    # Verify signature if configured
    sig_header = (
        request.headers.get("X-Intercom-Signature")
        or request.headers.get("X-Hub-Signature")
        or request.headers.get("x-intercom-signature")
    )

    if not verify_intercom_signature(settings.INTERCOM_WEBHOOK_SECRET, raw, sig_header):
        logger.error("Intercom webhook: Invalid signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = json.loads(raw.decode("utf-8") if raw else "{}")
    except Exception as e:  # noqa: BLE001
        logger.error("Intercom webhook: Invalid JSON. Error: %s, Body preview: %s", e, raw[:500] if raw else "empty")
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}") from e

    # Extract topic and contact info
    topic = payload.get("topic", "")
    created_at = payload.get("created_at", 0)

    logger.debug("Intercom webhook: topic=%s, created_at=%s", topic, created_at)

    # Support both contact.lead.tag.created and contact.user.tag.created
    supported_topics = ["contact.lead.tag.created", "contact.user.tag.created"]
    if topic not in supported_topics:
        logger.info("Intercom webhook ignored: unsupported topic=%s (supported: %s)", topic, supported_topics)
        return {"ok": True, "ignored": True, "reason": "unsupported_topic", "topic": topic}

    # Extract contact ID and tag info for idempotency
    data = payload.get("data", {})
    item = data.get("item", {})

    # The actual structure has item.type = "contact_tag" with nested contact and tag
    item_type = item.get("type", "")

    if item_type == "contact_tag":
        # New structure: item.contact and item.tag
        contact = item.get("contact", {})
        contact_id = contact.get("id", "")
        tag_obj = item.get("tag", {})
        tag_name = tag_obj.get("name", "") if isinstance(tag_obj, dict) else ""
    else:
        # Fallback: old structure where item is the contact directly
        contact_id = item.get("id", "")
        tag_name = ""

        # Try to find tag in various possible locations
        if "tag" in item:
            tag_obj = item.get("tag", {})
            if isinstance(tag_obj, dict):
                tag_name = tag_obj.get("name", "")
        elif "tags" in item:
            tags_data = item.get("tags", {})
            if isinstance(tags_data, dict):
                tags_list = tags_data.get("data", [])
                if isinstance(tags_list, list) and len(tags_list) > 0:
                    # Use the first tag (or most recent)
                    tag_name = tags_list[0].get("name", "") if isinstance(tags_list[0], dict) else ""

    if not contact_id:
        logger.error("Intercom webhook: Missing contact ID. payload_keys=%s", list(payload.keys()))
        raise HTTPException(status_code=400, detail="Missing contact ID in Intercom payload")

    logger.debug("Intercom webhook: contact_id=%s, tag_name=%s", contact_id, tag_name)

    # Check if tag is a qualifying tag
    qualifying_tags_str = settings.INTERCOM_QUALIFYING_TAGS or ""
    qualifying_tags = [t.strip() for t in qualifying_tags_str.split(",") if t.strip()]

    # If we couldn't extract the tag name, we'll process it anyway and let the job handler check all tags
    if tag_name and tag_name not in qualifying_tags:
        logger.info(
            "Intercom webhook ignored: tag '%s' not in qualifying tags: %s",
            tag_name,
            qualifying_tags,
        )
        return {
            "ok": True,
            "ignored": True,
            "reason": "tag_not_qualifying",
            "tag": tag_name,
            "qualifying_tags": qualifying_tags,
        }

    # Build idempotency key
    # Use contact_id + created_at to ensure uniqueness (a contact can be tagged multiple times)
    external_id = f"{contact_id}:{created_at}"
    idem_key = f"intercom:{topic}:{external_id}"
    event_id = new_event_id()

    acquired = try_acquire_idempotency_key(idempotency_key=idem_key, event_id=event_id)
    if not acquired.acquired:
        return {"ok": True, "duplicate": True, "event_id": acquired.existing_event_id}

    store_incoming_event(
        event_id=event_id,
        source="intercom",
        event_type=topic,
        external_id=external_id,
        idempotency_key=idem_key,
        payload=payload,
    )

    # Enqueue job - same handler for both lead and user tags
    func = "app.jobs.intercom_jobs.process_intercom_contact_tagged"

    try:
        q = get_queue()
        q.enqueue(func, event_id, job_id=idem_key, retry=default_retry())
        set_event_status(event_id, "queued")
    except Exception as e:  # noqa: BLE001
        # If enqueue fails, release idempotency key so Intercom can retry safely
        release_idempotency_key(idem_key)
        set_event_status(event_id, "failed", last_error=f"enqueue_failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to enqueue job") from e

    return {"ok": True, "queued": True, "event_id": event_id, "idempotency_key": idem_key}
