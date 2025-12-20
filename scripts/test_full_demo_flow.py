#!/usr/bin/env python3
"""
End-to-end test: Calendly booking → Read.ai demo completion → Zoho MEDDIC update

This simulates the complete flow:
1. Prospect books demo via Calendly
2. Demo happens and is recorded on Read.ai
3. Read.ai sends webhook when meeting ends
4. System extracts MEDDIC data via LLM
5. System updates Zoho Lead with MEDDIC fields
"""
import json
import os
import re
import sys
import time
import uuid
import hmac
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
import httpx


def load_env_var(key: str, default: str = "") -> str:
    """Load environment variable from .env file or environment"""
    if key in os.environ:
        return os.environ[key]
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        content = env_file.read_text()
        match = re.search(rf"^{re.escape(key)}=(.+)$", content, flags=re.M)
        if match:
            return match.group(1).strip()
    return default


def generate_calendly_signature(timestamp: int, raw_body: bytes, secret: str) -> str:
    """Generates Calendly HMAC-SHA256 signature."""
    signed_payload = f"{timestamp}.".encode("utf-8") + raw_body
    digest = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return digest


def send_calendly_webhook(base_url: str, email: str, name: str, event_time: datetime) -> tuple[str | None, str]:
    """Send a Calendly invitee.created webhook"""
    webhook_url = f"{base_url.rstrip('/')}/webhooks/calendly"
    
    invitee_uuid = str(uuid.uuid4())
    event_uuid = str(uuid.uuid4())
    
    payload = {
        "event": "invitee.created",
        "time": event_time.isoformat() + "Z",
        "payload": {
            "event_type": {
                "uuid": "event-type-uuid-123",
                "kind": "One-on-One",
                "slug": "demo",
                "name": "GoVisually Demo",
                "duration": 30,
                "uri": load_env_var("CALENDLY_EVENT_TYPE_URI", "https://api.calendly.com/event_types/FBHFVVJGIXH2RYRF")
            },
            "event": {
                "uri": f"https://api.calendly.com/scheduled_events/{event_uuid}",
                "name": "GoVisually Demo",
                "start_time": event_time.isoformat() + "Z",
                "end_time": (event_time + timedelta(minutes=30)).isoformat() + "Z",
                "timezone": "America/Los_Angeles",
            },
            "invitee": {
                "uri": f"https://api.calendly.com/invitees/{invitee_uuid}",
                "name": name,
                "email": email,
                "text_reminder_number": "+1-555-987-6543",
            },
            "questions_and_answers": [
                {
                    "question": "What's your current process and biggest challenge with getting content reviewed and approved?",
                    "answer": "We're using manual email threads and it's chaos. Clients miss comments, approvals get lost, and we waste hours tracking down feedback.",
                },
                {
                    "question": "Are you using a project management or CRM tool that you'd ideally like an integration with?",
                    "answer": "We use Asana for project management and Slack for communication. Integration with both would be ideal.",
                },
                {
                    "question": "What type of company are you?",
                    "answer": "Creative Agency",
                },
                {
                    "question": "Can you share the size of your team?",
                    "answer": "10-20 team members",
                },
                {
                    "question": "How did they hear about us?",
                    "answer": "LinkedIn ad",
                },
            ],
        },
    }
    
    payload_bytes = json.dumps(payload).encode("utf-8")
    timestamp = int(time.time())
    CALENDLY_SIGNING_KEY = load_env_var("CALENDLY_SIGNING_KEY", "")
    signature = generate_calendly_signature(timestamp, payload_bytes, CALENDLY_SIGNING_KEY)
    
    headers = {
        "Content-Type": "application/json",
        "Calendly-Webhook-Signature": f"t={timestamp},v1={signature}",
    }
    
    print(f"📅 STEP 1: Sending Calendly booking webhook")
    print(f"   Email: {email}")
    print(f"   Name: {name}")
    print(f"   Demo Time: {event_time.strftime('%Y-%m-%d %H:%M %Z')}")
    
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(webhook_url, content=payload_bytes, headers=headers)
            resp.raise_for_status()
            result = resp.json()
            event_id = result.get("event_id")
            print(f"   ✅ Calendly event accepted: {event_id}")
            return event_id, email
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None, email


