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
from app.services.zoho_service import create_note, upsert_lead_by_email
from app.settings import get_settings

logger = logging.getLogger(__name__)


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


