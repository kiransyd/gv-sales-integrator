#!/usr/bin/env python3
"""Check enrichment job status by event ID or email"""
import json
import sys
from pathlib import Path
import httpx


def check_by_event_id(event_id: str, base_url: str = "http://localhost:8000") -> dict | None:
    """Check enrichment status via debug endpoint"""
    try:
        url = f"{base_url}/debug/events/{event_id}"
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        print(f"❌ Error checking event: {e}")
        return None


def check_by_email(email: str, base_url: str = "http://localhost:8000") -> None:
    """Trigger enrichment and show status"""
    try:
        url = f"{base_url}/enrich/lead"
        headers = {
            "Content-Type": "application/json",
            "X-Enrich-Secret": "enrich_secret_2025"
        }
        payload = {"email": email}

        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            result = resp.json()

            print(f"✅ Enrichment queued for: {email}")
            print(f"   Event ID: {result['event_id']}")
            print(f"   Message: {result['message']}\n")
            print(f"💡 To check status, run:")
            print(f"   python scripts/check_enrichment.py {result['event_id']}")

    except Exception as e:
        print(f"❌ Error triggering enrichment: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/check_enrichment.py <event_id>")
        print("  python scripts/check_enrichment.py --email <email>")
        print("\nExamples:")
        print("  python scripts/check_enrichment.py d12bb51d-5510-4795-9b17-fd6cf9ca302f")
        print("  python scripts/check_enrichment.py --email kiran@govisually.com")
        return 1

    if sys.argv[1] == "--email":
        if len(sys.argv) < 3:
            print("❌ Email required after --email flag")
            return 1
        email = sys.argv[2]
        check_by_email(email)
        return 0

    event_id = sys.argv[1]

    print(f"🔍 Checking enrichment status for event: {event_id}\n")

    event = check_by_event_id(event_id)
    if not event:
        print(f"❌ Event not found")
        return 1

    # Display event status
    status = event.get("status", "unknown")
    attempts = event.get("attempts", 0)
    last_error = event.get("last_error", "")

    status_emoji = {
        "received": "⏳",
        "processing": "🔄",
        "completed": "✅",
        "processed": "✅",  # Processed is same as completed
        "failed": "❌"
    }.get(status, "❓")

    print(f"{status_emoji} Status: {status}")
    print(f"   Event ID: {event.get('id', event_id)}")
    print(f"   Source: {event.get('source', 'N/A')}")
    print(f"   Event Type: {event.get('event_type', 'N/A')}")
    print(f"   Attempts: {attempts}")
    print(f"   Received: {event.get('received_at', 'N/A')}")

    if last_error:
        print(f"\n❌ Last Error:")
        print(f"   {last_error}")

    # Show payload preview
    payload = event.get("payload", {})
    email = payload.get("email", "N/A")
    lead_id = payload.get("lead_id", "N/A")

    print(f"\n📧 Enrichment Target:")
    print(f"   Email: {email}")
    if lead_id != "N/A":
        print(f"   Lead ID: {lead_id}")

    # Status-specific guidance
    if status in ["completed", "processed"]:
        print(f"\n✅ Enrichment complete! Check Zoho Lead for:")
        print(f"   • Apollo fields (Job Title, Seniority, Company Size, etc.)")
        print(f"   • Enrichment note")
        print(f"\n💡 To check Zoho Lead:")
        print(f"   python scripts/check_zoho_lead.py {email}")

    elif status == "processing":
        print(f"\n⏳ Still processing... Check back in 30-60 seconds")
        print(f"\n💡 To watch worker logs:")
        print(f"   docker compose logs -f worker")

    elif status == "failed":
        print(f"\n❌ Enrichment failed after {attempts} attempt(s)")
        print(f"\n💡 Check worker logs for details:")
        print(f"   docker compose logs worker | grep {event_id}")

    elif status == "received":
        print(f"\n⏳ Queued, waiting for worker to pick up...")
        print(f"\n💡 Check if worker is running:")
        print(f"   docker compose ps worker")

    return 0


if __name__ == "__main__":
    sys.exit(main())
