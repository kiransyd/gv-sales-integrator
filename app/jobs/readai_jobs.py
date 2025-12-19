from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.jobs.retry import JobContext, PermanentJobError, run_event_job
from app.services.event_store_service import load_event, set_event_status
from app.services.llm_service import readai_meddic
from app.services.readai_service import (
    build_zoho_lead_payload_for_meddic,
    extract_readai_fields,
    get_all_external_attendee_emails,
    meddic_to_note_content,
    today_ymd,
)
from app.services.slack_service import notify_demo_completed
from app.services.zoho_service import create_note, create_task, find_lead_by_email, upsert_lead_by_email, update_lead
from app.settings import get_settings
from app.util.time import next_business_day

logger = logging.getLogger(__name__)


def _format_demo_date_for_zoho(dt_str: str) -> str | None:
    """
    Format a datetime string from Read.ai to Zoho's datetime format.
    Returns None if formatting fails.
    Zoho format: YYYY-MM-DDTHH:MM:SS+00:00 or YYYY-MM-DDTHH:MM:SSZ
    """
    if not dt_str or not isinstance(dt_str, str):
        return None
    
    try:
        # Parse the datetime string (handle various formats)
        s = dt_str.strip()
        
        # Handle case where string has both timezone offset and Z (e.g., "2025-12-20T01:23:58+00:00Z")
        # Remove Z if there's already a timezone offset
        if s.endswith("Z") and ("+" in s or s.count("-") > 2):
            # Has both offset and Z - remove Z
            s = s[:-1]
        elif s.endswith("Z"):
            # Only has Z, no offset - replace with +00:00
            s = s[:-1] + "+00:00"
        
        # Handle double timezone offset (shouldn't happen now, but just in case)
        if s.count("+") > 1:
            # Remove duplicate timezone offset (keep the last one)
            parts = s.rsplit("+", 1)
            if len(parts) == 2:
                s = parts[0] + "+" + parts[1]
        
        dt = datetime.fromisoformat(s)
        
        # Zoho datetime format: YYYY-MM-DDTHH:MM:SS+00:00 (with colon in timezone)
        if dt.tzinfo:
            # Ensure we're working with UTC
            dt_utc = dt.astimezone(timezone.utc)
            formatted = dt_utc.strftime('%Y-%m-%dT%H:%M:%S+00:00')
        else:
            # No timezone, assume UTC - use Z suffix
            formatted = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        return formatted
    except Exception as e:
        logger.warning("Failed to format Demo_Date from Read.ai start_time '%s': %s", dt_str, e)
        return None


