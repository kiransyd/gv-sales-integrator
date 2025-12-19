from __future__ import annotations

import json
from pathlib import Path

from app.services.calendly_service import build_zoho_lead_payload_for_calendly, parse_calendly_lead_info
from app.settings import get_settings


def test_calendly_mapping_sets_status_and_email():
    payload = json.loads(Path("tests/fixtures/calendly_invitee_created.json").read_text())
    info = parse_calendly_lead_info(payload)
    settings = get_settings()
    out = build_zoho_lead_payload_for_calendly(info=info, lead_status=settings.STATUS_DEMO_BOOKED, lead_intel_text="X")
    assert out["Email"] == "alice@example.com"
    assert out[settings.ZOHO_LEAD_STATUS_FIELD] == settings.STATUS_DEMO_BOOKED






