#!/usr/bin/env python3
"""Delete a Calendly webhook subscription"""
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


def delete_webhook(token: str, webhook_id: str) -> bool:
    """Delete a webhook subscription by ID"""
    url = f"https://api.calendly.com/webhook_subscriptions/{webhook_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=30.0) as client:
        resp = client.delete(url, headers=headers)
        resp.raise_for_status()
        return True


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/calendly_delete_webhook.py <webhook_id> [--env .env.production]")
        print("\nTo list webhook IDs:")
        print("  python scripts/calendly_list_webhooks.py [--env .env.production]")
        return 1

    webhook_id = sys.argv[1]

    # Parse optional env file argument
    env_file = ".env"
    if len(sys.argv) > 2:
        if sys.argv[2] in ("--env", "-e") and len(sys.argv) > 3:
            env_file = sys.argv[3]

    token = load_env_var("CALENDLY_API_TOKEN", env_file)
    if not token:
        print(f"❌ CALENDLY_API_TOKEN not found in {env_file}")
        return 1

    print(f"🗑️  Deleting webhook: {webhook_id}\n")

    try:
        delete_webhook(token, webhook_id)
        print("✅ Webhook deleted successfully!")
        print("\n💡 Next: Create a new webhook with updated URL:")
        print("   python scripts/calendly_setup_webhook.py")
        return 0

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            print(f"❌ Webhook not found: {webhook_id}")
        else:
            print(f"❌ Error {e.response.status_code}: {e.response.text}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
