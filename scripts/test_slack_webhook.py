#!/usr/bin/env python3
"""
Test Slack webhook notifications.

This script allows you to test all Slack notification types to verify
your webhook URL is working correctly.

Usage:
    # Test all notification types
    python3 scripts/test_slack_webhook.py --all

    # Test a specific notification type
    python3 scripts/test_slack_webhook.py --demo-booked
    python3 scripts/test_slack_webhook.py --demo-canceled
    python3 scripts/test_slack_webhook.py --demo-completed
    python3 scripts/test_slack_webhook.py --enrichment

    # Test with custom webhook URL (overrides .env)
    python3 scripts/test_slack_webhook.py --all --webhook-url https://hooks.slack.com/services/YOUR/WEBHOOK/URL

    # Use different .env file
    python3 scripts/test_slack_webhook.py --all --env .env.production
"""

import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import after setting up path
from app.services.slack_service import (
    notify_demo_booked,
    notify_demo_canceled,
    notify_demo_completed,
    notify_enrichment_completed,
    send_slack_alert,
    send_slack_event,
)
from app.settings import Settings, get_settings


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


def _reset_settings_cache():
    """Reset the Settings singleton cache to pick up new environment variables"""
    import app.settings as settings_module
    # Access the private _settings variable to reset it
    if hasattr(settings_module, '_settings'):
        settings_module._settings = None


def test_simple_alert(webhook_url: str | None = None):
    """Test basic text alert"""
    print("📤 Testing simple text alert...")
    
    if webhook_url:
        # Temporarily override webhook URL
        original = os.environ.get("SLACK_WEBHOOK_URL")
        os.environ["SLACK_WEBHOOK_URL"] = webhook_url
        _reset_settings_cache()
        try:
            send_slack_alert(text="🧪 Test alert from gv-sales-integrator")
            print("✅ Simple alert sent successfully!")
        finally:
            if original:
                os.environ["SLACK_WEBHOOK_URL"] = original
            else:
                del os.environ["SLACK_WEBHOOK_URL"]
            _reset_settings_cache()
    else:
        send_slack_alert(text="🧪 Test alert from gv-sales-integrator")
        print("✅ Simple alert sent successfully!")


def test_demo_booked(webhook_url: str | None = None):
    """Test demo booked notification"""
    print("📤 Testing demo booked notification...")
    
    if webhook_url:
        original = os.environ.get("SLACK_WEBHOOK_URL")
        os.environ["SLACK_WEBHOOK_URL"] = webhook_url
        _reset_settings_cache()
        try:
            notify_demo_booked(
                email="test@example.com",
                name="John Doe",
                company="Acme Corporation",
                demo_datetime="Dec 20, 2024 at 2:00 PM EST",
                lead_id="1234567890",
            )
            print("✅ Demo booked notification sent successfully!")
        finally:
            if original:
                os.environ["SLACK_WEBHOOK_URL"] = original
            else:
                del os.environ["SLACK_WEBHOOK_URL"]
            _reset_settings_cache()
    else:
        notify_demo_booked(
            email="test@example.com",
            name="John Doe",
            company="Acme Corporation",
            demo_datetime="Dec 20, 2024 at 2:00 PM EST",
            lead_id="1234567890",
        )
        print("✅ Demo booked notification sent successfully!")


def test_demo_canceled(webhook_url: str | None = None):
    """Test demo canceled notification"""
    print("📤 Testing demo canceled notification...")
    
    if webhook_url:
        original = os.environ.get("SLACK_WEBHOOK_URL")
        os.environ["SLACK_WEBHOOK_URL"] = webhook_url
        _reset_settings_cache()
        try:
            notify_demo_canceled(
                email="test@example.com",
                name="Jane Smith",
                company="TechCo Inc",
                lead_id="1234567891",
            )
            print("✅ Demo canceled notification sent successfully!")
        finally:
            if original:
                os.environ["SLACK_WEBHOOK_URL"] = original
            else:
                del os.environ["SLACK_WEBHOOK_URL"]
            _reset_settings_cache()
    else:
        notify_demo_canceled(
            email="test@example.com",
            name="Jane Smith",
            company="TechCo Inc",
            lead_id="1234567891",
        )
        print("✅ Demo canceled notification sent successfully!")


