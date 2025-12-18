#!/usr/bin/env python3
"""
Automated E2E test and fix script for MEDDIC extraction.
Runs test, checks Zoho, identifies issues, and suggests fixes.
"""
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path
from datetime import datetime, timezone
import requests
import subprocess

def load_env_var(key: str, default: str = "") -> str:
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        content = env_file.read_text()
        match = re.search(rf"^{re.escape(key)}=(.+)$", content, flags=re.M)
        if match:
            return match.group(1).strip()
    return default

def send_test_webhook() -> dict:
    """Send test webhook with rich MEDDIC content"""
    base_url = load_env_var("BASE_URL", "http://localhost:8000")
    webhook_url = f"{base_url.rstrip('/')}/webhooks/readai"
    session_id = f"fix-test-{uuid.uuid4().hex[:12]}"
    
    payload = {
        "session_id": session_id,
        "trigger": "meeting_end",
        "title": "MEDDIC Test - Full Extraction",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "end_time": (datetime.now(timezone.utc).replace(second=0, microsecond=0)).isoformat(),
        "participants": [
            {"name": "Test Lead", "first_name": "Test", "last_name": "Lead", "email": f"meddic-test-{uuid.uuid4().hex[:8]}@example.com"},
            {"name": "GV Rep", "first_name": "GV", "last_name": "Rep", "email": "rep@govisually.com"},
        ],
        "summary": "Test meeting with explicit MEDDIC information: Need to reduce approval time from 3 months to 4 weeks. Currently using Workfront which is slow. Decision criteria includes Adobe integration and compliance features. Will evaluate 3 vendors by Q2. Sara is very excited. IT Director John approves budget.",
        "transcript": {
            "speaker_blocks": [
                {
                    "start_time": int(time.time()),
                    "end_time": int(time.time()) + 10,
                    "speaker": {"name": "Test Lead"},
                    "words": "We need to reduce our artwork approval time from 3 months to 4 weeks. Our current process is a nightmare and takes way too long. We're currently using Workfront but it's too slow and frustrating."
                },
                {
                    "start_time": int(time.time()) + 10,
                    "end_time": int(time.time()) + 20,
                    "speaker": {"name": "GV Rep"},
                    "words": "GoVisually can help with that. We integrate with Adobe and have compliance features."
                },
                {
                    "start_time": int(time.time()) + 20,
                    "end_time": int(time.time()) + 30,
                    "speaker": {"name": "Test Lead"},
                    "words": "Integration with Adobe is important for us. We also need compliance features for FDA regulations. We'll need to evaluate 3 vendors and make a decision by Q2. IT Director John needs to approve the budget."
                },
                {
                    "start_time": int(time.time()) + 30,
                    "end_time": int(time.time()) + 40,
                    "speaker": {"name": "Sara"},
                    "words": "I'm really excited about this! This could solve our biggest pain point. We need to get pricing and schedule a technical demo with Emund."
                },
                {
                    "start_time": int(time.time()) + 40,
                    "end_time": int(time.time()) + 50,
                    "speaker": {"name": "Test Lead"},
                    "words": "Let's schedule a follow-up meeting. We're also comparing with other vendors but GoVisually looks promising."
                },
            ],
            "speakers": [
                {"name": "Test Lead"},
                {"name": "GV Rep"},
                {"name": "Sara"},
            ]
        }
    }
    
    headers = {"Content-Type": "application/json"}
    readai_secret = load_env_var("READAI_SHARED_SECRET", "")
    if readai_secret:
        headers["X-ReadAI-Secret"] = readai_secret
    
    response = requests.post(webhook_url, json=payload, headers=headers, timeout=30)
    if response.status_code != 200:
        print(f"❌ Webhook failed: {response.status_code}")
        return None
    return response.json()

def check_worker_logs(event_id: str, max_wait: int = 60) -> dict:
    """Check worker logs for LLM extraction results"""
    print(f"\n⏳ Waiting for processing (max {max_wait}s)...")
    
    base_url = load_env_var("BASE_URL", "http://localhost:8000")
    for i in range(max_wait // 2):
        time.sleep(2)
        try:
            response = requests.get(f"{base_url}/debug/events/{event_id}", timeout=5)
            if response.status_code == 200:
                event_data = response.json()
                status = event_data.get("status", "unknown")
                if status in ["processed", "completed", "failed", "ignored"]:
                    break
        except:
            pass
    
    # Get worker logs
    try:
        result = subprocess.run(
            ["docker-compose", "logs", "--tail", "200", "worker"],
            capture_output=True,
            text=True,
            timeout=10
        )
        logs = result.stdout
        
        # Extract LLM extraction results
        extraction = {}
        for line in logs.split("\n"):
            if "LLM extracted MEDDIC:" in line:
                # Parse: metrics=54 chars, economic_buyer=45 chars, ...
                matches = re.findall(r'(\w+)=(\d+)\s+chars', line)
                for field, count in matches:
                    extraction[field] = int(count)
                if "confidence=" in line:
                    conf_match = re.search(r'confidence=(\w+)', line)
                    if conf_match:
                        extraction["confidence"] = conf_match.group(1)
        
        return extraction
    except Exception as e:
        print(f"⚠️  Error checking logs: {e}")
        return {}

def main():
    print("🔧 MEDDIC E2E Test & Fix Script\n")
    print("="*60)
    
    # Step 1: Send webhook
    print("\n1️⃣  Sending test webhook...")
    result = send_test_webhook()
    if not result:
        return 1
    
    event_id = result.get("event_id")
    email = f"meddic-test-{uuid.uuid4().hex[:8]}@example.com"  # Extract from payload
    
    print(f"   ✅ Event ID: {event_id}")
    
    # Step 2: Wait and check extraction
    print("\n2️⃣  Checking LLM extraction...")
    extraction = check_worker_logs(event_id)
    
    if not extraction:
        print("   ⚠️  Could not get extraction results from logs")
        return 1
    
    print(f"\n   📊 LLM Extraction Results:")
    expected_fields = ["metrics", "economic_buyer", "decision_criteria", "decision_process", 
                      "identified_pain", "champion", "competition", "next_steps"]
    
    missing = []
    for field in expected_fields:
        count = extraction.get(field, 0)
        status = "✅" if count > 0 else "❌"
        print(f"      {status} {field}: {count} chars")
        if count == 0:
            missing.append(field)
    
    confidence = extraction.get("confidence", "unknown")
    print(f"      Confidence: {confidence}")
    
    # Step 3: Report and suggest fixes
    print("\n3️⃣  Analysis:")
    if not missing:
        print("   ✅ All fields extracted successfully!")
        return 0
    else:
        print(f"   ❌ Missing fields: {', '.join(missing)}")
        print(f"\n   💡 Suggestions:")
        print(f"      - Check if transcript contains information for these fields")
        print(f"      - Try increasing GEMINI_MODEL to gemini-1.5-pro (already done)")
        print(f"      - Check worker logs for LLM response details")
        print(f"      - Verify transcript is being passed correctly to LLM")
        return 1

if __name__ == "__main__":
    sys.exit(main())

