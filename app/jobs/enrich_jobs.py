from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.jobs.retry import JobContext, run_event_job
from app.schemas.apollo import EnrichmentResult
from app.services.apollo_service import ApolloTransientError, enrich_company, enrich_person
from app.services.brandfetch_service import fetch_company_logo
from app.services.event_store_service import load_event
from app.services.scraper_service import ScraperTransientError, scrape_website
from app.services.zoho_service import create_note, upsert_lead_by_email, upload_lead_photo
from app.settings import get_settings
from app.util.text_format import extract_domain_from_email

logger = logging.getLogger(__name__)


def _build_zoho_payload_from_enrichment(enrichment: EnrichmentResult, email: str) -> dict[str, str]:
    """Build Zoho Lead payload from enrichment result (for create or update)"""
    settings = get_settings()
    payload = {}

    # Ensure email is always set
    payload["Email"] = email

    # Apollo Person fields (including name fields for lead creation)
    if enrichment.person_data:
        person = enrichment.person_data
        # Add name fields for lead creation
        if person.first_name:
            payload["First_Name"] = person.first_name
        if person.last_name:
            payload["Last_Name"] = person.last_name
        # Add enrichment fields
        if person.title and settings.ZCF_APOLLO_JOB_TITLE:
            payload[settings.ZCF_APOLLO_JOB_TITLE] = person.title
        if person.seniority and settings.ZCF_APOLLO_SENIORITY:
            payload[settings.ZCF_APOLLO_SENIORITY] = person.seniority
        if person.department and settings.ZCF_APOLLO_DEPARTMENT:
            payload[settings.ZCF_APOLLO_DEPARTMENT] = person.department
        if person.linkedin_url and settings.ZCF_APOLLO_LINKEDIN_URL:
            payload[settings.ZCF_APOLLO_LINKEDIN_URL] = person.linkedin_url
        if person.phone_numbers and settings.ZCF_APOLLO_PHONE:
            payload[settings.ZCF_APOLLO_PHONE] = person.phone_numbers[0]

    # Apollo Company fields (including company name for lead creation)
    if enrichment.company_data:
        company = enrichment.company_data
        # Add company name for lead creation
        if company.name:
            payload["Company"] = company.name
        # Add enrichment fields
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
            payload[settings.ZCF_APOLLO_TECH_STACK] = ", ".join(company.technologies[:10])

    # Ensure minimum required fields for lead creation (Zoho requires Last_Name)
    if not payload.get("Last_Name"):
        # Extract domain from email as fallback
        domain = email.split("@")[1] if "@" in email else "Unknown"
        payload["Last_Name"] = domain.split(".")[0].title()
        logger.info("No last name found in enrichment, using domain as Last_Name: %s", payload["Last_Name"])

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
        lines.append("🌐 WEBSITE RESEARCH")
        lines.append("")
        if web.value_proposition:
            lines.append(f"What they do:")
            lines.append(web.value_proposition)
            lines.append("")
        if web.target_market:
            lines.append(f"Who they sell to:")
            lines.append(web.target_market)
            lines.append("")
        if web.products_services:
            lines.append(f"Their products/services:")
            lines.append(web.products_services)
            lines.append("")
        if web.pricing_model:
            lines.append(f"Pricing:")
            lines.append(web.pricing_model)
            lines.append("")
        if web.recent_news:
            lines.append(f"📰 What's new:")
            lines.append(web.recent_news)
            lines.append("")
        if web.growth_signals:
            lines.append(f"🚀 Growth signals:")
            lines.append(web.growth_signals)
            lines.append("")
        if web.key_pain_points:
            lines.append(f"Their customers' pain points:")
            lines.append(web.key_pain_points)
            lines.append("")
        if web.competitors_mentioned:
            lines.append(f"Competitors they mention:")
            lines.append(web.competitors_mentioned)
            lines.append("")

        if web.sales_insights:
            lines.append("🎯 HOW TO APPROACH THIS DEMO")
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
    """Process manual enrichment request - creates lead if doesn't exist"""
    ev = load_event(ctx.event_id)
    if ev is None:
        raise ValueError("Event not found")

    # Extract email from payload
    email = ev.payload.get("email")
    lead_id = ev.payload.get("lead_id")

    if not email:
        raise ValueError("Email is required in enrichment request")

    # Perform enrichment
    enrichment = enrich_lead_by_email(email)

    if not enrichment.data_sources:
        logger.warning("No enrichment data found for: %s", email)
        # Still create lead with minimal data if no enrichment found
        minimal_payload = {
            "Email": email,
            "Last_Name": email.split("@")[0].title() if "@" in email else "Lead",
        }
        lead_id_str = upsert_lead_by_email(email, minimal_payload)
        logger.info("Created minimal lead (no enrichment data): %s (lead_id: %s)", email, lead_id_str)
        return

    # Build Zoho payload from enrichment (includes name, company, and enrichment fields)
    zoho_payload = _build_zoho_payload_from_enrichment(enrichment, email)

    # Upsert lead (creates if doesn't exist, updates if exists)
    lead_id_str = upsert_lead_by_email(email, zoho_payload)
    logger.info("Lead upserted (created or updated): %s (lead_id: %s)", email, lead_id_str)

    # Create enrichment note
    note_title = "Lead Enrichment (Apollo + Website)"
    note_content = _build_enrichment_note(enrichment)
    create_note(lead_id_str, note_title, note_content)

    # Fetch and upload company logo (best effort)
    if enrichment.company_data and enrichment.company_data.domain:
        try:
            logo_data = fetch_company_logo(enrichment.company_data.domain)
            if logo_data:
                upload_lead_photo(lead_id_str, logo_data, filename=f"{enrichment.company_data.domain}_logo.png")
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to upload logo for %s: %s", email, e)

    logger.info("Lead enrichment complete: %s (%d sources)", email, len(enrichment.data_sources))


def process_manual_enrich_job(event_id: str) -> None:
    """Entry point for manual enrichment job"""
    run_event_job(event_id, _process_manual_enrich)
