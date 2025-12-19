#!/usr/bin/env python3
"""
Test script: Intercom contact tagged with "Lead" tag.
This tests the full Intercom → Zoho Lead integration.
"""

import hashlib
import hmac
import json
import time

import httpx

# Production configuration
BASE_URL = "https://salesapi.apps.govisually.co"
INTERCOM_WEBHOOK_SECRET = ""  # Empty if not configured

# Test contact details
TEST_CONTACT = {
    "email": "emma.wilson@craftbrew.io",
    "name": "Emma Wilson",
    "phone": "+1-555-789-0123",
    "company": "CraftBrew",
    "company_website": "https://craftbrew.io",
    "company_size": 45,
    "company_industry": "Food & Beverage",
}


def generate_intercom_signature(payload_bytes: bytes, secret: str) -> str:
    """Generate Intercom webhook signature using HMAC SHA256"""
    if not secret:
        return ""

    signature = hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()

    return signature


def create_intercom_payload():
    """
    Create realistic Intercom contact.user.tag.created webhook payload.

    This simulates what Intercom sends when a user/contact is tagged with "Lead".
    """
    created_at = int(time.time())

    return {
        "type": "notification_event",
        "topic": "contact.user.tag.created",
        "created_at": created_at,
        "data": {
            "type": "notification_event_data",
            "item": {
                "type": "contact",
                "id": "67890abcdef12345",
                "external_id": "",
                "email": TEST_CONTACT["email"],
                "name": TEST_CONTACT["name"],
                "phone": TEST_CONTACT["phone"],
                "custom_attributes": {
                    "source": "Website Chat",
                    "initial_inquiry": "Interested in video collaboration tools",
                    "conversations": 3,
                },
                "companies": {
                    "type": "list",
                    "data": [
                        {
                            "type": "company",
                            "id": "company_12345xyz",
                            "name": TEST_CONTACT["company"],
                            "website": TEST_CONTACT["company_website"],
                            "company_id": "craftbrew_io",
                            "size": TEST_CONTACT["company_size"],
                            "industry": TEST_CONTACT["company_industry"],
                        }
                    ]
                },
                "tags": {
                    "type": "list",
                    "data": [
                        {
                            "type": "tag",
                            "id": "tag_lead_001",
                            "name": "Lead"
                        },
                        {
                            "type": "tag",
                            "id": "tag_hot_002",
                            "name": "Hot"
                        }
                    ]
                },
                "created_at": created_at - 86400,  # Contact created 1 day ago
                "updated_at": created_at,
            }
        }
    }


def send_intercom_webhook():
    """Send Intercom webhook to production"""
    print("\n" + "="*80)
    print("Testing Intercom Webhook: Contact Tagged with 'Lead'")
    print("="*80)

    payload = create_intercom_payload()
    payload_bytes = json.dumps(payload).encode('utf-8')

    print(f"\nPayload preview:")
    print(f"  Topic: {payload['topic']}")
    print(f"  Contact: {payload['data']['item']['name']} <{payload['data']['item']['email']}>")
    print(f"  Company: {TEST_CONTACT['company']}")
    print(f"  Website: {TEST_CONTACT['company_website']}")
    print(f"  Tags: Lead, Hot")

    headers = {
        "Content-Type": "application/json"
    }

    if INTERCOM_WEBHOOK_SECRET:
        signature = generate_intercom_signature(payload_bytes, INTERCOM_WEBHOOK_SECRET)
        headers["X-Intercom-Signature"] = signature
        print(f"  Signature: {signature[:20]}...")
    else:
        print(f"  Signature: Not configured (will be skipped)")

    url = f"{BASE_URL}/webhooks/intercom"
    print(f"\nSending to: {url}")

    try:
        response = httpx.post(url, content=payload_bytes, headers=headers, timeout=30.0)
        print(f"\n✅ Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")

        if response.status_code == 200:
            data = response.json()
            if data.get("queued"):
                print(f"\n🎉 SUCCESS! Intercom webhook queued")
                print(f"Event ID: {data.get('event_id')}")
                print(f"Idempotency Key: {data.get('idempotency_key')}")
                return True
            elif data.get("duplicate"):
                print(f"\n⚠️  DUPLICATE: Event already processed")
                return True
            elif data.get("ignored"):
                print(f"\n⚠️  IGNORED: {data.get('reason')}")
                return True
        else:
            print(f"\n❌ FAILED: {response.text}")
            return False

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False


def main():
    print("\n" + "🎯"*40)
    print("INTERCOM INTEGRATION TEST: Emma Wilson from CraftBrew")
    print("🎯"*40)
    print("\nThis tests:")
    print("  1. Intercom webhook processing")
    print("  2. Contact tagged with 'Lead' triggers Zoho lead creation")
    print("  3. Company data extraction from Intercom")
    print("  4. Auto-enrichment with Apollo + Website (if enabled)")
    print("  5. Slack notification")
    print("\nTarget environment: PRODUCTION")
    print(f"Base URL: {BASE_URL}")
    print("\n" + "="*80)

    input("\nPress Enter to send webhook...")

    success = send_intercom_webhook()

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Intercom webhook: {'✅ SUCCESS' if success else '❌ FAILED'}")
    print("\n📊 Monitor worker logs and check Zoho CRM for:")
    print(f"   Email: {TEST_CONTACT['email']}")
    print(f"   Company: {TEST_CONTACT['company']}")
    print("\n📝 Expected in Zoho:")
    print("   ✅ Lead created from Intercom")
    print("   ✅ Lead status: 'Qualified'")
    print("   ✅ Lead source: 'Intercom'")
    print("   ✅ Company info populated")
    print("   ✅ Intercom contact note created")
    print("   ✅ Auto-enrichment note (if enabled)")
    print("   ✅ Company logo uploaded (if available)")
    print("\n💡 Check Zoho Lead and Slack notification!")
    print("="*80)


if __name__ == "__main__":
    main()
