from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.settings import get_settings

logger = logging.getLogger(__name__)


def send_slack_alert(
    *,
    text: str,
    blocks: Optional[list[dict[str, Any]]] = None,
) -> None:
    settings = get_settings()
    if not settings.SLACK_WEBHOOK_URL:
        logger.warning("Slack webhook not configured; skipping alert: %s", text)
        return

    payload: dict[str, Any] = {"text": text}
    if blocks:
        payload["blocks"] = blocks

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(settings.SLACK_WEBHOOK_URL, json=payload)
            resp.raise_for_status()
    except Exception as e:  # noqa: BLE001
        # Never crash the job just because Slack failed.
        logger.exception("Failed to send Slack alert: %s", e)



