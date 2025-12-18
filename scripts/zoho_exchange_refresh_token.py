#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _read_env_value(path: Path, key: str) -> str:
    if not path.exists():
        return ""
    m = re.search(rf"^{re.escape(key)}=(.*)$", path.read_text(), flags=re.M)
    return m.group(1).strip() if m else ""


def _write_env_value(path: Path, key: str, value: str) -> None:
    text = path.read_text() if path.exists() else ""
    if re.search(rf"^{re.escape(key)}=", text, flags=re.M):
        text = re.sub(rf"^{re.escape(key)}=.*$", f"{key}={value}", text, flags=re.M)
    else:
        if text and not text.endswith("\n"):
            text += "\n"
        text += f"{key}={value}\n"
    path.write_text(text)


def _accounts_domain(dc: str) -> str:
    m = {"us": "zoho.com", "au": "zoho.com.au", "eu": "zoho.eu", "in": "zoho.in"}
    if dc not in m:
        raise SystemExit(f"Unsupported ZOHO_DC={dc} (expected one of {sorted(m)})")
    return m[dc]


def _latest_self_client_json() -> Path:
    candidates = sorted(Path(".").glob("self_client*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise SystemExit("No self_client*.json found (expected Self Client output JSON in repo root).")
    return candidates[0]


def main() -> None:
    env_path = Path(".env")
    dc = _read_env_value(env_path, "ZOHO_DC") or "au"
    redirect_uri = _read_env_value(env_path, "ZOHO_REDIRECT_URI")
    if not redirect_uri:
        raise SystemExit(
            "Missing ZOHO_REDIRECT_URI in .env. Set it to the exact Authorized Redirect URI from Zoho API Console."
        )

    sc_path = _latest_self_client_json()
    sc = json.loads(sc_path.read_text())
    client_id = sc.get("client_id") or ""
    client_secret = sc.get("client_secret") or ""
    code = sc.get("code") or ""
    if not client_id or not client_secret or not code:
        raise SystemExit(f"{sc_path} missing one of: client_id, client_secret, code")

    token_url = f"https://accounts.{_accounts_domain(dc)}/oauth/v2/token"

    print(f"Exchanging Zoho Self Client grant token for refresh token (dc={dc})...")
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            },
        )

    try:
        body = resp.json()
    except Exception:  # noqa: BLE001
        body = {"raw": resp.text[:500]}

    if resp.status_code >= 400:
        # Do not print secrets.
        raise SystemExit(f"Token exchange failed: HTTP {resp.status_code} body={body}")

    refresh = body.get("refresh_token")
    if not refresh:
        raise SystemExit(f"Token exchange response missing refresh_token. body={ {k: ('***' if 'token' in k else v) for k,v in body.items()} }")

    # Keep env consistent with the client that generated the refresh token.
    _write_env_value(env_path, "ZOHO_CLIENT_ID", client_id)
    _write_env_value(env_path, "ZOHO_CLIENT_SECRET", client_secret)
    _write_env_value(env_path, "ZOHO_REFRESH_TOKEN", refresh)
    print("Saved ZOHO_REFRESH_TOKEN into .env (value not printed).")
    print("Also aligned ZOHO_CLIENT_ID/ZOHO_CLIENT_SECRET in .env with the Self Client used.")


if __name__ == "__main__":
    main()


