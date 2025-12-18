# GoVisually Sales Integrator - Architecture Reference

## SYSTEM PURPOSE
Sales automation pipeline that receives webhooks from Calendly (demo bookings) and Read.ai (meeting transcripts), enriches lead data using LLM (Gemini), and updates Zoho CRM Leads with structured sales intelligence.

## CORE DATA FLOW

```
Calendly/Read.ai → FastAPI Webhook → Redis (event store) → RQ Job Queue → Worker → LLM Enrichment → Zoho CRM
                                          ↓
                                    Idempotency Guard
                                          ↓
                                    Slack (on failure)
```

### Flow Details
1. **Webhook Receipt** → Validate signature/secret → Store raw payload in Redis → Enqueue RQ job
2. **Worker Processing** → Load event → Check idempotency → Call LLM for enrichment → Upsert Zoho Lead → Create Note → Mark processed
3. **Error Handling** → Transient errors retry with backoff → Terminal failures alert Slack

---

## ARCHITECTURE COMPONENTS

### 1. API Layer (`app/api/`)
**Purpose:** HTTP endpoints for webhook ingestion

- `routes_webhooks_calendly.py` - Calendly webhook handler
  - Events: `invitee.created`, `invitee.canceled`, `invitee.rescheduled`
  - Security: HMAC signature verification via `CALENDLY_SIGNING_KEY`
  - Idempotency key: `calendly:{event_type}:{external_id}`

- `routes_webhooks_readai.py` - Read.ai webhook handler
  - Events: `meeting_end` (meeting_completed)
  - Security: Shared secret via `X-ReadAI-Secret` header
  - Idempotency key: `readai:meeting_completed:{meeting_id}`

- `routes_health.py` - Health check endpoint (`/healthz`)
- `routes_debug.py` - Debug endpoints (dev only, requires `ALLOW_DEBUG_ENDPOINTS=true`)

**Key Pattern:** All webhooks follow: validate → store → acquire idempotency → enqueue → return 200

### 2. Job Layer (`app/jobs/`)
**Purpose:** Background processing of webhook events

- `calendly_jobs.py` - Calendly event processors
  - `process_calendly_invitee_created` → Extract Q&A → LLM enrichment → Create/Update Lead → Set status to "Demo Booked"
  - `process_calendly_invitee_canceled` → Update Lead → Set status to "Demo Canceled"
  - `process_calendly_invitee_rescheduled` → Update demo datetime → Set status to "Demo Booked"

- `readai_jobs.py` - Read.ai event processors
  - `process_readai_meeting_completed` → Extract transcript → LLM MEDDIC analysis → Find/Create Lead → Update with MEDDIC data → Set status to "Demo Complete"
  - Smart attendee selection: Prioritizes external (non-GoVisually) attendees
  - Duration filter: Skips meetings < `READAI_MIN_DURATION_MINUTES`

- `retry.py` - Job execution wrapper
  - `run_event_job()` wrapper provides: attempts tracking, status transitions, idempotency guard, Slack alerting
  - Classifies errors as Transient (retry) or Permanent (fail immediately)
  - Terminal failures (retries exhausted or permanent) → Slack alert

### 3. Services Layer (`app/services/`)
**Purpose:** Business logic and external integrations

- `llm_service.py` - Gemini LLM integration
  - `calendly_lead_intel()` - Extracts 25+ lead fields from Calendly Q&A
  - `readai_meddic()` - Extracts MEDDIC framework from meeting transcript
  - 2-attempt validation: Generate JSON → Validate → Repair if needed → Validate again
  - Handles transcript truncation for long meetings (smart sampling)

- `zoho_service.py` - Zoho CRM integration
  - OAuth refresh token flow (cached in Redis + in-memory)
  - `find_lead_by_email()` - Search for existing lead
  - `upsert_lead_by_email()` - Create or update lead
  - `create_note()` - Attach notes to leads
  - `create_task()` - Optional follow-up task creation
  - Multi-datacenter support: US, AU, EU, IN

- `calendly_service.py` - Calendly data transformation
  - `parse_calendly_lead_info()` - Extracts invitee email, name, Q&A, demo datetime
  - `build_zoho_lead_payload_for_calendly()` - Maps LLM intel to Zoho fields

- `readai_service.py` - Read.ai data transformation
  - `extract_readai_fields()` - Extracts meeting metadata, transcript, summary
  - `select_best_external_attendee_email()` - Finds customer attendee (not @govisually.com/@clockworkstudio.com)
  - `build_zoho_lead_payload_for_meddic()` - Maps MEDDIC to Zoho fields
  - `meddic_to_note_content()` - Formats MEDDIC as note text

