#!/usr/bin/env python3
"""
End-to-end test for Read.ai MEDDIC extraction and Zoho updates.
Sends webhook, waits for processing, checks Zoho, and reports what's missing.
"""
import json
import os
import re
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
import requests
import uuid

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

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

def get_zoho_lead(email: str) -> dict | None:
    """Fetch lead from Zoho by email using API"""
    import httpx
    
    # Get Zoho settings
    dc = load_env_var("ZOHO_DC", "au")
    refresh_token = load_env_var("ZOHO_REFRESH_TOKEN", "")
    client_id = load_env_var("ZOHO_CLIENT_ID", "")
    client_secret = load_env_var("ZOHO_CLIENT_SECRET", "")
    module = load_env_var("ZOHO_LEADS_MODULE", "Leads")
    
    if not refresh_token:
        print("⚠️  ZOHO_REFRESH_TOKEN not set, skipping Zoho check")
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
        print(f"⚠️  Error fetching Zoho lead: {e}")
        return None

def send_test_webhook() -> dict:
    """Send a test Read.ai webhook with rich transcript"""
    base_url = load_env_var("BASE_URL", "http://localhost:8000")
    webhook_url = f"{base_url.rstrip('/')}/webhooks/readai"
    
    # Use a unique session ID
    session_id = f"test-e2e-{uuid.uuid4().hex[:12]}"
    
    # Rich test payload with explicit MEDDIC information
    payload = {
        "session_id": session_id,
        "trigger": "meeting_end",
        "title": "GoVisually Demo - Test E2E",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "end_time": (datetime.now(timezone.utc).replace(second=0, microsecond=0)).isoformat(),
        "participants": [
            {"name": "Test Buyer", "first_name": "Test", "last_name": "Buyer", "email": "test.buyer@example.com"},
            {"name": "GV Rep", "first_name": "GV", "last_name": "Rep", "email": "rep@govisually.com"},
        ],
        "summary": "Demo meeting discussing GoVisually platform. Buyer mentioned they need to reduce approval time from 3 months to 4 weeks. They're currently using Workfront but it's slow. Decision will be made by Q2 after evaluating 3 vendors. Sara is very excited about the solution. Budget approval needed from IT Director John.",
        "transcript": {
            "speaker_blocks": [
                {
                    "start_time": int(time.time()),
                    "end_time": int(time.time()) + 10,
                    "speaker": {"name": "Test Buyer"},
                    "words": "We need to reduce our artwork approval time from 3 months to 4 weeks. Our current process is a nightmare and takes way too long."
                },
                {
                    "start_time": int(time.time()) + 10,
                    "end_time": int(time.time()) + 20,
                    "speaker": {"name": "GV Rep"},
                    "words": "GoVisually can help with that. We've helped other companies cut their approval time significantly."
                },
                {
                    "start_time": int(time.time()) + 20,
                    "end_time": int(time.time()) + 30,
                    "speaker": {"name": "Test Buyer"},
                    "words": "We're currently using Workfront but it's too slow and frustrating. We need something faster. Integration with Adobe is important for us."
                },
                {
                    "start_time": int(time.time()) + 30,
                    "end_time": int(time.time()) + 40,
                    "speaker": {"name": "Sara"},
                    "words": "I'm really excited about this! This could solve our biggest pain point. We need to get pricing and schedule a technical demo."
                },
                {
                    "start_time": int(time.time()) + 40,
                    "end_time": int(time.time()) + 50,
                    "speaker": {"name": "Test Buyer"},
                    "words": "We'll need to evaluate 3 vendors and make a decision by Q2. IT Director John needs to approve the budget. Let's schedule a follow-up meeting."
                },
            ],
            "speakers": [
                {"name": "Test Buyer"},
                {"name": "GV Rep"},
                {"name": "Sara"},
            ]
        }
    }
    
    headers = {"Content-Type": "application/json"}
    readai_secret = load_env_var("READAI_SHARED_SECRET", "")
    if readai_secret:
        headers["X-ReadAI-Secret"] = readai_secret
    
    print(f"📤 Sending test webhook to {webhook_url}...")
    response = requests.post(webhook_url, json=payload, headers=headers, timeout=30)
    
    if response.status_code != 200:
        print(f"❌ Webhook failed: {response.status_code} - {response.text}")
        return None
    
    result = response.json()
    print(f"✅ Webhook accepted. Event ID: {result.get('event_id')}")
    return result

