from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import quote

import httpx

from app.settings import get_settings

logger = logging.getLogger(__name__)


_DC_MAP: dict[str, dict[str, str]] = {
    "us": {"accounts": "zoho.com", "api": "zohoapis.com"},
    "au": {"accounts": "zoho.com.au", "api": "zohoapis.com.au"},
    "eu": {"accounts": "zoho.eu", "api": "zohoapis.eu"},
    "in": {"accounts": "zoho.in", "api": "zohoapis.in"},
}


@dataclass(frozen=True)
class ZohoToken:
    access_token: str
    expires_at_epoch: float


_token_lock = threading.Lock()
_cached_token: ZohoToken | None = None


class ZohoError(Exception):
    pass


class ZohoTransientError(ZohoError):
    """Transient Zoho errors (rate limits, timeouts) that should be retried with backoff."""


def _accounts_domain() -> str:
    settings = get_settings()
    dc = settings.ZOHO_DC.lower()
    if dc not in _DC_MAP:
        raise ZohoError(f"Unsupported ZOHO_DC: {settings.ZOHO_DC}")
    return _DC_MAP[dc]["accounts"]


def _api_domain() -> str:
    settings = get_settings()
    dc = settings.ZOHO_DC.lower()
    if dc not in _DC_MAP:
        raise ZohoError(f"Unsupported ZOHO_DC: {settings.ZOHO_DC}")
    return _DC_MAP[dc]["api"]


def _token_url() -> str:
    return f"https://accounts.{_accounts_domain()}/oauth/v2/token"


def _api_base() -> str:
    return f"https://www.{_api_domain()}/crm/v2"


def _refresh_access_token() -> ZohoToken:
    settings = get_settings()
    if not settings.ZOHO_REFRESH_TOKEN or not settings.ZOHO_CLIENT_ID or not settings.ZOHO_CLIENT_SECRET:
        raise ZohoError("Missing Zoho OAuth env vars (client id/secret/refresh token).")

    data = {
        "refresh_token": settings.ZOHO_REFRESH_TOKEN,
        "client_id": settings.ZOHO_CLIENT_ID,
        "client_secret": settings.ZOHO_CLIENT_SECRET,
        "grant_type": "refresh_token",
    }

    with httpx.Client(timeout=20.0) as client:
        resp = client.post(_token_url(), data=data)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            try:
                err_body = resp.json()
            except Exception:  # noqa: BLE001
                err_body = {"raw": resp.text[:500]}
            # Zoho sometimes returns HTTP 400 "Access Denied" when rate-limited on the token endpoint.
            if isinstance(err_body, dict):
                desc = str(err_body.get("error_description") or "").lower()
                err = str(err_body.get("error") or "").lower()
                if "too many requests" in desc or "rate" in desc and "limit" in desc or "access denied" in err:
                    raise ZohoTransientError(f"Zoho token refresh rate-limited: HTTP {resp.status_code} {err_body}") from e
            # Avoid leaking secrets; include only Zoho's error payload.
            raise ZohoError(f"Zoho token refresh failed: HTTP {resp.status_code} {err_body}") from e
        body = resp.json()

    token = body.get("access_token")
    expires_in = body.get("expires_in")
    if not token:
        raise ZohoError(f"Zoho token refresh response missing access_token: {body}")

    # expires_in is usually seconds. If missing, default to 50 minutes.
    ttl = float(expires_in) if expires_in else 50 * 60.0
    # Refresh slightly early
    return ZohoToken(access_token=token, expires_at_epoch=time.time() + ttl - 30.0)


def get_access_token() -> str:
    global _cached_token
    settings = get_settings()
    if settings.DRY_RUN:
        return "dry_run_access_token"

    # Prefer Redis-cached token to avoid hammering Zoho token endpoint across restarts/workers.
    try:
        from app.services.redis_client import get_redis_str

        r = get_redis_str()
        cached = r.get("zoho:access_token")
        if cached:
            return cached
    except Exception:  # noqa: BLE001
        cached = None

    with _token_lock:
        if _cached_token and _cached_token.expires_at_epoch > time.time():
            return _cached_token.access_token
        _cached_token = _refresh_access_token()
        # Best-effort Redis cache with TTL so multiple workers/processes reuse the same access token.
        try:
            from app.services.redis_client import get_redis_str

            r = get_redis_str()
            ttl = max(60, int(_cached_token.expires_at_epoch - time.time()))
            r.set("zoho:access_token", _cached_token.access_token, ex=ttl)
        except Exception:  # noqa: BLE001
            pass
        return _cached_token.access_token


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Zoho-oauthtoken {get_access_token()}",
        "Content-Type": "application/json",
    }


