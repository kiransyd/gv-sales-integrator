# GoVisually Integrations Service (FastAPI + RQ + Redis)

Receives **Calendly** and **Read.ai** webhooks, enqueues background jobs via **RQ**, and updates **Zoho CRM Leads** (upsert by email) with **Gemini** LLM enrichment and **MEDDIC** summaries. Terminal failures alert **Slack**.

## Quickstart (local, Docker Compose)
1. Copy env file:

```bash
cp .env.example .env
```

2. Fill required values in `.env` (at minimum for real writes: Zoho + Gemini + Slack). For safe local validation set:
- `DRY_RUN=true`

3. Run:

```bash
docker compose up --build
```

- API: `http://localhost:8000`
- Health: `GET /healthz`

## Webhook URLs
Configure your providers to call:
- Calendly: `{BASE_URL}/webhooks/calendly`
- Read.ai: `{BASE_URL}/webhooks/readai`

## ngrok (dev)
Expose the local API publicly:

```bash
./scripts/start_ngrok.sh
```

Set the printed HTTPS URL as `BASE_URL` in `.env`, then update webhook settings in Calendly/Read.ai.

## Posting sample payloads locally

```bash
curl -sS -X POST http://localhost:8000/webhooks/calendly \
  -H 'Content-Type: application/json' \
  -d @tests/fixtures/calendly_invitee_created.json
```

```bash
curl -sS -X POST http://localhost:8000/webhooks/readai \
  -H 'Content-Type: application/json' \
  -H 'X-ReadAI-Secret: <your-secret>' \
  -d @tests/fixtures/readai_meeting_completed.json
```

## Debug endpoints (dev-only)
Set `ALLOW_DEBUG_ENDPOINTS=true` to enable:
- `GET /debug/info`
- `GET /debug/events/{event_id}`
- `GET /debug/idem/{idempotency_key}`

## Idempotency model
- Incoming webhooks compute an idempotency key:
  - Calendly: `calendly:{event_type}:{external_id}`
  - Read.ai: `readai:meeting_completed:{meeting_id}`
- API stores the raw payload in Redis and enqueues an RQ job with `job_id=idempotency_key`.
- Worker sets `idem:processed:{idempotency_key}=1` after successful processing.

## Zoho OAuth (refresh token flow)
This service uses a refresh token to mint short-lived access tokens and caches them in memory.

See:
- `scripts/zoho_oauth_helper.md`

## DRY_RUN
Set `DRY_RUN=true` to avoid any Zoho writes. The worker will log what it would send.

## Signature / secret verification
- Calendly: HMAC verification is enabled when `CALENDLY_SIGNING_KEY` is set.
- Read.ai: expects `X-ReadAI-Secret` when `READAI_SHARED_SECRET` is set.

## Tests

```bash
pytest -q
```

## Deployment (Render)
- Build from `Dockerfile` (web service for API) and run a separate worker service using `python -m app.worker`.
- Add a Redis instance and set `REDIS_URL`.
- Set all env vars from `.env.example`.
- Use Render URL as `BASE_URL`.

## Troubleshooting
- **401 from Calendly**: signature header/key mismatch; ensure `CALENDLY_SIGNING_KEY` matches the webhook signing key and the provider sends `Calendly-Webhook-Signature`.
- **Zoho 401**: invalid/rotated refresh token or wrong data center (`ZOHO_DC`).
- **Zoho 429**: rate limited; jobs retry with backoff.
- **LLM schema errors**: the worker runs a 2-step validation/repair loop; persistent failures trigger Slack on terminal failure.



