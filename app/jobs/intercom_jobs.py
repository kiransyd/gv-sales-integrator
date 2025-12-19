from __future__ import annotations

import logging

from app.jobs.retry import JobContext, run_event_job
from app.services.event_store_service import load_event
from app.services.intercom_service import (
    build_zoho_lead_payload_for_intercom,
    format_intercom_note_content,
    parse_intercom_contact_info,
)
from app.services.slack_service import notify_support_qualified
from app.services.zoho_service import create_note, update_lead, upsert_lead_by_email
from app.settings import get_settings

logger = logging.getLogger(__name__)


def _auto_enrich_intercom_lead(email: str, lead_id: str, company: str = "") -> None:
    """
    Auto-enrich Intercom lead with Apollo + Website intelligence (if enabled).
    This is a best-effort enrichment - failures are logged but don't fail the main job.

    Args:
        email: Lead email address
        lead_id: Zoho Lead ID
        company: Company name (optional, for Slack notifications)
    """
    from app.jobs.enrich_jobs import (
        _build_enrichment_note,
        _build_zoho_payload_from_enrichment,
        enrich_lead_by_email,
    )

    settings = get_settings()

    if not settings.ENABLE_AUTO_ENRICH_INTERCOM:
        logger.debug("Auto-enrichment disabled for Intercom (ENABLE_AUTO_ENRICH_INTERCOM=false)")
        return

    logger.info("Auto-enriching Intercom lead: %s", email)

    try:
        # Perform enrichment
        enrichment = enrich_lead_by_email(email)

        if not enrichment.data_sources:
            logger.info("No enrichment data found for: %s", email)
            return

        # Build Zoho update payload from enrichment
        zoho_payload = _build_zoho_payload_from_enrichment(enrichment, email)

        # Update Zoho lead with enrichment data
        if zoho_payload:
            update_lead(lead_id, zoho_payload)
            logger.info("Updated lead with enrichment data: %s (%d fields)", lead_id, len(zoho_payload))

        # Create enrichment note
        note_title = "Auto-Enrichment (Apollo + Website)"
        note_content = _build_enrichment_note(enrichment)
        create_note(lead_id, note_title, note_content)

        # Fetch and upload company logo (best effort)
        from app.services.brandfetch_service import fetch_company_logo
        from app.services.zoho_service import upload_lead_photo
        from app.util.text_format import extract_domain_from_email

        domain = extract_domain_from_email(email)
        if domain:
            logo_data = fetch_company_logo(domain)
            if logo_data:
                upload_lead_photo(lead_id, logo_data, filename=f"{domain}_logo.png")

        logger.info("Auto-enrichment complete for: %s (%d sources)", email, len(enrichment.data_sources))

    except Exception as e:  # noqa: BLE001
        # Log but don't fail the main Intercom job
        logger.warning("Auto-enrichment failed for %s: %s", email, e)


def _extract_tags_from_payload(payload: dict) -> list[str]:
    """
    Extract all tag names from Intercom contact payload.

    Returns:
        List of tag names
    """
    tags = []

    # Navigate to contact's tags
    data = payload.get("data", {})
    item = data.get("item", {})

    # Tags might be in different locations
    tags_obj = item.get("tags")
    if isinstance(tags_obj, dict):
        tags_list = tags_obj.get("data", [])
        if isinstance(tags_list, list):
            for tag in tags_list:
                if isinstance(tag, dict):
                    tag_name = tag.get("name", "")
                    if tag_name:
                        tags.append(tag_name)

    return tags


def _process_contact_tagged(ctx: JobContext) -> None:
    """
    Process Intercom contact.tag.created event.

    1. Parse contact information from payload
    2. Check if contact has qualifying tags
    3. Create/update Zoho lead
    4. Create note with Intercom source info
    5. Auto-enrich if enabled
    6. Send Slack notification
    """
    settings = get_settings()
    ev = load_event(ctx.event_id)
    if ev is None:
        raise ValueError("Event not found")

    # Parse contact info
    info = parse_intercom_contact_info(ev.payload)
    if not info.email:
        raise ValueError("Intercom payload missing contact email")

    logger.info("Processing Intercom contact tagged: %s (ID: %s)", info.email, info.contact_id)

    # Extract all tags from payload
    all_tags = _extract_tags_from_payload(ev.payload)
    logger.debug("Contact has tags: %s", all_tags)

    # Check if any tags match qualifying tags
    qualifying_tags_str = settings.INTERCOM_QUALIFYING_TAGS or ""
    qualifying_tags = [t.strip() for t in qualifying_tags_str.split(",") if t.strip()]

    matched_tags = [tag for tag in all_tags if tag in qualifying_tags]

    if not matched_tags:
        logger.warning(
            "Contact %s (%s) has no qualifying tags. Tags: %s, Qualifying: %s",
            info.email,
            info.contact_id,
            all_tags,
            qualifying_tags,
        )
        # Still process it since the webhook was triggered - maybe tag was removed after
        matched_tags = all_tags[:1] if all_tags else ["Lead"]  # Use first tag or default to "Lead"

    logger.info("Matched qualifying tags: %s", matched_tags)

    # Build Zoho payload
    zoho_payload = build_zoho_lead_payload_for_intercom(
        info=info,
        lead_status=settings.STATUS_SUPPORT_QUALIFIED,
        tags=matched_tags,
    )

    # Upsert lead by email
    lead_id = upsert_lead_by_email(info.email, zoho_payload)
    logger.info("Created/updated Zoho lead: %s for contact %s", lead_id, info.email)

    # Create note with Intercom source info
    note_title = "Intercom: Contact Qualified"
    note_content = format_intercom_note_content(
        info=info,
        tags=matched_tags,
    )
    create_note(lead_id, note_title, note_content)
    logger.info("Created note in Zoho lead %s", lead_id)

    # Send Slack notification
    notify_support_qualified(
        email=info.email,
        name=info.name or "",
        company=info.company_name or "",
        tags=matched_tags,
        lead_id=lead_id,
    )

    # Auto-enrich lead with Apollo + Website intelligence (if enabled)
    _auto_enrich_intercom_lead(info.email, lead_id, company=info.company_name or "")


def process_intercom_contact_tagged(event_id: str) -> None:
    """
    Entry point for RQ job: process Intercom contact.tag.created event.
    """
    run_event_job(event_id, _process_contact_tagged)
