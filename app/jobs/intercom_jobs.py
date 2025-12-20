from __future__ import annotations

import logging

from app.jobs.retry import JobContext, run_event_job
from app.services.event_store_service import load_event
from app.services.intercom_service import (
    build_zoho_lead_payload_for_intercom,
    format_intercom_note_content,
    parse_intercom_contact_info,
)
from app.services.slack_service import notify_support_qualified
from app.services.zoho_service import create_note, update_lead, upsert_lead_by_email
from app.settings import get_settings

logger = logging.getLogger(__name__)


def _auto_enrich_intercom_lead(email: str, lead_id: str, company: str = "") -> None:
    """
    Auto-enrich Intercom lead with Apollo + Website intelligence (if enabled).
    This is a best-effort enrichment - failures are logged but don't fail the main job.

    Args:
        email: Lead email address
        lead_id: Zoho Lead ID
        company: Company name (optional, for Slack notifications)
    """
    from app.jobs.enrich_jobs import (
        _build_enrichment_note,
        _build_zoho_payload_from_enrichment,
        enrich_lead_by_email,
    )

    settings = get_settings()

    if not settings.ENABLE_AUTO_ENRICH_INTERCOM:
        logger.debug("Auto-enrichment disabled for Intercom (ENABLE_AUTO_ENRICH_INTERCOM=false)")
        return

    logger.info("Auto-enriching Intercom lead: %s", email)

    try:
        # Perform enrichment
        enrichment = enrich_lead_by_email(email)

        if not enrichment.data_sources:
            logger.info("No enrichment data found for: %s", email)
            return

        # Build Zoho update payload from enrichment
        zoho_payload = _build_zoho_payload_from_enrichment(enrichment, email)

        # Update Zoho lead with enrichment data
        if zoho_payload:
            update_lead(lead_id, zoho_payload)
            logger.info("Updated lead with enrichment data: %s (%d fields)", lead_id, len(zoho_payload))

        # Create enrichment note
        note_title = "Auto-Enrichment (Apollo + Website)"
        note_content = _build_enrichment_note(enrichment)
        create_note(lead_id, note_title, note_content)

        # Fetch and upload company logo (best effort)
        from app.services.brandfetch_service import fetch_company_logo
        from app.services.zoho_service import upload_lead_photo
        from app.util.text_format import extract_domain_from_email

        domain = extract_domain_from_email(email)
        if domain:
            logo_data = fetch_company_logo(domain)
            if logo_data:
                upload_lead_photo(lead_id, logo_data, filename=f"{domain}_logo.png")

        logger.info("Auto-enrichment complete for: %s (%d sources)", email, len(enrichment.data_sources))

    except Exception as e:  # noqa: BLE001
        # Log but don't fail the main Intercom job
        logger.warning("Auto-enrichment failed for %s: %s", email, e)


def _extract_tags_from_payload(payload: dict) -> list[str]:
    """
    Extract all tag names from Intercom contact payload.

    Returns:
        List of tag names
    """
    tags = []

    # Navigate to contact's tags
    data = payload.get("data", {})
    item = data.get("item", {})

    # Check if this is the new structure with contact_tag
    item_type = item.get("type", "")
    if item_type == "contact_tag":
        # Tags are in item.contact.tags
        contact = item.get("contact", {})
        tags_obj = contact.get("tags")
    else:
        # Tags are directly in item.tags (fallback)
        tags_obj = item.get("tags")

    if isinstance(tags_obj, dict):
        tags_list = tags_obj.get("data", [])
        if isinstance(tags_list, list):
            for tag in tags_list:
                if isinstance(tag, dict):
                    tag_name = tag.get("name", "")
                    if tag_name:
                        tags.append(tag_name)

    return tags