- `idempotency_service.py` - Prevents duplicate processing
  - `try_acquire_idempotency_key()` - Atomic check-and-set in Redis
  - `is_processed()` - Check if already processed
  - `mark_processed()` - Mark as complete

- `event_store_service.py` - Event persistence in Redis
  - `store_incoming_event()` - Save raw webhook payload
  - `load_event()` - Retrieve event by ID
  - `set_event_status()` - Update processing status
  - Statuses: `queued`, `processing`, `processed`, `ignored`, `failed`

- `rq_service.py` - RQ queue management
  - `get_queue()` - Get RQ queue instance
  - `default_retry()` - Retry config (3 retries, exponential backoff)

- `slack_service.py` - Slack alerting
  - `send_slack_alert()` - Posts to webhook URL on terminal failures

- `redis_client.py` - Redis connection management
  - `get_redis_bytes()` - Redis client for RQ (bytes mode)
  - `get_redis_str()` - Redis client for app data (str mode)

### 4. Schemas (`app/schemas/`)
**Purpose:** Pydantic models for data validation

- `llm.py` - LLM output schemas
  - `CalendlyLeadIntel` - 25+ fields extracted from Calendly Q&A
    - Name extraction (first/last), company inference from email domain
    - Location inference from timezone
    - BANT signals (Budget, Authority, Need, Timing)
    - Sales intelligence (pain points, tools, objectives, discovery questions, cheat sheet)
  - `MeddicOutput` - MEDDIC qualification framework
    - M: Metrics, E: Economic Buyer, D: Decision Criteria/Process
    - I: Identified Pain, C: Champion, C: Competition
    - Plus: next_steps, risks, confidence level

- `calendly.py` - Calendly webhook payload schemas
- `readai.py` - Read.ai webhook payload schemas

### 5. Utilities (`app/util/`)
- `security.py` - Webhook signature verification
- `text_format.py` - Text formatting helpers
- `time.py` - Date/time utilities (e.g., next_business_day)

---

## KEY PATTERNS & CONVENTIONS

### Idempotency Strategy
- **Key format:** `{source}:{event_type}:{external_id}`
- **Guard mechanism:** Try-acquire before enqueueing, check-processed before executing
- **Marker:** `idem:processed:{key}=1` set after successful completion
- **Duplicate handling:** Return `{ok: true, duplicate: true}` on duplicate webhooks

### Error Classification
- **Transient** (retry): Network errors, timeouts, 429/5xx, LLM transient errors, Zoho rate limits
- **Permanent** (fail): Validation errors, missing required fields, LLM schema failures after repair, 4xx errors (except 429)

### Retry Configuration
- Max retries: 3
- Backoff: Exponential (intervals: [60, 120, 240] seconds)
- RQ Retry object configured in `rq_service.default_retry()`

### LLM Extraction Flow
1. Build system prompt with instructions + JSON schema hint
2. Build user prompt with data
3. Call Gemini → Extract JSON from response (handle markdown code blocks)
4. Parse & validate against Pydantic schema
5. If validation fails → Call LLM again with repair instructions
6. If still fails → Raise `LLMError` (permanent failure)

### Zoho Field Mapping
- **Calendly → Zoho:** LLM intel fields map to custom Zoho fields via `ZCF_*` env vars
  - Example: `ZCF_PAIN_POINTS` → `stated_pain_points` from LLM
- **Read.ai → Zoho:** MEDDIC fields map to custom Zoho fields
  - Example: `ZCF_MEDDIC_METRICS` → `metrics` from LLM
- **Standard fields:** Email (search key), First_Name, Last_Name, Company, Lead_Status
- **Upsert logic:** Find by email → if exists, update; else create new

### DRY_RUN Mode
- When `DRY_RUN=true`: Zoho reads/writes are skipped, logged instead
- Useful for local validation without affecting production CRM
- LLM calls still execute (to test extraction)

---

## FILE STRUCTURE QUICK REFERENCE

