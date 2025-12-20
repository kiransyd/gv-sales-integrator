from __future__ import annotations

from app.services.readai_service import get_all_external_attendee_emails, select_best_external_attendee_email


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


def test_get_all_external_attendee_emails_prioritizes_owner(monkeypatch):
    """Test that the owner email is returned first if external"""
    import app.services.readai_service as svc

    monkeypatch.setattr(svc, "customer_domains_set", lambda: {"govisually.com"})

    attendees = [
        {"email": "mary@acme.com", "name": "Mary"},
        {"email": "john@acme.com", "name": "John"},
        {"email": "steve@acme.com", "name": "Steve"},
        {"email": "rep@govisually.com", "name": "Rep"},
    ]
    owner = {"email": "john@acme.com", "name": "John"}

    result = get_all_external_attendee_emails(attendees, owner)

    # john@acme.com should be first (owner), followed by mary and steve
    assert result == ["john@acme.com", "mary@acme.com", "steve@acme.com"]


def test_get_all_external_attendee_emails_owner_internal(monkeypatch):
    """Test that internal owner is excluded but other external attendees are returned"""
    import app.services.readai_service as svc

    monkeypatch.setattr(svc, "customer_domains_set", lambda: {"govisually.com"})

    attendees = [
        {"email": "mary@acme.com", "name": "Mary"},
        {"email": "john@acme.com", "name": "John"},
        {"email": "rep@govisually.com", "name": "Rep"},
    ]
    owner = {"email": "rep@govisually.com", "name": "Rep"}  # Internal owner

    result = get_all_external_attendee_emails(attendees, owner)

    # Owner is internal, so should get external attendees in order
    assert result == ["mary@acme.com", "john@acme.com"]


def test_get_all_external_attendee_emails_filters_google_calendar(monkeypatch):
    """Test that Google Calendar resource/group emails are filtered out"""
    import app.services.readai_service as svc

    monkeypatch.setattr(svc, "customer_domains_set", lambda: {"govisually.com"})

    attendees = [
        {"email": "john@acme.com", "name": "John"},
        {"email": "govisually.com_ta1cucmonc0ge4kua4pf4n9n3g@group.calendar.google.com"},
        {"email": "mary@acme.com", "name": "Mary"},
        {"email": "resource_123@resource.calendar.google.com"},
    ]
    owner = {}

    result = get_all_external_attendee_emails(attendees, owner)

    # Google Calendar emails should be filtered out
    assert result == ["john@acme.com", "mary@acme.com"]


def test_get_all_external_attendee_emails_no_duplicates(monkeypatch):
    """Test that owner email is not duplicated in the list"""
    import app.services.readai_service as svc

    monkeypatch.setattr(svc, "customer_domains_set", lambda: {"govisually.com"})

    attendees = [
        {"email": "john@acme.com", "name": "John"},  # Owner is also in attendees
        {"email": "mary@acme.com", "name": "Mary"},
    ]
    owner = {"email": "john@acme.com", "name": "John"}

    result = get_all_external_attendee_emails(attendees, owner)

    # john should appear only once (as owner, first position)
    assert result == ["john@acme.com", "mary@acme.com"]


def test_get_all_external_attendee_emails_empty_when_all_internal(monkeypatch):
    """Test that empty list is returned when all attendees are internal"""
    import app.services.readai_service as svc

    monkeypatch.setattr(svc, "customer_domains_set", lambda: {"govisually.com"})

    attendees = [
        {"email": "rep1@govisually.com", "name": "Rep1"},
        {"email": "rep2@govisually.com", "name": "Rep2"},
    ]
    owner = {"email": "rep1@govisually.com", "name": "Rep1"}

    result = get_all_external_attendee_emails(attendees, owner)

    assert result == []







