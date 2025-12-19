from __future__ import annotations

import logging

from app.jobs.retry import JobContext, run_event_job
from app.services.calendly_service import (
    build_zoho_lead_payload_for_calendly,
    lead_intel_to_text,
    parse_calendly_lead_info,
)
from app.services.event_store_service import load_event
from app.services.llm_service import calendly_lead_intel
from app.services.slack_service import notify_demo_booked, notify_demo_canceled, notify_enrichment_completed
from app.services.zoho_service import create_note, update_lead, upsert_lead_by_email
from app.settings import get_settings

logger = logging.getLogger(__name__)


def _auto_enrich_lead(email: str, lead_id: str, company: str = "") -> None:
    """
    Auto-enrich lead with Apollo + Website intelligence (if enabled).
    This is a best-effort enrichment - failures are logged but don't fail the main job.
    
    Args:
        email: Lead email address
        lead_id: Zoho Lead ID
        company: Company name (optional, for Slack notifications)
    """
    from app.jobs.enrich_jobs import _build_enrichment_note, _build_zoho_payload_from_enrichment, enrich_lead_by_email

    settings = get_settings()

    if not settings.ENABLE_AUTO_ENRICH_CALENDLY:
        logger.debug("Auto-enrichment disabled (ENABLE_AUTO_ENRICH_CALENDLY=false)")
        return

    logger.info("Auto-enriching Calendly lead: %s", email)

    try:
        # Perform enrichment
        enrichment = enrich_lead_by_email(email)

        if not enrichment.data_sources:
            logger.info("No enrichment data found for: %s", email)
            return

        # Build Zoho update payload from enrichment
        zoho_payload = _build_zoho_payload_from_enrichment(enrichment)

        # Update Zoho lead with enrichment data
        if zoho_payload:
            update_lead(lead_id, zoho_payload)
            logger.info("Updated lead with enrichment data: %s (%d fields)", lead_id, len(zoho_payload))

        # Create enrichment note
        note_title = "Auto-Enrichment (Apollo + Website)"
        note_content = _build_enrichment_note(enrichment)
        create_note(lead_id, note_title, note_content)

        # Fetch and upload company logo (best effort)
        from app.util.text_format import extract_domain_from_email
        from app.services.brandfetch_service import fetch_company_logo
        from app.services.zoho_service import upload_lead_photo

        domain = extract_domain_from_email(email)
        if domain:
            logo_data = fetch_company_logo(domain)
            if logo_data:
                upload_lead_photo(lead_id, logo_data, filename=f"{domain}_logo.png")

        logger.info("Auto-enrichment complete for: %s (%d sources)", email, len(enrichment.data_sources))

        # Send Slack notification
        notify_enrichment_completed(
            email=email,
            company=company,
            data_sources=enrichment.data_sources,
            lead_id=lead_id,
        )

    except Exception as e:  # noqa: BLE001
        # Log but don't fail the main Calendly job
        logger.warning("Auto-enrichment failed for %s: %s", email, e)


