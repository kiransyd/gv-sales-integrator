#!/usr/bin/env python3
"""
Test the website scraping endpoint.

Usage:
    python3 scripts/test_scrape_endpoint.py deputy.com
    python3 scripts/test_scrape_endpoint.py nike.com --env .env.production
"""

import argparse
import json
import sys
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
            env_vars[key] = value

    return env_vars


def scrape_website(domain: str, base_url: str):
    """Call the scrape/website endpoint"""

    url = f"{base_url}/scrape/website"
    headers = {"Content-Type": "application/json"}
    payload = {"domain": domain}

    print(f"📤 Scraping website: {domain}")
    print(f"🌐 Endpoint: {url}")
    print()

    try:
        with httpx.Client(timeout=90.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            result = resp.json()

        if result.get("ok"):
            print(f"✅ Successfully scraped {domain}\n")
            intel = result.get("intelligence", {})

            # Pretty print the results
            print("━" * 60)
            print("🌐 WEBSITE INTELLIGENCE")
            print("━" * 60)
            print()

            if intel.get("value_proposition"):
                print("What they do:")
                print(intel["value_proposition"])
                print()

            if intel.get("target_market"):
                print("Who they sell to:")
                print(intel["target_market"])
                print()

            if intel.get("products_services"):
                print("Products/services:")
                print(intel["products_services"])
                print()

            if intel.get("pricing_model"):
                print("Pricing:")
                print(intel["pricing_model"])
                print()

            if intel.get("recent_news"):
                print("📰 Recent news:")
                print(intel["recent_news"])
                print()

            if intel.get("growth_signals"):
                print("🚀 Growth signals:")
                print(intel["growth_signals"])
                print()

            if intel.get("key_pain_points"):
                print("Their customers' pain points:")
                print(intel["key_pain_points"])
                print()

            if intel.get("competitors_mentioned"):
                print("Competitors mentioned:")
                print(intel["competitors_mentioned"])
                print()

            if intel.get("sales_insights"):
                print("🎯 HOW TO APPROACH THIS DEMO:")
                print(intel["sales_insights"])
                print()

            print("━" * 60)
            print()
            print("💾 Full JSON response:")
            print(json.dumps(result, indent=2))

        else:
            print(f"❌ Failed to scrape {domain}")
            print(f"Error: {result.get('error')}")
            sys.exit(1)

    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP Error {e.response.status_code}")
        print(f"Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Test website scraping endpoint")
    parser.add_argument("domain", help="Domain to scrape (e.g., deputy.com)")
    parser.add_argument("--env", default=".env.production", help="Environment file (default: .env.production)")

    args = parser.parse_args()

    # Load environment
    env_vars = load_env_file(args.env)

    base_url = env_vars.get("BASE_URL", "http://localhost:8000")

    # Scrape website
    scrape_website(args.domain, base_url)


if __name__ == "__main__":
    main()
