from __future__ import annotations

from app.services.readai_service import _extract_attendee_summaries


def test_extract_attendee_summaries_with_transcript(monkeypatch):
    """Test that attendee summaries include speaking stats and sample quotes"""
    import app.services.readai_service as svc

    monkeypatch.setattr(svc, "customer_domains_set", lambda: {"govisually.com"})

    attendees = [
        {"email": "john@acme.com", "name": "John Smith"},
        {"email": "mary@acme.com", "name": "Mary Johnson"},
        {"email": "rep@govisually.com", "name": "Sales Rep"},
    ]

    owner = {"email": "john@acme.com", "name": "John Smith"}

    transcript_raw = {
        "speaker_blocks": [
            {
                "speaker": {"name": "John Smith"},
                "words": "We need a better way to review our video content with clients.",
            },
            {
                "speaker": {"name": "Sales Rep"},
                "words": "Great! Let me show you how our platform handles video reviews.",
            },
            {
                "speaker": {"name": "Mary Johnson"},
                "words": "This looks really useful for our design team.",
            },
            {
                "speaker": {"name": "John Smith"},
                "words": "How does the pricing work for teams of our size?",
            },
        ]
    }

    result = _extract_attendee_summaries(attendees, transcript_raw, owner)

    # Should include all attendees
    assert "John Smith" in result
    assert "Mary Johnson" in result
    assert "Sales Rep" in result

    # Should mark external vs internal
    assert "External" in result
    assert "Internal" in result

    # Should mark meeting owner
    assert "Meeting Owner" in result

    # Should include word count
    assert "Spoke" in result
    assert "words" in result

    # Should include sample quote
    assert "Sample:" in result
    assert "better way to review" in result


def test_extract_attendee_summaries_no_transcript(monkeypatch):
    """Test that attendee summaries work without transcript data"""
    import app.services.readai_service as svc

    monkeypatch.setattr(svc, "customer_domains_set", lambda: {"govisually.com"})

    attendees = [
        {"email": "john@acme.com", "name": "John Smith"},
        {"email": "rep@govisually.com", "name": "Sales Rep"},
    ]

    owner = {"email": "john@acme.com"}

    # No transcript
    result = _extract_attendee_summaries(attendees, None, owner)

    # Should still list attendees
    assert "John Smith" in result
    assert "Sales Rep" in result
    assert "External" in result
    assert "Internal" in result

    # Should NOT have speaking stats
    assert "Spoke" not in result
    assert "Sample:" not in result


def test_extract_attendee_summaries_truncates_long_quotes():
    """Test that long quotes are truncated"""
    attendees = [
        {"email": "john@acme.com", "name": "John Smith"},
    ]

    owner = {}

    # Very long statement
    long_statement = "A" * 200

    transcript_raw = {
        "speaker_blocks": [
            {
                "speaker": {"name": "John Smith"},
                "words": long_statement,
            },
        ]
    }

    result = _extract_attendee_summaries(attendees, transcript_raw, owner)

    # Should be truncated with ellipsis
    assert "..." in result
    # Should not include the full 200 characters
    assert len(result) < 400  # Account for formatting


def test_extract_attendee_summaries_filters_calendar_emails(monkeypatch):
    """Test that Google Calendar emails are handled correctly"""
    import app.services.readai_service as svc

    monkeypatch.setattr(svc, "customer_domains_set", lambda: {"govisually.com"})

    attendees = [
        {"email": "john@acme.com", "name": "John Smith"},
        {"email": "govisually.com_ta1cucmonc0ge4kua4pf4n9n3g@group.calendar.google.com"},
        {"email": "rep@govisually.com", "name": "Sales Rep"},
    ]

    owner = {}

    result = _extract_attendee_summaries(attendees, None, owner)

    # Should include real people
    assert "John Smith" in result
    assert "Sales Rep" in result

    # Google Calendar email should still be listed but marked appropriately
    # (It's in the attendees list, so we show it, but it's marked as External)
    assert "group.calendar.google.com" in result
