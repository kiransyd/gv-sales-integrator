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
    projects_allowed = custom_attrs.get("gv_projects_allowed", 0)
    plan_name = custom_attrs.get("gv_subscription_plan", "")
    subscription_status = custom_attrs.get("gv_subscription_status", "")
    subscription_exp_sec = custom_attrs.get("gv_subscription_exp_in_sec", 0)
    checklists_used = custom_attrs.get("gv_checklists", 0)

    # Get plan limits
    plan_limits = PLAN_LIMITS.get(plan_name, {})
    member_limit = plan_limits.get("members")

    # SIGNAL 1: Team at maximum capacity (CRITICAL)
    if member_limit and team_size >= member_limit:
        signals.append(
            ExpansionSignal(
                signal_type="team_at_capacity",
                priority="critical",
                details=f"{team_size}/{member_limit} members - AT LIMIT, cannot add more!",
                action="URGENT: Offer Enterprise/upgrade with unlimited users",
                urgency_days=2,  # Contact within 48 hours
                create_zoho_task=True,
                hot_lead=True,
                talking_points=[
                    "I noticed you're at your member limit. Are you blocked from adding teammates?",
                    "Enterprise gives you unlimited users, priority support, SSO, and custom branding.",
                    "Your team is clearly growing - let's make sure GoVisually grows with you.",
                ],
                metadata={"team_size": team_size, "member_limit": member_limit},
            )
        )

    # SIGNAL 2: Team approaching capacity (HIGH)
    elif member_limit and team_size >= (member_limit * 0.8):
        signals.append(
            ExpansionSignal(
                signal_type="team_approaching_capacity",
                priority="high",
                details=f"{team_size}/{member_limit} members - {int(team_size/member_limit*100)}% of limit",
                action="Proactive: Offer Enterprise trial before they hit limit",
                urgency_days=7,
                create_zoho_task=True,
                talking_points=[
                    f"You're at {team_size} out of {member_limit} members on your {plan_name} plan.",
                    "As your team grows, you might want to consider upgrading to avoid hitting the limit.",
                    "Let me show you what Enterprise offers.",
                ],
                metadata={"team_size": team_size, "member_limit": member_limit, "utilization": team_size / member_limit},
            )
        )

    # SIGNAL 3: Power user - extreme project volume (HIGH)
    if active_projects >= 100:
        intensity = "extreme" if active_projects >= 100 else "high"
        signals.append(
            ExpansionSignal(
                signal_type="power_user_projects",
                priority="high" if active_projects >= 100 else "medium",
                details=f"{active_projects} active projects ({intensity} usage)",
                action="Check in about advanced needs, API access, automation opportunities",
                urgency_days=14,
                create_zoho_task=True,
                talking_points=[
                    f"I see you have {active_projects} active projects - you're clearly power users!",
                    "Are there any workflows we can help automate or streamline?",
                    "Would API access or advanced integrations be valuable for your team?",
                ],
                metadata={"active_projects": active_projects, "projects_allowed": projects_allowed},
            )
        )

    # SIGNAL 4: Approaching project limit
    if projects_allowed and active_projects >= (projects_allowed * 0.8):
        signals.append(
            ExpansionSignal(
                signal_type="project_limit_approaching",
                priority="high" if active_projects >= (projects_allowed * 0.9) else "medium",
                details=f"{active_projects}/{projects_allowed} projects - {int(active_projects/projects_allowed*100)}% of limit",
                action="Offer plan upgrade with higher project limits",
                urgency_days=7 if active_projects >= (projects_allowed * 0.9) else 14,
                create_zoho_task=True,
                talking_points=[
                    f"You're at {active_projects} out of {projects_allowed} projects.",
                    "Let's discuss upgrading your plan before you hit the limit.",
                ],
                metadata={"active_projects": active_projects, "projects_allowed": projects_allowed},
            )
        )

    # SIGNAL 5: Subscription expiring soon
    if subscription_exp_sec:
        days_until_exp = (subscription_exp_sec - time.time()) / (60 * 60 * 24)

        if 0 < days_until_exp <= 90:  # Within 90 days
            priority = "high" if days_until_exp <= 30 else "medium"
            urgency = 7 if days_until_exp <= 30 else 14

            signals.append(
                ExpansionSignal(
                    signal_type="subscription_expiring",
                    priority=priority,
                    details=f"Subscription expires in {int(days_until_exp)} days",
                    action="Renewal outreach, check satisfaction, explore upsell opportunity",
                    urgency_days=urgency,
                    create_zoho_task=True,
                    talking_points=[
                        f"Your subscription renews in {int(days_until_exp)} days.",
                        "How has GoVisually been working for your team?",
                        "This is a good time to discuss if there are any features you'd like to see.",
                    ],
                    metadata={"days_until_expiration": int(days_until_exp)},
                )
            )

    # SIGNAL 6: Subscription churned/canceled (URGENT)
    if subscription_status in ["canceled", "cancelled", "expired", "unpaid"]:
        signals.append(
            ExpansionSignal(
                signal_type="subscription_churned",
                priority="critical",
                details=f"Subscription status: {subscription_status}",
                action="URGENT: Win-back campaign, understand why they left",
                urgency_days=1,
                create_zoho_task=True,
                churn_prevention=True,
                talking_points=[
                    "I noticed your subscription status has changed.",
                    "Can we schedule a quick call to understand what happened?",
                    "We'd love to have you back and address any concerns.",
                ],
                metadata={"subscription_status": subscription_status},
            )
        )

    # SIGNAL 7: Low feature adoption (LOW - customer success, not sales)
    if active_projects >= 10 and checklists_used == 0:
        signals.append(
            ExpansionSignal(
                signal_type="low_feature_adoption",
                priority="low",
                details=f"{active_projects} projects but 0 checklists used",
                action="Customer success: Show them checklist feature to increase engagement",
                urgency_days=30,
                create_zoho_task=False,  # This is for customer success, not sales
                metadata={"active_projects": active_projects, "checklists_used": checklists_used},
            )
        )

    logger.info(
        "Detected %d expansion signals for company %s: %s",
        len(signals),
        company_data.get("name", "Unknown"),
        [s.signal_type for s in signals],
    )

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
