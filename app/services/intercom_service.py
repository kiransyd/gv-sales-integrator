from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.settings import get_settings

logger = logging.getLogger(__name__)


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
    # Location data
    country: str
    city: str
    region: str
    # Device/browser info
    browser: str
    os: str
    # Intercom metadata
    intercom_url: str
    signed_up_at: str
    last_seen_at: str


def parse_intercom_contact_info(payload: dict[str, Any]) -> IntercomContactInfo:
    """
    Extract contact information from Intercom webhook payload.

    Expected structure for contact.user.tag.created / contact.lead.tag.created:
    {
        "type": "notification_event",
        "topic": "contact.user.tag.created",
        "data": {
            "item": {
                "type": "contact_tag",
                "tag": {...},
                "contact": {
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
    }
    """
    item = _get(payload, "data", "item") or {}

    # Check if this is the new structure with contact_tag
    item_type = item.get("type", "")
    if item_type == "contact_tag":
        # Contact is nested under item.contact
        item = item.get("contact", {})
    # Otherwise, item is the contact directly (fallback)

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

    # Extract location data
    location = item.get("location") or {}
    country = str(location.get("country") or "").strip()
    city = str(location.get("city") or "").strip()
    region = str(location.get("region") or "").strip()

    # Extract device/browser info
    browser = str(item.get("browser") or "").strip()
    os = str(item.get("os") or "").strip()

    # Intercom metadata
    workspace_id = item.get("workspace_id", "")
    intercom_url = f"https://app.intercom.com/a/apps/{workspace_id}/users/{contact_id}/all-conversations" if workspace_id and contact_id else ""
    signed_up_at = str(item.get("signed_up_at") or "").strip()
    last_seen_at = str(item.get("last_seen_at") or "").strip()

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
        country=country,
        city=city,
        region=region,
        browser=browser,
        os=os,
        intercom_url=intercom_url,
        signed_up_at=signed_up_at,
        last_seen_at=last_seen_at,
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

    # Location data
    if info.country:
        payload["Country"] = info.country
    if info.city:
        payload["City"] = info.city
    if info.region:
        payload["State"] = info.region

    # Extract valuable custom attributes
    if info.custom_attributes:
        # GoVisually-specific fields that sales reps care about
        plan_type = info.custom_attributes.get("plan_type", "")
        if plan_type:
            payload["Description"] = payload.get("Description", "") + f"\nPlan Type: {plan_type}"

        gv_version = info.custom_attributes.get("gv_version", "")
        if gv_version:
            payload["Description"] = payload.get("Description", "") + f"\nGoVisually Version: {gv_version}"

        user_type = info.custom_attributes.get("user_type", "")
        if user_type:
            payload["Description"] = payload.get("Description", "") + f"\nUser Type: {user_type}"

        # Tools being used (valuable competitive intel)
        pm_tool = info.custom_attributes.get("project_management_tool_used", "")
        proofing_tool = info.custom_attributes.get("proofing_tool_used", "")
        if pm_tool or proofing_tool:
            tools_info = []
            if pm_tool:
                tools_info.append(f"PM Tool: {pm_tool}")
            if proofing_tool:
                tools_info.append(f"Proofing Tool: {proofing_tool}")
            payload["Description"] = payload.get("Description", "") + f"\n{', '.join(tools_info)}"

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

    # Intercom link (clickable)
    if info.intercom_url:
        parts.append(f"[View in Intercom]({info.intercom_url})")

    parts.append(f"\n**Contact ID:** {info.contact_id}")
    if info.external_id:
        parts.append(f"**External ID:** {info.external_id}")

    parts.append(f"\n**Qualifying Tags:** {', '.join(tags)}")

    # Engagement metrics
    if info.signed_up_at or info.last_seen_at:
        parts.append("\n### Engagement")
        if info.signed_up_at:
            parts.append(f"**Signed Up:** {info.signed_up_at}")
        if info.last_seen_at:
            parts.append(f"**Last Seen:** {info.last_seen_at}")

    # Location
    if info.country or info.city or info.region:
        parts.append("\n### Location")
        location_parts = []
        if info.city:
            location_parts.append(info.city)
        if info.region:
            location_parts.append(info.region)
        if info.country:
            location_parts.append(info.country)
        parts.append(", ".join(location_parts))

    # Device/Browser info
    if info.browser or info.os:
        parts.append("\n### Device Information")
        if info.browser:
            parts.append(f"**Browser:** {info.browser}")
        if info.os:
            parts.append(f"**OS:** {info.os}")

    # Company information
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

    # GoVisually-specific custom attributes (highlighted)
    if info.custom_attributes:
        parts.append("\n### GoVisually Usage")

        # Highlight key fields
        important_fields = {
            "plan_type": "Plan Type",
            "gv_version": "Version",
            "user_type": "User Type",
            "channel": "Initial Channel",
            "main_goal": "Main Goal",
            "job_role": "Job Role",
        }

        for key, label in important_fields.items():
            value = info.custom_attributes.get(key)
            if value:
                parts.append(f"**{label}:** {value}")

        # Tools being used (competitive intel)
        pm_tool = info.custom_attributes.get("project_management_tool_used")
        proofing_tool = info.custom_attributes.get("proofing_tool_used")
        if pm_tool or proofing_tool:
            parts.append("\n### Tools Currently Using")
            if pm_tool:
                parts.append(f"**Project Management:** {pm_tool}")
            if proofing_tool:
                parts.append(f"**Proofing Tool:** {proofing_tool}")

        # Other custom attributes
        other_attrs = {k: v for k, v in info.custom_attributes.items()
                       if k not in important_fields and k not in ["project_management_tool_used", "proofing_tool_used"] and v}

        if other_attrs:
            parts.append("\n### Other Attributes")
            for key, value in other_attrs.items():
                parts.append(f"**{key}:** {value}")

    return "\n".join(parts)


