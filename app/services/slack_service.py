from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.settings import get_settings

logger = logging.getLogger(__name__)


def send_slack_alert(
    *,
    text: str,
    blocks: Optional[list[dict[str, Any]]] = None,
    attachments: Optional[list[dict[str, Any]]] = None,
) -> None:
    """
    Send a basic Slack alert via webhook using markdown format.
    
    All messages are sent as markdown-formatted text for maximum compatibility
    with intermediaries like Pabbly Connect. The text parameter should contain
    Slack markdown syntax (e.g., *bold*, _italic_, `code`).
    
    Args:
        text: Markdown-formatted message text
        blocks: Optional Slack Block Kit blocks (deprecated, not used)
        attachments: Optional Slack legacy attachments (deprecated, not used)
    """
    settings = get_settings()
    if not settings.SLACK_WEBHOOK_URL:
        logger.warning("Slack webhook not configured; skipping alert: %s", text)
        return

    # Always use plain text with markdown for maximum compatibility
    # This works reliably through intermediaries like Pabbly
    payload: dict[str, Any] = {"text": text}

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(settings.SLACK_WEBHOOK_URL, json=payload)
            resp.raise_for_status()
    except Exception as e:  # noqa: BLE001
        # Never crash the job just because Slack failed.
        logger.exception("Failed to send Slack alert: %s", e)