def check_zoho_lead(email: str, expected_fields: dict) -> dict:
    """Check Zoho lead and compare with expected fields"""
    print(f"\n🔍 Checking Zoho Lead for {email}...")
    
    lead = get_zoho_lead(email)
    if not lead:
        print(f"❌ Lead not found in Zoho")
        return {"found": False}
    
    print(f"✅ Lead found: {lead.get('id')}")
    
    results = {"found": True, "fields": {}, "missing": [], "incorrect": []}
    
    for field_name, expected_value in expected_fields.items():
        actual_value = lead.get(field_name, "")
        results["fields"][field_name] = {
            "expected": expected_value[:100] if isinstance(expected_value, str) and len(expected_value) > 100 else expected_value,
            "actual": actual_value[:100] if isinstance(actual_value, str) and len(actual_value) > 100 else actual_value,
            "populated": bool(actual_value and str(actual_value).strip()),
        }
        
        if expected_value and not actual_value:
            results["missing"].append(field_name)
        elif expected_value and actual_value and expected_value.lower() not in str(actual_value).lower():
            results["incorrect"].append(field_name)
    
    return results

def main():
    print("🧪 Starting End-to-End MEDDIC Test\n")
    
    # Send webhook
    webhook_result = send_test_webhook()
    if not webhook_result:
        return 1
    
    event_id = webhook_result.get("event_id")
    if not event_id:
        print("❌ No event_id returned")
        return 1
    
    # Wait for processing (check every 2 seconds, max 60 seconds)
    print(f"\n⏳ Waiting for processing (checking every 2s, max 60s)...")
    base_url = load_env_var("BASE_URL", "http://localhost:8000")
    
    for i in range(30):  # 30 * 2 = 60 seconds max
        time.sleep(2)
        try:
            response = requests.get(f"{base_url}/debug/events/{event_id}", timeout=5)
            if response.status_code == 200:
                event_data = response.json()
                status = event_data.get("status", "unknown")
                print(f"   Status: {status}")
                if status in ["completed", "failed", "ignored"]:
                    break
        except Exception as e:
            print(f"   Error checking status: {e}")
    
    # Check Zoho
    email = "test.buyer@example.com"
    
    # Expected fields based on test payload
    expected_fields = {
        "MEDDIC_Process": "reduce",  # Should contain "reduce" or "time"
        "Identified_Pain_Points": "nightmare",  # Should contain "nightmare" or "slow"
        "MEDDIC_Pain": "Adobe",  # Decision criteria - should contain "Adobe" or "integration"
        "Competition": "Workfront",  # Decision process - should contain "Workfront" or "evaluate"
        "Champion_and_Economic_Buyer": "Sara",  # Should contain "Sara" or "John"
    }
    
    results = check_zoho_lead(email, expected_fields)
    
    # Print results
    print("\n" + "="*60)
    print("📊 TEST RESULTS")
    print("="*60)
    
    if not results["found"]:
        print("❌ Lead not found in Zoho")
        return 1
    
    print(f"\n✅ Lead found in Zoho")
    print(f"\n📋 Field Status:")
    
    for field_name, field_data in results["fields"].items():
        status = "✅" if field_data["populated"] else "❌"
        print(f"   {status} {field_name}:")
        if field_data["populated"]:
            print(f"      Actual: {field_data['actual']}")
        else:
            print(f"      Expected: {field_data['expected']}")
            print(f"      Actual: (empty)")
    
    if results["missing"]:
        print(f"\n❌ Missing fields: {', '.join(results['missing'])}")
        return 1
    
    if results["incorrect"]:
        print(f"\n⚠️  Incorrect fields: {', '.join(results['incorrect'])}")
        return 1
    
    print("\n✅ All fields populated correctly!")
    return 0

if __name__ == "__main__":
    sys.exit(main())