def _process_meeting_completed(ctx: JobContext) -> None:
    settings = get_settings()
    ev = load_event(ctx.event_id)
    if ev is None:
        raise PermanentJobError("Event not found")

    fields = extract_readai_fields(ev.payload)
    duration = int(fields["duration_minutes"] or 0)
    if duration and duration < settings.READAI_MIN_DURATION_MINUTES:
        set_event_status(ctx.event_id, "ignored", last_error=f"Meeting too short: {duration} minutes")
        return

    attendees = fields["attendees"]
    owner = fields.get("owner", {})

    # Get all external attendee emails (owner is prioritized first)
    external_emails = get_all_external_attendee_emails(attendees, owner)
    if not external_emails:
        raise PermanentJobError("No external attendee email available to match Lead")

    # Try to find an existing lead for any of the external attendees
    # This handles cases where john@acme.com booked the meeting but mary@acme.com also attended
    email = None
    existing = None
    for candidate_email in external_emails:
        lead = find_lead_by_email(candidate_email)
        if lead and isinstance(lead, dict) and lead.get("id"):
            # Found a match! Use this email and lead
            email = candidate_email
            existing = lead
            logger.info(
                "✅ Matched Read.ai meeting to existing Zoho lead. email=%s lead_id=%s (tried %d emails)",
                email,
                lead.get("id"),
                external_emails.index(candidate_email) + 1,
            )
            break

    # If no existing lead found, use the first external email (owner if available)
    if not email:
        email = external_emails[0]
        logger.info(
            "No existing lead found for any attendee. Will create new lead with email=%s",
            email,
        )
    if existing and isinstance(existing, dict) and existing.get("id"):
        lead_id = str(existing["id"])
        # Preserve existing basic fields when updating
        existing_first = existing.get("First_Name", "")
        existing_last = existing.get("Last_Name", "")
        existing_demo_date = existing.get(settings.ZCF_DEMO_DATETIME) if settings.ZCF_DEMO_DATETIME else None
    else:
        # Create a lead if missing so we don't drop MEDDIC.
        # Try to extract name from attendees
        first_name = ""
        last_name = ""
        for att in attendees:
            att_email = att.get("email", "").strip().lower()
            if att_email == email.lower():
                first_name = att.get("first_name", "") or att.get("name", "").split()[0] if att.get("name") else ""
                last_name = att.get("last_name", "") or " ".join(att.get("name", "").split()[1:]) if att.get("name") and " " in att.get("name", "") else ""
                break

        # Truncate names to Zoho's 40-character limit to prevent validation errors
        first_name = first_name[:40] if first_name else ""
        last_name = last_name[:40] if last_name else ""

        create_payload = {
            "Email": email,
            settings.ZOHO_LEAD_STATUS_FIELD: settings.STATUS_DEMO_COMPLETE,
            "Last_Name": last_name or ".",
        }
        if first_name:
            create_payload["First_Name"] = first_name
        
        # Add Demo_Date from Read.ai start_time if available
        if settings.ZCF_DEMO_DATETIME and fields.get("start_time"):
            demo_date_formatted = _format_demo_date_for_zoho(fields["start_time"])
            if demo_date_formatted:
                create_payload[settings.ZCF_DEMO_DATETIME] = demo_date_formatted
                logger.debug("Setting Demo_Date from Read.ai start_time: %s", demo_date_formatted)
        
        lead_id = upsert_lead_by_email(email, create_payload)
        create_note(
            lead_id,
            "Read.ai Lead Created (No Calendly Match)",
            f"Created from Read.ai webhook because no existing Lead matched attendee email: {email}",
        )
        existing_first = first_name
        existing_last = last_name
        existing_demo_date = None

    logger.info(
        "Calling LLM to generate MEDDIC data. transcript_len=%d summary_len=%d",
        len(str(fields["transcript"] or "")),
        len(str(fields["summary"] or "")),
    )
    meddic = readai_meddic(
        title=str(fields["title"] or ""),
        datetime_str=str(fields["datetime"] or ""),
        attendees=attendees,
        summary=str(fields["summary"] or ""),
        transcript=str(fields["transcript"] or ""),
    )
    # Log all MEDDIC fields for debugging
    logger.info(
        "LLM MEDDIC extraction complete. metrics=%s confidence=%s",
        bool(getattr(meddic, "metrics", "")),
        getattr(meddic, "confidence", "unknown"),
    )
    logger.debug(
        "Full MEDDIC output: metrics=%s economic_buyer=%s decision_criteria=%s decision_process=%s "
        "identified_pain=%s champion=%s competition=%s next_steps=%s risks=%s",
        bool(getattr(meddic, "metrics", "")),
        bool(getattr(meddic, "economic_buyer", "")),
        bool(getattr(meddic, "decision_criteria", "")),
        bool(getattr(meddic, "decision_process", "")),
        bool(getattr(meddic, "identified_pain", "")),
        bool(getattr(meddic, "champion", "")),
        bool(getattr(meddic, "competition", "")),
        bool(getattr(meddic, "next_steps", "")),
        bool(getattr(meddic, "risks", "")),
    )

    update_payload = build_zoho_lead_payload_for_meddic(meddic)
    
    # Preserve basic fields if they exist (don't overwrite with empty)
    if existing_first and not update_payload.get("First_Name"):
        update_payload["First_Name"] = existing_first
    if existing_last and not update_payload.get("Last_Name"):
        update_payload["Last_Name"] = existing_last
    # Always include email to ensure it's set
    update_payload["Email"] = email
    
    # Add Demo_Date from Read.ai start_time if:
    # 1. Demo_Date field is configured
    # 2. Read.ai has start_time
    # 3. Existing lead doesn't already have Demo_Date (preserve Calendly date if it exists)
    if settings.ZCF_DEMO_DATETIME and fields.get("start_time"):
        if not existing_demo_date:
            # Existing lead doesn't have Demo_Date, set it from Read.ai
            demo_date_formatted = _format_demo_date_for_zoho(fields["start_time"])
            if demo_date_formatted:
                update_payload[settings.ZCF_DEMO_DATETIME] = demo_date_formatted
                logger.debug("Setting Demo_Date from Read.ai start_time (existing lead had none): %s", demo_date_formatted)
        else:
            # Existing lead already has Demo_Date (likely from Calendly), preserve it
            logger.debug("Preserving existing Demo_Date from existing lead: %s", existing_demo_date)
    
    # Log what we're about to send to Zoho
    logger.info("📤 Sending to Zoho: %d fields", len(update_payload))
    for field, value in update_payload.items():
        if field not in ["Lead_Status", "Email"]:  # Skip status and email, they're always there
            logger.info("   - %s: %s", field, (value[:80] + "..." if isinstance(value, str) and len(value) > 80 else value))
    
    zoho_response = update_lead(lead_id, update_payload)
    
    # Log Zoho response
    if zoho_response:
        logger.info("📥 Zoho response received")
        if zoho_response.get("data"):
            data = zoho_response["data"][0] if isinstance(zoho_response["data"], list) else {}
            if data.get("status") == "success":
                logger.info("✅ Zoho update confirmed successful")
            else:
                logger.warning("⚠️  Zoho update may have issues: %s", zoho_response)

    note_title = f"Read.ai Demo Summary (MEDDIC) - {today_ymd()}"
    note_content = meddic_to_note_content(
        meddic,
        recording_url=str(fields["recording_url"] or ""),
        attendees=attendees,
        transcript_raw=ev.payload.get("transcript"),
        owner=owner,
    )
    create_note(lead_id, note_title, note_content)

    if settings.CREATE_FOLLOWUP_TASK:
        due = next_business_day().isoformat()
        desc = f"Next steps:\n{getattr(meddic, 'next_steps', '')}".strip()
        create_task(lead_id=lead_id, subject="Follow up after demo", due_date=due, description=desc)

    # Send Slack notification
    # Extract name and company from existing lead or attendees
    name = existing_first + " " + existing_last if existing_first or existing_last else ""
    company = existing.get("Company", "") if existing else ""
    meddic_confidence = getattr(meddic, "confidence", None)
    notify_demo_completed(
        email=email,
        name=name.strip() if name else "",
        company=company,
        meeting_duration=duration,
        meddic_confidence=str(meddic_confidence) if meddic_confidence else None,
        lead_id=lead_id,
    )


def process_readai_meeting_completed(event_id: str) -> None:
    run_event_job(event_id, _process_meeting_completed)


