#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

import httpx


DC_MAP = {
    "us": {"accounts": "zoho.com", "api": "zohoapis.com"},
    "au": {"accounts": "zoho.com.au", "api": "zohoapis.com.au"},
    "eu": {"accounts": "zoho.eu", "api": "zohoapis.eu"},
    "in": {"accounts": "zoho.in", "api": "zohoapis.in"},
}


def _read_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _get_access_token(*, dc: str, client_id: str, client_secret: str, refresh_token: str) -> str:
    url = f"https://accounts.{DC_MAP[dc]['accounts']}/oauth/v2/token"
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
        resp.raise_for_status()
        body = resp.json()
    token = body.get("access_token")
    if not token:
        raise SystemExit(f"Token refresh did not return access_token. keys={list(body.keys())}")
    return token


def _search_lead(*, dc: str, token: str, module: str, email: str) -> dict | None:
    base = f"https://www.{DC_MAP[dc]['api']}/crm/v2"
    criteria = quote(f"(Email:equals:{email})", safe="():,=")
    url = f"{base}/{module}/search?criteria={criteria}"
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(url, headers={"Authorization": f"Zoho-oauthtoken {token}"})
        if resp.status_code == 204 or not resp.content:
            return None
        resp.raise_for_status()
        body = resp.json()
    data = body.get("data") or []
    if isinstance(data, list) and data:
        return data[0]
    return None


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--email", required=True)
    args = ap.parse_args()

    env = _read_env(Path(".env"))
    dc = (env.get("ZOHO_DC") or "au").lower()
    if dc not in DC_MAP:
        raise SystemExit(f"Unsupported ZOHO_DC={dc}")

    module = env.get("ZOHO_LEADS_MODULE") or "Leads"
    token = _get_access_token(
        dc=dc,
        client_id=env.get("ZOHO_CLIENT_ID") or "",
        client_secret=env.get("ZOHO_CLIENT_SECRET") or "",
        refresh_token=env.get("ZOHO_REFRESH_TOKEN") or "",
    )

    lead = _search_lead(dc=dc, token=token, module=module, email=args.email)
    if not lead:
        print("Lead not found.")
        return

    # Print high-signal fields for our integration
    keys = [
        "id",
        "Email",
        "First_Name",
        "Last_Name",
        "Lead_Status",
        "Demo_Date",
        "Demo_Notes",
        "Sales_Rep_Cheat_Sheet",
        "MEDDIC_Process",
        "MEDDIC_Pain",
        "Competition",
        "Identified_Pain_Points",
        "Champion_and_Economic_Buyer",
    ]
    out = {k: lead.get(k) for k in keys if k in lead}
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()




