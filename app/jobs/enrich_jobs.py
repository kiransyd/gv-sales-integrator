from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.jobs.retry import JobContext, run_event_job
from app.schemas.apollo import EnrichmentResult
from app.services.apollo_service import ApolloTransientError, enrich_company, enrich_person
from app.services.event_store_service import load_event
from app.services.scraper_service import ScraperTransientError, scrape_website
from app.services.zoho_service import create_note, find_lead_by_email, update_lead
from app.settings import get_settings
from app.util.text_format import extract_domain_from_email

logger = logging.getLogger(__name__)


def _build_zoho_payload_from_enrichment(enrichment: EnrichmentResult) -> dict[str, str]:
    """Build Zoho Lead update payload from enrichment result"""
    settings = get_settings()
    payload = {}

    # Apollo Person fields
    if enrichment.person_data:
        person = enrichment.person_data
        if person.title and settings.ZCF_APOLLO_JOB_TITLE:
            payload[settings.ZCF_APOLLO_JOB_TITLE] = person.title
        if person.seniority and settings.ZCF_APOLLO_SENIORITY:
            payload[settings.ZCF_APOLLO_SENIORITY] = person.seniority
        if person.department and settings.ZCF_APOLLO_DEPARTMENT:
            payload[settings.ZCF_APOLLO_DEPARTMENT] = person.department
        if person.linkedin_url and settings.ZCF_APOLLO_LINKEDIN_URL:
            payload[settings.ZCF_APOLLO_LINKEDIN_URL] = person.linkedin_url
        if person.phone_numbers and settings.ZCF_APOLLO_PHONE:
            # Use first phone number
            payload[settings.ZCF_APOLLO_PHONE] = person.phone_numbers[0]

    # Apollo Company fields
    if enrichment.company_data:
        company = enrichment.company_data
        if company.employee_count and settings.ZCF_APOLLO_COMPANY_SIZE:
            payload[settings.ZCF_APOLLO_COMPANY_SIZE] = company.employee_count
        if company.revenue and settings.ZCF_APOLLO_COMPANY_REVENUE:
            payload[settings.ZCF_APOLLO_COMPANY_REVENUE] = company.revenue
        if company.industry and settings.ZCF_APOLLO_COMPANY_INDUSTRY:
            payload[settings.ZCF_APOLLO_COMPANY_INDUSTRY] = company.industry
        if company.founded_year and settings.ZCF_APOLLO_COMPANY_FOUNDED_YEAR:
            payload[settings.ZCF_APOLLO_COMPANY_FOUNDED_YEAR] = company.founded_year
        if company.funding_stage and settings.ZCF_APOLLO_COMPANY_FUNDING_STAGE:
            payload[settings.ZCF_APOLLO_COMPANY_FUNDING_STAGE] = company.funding_stage
        if company.funding_total and settings.ZCF_APOLLO_COMPANY_FUNDING_TOTAL:
            payload[settings.ZCF_APOLLO_COMPANY_FUNDING_TOTAL] = company.funding_total
        if company.technologies and settings.ZCF_APOLLO_TECH_STACK:
            # Format tech stack as comma-separated list
            payload[settings.ZCF_APOLLO_TECH_STACK] = ", ".join(company.technologies[:10])  # Limit to 10

    return payload


def _build_enrichment_note(enrichment: EnrichmentResult) -> str:
    """Build formatted note content from enrichment result"""
    lines = []
    lines.append("━" * 60)
    lines.append(f"🔍 LEAD ENRICHMENT - {datetime.now(timezone.utc).strftime('%b %d, %Y %I:%M %p UTC')}")
    lines.append("")

    # Person intel
    if enrichment.person_data:
        person = enrichment.person_data
        lines.append("👤 PERSON INTEL (Apollo)")
        if person.title:
            lines.append(f"• Job Title: {person.title}")
        if person.seniority:
            lines.append(f"• Seniority: {person.seniority}")
        if person.department:
            lines.append(f"• Department: {person.department}")
        if person.linkedin_url:
            lines.append(f"• LinkedIn: {person.linkedin_url}")
        if person.phone_numbers:
            lines.append(f"• Phone: {person.phone_numbers[0]}")
        lines.append("")

    # Company intel
    if enrichment.company_data:
        company = enrichment.company_data
        lines.append("🏢 COMPANY INTEL (Apollo)")
        if company.employee_count:
            lines.append(f"• Employees: {company.employee_count}")
        if company.revenue:
            lines.append(f"• Revenue: {company.revenue}")
        if company.industry:
            lines.append(f"• Industry: {company.industry}")
        if company.founded_year:
            lines.append(f"• Founded: {company.founded_year}")
        if company.funding_stage:
            lines.append(f"• Funding: {company.funding_stage}")
            if company.funding_total:
                lines.append(f"  Total Raised: {company.funding_total}")
        if company.technologies:
            tech_list = ", ".join(company.technologies[:8])
            lines.append(f"• Tech Stack: {tech_list}")
        lines.append("")

    # Website intelligence
    if enrichment.website_intelligence:
        web = enrichment.website_intelligence
        lines.append("🌐 WEBSITE INTELLIGENCE (AI Analysis)")
        if web.value_proposition:
            lines.append(f"• Value Prop: {web.value_proposition}")
        if web.target_market:
            lines.append(f"• Target Market: {web.target_market}")
        if web.products_services:
            lines.append(f"• Products/Services: {web.products_services}")
        if web.pricing_model:
            lines.append(f"• Pricing Model: {web.pricing_model}")
        if web.recent_news:
            lines.append(f"• Recent News: {web.recent_news}")
        if web.growth_signals:
            lines.append(f"• Growth Signals: {web.growth_signals}")
        if web.key_pain_points:
            lines.append(f"• Key Pain Points: {web.key_pain_points}")
        if web.competitors_mentioned:
            lines.append(f"• Competitors Mentioned: {web.competitors_mentioned}")
        lines.append("")

        if web.sales_insights:
            lines.append("🎯 SALES INSIGHTS")
            lines.append(web.sales_insights)
            lines.append("")

    lines.append("━" * 60)
    sources_list = ", ".join(enrichment.data_sources)
    lines.append(f"Enriched by: {sources_list}")

    return "\n".join(lines)


