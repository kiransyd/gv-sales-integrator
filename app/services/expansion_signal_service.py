"""
Service for detecting expansion signals from Intercom company data.

Analyzes company usage metrics to identify:
- Teams approaching capacity limits
- Power user behavior
- Subscription changes
- Churn risks
- Upsell opportunities
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)


# Plan limits configuration
# TODO: Move this to settings or database for easier updates
PLAN_LIMITS = {
    "PRO - Yearly": {
        "members": 25,  # Adjust based on actual plan limits
        "projects": 250,
    },
    "Team Yearly": {
        "members": 10,  # Adjust based on actual plan limits
        "projects": 1000,
    },
    "PRO - Monthly": {
        "members": 25,
        "projects": 250,
    },
    "Team Monthly": {
        "members": 10,
        "projects": 1000,
    },
}


@dataclass
class ExpansionSignal:
    """Represents a detected expansion or churn signal."""

    signal_type: str  # e.g., "team_at_capacity", "power_user", etc.
    priority: Literal["critical", "high", "medium", "low"]
    details: str  # Human-readable description
    action: str  # Recommended sales action
    urgency_days: int  # How soon to contact (for task due date)
    create_zoho_task: bool = True
    hot_lead: bool = False
    churn_prevention: bool = False
    talking_points: list[str] | None = None
    metadata: dict | None = None  # Additional context


def detect_company_expansion_signals(company_data: dict) -> list[ExpansionSignal]:
    """
    Analyze Intercom company data for expansion signals.
    
    Currently only detects trial_engaged_user signal (trial users with 2+ projects AND 2+ team members).
    All other signals have been disabled to reduce noise.

    Args:
        company_data: Company object from Intercom webhook payload

    Returns:
        List of detected expansion signals with recommended actions
    """
    signals: list[ExpansionSignal] = []
    custom_attrs = company_data.get("custom_attributes", {})

    # Extract GoVisually metrics
    team_size = custom_attrs.get("gv_no_of_members", 0)
    active_projects = custom_attrs.get("gv_total_active_projects", 0)
    subscription_status = custom_attrs.get("gv_subscription_status", "")
    subscription_exp_sec = custom_attrs.get("gv_subscription_exp_in_sec", 0)

    # Check if trial user
    is_trial = subscription_status in ["trial", "trialing", "Trial"]

    # Only process trial users - all paid user signals disabled
    if not is_trial:
        logger.debug("Company %s is not a trial user, skipping signal detection", company_data.get("name", "Unknown"))
        return signals

    # Calculate days until trial expiration
    days_until_exp = None
    if subscription_exp_sec:
        days_until_exp = (subscription_exp_sec - time.time()) / (60 * 60 * 24)

    # TRIAL SIGNAL: Engaged trial user (2+ projects + team member/reviewer)
    # This shows they've hit multiple "aha moments"
    if active_projects >= 2 and team_size >= 2:
        signals.append(
            ExpansionSignal(
                signal_type="trial_engaged_user",
                priority="high",
                details=f"Trial user created {active_projects}/3 projects AND added {team_size} team members/reviewers - strong engagement!",
                action="Hot lead: Proactive conversion outreach, offer discount or extended trial",
                urgency_days=2,
                create_zoho_task=True,
                hot_lead=True,
                talking_points=[
                    f"I see you've created {active_projects} projects and added team members!",
                    "You're clearly getting value from GoVisually.",
                    "Let's get you set up on a plan - I can offer you a special rate.",
                ],
                metadata={
                    "active_projects": active_projects,
                    "team_size": team_size,
                    "days_left": int(days_until_exp) if days_until_exp else None,
                },
            )
        )

    logger.info("Detected %d trial signals for company %s", len(signals), company_data.get("name"))
    return signals


def format_signal_for_zoho_task(
    signal: ExpansionSignal,
    company_name: str,
    company_id: str,
    contact_email: str | None = None,
) -> dict:
    """
    Format expansion signal as Zoho task payload.

    Args:
        signal: Detected expansion signal
        company_name: Company name
        company_id: Intercom company ID
        contact_email: Primary contact email (optional)

    Returns:
        Dict with Zoho task fields
    """
    from datetime import date, timedelta

    # Priority emoji
    priority_emoji = {
        "critical": "🔥",
        "high": "🚀",
        "medium": "⚡",
        "low": "📌",
    }.get(signal.priority, "📌")

    # Build subject
    subject = f"{priority_emoji} {signal.signal_type.replace('_', ' ').title()}: {company_name}"

    # Build description
    description_parts = [
        f"EXPANSION SIGNAL: {signal.signal_type.replace('_', ' ').title()}",
        "",
        f"Company: {company_name}",
    ]

    if contact_email:
        description_parts.append(f"Contact: {contact_email}")

    description_parts.extend(
        [
            f"Intercom Company ID: {company_id}",
            "",
            f"SIGNAL DETAILS:",
            f"- {signal.details}",
            "",
            f"ACTION REQUIRED:",
            f"- {signal.action}",
            f"- Contact within {signal.urgency_days} days",
        ]
    )

    if signal.talking_points:
        description_parts.extend(
            [
                "",
                "TALKING POINTS:",
            ]
        )
        for point in signal.talking_points:
            description_parts.append(f"- {point}")

    if signal.metadata:
        description_parts.extend(
            [
                "",
                "METRICS:",
            ]
        )
        for key, value in signal.metadata.items():
            description_parts.append(f"- {key}: {value}")

    description_parts.extend(
        [
            "",
            f"[View in Intercom](https://app.intercom.com/a/apps/wfkef3s2/companies/{company_id})",
        ]
    )

    description = "\n".join(description_parts)

    # Calculate due date
    due_date = date.today() + timedelta(days=signal.urgency_days)

    # Map priority to Zoho
    zoho_priority = {
        "critical": "High",
        "high": "High",
        "medium": "Normal",
        "low": "Low",
    }.get(signal.priority, "Normal")

    return {
        "Subject": subject[:255],  # Zoho has 255 char limit on subject
        "Description": description,
        "Due_Date": due_date.isoformat(),
        "Priority": zoho_priority,
        "Status": "Not Started",
    }


def get_plan_limits(plan_name: str) -> dict:
    """
    Get plan limits for a given plan name.

    Args:
        plan_name: Subscription plan name from Intercom

    Returns:
        Dict with member and project limits
    """
    return PLAN_LIMITS.get(plan_name, {})
