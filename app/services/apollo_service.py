from __future__ import annotations

import json
import logging
from typing import Optional

import httpx

from app.schemas.apollo import ApolloCompanyData, ApolloPersonData
from app.services.redis_client import get_redis_str
from app.settings import get_settings

logger = logging.getLogger(__name__)


class ApolloError(Exception):
    pass


class ApolloTransientError(ApolloError):
    """Transient Apollo errors (rate limits, timeouts) that should be retried."""


def _apollo_headers() -> dict[str, str]:
    settings = get_settings()
    return {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": settings.APOLLO_API_KEY,
    }


def _cache_key_person(email: str) -> str:
    return f"apollo:person:{email.lower()}"


def _cache_key_company(domain: str) -> str:
    return f"apollo:company:{domain.lower()}"


def enrich_person(email: str, *, use_cache: bool = True) -> Optional[ApolloPersonData]:
    """
    Enrich person data from Apollo.io People Enrichment API.

    https://apolloio.github.io/apollo-api-docs/#people-enrichment
    """
    settings = get_settings()

    if not settings.APOLLO_API_KEY:
        logger.warning("APOLLO_API_KEY not set, skipping person enrichment")
        return None

    # Check cache first
    if use_cache:
        r = get_redis_str()
        cache_key = _cache_key_person(email)
        cached = r.get(cache_key)
        if cached:
            logger.info("Apollo person cache hit: %s", email)
            try:
                return ApolloPersonData.model_validate_json(cached)
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to parse cached Apollo person data: %s", e)

    url = "https://api.apollo.io/v1/people/match"
    payload = {
        "email": email,
    }

    logger.info("Calling Apollo person enrichment API: %s", email)

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=_apollo_headers(), json=payload)
            resp.raise_for_status()
            body = resp.json()
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        raise ApolloTransientError(str(e)) from e
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        if code == 429 or 500 <= code <= 599:
            raise ApolloTransientError(f"Apollo HTTP {code}") from e
        raise ApolloError(f"Apollo person enrichment failed: HTTP {code}") from e

    # Parse Apollo response
    person_raw = body.get("person", {})
    if not person_raw:
        logger.warning("Apollo person enrichment returned no data for: %s", email)
        return None

    # Extract employment (current job)
    employment = person_raw.get("employment_history", [])
    current_title = person_raw.get("title", "")
    current_seniority = person_raw.get("seniority", "")

    # Extract phone numbers
    phone_numbers = []
    if person_raw.get("phone_numbers"):
        phone_numbers = [p.get("sanitized_number", "") for p in person_raw.get("phone_numbers", []) if p.get("sanitized_number")]

    person_data = ApolloPersonData(
        email=email,
        first_name=person_raw.get("first_name", ""),
        last_name=person_raw.get("last_name", ""),
        title=current_title,
        seniority=current_seniority,
        department=person_raw.get("departments", [""])[0] if person_raw.get("departments") else "",
        linkedin_url=person_raw.get("linkedin_url", ""),
        phone_numbers=phone_numbers,
        employment_history=employment,
    )

    # Cache result
    if use_cache:
        r = get_redis_str()
        cache_key = _cache_key_person(email)
        ttl = settings.APOLLO_CACHE_TTL_DAYS * 24 * 60 * 60
        r.set(cache_key, person_data.model_dump_json(), ex=ttl)
        logger.info("Cached Apollo person data: %s", email)

    logger.info("Apollo person enrichment successful: %s (title: %s, seniority: %s)", email, current_title, current_seniority)
    return person_data


def extract_company_from_person(person_raw: dict) -> Optional[ApolloCompanyData]:
    """
    Extract company data from Apollo person enrichment response.

    Useful fallback when organization enrichment endpoint is not accessible.
    Person API often includes current organization data.
    """
    # Get current organization from employment history or organization field
    org_raw = person_raw.get("organization")
    if not org_raw and person_raw.get("employment_history"):
        # Try to get from current employment
        for job in person_raw["employment_history"]:
            if job.get("current"):
                org_raw = job.get("organization")
                break

    if not org_raw:
        return None

    # Extract basic company info from organization object
    domain = org_raw.get("primary_domain", "")
    if not domain:
        return None

    employee_count_str = ""
    if org_raw.get("estimated_num_employees"):
        employee_count_str = str(org_raw["estimated_num_employees"])

    company_data = ApolloCompanyData(
        name=org_raw.get("name", ""),
        domain=domain,
        employee_count=employee_count_str,
        revenue="",  # Not typically in person response
        industry=org_raw.get("industry", ""),
        founded_year=str(org_raw.get("founded_year", "")),
        funding_stage="",  # Not typically in person response
        funding_total="",  # Not typically in person response
        technologies=[],  # Not typically in person response
        linkedin_url=org_raw.get("linkedin_url", ""),
        twitter_url=org_raw.get("twitter_url", ""),
        facebook_url=org_raw.get("facebook_url", ""),
        city="",
        state="",
        country="",
    )

    logger.info("Extracted basic company data from person enrichment: %s", domain)
    return company_data


