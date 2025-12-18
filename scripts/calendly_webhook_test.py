#!/usr/bin/env python3
"""Send a test Calendly webhook event to the local or production endpoint"""
import hashlib
import hmac
import json
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
import httpx


def load_env_var(key: str, env_file_name: str = ".env") -> str:
    """Load environment variable from specified .env file"""
    env_file = Path(__file__).parent.parent / env_file_name
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip()
    return ""


def create_calendly_signature(payload_json: str, signing_key: str, timestamp: str) -> str:
    """Create Calendly webhook signature using HMAC-SHA256"""
    # Calendly signature format: timestamp.payload_json
    signed_payload = f"{timestamp}.{payload_json}"
    signature = hmac.new(
        signing_key.encode('utf-8'),
        signed_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature


def main():
    # Parse command-line arguments for env file
    env_file = ".env"
    if len(sys.argv) > 1:
        if sys.argv[1] in ("--env", "-e") and len(sys.argv) > 2:
            env_file = sys.argv[2]
        else:
            env_file = sys.argv[1]

    # Load config from env
    base_url = load_env_var("BASE_URL", env_file)
    signing_key = load_env_var("CALENDLY_SIGNING_KEY", env_file)
    event_type_uri = load_env_var("CALENDLY_EVENT_TYPE_URI", env_file)

    if not base_url:
        print(f"❌ BASE_URL not found in {env_file}")
        return 1

    webhook_url = f"{base_url.rstrip('/')}/webhooks/calendly"

    print(f"📤 Sending Calendly test webhook to: {webhook_url}")
    print(f"🔧 Using environment: {env_file}")
    if signing_key:
        print("🔐 Using webhook signature authentication")
    else:
        print("⚠️  No CALENDLY_SIGNING_KEY set (webhook will accept without signature)")
    print()

    # Create test payload with unique IDs to avoid idempotency deduplication
    demo_time = datetime.now(timezone.utc) + timedelta(days=2)
    unique_invitee_id = f"TEST-INV-{uuid.uuid4().hex[:8]}"
    unique_event_id = f"TEST-EVENT-{uuid.uuid4().hex[:8]}"

    payload = {
        "event": "invitee.created",
        "payload": {
            "invitee": {
                "email": "test.demo@example.com",
                "name": "Test Demo User",
                "uri": f"https://api.calendly.com/scheduled_events/{unique_event_id}/invitees/{unique_invitee_id}",
                "uuid": unique_invitee_id
            },
            "event": {
                "uri": f"https://api.calendly.com/scheduled_events/{unique_event_id}",
                "uuid": unique_event_id,
                "start_time": demo_time.isoformat(),
                "timezone": "Australia/Sydney"
            },
            "questions_and_answers": [
                {"question": "What's your company name?", "answer": "Test Company Inc"},
                {"question": "What do you want to achieve with GoVisually?", "answer": "Streamline our packaging approval workflow and reduce review time"},
                {"question": "How many team members will use GoVisually?", "answer": "5-10 people"},
                {"question": "What tools do you currently use?", "answer": "Email, Slack, shared drives"}
            ],
            "event_type": event_type_uri or "https://api.calendly.com/event_types/FBHFVVJGIXH2RYRF"
        }
    }

    # Prepare headers
    payload_json = json.dumps(payload)
    headers = {"Content-Type": "application/json"}

    # Add Calendly signature if signing key is configured
    if signing_key:
        timestamp = str(int(time.time()))
        signature = create_calendly_signature(payload_json, signing_key, timestamp)
        headers["Calendly-Webhook-Signature"] = f"t={timestamp},v1={signature}"

    # Print payload summary
    print("📋 Payload summary:")
    print(f"   Event: {payload['event']}")
    print(f"   Invitee: {payload['payload']['invitee']['name']} ({payload['payload']['invitee']['email']})")
    print(f"   Invitee ID: {unique_invitee_id}")
    print(f"   Event ID: {unique_event_id}")
    print(f"   Demo time: {demo_time.strftime('%Y-%m-%d %H:%M %Z')}")
    print(f"   Questions answered: {len(payload['payload']['questions_and_answers'])}")
    print()

    try:
        print("🚀 Sending webhook...")
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                webhook_url,
                content=payload_json,
                headers=headers
            )

        # Print response details
        print(f"\n📥 Response Status: {response.status_code}")

        try:
            response_json = response.json()
            print("📄 Response Body:")
            print(json.dumps(response_json, indent=2))

            # Check if request was successful
            if response.status_code == 200:
                if response_json.get("ok"):
                    print("\n✅ Webhook accepted successfully!")
                    if "event_id" in response_json:
                        print(f"   Event ID: {response_json['event_id']}")
                    if "idempotency_key" in response_json:
                        print(f"   Idempotency Key: {response_json['idempotency_key']}")
                    print("\n💡 Next steps:")
                    print("   1. Check worker logs: docker-compose logs -f worker")
                    print(f"   2. Check debug endpoint: {base_url}/debug/events (if ALLOW_DEBUG_ENDPOINTS=true)")
                    print(f"   3. Check Zoho CRM for Lead updates (email: {payload['payload']['invitee']['email']})")
                else:
                    print("\n⚠️  Webhook returned ok=false")
            else:
                print(f"\n❌ Webhook request failed with status code {response.status_code}")
        except json.JSONDecodeError:
            print("📄 Response Body (non-JSON):")
            print(response.text[:500])
            if response.status_code == 200:
                print("\n✅ Webhook accepted (non-JSON response)")
            else:
                print(f"\n❌ Webhook request failed with status code {response.status_code}")

        return 0

    except httpx.TimeoutException:
        print("\n⏱️  Request timed out after 30 seconds")
        print("   The webhook may still be processing. Check worker logs.")
        return 1
    except httpx.ConnectError as e:
        print(f"\n🔌 Connection error: {e}")
        print(f"   Make sure your API is running at {base_url}")
        print("   If using Docker: docker-compose up")
        return 1
    except Exception as e:
        print(f"\n❌ Error triggering webhook: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
