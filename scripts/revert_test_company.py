#!/usr/bin/env python3
"""Revert test changes to Bachan's company."""

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.settings import get_settings


def revert_company():
    """Revert gv_checklists back to original value."""
    settings = get_settings()

    headers = {
        "Authorization": f"Bearer {settings.INTERCOM_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Intercom-Version": "2.11"
    }

    company_id = "66311f0fa8475847eb9a281a"

    payload = {
        "id": company_id,
        "custom_attributes": {
            "gv_checklists": 1  # Original value
        }
    }

    print(f"🔄 Reverting test changes...")
    print(f"   Company: Bachan's")
    print(f"   Setting gv_checklists back to: 1")

    try:
        response = httpx.put(
            f"https://api.intercom.io/companies/{company_id}",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        print("✅ Company reverted to original state")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    revert_company()