def _request(method: str, path: str, *, json_body: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    url = f"{_api_base()}{path}"
    with httpx.Client(timeout=30.0) as client:
        resp = client.request(method, url, headers=_headers(), json=json_body)
        resp.raise_for_status()
        # Zoho search endpoints may return 204 No Content when no records match.
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()


def find_lead_by_email(email: str) -> Optional[dict[str, Any]]:
    settings = get_settings()
    # In DRY_RUN, skip Zoho reads to allow end-to-end testing without requiring a valid token.
    # (Writes are already skipped elsewhere.)
    if settings.DRY_RUN:
        logger.info("DRY_RUN Zoho find_lead_by_email skipped: %s", email)
        return None

    criteria = quote(f"(Email:equals:{email})", safe="():,=")
    body = _request("GET", f"/{settings.ZOHO_LEADS_MODULE}/search?criteria={criteria}")
    data = body.get("data") or []
    if not data:
        return None
    if isinstance(data, list):
        return data[0]
    return None


def find_lead_by_company(company_name: str) -> Optional[dict[str, Any]]:
    """
    Find a Zoho lead by company name (exact match).
    
    Args:
        company_name: Company name to search for
        
    Returns:
        Lead dict if found, None otherwise
    """
    settings = get_settings()
    if settings.DRY_RUN:
        logger.info("DRY_RUN Zoho find_lead_by_company skipped: %s", company_name)
        return None

    # Search by Company field (exact match)
    criteria = quote(f'(Company:equals:"{company_name}")', safe="():,=")
    body = _request("GET", f"/{settings.ZOHO_LEADS_MODULE}/search?criteria={criteria}")
    data = body.get("data") or []
    if not data:
        return None
    if isinstance(data, list):
        # Return the first match (most recent if sorted)
        return data[0]
    return None


def list_module_fields(module_api_name: str) -> list[dict[str, Any]]:
    """
    Returns field metadata for a module, e.g. Leads.
    Zoho CRM v2: GET /settings/fields?module={module_api_name}
    """
    body = _request("GET", f"/settings/fields?module={quote(module_api_name)}")
    data = body.get("fields") or body.get("data") or []
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    return []


def create_lead(payload: dict[str, Any]) -> str:
    settings = get_settings()
    if settings.DRY_RUN:
        logger.info("DRY_RUN Zoho create_lead: %s", payload)
        return "dry_run_lead_id"

    # Log what we're sending
    logger.info("📤 Creating Zoho Lead with %d fields: %s", len(payload), list(payload.keys()))
    for key, value in payload.items():
        if key != "Email":  # Email is always there
            logger.debug("   - %s: %s", key, (str(value)[:100] + "..." if isinstance(value, str) and len(str(value)) > 100 else value))
    
    body = _request("POST", f"/{settings.ZOHO_LEADS_MODULE}", json_body={"data": [payload]})
    logger.debug("Zoho create_lead response: %s", body)
    data = (body.get("data") or [{}])[0]
    details = data.get("details") or {}
    lead_id = details.get("id")
    if not lead_id:
        # Check if there's an INVALID_DATA error for a datetime field
        error_data = body.get("data", [])
        if error_data and isinstance(error_data, list):
            for err in error_data:
                if isinstance(err, dict) and err.get("code") == "INVALID_DATA":
                    error_details = err.get("details", {})
                    if error_details.get("expected_data_type") == "datetime":
                        field_name = error_details.get("api_name", "unknown")
                        logger.warning(
                            "Zoho rejected datetime field '%s'. Removing it and retrying lead creation.",
                            field_name
                        )
                        # Remove the problematic datetime field and retry
                        if field_name in payload:
                            retry_payload = {k: v for k, v in payload.items() if k != field_name}
                            logger.info("🔄 Retrying lead creation without field '%s'", field_name)
                            return create_lead(retry_payload)
        raise ZohoError(f"Create lead response missing id: {body}")
    logger.info("✅ Zoho Lead created: %s", lead_id)
    return lead_id


def update_lead(lead_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    if settings.DRY_RUN:
        logger.info("DRY_RUN Zoho update_lead: lead_id=%s payload=%s", lead_id, payload)
        return {}

    # Log what we're sending
    logger.info("📤 Updating Zoho Lead %s with %d fields: %s", lead_id, len(payload), list(payload.keys()))
    for key, value in payload.items():
        logger.debug("   - %s: %s", key, (str(value)[:100] + "..." if isinstance(value, str) and len(str(value)) > 100 else value))
    
    response = _request("PUT", f"/{settings.ZOHO_LEADS_MODULE}/{lead_id}", json_body={"data": [payload]})
    
    # Log Zoho response for debugging
    if response.get("data"):
        data = response["data"][0] if isinstance(response["data"], list) and response["data"] else {}
        status = data.get("status", "unknown")
        if status == "success":
            logger.info("✅ Zoho update successful. lead_id=%s fields_sent=%d", lead_id, len(payload))
        else:
            logger.warning("⚠️  Zoho update status: %s. response=%s", status, response)
        
        # Check for field-level errors
        if "details" in data:
            details = data["details"]
            if isinstance(details, dict):
                api_name = details.get("api_name")
                if api_name:
                    logger.debug("Zoho updated field: %s", api_name)
    
    return response


def upsert_lead_by_email(email: str, payload: dict[str, Any]) -> str:
    existing = find_lead_by_email(email)
    if existing and isinstance(existing, dict) and existing.get("id"):
        lead_id = str(existing["id"])
        update_lead(lead_id, payload)
        return lead_id
    return create_lead(payload)


def upsert_lead_by_company(company_name: str, payload: dict[str, Any]) -> str:
    """
    Upsert a Zoho lead by company name.
    
    If a lead with this company name exists, update it.
    Otherwise, create a new lead.
    
    Important: If updating an existing lead, preserves the existing Email field
    to avoid overwriting the primary contact when multiple contacts from the same
    company trigger signals.
    
    Args:
        company_name: Company name to search for/create
        payload: Lead data to create/update
        
    Returns:
        Lead ID (existing or newly created)
    """
    existing = find_lead_by_company(company_name)
    if existing and isinstance(existing, dict) and existing.get("id"):
        lead_id = str(existing["id"])
        logger.info("Found existing lead for company %s: %s", company_name, lead_id)
        
        # Preserve existing Email if the lead already has one
        # This prevents overwriting the primary contact when multiple contacts trigger signals
        # BUT: If existing lead has no email, use the new one
        existing_email = existing.get("Email")
        if existing_email and "Email" in payload:
            logger.debug("Preserving existing email %s for lead %s (new email would be %s)", 
                        existing_email, lead_id, payload.get("Email"))
            # Remove Email from payload to preserve the existing one
            payload = {k: v for k, v in payload.items() if k != "Email"}
        elif not existing_email and "Email" in payload:
            logger.debug("Setting email %s for lead %s (lead had no email)", payload.get("Email"), lead_id)
        
        update_lead(lead_id, payload)
        return lead_id
    logger.info("Creating new lead for company: %s", company_name)
    return create_lead(payload)


def create_note(lead_id: str, note_title: str, note_content: str) -> None:
    settings = get_settings()
    if settings.DRY_RUN:
        logger.info("DRY_RUN Zoho create_note: lead_id=%s title=%s content_len=%s", lead_id, note_title, len(note_content))
        return

    payload = {
        "Note_Title": note_title,
        "Note_Content": note_content,
        "Parent_Id": lead_id,
        "se_module": settings.ZOHO_LEADS_MODULE,
    }
    _request("POST", "/Notes", json_body={"data": [payload]})


def upload_lead_photo(lead_id: str, image_data: bytes, filename: str = "logo.png") -> bool:
    """
    Upload a photo to a Zoho Lead record.

    Args:
        lead_id: Zoho Lead record ID
        image_data: Image file bytes (PNG, JPEG, JPG, GIF, BMP)
        filename: Optional filename (default: "logo.png")

    Returns:
        bool: True if upload succeeded, False otherwise

    Note:
        - Max file size: 10 MB
        - Supported formats: PNG, JPEG, JPG, GIF, BMP
        - Endpoint: POST /crm/v2/Leads/{lead_id}/photo
    """
    settings = get_settings()
    if settings.DRY_RUN:
        logger.info("DRY_RUN Zoho upload_lead_photo: lead_id=%s size=%d bytes", lead_id, len(image_data))
        return True

    # Validate size (10 MB Zoho limit)
    if len(image_data) > 10 * 1024 * 1024:
        logger.warning("Image too large (%d bytes) - Zoho limit is 10 MB", len(image_data))
        return False

    try:
        # Get access token (returns string directly)
        token = get_access_token()

        # Build URL
        url = f"{_api_base()}/{settings.ZOHO_LEADS_MODULE}/{lead_id}/photo"

        # Prepare multipart form data
        files = {"file": (filename, image_data, "image/png")}
        headers = {"Authorization": f"Zoho-oauthtoken {token}"}

        logger.info("📷 Uploading photo to Zoho Lead %s (%d bytes)", lead_id, len(image_data))

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, files=files, headers=headers)
            resp.raise_for_status()
            result = resp.json()

        # Check response
        status = result.get("status", "unknown")
        if status == "success":
            logger.info("✅ Photo uploaded successfully to Lead %s", lead_id)
            return True
        else:
            logger.warning("⚠️  Photo upload failed. status=%s response=%s", status, result)
            return False

    except httpx.HTTPStatusError as e:
        logger.warning("Zoho photo upload failed for Lead %s: HTTP %d - %s", lead_id, e.response.status_code, e.response.text[:200])
        return False
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to upload photo to Lead %s: %s", lead_id, e)
        return False


def create_task(
    *,
    lead_id: str,
    subject: str,
    due_date: str,
    description: str = "",
) -> None:
    """
    Optional helper: creates a Task related to a Lead.

    due_date: YYYY-MM-DD
    """
    settings = get_settings()
    if settings.DRY_RUN:
        logger.info("DRY_RUN Zoho create_task: lead_id=%s subject=%s due=%s", lead_id, subject, due_date)
        return

    payload = {
        "Subject": subject,
        "Due_Date": due_date,
        "What_Id": lead_id,
        "se_module": settings.ZOHO_LEADS_MODULE,
        "Description": description,
    }
    _request("POST", "/Tasks", json_body={"data": [payload]})


