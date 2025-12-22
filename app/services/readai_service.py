from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from app.settings import get_settings


def _domain(email: str) -> str:
    return email.split("@", 1)[-1].lower().strip() if "@" in email else ""


def customer_domains_set() -> set[str]:
    settings = get_settings()
    return {d.strip().lower() for d in settings.READAI_CUSTOMER_DOMAINS.split(",") if d.strip()}


def _is_external_email(email: str) -> bool:
    """
    Check if an email is external (not internal/system).
    Returns True if the email is external and should be considered for matching.
    """
    if not isinstance(email, str) or not email.strip():
        return False

    email_clean = email.strip().lower()
    internal = customer_domains_set()

    # Skip internal domains
    if _domain(email_clean) in internal:
        return False

    # Skip Google Calendar resource/group emails
    if email_clean.endswith("@group.calendar.google.com") or \
       email_clean.endswith("@resource.calendar.google.com"):
        return False

    return True


def get_all_external_attendee_emails(attendees: list[dict[str, Any]], owner: dict[str, Any]) -> list[str]:
    """
    Get all external attendee emails, prioritizing the meeting owner.

    Returns:
        List of external emails, with owner first (if external), followed by other external attendees.
        Returns empty list if no external emails found.
    """
    emails: list[str] = []

    # First, try to add the owner email (likely the Calendly booker)
    owner_email = owner.get("email") if isinstance(owner, dict) else None
    if owner_email and _is_external_email(owner_email):
        emails.append(owner_email.strip().lower())

    # Then add other external attendee emails
    for a in attendees:
        email = a.get("email")
        if not email:
            continue
        email_clean = email.strip().lower()

        # Skip if already added (owner) or not external
        if email_clean in emails or not _is_external_email(email_clean):
            continue

        emails.append(email_clean)

    return emails


def select_best_external_attendee_email(attendees: list[dict[str, Any]]) -> str:
    """
    Deterministic selection:
    - requires email
    - excludes internal/customer domains from READAI_CUSTOMER_DOMAINS
    - excludes Google Calendar resource/group emails
    - returns first external in input order

    DEPRECATED: Use get_all_external_attendee_emails for better matching.
    """
    for a in attendees:
        email = a.get("email")
        if email and _is_external_email(email):
            return email.strip().lower()
    return ""


def extract_readai_fields(payload: dict[str, Any]) -> dict[str, Any]:
    # Read.ai docs:
    # session_id, trigger=meeting_end, title, start_time, end_time, participants, owner, summary,
    # action_items, key_questions, topics, report_url, transcript{speaker_blocks...}
    title = payload.get("title") or payload.get("meeting_title") or ""
    if not isinstance(title, str):
        title = ""

    start_time = payload.get("start_time") or payload.get("datetime") or payload.get("started_at") or ""
    end_time = payload.get("end_time") or payload.get("ended_at") or ""
    dt = start_time if isinstance(start_time, str) else ""
    if not isinstance(dt, str):
        dt = ""

    summary = payload.get("summary") or payload.get("meeting_summary") or ""
    if not isinstance(summary, str):
        summary = ""

    transcript_raw = payload.get("transcript") or payload.get("meeting_transcript") or ""
    transcript = _transcript_to_text(transcript_raw)

    attendees = payload.get("attendees") or payload.get("participants") or payload.get("participants") or []
    if not isinstance(attendees, list):
        attendees = []
    attendees = [a for a in attendees if isinstance(a, dict)]

    # Extract owner (the person who scheduled/owns the meeting)
    owner = payload.get("owner")
    if not isinstance(owner, dict):
        owner = {}

    duration_min = payload.get("duration_minutes") or payload.get("duration_min") or payload.get("duration") or 0
    try:
        duration_min = int(duration_min)
    except Exception:  # noqa: BLE001
        duration_min = 0
    if not duration_min:
        duration_min = _duration_minutes_from_times(start_time, end_time)

    recording_url = payload.get("recording_url") or payload.get("recording") or payload.get("report_url") or ""
    if not isinstance(recording_url, str):
        recording_url = ""

    return {
        "title": title,
        "datetime": dt,
        "start_time": start_time if isinstance(start_time, str) else "",
        "end_time": end_time if isinstance(end_time, str) else "",
        "summary": summary,
        "transcript": transcript,
        "attendees": attendees,
        "owner": owner,
        "duration_minutes": duration_min,
        "recording_url": recording_url,
    }