```
app/
├── main.py                           # FastAPI app factory, route registration
├── worker.py                         # RQ worker entry point
├── settings.py                       # Pydantic settings (env vars)
├── logging.py                        # Logging configuration
├── api/
│   ├── routes_webhooks_calendly.py  # POST /webhooks/calendly
│   ├── routes_webhooks_readai.py    # POST /webhooks/readai
│   ├── routes_health.py             # GET /healthz
│   └── routes_debug.py              # Debug endpoints (dev only)
├── jobs/
│   ├── calendly_jobs.py             # Calendly event processors
│   ├── readai_jobs.py               # Read.ai event processors
│   └── retry.py                     # run_event_job() wrapper
├── services/
│   ├── llm_service.py               # Gemini LLM integration
│   ├── zoho_service.py              # Zoho CRM API client
│   ├── calendly_service.py          # Calendly data transformation
│   ├── readai_service.py            # Read.ai data transformation
│   ├── idempotency_service.py       # Idempotency guards
│   ├── event_store_service.py       # Event persistence (Redis)
│   ├── rq_service.py                # RQ queue management
│   ├── slack_service.py             # Slack alerting
│   └── redis_client.py              # Redis connection
├── schemas/
│   ├── llm.py                       # CalendlyLeadIntel, MeddicOutput
│   ├── calendly.py                  # Calendly webhook schemas
│   └── readai.py                    # Read.ai webhook schemas
└── util/
    ├── security.py                  # Signature verification
    ├── text_format.py               # Text formatting
    └── time.py                      # Date/time helpers
```

---

## CONFIGURATION REFERENCE

### Startup Validation
**The application validates configuration on startup and fails fast if critical settings are missing.**

- Required (when `DRY_RUN=false`): `GEMINI_API_KEY`, `ZOHO_CLIENT_ID`, `ZOHO_CLIENT_SECRET`, `ZOHO_REFRESH_TOKEN`
- Warnings logged for missing: `CALENDLY_SIGNING_KEY`, `READAI_SHARED_SECRET`, `SLACK_WEBHOOK_URL`, critical `ZCF_*` fields
- Validates `ZOHO_DC` is one of: `us`, `au`, `eu`, `in`

This prevents silent failures where webhooks are received but data isn't saved to Zoho.

### Critical Environment Variables
- `REDIS_URL` - Redis connection (default: `redis://redis:6379/0`)
- `DRY_RUN` - Skip Zoho writes (default: `true` for safety)
- `GEMINI_API_KEY` - Google Gemini API key (required for LLM when `DRY_RUN=false`)
- `ZOHO_REFRESH_TOKEN`, `ZOHO_CLIENT_ID`, `ZOHO_CLIENT_SECRET` - Zoho OAuth (required when `DRY_RUN=false`)
- `ZOHO_DC` - Data center: `us`, `au`, `eu`, `in`
- `SLACK_WEBHOOK_URL` - Slack incoming webhook for alerts
- `CALENDLY_SIGNING_KEY` - HMAC key for Calendly signature verification
- `READAI_SHARED_SECRET` - Shared secret for Read.ai webhook auth

### Redis TTL Configuration
- `EVENT_TTL_SECONDS` - Event data expiry (default: 30 days / 2,592,000 seconds)
- `IDEMPOTENCY_TTL_SECONDS` - Idempotency key expiry (default: 90 days / 7,776,000 seconds)

### Zoho Custom Field Mapping
All `ZCF_*` variables map LLM-extracted fields to Zoho CRM custom field API names.
Must be configured to match your Zoho instance:
- `ZCF_DEMO_DATETIME`, `ZCF_DEMO_TIMEZONE` - Demo scheduling info
- `ZCF_PAIN_POINTS`, `ZCF_TOOLS_CURRENTLY_USED` - Calendly extraction
- `ZCF_MEDDIC_METRICS`, `ZCF_MEDDIC_ECONOMIC_BUYER`, etc. - Read.ai MEDDIC

### Lead Statuses
- `STATUS_DEMO_BOOKED` - Default: "Demo Booked"
- `STATUS_DEMO_COMPLETE` - Default: "Demo Complete"
- `STATUS_DEMO_CANCELED` - Default: "Demo Canceled"
- `STATUS_DEMO_NO_SHOW` - Default: "Demo No-show"

---

## DEPLOYMENT ARCHITECTURE

### Local Development (Docker Compose)
- 3 services: `redis`, `api`, `worker`
- API: FastAPI with uvicorn --reload on port 8000
- Worker: RQ worker with scheduler
- Volumes mounted for hot reload

### Production (Render)
- Web service: Runs `uvicorn app.main:app` (Dockerfile)
- Worker service: Runs `python -m app.worker`
- Redis: Managed Redis instance
- Environment variables configured in Render dashboard

