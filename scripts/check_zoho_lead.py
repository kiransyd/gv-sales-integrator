#!/usr/bin/env python3
"""Check what's actually in a Zoho Lead and compare with what we sent"""
import json
import os
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

def get_zoho_lead(email: str) -> dict | None:
    """Fetch lead from Zoho by email"""
    dc = load_env_var("ZOHO_DC", "au")
    refresh_token = load_env_var("ZOHO_REFRESH_TOKEN", "")
    client_id = load_env_var("ZOHO_CLIENT_ID", "")
    client_secret = load_env_var("ZOHO_CLIENT_SECRET", "")
    module = load_env_var("ZOHO_LEADS_MODULE", "Leads")
    
    if not refresh_token:
        print("❌ ZOHO_REFRESH_TOKEN not set")
        return None
    
    # Get access token
    token_url = f"https://accounts.zoho.{dc}/oauth/v2/token"
    token_data = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
    }
    
    try:
        with httpx.Client(timeout=10.0) as client:
            token_resp = client.post(token_url, data=token_data)
            token_resp.raise_for_status()
            access_token = token_resp.json()["access_token"]
            
            # Search for lead
            api_url = f"https://www.zohoapis.{dc}/crm/v2/{module}/search"
            params = {"criteria": f"(Email:equals:{email})"}
            headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
            
            search_resp = client.get(api_url, params=params, headers=headers, timeout=10.0)
            
            if search_resp.status_code == 204:
                return None
            
            search_resp.raise_for_status()
            data = search_resp.json()
            
            if data.get("data") and len(data["data"]) > 0:
                return data["data"][0]
            
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    email = sys.argv[1] if len(sys.argv) > 1 else "test.buyer@example.com"
    
    print(f"🔍 Fetching Zoho Lead for: {email}\n")
    
    lead = get_zoho_lead(email)
    if not lead:
        print(f"❌ Lead not found")
        return 1
    
    print(f"✅ Lead found: {lead.get('id')}")
    print(f"   Name: {lead.get('Full_Name', 'N/A')}")
    print(f"   Email: {lead.get('Email', 'N/A')}")
    print(f"   Status: {lead.get('Lead_Status', 'N/A')}\n")
    
    # Check MEDDIC fields
    meddic_fields = {
        "MEDDIC_Process": "Metrics",
        "MEDDIC_Pain": "Decision Criteria",
        "Competition": "Decision Process",
        "Identified_Pain_Points": "Identified Pain",
        "Champion_and_Economic_Buyer": "Champion/Economic Buyer",
    }
    
    print("="*60)
    print("MEDDIC Fields in Zoho:")
    print("="*60)
    
    for field_api, field_label in meddic_fields.items():
        value = lead.get(field_api, "")
        if value:
            print(f"\n✅ {field_label} ({field_api}):")
            print(f"   {str(value)[:200]}{'...' if len(str(value)) > 200 else ''}")
        else:
            print(f"\n❌ {field_label} ({field_api}): (empty)")
    
    # Show all fields for debugging
    print("\n" + "="*60)
    print("All Custom Fields (for debugging):")
    print("="*60)
    for key, value in sorted(lead.items()):
        if key.startswith(("MEDDIC_", "Competition", "Identified_", "Champion_")) or key in ["Lead_Status", "Email", "Full_Name"]:
            if value:
                print(f"  {key}: {str(value)[:100]}{'...' if len(str(value)) > 100 else ''}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())


