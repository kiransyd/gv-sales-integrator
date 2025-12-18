from __future__ import annotations

from app.services.readai_service import select_best_external_attendee_email


def test_select_best_external_attendee_email_excludes_internal_domains(monkeypatch):
    # Override domains by patching the helper used internally
    import app.services.readai_service as svc

    monkeypatch.setattr(svc, "customer_domains_set", lambda: {"govisually.com"})

    attendees = [
        {"email": "rep@govisually.com", "name": "Rep"},
        {"email": "alice@example.com", "name": "Alice"},
    ]
    assert select_best_external_attendee_email(attendees) == "alice@example.com"


def test_select_best_external_attendee_email_empty_when_none():
    attendees = [{"email": ""}, {"name": "NoEmail"}]
    assert select_best_external_attendee_email(attendees) == ""