def test_demo_completed(webhook_url: str | None = None):
    """Test demo completed notification"""
    print("📤 Testing demo completed notification...")
    
    if webhook_url:
        original = os.environ.get("SLACK_WEBHOOK_URL")
        os.environ["SLACK_WEBHOOK_URL"] = webhook_url
        _reset_settings_cache()
        try:
            notify_demo_completed(
                email="test@example.com",
                name="John Doe",
                company="Acme Corporation",
                meeting_duration=45,
                meddic_confidence="High",
                lead_id="1234567890",
            )
            print("✅ Demo completed notification sent successfully!")
        finally:
            if original:
                os.environ["SLACK_WEBHOOK_URL"] = original
            else:
                del os.environ["SLACK_WEBHOOK_URL"]
            _reset_settings_cache()
    else:
        notify_demo_completed(
            email="test@example.com",
            name="John Doe",
            company="Acme Corporation",
            meeting_duration=45,
            meddic_confidence="High",
            lead_id="1234567890",
        )
        print("✅ Demo completed notification sent successfully!")


def test_enrichment_completed(webhook_url: str | None = None):
    """Test enrichment completed notification"""
    print("📤 Testing enrichment completed notification...")
    
    if webhook_url:
        original = os.environ.get("SLACK_WEBHOOK_URL")
        os.environ["SLACK_WEBHOOK_URL"] = webhook_url
        _reset_settings_cache()
        try:
            notify_enrichment_completed(
                email="test@example.com",
                company="Acme Corporation",
                data_sources=["apollo_person", "apollo_company", "website"],
                lead_id="1234567890",
            )
            print("✅ Enrichment completed notification sent successfully!")
        finally:
            if original:
                os.environ["SLACK_WEBHOOK_URL"] = original
            else:
                del os.environ["SLACK_WEBHOOK_URL"]
            _reset_settings_cache()
    else:
        notify_enrichment_completed(
            email="test@example.com",
            company="Acme Corporation",
            data_sources=["apollo_person", "apollo_company", "website"],
            lead_id="1234567890",
        )
        print("✅ Enrichment completed notification sent successfully!")


def test_custom_event(webhook_url: str | None = None):
    """Test custom event notification"""
    print("📤 Testing custom event notification...")
    
    if webhook_url:
        original = os.environ.get("SLACK_WEBHOOK_URL")
        os.environ["SLACK_WEBHOOK_URL"] = webhook_url
        _reset_settings_cache()
        try:
            send_slack_event(
                title="🎉 Custom Test Event",
                message="This is a custom notification with rich formatting.",
                color="good",
                fields=[
                    {"title": "Test Field 1", "value": "Value 1"},
                    {"title": "Test Field 2", "value": "Value 2"},
                    {"title": "Status", "value": "✅ Working"},
                ],
            )
            print("✅ Custom event notification sent successfully!")
        finally:
            if original:
                os.environ["SLACK_WEBHOOK_URL"] = original
            else:
                del os.environ["SLACK_WEBHOOK_URL"]
            _reset_settings_cache()
    else:
        send_slack_event(
            title="🎉 Custom Test Event",
            message="This is a custom notification with rich formatting.",
            color="good",
            fields=[
                {"title": "Test Field 1", "value": "Value 1"},
                {"title": "Test Field 2", "value": "Value 2"},
                {"title": "Status", "value": "✅ Working"},
            ],
        )
        print("✅ Custom event notification sent successfully!")


