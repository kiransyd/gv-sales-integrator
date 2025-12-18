from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from app.settings import get_settings
from app.util.text_format import qa_to_text


def _get(d: dict[str, Any], *keys: str) -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


@dataclass(frozen=True)
class CalendlyLeadInfo:
    email: str
    name: str
    first_name: str
    last_name: str
    demo_datetime: str
    demo_timezone: str
    invitee_uri: str
    event_uri: str
    qa_text: str
    phone: str = ""
    tracking: dict[str, Any] = None  # UTM parameters and tracking data


def parse_calendly_lead_info(payload: dict[str, Any]) -> CalendlyLeadInfo:
    # Calendly webhook structure can vary:
    # New format: payload.payload.email, payload.payload.name (flattened)
    # Old format: payload.payload.invitee.email, payload.payload.invitee.name (nested)
    
    # Try new flattened format first
    email = str(_get(payload, "payload", "email") or _get(payload, "payload", "invitee", "email") or "").strip()
    name = str(_get(payload, "payload", "name") or _get(payload, "payload", "invitee", "name") or "").strip()
    invitee_uri = str(_get(payload, "payload", "uri") or _get(payload, "payload", "invitee", "uri") or "").strip()
    
    # Event URI: try scheduled_event.uri (new format) or event.uri (old format)
    scheduled_event = _get(payload, "payload", "scheduled_event")
    if isinstance(scheduled_event, dict):
        event_uri = str(scheduled_event.get("uri") or "").strip()
        demo_datetime = str(scheduled_event.get("start_time") or "").strip()
        demo_timezone = str(scheduled_event.get("timezone") or "").strip()
    else:
        event_uri = str(_get(payload, "payload", "event", "uri") or "").strip()
        demo_datetime = str(_get(payload, "payload", "event", "start_time") or "").strip()
        demo_timezone = str(_get(payload, "payload", "event", "timezone") or "").strip()
    
    qa = _get(payload, "payload", "questions_and_answers")
    qa_text = qa_to_text(qa)
    
    # Extract phone if available (new format: payload.payload.text_reminder_number)
    phone = str(_get(payload, "payload", "text_reminder_number") or _get(payload, "payload", "invitee", "text_reminder_number") or "").strip()
    
    # Extract tracking data (new format: payload.payload.tracking)
    tracking = _get(payload, "payload", "tracking") or _get(payload, "payload", "invitee", "tracking") or {}
    if not isinstance(tracking, dict):
        tracking = {}

    first = ""
    last = ""
    if name:
        parts = [p for p in name.split(" ") if p]
        if parts:
            first = parts[0]
            last = " ".join(parts[1:]) if len(parts) > 1 else ""
    return CalendlyLeadInfo(
        email=email,
        name=name,
        first_name=first,
        last_name=last,
        demo_datetime=demo_datetime,
        demo_timezone=demo_timezone,
        invitee_uri=invitee_uri,
        event_uri=event_uri,
        qa_text=qa_text,
        phone=phone,
        tracking=tracking,
    )


def lead_intel_to_text(intel: Any) -> str:
    """
    Converts `CalendlyLeadIntel` into a formatted text for notes.
    This is now mainly for backward compatibility - fields are mapped directly to Zoho.
    """
    parts: list[str] = []
    
    company = getattr(intel, "company_name", "") or ""
    company_type = getattr(intel, "company_type", "") or ""
    company_desc = getattr(intel, "company_description", "") or ""
    if company or company_type or company_desc:
        parts.append(f"Company: {company} ({company_type})")
        if company_desc and company_desc != "Not discussed":
            parts.append(f"Description: {company_desc}")
    
    team_size = getattr(intel, "team_size", "") or ""
    if team_size and team_size != "Not discussed":
        parts.append(f"Team Size: {team_size}")
    
    tools = getattr(intel, "tools_in_use", "") or ""
    if tools and tools != "Not discussed":
        parts.append(f"Tools in Use: {tools}")
    
    pains = getattr(intel, "stated_pain_points", "") or ""
    if pains and pains != "Not discussed":
        parts.append(f"Pain Points:\n{pains}")
    
    objectives = getattr(intel, "stated_demo_objectives", "") or ""
    if objectives and objectives != "Not discussed":
        parts.append(f"Demo Objectives:\n{objectives}")
    
    return "\n\n".join(parts).strip()


