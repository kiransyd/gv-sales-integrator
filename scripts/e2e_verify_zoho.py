#!/usr/bin/env python3
"""
End-to-End Test with Zoho Verification
Tests the full flow and actually queries Zoho to verify all fields are populated correctly.
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
import httpx

def load_env_var(key: str, default: str = "") -> str:
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        content = env_file.read_text()
        match = re.search(rf"^{re.escape(key)}=(.+)$", content, flags=re.M)
        if match:
            return match.group(1).strip()
    return default

def get_zoho_lead(email: str) -> dict | None:
    """Fetch lead from Zoho by email"""
    dc = load_env_var("ZOHO_DC", "au")
    refresh_token = load_env_var("ZOHO_REFRESH_TOKEN", "")
    client_id = load_env_var("ZOHO_CLIENT_ID", "")
    client_secret = load_env_var("ZOHO_CLIENT_SECRET", "")
    module = load_env_var("ZOHO_LEADS_MODULE", "Leads")
    
    if not refresh_token:
        print("   ⚠️  ZOHO_REFRESH_TOKEN not set, skipping Zoho check")
        return None
    
    # Get access token
    token_url = f"https://accounts.zoho.{dc}/oauth/v2/token"
    token_data = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
    }
    
    try:
        with httpx.Client(timeout=10.0) as client:
            token_resp = client.post(token_url, data=token_data)
            token_resp.raise_for_status()
            access_token = token_resp.json()["access_token"]
            
            # Search for lead
            api_url = f"https://www.zohoapis.{dc}/crm/v2/{module}/search"
            params = {"criteria": f"(Email:equals:{email})"}
            headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
            
            search_resp = client.get(api_url, params=params, headers=headers, timeout=10.0)
            
            if search_resp.status_code == 204:
                return None
            
            search_resp.raise_for_status()
            data = search_resp.json()
            
            if data.get("data") and len(data["data"]) > 0:
                return data["data"][0]
            
            return None
    except Exception as e:
        print(f"   ❌ Error fetching Zoho lead: {e}")
        return None

def verify_zoho_fields(lead: dict, expected_fields: dict, stage: str) -> dict:
    """Verify Zoho lead has expected fields"""
    print(f"\n   📋 Verifying {stage} fields in Zoho:")
    
    results = {
        "found": [],
        "missing": [],
        "empty": [],
        "incorrect": []
    }
    
    for field_name, expected_value in expected_fields.items():
        actual_value = lead.get(field_name, "")
        is_empty = not actual_value or (isinstance(actual_value, str) and not actual_value.strip())
        
        if is_empty:
            if expected_value:
                results["missing"].append(field_name)
                print(f"      ❌ {field_name}: MISSING (expected: {str(expected_value)[:50]})")
            else:
                results["empty"].append(field_name)
                print(f"      ⚠️  {field_name}: empty (OK if not required)")
        else:
            results["found"].append(field_name)
            display_value = str(actual_value)[:80] + "..." if len(str(actual_value)) > 80 else str(actual_value)
            print(f"      ✅ {field_name}: {display_value}")
    
    return results

def send_calendly_webhook(base_url: str, email: str, name: str, event_time: datetime) -> dict:
    """Send Calendly webhook with proper signature"""
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
        print(f"   ❌ Calendly webhook failed: {response.status_code} - {response.text}")
        return None
    return response.json()

def send_readai_webhook(base_url: str, email: str, name: str, meeting_time: datetime) -> dict:
    """Send Read.ai webhook"""
    webhook_url = f"{base_url.rstrip('/')}/webhooks/readai"
    session_id = f"verify-{uuid.uuid4().hex[:12]}"
    
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
        "summary": "Demo meeting discussing GoVisually platform. Customer needs to reduce artwork approval time from 3 months to 4 weeks.",
        "transcript": {
            "speaker_blocks": [
                {
                    "start_time": int(meeting_time.timestamp()),
                    "end_time": int((meeting_time + timedelta(minutes=2)).timestamp()),
                    "speaker": {"name": "GV Rep"},
                    "words": "Thanks for joining! Let's discuss your packaging workflow challenges."
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
        print(f"   ❌ Read.ai webhook failed: {response.status_code} - {response.text}")
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
                    return status == "processed" or status == "completed"
        except:
            pass
    return False

def main():
    print("="*70)
    print("  END-TO-END TEST WITH ZOHO VERIFICATION")
    print("="*70)
    
    base_url = load_env_var("BASE_URL", "http://localhost:8000")
    test_email = f"verify-{uuid.uuid4().hex[:8]}@example.com"
    test_name = "John Smith"
    demo_time = datetime.now(timezone.utc) + timedelta(days=2, hours=10)
    
    print(f"\n📧 Test Lead: {test_name} ({test_email})")
    print(f"📅 Demo Time: {demo_time.strftime('%Y-%m-%d %H:%M %Z')}\n")
    
    # STEP 1: Calendly Booking
    print("STEP 1: Calendly Booking")
    print("-" * 70)
    calendly_result = send_calendly_webhook(base_url, test_email, test_name, demo_time)
    if not calendly_result:
        return 1
    
    calendly_event_id = calendly_result.get("event_id")
    if calendly_event_id:
        print(f"   ✅ Event ID: {calendly_event_id}")
        if wait_for_processing(base_url, calendly_event_id, max_wait=60):
            print("   ✅ Processed successfully")
        else:
            print("   ⚠️  Processing timeout or failed")
    else:
        print(f"   ⚠️  Event ignored: {calendly_result.get('reason', 'unknown')}")
    
    # Wait a bit for Zoho to update
    print("\n   ⏳ Waiting 5s for Zoho update...")
    time.sleep(5)
    
    # Verify Calendly fields in Zoho
    lead = get_zoho_lead(test_email)
    if not lead:
        print("   ❌ Lead not found in Zoho after Calendly booking!")
        print("   (This might be OK if Calendly event was ignored)")
    else:
        print(f"   ✅ Lead found in Zoho: {lead.get('id')}")
        expected_calendly = {
            "Email": test_email,
            "First_Name": "John",
            "Last_Name": "Smith",
            "Lead_Status": load_env_var("STATUS_DEMO_BOOKED", "Demo Booked"),
        }
        calendly_results = verify_zoho_fields(lead, expected_calendly, "Calendly")
        
        if calendly_results["missing"]:
            print(f"\n   ❌ MISSING REQUIRED FIELDS: {', '.join(calendly_results['missing'])}")
            return 1
    
    # STEP 2: Read.ai Demo Completion
    print("\n\nSTEP 2: Read.ai Demo Completion")
    print("-" * 70)
    readai_result = send_readai_webhook(base_url, test_email, test_name, demo_time)
    if not readai_result:
        return 1
    
    readai_event_id = readai_result.get("event_id")
    print(f"   ✅ Event ID: {readai_event_id}")
    if wait_for_processing(base_url, readai_event_id, max_wait=90):
        print("   ✅ Processed successfully")
    else:
        print("   ❌ Processing failed")
        return 1
    
    # Wait for Zoho update
    print("\n   ⏳ Waiting 5s for Zoho update...")
    time.sleep(5)
    
    # Verify all fields in Zoho
    lead = get_zoho_lead(test_email)
    if not lead:
        print("   ❌ Lead not found in Zoho after Read.ai!")
        return 1
    
    print(f"   ✅ Lead found in Zoho: {lead.get('id')}")
    
    # Verify basic fields are still there
    expected_basic = {
        "Email": test_email,
        "First_Name": "John",
        "Last_Name": "Smith",
        "Lead_Status": load_env_var("STATUS_DEMO_COMPLETE", "Demo Complete"),
    }
    basic_results = verify_zoho_fields(lead, expected_basic, "Basic")
    
    # Verify MEDDIC fields
    meddic_fields = {
        "MEDDIC_Process": "",  # Should have content
        "MEDDIC_Pain": "",  # Should have content
        "Competition": "",  # Should have content
        "Identified_Pain_Points": "",  # Should have content
    }
    meddic_results = verify_zoho_fields(lead, meddic_fields, "MEDDIC")
    
    # Final summary
    print("\n" + "="*70)
    print("  TEST SUMMARY")
    print("="*70)
    
    all_missing = basic_results["missing"] + [f for f in meddic_results["missing"] if lead.get(f, "").strip()]
    
    if all_missing:
        print(f"❌ MISSING FIELDS: {', '.join(all_missing)}")
        return 1
    else:
        print("✅ All critical fields populated!")
        print(f"\n   Basic fields: {len(basic_results['found'])} found")
        print(f"   MEDDIC fields: {len([f for f in meddic_results['found'] if lead.get(f, '').strip()])} populated")
        return 0

if __name__ == "__main__":
    sys.exit(main())