def get_primary_contact_for_company(company_id: str) -> dict | None:
    """
    Get the primary contact (user_type=primary) for a company.

    Args:
        company_id: Intercom company ID

    Returns:
        Contact data dict if found, None otherwise
    """
    import httpx

    from app.settings import get_settings

    settings = get_settings()

    if not settings.INTERCOM_API_KEY:
        logger.error("INTERCOM_API_KEY not configured")
        return None

    headers = {
        "Authorization": f"Bearer {settings.INTERCOM_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Intercom-Version": "2.11",
    }

    try:
        # Search for contacts in this company with user_type=primary
        search_payload = {
            "query": {
                "operator": "AND",
                "value": [
                    {
                        "field": "role",
                        "operator": "=",
                        "value": "user",
                    },
                    {
                        "field": "custom_attributes.user_type",
                        "operator": "=",
                        "value": "primary",
                    },
                ],
            },
        }

        response = httpx.post(
            "https://api.intercom.io/contacts/search",
            headers=headers,
            json=search_payload,
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        contacts = data.get("data", [])

        # Filter by company ID (search API doesn't support company filter directly)
        for contact in contacts:
            companies = contact.get("companies", {}).get("data", [])
            for company in companies:
                if company.get("id") == company_id:
                    logger.info("Found primary contact: %s for company %s", contact.get("email"), company_id)
                    return contact

        # Fallback: If no primary user, get first contact from company
        logger.warning("No primary contact found for company %s, fetching first contact", company_id)

        # Get company to find associated contacts
        response = httpx.get(
            f"https://api.intercom.io/companies/{company_id}",
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()

        # Note: Company object doesn't include full contact list
        # We'd need to search contacts by company which isn't straightforward
        # For now, return None if no primary user found
        logger.warning("Could not find primary contact for company %s", company_id)
        return None

    except httpx.HTTPStatusError as e:
        logger.error("Failed to fetch contact for company %s: %s", company_id, e.response.text)
        return None
    except Exception as e:  # noqa: BLE001
        logger.error("Error fetching contact for company %s: %s", company_id, e)
        return None


def get_any_contact_for_company(company_id: str) -> dict | None:
    """
    Get ANY contact for a company (fallback when primary user not found).

    Searches for any user role contact associated with the company.
    This is used when no primary contact is found.

    Args:
        company_id: Intercom company ID

    Returns:
        Contact data dict if found, None otherwise
    """
    import httpx

    from app.settings import get_settings

    settings = get_settings()

    if not settings.INTERCOM_API_KEY:
        logger.error("INTERCOM_API_KEY not configured")
        return None

    headers = {
        "Authorization": f"Bearer {settings.INTERCOM_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Intercom-Version": "2.11",
    }

    try:
        # Search for any user role contacts (not leads/visitors)
        search_payload = {
            "query": {
                "field": "role",
                "operator": "=",
                "value": "user",
            },
        }

        response = httpx.post(
            "https://api.intercom.io/contacts/search",
            headers=headers,
            json=search_payload,
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        contacts = data.get("data", [])

        # Filter by company ID (search API doesn't support company filter directly)
        for contact in contacts:
            companies = contact.get("companies", {}).get("data", [])
            for company in companies:
                if company.get("id") == company_id:
                    logger.info(
                        "Found fallback contact: %s (user_type: %s) for company %s",
                        contact.get("email"),
                        contact.get("custom_attributes", {}).get("user_type", "unknown"),
                        company_id,
                    )
                    return contact

        logger.warning("Could not find any contacts for company %s", company_id)
        return None

    except httpx.HTTPStatusError as e:
        logger.error("Failed to fetch any contact for company %s: %s", company_id, e.response.text)
        return None
    except Exception as e:  # noqa: BLE001
        logger.error("Error fetching any contact for company %s: %s", company_id, e)
        return None
