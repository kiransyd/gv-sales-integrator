#!/usr/bin/env python3
"""
Inspect Intercom contact to see what product usage signals are available.

Usage:
    python3 scripts/inspect_intercom_contact.py lucious.begay@calvaryabq.org
"""

import json
import sys
from pathlib import Path

import httpx

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.settings import get_settings


def search_contact_by_email(email: str) -> dict | None:
    """
    Search for an Intercom contact by email address.

    Returns contact data if found, None otherwise.
    """
    settings = get_settings()

    if not settings.INTERCOM_API_KEY:
        print("❌ INTERCOM_API_KEY not configured in .env")
        return None

    headers = {
        "Authorization": f"Bearer {settings.INTERCOM_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Intercom-Version": "2.11"
    }

    # Search for contact by email
    search_payload = {
        "query": {
            "field": "email",
            "operator": "=",
            "value": email
        }
    }

    print(f"🔍 Searching Intercom for contact: {email}")
    print(f"   Endpoint: https://api.intercom.io/contacts/search")

    try:
        response = httpx.post(
            "https://api.intercom.io/contacts/search",
            headers=headers,
            json=search_payload,
            timeout=30
        )
        response.raise_for_status()

        data = response.json()
        contacts = data.get("data", [])

        if not contacts:
            print(f"❌ No contact found with email: {email}")
            return None

        if len(contacts) > 1:
            print(f"⚠️  Found {len(contacts)} contacts with this email (using first one)")

        return contacts[0]

    except httpx.HTTPStatusError as e:
        print(f"❌ API error: {e.response.status_code}")
        print(f"   Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def get_contact_events(contact_id: str, per_page: int = 50) -> list[dict]:
    """
    Get events for a contact.

    https://developers.intercom.com/docs/references/rest-api/api.intercom.io/Events/listEvents/
    """
    settings = get_settings()

    headers = {
        "Authorization": f"Bearer {settings.INTERCOM_API_KEY}",
        "Accept": "application/json",
        "Intercom-Version": "2.11"
    }

    # Note: The Events API uses user_id or email, not contact_id
    # For now, we'll rely on what's in the contact data
    print(f"\n📊 Note: Event timeline is embedded in contact data (not separate API)")
    return []


def analyze_usage_signals(contact: dict) -> dict:
    """
    Analyze contact data for product usage signals.

    Returns dict of detected signals.
    """
    signals = {
        "basic_info": {},
        "usage_indicators": {},
        "custom_attributes": {},
        "expansion_signals": [],
        "churn_risks": []
    }

    # Basic info
    signals["basic_info"] = {
        "email": contact.get("email"),
        "name": contact.get("name"),
        "role": contact.get("role"),
        "signed_up_at": contact.get("signed_up_at"),
        "last_seen_at": contact.get("last_seen_at"),
        "created_at": contact.get("created_at"),
        "updated_at": contact.get("updated_at")
    }

    # Custom attributes (this is where GoVisually usage data would be)
    custom_attrs = contact.get("custom_attributes", {})
    signals["custom_attributes"] = custom_attrs

    # Check for GoVisually-specific usage indicators
    plan_type = custom_attrs.get("plan_type")
    projects_count = custom_attrs.get("projects_count")
    teammates_count = custom_attrs.get("teammates_count") or custom_attrs.get("teammates_invited")
    storage_used = custom_attrs.get("storage_used_mb")
    last_active = custom_attrs.get("last_active_date") or custom_attrs.get("last_active")

    signals["usage_indicators"] = {
        "plan_type": plan_type,
        "projects_count": projects_count,
        "teammates_count": teammates_count,
        "storage_used_mb": storage_used,
        "last_active": last_active
    }

    # Detect expansion signals
    if plan_type == "team":
        if teammates_count and teammates_count >= 8:
            signals["expansion_signals"].append({
                "signal": "team_size_limit",
                "details": f"{teammates_count}/10 users (approaching limit)",
                "action": "Offer Enterprise plan upgrade"
            })

        if storage_used and storage_used > 800:
            signals["expansion_signals"].append({
                "signal": "storage_threshold",
                "details": f"{storage_used}MB used (80%+ of 1GB limit)",
                "action": "Upsell more storage or Enterprise"
            })

        if projects_count and projects_count >= 20:
            signals["expansion_signals"].append({
                "signal": "power_user",
                "details": f"{projects_count} projects created",
                "action": "Check in about advanced needs"
            })

    # Check for enterprise feature interest
    enterprise_features = custom_attrs.get("enterprise_features_tried", [])
    if enterprise_features:
        signals["expansion_signals"].append({
            "signal": "enterprise_feature_interest",
            "details": f"Tried: {', '.join(enterprise_features)}",
            "action": "Sales call to discuss Enterprise"
        })

    # Detect churn risks
    # (Would need actual activity data to calculate this properly)

    return signals


def print_contact_overview(contact: dict):
    """Print contact overview in a readable format."""
    print("\n" + "="*80)
    print("📋 CONTACT OVERVIEW")
    print("="*80)

    print(f"\n👤 Basic Info:")
    print(f"   Email: {contact.get('email')}")
    print(f"   Name: {contact.get('name')}")
    print(f"   ID: {contact.get('id')}")
    print(f"   Role: {contact.get('role', 'N/A')}")
    print(f"   Workspace: {contact.get('workspace_id', 'N/A')}")

    # Timestamps
    signed_up = contact.get("signed_up_at")
    last_seen = contact.get("last_seen_at")
    print(f"\n📅 Activity:")
    print(f"   Signed up: {signed_up if signed_up else 'N/A'}")
    print(f"   Last seen: {last_seen if last_seen else 'N/A'}")

    # Location
    location = contact.get("location", {})
    if location:
        print(f"\n📍 Location:")
        print(f"   City: {location.get('city', 'N/A')}")
        print(f"   Region: {location.get('region', 'N/A')}")
        print(f"   Country: {location.get('country', 'N/A')}")

    # Companies
    companies = contact.get("companies", {}).get("data", [])
    if companies:
        print(f"\n🏢 Companies ({len(companies)}):")
        for company in companies[:3]:  # Show first 3
            print(f"   - {company.get('name')} ({company.get('website', 'no website')})")
            if company.get("size"):
                print(f"     Size: {company.get('size')} employees")

    # Tags
    tags = contact.get("tags", {}).get("data", [])
    if tags:
        tag_names = [t.get("name") for t in tags]
        print(f"\n🏷️  Tags ({len(tags)}): {', '.join(tag_names)}")

    # Custom attributes
    custom_attrs = contact.get("custom_attributes", {})
    if custom_attrs:
        print(f"\n⚙️  Custom Attributes ({len(custom_attrs)}):")
        for key, value in custom_attrs.items():
            print(f"   {key}: {value}")
    else:
        print(f"\n⚠️  No custom attributes found")
        print(f"   (This is where GoVisually usage data would be stored)")

    # Notes/conversations count
    print(f"\n💬 Engagement:")
    print(f"   Notes count: {contact.get('notes_count', 0)}")
    print(f"   Conversations: {contact.get('conversations_count', 'N/A')}")


def print_usage_signals(signals: dict):
    """Print detected usage signals."""
    print("\n" + "="*80)
    print("🎯 PRODUCT USAGE SIGNALS ANALYSIS")
    print("="*80)

    # Usage indicators
    usage = signals["usage_indicators"]
    print(f"\n📊 Current Usage Indicators:")
    for key, value in usage.items():
        if value is not None:
            print(f"   {key}: {value}")
        else:
            print(f"   {key}: ❌ NOT TRACKED")

    # Expansion signals
    expansion = signals["expansion_signals"]
    if expansion:
        print(f"\n🚀 EXPANSION SIGNALS DETECTED ({len(expansion)}):")
        for i, signal in enumerate(expansion, 1):
            print(f"\n   {i}. {signal['signal'].upper()}")
            print(f"      Details: {signal['details']}")
            print(f"      → Action: {signal['action']}")
    else:
        print(f"\n✅ No expansion signals detected")

    # Churn risks
    churn = signals["churn_risks"]
    if churn:
        print(f"\n⚠️  CHURN RISKS DETECTED ({len(churn)}):")
        for i, risk in enumerate(churn, 1):
            print(f"\n   {i}. {risk['risk'].upper()}")
            print(f"      Details: {risk['details']}")
            print(f"      → Action: {risk['action']}")
    else:
        print(f"\n✅ No churn risks detected")


def print_recommendations(contact: dict, signals: dict):
    """Print recommendations for what to track."""
    print("\n" + "="*80)
    print("💡 RECOMMENDATIONS: What to Track in Intercom")
    print("="*80)

    custom_attrs = contact.get("custom_attributes", {})

    missing_fields = []

    # Check what's missing
    recommended_fields = {
        "plan_type": "User's subscription plan (free, team, enterprise)",
        "projects_count": "Total number of projects created",
        "teammates_count": "Number of teammates invited",
        "teammates_invited": "Number of teammates invited (total)",
        "storage_used_mb": "Storage usage in MB",
        "storage_limit_mb": "Storage limit in MB",
        "last_active_date": "Last time user was active in product",
        "last_project_created": "Timestamp of last project creation",
        "enterprise_features_tried": "List of enterprise features accessed",
        "integrations_enabled": "List of integrations user has set up",
        "workspace_count": "Number of workspaces created"
    }

    print("\n📋 Recommended Data Attributes to Track:")
    print()

    for field, description in recommended_fields.items():
        exists = field in custom_attrs
        status = "✅ EXISTS" if exists else "❌ MISSING"
        current_value = custom_attrs.get(field, "N/A") if exists else "N/A"

        print(f"   {status} | {field}")
        print(f"            Purpose: {description}")
        if exists:
            print(f"            Current value: {current_value}")
        print()

    # Events to track
    print("\n📊 Recommended Events to Track:")
    events = [
        ("project_created", "When user creates a new project"),
        ("teammate_invited", "When user invites a teammate"),
        ("storage_threshold_reached", "When user hits 50%, 80%, 90% storage"),
        ("enterprise_feature_accessed", "When user tries SSO, custom branding, etc."),
        ("integration_connected", "When user connects to Slack, Asana, etc."),
        ("workspace_created", "When user creates additional workspace"),
        ("export_performed", "When user exports project/assets"),
        ("inactive_14_days", "User hasn't logged in for 14 days")
    ]

    for event_name, description in events:
        print(f"   • {event_name}")
        print(f"     → {description}")
        print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/inspect_intercom_contact.py <email>")
        print("Example: python3 scripts/inspect_intercom_contact.py lucious.begay@calvaryabq.org")
        sys.exit(1)

    email = sys.argv[1]

    # Search for contact
    contact = search_contact_by_email(email)

    if not contact:
        print("\n❌ Could not retrieve contact data")
        sys.exit(1)

    print(f"✅ Found contact: {contact.get('name')} ({contact.get('email')})")

    # Print overview
    print_contact_overview(contact)

    # Analyze usage signals
    signals = analyze_usage_signals(contact)
    print_usage_signals(signals)

    # Print recommendations
    print_recommendations(contact, signals)

    # Save raw data to file for inspection
    output_file = Path(__file__).parent.parent / "contact_data.json"
    with open(output_file, "w") as f:
        json.dump(contact, f, indent=2)

    print("\n" + "="*80)
    print(f"💾 Full contact data saved to: {output_file}")
    print("="*80)


if __name__ == "__main__":
    main()
