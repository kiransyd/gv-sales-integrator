#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from dataclasses import dataclass
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


@dataclass(frozen=True)
class ZohoConfig:
    dc: str
    accounts_domain: str
    api_domain: str
    client_id: str
    client_secret: str
    refresh_token: str


def _cfg(env: dict[str, str]) -> ZohoConfig:
    dc = (env.get("ZOHO_DC") or "au").lower()
    if dc not in DC_MAP:
        raise SystemExit(f"Unsupported ZOHO_DC={dc}")
    client_id = env.get("ZOHO_CLIENT_ID") or ""
    client_secret = env.get("ZOHO_CLIENT_SECRET") or ""
    refresh_token = env.get("ZOHO_REFRESH_TOKEN") or ""
    if not (client_id and client_secret and refresh_token):
        raise SystemExit("Missing one of ZOHO_CLIENT_ID/ZOHO_CLIENT_SECRET/ZOHO_REFRESH_TOKEN in .env")
    return ZohoConfig(
        dc=dc,
        accounts_domain=DC_MAP[dc]["accounts"],
        api_domain=DC_MAP[dc]["api"],
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token,
    )


def _get_access_token(cfg: ZohoConfig) -> str:
    url = f"https://accounts.{cfg.accounts_domain}/oauth/v2/token"
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": cfg.refresh_token,
                "client_id": cfg.client_id,
                "client_secret": cfg.client_secret,
            },
        )
        resp.raise_for_status()
        body = resp.json()
    token = body.get("access_token")
    if not token:
        raise SystemExit(f"Refresh flow did not return access_token. keys={list(body.keys())}")
    return token


def _list_fields(cfg: ZohoConfig, module: str) -> list[dict]:
    token = _get_access_token(cfg)
    base = f"https://www.{cfg.api_domain}/crm/v2"
    url = f"{base}/settings/fields?module={quote(module)}"
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(url, headers={"Authorization": f"Zoho-oauthtoken {token}"})
        resp.raise_for_status()
        body = resp.json()
    data = body.get("fields") or body.get("data") or []
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    return []


def main() -> None:
    env = _read_env(Path(".env"))
    module = env.get("ZOHO_LEADS_MODULE") or "Leads"
    cfg = _cfg(env)
    fields = _list_fields(cfg, module)

    # Print a compact table first
    print(f"Module: {module}")
    print("custom\tapi_name\tdata_type\tfield_label")
    for f in fields:
        api_name = f.get("api_name", "")
        label = f.get("field_label", "")
        data_type = f.get("data_type", "")
        is_custom = f.get("custom_field", False)
        if not api_name:
            continue
        print(f"{bool(is_custom)}\t{api_name}\t{data_type}\t{label}")

    # Then print full JSON at the end (useful for copy/paste + searching)
    print("\n--- JSON ---")
    print(json.dumps(fields, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()


