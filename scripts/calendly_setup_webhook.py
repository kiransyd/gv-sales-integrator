#!/usr/bin/env python3
from __future__ import annotations

import json
import secrets
import sys
from pathlib import Path
from typing import Any, Optional

import httpx


API_BASE = "https://api.calendly.com"


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


def _write_env_value(path: Path, key: str, value: str) -> None:
    text = path.read_text() if path.exists() else ""
    lines = text.splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            found = True
            break
    if not found:
        if lines and lines[-1].strip() != "":
            lines.append("")
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n")


def _http_json(
    method: str,
    url: str,
    token: str,
    payload: Optional[dict[str, Any]] = None,
    params: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Uses httpx with explicit headers. Calendly's edge/CDN may block some default user agents.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "govisually-integrations/1.0 (+https://govisually.com)",
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.request(method, url, headers=headers, json=payload, params=params)
            resp.raise_for_status()
            if not resp.content:
                return {}
            return resp.json()
    except httpx.HTTPStatusError as e:
        # Print body without leaking token.
        body = e.response.text[:2000]
        raise SystemExit(f"Calendly API error {e.response.status_code} for {url}: {body}") from e


def _deep_get(d: dict[str, Any], *paths: tuple[str, ...]) -> str:
    for path in paths:
        cur: Any = d
        ok = True
        for k in path:
            if not isinstance(cur, dict) or k not in cur:
                ok = False
                break
            cur = cur[k]
        if ok and isinstance(cur, str) and cur:
            return cur
    return ""


def get_me(token: str) -> dict[str, Any]:
    return _http_json("GET", f"{API_BASE}/users/me", token)


def list_event_types(token: str, user_uri: str) -> list[dict[str, Any]]:
    # Calendly supports listing event types by user query param.
    body = _http_json(
        "GET",
        f"{API_BASE}/event_types",
        token,
        params={"user": user_uri, "active": "true", "count": 100},
    )
    col = body.get("collection") or body.get("data") or []
    if isinstance(col, list):
        return [x for x in col if isinstance(x, dict)]
    return []


def create_webhook_subscription(
    *,
    token: str,
    url: str,
    organization_uri: str,
    scope: str,
    user_uri: str = "",
    signing_key: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "url": url,
        # Calendly-supported webhook events (reschedules come as invitee.created + invitee.canceled with rescheduled=true)
        "events": ["invitee.created", "invitee.canceled"],
        "organization": organization_uri,
        "scope": scope,
    }
    if scope == "user":
        payload["user"] = user_uri
    if signing_key:
        payload["signing_key"] = signing_key
    return _http_json("POST", f"{API_BASE}/webhook_subscriptions", token, payload)


def prompt(msg: str, default: str = "") -> str:
    if default:
        v = input(f"{msg} [{default}]: ").strip()
        return v or default
    return input(f"{msg}: ").strip()


def main() -> None:
    env_path = Path(".env")
    env = _read_env(env_path)

    token = env.get("CALENDLY_API_TOKEN", "").strip()
    if not token:
        raise SystemExit("Missing CALENDLY_API_TOKEN in .env")

    base_url = env.get("BASE_URL", "").strip() or "http://localhost:8000"
    print(f"Detected BASE_URL={base_url}")
    if not base_url.startswith("https://"):
        print("ERROR: Calendly requires a publicly reachable HTTPS webhook URL.")
        print("Set BASE_URL to your ngrok/Render HTTPS URL and rerun this script.")
        return

    webhook_url = base_url.rstrip("/") + "/webhooks/calendly"

    print("\nFetching your Calendly user + org…")
    me = get_me(token)
    user_uri = _deep_get(me, ("resource", "uri"), ("uri",), ("resource", "user", "uri"))
    org_uri = _deep_get(me, ("resource", "current_organization"), ("resource", "organization"), ("organization",))
    if not user_uri or not org_uri:
        print("Could not auto-detect user/org URIs from /users/me response.")
        print(json.dumps(me, indent=2)[:2000])
        raise SystemExit(1)

    print(f"User URI: {user_uri}")
    print(f"Org URI:  {org_uri}")

    print("\nListing your active Event Types…")
    ets = list_event_types(token, user_uri)
    if not ets:
        print("No event types found. Are you using the right Calendly account/token?")
    else:
        for i, et in enumerate(ets):
            name = et.get("name") or ""
            uri = et.get("uri") or ""
            print(f"{i:>2}) {name}  [{uri}]")

    print("\nQuestion 1: Which event type is your *Demo booking*?")
    print("This sets CALENDLY_EVENT_TYPE_URI so our service ignores other Calendly bookings.")
    choice = prompt("Enter number (or leave blank to skip)", default="")
    demo_event_type_uri = ""
    if choice:
        try:
            idx = int(choice)
            demo_event_type_uri = str(ets[idx].get("uri") or "")
        except Exception:
            raise SystemExit("Invalid selection.")

    print("\nQuestion 2: Webhook scope?")
    print("- organization: receive events for everyone in your org (recommended if multiple reps use Calendly)")
    print("- user: receive only your events")
    scope = prompt("Enter scope", default="organization").lower()
    if scope not in ("organization", "user"):
        raise SystemExit("Scope must be 'organization' or 'user'")

    print("\nQuestion 3: Enable signature verification?")
    print("Recommended: yes. We'll generate a signing key and set CALENDLY_SIGNING_KEY.")
    sig_yes = prompt("Enable signing key? (y/n)", default="y").lower().startswith("y")
    signing_key = secrets.token_urlsafe(32) if sig_yes else ""

    print("\nCreating webhook subscription…")
    resp = create_webhook_subscription(
        token=token,
        url=webhook_url,
        organization_uri=org_uri,
        scope=scope,
        user_uri=user_uri,
        signing_key=signing_key,
    )
    # Calendly responses often wrap with {resource: {...}}; print safely.
    resource = resp.get("resource") if isinstance(resp, dict) else None
    sub_uri = ""
    if isinstance(resource, dict):
        sub_uri = str(resource.get("uri") or "")
    print("Created webhook subscription.")
    if sub_uri:
        print(f"Subscription URI: {sub_uri}")
    else:
        print(json.dumps(resp, indent=2)[:2000])

    # Offer to write env values
    print("\nUpdate your .env now?")
    if prompt("Write CALENDLY_EVENT_TYPE_URI + CALENDLY_SIGNING_KEY to .env? (y/n)", default="y").lower().startswith("y"):
        if demo_event_type_uri:
            _write_env_value(env_path, "CALENDLY_EVENT_TYPE_URI", demo_event_type_uri)
            print("Wrote CALENDLY_EVENT_TYPE_URI.")
        if signing_key:
            _write_env_value(env_path, "CALENDLY_SIGNING_KEY", signing_key)
            print("Wrote CALENDLY_SIGNING_KEY.")

    print("\nNext steps:")
    print(f"- Ensure your service is reachable publicly (ngrok/Render) and BASE_URL is set accordingly.")
    print(f"- Calendly will POST to: {webhook_url}")
    print("- Restart docker-compose so API picks up any .env changes.")
    print("- Book/cancel/reschedule a demo and watch: docker-compose logs -f worker")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)


