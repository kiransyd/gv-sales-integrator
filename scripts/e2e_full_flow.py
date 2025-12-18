#!/usr/bin/env python3
"""
End-to-End Full Flow Test: Calendly Booking → Demo → Zoho Updates

Simulates the complete customer journey:
1. Customer books a Calendly demo (invitee.created)
2. System creates/enriches Lead in Zoho
3. Demo happens (Read.ai meeting_end)
4. System extracts MEDDIC and updates Lead in Zoho
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
import requests

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

def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def print_step(step_num: int, title: str):
    """Print a step header"""
    print(f"\n{'─'*70}")
    print(f"STEP {step_num}: {title}")
    print(f"{'─'*70}")

def send_calendly_webhook(base_url: str, email: str, name: str, event_time: datetime) -> dict:
    """Send a Calendly invitee.created webhook"""
    webhook_url = f"{base_url.rstrip('/')}/webhooks/calendly"
    
    # Generate unique Calendly URIs
    invitee_uuid = str(uuid.uuid4())
    event_uuid = str(uuid.uuid4())
    
    payload = {
        "event": "invitee.created",
        "time": event_time.isoformat(),
        "payload": {
            "invitee": {
                "uuid": invitee_uuid,
                "name": name,
                "email": email,
                "uri": f"https://api.calendly.com/scheduled_events/{event_uuid}/invitees/{invitee_uuid}",
                "text_reminder_number": None,
                "timezone": "America/New_York",
                "event_guests": [],
                "event_guest_statuses": [],
                "created_at": (event_time - timedelta(days=1)).isoformat(),
                "updated_at": (event_time - timedelta(days=1)).isoformat(),
                "canceled": False,
                "cancellation": None,
                "payment": None,
                "tracking": {
                    "utm_campaign": None,
                    "utm_source": None,
                    "utm_medium": None,
                    "utm_content": None,
                    "utm_term": None,
                    "salesforce_uuid": None
                },
                "rescheduled": False
            },
            "event": {
                "uuid": event_uuid,
                "uri": f"https://api.calendly.com/scheduled_events/{event_uuid}",
                "start_time": event_time.isoformat(),
                "end_time": (event_time + timedelta(minutes=30)).isoformat(),
                "timezone": "America/New_York",
                "created_at": (event_time - timedelta(days=1)).isoformat(),
                "updated_at": (event_time - timedelta(days=1)).isoformat()
            },
            "event_type": {
                "uuid": "event-type-uuid-123",
                "kind": "One-on-One",
                "slug": "demo",
                "name": "GoVisually Demo",
                "duration": 30,
                "uri": "https://api.calendly.com/event_types/event-type-uuid-123"
            },
            "questions_and_answers": [
                {
                    "question": "What's your role?",
                    "answer": "Packaging Manager"
                },
                {
                    "question": "What's your company size?",
                    "answer": "500-1000 employees"
                }
            ]
        }
    }
    
    headers = {"Content-Type": "application/json"}
    calendly_key = load_env_var("CALENDLY_SIGNING_KEY", "")
    if calendly_key:
        # Generate proper Calendly signature: t=timestamp,v1=hexsignature
        # Signature is HMAC-SHA256 of "{timestamp}.{raw_body}"
        timestamp = int(time.time())
        raw_body = json.dumps(payload).encode("utf-8")
        signed_payload = f"{timestamp}.".encode("utf-8") + raw_body
        signature = hmac.new(calendly_key.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
        headers["Calendly-Webhook-Signature"] = f"t={timestamp},v1={signature}"
    
    print(f"   📤 Sending to: {webhook_url}")
    print(f"   👤 Attendee: {name} ({email})")
    print(f"   📅 Event Time: {event_time.strftime('%Y-%m-%d %H:%M %Z')}")
    
    response = requests.post(webhook_url, json=payload, headers=headers, timeout=30)
    
    if response.status_code != 200:
        print(f"   ❌ Failed: {response.status_code} - {response.text}")
        return None
    
    result = response.json()
    print(f"   ✅ Accepted: Event ID {result.get('event_id')}")
    return result

def send_readai_webhook(base_url: str, email: str, name: str, meeting_time: datetime) -> dict:
    """Send a Read.ai meeting_end webhook"""
    webhook_url = f"{base_url.rstrip('/')}/webhooks/readai"
    session_id = f"e2e-{uuid.uuid4().hex[:12]}"
    
    # Create a realistic demo transcript with MEDDIC information
    transcript_blocks = [
        {
            "start_time": int(meeting_time.timestamp()),
            "end_time": int((meeting_time + timedelta(minutes=2)).timestamp()),
            "speaker": {"name": "GV Rep"},
            "words": "Thanks for joining today! Let's start with understanding your current packaging workflow and what challenges you're facing."
        },
        {
            "start_time": int((meeting_time + timedelta(minutes=2)).timestamp()),
            "end_time": int((meeting_time + timedelta(minutes=5)).timestamp()),
            "speaker": {"name": name.split()[0] if name else "Customer"},
            "words": "We're currently using Workfront but it's too slow. Our artwork approval process takes about 3 months and we need to get it down to 4 weeks. We also have issues with human error in compliance checks for FDA regulations."
        },
        {
            "start_time": int((meeting_time + timedelta(minutes=5)).timestamp()),
            "end_time": int((meeting_time + timedelta(minutes=8)).timestamp()),
            "speaker": {"name": "GV Rep"},
            "words": "GoVisually can definitely help with that. We have AI-powered compliance checking and version control. What integrations are important for you?"
        },
        {
            "start_time": int((meeting_time + timedelta(minutes=8)).timestamp()),
            "end_time": int((meeting_time + timedelta(minutes=10)).timestamp()),
            "speaker": {"name": name.split()[0] if name else "Customer"},
            "words": "Integration with Adobe is critical for us. We also need SSO and compliance features for FDA and nutrition facts. Our IT Director John needs to approve the budget, and we'll need to evaluate 3 vendors by Q2."
        },
        {
            "start_time": int((meeting_time + timedelta(minutes=10)).timestamp()),
            "end_time": int((meeting_time + timedelta(minutes=12)).timestamp()),
            "speaker": {"name": "Sara"},
            "words": "I'm really excited about this! This could solve our biggest pain point. The AI compliance checking sounds perfect for reducing errors."
        },
        {
            "start_time": int((meeting_time + timedelta(minutes=12)).timestamp()),
            "end_time": int((meeting_time + timedelta(minutes=15)).timestamp()),
            "speaker": {"name": name.split()[0] if name else "Customer"},
            "words": "Let's schedule a follow-up. We need to get pricing information this week, and I'd like to connect you with our packaging project manager Emond for technical questions."
        },
        {
            "start_time": int((meeting_time + timedelta(minutes=15)).timestamp()),
            "end_time": int((meeting_time + timedelta(minutes=18)).timestamp()),
            "speaker": {"name": "GV Rep"},
            "words": "Perfect! I'll send pricing and we can schedule a technical deep-dive with Emond. Any concerns about implementation?"
        },
        {
            "start_time": int((meeting_time + timedelta(minutes=18)).timestamp()),
            "end_time": int((meeting_time + timedelta(minutes=20)).timestamp()),
            "speaker": {"name": name.split()[0] if name else "Customer"},
            "words": "The main concern is making sure Emond is comfortable with the system. Also, we need to make sure it integrates well with our existing Adobe workflows."
        }
    ]
    
    payload = {
        "session_id": session_id,
        "trigger": "meeting_end",
        "title": f"GoVisually Demo - {name}",
        "start_time": meeting_time.isoformat(),
        "end_time": (meeting_time + timedelta(minutes=30)).isoformat(),
        "participants": [
            {"name": name, "first_name": name.split()[0] if " " in name else name, "last_name": name.split()[-1] if " " in name else "", "email": email},
            {"name": "GV Rep", "first_name": "GV", "last_name": "Rep", "email": "rep@govisually.com"},
            {"name": "Sara", "first_name": "Sara", "last_name": "", "email": "sara@example.com"},
        ],
        "summary": f"Demo meeting with {name} discussing GoVisually platform. Customer needs to reduce artwork approval time from 3 months to 4 weeks. Currently using Workfront. Key requirements: Adobe integration, FDA compliance, SSO. IT Director John approves budget. Decision timeline: Q2 after evaluating 3 vendors. Sara is enthusiastic champion.",
        "transcript": {
            "speaker_blocks": transcript_blocks,
            "speakers": [
                {"name": "GV Rep"},
                {"name": name.split()[0] if name else "Customer"},
                {"name": "Sara"},
            ]
        }
    }
    
    headers = {"Content-Type": "application/json"}
    readai_secret = load_env_var("READAI_SHARED_SECRET", "")
    if readai_secret:
        headers["X-ReadAI-Secret"] = readai_secret
    
    print(f"   📤 Sending to: {webhook_url}")
    print(f"   🎥 Session ID: {session_id}")
    print(f"   👥 Participants: {len(payload['participants'])}")
    print(f"   📝 Transcript blocks: {len(transcript_blocks)}")
    
    response = requests.post(webhook_url, json=payload, headers=headers, timeout=30)
    
    if response.status_code != 200:
        print(f"   ❌ Failed: {response.status_code} - {response.text}")
        return None
    
    result = response.json()
    print(f"   ✅ Accepted: Event ID {result.get('event_id')}")
    return result

def wait_for_processing(base_url: str, event_id: str, max_wait: int = 60, event_type: str = "event") -> bool:
    """Wait for an event to be processed"""
    print(f"\n   ⏳ Waiting for processing (max {max_wait}s)...")
    
    for i in range(max_wait // 2):
        time.sleep(2)
        try:
            response = requests.get(f"{base_url}/debug/events/{event_id}", timeout=5)
            if response.status_code == 200:
                event_data = response.json()
                status = event_data.get("status", "unknown")
                print(f"      Status: {status}", end="\r")
                if status in ["processed", "completed", "failed", "ignored"]:
                    print()  # New line after status
                    if status == "failed":
                        error = event_data.get("last_error", "")
                        print(f"   ⚠️  {event_type} failed: {error[:200]}")
                        return False
                    elif status == "processed":
                        print(f"   ✅ {event_type} processed successfully")
                        return True
                    else:
                        print(f"   ℹ️  {event_type} status: {status}")
                        return True
        except Exception as e:
            print(f"      Error checking status: {e}", end="\r")
    
    print(f"\n   ⚠️  Timeout waiting for {event_type} to process")
    return False

def check_zoho_lead(email: str) -> dict | None:
    """Check if lead exists in Zoho (simplified - would need Zoho API)"""
    # In a real scenario, we'd query Zoho API here
    # For now, we'll just indicate this step
    print(f"\n   🔍 Checking Zoho Lead for: {email}")
    print(f"   ℹ️  (In production, this would query Zoho API to verify fields)")
    return {"email": email, "status": "would_check_zoho"}

def show_worker_logs_summary(event_ids: list[str]):
    """Show a summary of what was sent to Zoho from worker logs"""
    print("\n   📊 Checking worker logs for Zoho operations...")
    try:
        import subprocess
        result = subprocess.run(
            ["docker-compose", "logs", "--tail", "1000", "worker"],
            capture_output=True,
            text=True,
            timeout=10
        )
        logs = result.stdout
        
        # Look for field lists in logs
        for event_id in event_ids:
            if not event_id:
                continue
            event_logs = [line for line in logs.split("\n") if event_id in line]
            
            # Find Creating/Updating Zoho messages
            for line in event_logs:
                if "Creating Zoho Lead with" in line or "Updating Zoho Lead" in line:
                    # Extract field list
                    import re
                    match = re.search(r"with \d+ fields: \[(.*?)\]", line)
                    if match:
                        fields_str = match.group(1)
                        fields = [f.strip().strip("'\"") for f in fields_str.split(",")]
                        print(f"      ✅ Found: {len(fields)} fields")
                        for field in fields[:10]:  # Show first 10
                            print(f"         - {field}")
                        if len(fields) > 10:
                            print(f"         ... and {len(fields) - 10} more")
                        break
                elif "Zoho Lead created" in line or "Zoho update successful" in line:
                    print(f"      ✅ {line.split('INFO')[-1].strip()}")
    except Exception as e:
        print(f"      ⚠️  Could not check logs: {e}")

def main():
    print_section("END-TO-END FULL FLOW TEST")
    print("Simulating: Calendly Booking → Demo → Zoho Updates\n")
    
    # Configuration
    base_url = load_env_var("BASE_URL", "http://localhost:8000")
    test_email = f"e2e-test-{uuid.uuid4().hex[:8]}@example.com"
    test_name = "John Smith"
    
    # Timeline: Book demo 2 days from now, demo happens at that time
    now = datetime.now(timezone.utc)
    demo_time = now + timedelta(days=2, hours=10)  # 2 days from now at 10 AM
    
    print(f"📧 Test Lead Email: {test_email}")
    print(f"👤 Test Lead Name: {test_name}")
    print(f"📅 Demo Scheduled: {demo_time.strftime('%Y-%m-%d %H:%M %Z')}\n")
    
    # STEP 1: Calendly Booking
    print_step(1, "Calendly Booking (invitee.created)")
    calendly_result = send_calendly_webhook(base_url, test_email, test_name, demo_time)
    if not calendly_result:
        print("\n❌ Calendly webhook failed. Aborting.")
        return 1
    
    calendly_event_id = calendly_result.get("event_id")
    if calendly_result.get("ignored"):
        print(f"\n   ℹ️  Calendly event ignored: {calendly_result.get('reason', 'unknown')}")
        print(f"   (This is OK - event_type_uri filter may be active)")
    elif calendly_event_id:
        if not wait_for_processing(base_url, calendly_event_id, max_wait=60, event_type="Calendly event"):
            print("\n⚠️  Calendly event processing had issues, but continuing...")
        print(f"\n   ✅ Step 1 Complete: Lead should be created/enriched in Zoho")
    else:
        print(f"\n   ⚠️  Calendly event accepted but no event_id returned")
    time.sleep(2)  # Brief pause between steps
    
    # STEP 2: Demo Happens (Read.ai)
    print_step(2, "Demo Completion (Read.ai meeting_end)")
    readai_result = send_readai_webhook(base_url, test_email, test_name, demo_time)
    if not readai_result:
        print("\n❌ Read.ai webhook failed. Aborting.")
        return 1
    
    readai_event_id = readai_result.get("event_id")
    if not wait_for_processing(base_url, readai_event_id, max_wait=90, event_type="Read.ai event"):
        print("\n⚠️  Read.ai event processing had issues")
        return 1
    
    print(f"\n   ✅ Step 2 Complete: MEDDIC data should be extracted and sent to Zoho")
    time.sleep(2)
    
    # STEP 3: Verification
    print_step(3, "Verification & Summary")
    
    # Check event statuses
    print("\n   📊 Event Status Summary:")
    try:
        if calendly_event_id:
            cal_response = requests.get(f"{base_url}/debug/events/{calendly_event_id}", timeout=5)
            if cal_response.status_code == 200:
                cal_data = cal_response.json()
                status = cal_data.get('status', 'unknown')
                attempts = cal_data.get('attempts', 0)
                print(f"      Calendly Event: {status} (attempts: {attempts})")
                if status == "failed":
                    error = cal_data.get('last_error', '')[:200]
                    print(f"         Error: {error}")
    except:
        pass
    
    try:
        rai_response = requests.get(f"{base_url}/debug/events/{readai_event_id}", timeout=5)
        if rai_response.status_code == 200:
            rai_data = rai_response.json()
            status = rai_data.get('status', 'unknown')
            attempts = rai_data.get('attempts', 0)
            print(f"      Read.ai Event: {status} (attempts: {attempts})")
            if status == "failed":
                error = rai_data.get('last_error', '')[:200]
                print(f"         Error: {error}")
    except:
        pass
    
    # Show what was sent to Zoho from logs
    show_worker_logs_summary([calendly_event_id, readai_event_id])
    
    # Check Zoho (would need API access)
    check_zoho_lead(test_email)
    
    # Final summary
    print_section("END-TO-END TEST COMPLETE")
    print(f"""
✅ Flow Summary:
   1. Calendly booking created → Lead upserted/enriched in Zoho
   2. Demo completed → MEDDIC extracted and Lead updated in Zoho
   
📋 Next Steps:
   - Check Zoho CRM for Lead: {test_email}
   - Verify all MEDDIC fields are populated
   - Check worker logs: docker-compose logs -f worker
   - Review debug endpoints:
     * {base_url}/debug/events/{calendly_event_id}
     * {base_url}/debug/events/{readai_event_id}
""")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