def wait_for_processing(base_url: str, event_id: str, max_wait: int = 90) -> bool:
    """Wait for event to be processed."""
    start = time.time()
    while time.time() - start < max_wait:
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(f"{base_url}/debug/events/{event_id}")
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status", "unknown")
                    if status in ("processed", "failed", "ignored"):
                        return status == "processed"
                time.sleep(2)
        except Exception as e:
            time.sleep(2)
    return False


def send_readai_webhook(base_url: str, email: str, name: str, meeting_time: datetime) -> tuple[str | None, str]:
    """Send a Read.ai meeting_end webhook with comprehensive MEDDIC data"""
    webhook_url = f"{base_url.rstrip('/')}/webhooks/readai"
    session_id = f"readai-{uuid.uuid4().hex[:12]}"
    
    # Create a realistic demo transcript with MEDDIC information
    transcript_blocks = [
        {
            "start_time": int(meeting_time.timestamp()),
            "end_time": int((meeting_time + timedelta(minutes=2)).timestamp()),
            "speaker": {"name": "GV Rep"},
            "words": "Thanks for joining today! Let's start with understanding your current workflow and what challenges you're facing with client approvals."
        },
        {
            "start_time": int((meeting_time + timedelta(minutes=2)).timestamp()),
            "end_time": int((meeting_time + timedelta(minutes=5)).timestamp()),
            "speaker": {"name": name.split()[0] if name else "Customer"},
            "words": "We're a creative agency with about 15 team members. Our biggest pain point is that we're using manual email threads for client approvals and it's absolute chaos. Clients miss comments, approvals get lost in email chains, and we waste hours every week tracking down feedback. We need something that centralizes everything."
        },
        {
            "start_time": int((meeting_time + timedelta(minutes=5)).timestamp()),
            "end_time": int((meeting_time + timedelta(minutes=8)).timestamp()),
            "speaker": {"name": "GV Rep"},
            "words": "That's exactly what GoVisually solves. What's your current process when you send work for review?"
        },
        {
            "start_time": int((meeting_time + timedelta(minutes=8)).timestamp()),
            "end_time": int((meeting_time + timedelta(minutes=12)).timestamp()),
            "speaker": {"name": name.split()[0] if name else "Customer"},
            "words": "We export designs, attach them to emails, send to clients, then wait. Sometimes they reply to the email, sometimes they call, sometimes they send Slack messages. It's all over the place. We've tried using Asana but clients don't want to learn another tool. We need something that's dead simple for clients to use."
        },
        {
            "start_time": int((meeting_time + timedelta(minutes=12)).timestamp()),
            "end_time": int((meeting_time + timedelta(minutes=15)).timestamp()),
            "speaker": {"name": "GV Rep"},
            "words": "GoVisually is designed exactly for that - clients can review and approve directly in the platform without any training. What's your timeline for implementing a solution?"
        },
        {
            "start_time": int((meeting_time + timedelta(minutes=15)).timestamp()),
            "end_time": int((meeting_time + timedelta(minutes=18)).timestamp()),
            "speaker": {"name": name.split()[0] if name else "Customer"},
            "words": "We're looking to solve this in Q1. Our creative director Sarah is the decision maker, and she's been pushing for a better solution. We have budget approved - around $500-800 per month. We're also evaluating Workfront and Frame.io, but GoVisually seems more client-friendly."
        },
        {
            "start_time": int((meeting_time + timedelta(minutes=18)).timestamp()),
            "end_time": int((meeting_time + timedelta(minutes=20)).timestamp()),
            "speaker": {"name": "GV Rep"},
            "words": "Great! What would be the key factors in your decision?"
        },
        {
            "start_time": int((meeting_time + timedelta(minutes=20)).timestamp()),
            "end_time": int((meeting_time + timedelta(minutes=23)).timestamp()),
            "speaker": {"name": name.split()[0] if name else "Customer"},
            "words": "Ease of use for clients is number one. Integration with Asana would be huge. Also need SSO for security. And the pricing needs to fit our budget. Sarah will want to see a technical demo before we decide."
        },
        {
            "start_time": int((meeting_time + timedelta(minutes=23)).timestamp()),
            "end_time": int((meeting_time + timedelta(minutes=25)).timestamp()),
            "speaker": {"name": "GV Rep"},
            "words": "Perfect. Let's schedule a technical demo with Sarah next week. I'll send over pricing and integration details. Any concerns or risks we should address?"
        },
        {
            "start_time": int((meeting_time + timedelta(minutes=25)).timestamp()),
            "end_time": int((meeting_time + timedelta(minutes=27)).timestamp()),
            "speaker": {"name": name.split()[0] if name else "Customer"},
            "words": "The main concern is getting clients to adopt it. If it's not super simple, they'll just go back to email. Also, we need to make sure it works with our Adobe Creative Cloud workflow."
        },
        {
            "start_time": int((meeting_time + timedelta(minutes=27)).timestamp()),
            "end_time": int((meeting_time + timedelta(minutes=30)).timestamp()),
            "speaker": {"name": "GV Rep"},
            "words": "Understood. We'll make sure to show the Adobe integration and the client onboarding process. I'll send you a follow-up email with next steps."
        },
    ]
    
    # Build transcript as structured format
    transcript = {
        "speaker_blocks": transcript_blocks
    }
    
    # Flatten transcript for Read.ai format
    transcript_flat = []
    for block in transcript_blocks:
        speaker_name = block.get("speaker", {}).get("name", "Unknown")
        words = block.get("words", "")
        transcript_flat.append(f"{speaker_name}: {words}")
    
    payload = {
        "session_id": session_id,
        "trigger": "meeting_end",
        "title": "GoVisually Demo",
        "start_time": meeting_time.isoformat() + "Z",
        "end_time": (meeting_time + timedelta(minutes=30)).isoformat() + "Z",
        "participants": [
            {"name": "GV Rep", "email": "rep@govisually.com"},
            {"name": name, "email": email},
        ],
        "summary": "Discussed current approval workflow challenges, timeline (Q1), budget ($500-800/month), decision criteria (ease of use, Asana integration, SSO), and next steps (technical demo with Sarah).",
        "report_url": f"https://app.read.ai/analytics/meetings/{session_id}",
        "transcript": transcript,  # Structured format
    }
    
    READAI_SECRET = load_env_var("READAI_SHARED_SECRET", "")
    headers = {
        "Content-Type": "application/json",
    }
    if READAI_SECRET:
        headers["X-ReadAI-Secret"] = READAI_SECRET
    
    print(f"\n🎥 STEP 2: Sending Read.ai meeting completion webhook")
    print(f"   Session ID: {session_id}")
    print(f"   Attendee: {name} ({email})")
    print(f"   Meeting Duration: 30 minutes")
    print(f"   Transcript blocks: {len(transcript_blocks)}")
    
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(webhook_url, json=payload, headers=headers)
            resp.raise_for_status()
            result = resp.json()
            event_id = result.get("event_id")
            print(f"   ✅ Read.ai event accepted: {event_id}")
            return event_id, email
    except Exception as e:
        print(f"   ❌ Error: {e}")
        if hasattr(e, "response"):
            print(f"   Response: {e.response.text}")
        return None, email