def _parse_iso(dt: Any) -> Optional[datetime]:
    if not isinstance(dt, str) or not dt.strip():
        return None
    s = dt.strip()
    # Support trailing Z
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except Exception:  # noqa: BLE001
        return None


def _duration_minutes_from_times(start_time: Any, end_time: Any) -> int:
    s = _parse_iso(start_time)
    e = _parse_iso(end_time)
    if not s or not e:
        return 0
    delta = e - s
    mins = int(delta.total_seconds() // 60)
    return max(0, mins)


def _transcript_to_text(transcript: Any) -> str:
    # Read.ai transcript is typically an object with speaker_blocks.
    if isinstance(transcript, str):
        return transcript
    if not isinstance(transcript, dict):
        return ""
    blocks = transcript.get("speaker_blocks") or []
    if not isinstance(blocks, list):
        return ""
    lines: list[str] = []
    for b in blocks:
        if not isinstance(b, dict):
            continue
        speaker = b.get("speaker") or {}
        name = ""
        if isinstance(speaker, dict):
            name = str(speaker.get("name") or "").strip()
        words = str(b.get("words") or "").strip()
        if not words:
            continue
        if name:
            lines.append(f"{name}: {words}")
        else:
            lines.append(words)
    return "\n".join(lines).strip()


def _extract_attendee_summaries(
    attendees: list[dict[str, Any]],
    transcript_raw: Any,
    owner: dict[str, Any],
) -> str:
    """
    Extract attendee information and their key talking points from the transcript.
    Returns a formatted string with attendee details.
    """
    if not attendees:
        return ""

    # Parse transcript to get speaker blocks
    speaker_stats: dict[str, dict[str, Any]] = {}
    if isinstance(transcript_raw, dict):
        blocks = transcript_raw.get("speaker_blocks") or []
        if isinstance(blocks, list):
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                speaker = block.get("speaker") or {}
                if not isinstance(speaker, dict):
                    continue
                name = str(speaker.get("name") or "").strip()
                words = str(block.get("words") or "").strip()

                if name and words:
                    if name not in speaker_stats:
                        speaker_stats[name] = {
                            "statements": [],
                            "word_count": 0,
                        }
                    # Store first few statements (up to 3) for context
                    if len(speaker_stats[name]["statements"]) < 3:
                        speaker_stats[name]["statements"].append(words)
                    speaker_stats[name]["word_count"] += len(words.split())

    # Build attendee list with details
    lines: list[str] = []
    internal = customer_domains_set()
    owner_email = owner.get("email", "").strip().lower() if isinstance(owner, dict) else ""

    for att in attendees:
        email = att.get("email", "").strip()
        name = att.get("name", "").strip()

        if not email and not name:
            continue

        # Determine if internal/external
        is_internal = email and _domain(email) in internal
        role = "Internal" if is_internal else "External"

        # Check if this is the meeting owner
        is_owner = email.lower() == owner_email if email and owner_email else False
        if is_owner:
            role += " (Meeting Owner)"

        # Build attendee info line
        info_parts = []
        if name:
            info_parts.append(name)
        if email:
            info_parts.append(f"<{email}>")
        info_parts.append(f"[{role}]")

        lines.append("  • " + " ".join(info_parts))

        # Add speaking stats if available
        if name in speaker_stats:
            stats = speaker_stats[name]
            word_count = stats["word_count"]
            lines.append(f"    - Spoke ~{word_count} words")

            # Add first key statement as a sample
            if stats["statements"]:
                first_statement = stats["statements"][0]
                # Truncate if too long
                if len(first_statement) > 150:
                    first_statement = first_statement[:150] + "..."
                lines.append(f'    - Sample: "{first_statement}"')

    if not lines:
        return ""

    return "\n".join(lines)


def meddic_to_note_content(
    meddic: Any,
    *,
    recording_url: str = "",
    attendees: list[dict[str, Any]] | None = None,
    transcript_raw: Any = None,
    owner: dict[str, Any] | None = None,
    kb_intelligence: str | None = None,
) -> str:
    def g(attr: str) -> str:
        return (getattr(meddic, attr, "") or "").strip()

    lines: list[str] = []
    conf = g("confidence")
    if conf:
        lines.append(f"Confidence: {conf}")
        lines.append("")

    def section(title: str, body: str) -> None:
        if not body:
            return
        lines.append(f"{title}:\n{body}".strip())
        lines.append("")

    # Add attendee information at the top (after confidence)
    if attendees:
        attendee_summary = _extract_attendee_summaries(
            attendees or [],
            transcript_raw,
            owner or {},
        )
        if attendee_summary:
            section("Meeting Attendees", attendee_summary)

    section("Metrics", g("metrics"))
    section("Economic buyer", g("economic_buyer"))
    section("Decision criteria", g("decision_criteria"))
    section("Decision process", g("decision_process"))
    section("Identified pain", g("identified_pain"))
    section("Champion", g("champion"))
    section("Competition", g("competition"))
    section("Next steps", g("next_steps"))
    section("Risks", g("risks"))
    
    # Add GoVisually Intelligence section if KB was used
    if kb_intelligence:
        import logging
        logger = logging.getLogger(__name__)
        logger.info("📚 Adding GoVisually Intelligence section to note (%d chars)", len(kb_intelligence))
        section("Key Talking Points for Follow-up", kb_intelligence)

    if recording_url:
        lines.append(f"Recording: {recording_url}")

    return "\n".join(lines).strip()


def build_zoho_lead_payload_for_meddic(meddic: Any) -> dict[str, Any]:
    import logging
    logger = logging.getLogger(__name__)
    
    settings = get_settings()
    payload: dict[str, Any] = {
        settings.ZOHO_LEAD_STATUS_FIELD: settings.STATUS_DEMO_COMPLETE,
    }

    def set_if(field: str, value: str) -> None:
        if field and value:
            payload[field] = value
            logger.debug("Setting Zoho field %s = %s (len=%d)", field, value[:50] + "..." if len(value) > 50 else value, len(value))
        elif field and not value:
            logger.debug("Skipping Zoho field %s (empty value)", field)
        elif not field:
            logger.debug("Skipping MEDDIC field (no Zoho mapping configured)")

    # Extract all MEDDIC values
    metrics_val = getattr(meddic, "metrics", "") or ""
    econ = getattr(meddic, "economic_buyer", "") or ""
    decision_criteria_val = getattr(meddic, "decision_criteria", "") or ""
    decision_process_val = getattr(meddic, "decision_process", "") or ""
    identified_pain_val = getattr(meddic, "identified_pain", "") or ""
    champ = getattr(meddic, "champion", "") or ""
    competition_val = getattr(meddic, "competition", "") or ""
    confidence_val = getattr(meddic, "confidence", "") or ""
    next_steps_val = getattr(meddic, "next_steps", "") or ""
    risks_val = getattr(meddic, "risks", "") or ""
    
    # Log what LLM extracted (for debugging)
    logger.info(
        "LLM extracted MEDDIC: metrics=%d chars, economic_buyer=%d chars, decision_criteria=%d chars, "
        "decision_process=%d chars, identified_pain=%d chars, champion=%d chars, competition=%d chars, "
        "confidence=%s, next_steps=%d chars, risks=%d chars",
        len(metrics_val), len(econ), len(decision_criteria_val), len(decision_process_val),
        len(identified_pain_val), len(champ), len(competition_val), confidence_val,
        len(next_steps_val), len(risks_val),
    )
    
    set_if(settings.ZCF_MEDDIC_METRICS, metrics_val)
    set_if(settings.ZCF_MEDDIC_DECISION_CRITERIA, decision_criteria_val)
    set_if(settings.ZCF_MEDDIC_DECISION_PROCESS, decision_process_val)
    set_if(settings.ZCF_MEDDIC_IDENTIFIED_PAIN, identified_pain_val)
    # If both map to the same Zoho field, combine without overwriting.
    if (
        settings.ZCF_MEDDIC_ECONOMIC_BUYER
        and settings.ZCF_MEDDIC_ECONOMIC_BUYER == settings.ZCF_MEDDIC_CHAMPION
        and (econ or champ)
    ):
        combined_parts: list[str] = []
        if econ:
            combined_parts.append(f"Economic buyer:\n{econ}".strip())
        if champ:
            combined_parts.append(f"Champion:\n{champ}".strip())
        payload[settings.ZCF_MEDDIC_ECONOMIC_BUYER] = "\n\n".join(combined_parts).strip()
    else:
        set_if(settings.ZCF_MEDDIC_ECONOMIC_BUYER, econ)
        set_if(settings.ZCF_MEDDIC_CHAMPION, champ)
    set_if(settings.ZCF_MEDDIC_COMPETITION, competition_val)
    set_if(settings.ZCF_MEDDIC_CONFIDENCE, confidence_val)

    return payload


def today_ymd() -> str:
    return datetime.now(timezone.utc).date().isoformat()


