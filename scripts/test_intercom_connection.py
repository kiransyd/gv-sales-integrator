#!/usr/bin/env python3
"""
Test Intercom API connection and explore available data
"""

import base64
import httpx
from dotenv import load_dotenv
import os

load_dotenv()

INTERCOM_API_KEY = os.getenv("INTERCOM_API_KEY")
INTERCOM_ADMIN_ID = os.getenv("INTERCOM_ADMIN_ID")

# Intercom API base URL
BASE_URL = "https://api.intercom.io"


def test_connection():
    """Test basic Intercom API connection"""
    print("\n" + "="*80)
    print("INTERCOM API CONNECTION TEST")
    print("="*80)

    if not INTERCOM_API_KEY:
        print("❌ INTERCOM_API_KEY not found in environment")
        return False

    print(f"\n✓ API Key found: {INTERCOM_API_KEY[:20]}...")
    print(f"✓ Admin ID: {INTERCOM_ADMIN_ID}")

    headers = {
        "Authorization": f"Bearer {INTERCOM_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    # Test 1: Get current admin info
    print("\n" + "-"*80)
    print("Test 1: Getting current admin info (me)")
    print("-"*80)

    try:
        response = httpx.get(f"{BASE_URL}/me", headers=headers, timeout=10.0)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Connection successful!")
            print(f"   Type: {data.get('type')}")
            print(f"   ID: {data.get('id')}")
            print(f"   Name: {data.get('name')}")
            print(f"   Email: {data.get('email')}")
            print(f"   App: {data.get('app', {}).get('name')}")
        else:
            print(f"❌ Failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    # Test 2: List tags
    print("\n" + "-"*80)
    print("Test 2: Listing available tags")
    print("-"*80)

    try:
        response = httpx.get(f"{BASE_URL}/tags", headers=headers, timeout=10.0)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            tags = data.get('data', [])
            print(f"✅ Found {len(tags)} tags:")
            for tag in tags[:10]:  # Show first 10
                print(f"   - {tag.get('name')} (id: {tag.get('id')})")
            if len(tags) > 10:
                print(f"   ... and {len(tags) - 10} more")
        else:
            print(f"⚠️  Could not fetch tags: {response.text}")
    except Exception as e:
        print(f"⚠️  Error fetching tags: {e}")

    # Test 3: List recent contacts (limited)
    print("\n" + "-"*80)
    print("Test 3: Fetching sample contacts (first 5)")
    print("-"*80)

    try:
        response = httpx.get(
            f"{BASE_URL}/contacts",
            headers=headers,
            params={"per_page": 5},
            timeout=10.0
        )
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            contacts = data.get('data', [])
            print(f"✅ Found contacts (showing {len(contacts)}):")

            for contact in contacts:
                email = contact.get('email') or 'No email'
                name = contact.get('name') or 'No name'
                role = contact.get('role')
                tags = contact.get('tags', {}).get('data', [])
                tag_names = [t.get('name') for t in tags]

                print(f"\n   Contact: {name} <{email}>")
                print(f"   Role: {role}")
                print(f"   ID: {contact.get('id')}")
                if tag_names:
                    print(f"   Tags: {', '.join(tag_names)}")

                # Check if they have a company
                if contact.get('companies'):
                    companies = contact.get('companies', {}).get('data', [])
                    if companies:
                        company = companies[0]
                        print(f"   Company: {company.get('name')} (id: {company.get('id')})")
        else:
            print(f"⚠️  Could not fetch contacts: {response.text}")
    except Exception as e:
        print(f"⚠️  Error fetching contacts: {e}")

    # Test 4: Available webhook topics
    print("\n" + "-"*80)
    print("Test 4: Available webhook topics")
    print("-"*80)
    print("Intercom supports these webhook topics:")
    print("   - contact.created")
    print("   - contact.updated")
    print("   - contact.added_email")
    print("   - contact.tag.created (🎯 useful for qualification)")
    print("   - contact.tag.deleted")
    print("   - conversation.user.created")
    print("   - conversation.user.replied")
    print("   - conversation.admin.replied")
    print("   - conversation.admin.closed")
    print("   ... and more")

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("✅ Intercom API connection is working!")
    print("✅ You can proceed with webhook setup")
    print("\n💡 Recommended approach:")
    print("   1. Use 'contact.tag.created' webhook")
    print("   2. Filter for specific tags (e.g., 'Sales Qualified')")
    print("   3. Create Zoho Lead with Intercom contact + company data")
    print("="*80)

    return True


if __name__ == "__main__":
    test_connection()