def enrich_lead_by_email(email: str) -> EnrichmentResult:
    """
    Enrich a lead with Apollo + Website scraping.
    Returns EnrichmentResult with all available data.
    """
    logger.info("Enriching lead: %s", email)

    enrichment = EnrichmentResult(
        enrichment_timestamp=datetime.now(timezone.utc).isoformat(),
        data_sources=[],
    )

    # Extract domain from email
    domain = extract_domain_from_email(email)
    if not domain:
        logger.warning("Could not extract domain from email: %s", email)
        return enrichment

    # Skip personal email domains
    personal_domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "me.com"]
    if domain.lower() in personal_domains:
        logger.info("Skipping enrichment for personal email domain: %s", domain)
        return enrichment

    # Enrich person with Apollo
    try:
        person_data = enrich_person(email)
        if person_data:
            enrichment.person_data = person_data
            enrichment.data_sources.append("apollo_person")
    except ApolloTransientError:
        logger.warning("Apollo person enrichment failed (transient), will retry")
        raise
    except Exception as e:  # noqa: BLE001
        logger.warning("Apollo person enrichment failed: %s", e)

    # Enrich company with Apollo
    try:
        company_data = enrich_company(domain)
        if company_data:
            enrichment.company_data = company_data
            enrichment.data_sources.append("apollo_company")
    except ApolloTransientError:
        logger.warning("Apollo company enrichment failed (transient), will retry")
        raise
    except Exception as e:  # noqa: BLE001
        logger.warning("Apollo company enrichment failed: %s", e)

    # Scrape website
    try:
        website_intel = scrape_website(domain)
        if website_intel:
            enrichment.website_intelligence = website_intel
            enrichment.data_sources.append("website")
    except ScraperTransientError:
        logger.warning("Website scraping failed (transient), will retry")
        raise
    except Exception as e:  # noqa: BLE001
        logger.warning("Website scraping failed: %s", e)

    logger.info("Enrichment complete for %s: %d data sources", email, len(enrichment.data_sources))
    return enrichment


def _process_manual_enrich(ctx: JobContext) -> None:
    """Process manual enrichment request"""
    ev = load_event(ctx.event_id)
    if ev is None:
        raise ValueError("Event not found")

    # Extract email from payload
    email = ev.payload.get("email")
    lead_id = ev.payload.get("lead_id")

    if not email:
        # If no email provided, try to fetch from Zoho using lead_id
        if lead_id:
            existing = find_lead_by_email("")  # We don't have email yet
            # This won't work - we need to fetch lead by ID first
            # For now, require email in payload
            raise ValueError("Email is required in enrichment request")
        raise ValueError("Email is required in enrichment request")

    # Perform enrichment
    enrichment = enrich_lead_by_email(email)

    if not enrichment.data_sources:
        logger.warning("No enrichment data found for: %s", email)
        return

    # Build Zoho update payload
    zoho_payload = _build_zoho_payload_from_enrichment(enrichment)

    # Update Zoho lead (or create if doesn't exist)
    existing = find_lead_by_email(email)
    if existing and isinstance(existing, dict) and existing.get("id"):
        lead_id_str = str(existing["id"])
        if zoho_payload:
            update_lead(lead_id_str, zoho_payload)
    else:
        logger.warning("Lead not found in Zoho for enrichment: %s", email)
        # Could create lead here, but for manual enrichment we expect lead to exist
        return

    # Create enrichment note
    note_title = "Lead Enrichment (Apollo + Website)"
    note_content = _build_enrichment_note(enrichment)
    create_note(lead_id_str, note_title, note_content)

    logger.info("Lead enrichment complete: %s (%d sources)", email, len(enrichment.data_sources))


def process_manual_enrich_job(event_id: str) -> None:
    """Entry point for manual enrichment job"""
    run_event_job(event_id, _process_manual_enrich)
