# Calendly Webhook Payload Structure

This document describes the complete structure of Calendly webhook payloads received by the GoVisually Sales Integrator service.

## Event Types

The service handles the following Calendly event types:
- `invitee.created` - When a new demo is booked
- `invitee.canceled` - When a demo is canceled (may include `rescheduled=true` for reschedules)

## Complete Payload Structure

### Top-Level Structure

```json
{
  "event": "invitee.created",
  "time": "2025-12-18T00:30:00.000000Z",
  "payload": {
    "invitee": { ... },
    "event": { ... },
    "event_type": { ... },
    "questions_and_answers": [ ... ],
    "tracking": { ... }  // Optional, may be in invitee.tracking
  }
}
```

### Invitee Object

```json
{
  "invitee": {
    "uuid": "inv-123",
    "uri": "https://api.calendly.com/scheduled_events/evt-123/invitees/inv-123",
    "name": "Isabelle Mercier",
    "email": "isabelle@leapzonestrategies.com",
    "text_reminder_number": "+1-555-123-4567",  // Phone number (optional)
    "timezone": "America/Los_Angeles",
    "event_guests": [],
    "event_guest_statuses": [],
    "created_at": "2025-12-17T10:00:00.000000Z",
    "updated_at": "2025-12-17T10:00:00.000000Z",
    "canceled": false,
    "cancellation": null,
    "payment": null,
    "tracking": {
      "utm_campaign": "summer2025",
      "utm_source": "google",
      "utm_medium": "cpc",
      "utm_content": "ad_variant_1",
      "utm_term": "proofing software",
      "salesforce_uuid": null
    },
    "rescheduled": false
  }
}
```

**Key Fields:**
- `name`: Full name of the person booking
- `email`: Email address (used as primary key for Zoho Lead matching)
- `text_reminder_number`: Phone number if provided (mapped to Zoho `Phone` field)
- `timezone`: Timezone of the invitee (used to infer location)
- `tracking`: UTM parameters and tracking data (can be used for Lead Source refinement)

### Event Object

```json
{
  "event": {
    "uuid": "evt-123",
    "uri": "https://api.calendly.com/scheduled_events/evt-123",
    "name": "GoVisually Demo",
    "start_time": "2025-12-16T22:30:00.000000Z",
    "end_time": "2025-12-16T23:00:00.000000Z",
    "timezone": "America/Los_Angeles",
    "created_at": "2025-12-15T10:00:00.000000Z",
    "updated_at": "2025-12-15T10:00:00.000000Z"
  }
}
```

**Key Fields:**
- `start_time`: ISO 8601 datetime in UTC (mapped to Zoho `Demo_Date` custom field)
- `timezone`: Event timezone (used for location inference and datetime formatting)
- `uri`: Event URI (stored in custom field if configured)

### Event Type Object

```json
{
  "event_type": {
    "uuid": "event-type-uuid-123",
    "kind": "One-on-One",
    "slug": "demo",
    "name": "GoVisually Demo",
    "duration": 30,
    "uri": "https://api.calendly.com/event_types/event-type-uuid-123"
  }
}
```

**Key Fields:**
- `uri`: Event type URI (used for filtering if `CALENDLY_EVENT_TYPE_URI` is configured)
- `name`: Event type name

### Questions and Answers

```json
{
  "questions_and_answers": [
    {
      "question": "What's your current process and biggest challenge with getting content reviewed and approved?",
      "answer": "To get clients to attentively review a final proof before approving...the check list will help for that for sure. Also, I find that clients don't respond to comment replies...like when we have questions for them or need more info."
    },
    {
      "question": "Are you using a project management or CRM tool that you'd ideally like an integration with?",
      "answer": "Trello\nAdobe Creative Cloud"
    },
    {
      "question": "What type of company are you?",
      "answer": "Branding/Design Agency"
    },
    {
      "question": "Can you share the size of your team?",
      "answer": "2 to 5 team members"
    },
    {
      "question": "How did they hear about us?",
      "answer": "Search engine (Google, Bing)"
    }
  ]
}
```

**Key Fields Extracted:**
- Company type → `company_type` → Zoho custom field
- Team size → `team_size` → Zoho `Team_members` custom field
- Tools in use → `tools_in_use` → Zoho `Tools_Currently_Used` custom field
- Pain points → `stated_pain_points` → Zoho `Pain_Points` custom field
- Demo objectives → `stated_demo_objectives` → Zoho `Demo_Objectives` custom field
- Referral source → `referred_by` → Zoho `Referred_by` field
- Industry (if mentioned) → `industry` → Zoho `Industry` field

## Data Extraction and Mapping

### Standard Zoho Fields

| Calendly Source | Zoho Field | Extraction Method |
|----------------|------------|-------------------|
| `invitee.email` | `Email` | Direct mapping |
| `invitee.name` | `First_Name`, `Last_Name` | Split by space |
| `invitee.text_reminder_number` | `Phone` | Direct mapping |
| `invitee.tracking.utm_source` | `Lead_Source` | Set to "Calendly" (can be enhanced with UTM) |
| `event.start_time` | `Demo_Date` (custom) | Formatted to Zoho datetime format |
| `event.timezone` | Location inference | Used to infer Country, State, City |
| Email domain | `Company`, `Website` | Derived from email domain |
| Q&A answers | Various custom fields | LLM extraction |

### LLM-Extracted Fields

The LLM extracts the following from Q&A answers and other data:

1. **Company Information:**
   - `company_name`: From email domain
   - `company_website`: Derived from email domain
   - `company_type`: From Q&A (e.g., "Branding/Design Agency")
   - `industry`: From Q&A or inferred from company type

2. **Location:**
   - `country`, `state_or_region`, `city`: Inferred from timezone

3. **Business Details:**
   - `team_size`: From Q&A
   - `tools_in_use`: From Q&A
   - `stated_pain_points`: From Q&A
   - `stated_demo_objectives`: From Q&A
   - `referred_by`: From Q&A "How did they hear about us?"

4. **Sales Intelligence:**
   - `demo_focus_recommendations`: Generated based on pain points
   - `recommended_discovery_questions`: Generated based on gaps
   - `sales_rep_cheat_sheet`: Summary of key facts
   - BANT signals: Budget, Authority, Need, Timing

## Example Complete Payload

See `tests/fixtures/calendly_invitee_created.json` for a minimal example.

For a complete real-world example, see the payload structure in `scripts/e2e_full_flow.py` (lines 55-110).

## Notes

- **Demo Date**: Always extracted from `event.start_time` and formatted to Zoho's datetime format (YYYY-MM-DDTHH:MM:SS+HHMM)
- **Lead Source**: Always set to "Calendly" for Calendly bookings. Can be enhanced with UTM source if available.
- **Referred By**: Extracted from Q&A question "How did they hear about us?" or similar
- **Industry**: Extracted from Q&A or inferred from company type
- **Phone**: Extracted from `invitee.text_reminder_number` or Q&A if mentioned
- **Website**: Derived from email domain (skipped for personal email domains like gmail.com)

## References

- [Calendly Webhook Documentation](https://developer.calendly.com/api-docs/adf83e8f05e54-webhook-examples)
- [Calendly API Reference](https://developer.calendly.com/api-docs/ZG9jOjM2MzE2MDM4-webhooks)



