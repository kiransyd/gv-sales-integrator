from __future__ import annotations

from typing import Any, Optional


def _get(d: dict[str, Any], *keys: str) -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def extract_calendly_event_type(payload: dict[str, Any]) -> str:
    # Calendly commonly includes top-level 'event' as the event name.
    ev = payload.get("event")
    if isinstance(ev, str) and ev:
        return ev
    # Fallbacks (defensive)
    ev2 = _get(payload, "event", "type")
    return ev2 if isinstance(ev2, str) else ""


def derive_calendly_event_type_for_processing(payload: dict[str, Any], raw_event_type: str) -> str:
    """
    Calendly reschedules trigger BOTH invitee.created and invitee.canceled.
    The invitee.canceled payload includes payload.rescheduled == true.
    See: https://developer.calendly.com/see-how-webhook-payloads-change-when-invitees-reschedule-events
    """
    if raw_event_type == "invitee.canceled":
        rescheduled = _get(payload, "payload", "rescheduled")
        if rescheduled is True:
            return "invitee.rescheduled"
    return raw_event_type


def extract_calendly_external_id(payload: dict[str, Any]) -> str:
    # Calendly webhook structure can vary:
    # 1. New format: payload.payload.uri (flattened, invitee data directly in payload.payload)
    # 2. Old format: payload.payload.invitee.uri (nested invitee object)
    
    # Try new flattened format first (uri directly in payload.payload)
    uri = _get(payload, "payload", "uri")
    if isinstance(uri, str) and uri:
        return uri
    
    # Try nested format (payload.payload.invitee.uri)
    invitee_uri = _get(payload, "payload", "invitee", "uri")
    if isinstance(invitee_uri, str) and invitee_uri:
        return invitee_uri
    
    # Try UUIDs (new format might have uuid directly in payload.payload, or nested)
    invitee_uuid = _get(payload, "payload", "uuid")
    if isinstance(invitee_uuid, str) and invitee_uuid:
        return invitee_uuid
    
    invitee_uuid_nested = _get(payload, "payload", "invitee", "uuid")
    if isinstance(invitee_uuid_nested, str) and invitee_uuid_nested:
        return invitee_uuid_nested
    
    # Try event UUID
    event_uuid = _get(payload, "payload", "event", "uuid")
    if isinstance(event_uuid, str) and event_uuid:
        return event_uuid
    
    # Try scheduled_event (new format)
    scheduled_event = _get(payload, "payload", "scheduled_event")
    if isinstance(scheduled_event, dict):
        event_uri = scheduled_event.get("uri")
        if isinstance(event_uri, str) and event_uri:
            return event_uri
    
    return ""


def extract_calendly_event_type_uri(payload: dict[str, Any]) -> str:
    # Event type is often a URI in payload: payload.event_type or payload.event_type.uri
    uri = _get(payload, "payload", "event_type")
    if isinstance(uri, str) and uri:
        return uri
    uri2 = _get(payload, "payload", "event_type", "uri")
    if isinstance(uri2, str) and uri2:
        return uri2
    uri3 = _get(payload, "payload", "event", "event_type")
    if isinstance(uri3, str) and uri3:
        return uri3
    uri4 = _get(payload, "payload", "event", "event_type", "uri")
    if isinstance(uri4, str) and uri4:
        return uri4
    return ""


def extract_readai_meeting_id(payload: dict[str, Any]) -> str:
    # Read.ai docs: session_id (trigger meeting_end)
    mid = (
        payload.get("session_id")
        or payload.get("sessionId")
        or payload.get("meeting_id")
        or payload.get("id")
        or payload.get("meetingId")
    )
    return mid if isinstance(mid, str) else ""


def extract_readai_event_type(payload: dict[str, Any]) -> str:
    # Read.ai schemas vary; standardize to a single type for idempotency.
    t = payload.get("trigger") or payload.get("event_type") or payload.get("type")
    if isinstance(t, str) and t:
        return t
    return "meeting.completed"


def best_effort_extract_email(payload: dict[str, Any]) -> Optional[str]:
    # This is only used for Slack alert context and debug; real matching is in worker.
    invitee_email = _get(payload, "payload", "invitee", "email")
    if isinstance(invitee_email, str) and invitee_email:
        return invitee_email
    # Read.ai: attendees list
    attendees = payload.get("attendees") or payload.get("participants")
    if isinstance(attendees, list):
        for a in attendees:
            if isinstance(a, dict):
                em = a.get("email")
                if isinstance(em, str) and em:
                    return em
    return None



