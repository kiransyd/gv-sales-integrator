#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

import httpx


DC_MAP = {
    "us": "zoho.com",
    "au": "zoho.com.au",
    "eu": "zoho.eu",
    "in": "zoho.in",
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


def main() -> None:
    env = _read_env(Path(".env"))
    dc = (env.get("ZOHO_DC") or "au").lower()
    if dc not in DC_MAP:
        raise SystemExit(f"Unsupported ZOHO_DC={dc}")

    client_id = env.get("ZOHO_CLIENT_ID") or ""
    client_secret = env.get("ZOHO_CLIENT_SECRET") or ""
    refresh_token = env.get("ZOHO_REFRESH_TOKEN") or ""
    if not (client_id and client_secret and refresh_token):
        raise SystemExit("Missing ZOHO_CLIENT_ID/ZOHO_CLIENT_SECRET/ZOHO_REFRESH_TOKEN in .env")

    url = f"https://accounts.{DC_MAP[dc]}/oauth/v2/token"
    print(f"POST {url} (grant_type=refresh_token) dc={dc}")

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

    # Print response without leaking token values
    try:
        body = resp.json()
    except Exception:  # noqa: BLE001
        body = {"raw": resp.text[:1000]}

    redacted = {}
    for k, v in (body.items() if isinstance(body, dict) else []):
        if "token" in str(k).lower():
            redacted[k] = "***"
        else:
            redacted[k] = v

    print(f"status={resp.status_code}")
    print(redacted if redacted else body)


if __name__ == "__main__":
    main()



