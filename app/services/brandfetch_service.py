from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.settings import get_settings

logger = logging.getLogger(__name__)


class BrandFetchError(Exception):
    """BrandFetch API errors"""


def fetch_company_logo(domain: str) -> Optional[bytes]:
    """
    Fetch company logo from BrandFetch API.

    Returns the logo image as bytes (PNG/JPEG format), or None if not found.

    Args:
        domain: Company domain (e.g., "nike.com", "apple.com")

    Returns:
        bytes: Logo image data, or None if not found
    """
    settings = get_settings()

    if not settings.BRAND_FETCH_API:
        logger.warning("BRAND_FETCH_API not configured - skipping logo fetch")
        return None

    # Clean domain (remove protocol, www, trailing slashes)
    clean_domain = domain.strip().lower()
    clean_domain = clean_domain.replace("https://", "").replace("http://", "")
    clean_domain = clean_domain.replace("www.", "")
    clean_domain = clean_domain.rstrip("/")

    if not clean_domain:
        logger.warning("Empty domain provided")
        return None

    # BrandFetch API endpoint
    api_url = f"https://api.brandfetch.io/v2/brands/{clean_domain}"

    headers = {
        "Authorization": f"Bearer {settings.BRAND_FETCH_API}",
        "Accept": "application/json",
    }

    try:
        logger.info("Fetching logo from BrandFetch: %s", clean_domain)

        # Get brand data
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(api_url, headers=headers)
            resp.raise_for_status()
            brand_data = resp.json()

        # Extract logo URL from response
        # BrandFetch returns logos array with different formats/sizes
        logos = brand_data.get("logos", [])
        if not logos:
            logger.info("No logos found for domain: %s", clean_domain)
            return None

        # Prefer the first logo (usually the primary/largest)
        logo_entry = logos[0]
        logo_formats = logo_entry.get("formats", [])

        if not logo_formats:
            logger.warning("Logo found but no formats available: %s", clean_domain)
            return None

        # Prefer PNG format, fallback to first available
        logo_url = None
        for fmt in logo_formats:
            if fmt.get("format") == "png":
                logo_url = fmt.get("src")
                break

        if not logo_url and logo_formats:
            # Fallback to first format
            logo_url = logo_formats[0].get("src")

        if not logo_url:
            logger.warning("Could not extract logo URL from BrandFetch response")
            return None

        logger.info("Downloading logo from: %s", logo_url)

        # Download the logo image
        with httpx.Client(timeout=15.0) as client:
            img_resp = client.get(logo_url)
            img_resp.raise_for_status()

            # Verify it's an image
            content_type = img_resp.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                logger.warning("Downloaded content is not an image: %s", content_type)
                return None

            # Check size (Zoho limit is 10 MB)
            img_size = len(img_resp.content)
            if img_size > 10 * 1024 * 1024:
                logger.warning("Logo too large (%d bytes) - Zoho limit is 10 MB", img_size)
                return None

            logger.info("Successfully fetched logo for %s (%d bytes, %s)", clean_domain, img_size, content_type)
            return img_resp.content

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.info("No brand found in BrandFetch for domain: %s", clean_domain)
        else:
            logger.warning("BrandFetch API error for %s: HTTP %d", clean_domain, e.response.status_code)
        return None
    except httpx.TimeoutException:
        logger.warning("BrandFetch request timed out for domain: %s", clean_domain)
        return None
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to fetch logo for %s: %s", clean_domain, e)
        return None
