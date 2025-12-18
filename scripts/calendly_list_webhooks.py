#!/usr/bin/env python3
"""List all Calendly webhook subscriptions"""
import json
import sys
from pathlib import Path
import httpx


def load_env_var(key: str, env_file_name: str = ".env") -> str:
    env_file = Path(__file__).parent.parent / env_file_name
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip()
    return ""


def get_organization_uri(token: str) -> str:
    """Get the organization URI from user info"""
    url = "https://api.calendly.com/users/me"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=30.0) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        # Extract organization URI from various possible locations
        resource = data.get("resource", {})
        org_uri = (
            resource.get("current_organization") or
            resource.get("organization") or
            data.get("organization", "")
        )
        return org_uri


def list_webhooks(token: str, organization_uri: str) -> list:
    """List all webhook subscriptions for an organization"""
    url = "https://api.calendly.com/webhook_subscriptions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    params = {
        "organization": organization_uri,
        "scope": "organization"
    }

    with httpx.Client(timeout=30.0) as client:
        resp = client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

        # Calendly wraps response in "collection"
        return data.get("collection", [])


def main():
    # Parse command-line arguments for env file
    env_file = ".env"
    if len(sys.argv) > 1:
        if sys.argv[1] in ("--env", "-e") and len(sys.argv) > 2:
            env_file = sys.argv[2]
        else:
            env_file = sys.argv[1]

    token = load_env_var("CALENDLY_API_TOKEN", env_file)
    if not token:
        print(f"❌ CALENDLY_API_TOKEN not found in {env_file}")
        return 1

    print("📋 Listing Calendly webhook subscriptions...\n")

    try:
        # Get organization URI first
        org_uri = get_organization_uri(token)
        if not org_uri:
            print("❌ Could not determine organization URI")
            return 1

        webhooks = list_webhooks(token, org_uri)

        if not webhooks:
            print("No webhook subscriptions found.")
            return 0

        for i, webhook in enumerate(webhooks):
            uri = webhook.get("uri", "")
            webhook_id = uri.split("/")[-1] if uri else "N/A"
            callback_url = webhook.get("callback_url", "N/A")
            scope = webhook.get("scope", "N/A")
            state = webhook.get("state", "N/A")
            events = ", ".join(webhook.get("events", []))

            print(f"{i + 1}. ID: {webhook_id}")
            print(f"   URL: {callback_url}")
            print(f"   Scope: {scope}")
            print(f"   State: {state}")
            print(f"   Events: {events}")
            print()

        print(f"\n💡 To delete a webhook, run:")
        print(f"   python scripts/calendly_delete_webhook.py <webhook_id>")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
