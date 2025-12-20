#!/usr/bin/env python3
"""
Simple script to test company.updated webhook by making a test update.

Usage:
    python3 scripts/test_company_update_simple.py <company_id>
"""

import json
import sys
import time
from pathlib import Path

import httpx

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.settings import get_settings


def update_company_test(company_id: str):
    """Update company with test attribute to trigger webhook."""
    settings = get_settings()

    headers = {
        "Authorization": f"Bearer {settings.INTERCOM_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Intercom-Version": "2.11"
    }

    # Make a small test update using existing attribute
    # We'll increment gv_checklists temporarily to test the webhook
    test_value = int(time.time()) % 100  # Use timestamp mod 100 as test value

    payload = {
        "id": company_id,
        "custom_attributes": {
            "gv_checklists": test_value  # Update existing attribute
        }
    }

    print(f"🧪 Testing company.updated webhook")
    print(f"   Company ID: {company_id}")
    print(f"   Adding test attribute: {test_value}\n")

    try:
        response = httpx.put(
            f"https://api.intercom.io/companies/{company_id}",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()

        company = response.json()

        print(f"✅ Company updated successfully!")
        print(f"   Company: {company.get('name')}")
        print(f"   Updated at: {company.get('updated_at')}")

        print(f"\n📊 Company data:")
        print(f"   ID: {company.get('id')}")
        print(f"   Name: {company.get('name')}")
        print(f"   User count: {company.get('user_count')}")

        custom_attrs = company.get("custom_attributes", {})
        print(f"\n⚙️  Custom Attributes:")
        for key, value in sorted(custom_attrs.items()):
            print(f"   {key}: {value}")

        print(f"\n⏳ If company.updated webhook is configured:")
        print(f"   → Check your webhook endpoint logs")
        print(f"   → Look for POST to /webhooks/intercom")
        print(f"   → Topic should be: 'company.updated'")
        print(f"   → Company ID should be: {company_id}")

        # Save full response
        output_file = Path(__file__).parent.parent / "company_update_response.json"
        with open(output_file, "w") as f:
            json.dump(company, f, indent=2)

        print(f"\n💾 Full response saved to: {output_file}")

        return company

    except httpx.HTTPStatusError as e:
        print(f"❌ API error: {e.response.status_code}")
        print(f"   Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/test_company_update_simple.py <company_id>")
        print("Example: python3 scripts/test_company_update_simple.py 66311f0fa8475847eb9a281a")
        sys.exit(1)

    company_id = sys.argv[1]
    update_company_test(company_id)


if __name__ == "__main__":
    main()