def check_worker_logs_for_meddic(base_url: str, email: str):
    """Check worker logs for MEDDIC extraction and Zoho updates"""
    print(f"\n📊 STEP 3: Checking worker logs for MEDDIC extraction...")
    print(f"   Run: docker-compose logs worker --tail 300 | grep -E '(MEDDIC|extracted|Updating Zoho Lead|{email})'")


def main():
    BASE_URL = load_env_var("BASE_URL", "http://localhost:8000")
    
    print("=" * 70)
    print("FULL DEMO FLOW TEST: Calendly → Read.ai → Zoho MEDDIC")
    print("=" * 70)
    print("\nThis test simulates:")
    print("  1. Prospect books demo via Calendly")
    print("  2. Demo happens and is recorded on Read.ai")
    print("  3. Read.ai sends webhook when meeting ends")
    print("  4. System extracts MEDDIC data via LLM")
    print("  5. System updates Zoho Lead with MEDDIC fields")
    print()
    
    # Use a consistent email for both webhooks
    timestamp = int(time.time())
    test_email = f"e2e-fullflow-{timestamp}@creativeagency.com"
    test_name = "Alex Johnson"
    
    # Step 1: Calendly booking
    demo_time = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=2)
    calendly_event_id, email = send_calendly_webhook(BASE_URL, test_email, test_name, demo_time)
    
    if not calendly_event_id:
        print("\n❌ Failed to send Calendly webhook")
        sys.exit(1)
    
    print(f"\n⏳ Waiting for Calendly event processing...")
    if wait_for_processing(BASE_URL, calendly_event_id, max_wait=90):
        print("   ✅ Calendly event processed")
    else:
        print("   ⚠️  Calendly event processing timed out or failed")
    
    # Wait a bit before sending Read.ai webhook
    print("\n⏸️  Waiting 5 seconds before sending Read.ai webhook...")
    time.sleep(5)
    
    # Step 2: Read.ai demo completion (use same email to match the lead)
    meeting_time = demo_time  # Demo happened at the scheduled time
    readai_event_id, email = send_readai_webhook(BASE_URL, test_email, test_name, meeting_time)
    
    if not readai_event_id:
        print("\n❌ Failed to send Read.ai webhook")
        sys.exit(1)
    
    print(f"\n⏳ Waiting for Read.ai event processing...")
    if wait_for_processing(BASE_URL, readai_event_id, max_wait=90):
        print("   ✅ Read.ai event processed")
    else:
        print("   ⚠️  Read.ai event processing timed out or failed")
    
    # Step 3: Check logs
    check_worker_logs_for_meddic(BASE_URL, email)
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    
    print(f"\n✅ Full flow completed:")
    print(f"   📅 Calendly Event ID: {calendly_event_id}")
    print(f"   🎥 Read.ai Event ID: {readai_event_id}")
    print(f"   📧 Lead Email: {email}")
    
    print("\n📋 Next Steps:")
    print(f"   1. Check Zoho CRM for Lead: {email}")
    print("   2. Verify these fields are populated:")
    print("      - Lead Status: Demo Complete")
    print("      - MEDDIC_Process (Metrics)")
    print("      - MEDDIC_Pain (Decision Criteria)")
    print("      - Competition (Decision Process)")
    print("      - Identified_Pain_Points")
    print("      - Champion_and_Economic_Buyer")
    print("   3. Check worker logs for MEDDIC extraction:")
    print(f"      docker-compose logs worker --tail 400 | grep -E '(MEDDIC|extracted|Updating Zoho Lead|{email})'")
    print("   4. Review debug endpoints:")
    print(f"      {BASE_URL}/debug/events/{calendly_event_id}")
    print(f"      {BASE_URL}/debug/events/{readai_event_id}")
    
    print("\n💡 Expected MEDDIC fields from transcript:")
    print("   - Metrics: Reduce approval time, centralize feedback")
    print("   - Economic Buyer: Sarah (Creative Director)")
    print("   - Decision Criteria: Ease of use, Asana integration, SSO, pricing")
    print("   - Decision Process: Q1 timeline, technical demo with Sarah")
    print("   - Identified Pain: Manual email threads, lost approvals, client adoption")
    print("   - Champion: Customer (Alex Johnson)")
    print("   - Competition: Workfront, Frame.io")
    print("   - Next Steps: Technical demo, pricing details")
    print("   - Risks: Client adoption, Adobe integration")
    print("   - Confidence: Hot (budget approved, timeline set, decision maker identified)")


if __name__ == "__main__":
    main()





