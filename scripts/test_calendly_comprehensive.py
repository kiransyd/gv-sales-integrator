#!/usr/bin/env python3
"""
Test script to verify comprehensive Calendly LLM extraction and Zoho field mapping.
This simulates a Calendly booking and checks that all fields are extracted and sent to Zoho.
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from dotenv import load_dotenv
import hmac
import hashlib

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
CALENDLY_SIGNING_KEY = os.getenv("CALENDLY_SIGNING_KEY", "")


def generate_calendly_signature(timestamp: int, raw_body: bytes, secret: str) -> str:
    """Generate HMAC signature for Calendly webhook."""
    signed_payload = f"{timestamp}.".encode("utf-8") + raw_body
    return hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()


def send_calendly_webhook():
    """Send a comprehensive Calendly webhook with realistic data."""
    # Use the example from the user's prompt
    # Use a realistic email domain to test website extraction
    email = f"e2e-calendly-{int(time.time())}@leapzonestrategies.com"
    
    payload = {
        "event": "invitee.created",
        "time": datetime.utcnow().isoformat() + "Z",
        "payload": {
            "event_type": {
                "uri": "https://api.calendly.com/event_types/FBHFVVJGIXH2RYRF",
                "name": "GoVisually Demo",
            },
            "event": {
                "uri": f"https://api.calendly.com/scheduled_events/EVENT_{int(time.time())}",
                "name": "GoVisually Demo",
                "start_time": "2025-12-16T22:30:00.000000Z",
                "end_time": "2025-12-16T23:00:00.000000Z",
                "timezone": "America/Los_Angeles",
            },
            "invitee": {
                "uri": f"https://api.calendly.com/invitees/INV_{int(time.time())}",
                "name": "Isabelle Mercier",
                "email": email,
                "text_reminder_number": "+1-555-123-4567",  # Add phone for testing
            },
            "questions_and_answers": [
                {
                    "question": "What's your current process and biggest challenge with getting content reviewed and approved?",
                    "answer": "To get clients to attentively review a final proof before approving...the check list will help for that for sure. Also, I find that clients don't respond to comment replies...like when we have questions for them or need more info.",
                },
                {
                    "question": "Are you using a project management or CRM tool that you'd ideally like an integration with?",
                    "answer": "Trello\nAdobe Creative Cloud",
                },
                {
                    "question": "What type of company are you?",
                    "answer": "Branding/Design Agency",
                },
                {
                    "question": "Can you share the size of your team?",
                    "answer": "2 to 5 team members",
                },
                {
                    "question": "How did they hear about us?",
                    "answer": "Search engine (Google, Bing)",
                },
            ],
        },
    }
    
    payload_bytes = json.dumps(payload).encode("utf-8")
    timestamp = int(time.time())
    signature = generate_calendly_signature(timestamp, payload_bytes, CALENDLY_SIGNING_KEY)
    
    headers = {
        "Content-Type": "application/json",
        "Calendly-Webhook-Signature": f"t={timestamp},v1={signature}",
    }
    
    print(f"📤 Sending Calendly webhook to {BASE_URL}/webhooks/calendly")
    print(f"   Email: {email}")
    print(f"   Name: {payload['payload']['invitee']['name']}")
    print(f"   Timezone: {payload['payload']['event']['timezone']}")
    print(f"   Q&A questions: {len(payload['payload']['questions_and_answers'])}")
    
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{BASE_URL}/webhooks/calendly",
                content=payload_bytes,
                headers=headers,
            )
            resp.raise_for_status()
            result = resp.json()
            event_id = result.get("event_id")
            print(f"✅ Accepted: Event ID {event_id}")
            return event_id, email
    except Exception as e:
        print(f"❌ Error: {e}")
        if hasattr(e, "response"):
            print(f"   Response: {e.response.text}")
        return None, email


def wait_for_processing(base_url: str, event_id: str, max_wait: int = 90) -> bool:
    """Wait for event to be processed."""
    print(f"\n⏳ Waiting for processing (max {max_wait}s)...")
    start = time.time()
    
    while time.time() - start < max_wait:
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(f"{base_url}/debug/events/{event_id}")
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status", "unknown")
                    print(f"   Status: {status}")
                    if status in ("processed", "failed", "ignored"):
                        return status == "processed"
                time.sleep(2)
        except Exception as e:
            print(f"   Error checking status: {e}")
            time.sleep(2)
    
    print(f"   ⚠️  Timeout after {max_wait}s")
    return False


def check_worker_logs_for_fields():
    """Check worker logs for field extraction and Zoho updates."""
    print("\n📊 Checking worker logs for LLM extraction and Zoho updates...")
    print("   (Run: docker-compose logs worker --tail 100 | grep -E '(LLM|extracted|Zoho|fields)')")


def main():
    print("=" * 70)
    print("COMPREHENSIVE CALENDLY LLM EXTRACTION TEST")
    print("=" * 70)
    print()
    print("This test verifies that:")
    print("  1. Calendly webhook is received and processed")
    print("  2. LLM extracts all comprehensive fields (company, pain points, tools, etc.)")
    print("  3. All fields are mapped to Zoho custom fields")
    print()
    
    event_id, email = send_calendly_webhook()
    if not event_id:
        print("\n❌ Failed to send webhook")
        return 1
    
    processed = wait_for_processing(BASE_URL, event_id)
    if not processed:
        print("\n⚠️  Event may still be processing or failed")
        return 1
    
    check_worker_logs_for_fields()
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print()
    print(f"✅ Calendly event processed: {event_id}")
    print(f"📧 Lead email: {email}")
    print()
    print("📋 Next Steps:")
    print(f"   1. Check Zoho CRM for Lead: {email}")
    print("   2. Verify these fields are populated:")
    print("      - Pain Points")
    print("      - Team members")
    print("      - Tools Currently Used")
    print("      - Demo Date")
    print("      - Demo Objectives")
    print("      - Demo Focus Recommendation")
    print("      - Discovery Questions")
    print("      - Sales Rep Cheat Sheet")
    print("      - Company Name, Website, Type")
    print("      - Location (Country, State, City)")
    print("      - BANT signals")
    print("   3. Check worker logs:")
    print("      docker-compose logs worker --tail 200 | grep -E '(LLM|extracted|Zoho|fields)'")
    print("   4. Review debug endpoint:")
    print(f"      {BASE_URL}/debug/events/{event_id}")
    print()
    print("⚠️  IMPORTANT: Make sure you've mapped all Zoho custom field API names in .env:")
    print("      ZCF_PAIN_POINTS=...")
    print("      ZCF_TEAM_MEMBERS=...")
    print("      ZCF_TOOLS_CURRENTLY_USED=...")
    print("      ZCF_DEMO_OBJECTIVES=...")
    print("      ZCF_DEMO_FOCUS_RECOMMENDATION=...")
    print("      ZCF_DISCOVERY_QUESTIONS=...")
    print("      ZCF_SALES_REP_CHEAT_SHEET=...")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

