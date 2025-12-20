#!/usr/bin/env python3
"""
Inspect Intercom company to see what product usage signals are stored at company level.

Usage:
    python3 scripts/inspect_intercom_company.py <company_id>
    python3 scripts/inspect_intercom_company.py --search "Calvary Design Team"
"""

import json
import sys
from pathlib import Path

import httpx

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.settings import get_settings


def get_company_by_id(company_id: str) -> dict | None:
    """
    Get Intercom company by ID.

    https://developers.intercom.com/docs/references/rest-api/api.intercom.io/Companies/GetCompany/
    """
    settings = get_settings()

    if not settings.INTERCOM_API_KEY:
        print("❌ INTERCOM_API_KEY not configured in .env")
        return None

    headers = {
        "Authorization": f"Bearer {settings.INTERCOM_API_KEY}",
        "Accept": "application/json",
        "Intercom-Version": "2.11"
    }

    print(f"🔍 Fetching company by ID: {company_id}")

    try:
        response = httpx.get(
            f"https://api.intercom.io/companies/{company_id}",
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        return response.json()

    except httpx.HTTPStatusError as e:
        print(f"❌ API error: {e.response.status_code}")
        print(f"   Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def search_company_by_name(name: str) -> list[dict]:
    """
    Search for companies by name.

    https://developers.intercom.com/docs/references/rest-api/api.intercom.io/Companies/ScrollCompanies/
    """
    settings = get_settings()

    headers = {
        "Authorization": f"Bearer {settings.INTERCOM_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Intercom-Version": "2.11"
    }

    print(f"🔍 Searching for companies matching: {name}")

    # Use scroll API to list all companies (Intercom doesn't have company search by name)
    all_companies = []
    scroll_param = None

    try:
        while True:
            url = "https://api.intercom.io/companies/scroll"
            if scroll_param:
                url += f"?scroll_param={scroll_param}"

            response = httpx.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            companies = data.get("data", [])
            all_companies.extend(companies)

            scroll_param = data.get("scroll_param")
            if not scroll_param:
                break

            # Limit to prevent infinite loops
            if len(all_companies) > 1000:
                print("⚠️  Reached 1000 companies limit, stopping search")
                break

        # Filter by name (case-insensitive partial match)
        name_lower = name.lower()
        matching = [
            c for c in all_companies
            if name_lower in c.get("name", "").lower()
        ]

        return matching

    except Exception as e:
        print(f"❌ Error: {e}")
        return []


def analyze_company_usage_signals(company: dict) -> dict:
    """
    Analyze company data for product usage signals.

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
        "name": company.get("name"),
        "company_id": company.get("company_id"),
        "id": company.get("id"),
        "website": company.get("website"),
        "size": company.get("size"),
        "industry": company.get("industry"),
        "plan": company.get("plan", {}).get("name") if company.get("plan") else None,
        "created_at": company.get("created_at"),
        "updated_at": company.get("updated_at")
    }

    # Custom attributes (this is where usage data should be)
    custom_attrs = company.get("custom_attributes", {})
    signals["custom_attributes"] = custom_attrs

    # Extract usage indicators
    plan_type = custom_attrs.get("plan_type") or custom_attrs.get("plan")
    projects_count = custom_attrs.get("projects_count")
    teammates_count = custom_attrs.get("teammates_count") or custom_attrs.get("users_count") or custom_attrs.get("team_size")
    storage_used = custom_attrs.get("storage_used_mb") or custom_attrs.get("storage_used")
    storage_percent = custom_attrs.get("storage_percent")
    last_active = custom_attrs.get("last_active") or custom_attrs.get("last_activity_date")

    signals["usage_indicators"] = {
        "plan_type": plan_type,
        "projects_count": projects_count,
        "teammates_count": teammates_count,
        "storage_used_mb": storage_used,
        "storage_percent": storage_percent,
        "last_active": last_active
    }

    # Detect expansion signals
    if plan_type in ["team", "Team"]:
        if teammates_count and teammates_count >= 8:
            signals["expansion_signals"].append({
                "signal": "team_size_limit",
                "details": f"{teammates_count}/10 users (approaching limit)",
                "action": "Offer Enterprise plan upgrade",
                "priority": "high"
            })

        if storage_percent and storage_percent >= 80:
            signals["expansion_signals"].append({
                "signal": "storage_threshold",
                "details": f"{storage_percent}% storage used",
                "action": "Upsell more storage or Enterprise",
                "priority": "high" if storage_percent >= 90 else "medium"
            })

        if projects_count and projects_count >= 20:
            signals["expansion_signals"].append({
                "signal": "power_user",
                "details": f"{projects_count} projects created",
                "action": "Check in about advanced needs",
                "priority": "medium"
            })

    # Check for enterprise features
    enterprise_features = custom_attrs.get("enterprise_features_tried", [])
    if enterprise_features:
        signals["expansion_signals"].append({
            "signal": "enterprise_feature_interest",
            "details": f"Tried: {', '.join(enterprise_features) if isinstance(enterprise_features, list) else enterprise_features}",
            "action": "Sales call to discuss Enterprise",
            "priority": "high"
        })

    return signals


def print_company_overview(company: dict):
    """Print company overview in a readable format."""
    print("\n" + "="*80)
    print("🏢 COMPANY OVERVIEW")
    print("="*80)

    print(f"\n📋 Basic Info:")
    print(f"   Name: {company.get('name')}")
    print(f"   ID: {company.get('id')}")
    print(f"   Company ID: {company.get('company_id', 'N/A')}")
    print(f"   Website: {company.get('website', 'N/A')}")
    print(f"   Industry: {company.get('industry', 'N/A')}")
    print(f"   Size: {company.get('size', 'N/A')} employees")

    # Plan info
    plan = company.get("plan")
    if plan:
        print(f"\n💳 Plan:")
        print(f"   Name: {plan.get('name', 'N/A')}")
        print(f"   ID: {plan.get('id', 'N/A')}")

    # Timestamps
    created = company.get("created_at")
    updated = company.get("updated_at")
    print(f"\n📅 Activity:")
    print(f"   Created: {created if created else 'N/A'}")
    print(f"   Last updated: {updated if updated else 'N/A'}")

    # Monthly spend
    monthly_spend = company.get("monthly_spend")
    if monthly_spend:
        print(f"\n💰 Revenue:")
        print(f"   Monthly spend: ${monthly_spend}")

    # User count
    user_count = company.get("user_count")
    if user_count:
        print(f"\n👥 Users:")
        print(f"   Total users: {user_count}")

    # Session count
    session_count = company.get("session_count")
    if session_count:
        print(f"   Total sessions: {session_count}")

    # Tags
    tags = company.get("tags", {}).get("data", [])
    if tags:
        tag_names = [t.get("name") for t in tags]
        print(f"\n🏷️  Tags ({len(tags)}): {', '.join(tag_names)}")

    # Custom attributes
    custom_attrs = company.get("custom_attributes", {})
    if custom_attrs:
        print(f"\n⚙️  Custom Attributes ({len(custom_attrs)}):")
        for key, value in custom_attrs.items():
            # Format value nicely
            if isinstance(value, list):
                value_str = f"[{', '.join(str(v) for v in value)}]"
            else:
                value_str = str(value)
            print(f"   {key}: {value_str}")
    else:
        print(f"\n⚠️  No custom attributes found")
        print(f"   (This is where GoVisually usage data should be stored)")


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
            print(f"   ✅ {key}: {value}")
        else:
            print(f"   ❌ {key}: NOT TRACKED")

    # Expansion signals
    expansion = signals["expansion_signals"]
    if expansion:
        print(f"\n🚀 EXPANSION SIGNALS DETECTED ({len(expansion)}):")
        for i, signal in enumerate(expansion, 1):
            priority_emoji = {"high": "🔥", "medium": "⚡", "low": "📌"}.get(signal.get("priority", "medium"), "📌")
            print(f"\n   {i}. {priority_emoji} {signal['signal'].upper()} [{signal.get('priority', 'medium').upper()}]")
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


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 scripts/inspect_intercom_company.py <company_id>")
        print("  python3 scripts/inspect_intercom_company.py --search \"Company Name\"")
        print("\nExample:")
        print("  python3 scripts/inspect_intercom_company.py 6631059bebbd37855746fc2d")
        print("  python3 scripts/inspect_intercom_company.py --search \"Calvary Design Team\"")
        sys.exit(1)

    if sys.argv[1] == "--search":
        if len(sys.argv) < 3:
            print("❌ Please provide a search term after --search")
            sys.exit(1)

        search_term = sys.argv[2]
        companies = search_company_by_name(search_term)

        if not companies:
            print(f"\n❌ No companies found matching: {search_term}")
            sys.exit(1)

        print(f"\n✅ Found {len(companies)} matching companies:")
        for i, comp in enumerate(companies, 1):
            print(f"   {i}. {comp.get('name')} (ID: {comp.get('id')})")

        # Use first match
        company = companies[0]
        if len(companies) > 1:
            print(f"\n📌 Using first match: {company.get('name')}")

    else:
        company_id = sys.argv[1]
        company = get_company_by_id(company_id)

        if not company:
            print("\n❌ Could not retrieve company data")
            sys.exit(1)

    print(f"\n✅ Retrieved company: {company.get('name')}")

    # Print overview
    print_company_overview(company)

    # Analyze usage signals
    signals = analyze_company_usage_signals(company)
    print_usage_signals(signals)

    # Save raw data to file for inspection
    output_file = Path(__file__).parent.parent / "company_data.json"
    with open(output_file, "w") as f:
        json.dump(company, f, indent=2)

    print("\n" + "="*80)
    print(f"💾 Full company data saved to: {output_file}")
    print("="*80)


if __name__ == "__main__":
    main()
