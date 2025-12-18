from __future__ import annotations

import hmac
import hashlib
import time
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SignatureCheck:
    ok: bool
    reason: str = ""


def verify_calendly_signature(
    *,
    signing_key: str,
    header_value: Optional[str],
    raw_body: bytes,
    tolerance_seconds: int = 5 * 60,
) -> SignatureCheck:
    """
    Calendly webhook signature verification.

    Calendly's signature header is commonly formatted like: 't=timestamp,v1=hexsignature'.
    We compute HMAC-SHA256 over '{t}.{raw_body}' using the signing key and compare to v1.

    If signing_key is empty, verification is skipped by design (treated as OK).
    """
    if not signing_key:
        return SignatureCheck(ok=True, reason="signing_key_not_set")

    if not header_value:
        return SignatureCheck(ok=False, reason="missing_signature_header")

    parts = {}
    try:
        for kv in header_value.split(","):
            k, v = kv.strip().split("=", 1)
            parts[k] = v
        ts = int(parts.get("t", "0"))
        sig = parts.get("v1", "")
    except Exception:  # noqa: BLE001
        return SignatureCheck(ok=False, reason="invalid_signature_header_format")

    now = int(time.time())
    if ts <= 0 or abs(now - ts) > tolerance_seconds:
        return SignatureCheck(ok=False, reason="timestamp_out_of_tolerance")

    signed_payload = f"{ts}.".encode("utf-8") + raw_body
    digest = hmac.new(signing_key.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(digest, sig):
        return SignatureCheck(ok=False, reason="signature_mismatch")
    return SignatureCheck(ok=True)


def verify_shared_secret(
    *,
    expected: str,
    provided: Optional[str],
) -> SignatureCheck:
    if not expected:
        return SignatureCheck(ok=True, reason="shared_secret_not_set")
    if not provided:
        return SignatureCheck(ok=False, reason="missing_shared_secret")
    if not hmac.compare_digest(expected, provided):
        return SignatureCheck(ok=False, reason="shared_secret_mismatch")
    return SignatureCheck(ok=True)




