#!/usr/bin/env python3
"""Debug Apollo API directly with raw requests"""
import json
import sys
import httpx
from pathlib import Path
import re


def load_env_var(key: str, default: str = "") -> str:
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        content = env_file.read_text()
        match = re.search(rf"^{re.escape(key)}=(.+)$", content, flags=re.M)
        if match:
            return match.group(1).strip()
    return default


def test_person(email: str):
    """Test Apollo person API with raw request"""
    api_key = load_env_var("APOLLO_API_KEY")

    if not api_key:
        print("❌ APOLLO_API_KEY not found in .env")
        return 1

    url = "https://api.apollo.io/v1/people/match"
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": api_key,
    }
    payload = {"email": email}

    print(f"🔍 Testing Apollo Person API")
    print(f"   URL: {url}")
    print(f"   Email: {email}")
    print(f"   API Key: {api_key[:10]}...{api_key[-5:]}\n")

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=headers, json=payload)

            print(f"📥 Response Status: {resp.status_code}")
            print(f"📥 Response Headers: {dict(resp.headers)}\n")

            if resp.status_code == 200:
                body = resp.json()
                print(f"✅ Success!\n")
                print(json.dumps(body, indent=2))
                return 0
            else:
                print(f"❌ Failed!")
                print(f"Response Body:")
                print(resp.text)
                return 1

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def test_company(domain: str):
    """Test Apollo company API with raw request"""
    api_key = load_env_var("APOLLO_API_KEY")

    if not api_key:
        print("❌ APOLLO_API_KEY not found in .env")
        return 1

    url = "https://api.apollo.io/api/v1/organizations/enrich"
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": api_key,
    }
    params = {"domain": domain}

    print(f"🔍 Testing Apollo Company API")
    print(f"   URL: {url}")
    print(f"   Method: GET")
    print(f"   Domain: {domain}")
    print(f"   API Key: {api_key[:10]}...{api_key[-5:]}\n")

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url, headers=headers, params=params)

            print(f"📥 Response Status: {resp.status_code}")
            print(f"📥 Response Headers: {dict(resp.headers)}\n")

            if resp.status_code == 200:
                body = resp.json()
                print(f"✅ Success!\n")
                print(json.dumps(body, indent=2))
                return 0
            else:
                print(f"❌ Failed!")
                print(f"Response Body:")
                print(resp.text)
                return 1

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/debug_apollo.py person <email>")
        print("  python scripts/debug_apollo.py company <domain>")
        print("\nExamples:")
        print("  python scripts/debug_apollo.py person kiran@govisually.com")
        print("  python scripts/debug_apollo.py company govisually.com")
        return 1

    cmd = sys.argv[1]

    if cmd == "person":
        if len(sys.argv) < 3:
            print("❌ Email required")
            return 1
        return test_person(sys.argv[2])

    elif cmd == "company":
        if len(sys.argv) < 3:
            print("❌ Domain required")
            return 1
        return test_company(sys.argv[2])

    else:
        print(f"❌ Unknown command: {cmd}")
        print("Use: person or company")
        return 1


if __name__ == "__main__":
    sys.exit(main())
