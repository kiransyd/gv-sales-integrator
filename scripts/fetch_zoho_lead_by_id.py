#!/usr/bin/env python3
"""
Fetch a Zoho Lead by ID and display its fields.
"""
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

import httpx


def load_env_var(key: str, default: str = "") -> str:
    """Load environment variable from .env file or environment"""
    if key in os.environ:
        return os.environ[key]
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        content = env_file.read_text()
        match = re.search(rf"^{re.escape(key)}=(.+)$", content, flags=re.M)
        if match:
            return match.group(1).strip()
    return default


def get_zoho_access_token() -> str:
    """Get Zoho access token using refresh token"""
    dc = load_env_var("ZOHO_DC", "au").lower()
    client_id = load_env_var("ZOHO_CLIENT_ID", "")
    client_secret = load_env_var("ZOHO_CLIENT_SECRET", "")
    refresh_token = load_env_var("ZOHO_REFRESH_TOKEN", "")
    
    if not all([client_id, client_secret, refresh_token]):
        raise ValueError("Missing Zoho credentials in .env")
    
    dc_map = {
        "au": "zohoapis.com.au",
        "com": "zohoapis.com",
        "eu": "zohoapis.eu",
        "in": "zohoapis.in",
    }
    
    api_base = f"https://accounts.{dc_map.get(dc, dc_map['com'])}"
    url = f"{api_base}/oauth/v2/token"
    
    params = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
    }
    
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, params=params)
        resp.raise_for_status()
        body = resp.json()
        return body.get("access_token", "")


def fetch_lead_by_id(lead_id: str) -> dict | None:
    """Fetch a Zoho Lead by ID"""
    dc = load_env_var("ZOHO_DC", "au").lower()
    module = load_env_var("ZOHO_LEADS_MODULE", "Leads")
    
    dc_map = {
        "au": "zohoapis.com.au",
        "com": "zohoapis.com",
        "eu": "zohoapis.eu",
        "in": "zohoapis.in",
    }
    
    api_base = f"https://www.{dc_map.get(dc, dc_map['com'])}/crm/v2"
    url = f"{api_base}/{module}/{lead_id}"
    
    token = get_zoho_access_token()
    headers = {
        "Authorization": f"Zoho-oauthtoken {token}",
        "Content-Type": "application/json",
    }
    
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(url, headers=headers)
        if resp.status_code == 204:
            return None
        resp.raise_for_status()
        body = resp.json()
        data = body.get("data", [])
        if isinstance(data, list) and data:
            return data[0]
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/fetch_zoho_lead_by_id.py <lead_id>")
        print("Example: python3 scripts/fetch_zoho_lead_by_id.py 103229000000469034")
        sys.exit(1)
    
    lead_id = sys.argv[1]
    print(f"🔍 Fetching Zoho Lead ID: {lead_id}\n")
    
    try:
        lead = fetch_lead_by_id(lead_id)
        if not lead:
            print("❌ Lead not found")
            sys.exit(1)
        
        print("✅ Lead found!\n")
        print("=" * 70)
        print("LEAD DETAILS")
        print("=" * 70)
        
        # Display key fields
        key_fields = [
            "id",
            "Email",
            "First_Name",
            "Last_Name",
            "Company",
            "Website",
            "Phone",
            "Lead_Status",
            "Lead_Source",
            "Industry",
            "Referred_by",
            "Country",
            "State",
            "City",
            "Demo_Date",
            "Pain_Points",
            "Team_members",
            "Tools_Currently_Used",
            "Demo_Objectives",
            "Demo_Focus_Recommendation",
            "Discovery_Questions",
            "Sales_Rep_Cheat_Sheet",
            "Demo_Notes",
        ]
        
        for field in key_fields:
            value = lead.get(field)
            if value:
                if isinstance(value, str) and len(value) > 100:
                    print(f"{field}: {value[:100]}...")
                else:
                    print(f"{field}: {value}")
        
        print("\n" + "=" * 70)
        print("FULL JSON RESPONSE")
        print("=" * 70)
        print(json.dumps(lead, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


