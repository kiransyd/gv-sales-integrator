#!/usr/bin/env python3
"""Create Apollo custom fields in Zoho CRM Leads module"""
import json
import re
import sys
from pathlib import Path
import httpx


def load_env_var(key: str, default: str = "") -> str:
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        content = env_file.read_text()
        match = re.search(rf"^{re.escape(key)}=(.+)$", content, flags=re.M)
        if match:
            return match.group(1).strip()
    return default


def get_zoho_access_token() -> str:
    """Get Zoho access token using refresh token"""
    dc = load_env_var("ZOHO_DC", "au")
    refresh_token = load_env_var("ZOHO_REFRESH_TOKEN", "")
    client_id = load_env_var("ZOHO_CLIENT_ID", "")
    client_secret = load_env_var("ZOHO_CLIENT_SECRET", "")

    if not refresh_token:
        raise ValueError("ZOHO_REFRESH_TOKEN not set in .env")

    # Map DC to correct Zoho domain
    dc_domain = "com.au" if dc == "au" else dc
    token_url = f"https://accounts.zoho.{dc_domain}/oauth/v2/token"
    token_data = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
    }

    with httpx.Client(timeout=10.0) as client:
        resp = client.post(token_url, data=token_data)
        resp.raise_for_status()
        return resp.json()["access_token"]


def create_custom_field(access_token: str, module: str, field_config: dict) -> dict:
    """Create a custom field in Zoho CRM"""
    dc = load_env_var("ZOHO_DC", "au")
    # Map DC to correct Zoho domain
    dc_domain = "com.au" if dc == "au" else dc
    url = f"https://www.zohoapis.{dc_domain}/crm/v2/settings/fields?module={module}"

    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "fields": [field_config]
    }

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()


def main():
    print("🔧 Creating Apollo custom fields in Zoho CRM...\n")

    # Get access token
    try:
        access_token = get_zoho_access_token()
        print("✅ Got Zoho access token\n")
    except Exception as e:
        print(f"❌ Failed to get Zoho access token: {e}")
        return 1

    # Define all Apollo fields
    fields_to_create = [
        {
            "api_name": "Apollo_Job_Title",
            "field_label": "Apollo Job Title",
            "data_type": "text",
            "length": 255,
        },
        {
            "api_name": "Apollo_Seniority",
            "field_label": "Apollo Seniority",
            "data_type": "text",
            "length": 100,
        },
        {
            "api_name": "Apollo_Department",
            "field_label": "Apollo Department",
            "data_type": "text",
            "length": 100,
        },
        {
            "api_name": "Apollo_LinkedIn_URL",
            "field_label": "Apollo LinkedIn URL",
            "data_type": "website",
        },
        {
            "api_name": "Apollo_Phone",
            "field_label": "Apollo Phone",
            "data_type": "phone",
        },
        {
            "api_name": "Apollo_Company_Size",
            "field_label": "Apollo Company Size",
            "data_type": "text",
            "length": 100,
        },
        {
            "api_name": "Apollo_Company_Revenue",
            "field_label": "Apollo Company Revenue",
            "data_type": "text",
            "length": 100,
        },
        {
            "api_name": "Apollo_Company_Industry",
            "field_label": "Apollo Company Industry",
            "data_type": "text",
            "length": 255,
        },
        {
            "api_name": "Apollo_Company_Founded_Year",
            "field_label": "Apollo Company Founded Year",
            "data_type": "text",
            "length": 50,
        },
        {
            "api_name": "Apollo_Company_Funding_Stage",
            "field_label": "Apollo Company Funding Stage",
            "data_type": "text",
            "length": 100,
        },
        {
            "api_name": "Apollo_Company_Funding_Total",
            "field_label": "Apollo Company Funding Total",
            "data_type": "text",
            "length": 100,
        },
        {
            "api_name": "Apollo_Tech_Stack",
            "field_label": "Apollo Tech Stack",
            "data_type": "textarea",
        },
    ]

    module = load_env_var("ZOHO_LEADS_MODULE", "Leads")
    created_count = 0
    failed_count = 0

    for field_config in fields_to_create:
        field_name = field_config["api_name"]
        try:
            print(f"Creating field: {field_name}...", end=" ")
            result = create_custom_field(access_token, module, field_config)

            # Handle different response formats
            if not isinstance(result, dict):
                print(f"⚠️  Unexpected response type: {type(result)}")
                print(f"   Full result: {result}")
                failed_count += 1
            elif result.get("fields") and result["fields"][0].get("status", {}).get("status_code") == "SUCCESS":
                print("✅")
                created_count += 1
            else:
                error_msg = result.get("fields", [{}])[0].get("status", {}).get("message", "Unknown error")
                print(f"⚠️  {error_msg}")
                print(f"   Full result: {result}")
                failed_count += 1

        except httpx.HTTPStatusError as e:
            error_body = e.response.json() if e.response.content else {}

            # Check if it's a duplicate (field already exists)
            if error_body.get("fields", [{}])[0].get("code") == "DUPLICATE_DATA":
                print("⚠️  Already exists")
                created_count += 1  # Count as success since field is available
            else:
                error_msg = error_body.get("message", str(e))
                print(f"❌ {error_msg}")
                if error_body:
                    print(f"   Full response: {error_body}")
                failed_count += 1
        except Exception as e:
            print(f"❌ {e}")
            failed_count += 1

    print(f"\n{'='*60}")
    print(f"✅ Created: {created_count} fields")
    if failed_count > 0:
        print(f"⚠️  Failed: {failed_count} fields (may already exist)")
    print(f"{'='*60}")

    print(f"\n💡 Next steps:")
    print(f"   1. Check Zoho CRM → Settings → Customization → Modules → {module}")
    print(f"   2. Verify all Apollo fields are visible")
    print(f"   3. Test enrichment with: curl -X POST http://localhost:8000/enrich/lead ...")

    return 0


if __name__ == "__main__":
    sys.exit(main())