def _process_contact_tagged(ctx: JobContext) -> None:
    """
    Process Intercom contact.lead.tag.created or contact.user.tag.created event.

    1. Parse contact information from payload
    2. Check if contact has qualifying tags
    3. Create/update Zoho lead
    4. Create note with Intercom source info
    5. Auto-enrich if enabled
    6. Send Slack notification
    """
    settings = get_settings()
    ev = load_event(ctx.event_id)
    if ev is None:
        raise ValueError("Event not found")

    # Parse contact info
    info = parse_intercom_contact_info(ev.payload)
    if not info.email:
        raise ValueError("Intercom payload missing contact email")

    logger.info("Processing Intercom contact tagged: %s (ID: %s)", info.email, info.contact_id)

    # Extract all tags from payload
    all_tags = _extract_tags_from_payload(ev.payload)
    logger.debug("Contact has tags: %s", all_tags)

    # Check if any tags match qualifying tags
    qualifying_tags_str = settings.INTERCOM_QUALIFYING_TAGS or ""
    qualifying_tags = [t.strip() for t in qualifying_tags_str.split(",") if t.strip()]

    matched_tags = [tag for tag in all_tags if tag in qualifying_tags]

    if not matched_tags:
        logger.warning(
            "Contact %s (%s) has no qualifying tags. Tags: %s, Qualifying: %s",
            info.email,
            info.contact_id,
            all_tags,
            qualifying_tags,
        )
        # Still process it since the webhook was triggered - maybe tag was removed after
        matched_tags = all_tags[:1] if all_tags else ["Lead"]  # Use first tag or default to "Lead"

    logger.info("Matched qualifying tags: %s", matched_tags)

    # Build Zoho payload
    zoho_payload = build_zoho_lead_payload_for_intercom(
        info=info,
        lead_status=settings.STATUS_SUPPORT_QUALIFIED,
        tags=matched_tags,
    )

    # Upsert lead by email
    lead_id = upsert_lead_by_email(info.email, zoho_payload)
    logger.info("Created/updated Zoho lead: %s for contact %s", lead_id, info.email)

    # Create note with Intercom source info
    note_title = "Intercom: Contact Qualified"
    note_content = format_intercom_note_content(
        info=info,
        tags=matched_tags,
    )
    create_note(lead_id, note_title, note_content)
    logger.info("Created note in Zoho lead %s", lead_id)

    # Build location string for Slack
    location_parts = []
    if info.city:
        location_parts.append(info.city)
    if info.region:
        location_parts.append(info.region)
    if info.country:
        location_parts.append(info.country)
    location_str = ", ".join(location_parts) if location_parts else None

    # Get plan type from custom attributes
    plan_type = info.custom_attributes.get("plan_type") if info.custom_attributes else None

    # Send Slack notification
    notify_support_qualified(
        email=info.email,
        name=info.name or "",
        company=info.company_name or "",
        tags=matched_tags,
        lead_id=lead_id,
        location=location_str,
        plan_type=plan_type,
    )

    # Auto-enrich lead with Apollo + Website intelligence (if enabled)
    _auto_enrich_intercom_lead(info.email, lead_id, company=info.company_name or "")


def process_intercom_contact_tagged(event_id: str) -> None:
    """
    Entry point for RQ job: process Intercom contact.lead.tag.created or contact.user.tag.created event.
    """
    run_event_job(event_id, _process_contact_tagged)