def _convert_blocks_to_attachments(text: str, blocks: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Convert Slack Block Kit blocks to legacy attachments format.
    This format is more compatible with intermediaries like Pabbly.
    """
    attachment: dict[str, Any] = {
        "color": "good",  # Default color
        "text": text,
        "fields": [],
    }

    # Extract title from header block
    for block in blocks:
        if block.get("type") == "header":
            title_text = block.get("text", {}).get("text", "")
            if title_text:
                attachment["title"] = title_text
                attachment["pretext"] = title_text

        # Extract fields from section blocks
        elif block.get("type") == "section":
            section_text = block.get("text", {}).get("text", "")
            if section_text:
                attachment["text"] = section_text

            # Extract fields
            section_fields = block.get("fields", [])
            for field in section_fields:
                field_text = field.get("text", "")
                if field_text:
                    # Parse markdown field format: "*Title*\nValue"
                    lines = field_text.split("\n", 1)
                    if len(lines) == 2:
                        title = lines[0].strip("*").strip()
                        value = lines[1]
                        attachment["fields"].append({
                            "title": title,
                            "value": value,
                            "short": True,
                        })

    return {"text": text, "attachments": [attachment]}


def _format_text_message(
    title: str,
    message: str,
    fields: Optional[list[dict[str, str]]] = None,
) -> str:
    """
    Format a message as markdown text for maximum compatibility.
    Uses Slack's markdown syntax for formatting.
    """
    lines = [f"*{title}*", "", message]
    
    if fields:
        lines.append("")
        for field in fields:
            # Format field with bold title and value
            value = field.get('value', 'N/A')
            lines.append(f"*{field['title']}*: {value}")
    
    return "\n".join(lines)


def send_slack_event(
    *,
    title: str,
    message: str,
    color: str = "good",  # "good" (green), "warning" (yellow), "danger" (red)
    fields: Optional[list[dict[str, str]]] = None,
) -> None:
    """
    Send a formatted Slack event notification using markdown format.
    
    All notifications are sent as markdown-formatted text for maximum compatibility
    with intermediaries like Pabbly Connect.
    
    Args:
        title: Event title (e.g., "🎯 New Demo Booked")
        message: Main message text (supports markdown)
        color: Attachment color ("good", "warning", "danger") - used if format mode supports it
        fields: Optional list of field dicts with "title" and "value" keys
    """
    settings = get_settings()
    if not settings.SLACK_WEBHOOK_URL:
        logger.debug("Slack webhook not configured; skipping event: %s", title)
        return

    # Always use markdown text format for maximum compatibility
    text = _format_text_message(title, message, fields)
    send_slack_alert(text=text)


# Convenience functions for common events
def notify_demo_booked(
    *,
    email: str,
    name: str,
    company: str,
    demo_datetime: str,
    lead_id: Optional[str] = None,
) -> None:
    """Send notification when a new demo is booked via Calendly."""
    fields = [
        {"title": "Email", "value": email},
        {"title": "Name", "value": name or "N/A"},
        {"title": "Company", "value": company or "N/A"},
        {"title": "Demo Date", "value": demo_datetime or "N/A"},
    ]
    if lead_id:
        fields.append({"title": "Zoho Lead ID", "value": lead_id})

    send_slack_event(
        title="🎯 New Demo Booked",
        message=f"*{name or email}* from *{company or 'Unknown'}* has booked a demo.",
        color="good",
        fields=fields,
    )


def notify_demo_canceled(
    *,
    email: str,
    name: str,
    company: str,
    lead_id: Optional[str] = None,
) -> None:
    """Send notification when a demo is canceled."""
    fields = [
        {"title": "Email", "value": email},
        {"title": "Name", "value": name or "N/A"},
        {"title": "Company", "value": company or "N/A"},
    ]
    if lead_id:
        fields.append({"title": "Zoho Lead ID", "value": lead_id})

    send_slack_event(
        title="❌ Demo Canceled",
        message=f"*{name or email}* from *{company or 'Unknown'}* has canceled their demo.",
        color="warning",
        fields=fields,
    )


def notify_demo_completed(
    *,
    email: str,
    name: str,
    company: str,
    meeting_duration: Optional[int] = None,
    meddic_confidence: Optional[str] = None,
    lead_id: Optional[str] = None,
) -> None:
    """Send notification when a demo meeting is completed (Read.ai)."""
    fields = [
        {"title": "Email", "value": email},
        {"title": "Name", "value": name or "N/A"},
        {"title": "Company", "value": company or "N/A"},
    ]
    if meeting_duration:
        fields.append({"title": "Duration", "value": f"{meeting_duration} minutes"})
    if meddic_confidence:
        fields.append({"title": "MEDDIC Confidence", "value": meddic_confidence})
    if lead_id:
        fields.append({"title": "Zoho Lead ID", "value": lead_id})

    send_slack_event(
        title="✅ Demo Completed",
        message=f"Demo meeting completed for *{name or email}* from *{company or 'Unknown'}*. MEDDIC analysis added to Zoho.",
        color="good",
        fields=fields,
    )


def notify_enrichment_completed(
    *,
    email: str,
    company: str,
    data_sources: list[str],
    lead_id: Optional[str] = None,
) -> None:
    """Send notification when lead enrichment is completed."""
    sources_text = ", ".join(data_sources) if data_sources else "None"
    fields = [
        {"title": "Email", "value": email},
        {"title": "Company", "value": company or "N/A"},
        {"title": "Data Sources", "value": sources_text},
    ]
    if lead_id:
        fields.append({"title": "Zoho Lead ID", "value": lead_id})

    send_slack_event(
        title="🔍 Lead Enrichment Complete",
        message=f"Auto-enrichment completed for *{email}* from *{company or 'Unknown'}*.",
        color="good",
        fields=fields,
    )


def notify_support_qualified(
    *,
    email: str,
    name: str,
    company: str,
    tags: list[str],
    lead_id: Optional[str] = None,
) -> None:
    """Send notification when an Intercom contact is qualified for sales."""
    tags_text = ", ".join(tags) if tags else "N/A"
    fields = [
        {"title": "Email", "value": email},
        {"title": "Name", "value": name or "N/A"},
        {"title": "Company", "value": company or "N/A"},
        {"title": "Qualifying Tags", "value": tags_text},
    ]
    if lead_id:
        fields.append({"title": "Zoho Lead ID", "value": lead_id})

    send_slack_event(
        title="🎯 Support Contact Qualified",
        message=f"*{name or email}* from *{company or 'Unknown'}* has been qualified from Intercom support.",
        color="good",
        fields=fields,
    )






