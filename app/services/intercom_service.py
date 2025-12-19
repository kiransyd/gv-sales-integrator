from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.settings import get_settings


def _get(d: dict[str, Any], *keys: str) -> Any:
    """Navigate nested dict safely"""
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


@dataclass(frozen=True)
class IntercomContactInfo:
    """Extracted Intercom contact information"""
    email: str
    name: str
    first_name: str
    last_name: str
    phone: str
    contact_id: str
    external_id: str
    custom_attributes: dict[str, Any]
    company_name: str
    company_website: str
    company_size: int | None
    company_industry: str


def parse_intercom_contact_info(payload: dict[str, Any]) -> IntercomContactInfo:
    """
    Extract contact information from Intercom webhook payload.

    Expected structure for contact.tag.created:
    {
        "type": "notification_event",
        "topic": "contact.tag.created",
        "data": {
            "item": {
                "type": "contact",
                "id": "...",
                "email": "...",
                "name": "...",
                "phone": "...",
                "external_id": "...",
                "custom_attributes": {...},
                "companies": {
                    "data": [...]
                }
            }
        }
    }
    """
    item = _get(payload, "data", "item") or {}

    email = str(item.get("email") or "").strip()
    name = str(item.get("name") or "").strip()
    phone = str(item.get("phone") or "").strip()
    contact_id = str(item.get("id") or "").strip()
    external_id = str(item.get("external_id") or "").strip()
    custom_attributes = item.get("custom_attributes") or {}

    # Parse first/last name
    first = ""
    last = ""
    if name:
        parts = [p for p in name.split(" ") if p]
        if parts:
            first = parts[0]
            last = " ".join(parts[1:]) if len(parts) > 1 else ""

    # Extract company info (use first company if multiple)
    company_name = ""
    company_website = ""
    company_size = None
    company_industry = ""

    companies = _get(item, "companies", "data") or []
    if isinstance(companies, list) and len(companies) > 0:
        company = companies[0]
        company_name = str(company.get("name") or "").strip()
        company_website = str(company.get("website") or "").strip()
        company_size = company.get("size")
        company_industry = str(company.get("industry") or "").strip()

    return IntercomContactInfo(
        email=email,
        name=name,
        first_name=first,
        last_name=last,
        phone=phone,
        contact_id=contact_id,
        external_id=external_id,
        custom_attributes=custom_attributes,
        company_name=company_name,
        company_website=company_website,
        company_size=company_size,
        company_industry=company_industry,
    )


def build_zoho_lead_payload_for_intercom(
    *,
    info: IntercomContactInfo,
    lead_status: str,
    tags: list[str],
) -> dict[str, Any]:
    """
    Build Zoho Lead payload from Intercom contact info.
    Maps Intercom fields to Zoho CRM fields.
    """
    import logging
    logger = logging.getLogger(__name__)

    settings = get_settings()
    if not info.email:
        raise ValueError("Missing email")

    payload: dict[str, Any] = {
        "Email": info.email,
        settings.ZOHO_LEAD_STATUS_FIELD: lead_status,
        "Lead_Source": "Intercom",  # Always set Lead Source to Intercom
    }

    # Basic name fields
    if info.first_name:
        payload["First_Name"] = info.first_name
    if info.last_name:
        payload["Last_Name"] = info.last_name
    elif info.first_name:
        # Zoho often requires Last_Name; use company name or '.' as placeholder
        payload["Last_Name"] = info.company_name if info.company_name else "."

    # Company fields
    if info.company_name:
        payload["Company"] = info.company_name

    if info.company_website:
        payload["Website"] = info.company_website

    # Phone number
    if info.phone:
        payload["Phone"] = info.phone

    # Industry
    if info.company_industry:
        payload["Industry"] = info.company_industry

    # Company size
    if info.company_size:
        payload["No_of_Employees"] = info.company_size

    if settings.ZOHO_OWNER_ID:
        payload["Owner"] = {"id": settings.ZOHO_OWNER_ID}

    logger.info("📤 Built Zoho payload with %d fields from Intercom contact", len(payload))
    logger.debug("Intercom tags that triggered creation: %s", tags)

    return payload


def format_intercom_note_content(
    *,
    info: IntercomContactInfo,
    tags: list[str],
) -> str:
    """
    Format Intercom contact information into a note for Zoho.
    """
    parts = []

    parts.append("## Intercom Contact Qualified")
    parts.append(f"**Contact ID:** {info.contact_id}")
    if info.external_id:
        parts.append(f"**External ID:** {info.external_id}")

    parts.append(f"\n**Qualifying Tags:** {', '.join(tags)}")

    if info.company_name or info.company_website:
        parts.append("\n### Company Information")
        if info.company_name:
            parts.append(f"**Name:** {info.company_name}")
        if info.company_website:
            parts.append(f"**Website:** {info.company_website}")
        if info.company_size:
            parts.append(f"**Size:** {info.company_size} employees")
        if info.company_industry:
            parts.append(f"**Industry:** {info.company_industry}")

    # Custom attributes
    if info.custom_attributes:
        parts.append("\n### Custom Attributes")
        for key, value in info.custom_attributes.items():
            if value:
                parts.append(f"**{key}:** {value}")

    return "\n".join(parts)
