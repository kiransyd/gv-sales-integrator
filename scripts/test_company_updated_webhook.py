#!/usr/bin/env python3
"""
Test the company.updated webhook by making a test update to a company.

This script:
1. Lists current webhook subscriptions
2. Optionally subscribes to company.updated webhook
3. Updates a test company attribute
4. Monitors for incoming webhook (requires manual verification in logs)

Usage:
    python3 scripts/test_company_updated_webhook.py --list
    python3 scripts/test_company_updated_webhook.py --subscribe
    python3 scripts/test_company_updated_webhook.py --test-update <company_id>
    python3 scripts/test_company_updated_webhook.py --test-update 66311f0fa8475847eb9a281a
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.settings import get_settings


def list_webhook_subscriptions() -> list[dict]:
    """
    List all current webhook subscriptions.

    https://developers.intercom.com/docs/references/rest-api/api.intercom.io/Subscriptions/listSubscriptions/
    """
    settings = get_settings()

    headers = {
        "Authorization": f"Bearer {settings.INTERCOM_API_KEY}",
        "Accept": "application/json",
        "Intercom-Version": "2.11"
    }

    print("🔍 Fetching current webhook subscriptions...")

    try:
        response = httpx.get(
            "https://api.intercom.io/subscriptions",
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        data = response.json()
        subscriptions = data.get("data", [])

        print(f"\n✅ Found {len(subscriptions)} webhook subscription(s):\n")

        for i, sub in enumerate(subscriptions, 1):
            print(f"{i}. Webhook ID: {sub.get('id')}")
            print(f"   URL: {sub.get('url')}")
            print(f"   Active: {sub.get('active')}")
            print(f"   Topics: {', '.join(sub.get('topics', []))}")
            print()

        return subscriptions

    except httpx.HTTPStatusError as e:
        print(f"❌ API error: {e.response.status_code}")
        print(f"   Response: {e.response.text}")
        return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []


def subscribe_to_company_updated(webhook_url: str) -> dict | None:
    """
    Subscribe to company.updated webhook topic.

    NOTE: You need to provide your webhook endpoint URL.

    https://developers.intercom.com/docs/references/rest-api/api.intercom.io/Subscriptions/createSubscription/
    """
    settings = get_settings()

    headers = {
        "Authorization": f"Bearer {settings.INTERCOM_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Intercom-Version": "2.11"
    }

    payload = {
        "url": webhook_url,
        "topics": ["company.updated"]
    }

    print(f"📝 Subscribing to company.updated webhook...")
    print(f"   Webhook URL: {webhook_url}")

    try:
        response = httpx.post(
            "https://api.intercom.io/subscriptions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()

        subscription = response.json()

        print(f"\n✅ Successfully subscribed!")
        print(f"   Subscription ID: {subscription.get('id')}")
        print(f"   Topics: {', '.join(subscription.get('topics', []))}")

        return subscription

    except httpx.HTTPStatusError as e:
        print(f"❌ API error: {e.response.status_code}")
        print(f"   Response: {e.response.text}")

        # Check if already subscribed
        if e.response.status_code == 400:
            print("\n💡 Tip: You may already be subscribed to this topic.")
            print("   Run --list to see current subscriptions.")

        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def update_company_test_attribute(company_id: str) -> dict | None:
    """
    Update a company with a test custom attribute.

    This should trigger the company.updated webhook.

    https://developers.intercom.com/docs/references/rest-api/api.intercom.io/Companies/updateCompany/
    """
    settings = get_settings()

    headers = {
        "Authorization": f"Bearer {settings.INTERCOM_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Intercom-Version": "2.11"
    }

    # Test attribute with timestamp
    test_value = f"webhook_test_{int(time.time())}"

    payload = {
        "id": company_id,
        "custom_attributes": {
            "test_webhook_trigger": test_value,
            "test_webhook_timestamp": int(time.time())
        }
    }

    print(f"🧪 Updating company to test webhook...")
    print(f"   Company ID: {company_id}")
    print(f"   Test value: {test_value}")

    try:
        response = httpx.put(
            f"https://api.intercom.io/companies/{company_id}",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()

        company = response.json()

        print(f"\n✅ Company updated successfully!")
        print(f"   Company: {company.get('name')}")
        print(f"   Updated at: {company.get('updated_at')}")
        print(f"\n📊 Custom attributes now include:")

        custom_attrs = company.get("custom_attributes", {})
        for key, value in custom_attrs.items():
            if key.startswith("test_"):
                print(f"   ✅ {key}: {value}")

        print(f"\n⏳ Waiting for webhook to fire...")
        print(f"   Check your webhook endpoint logs for incoming POST request")
        print(f"   Expected topic: company.updated")
        print(f"   Expected company ID: {company_id}")

        return company

    except httpx.HTTPStatusError as e:
        print(f"❌ API error: {e.response.status_code}")
        print(f"   Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def simulate_real_world_updates(company_id: str):
    """
    Simulate real-world company updates to see which trigger webhooks.

    Tests:
    1. Update custom attribute (e.g., gv_no_of_members)
    2. Add a tag
    3. Update monthly_spend
    """
    settings = get_settings()

    headers = {
        "Authorization": f"Bearer {settings.INTERCOM_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Intercom-Version": "2.11"
    }

    print("🧪 Running simulation of real-world company updates...")
    print(f"   Company ID: {company_id}\n")

    # Test 1: Update gv_no_of_members (simulating team member added)
    print("Test 1: Updating gv_no_of_members (simulating team growth)")
    payload_1 = {
        "id": company_id,
        "custom_attributes": {
            "gv_no_of_members": 17,  # Increment from 16
            "last_test_update": "team_member_added",
            "last_test_timestamp": int(time.time())
        }
    }

    try:
        response = httpx.put(
            f"https://api.intercom.io/companies/{company_id}",
            headers=headers,
            json=payload_1,
            timeout=30
        )
        response.raise_for_status()
        print("   ✅ Updated gv_no_of_members → Should trigger company.updated webhook")
        time.sleep(2)
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 2: Update gv_total_active_projects (simulating project created)
    print("\nTest 2: Updating gv_total_active_projects (simulating project creation)")
    payload_2 = {
        "id": company_id,
        "custom_attributes": {
            "gv_total_active_projects": 23,  # Increment from 22
            "last_test_update": "project_created",
            "last_test_timestamp": int(time.time())
        }
    }

    try:
        response = httpx.put(
            f"https://api.intercom.io/companies/{company_id}",
            headers=headers,
            json=payload_2,
            timeout=30
        )
        response.raise_for_status()
        print("   ✅ Updated gv_total_active_projects → Should trigger company.updated webhook")
        time.sleep(2)
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 3: Update subscription status (simulating payment/cancellation)
    print("\nTest 3: Updating gv_subscription_status (simulating status change)")
    payload_3 = {
        "id": company_id,
        "custom_attributes": {
            "gv_subscription_status": "paid",  # Re-confirm paid status
            "last_test_update": "subscription_confirmed",
            "last_test_timestamp": int(time.time())
        }
    }

    try:
        response = httpx.put(
            f"https://api.intercom.io/companies/{company_id}",
            headers=headers,
            json=payload_3,
            timeout=30
        )
        response.raise_for_status()
        print("   ✅ Updated gv_subscription_status → Should trigger company.updated webhook")
        time.sleep(2)
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n" + "="*80)
    print("✅ Simulation complete!")
    print("\n📊 Results to check:")
    print("   1. Check your webhook endpoint logs (FastAPI logs)")
    print("   2. Look for 3 POST requests to /webhooks/intercom")
    print("   3. Each should have topic: 'company.updated'")
    print("   4. Payload should contain updated company data")
    print("\n💡 If you see the webhooks:")
    print("   → company.updated fires on ANY custom attribute change")
    print("   → You can use this for automatic expansion signal detection!")
    print("="*80)


def revert_test_updates(company_id: str):
    """
    Revert test updates back to original values.
    """
    settings = get_settings()

    headers = {
        "Authorization": f"Bearer {settings.INTERCOM_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Intercom-Version": "2.11"
    }

    print("🔄 Reverting test updates to original values...")

    payload = {
        "id": company_id,
        "custom_attributes": {
            "gv_no_of_members": 16,  # Original value
            "gv_total_active_projects": 22,  # Original value
            "last_test_update": None,
            "last_test_timestamp": None,
            "test_webhook_trigger": None,
            "test_webhook_timestamp": None
        }
    }

    try:
        response = httpx.put(
            f"https://api.intercom.io/companies/{company_id}",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        print("✅ Company reverted to original state")
    except Exception as e:
        print(f"❌ Error reverting: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 scripts/test_company_updated_webhook.py --list")
        print("  python3 scripts/test_company_updated_webhook.py --subscribe <webhook_url>")
        print("  python3 scripts/test_company_updated_webhook.py --test-update <company_id>")
        print("  python3 scripts/test_company_updated_webhook.py --simulate <company_id>")
        print("  python3 scripts/test_company_updated_webhook.py --revert <company_id>")
        print("\nExamples:")
        print("  python3 scripts/test_company_updated_webhook.py --list")
        print("  python3 scripts/test_company_updated_webhook.py --subscribe https://your-domain.com/webhooks/intercom")
        print("  python3 scripts/test_company_updated_webhook.py --test-update 66311f0fa8475847eb9a281a")
        print("  python3 scripts/test_company_updated_webhook.py --simulate 66311f0fa8475847eb9a281a")
        print("  python3 scripts/test_company_updated_webhook.py --revert 66311f0fa8475847eb9a281a")
        sys.exit(1)

    command = sys.argv[1]

    if command == "--list":
        list_webhook_subscriptions()

    elif command == "--subscribe":
        if len(sys.argv) < 3:
            print("❌ Please provide webhook URL")
            print("   Example: python3 scripts/test_company_updated_webhook.py --subscribe https://your-domain.com/webhooks/intercom")
            sys.exit(1)

        webhook_url = sys.argv[2]
        subscribe_to_company_updated(webhook_url)

    elif command == "--test-update":
        if len(sys.argv) < 3:
            print("❌ Please provide company ID")
            print("   Example: python3 scripts/test_company_updated_webhook.py --test-update 66311f0fa8475847eb9a281a")
            sys.exit(1)

        company_id = sys.argv[2]
        update_company_test_attribute(company_id)

    elif command == "--simulate":
        if len(sys.argv) < 3:
            print("❌ Please provide company ID")
            print("   Example: python3 scripts/test_company_updated_webhook.py --simulate 66311f0fa8475847eb9a281a")
            sys.exit(1)

        company_id = sys.argv[2]

        print("="*80)
        print("⚠️  WARNING: This will temporarily modify company data")
        print("="*80)
        print(f"Company ID: {company_id}")
        print("\nChanges that will be made:")
        print("  • gv_no_of_members: 16 → 17 → 16")
        print("  • gv_total_active_projects: 22 → 23 → 22")
        print("  • Add temporary test attributes")
        print("\nThese changes simulate real user actions (adding team member, creating project)")
        print("\nThe script will:")
        print("  1. Make test updates")
        print("  2. Check if webhooks fire")
        print("  3. Revert to original values (optional)")

        confirm = input("\nProceed with simulation? (yes/no): ")

        if confirm.lower() in ["yes", "y"]:
            simulate_real_world_updates(company_id)

            revert = input("\nRevert changes back to original values? (yes/no): ")
            if revert.lower() in ["yes", "y"]:
                revert_test_updates(company_id)
        else:
            print("❌ Simulation cancelled")

    elif command == "--revert":
        if len(sys.argv) < 3:
            print("❌ Please provide company ID")
            sys.exit(1)

        company_id = sys.argv[2]
        revert_test_updates(company_id)

    else:
        print(f"❌ Unknown command: {command}")
        print("   Use --list, --subscribe, --test-update, --simulate, or --revert")
        sys.exit(1)


if __name__ == "__main__":
    main()