def build_zoho_lead_payload_for_calendly(
    *,
    info: CalendlyLeadInfo,
    lead_status: str,
    intel: Any,
) -> dict[str, Any]:
    """
    Build Zoho Lead payload from Calendly info and LLM-extracted intel.
    Maps all fields from the comprehensive CalendlyLeadIntel schema to Zoho fields.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    settings = get_settings()
    if not info.email:
        raise ValueError("Missing email")

    payload: dict[str, Any] = {
        "Email": info.email,
        settings.ZOHO_LEAD_STATUS_FIELD: lead_status,
        "Lead_Source": "Calendly",  # Always set Lead Source to Calendly for Calendly bookings
    }

    # Basic name fields (use LLM-extracted if available, fallback to parsed)
    first_name = getattr(intel, "first_name", "") or info.first_name or ""
    last_name = getattr(intel, "last_name", "") or info.last_name or ""
    
    if first_name:
        payload["First_Name"] = first_name
    if last_name:
        payload["Last_Name"] = last_name
    elif first_name:
        # Zoho often requires Last_Name; use company name or '.' as placeholder
        company_name = getattr(intel, "company_name", "") or ""
        payload["Last_Name"] = company_name if company_name else "."

    # Company fields
    company_name = getattr(intel, "company_name", "") or ""
    if company_name and company_name != "Not discussed":
        payload["Company"] = company_name
    
    company_website = getattr(intel, "company_website", "") or ""
    if company_website and company_website != "Not discussed" and company_website.strip():
        payload["Website"] = company_website.strip()
    
    # Phone number (from Calendly payload or LLM extraction if available in Q&A)
    phone = info.phone or getattr(intel, "phone", "") or ""
    if phone and phone.strip():
        payload["Phone"] = phone.strip()
    
    # Location fields
    country = getattr(intel, "country", "") or ""
    if country and country != "Unknown" and country != "Not discussed":
        payload["Country"] = country
    
    state_or_region = getattr(intel, "state_or_region", "") or ""
    if state_or_region and state_or_region != "Unknown" and state_or_region != "Not discussed":
        payload["State"] = state_or_region
    
    city = getattr(intel, "city", "") or ""
    if city and city != "Unknown" and city != "Not discussed":
        payload["City"] = city

    if settings.ZOHO_OWNER_ID:
        payload["Owner"] = {"id": settings.ZOHO_OWNER_ID}

    # Industry (from LLM extraction or infer from company type)
    company_type = getattr(intel, "company_type", "") or ""
    industry = getattr(intel, "industry", "") or ""
    if industry and industry != "Not discussed" and industry.strip():
        payload["Industry"] = industry.strip()
        logger.debug("Setting Industry from LLM: %s", industry.strip())
    elif company_type and company_type != "Not discussed":
        # Fallback: try to infer industry from company type
        company_type_lower = company_type.lower()
        if "agency" in company_type_lower or "design" in company_type_lower or "marketing" in company_type_lower:
            payload["Industry"] = "Marketing"
            logger.debug("Inferred Industry from company_type: Marketing")
        elif "tech" in company_type_lower or "software" in company_type_lower or "saas" in company_type_lower:
            payload["Industry"] = "Technology"
            logger.debug("Inferred Industry from company_type: Technology")
        elif "healthcare" in company_type_lower or "medical" in company_type_lower:
            payload["Industry"] = "Healthcare"
            logger.debug("Inferred Industry from company_type: Healthcare")
        elif "manufacturing" in company_type_lower or "production" in company_type_lower:
            payload["Industry"] = "Manufacturing"
            logger.debug("Inferred Industry from company_type: Manufacturing")
    
    # Referred by (from Q&A or tracking data)
    referred_by = getattr(intel, "referred_by", "") or ""
    if referred_by and referred_by != "Not discussed" and referred_by.strip():
        # Check if we have a Zoho custom field for this, otherwise use standard field if available
        if settings.ZCF_REFERRED_BY:
            payload[settings.ZCF_REFERRED_BY] = referred_by.strip()
            logger.debug("Setting Referred_by (custom field %s): %s", settings.ZCF_REFERRED_BY, referred_by.strip())
        else:
            # Try to use standard Zoho field if it exists
            payload["Referred_by"] = referred_by.strip()
            logger.debug("Setting Referred_by (standard field): %s", referred_by.strip())

    # Demo datetime (use LLM-extracted local format if available)
    # CRITICAL: Always set Demo_Date custom field if configured
    if settings.ZCF_DEMO_DATETIME:
        demo_datetime_utc = getattr(intel, "demo_datetime_utc", "") or info.demo_datetime
        if demo_datetime_utc:
            try:
                from datetime import datetime, timezone
                # Parse the UTC datetime
                dt_str = demo_datetime_utc.strip()
                
                # Handle case where string has both timezone offset and Z (e.g., "2025-12-20T01:23:58+00:00Z")
                # Remove Z if there's already a timezone offset
                if dt_str.endswith("Z") and ("+" in dt_str or dt_str.count("-") > 2):
                    # Has both offset and Z - remove Z
                    dt_str = dt_str[:-1]
                elif dt_str.endswith("Z"):
                    # Only has Z, no offset - replace with +00:00
                    dt_str = dt_str[:-1] + "+00:00"
                
                dt = datetime.fromisoformat(dt_str)
                
                # Zoho datetime format: Try ISO 8601 with timezone offset (with colon)
                # Format: YYYY-MM-DDTHH:MM:SS+00:00 or YYYY-MM-DDTHH:MM:SSZ
                if dt.tzinfo:
                    # Ensure we're working with UTC
                    dt_utc = dt.astimezone(timezone.utc)
                    # Try ISO 8601 format with timezone offset (with colon)
                    formatted = dt_utc.strftime('%Y-%m-%dT%H:%M:%S+00:00')
                else:
                    # No timezone, assume UTC - use Z suffix
                    formatted = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                
                payload[settings.ZCF_DEMO_DATETIME] = formatted
                logger.debug("Setting Demo_Date: %s", formatted)
            except Exception as e:
                logger.warning("Skipping Demo_Date field due to datetime format issue: %s", e)
    
    if settings.ZCF_DEMO_TIMEZONE and info.demo_timezone:
        payload[settings.ZCF_DEMO_TIMEZONE] = info.demo_timezone
    
    # Map LLM-extracted fields to Zoho custom fields
    def set_if(field: str, value: str) -> None:
        """Helper to set Zoho field if value exists and is not 'Not discussed'"""
        if field and value and value.strip() and value != "Not discussed":
            payload[field] = value.strip()
            logger.debug("Setting Zoho field %s = %s", field, value[:100] + "..." if len(value) > 100 else value)
    
    # Map all the fields from the image/schema
    set_if(settings.ZCF_PAIN_POINTS, getattr(intel, "stated_pain_points", "") or "")
    set_if(settings.ZCF_TEAM_MEMBERS, getattr(intel, "team_size", "") or "")
    set_if(settings.ZCF_TOOLS_CURRENTLY_USED, getattr(intel, "tools_in_use", "") or "")
    set_if(settings.ZCF_DEMO_OBJECTIVES, getattr(intel, "stated_demo_objectives", "") or "")
    set_if(settings.ZCF_DEMO_FOCUS_RECOMMENDATION, getattr(intel, "demo_focus_recommendations", "") or "")
    set_if(settings.ZCF_DISCOVERY_QUESTIONS, getattr(intel, "recommended_discovery_questions", "") or "")
    set_if(settings.ZCF_SALES_REP_CHEAT_SHEET, getattr(intel, "sales_rep_cheat_sheet", "") or "")
    
    # Additional fields
    set_if(settings.ZCF_COMPANY_TYPE, getattr(intel, "company_type", "") or "")
    set_if(settings.ZCF_COMPANY_DESCRIPTION, getattr(intel, "company_description", "") or "")
    set_if(settings.ZCF_QUALIFICATION_GAPS, getattr(intel, "qualification_gaps", "") or "")
    set_if(settings.ZCF_BANT_BUDGET, getattr(intel, "bant_budget_signal", "") or "")
    set_if(settings.ZCF_BANT_AUTHORITY, getattr(intel, "bant_authority_signal", "") or "")
    set_if(settings.ZCF_BANT_NEED, getattr(intel, "bant_need_signal", "") or "")
    set_if(settings.ZCF_BANT_TIMING, getattr(intel, "bant_timing_signal", "") or "")
    
    # Legacy fields (for backward compatibility)
    if settings.ZCF_CALENDLY_INVITEE_URI and info.invitee_uri:
        payload[settings.ZCF_CALENDLY_INVITEE_URI] = info.invitee_uri
    if settings.ZCF_CALENDLY_EVENT_URI and info.event_uri:
        payload[settings.ZCF_CALENDLY_EVENT_URI] = info.event_uri
    if settings.ZCF_CALENDLY_QA and info.qa_text:
        payload[settings.ZCF_CALENDLY_QA] = info.qa_text

    logger.info("📤 Built Zoho payload with %d fields from Calendly intel", len(payload))
    return payload



