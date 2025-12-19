#!/usr/bin/env python3
"""
Test script: Sarah Martinez from Huel books a Calendly meeting.
This specifically tests the enrichment fix.
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
MEETING_TIME = datetime.now(timezone.utc) + timedelta(days=3)
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
    """Create realistic Calendly invitee.created payload for Sarah Martinez"""
    return {
        "event": "invitee.created",
        "payload": {
            "invitee": {
                "email": "sarah.martinez@huel.com",
                "name": "Sarah Martinez",
                "uri": "https://api.calendly.com/scheduled_events/test-sarah-huel-event/invitees/test-sarah-huel-invitee",
                "uuid": "test-sarah-huel-invitee"
            },
            "event": {
                "uri": "https://api.calendly.com/scheduled_events/test-sarah-huel-event",
                "uuid": "test-sarah-huel-event",
                "start_time": MEETING_START_TIME,
                "timezone": "Europe/London"
            },
            "questions_and_answers": [
                {
                    "question": "What is your company name?",
                    "answer": "Huel"
                },
                {
                    "question": "What is your company website?",
                    "answer": "https://huel.com"
                },
                {
                    "question": "What is your role?",
                    "answer": "Director of Brand Marketing"
                },
                {
                    "question": "How many people are on your team?",
                    "answer": "30-40 people in marketing"
                },
                {
                    "question": "What are your main pain points?",
                    "answer": "We create tons of video content for social media and product launches. Our current process for reviews involves Slack threads and it's incredibly messy. We need better collaboration between our in-house team and freelance videographers."
                },
                {
                    "question": "What tools do you currently use?",
                    "answer": "Monday.com for project management, Dropbox for assets, Slack for feedback (which doesn't work well)"
                },
                {
                    "question": "What would you like to see in the demo?",
                    "answer": "How to streamline video review with external freelancers, better annotation tools, version control"
                },
                {
                    "question": "How did you hear about us?",
                    "answer": "LinkedIn ad"
                }
            ],
            "event_type": "https://api.calendly.com/event_types/FBHFVVJGIXH2RYRF"
        }
    }


def send_calendly_webhook():
    """Send Calendly webhook to production"""
    print("\n" + "="*80)
    print("Testing Enrichment Fix: Sarah Martinez from Huel")
    print("="*80)

    payload = create_calendly_payload()
    payload_bytes = json.dumps(payload).encode('utf-8')
    signature = generate_calendly_signature(payload_bytes, CALENDLY_SIGNING_KEY)

    print(f"\nPayload preview:")
    print(f"  Event: {payload['event']}")
    print(f"  Invitee: {payload['payload']['invitee']['name']} <{payload['payload']['invitee']['email']}>")
    print(f"  Company: Huel")
    print(f"  Website: https://huel.com")
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
    print("\n" + "🧪"*40)
    print("ENRICHMENT FIX TEST: Sarah Martinez from Huel")
    print("🧪"*40)
    print("\nThis tests the enrichment bug fix where _build_zoho_payload_from_enrichment")
    print("was missing the 'email' parameter.")
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
    print("\n📊 Check Zoho CRM in 10-15 seconds for the lead:")
    print("   Email: sarah.martinez@huel.com")
    print("   Company: Huel")
    print("\n📝 Expected in Zoho:")
    print("   ✅ Lead created from Calendly with LLM intelligence")
    print("   ✅ Auto-enrichment note with Apollo + Website data")
    print("   ✅ Website scraping results (Huel is a real company)")
    print("   ✅ Company logo uploaded")
    print("\n💡 This test specifically validates the enrichment fix!")
    print("="*80)


if __name__ == "__main__":
    main()