---

## TROUBLESHOOTING GUIDE

### Webhook Not Processing
1. Check signature/secret verification (401 errors)
2. Check event type filtering (`CALENDLY_EVENT_TYPE_URI`)
3. Check Redis connection
4. Check RQ worker is running
5. Look for duplicate idempotency key

### LLM Extraction Failing
1. Check `GEMINI_API_KEY` is valid
2. Review LLM logs for validation errors
3. Check if repair attempt succeeded
4. Verify prompt structure in `llm_service.py`

### Zoho Update Failing
1. Check `ZOHO_REFRESH_TOKEN` is valid (401 = expired/invalid)
2. Verify `ZOHO_DC` matches your account
3. Check custom field API names (`ZCF_*` vars) match Zoho
4. Check for rate limiting (429 errors)
5. Review Zoho API response in logs

### Missing Fields in Zoho
1. Verify `ZCF_*` env var is set correctly
2. Check LLM extracted non-empty value (review logs)
3. Verify Zoho field is writable (not read-only)
4. Check field type matches (e.g., datetime formatting)

---

## MAKING CHANGES - QUICK GUIDE

### Add New Calendly Field Extraction
1. Add field to `CalendlyLeadIntel` schema in `app/schemas/llm.py`
2. Update LLM prompt in `llm_service.calendly_lead_intel()` to extract it
3. Add `ZCF_*` env var to `settings.py`
4. Map field in `calendly_service.build_zoho_lead_payload_for_calendly()`
5. Set `ZCF_*` value in `.env` to Zoho field API name

### Add New MEDDIC Field
1. Add field to `MeddicOutput` schema in `app/schemas/llm.py`
2. Update LLM prompt in `llm_service.readai_meddic()` to extract it
3. Add `ZCF_*` env var to `settings.py`
4. Map field in `readai_service.build_zoho_lead_payload_for_meddic()`
5. Set `ZCF_*` value in `.env` to Zoho field API name

### Add New Webhook Event Type
1. Add event type handling in `routes_webhooks_*.py`
2. Create processor function in `jobs/*_jobs.py`
3. Add job enqueue logic in webhook route
4. Update event type mapping in `ingest_helpers.py` if needed

### Modify LLM Prompt
- **Calendly:** Edit `llm_service.calendly_lead_intel()` system/user prompts
- **Read.ai:** Edit `llm_service.readai_meddic()` system/user prompts
- **Testing:** Use `DRY_RUN=true` to test extraction without Zoho writes
- **Validation:** LLM output is validated against Pydantic schema automatically

### Change Retry Logic
- Edit `rq_service.default_retry()` for retry count/intervals
- Edit `retry.py._is_transient_exc()` to classify new error types
- Add new error types to `TransientJobError` or `PermanentJobError`

### Add New Zoho Operation
- Add method to `zoho_service.py`
- Use `_request()` helper for API calls
- Honor `DRY_RUN` mode (log instead of execute)
- Handle `ZohoTransientError` for rate limits/timeouts

---

## TESTING REFERENCE

### Unit Tests (`tests/`)
- `test_attendee_selection.py` - Read.ai attendee email selection logic
- `test_idempotency_logic.py` - Idempotency acquire/release/processed
- `test_llm_schema_validation.py` - LLM output schema validation
- `test_zoho_payload_mapping.py` - Zoho payload construction
- `util_fake_redis.py` - Fake Redis for testing

### Manual Testing
```bash
# Post Calendly sample
curl -X POST http://localhost:8000/webhooks/calendly \
  -H 'Content-Type: application/json' \
  -d @tests/fixtures/calendly_invitee_created.json

# Post Read.ai sample
curl -X POST http://localhost:8000/webhooks/readai \
  -H 'Content-Type: application/json' \
  -H 'X-ReadAI-Secret: your-secret' \
  -d @tests/fixtures/readai_meeting_completed.json
```

### Debug Endpoints (dev only)
- `GET /debug/info` - System info
- `GET /debug/events/{event_id}` - Event details
- `GET /debug/idem/{idempotency_key}` - Idempotency status

---

## REDIS DATA STRUCTURES

### Keys (with TTLs)
- `event:{event_id}` - Hash with event metadata (TTL: `EVENT_TTL_SECONDS`, default 30 days)
- `event_by_idem:{idempotency_key}` - String (event_id) for idempotency acquisition (TTL: `IDEMPOTENCY_TTL_SECONDS`, default 90 days)
- `idem:processed:{idempotency_key}` - String ("1") for processed marker (TTL: `IDEMPOTENCY_TTL_SECONDS`, default 90 days)
- `zoho:access_token` - String (cached Zoho access token, TTL set dynamically based on token expiry)

