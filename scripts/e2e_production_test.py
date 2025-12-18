#!/usr/bin/env python3
"""
Production-Ready End-to-End Test
Tests the complete flow and verifies all fields are populated correctly by checking worker logs.
"""
import json
import os
import re
import sys
import time
import uuid
import hmac
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta
import requests

def load_env_var(key: str, default: str = "") -> str:
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        content = env_file.read_text()
        match = re.search(rf"^{re.escape(key)}=(.+)$", content, flags=re.M)
        if match:
            return match.group(1).strip()
    return default

def get_worker_logs(pattern: str, max_lines: int = 100) -> list[str]:
    """Get worker logs matching a pattern"""
    try:
        result = subprocess.run(
            ["docker-compose", "logs", "--tail", "1000", "worker"],
            capture_output=True,
            text=True,
            timeout=10
        )
        lines = result.stdout.split("\n")
        matching = [line for line in lines if pattern in line]
        return matching[-max_lines:] if len(matching) > max_lines else matching
    except Exception:
        return []

def check_field_in_logs(event_id: str, field_name: str) -> bool:
    """Check if a field appears in logs for an event"""
    logs = get_worker_logs(event_id, max_lines=200)
    for line in logs:
        if field_name in line and ("Setting" in line or field_name in line):
            return True
    return False