def _process_company_updated(ctx: JobContext) -> None:
    """
    Process Intercom company.updated event.

    1. Extract company data from webhook payload
    2. Detect expansion signals
    3. Find primary contact for the company
    4. Create Zoho tasks for high-priority signals
    5. Send Slack notifications for critical signals
    """
    from app.services.expansion_signal_service import detect_company_expansion_signals, format_signal_for_zoho_task
    from app.services.slack_service import notify_expansion_opportunity
    from app.services.zoho_service import create_note, create_task, upsert_lead_by_company

    ev = load_event(ctx.event_id)
    if ev is None:
        raise ValueError("Event not found")

    # Extract company data from payload
    data = ev.payload.get("data", {})
    company_data = data.get("item", {})

    company_id = company_data.get("id", "")
    company_name = company_data.get("name", "Unknown Company")
    user_count = company_data.get("user_count", 0)

    logger.info("Processing company.updated: %s (ID: %s, %d users)", company_name, company_id, user_count)

    # Detect expansion signals
    signals = detect_company_expansion_signals(company_data)

    if not signals:
        logger.info("No expansion signals detected for company: %s", company_name)
        return

    logger.info("Detected %d expansion signals for %s", len(signals), company_name)

    # Try to find primary contact for this company
    # We'll need to fetch from Intercom API to get contacts
    from app.services.intercom_service import get_primary_contact_for_company, get_any_contact_for_company

    primary_contact = get_primary_contact_for_company(company_id)

    contact_email = None
    contact_name = ""
    lead_id = None

    if primary_contact:
        contact_email = primary_contact.get("email")
        contact_name = primary_contact.get("name", "")

        logger.info("Found primary contact for %s: %s (%s)", company_name, contact_name, contact_email)
    else:
        logger.warning("No primary contact found for company %s, trying to find any contact...", company_name)

        # Fallback: Try to find ANY contact for this company
        any_contact = get_any_contact_for_company(company_id)

        if any_contact:
            contact_email = any_contact.get("email")
            contact_name = any_contact.get("name", "")
            logger.info("Found fallback contact for %s: %s (%s)", company_name, contact_name, contact_email)
        else:
            logger.error(
                "No contacts found for company %s - signals will be created but not linked to a lead",
                company_name,
            )

    # Build enriched lead payload from company data
    custom_attrs = company_data.get("custom_attributes", {})
    
    # Parse contact name
    first_name = ""
    last_name = contact_name or "Unknown"
    if contact_name:
        name_parts = contact_name.split(" ", 1)
        if len(name_parts) == 2:
            first_name, last_name = name_parts
        elif len(name_parts) == 1:
            first_name = name_parts[0]
            last_name = ""
    
    # Build enriched lead payload
    lead_payload = {
        "Company": company_name,
        "First_Name": first_name,
        "Last_Name": last_name,
        "Lead_Source": "Intercom - Expansion Signal",
    }
    
    # Only add Email if we have a contact
    if contact_email:
        lead_payload["Email"] = contact_email
    
    # Add company metrics from Intercom
    if user_count:
        lead_payload["No_of_Employees"] = user_count
    
    # Add GoVisually-specific data
    plan_type = custom_attrs.get("gv_subscription_plan", "")
    if plan_type:
        lead_payload["Description"] = f"Plan: {plan_type}\n"
    
    active_projects = custom_attrs.get("gv_total_active_projects", 0)
    projects_allowed = custom_attrs.get("gv_projects_allowed", 0)
    if active_projects or projects_allowed:
        desc = lead_payload.get("Description", "")
        lead_payload["Description"] = desc + f"Active Projects: {active_projects}/{projects_allowed}\n"
    
    team_size = custom_attrs.get("gv_no_of_members", 0)
    if team_size:
        desc = lead_payload.get("Description", "")
        lead_payload["Description"] = desc + f"Team Size: {team_size}\n"
    
    subscription_status = custom_attrs.get("gv_subscription_status", "")
    if subscription_status:
        desc = lead_payload.get("Description", "")
        lead_payload["Description"] = desc + f"Subscription Status: {subscription_status}\n"
    
    subscription_exp = custom_attrs.get("gv_subscription_exp", "")
    if subscription_exp:
        desc = lead_payload.get("Description", "")
        lead_payload["Description"] = desc + f"Subscription Expires: {subscription_exp}\n"
    
    # Upsert lead by COMPANY (not email) to avoid duplicate leads for same company
    # This ensures one lead per company, even if multiple contacts trigger signals
    try:
        lead_id = upsert_lead_by_company(company_name, lead_payload)
        logger.info("Ensured Zoho lead exists for company %s: %s (primary contact: %s)", company_name, lead_id, contact_email or "None")
        
        # Create a note summarizing all detected expansion signals
        # Use plain text formatting (Zoho Notes don't support Markdown)
        if signals and lead_id:
            from app.util.text_format import format_zoho_note_plain_text
            
            # Build sections for each signal
            signal_sections = []
            for signal in signals:
                priority_emoji = {
                    "critical": "🔥",
                    "high": "🚀",
                    "medium": "⚡",
                    "low": "📌",
                }.get(signal.priority, "📌")
                
                signal_title = f"{priority_emoji} {signal.signal_type.replace('_', ' ').title()} ({signal.priority.upper()})"
                
                items = [
                    {"label": "Details", "value": signal.details},
                    {"label": "Action", "value": signal.action},
                ]
                
                if signal.talking_points:
                    items.append({"label": "Talking Points", "value": ""})
                    items.extend([{"label": "", "value": point} for point in signal.talking_points])
                
                if signal.metadata:
                    items.append({"label": "Metrics", "value": ""})
                    items.extend([{"label": "", "value": f"{key}: {value}"} for key, value in signal.metadata.items()])
                
                signal_sections.append({
                    "title": signal_title,
                    "items": items,
                })
            
            # Build main sections
            sections = [
                {
                    "title": "Company Information",
                    "items": [
                        {"label": "Company", "value": company_name},
                        {"label": "Intercom Company ID", "value": company_id},
                        {"label": "User Count", "value": str(user_count)},
                    ],
                },
            ]
            
            if contact_email:
                sections[0]["items"].append({
                    "label": "Primary Contact",
                    "value": f"{contact_name or 'Unknown'} ({contact_email})",
                })
            
            sections.append({
                "title": f"Detected {len(signals)} Expansion Signal(s)",
                "items": [],
            })
            
            # Add signal sections
            sections.extend(signal_sections)
            
            # Format as plain text
            note_content = format_zoho_note_plain_text(
                title="Expansion Signals Detected",
                sections=sections,
                footer=f"View in Intercom: https://app.intercom.com/a/apps/wfkef3s2/companies/{company_id}",
            )
            
            create_note(lead_id, "Expansion Signals", note_content)
            logger.info("Created expansion signals note for lead: %s", lead_id)
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to upsert lead for company %s: %s", company_name, e)
        lead_id = None

    # Process each signal
    for signal in signals:
        logger.info(
            "Processing signal: %s (priority: %s) for %s",
            signal.signal_type,
            signal.priority,
            company_name,
        )

        # Create Zoho task if needed
        if signal.create_zoho_task and lead_id:
            try:
                task_payload = format_signal_for_zoho_task(
                    signal=signal,
                    company_name=company_name,
                    company_id=company_id,
                    contact_email=contact_email,
                )

                # Extract fields from task_payload and call create_task with keyword args
                # Ensure due_date is set (default to 7 days from now if missing)
                due_date = task_payload.get("Due_Date", "")
                if not due_date:
                    from datetime import date, timedelta
                    due_date = (date.today() + timedelta(days=7)).isoformat()
                
                create_task(
                    lead_id=lead_id,
                    subject=task_payload.get("Subject", f"Expansion Signal: {signal.signal_type}"),
                    due_date=due_date,
                    description=task_payload.get("Description", signal.details),
                )
                logger.info("Created Zoho task for signal: %s", signal.signal_type)
            except Exception as e:  # noqa: BLE001
                logger.error("Failed to create Zoho task for signal %s: %s", signal.signal_type, e)

        # Send Slack notification for high-priority signals
        if signal.priority in ["critical", "high"]:
            try:
                success = notify_expansion_opportunity(
                    company_name=company_name,
                    contact_email=contact_email or "No primary contact",
                    signal_type=signal.signal_type,
                    details=signal.details,
                    action=signal.action,
                    priority=signal.priority,
                    lead_id=lead_id,
                )
                if success:
                    logger.info("Sent Slack notification for signal: %s", signal.signal_type)
                else:
                    logger.warning("Failed to send Slack notification for signal: %s (check webhook URL)", signal.signal_type)
            except Exception as e:  # noqa: BLE001
                logger.error("Exception sending Slack notification for signal %s: %s", signal.signal_type, e)


def process_company_updated(event_id: str) -> None:
    """
    Entry point for RQ job: process Intercom company.updated event.
    """
    run_event_job(event_id, _process_company_updated)