def _process_created(ctx: JobContext) -> None:
    settings = get_settings()
    ev = load_event(ctx.event_id)
    if ev is None:
        raise ValueError("Event not found")

    info = parse_calendly_lead_info(ev.payload)
    if not info.email:
        raise ValueError("Calendly payload missing invitee email")

    subset = {
        "event": ev.event_type,
        "invitee": {"email": info.email, "name": info.name, "uri": info.invitee_uri},
        "demo": {"start_time": info.demo_datetime, "timezone": info.demo_timezone, "event_uri": info.event_uri},
        "questions_and_answers": info.qa_text,
    }
    intel = calendly_lead_intel(calendly_payload_subset=subset)
    intel_text = lead_intel_to_text(intel)

    zoho_payload = build_zoho_lead_payload_for_calendly(
        info=info,
        lead_status=settings.STATUS_DEMO_BOOKED,
        intel=intel,
    )
    lead_id = upsert_lead_by_email(info.email, zoho_payload)

    note_title = "Calendly Demo Booked"
    note_lines = []
    if info.demo_datetime:
        demo_local = getattr(intel, "demo_datetime_local", "") or ""
        if demo_local and demo_local != "Not discussed":
            note_lines.append(f"Demo datetime: {demo_local}".strip())
        else:
            note_lines.append(f"Demo datetime: {info.demo_datetime} ({info.demo_timezone})".strip())
    if info.qa_text:
        note_lines.append("")
        note_lines.append("Q&A:")
        note_lines.append(info.qa_text)
    if intel_text:
        note_lines.append("")
        note_lines.append("Lead intel:")
        note_lines.append(intel_text)
    create_note(lead_id, note_title, "\n".join(note_lines).strip())

    # Send Slack notification
    demo_dt_str = info.demo_datetime or "Not specified"
    if intel.demo_datetime_local and intel.demo_datetime_local != "Not discussed":
        demo_dt_str = intel.demo_datetime_local
    notify_demo_booked(
        email=info.email,
        name=info.name or "",
        company=intel.company_name or "",
        demo_datetime=demo_dt_str,
        lead_id=lead_id,
    )

    # Auto-enrich lead with Apollo + Website intelligence (if enabled)
    _auto_enrich_lead(info.email, lead_id, company=intel.company_name or "")


def _process_canceled(ctx: JobContext) -> None:
    settings = get_settings()
    ev = load_event(ctx.event_id)
    if ev is None:
        raise ValueError("Event not found")

    info = parse_calendly_lead_info(ev.payload)
    if not info.email:
        raise ValueError("Calendly payload missing invitee email")

    # For canceled, we don't need LLM extraction
    from app.schemas.llm import CalendlyLeadIntel
    empty_intel = CalendlyLeadIntel()
    zoho_payload = build_zoho_lead_payload_for_calendly(
        info=info,
        lead_status=settings.STATUS_DEMO_CANCELED,
        intel=empty_intel,
    )
    lead_id = upsert_lead_by_email(info.email, zoho_payload)
    create_note(
        lead_id,
        "Calendly Demo Canceled",
        f"Calendly cancellation received.\nInvitee: {info.email}\nInvitee URI: {info.invitee_uri}".strip(),
    )

    # Send Slack notification
    notify_demo_canceled(
        email=info.email,
        name=info.name or "",
        company="",  # Company not extracted for canceled events
        lead_id=lead_id,
    )


def _process_rescheduled(ctx: JobContext) -> None:
    # Treat rescheduled as booked with updated demo datetime/timezone.
    settings = get_settings()
    ev = load_event(ctx.event_id)
    if ev is None:
        raise ValueError("Event not found")

    info = parse_calendly_lead_info(ev.payload)
    if not info.email:
        raise ValueError("Calendly payload missing invitee email")

    subset = {
        "event": ev.event_type,
        "invitee": {"email": info.email, "name": info.name, "uri": info.invitee_uri},
        "demo": {"start_time": info.demo_datetime, "timezone": info.demo_timezone, "event_uri": info.event_uri},
        "questions_and_answers": info.qa_text,
    }
    intel = calendly_lead_intel(calendly_payload_subset=subset)

    zoho_payload = build_zoho_lead_payload_for_calendly(
        info=info,
        lead_status=settings.STATUS_DEMO_BOOKED,
        intel=intel,
    )
    lead_id = upsert_lead_by_email(info.email, zoho_payload)
    
    demo_local = getattr(intel, "demo_datetime_local", "") or ""
    if demo_local and demo_local != "Not discussed":
        demo_dt_str = demo_local
    else:
        demo_dt_str = f"{info.demo_datetime} ({info.demo_timezone})"
    create_note(
        lead_id,
        "Calendly Demo Rescheduled",
        f"Calendly reschedule received.\nNew demo datetime: {demo_dt_str}".strip(),
    )


def process_calendly_invitee_created(event_id: str) -> None:
    run_event_job(event_id, _process_created)


def process_calendly_invitee_canceled(event_id: str) -> None:
    run_event_job(event_id, _process_canceled)


def process_calendly_invitee_rescheduled(event_id: str) -> None:
    run_event_job(event_id, _process_rescheduled)