**TTL prevents unbounded Redis growth.** Events expire after 30 days, idempotency keys after 90 days.

### Event Hash Fields
- `event_id`, `source`, `event_type`, `external_id`, `idempotency_key`
- `status`, `attempts`, `last_error`, `created_at`, `updated_at`
- `payload` - JSON string of raw webhook payload

---

## SECURITY CONSIDERATIONS

### Webhook Authentication
- **Calendly:** HMAC-SHA256 signature verification (header: `Calendly-Webhook-Signature`)
- **Read.ai:** Shared secret comparison (header: `X-ReadAI-Secret`)
- Both return 401 if verification fails

### Secrets Management
- All secrets in `.env` file (not committed to git)
- Zoho refresh token should be rotated if exposed
- Gemini API key has usage quota limits
- Slack webhook URL should be kept private

### Data Handling
- Raw webhook payloads stored in Redis (sensitive data)
- Redis should be password-protected in production
- Zoho access tokens cached with TTL, refreshed automatically
- No PII logged except in debug mode

---

## PERFORMANCE CONSIDERATIONS

### LLM Calls
- Calendly: ~2-5 seconds per call (lightweight Q&A extraction)
- Read.ai: ~10-30 seconds per call (transcript analysis, can be long)
- Transcript truncation applied for meetings > 15k chars
- Rate limits: Gemini API has per-minute quotas (monitor usage)

### Zoho API
- Rate limits: 100 calls/minute per token (varies by plan)
- Access token cached in Redis to avoid refresh on every call
- Retry with backoff on 429 responses

### Redis
- Event payloads stored as JSON strings (size varies)
- No automatic cleanup (consider TTL on event keys if needed)
- Idempotency keys never expire (prevents duplicate processing forever)

---

## IMPORTANT IMPLEMENTATION DETAILS

### Calendly Event Type Normalization
- Calendly sends `invitee.created`, `invitee.canceled`, etc.
- These map to different Zoho lead statuses
- Rescheduled events treated as bookings with updated datetime

### Read.ai Attendee Selection
- Prioritizes external attendees (not @govisually.com/@clockworkstudio.com)
- Configured via `READAI_CUSTOMER_DOMAINS` (comma-separated)
- Falls back to any attendee if no external found
- Fails permanently if no email available

### LLM Output Validation
- 2-attempt flow: generate → validate → repair → validate
- Handles markdown code blocks in LLM responses
- Converts `null` to empty strings for optional fields
- Raises `LLMError` if schema still invalid after repair

### Zoho Datetime Formatting
- Calendly datetimes: ISO 8601 (passed through)
- Read.ai datetimes: Formatted to `YYYY-MM-DDTHH:MM:SS+00:00`
- Timezone handling in `readai_jobs._format_demo_date_for_zoho()`

### Note Creation
- Calendly: Attaches Q&A + LLM intel as formatted note
- Read.ai: Attaches MEDDIC summary + recording URL as note
- Notes include date in title for easy sorting

---

## QUICK WINS FOR OPTIMIZATION

1. **Add Redis TTL** on event keys to prevent unbounded growth
2. **Cache Zoho field metadata** to reduce API calls
3. **Batch Zoho updates** if processing multiple events for same lead
4. **Add monitoring** for LLM extraction success rate
5. **Implement circuit breaker** for Zoho API (if rate limited, pause jobs)
6. **Add metrics** to track processing latency by event type

---

## GOTCHAS & EDGE CASES

1. **Duplicate Webhooks:** Calendly/Read.ai may send duplicates on retries → Idempotency handles this
2. **Missing Zoho Lead:** Read.ai creates minimal lead if no Calendly match exists
3. **Long Transcripts:** Truncated intelligently to fit LLM token limits
4. **Zoho Custom Fields:** Must exist in Zoho before setting (will fail silently otherwise)
5. **Email Case Sensitivity:** All emails normalized to lowercase for matching
6. **Demo Date Preservation:** Read.ai doesn't overwrite Calendly's demo date if already set
7. **Empty LLM Fields:** LLM may return empty strings for fields (not extractable from data)
8. **Webhook Ordering:** No guarantee Calendly fires before Read.ai for same customer
