#!/usr/bin/env python3
"""
Test Intercom company.updated webhook endpoint.

This script sends test company.updated webhooks to trigger expansion signal detection.
You can monitor worker logs to see the processing.

Usage:
    # Test with a company that should trigger signals
    python3 scripts/test_intercom_company_updated.py --signal team_at_capacity

    # Test with a company that has no signals
    python3 scripts/test_intercom_company_updated.py --signal none

    # Test with custom company data
    python3 scripts/test_intercom_company_updated.py --custom

    # Use production URL
    python3 scripts/test_intercom_company_updated.py --signal power_user --env .env.production
"""

import argparse
import hashlib
import hmac
import json
import sys
import time
from pathlib import Path

import httpx


def load_env_file(env_path: str) -> dict[str, str]:
    """Load environment variables from .env file"""
    env_vars = {}
    env_file = Path(env_path)

    if not env_file.exists():
        print(f"❌ Environment file not found: {env_path}")
        sys.exit(1)

    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            # Remove quotes if present
            value = value.strip('"').strip("'")
            env_vars[key] = value

    return env_vars


def generate_signature(secret: str, body: bytes) -> str:
    """Generate HMAC SHA256 signature for Intercom webhook"""
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def build_company_updated_payload(
    company_id: str,
    company_name: str,
    custom_attributes: dict,
    user_count: int = 1,
) -> dict:
    """Build a company.updated webhook payload"""
    now = int(time.time())
    updated_at = now

    return {
        "type": "notification_event",
        "topic": "company.updated",
        "created_at": now,
        "data": {
            "item": {
                "type": "company",
                "id": company_id,
                "name": company_name,
                "company_id": company_id,
                "user_count": user_count,
                "session_count": 100,
                "last_request_at": now - 3600,  # 1 hour ago
                "created_at": now - 86400 * 30,  # 30 days ago
                "updated_at": updated_at,
                "custom_attributes": custom_attributes,
            }
        }
    }


def get_test_scenarios() -> dict[str, dict]:
    """Get predefined test scenarios for different expansion signals
    
    Note: Only trial_engaged_user signal is enabled. All other signals have been disabled.
    """
    now = int(time.time())
    
    return {
        "trial_engaged": {
            "company_id": "test_company_trial_001",
            "company_name": "Test Company - Engaged Trial",
            "user_count": 2,
            "custom_attributes": {
                "gv_no_of_members": 2,
                "gv_total_active_projects": 2,  # 2+ projects AND 2+ team members
                "gv_projects_allowed": 3,
                "gv_subscription_plan": "Trial",
                "gv_subscription_status": "trial",
                "gv_subscription_exp": "1/2026",
                "gv_subscription_exp_in_sec": now + (2 * 24 * 60 * 60),  # 2 days from now
                "gv_checklists": 0,
            },
            "expected_signals": ["trial_engaged_user"],
        },
        "trial_not_engaged": {
            "company_id": "test_company_trial_002",
            "company_name": "Test Company - Trial Not Engaged",
            "user_count": 1,
            "custom_attributes": {
                "gv_no_of_members": 1,  # Only 1 team member (needs 2+)
                "gv_total_active_projects": 1,  # Only 1 project (needs 2+)
                "gv_projects_allowed": 3,
                "gv_subscription_plan": "Trial",
                "gv_subscription_status": "trial",
                "gv_subscription_exp_in_sec": now + (5 * 24 * 60 * 60),
                "gv_checklists": 0,
            },
            "expected_signals": [],  # Doesn't meet criteria (2+ projects AND 2+ team members)
        },
        "paid_user": {
            "company_id": "test_company_paid_001",
            "company_name": "Test Company - Paid User",
            "user_count": 5,
            "custom_attributes": {
                "gv_no_of_members": 5,
                "gv_total_active_projects": 120,
                "gv_projects_allowed": 1000,
                "gv_subscription_plan": "PRO - Yearly",
                "gv_subscription_status": "paid",
                "gv_subscription_exp_in_sec": now + (200 * 24 * 60 * 60),
                "gv_checklists": 2,
            },
            "expected_signals": [],  # Paid user signals disabled
        },
    }


