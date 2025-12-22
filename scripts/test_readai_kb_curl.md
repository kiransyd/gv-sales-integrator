# Testing Read.ai Webhook with Knowledge Base

## Quick Test with curl

### 1. Get your Read.ai Secret

```bash
# From .env file
grep READAI_SHARED_SECRET .env

# Or set it directly
export READAI_SECRET="your_secret_here"
```

### 2. Send Test Request

```bash
curl -X POST http://localhost:8000/webhooks/readai \
  -H "Content-Type: application/json" \
  -H "X-ReadAI-Secret: $READAI_SECRET" \
  -d @- << 'EOF'
{
  "session_id": "test-kb-$(date +%s)",
  "trigger": "meeting_end",
  "title": "FDA Compliance Discussion - Pharma Company",
  "start_time": "2025-12-21T10:00:00Z",
  "end_time": "2025-12-21T10:30:00Z",
  "duration_minutes": 30,
  "participants": [
    { "name": "Sales Rep", "email": "sales@govisually.com" },
    { "name": "John Smith", "email": "john.smith@pharmacorp.com" }
  ],
  "owner": { "name": "Sales Rep", "email": "sales@govisually.com" },
  "summary": "Discussion about FDA compliance challenges. Current manual process takes 2-3 weeks per product. Concerns about allergen disclosure errors.",
  "transcript": {
    "speaker_blocks": [
      {
        "speaker": { "name": "John Smith" },
        "words": "We're a pharma company struggling with FDA compliance. Our manual process takes 2-3 weeks per product. We're worried about allergen disclosure errors and net weight requirements."
      },
      {
        "speaker": { "name": "Sales Rep" },
        "words": "Our FDA Regulatory Agent can help with that. We typically see 85-90% time savings for pharma companies with ROI payback in 2-4 months."
      },
      {
        "speaker": { "name": "John Smith" },
        "words": "We're evaluating vendors including Workfront. Our VP of Regulatory Affairs, Sarah Johnson, makes the final decision. We need something by Q2."
      }
    ]
  }
}
EOF
```

### 3. Monitor Worker Logs for KB Usage

```bash
# Watch worker logs in real-time
docker-compose logs -f worker | grep -E "KB|Knowledge|chunks|MEDDIC|File Search"

# Or see full logs
docker-compose logs worker --tail=100
```

Look for these log messages:
- `📚 Using Knowledge Base (File Search)`
- `✅ Knowledge Base used! Retrieved X chunks`
- `📚 KB files referenced: ...`

### 4. Check Event Status

After sending, you'll get an `event_id` in the response. Check its status:

```bash
# Replace EVENT_ID with the ID from the response
curl http://localhost:8000/debug/events/EVENT_ID
```

## Expected Response

```json
{
  "ok": true,
  "queued": true,
  "event_id": "evt_...",
  "idempotency_key": "readai:meeting_completed:..."
}
```

## What to Look For

1. **Webhook Response**: Should return `200 OK` with `queued: true`
2. **Worker Logs**: Should show KB usage messages
3. **Zoho Lead**: Should be created/updated with enhanced MEDDIC data
4. **Zoho Note**: Should contain KB-enhanced insights

## Troubleshooting

If KB isn't being used:
- Check `GOVISUALLY_KB_STORE_ID` is set in `.env`
- Check worker logs for errors
- Verify the transcript mentions topics that match KB content (FDA, compliance, ROI, etc.)