def main():
    parser = argparse.ArgumentParser(
        description="Test Slack webhook notifications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test all notification types
  python3 scripts/test_slack_webhook.py --all

  # Test specific notification
  python3 scripts/test_slack_webhook.py --demo-booked

  # Test with custom webhook URL
  python3 scripts/test_slack_webhook.py --all --webhook-url https://hooks.slack.com/services/YOUR/URL

  # Use different .env file
  python3 scripts/test_slack_webhook.py --all --env .env.production
        """,
    )
    parser.add_argument("--all", action="store_true", help="Test all notification types")
    parser.add_argument("--simple", action="store_true", help="Test simple text alert")
    parser.add_argument("--demo-booked", action="store_true", help="Test demo booked notification")
    parser.add_argument("--demo-canceled", action="store_true", help="Test demo canceled notification")
    parser.add_argument("--demo-completed", action="store_true", help="Test demo completed notification")
    parser.add_argument("--enrichment", action="store_true", help="Test enrichment completed notification")
    parser.add_argument("--custom", action="store_true", help="Test custom event notification")
    parser.add_argument(
        "--webhook-url",
        type=str,
        help="Override SLACK_WEBHOOK_URL from .env file",
    )
    parser.add_argument(
        "--env",
        default=".env",
        help="Environment file to load (default: .env)",
    )
    parser.add_argument(
        "--format-mode",
        choices=["blocks", "attachments", "text"],
        help="Override SLACK_FORMAT_MODE for this test (blocks/attachments/text)",
    )

    args = parser.parse_args()

    # Load environment variables
    env_vars = load_env_file(args.env)

    # Get webhook URL (command line override takes precedence)
    webhook_url = args.webhook_url or env_vars.get("SLACK_WEBHOOK_URL")

    if not webhook_url:
        print("❌ Error: SLACK_WEBHOOK_URL not found!")
        print(f"   Checked: {args.env}")
        print("   Options:")
        print("   1. Set SLACK_WEBHOOK_URL in your .env file")
        print("   2. Use --webhook-url flag to provide it directly")
        sys.exit(1)

    print("━" * 60)
    print("🧪 SLACK WEBHOOK TEST")
    print("━" * 60)
    print(f"📋 Webhook URL: {webhook_url[:50]}..." if len(webhook_url) > 50 else f"📋 Webhook URL: {webhook_url}")
    print()

    # Set webhook URL in environment for Settings to pick up
    os.environ["SLACK_WEBHOOK_URL"] = webhook_url
    
    # Override format mode if specified
    if args.format_mode:
        os.environ["SLACK_FORMAT_MODE"] = args.format_mode
        print(f"📝 Using format mode: {args.format_mode}")
        print()
    
    _reset_settings_cache()

    # Determine what to test
    test_all = args.all or not any(
        [
            args.simple,
            args.demo_booked,
            args.demo_canceled,
            args.demo_completed,
            args.enrichment,
            args.custom,
        ]
    )

    if test_all:
        print("Testing all notification types...\n")
        test_simple_alert(webhook_url)
        print()
        test_demo_booked(webhook_url)
        print()
        test_demo_canceled(webhook_url)
        print()
        test_demo_completed(webhook_url)
        print()
        test_enrichment_completed(webhook_url)
        print()
        test_custom_event(webhook_url)
    else:
        if args.simple:
            test_simple_alert(webhook_url)
            print()
        if args.demo_booked:
            test_demo_booked(webhook_url)
            print()
        if args.demo_canceled:
            test_demo_canceled(webhook_url)
            print()
        if args.demo_completed:
            test_demo_completed(webhook_url)
            print()
        if args.enrichment:
            test_enrichment_completed(webhook_url)
            print()
        if args.custom:
            test_custom_event(webhook_url)
            print()

    print("━" * 60)
    print("✅ All tests completed!")
    print("📱 Check your Slack channel to see the notifications.")
    print("━" * 60)


if __name__ == "__main__":
    main()