def enrich_company(domain: str, *, use_cache: bool = True) -> Optional[ApolloCompanyData]:
    """
    Enrich company data from Apollo.io Organization Enrichment API.

    https://apolloio.github.io/apollo-api-docs/#organization-enrichment

    Note: This endpoint requires Apollo API tier with organization enrichment access.
    Returns None if not accessible.
    """
    settings = get_settings()

    if not settings.APOLLO_API_KEY:
        logger.warning("APOLLO_API_KEY not set, skipping company enrichment")
        return None

    # Check cache first
    if use_cache:
        r = get_redis_str()
        cache_key = _cache_key_company(domain)
        cached = r.get(cache_key)
        if cached:
            logger.info("Apollo company cache hit: %s", domain)
            try:
                return ApolloCompanyData.model_validate_json(cached)
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to parse cached Apollo company data: %s", e)

    url = "https://api.apollo.io/api/v1/organizations/enrich"
    params = {
        "domain": domain,
    }

    logger.info("Calling Apollo company enrichment API: %s", domain)

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url, headers=_apollo_headers(), params=params)
            resp.raise_for_status()
            body = resp.json()
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        raise ApolloTransientError(str(e)) from e
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        if code == 429 or 500 <= code <= 599:
            raise ApolloTransientError(f"Apollo HTTP {code}") from e
        # 403 often means API tier doesn't include company enrichment
        if code == 403:
            try:
                error_body = e.response.json()
                error_msg = error_body.get("error", "Unknown error")
                logger.warning("Apollo company enrichment not available: %s (consider upgrading API tier)", error_msg)
            except Exception:  # noqa: BLE001
                logger.warning("Apollo company enrichment returned 403 (API tier may not include this endpoint)")
            return None
        raise ApolloError(f"Apollo company enrichment failed: HTTP {code}") from e

    # Parse Apollo response
    org_raw = body.get("organization", {})
    if not org_raw:
        logger.warning("Apollo company enrichment returned no data for: %s", domain)
        return None

    # Extract employee count range
    employee_count_str = ""
    if org_raw.get("estimated_num_employees"):
        employee_count_str = str(org_raw["estimated_num_employees"])

    # Extract revenue range (if available)
    revenue_str = ""
    if org_raw.get("estimated_annual_revenue"):
        revenue_str = org_raw["estimated_annual_revenue"]

    # Extract technologies
    technologies = []
    if org_raw.get("technologies"):
        technologies = [tech.get("name", "") for tech in org_raw.get("technologies", []) if tech.get("name")]

    # Extract funding info
    funding_stage = ""
    funding_total = ""
    if org_raw.get("funding_stage"):
        funding_stage = org_raw["funding_stage"]
    if org_raw.get("total_funding"):
        funding_total = f"${org_raw['total_funding'] / 1_000_000:.1f}M"

    company_data = ApolloCompanyData(
        name=org_raw.get("name", ""),
        domain=domain,
        employee_count=employee_count_str,
        revenue=revenue_str,
        industry=org_raw.get("industry", ""),
        founded_year=str(org_raw.get("founded_year", "")),
        funding_stage=funding_stage,
        funding_total=funding_total,
        technologies=technologies,
        linkedin_url=org_raw.get("linkedin_url", ""),
        twitter_url=org_raw.get("twitter_url", ""),
        facebook_url=org_raw.get("facebook_url", ""),
        city=org_raw.get("city", ""),
        state=org_raw.get("state", ""),
        country=org_raw.get("country", ""),
    )

    # Cache result
    if use_cache:
        r = get_redis_str()
        cache_key = _cache_key_company(domain)
        ttl = settings.APOLLO_CACHE_TTL_DAYS * 24 * 60 * 60
        r.set(cache_key, company_data.model_dump_json(), ex=ttl)
        logger.info("Cached Apollo company data: %s", domain)

    logger.info(
        "Apollo company enrichment successful: %s (employees: %s, industry: %s)",
        domain,
        employee_count_str,
        company_data.industry,
    )
    return company_data
