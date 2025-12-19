#!/usr/bin/env python3
"""
Test script: Mike Johnson from Allbirds books a Calendly meeting.
Fresh test to verify enrichment fix is deployed.
"""

import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone

import httpx

# Production configuration
BASE_URL = "https://salesapi.apps.govisually.co"
CALENDLY_SIGNING_KEY = "m6nb-XWn5X7791jp09V9M9dTqsW4Hqw_-ani7I5Tvl4"

# Meeting details
MEETING_TIME = datetime.now(timezone.utc) + timedelta(days=4)
MEETING_START_TIME = MEETING_TIME.isoformat()


def generate_calendly_signature(payload_bytes: bytes, signing_key: str) -> str:
    """Generate Calendly webhook signature"""
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.".encode("utf-8") + payload_bytes
    signature = hmac.new(
        signing_key.encode("utf-8"),
        signed_payload,
        hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={signature}"


def create_calendly_payload():
    """Create realistic Calendly invitee.created payload for Mike Johnson"""
    return {
        "event": "invitee.created",
        "payload": {
            "invitee": {
                "email": "mike.johnson@allbirds.com",
                "name": "Mike Johnson",
                "uri": "https://api.calendly.com/scheduled_events/test-mike-allbirds-event/invitees/test-mike-allbirds-invitee",
                "uuid": "test-mike-allbirds-invitee"
            },
            "event": {
                "uri": "https://api.calendly.com/scheduled_events/test-mike-allbirds-event",
                "uuid": "test-mike-allbirds-event",
                "start_time": MEETING_START_TIME,
                "timezone": "America/New_York"
            },
            "questions_and_answers": [
                {
                    "question": "What is your company name?",
                    "answer": "Allbirds"
                },
                {
                    "question": "What is your company website?",
                    "answer": "https://www.allbirds.com"
                },
                {
                    "question": "What is your role?",
                    "answer": "Head of Digital Content"
                },
                {
                    "question": "How many people are on your team?",
                    "answer": "25 people"
                },
                {
                    "question": "What are your main pain points?",
                    "answer": "We produce a lot of product photography and video content. Getting feedback from our design team, product managers, and external photographers is chaotic. We're using email and it's not working."
                },
                {
                    "question": "What tools do you currently use?",
                    "answer": "Trello, Google Drive, email for reviews"
                },
                {
                    "question": "What would you like to see in the demo?",
                    "answer": "Better way to review product photos and videos with annotations, version control"
                },
                {
                    "question": "How did you hear about us?",
                    "answer": "Google search"
                }
            ],
            "event_type": "https://api.calendly.com/event_types/FBHFVVJGIXH2RYRF"
        }
    }


def send_calendly_webhook():
    """Send Calendly webhook to production"""
    print("\n" + "="*80)
    print("Testing Enrichment Fix: Mike Johnson from Allbirds")
    print("="*80)

    payload = create_calendly_payload()
    payload_bytes = json.dumps(payload).encode('utf-8')
    signature = generate_calendly_signature(payload_bytes, CALENDLY_SIGNING_KEY)

    print(f"\nPayload preview:")
    print(f"  Event: {payload['event']}")
    print(f"  Invitee: {payload['payload']['invitee']['name']} <{payload['payload']['invitee']['email']}>")
    print(f"  Company: Allbirds")
    print(f"  Website: https://www.allbirds.com")
    print(f"  Meeting time: {payload['payload']['event']['start_time']}")

    headers = {
        "Content-Type": "application/json",
        "Calendly-Webhook-Signature": signature
    }

    url = f"{BASE_URL}/webhooks/calendly"
    print(f"\nSending to: {url}")

    try:
        response = httpx.post(url, content=payload_bytes, headers=headers, timeout=30.0)
        print(f"\n✅ Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")

        if response.status_code == 200:
            data = response.json()
            if data.get("queued"):
                print(f"\n🎉 SUCCESS! Calendly webhook queued")
                print(f"Event ID: {data.get('event_id')}")
                print(f"Idempotency Key: {data.get('idempotency_key')}")
                return True
            elif data.get("duplicate"):
                print(f"\n⚠️  DUPLICATE: Event already processed")
                return True
        else:
            print(f"\n❌ FAILED: {response.text}")
            return False

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False


def main():
    print("\n" + "✅"*40)
    print("ENRICHMENT FIX VERIFICATION: Mike Johnson from Allbirds")
    print("✅"*40)
    print("\nThis verifies the deployed fix for the enrichment bug.")
    print("\nTarget environment: PRODUCTION")
    print(f"Base URL: {BASE_URL}")
    print("\n" + "="*80)

    input("\nPress Enter to send webhook...")

    success = send_calendly_webhook()

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Calendly webhook: {'✅ SUCCESS' if success else '❌ FAILED'}")
    print("\n📊 Monitor worker logs and check Zoho CRM for:")
    print("   Email: mike.johnson@allbirds.com")
    print("   Company: Allbirds")
    print("\n📝 Expected in Zoho:")
    print("   ✅ Lead created from Calendly")
    print("   ✅ Auto-Enrichment note with website intelligence")
    print("   ✅ NO enrichment error in worker logs")
    print("   ✅ Allbirds logo uploaded")
    print("\n💡 If enrichment succeeds, the fix is deployed correctly!")
    print("="*80)


if __name__ == "__main__":
    main()