def send_calendly_webhook(base_url: str, email: str, name: str, event_time: datetime) -> dict:
    """Send Calendly webhook"""
    webhook_url = f"{base_url.rstrip('/')}/webhooks/calendly"
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
            },
            "event": {
                "uuid": event_uuid,
                "uri": f"https://api.calendly.com/scheduled_events/{event_uuid}",
                "start_time": event_time.isoformat(),
                "end_time": (event_time + timedelta(minutes=30)).isoformat(),
                "timezone": "America/New_York",
            },
            "event_type": {
                "uri": load_env_var("CALENDLY_EVENT_TYPE_URI", "https://api.calendly.com/event_types/TEST123")
            },
            "questions_and_answers": [
                {"question": "What's your role?", "answer": "Packaging Manager"},
                {"question": "Company?", "answer": "Test Company Inc"}
            ]
        }
    }
    
    headers = {"Content-Type": "application/json"}
    calendly_key = load_env_var("CALENDLY_SIGNING_KEY", "")
    if calendly_key:
        timestamp = int(time.time())
        raw_body = json.dumps(payload).encode("utf-8")
        signed_payload = f"{timestamp}.".encode("utf-8") + raw_body
        signature = hmac.new(calendly_key.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
        headers["Calendly-Webhook-Signature"] = f"t={timestamp},v1={signature}"
    
    response = requests.post(webhook_url, json=payload, headers=headers, timeout=30)
    if response.status_code != 200:
        return None
    return response.json()

def send_readai_webhook(base_url: str, email: str, name: str, meeting_time: datetime) -> dict:
    """Send Read.ai webhook"""
    webhook_url = f"{base_url.rstrip('/')}/webhooks/readai"
    session_id = f"prod-test-{uuid.uuid4().hex[:12]}"
    first_name = name.split()[0] if " " in name else name
    last_name = name.split()[-1] if " " in name and len(name.split()) > 1 else ""
    
    payload = {
        "session_id": session_id,
        "trigger": "meeting_end",
        "title": f"GoVisually Demo - {name}",
        "start_time": meeting_time.isoformat(),
        "end_time": (meeting_time + timedelta(minutes=30)).isoformat(),
        "participants": [
            {"name": name, "first_name": first_name, "last_name": last_name, "email": email},
            {"name": "GV Rep", "first_name": "GV", "last_name": "Rep", "email": "rep@govisually.com"},
        ],
        "summary": "Demo meeting. Customer needs to reduce approval time from 3 months to 4 weeks. Using Workfront. Adobe integration critical. IT Director John approves budget. Evaluate 3 vendors by Q2.",
        "transcript": {
            "speaker_blocks": [
                {
                    "start_time": int(meeting_time.timestamp()),
                    "end_time": int((meeting_time + timedelta(minutes=2)).timestamp()),
                    "speaker": {"name": "GV Rep"},
                    "words": "Thanks for joining! Let's discuss your packaging workflow."
                },
                {
                    "start_time": int((meeting_time + timedelta(minutes=2)).timestamp()),
                    "end_time": int((meeting_time + timedelta(minutes=5)).timestamp()),
                    "speaker": {"name": first_name},
                    "words": "We need to reduce approval time from 3 months to 4 weeks. Currently using Workfront but it's too slow. Integration with Adobe is critical. IT Director John approves budget. We'll evaluate 3 vendors by Q2."
                },
            ],
            "speakers": [{"name": "GV Rep"}, {"name": first_name}]
        }
    }
    
    headers = {"Content-Type": "application/json"}
    readai_secret = load_env_var("READAI_SHARED_SECRET", "")
    if readai_secret:
        headers["X-ReadAI-Secret"] = readai_secret
    
    response = requests.post(webhook_url, json=payload, headers=headers, timeout=30)
    if response.status_code != 200:
        return None
    return response.json()

def wait_for_processing(base_url: str, event_id: str, max_wait: int = 60) -> bool:
    """Wait for event processing"""
    for i in range(max_wait // 2):
        time.sleep(2)
        try:
            response = requests.get(f"{base_url}/debug/events/{event_id}", timeout=5)
            if response.status_code == 200:
                event_data = response.json()
                status = event_data.get("status", "unknown")
                if status in ["processed", "completed", "failed"]:
                    return status in ["processed", "completed"]
        except:
            pass
    return False

def verify_fields_in_logs(event_id: str, expected_fields: list[str], stage: str) -> dict:
    """Verify fields appear in worker logs"""
    print(f"\n   🔍 Verifying {stage} fields in logs...")
    results = {"found": [], "missing": []}
    
    logs = get_worker_logs(event_id, max_lines=500)
    log_text = "\n".join(logs)
    
    for field in expected_fields:
        # Check if field appears in logs (in payload lists, "Setting" messages, or field names)
        # Look for patterns like: "fields: ['Email', 'First_Name', ...]" or "Setting Zoho field First_Name"
        found = False
        for line in logs:
            if f"'{field}'" in line or f'"{field}"' in line:  # In field list
                found = True
                break
            if f"field {field}" in line.lower() or f"field: {field}" in line.lower():
                found = True
                break
            if field in line and ("Creating" in line or "Updating" in line or "Setting" in line):
                found = True
                break
        
        if found:
            results["found"].append(field)
            print(f"      ✅ {field}")
        else:
            results["missing"].append(field)
            print(f"      ❌ {field}: NOT FOUND in logs")
    
    return results

def main():
    print("="*70)
    print("  PRODUCTION-READY END-TO-END TEST")
    print("="*70)
    
    base_url = load_env_var("BASE_URL", "http://localhost:8000")
    test_email = f"prod-test-{uuid.uuid4().hex[:8]}@example.com"
    test_name = "John Smith"
    demo_time = datetime.now(timezone.utc) + timedelta(days=2, hours=10)
    
    print(f"\n📧 Test Lead: {test_name} ({test_email})")
    print(f"📅 Demo Time: {demo_time.strftime('%Y-%m-%d %H:%M %Z')}\n")
    
    all_passed = True
    
    # STEP 1: Calendly
    print("STEP 1: Calendly Booking")
    print("-" * 70)
    calendly_result = send_calendly_webhook(base_url, test_email, test_name, demo_time)
    if not calendly_result:
        print("   ❌ Calendly webhook failed")
        return 1
    
    calendly_event_id = calendly_result.get("event_id")
    if calendly_event_id:
        print(f"   ✅ Event ID: {calendly_event_id}")
        if wait_for_processing(base_url, calendly_event_id, max_wait=60):
            print("   ✅ Processed successfully")
            
            # Verify Calendly fields
            expected_calendly = ["Email", "First_Name", "Last_Name", "Lead_Status"]
            calendly_results = verify_fields_in_logs(calendly_event_id, expected_calendly, "Calendly Basic")
            
            if calendly_results["missing"]:
                print(f"   ⚠️  Missing fields: {', '.join(calendly_results['missing'])}")
                all_passed = False
        else:
            print("   ⚠️  Processing failed or timeout")
            all_passed = False
    else:
        print(f"   ℹ️  Event ignored: {calendly_result.get('reason', 'unknown')}")
    
    time.sleep(3)
    
    # STEP 2: Read.ai
    print("\n\nSTEP 2: Read.ai Demo Completion")
    print("-" * 70)
    readai_result = send_readai_webhook(base_url, test_email, test_name, demo_time)
    if not readai_result:
        print("   ❌ Read.ai webhook failed")
        return 1
    
    readai_event_id = readai_result.get("event_id")
    print(f"   ✅ Event ID: {readai_event_id}")
    if wait_for_processing(base_url, readai_event_id, max_wait=90):
        print("   ✅ Processed successfully")
        
        # Verify Read.ai fields
        expected_readai = [
            "Email", "First_Name", "Last_Name", "Lead_Status",
            "MEDDIC_Process", "MEDDIC_Pain", "Competition", "Identified_Pain_Points"
        ]
        readai_results = verify_fields_in_logs(readai_event_id, expected_readai, "Read.ai + MEDDIC")
        
        if readai_results["missing"]:
            print(f"   ⚠️  Missing fields: {', '.join(readai_results['missing'])}")
            all_passed = False
    else:
        print("   ❌ Processing failed")
        return 1
    
    # Final summary
    print("\n" + "="*70)
    print("  TEST SUMMARY")
    print("="*70)
    
    if all_passed:
        print("✅ ALL TESTS PASSED - System is production-ready!")
        return 0
    else:
        print("⚠️  SOME ISSUES FOUND - Review logs above")
        return 1

if __name__ == "__main__":
    sys.exit(main())