def send_webhook(
    url: str,
    payload: dict,
    webhook_secret: str | None = None,
) -> dict:
    """Send webhook to endpoint"""
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}

    # Add signature if secret is provided
    if webhook_secret:
        signature = generate_signature(webhook_secret, body)
        headers["X-Intercom-Signature"] = signature

    print(f"📤 Sending company.updated webhook to: {url}")
    print(f"   Company: {payload['data']['item']['name']}")
    print(f"   Company ID: {payload['data']['item']['id']}")
    print(f"   User Count: {payload['data']['item']['user_count']}")
    print()

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP Error {e.response.status_code}")
        print(f"Response: {e.response.text}")
        return {"error": str(e)}
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(
        description="Test Intercom company.updated webhook endpoint",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test trial engaged signal (only enabled signal)
  python3 scripts/test_intercom_company_updated.py --signal trial_engaged

  # Test with production URL
  python3 scripts/test_intercom_company_updated.py --signal trial_engaged --env .env.production

  # List all available test scenarios
  python3 scripts/test_intercom_company_updated.py --list
        """,
    )
    parser.add_argument(
        "--signal",
        type=str,
        help="Signal type to test: trial_engaged, trial_not_engaged, paid_user",
    )
    parser.add_argument(
        "--env",
        default=".env",
        help="Environment file (default: .env)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available test scenarios",
    )
    parser.add_argument(
        "--custom",
        action="store_true",
        help="Use custom company data (interactive)",
    )

    args = parser.parse_args()

    # Load environment
    env_vars = load_env_file(args.env)
    base_url = env_vars.get("BASE_URL", "http://localhost:8000")
    webhook_secret = env_vars.get("INTERCOM_WEBHOOK_SECRET", "")

    webhook_url = f"{base_url}/webhooks/intercom"

    # Get test scenarios
    scenarios = get_test_scenarios()

    if args.list:
        print("📋 Available Test Scenarios:\n")
        for name, scenario in scenarios.items():
            print(f"  {name}:")
            print(f"    Company: {scenario['company_name']}")
            print(f"    Expected Signals: {', '.join(scenario['expected_signals']) or 'None'}")
            print()
        return

    if args.custom:
        # Interactive custom payload
        print("🔧 Custom Company Data (Interactive Mode)\n")
        company_id = input("Company ID (or press Enter for auto-generated): ").strip()
        if not company_id:
            company_id = f"test_custom_{int(time.time())}"

        company_name = input("Company Name: ").strip() or "Test Custom Company"
        user_count = int(input("User Count (default 1): ").strip() or "1")

        print("\nEnter custom attributes (press Enter to skip):")
        custom_attrs = {}
        custom_attrs["gv_no_of_members"] = input("  gv_no_of_members: ").strip() or "1"
        custom_attrs["gv_total_active_projects"] = input("  gv_total_active_projects: ").strip() or "0"
        custom_attrs["gv_projects_allowed"] = input("  gv_projects_allowed: ").strip() or "250"
        custom_attrs["gv_subscription_plan"] = input("  gv_subscription_plan: ").strip() or "PRO - Yearly"
        custom_attrs["gv_subscription_status"] = input("  gv_subscription_status: ").strip() or "paid"
        custom_attrs["gv_checklists"] = input("  gv_checklists: ").strip() or "0"

        # Convert string numbers to ints where appropriate
        for key in ["gv_no_of_members", "gv_total_active_projects", "gv_projects_allowed", "gv_checklists"]:
            if custom_attrs[key]:
                try:
                    custom_attrs[key] = int(custom_attrs[key])
                except ValueError:
                    pass

        payload = build_company_updated_payload(
            company_id=company_id,
            company_name=company_name,
            custom_attributes=custom_attrs,
            user_count=user_count,
        )
    elif args.signal:
        if args.signal not in scenarios:
            print(f"❌ Unknown signal type: {args.signal}")
            print(f"Available: {', '.join(scenarios.keys())}")
            sys.exit(1)

        scenario = scenarios[args.signal]
        print(f"🧪 Testing scenario: {args.signal}")
        print(f"   Expected signals: {', '.join(scenario['expected_signals']) or 'None'}")
        print()

        payload = build_company_updated_payload(
            company_id=scenario["company_id"],
            company_name=scenario["company_name"],
            custom_attributes=scenario["custom_attributes"],
            user_count=scenario["user_count"],
        )
    else:
        # Default: test trial_engaged
        print("ℹ️  No signal specified, using default: trial_engaged\n")
        scenario = scenarios["trial_engaged"]
        payload = build_company_updated_payload(
            company_id=scenario["company_id"],
            company_name=scenario["company_name"],
            custom_attributes=scenario["custom_attributes"],
            user_count=scenario["user_count"],
        )

    # Send webhook
    print("━" * 60)
    result = send_webhook(webhook_url, payload, webhook_secret)
    print("━" * 60)
    print()

    # Display result
    if result.get("ok"):
        print("✅ Webhook accepted!")
        print(f"   Event ID: {result.get('event_id')}")
        print(f"   Queued: {result.get('queued', False)}")
        if result.get("duplicate"):
            print("   ⚠️  Duplicate webhook (idempotency)")
        print()
        print("📊 Next steps:")
        print("   1. Check worker logs for processing")
        print("   2. Look for expansion signal detection")
        print("   3. Check Zoho for lead/task creation")
        print("   4. Check Slack for notifications (if high/critical priority)")
    elif result.get("ignored"):
        print("⚠️  Webhook ignored")
        print(f"   Reason: {result.get('reason')}")
    else:
        print("❌ Webhook failed")
        print(f"   Error: {result.get('error', result)}")

    print()
    print("💡 Tip: Monitor worker logs with:")
    print("   docker logs -f gv-sales-integrator-worker-1")
    print("   # or")
    print("   tail -f /path/to/worker.log")


if __name__ == "__main__":
    main()
