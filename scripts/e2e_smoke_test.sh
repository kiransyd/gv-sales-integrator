#!/usr/bin/env bash
set -euo pipefail

# End-to-end smoke test for:
# - Read.ai webhook -> enqueue -> worker -> Zoho/Gemini
# - (optional) Calendly webhook -> enqueue -> worker -> Zoho/Gemini
#
# Requirements:
# - docker-compose stack running (api on localhost:8000)
# - ALLOW_DEBUG_ENDPOINTS=true in .env
#
# Usage:
#   ./scripts/e2e_smoke_test.sh
#   BASE_URL=http://localhost:8000 ./scripts/e2e_smoke_test.sh
#   TEST_CALENDLY=true ./scripts/e2e_smoke_test.sh

BASE_URL="${BASE_URL:-http://localhost:8000}"
TEST_CALENDLY="${TEST_CALENDLY:-false}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-120}"
POLL_SECONDS="${POLL_SECONDS:-2}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

require_cmd curl
require_cmd python3

json_get() {
  # Reads JSON from stdin and prints a key via python (no jq dependency).
  python3 -c '
import json, sys
key = sys.argv[1]
data = json.load(sys.stdin)
cur = data
for part in key.split("."):
    if isinstance(cur, dict):
        cur = cur.get(part)
    else:
        cur = None
        break
print("" if cur is None else cur)
' "$1"
}

poll_event() {
  local event_id="$1"
  local start
  start="$(python3 -c 'import time; print(int(time.time()))')"

  while true; do
    local now
    now="$(python3 -c 'import time; print(int(time.time()))')"
    local elapsed=$((now - start))
    if [[ "$elapsed" -ge "$TIMEOUT_SECONDS" ]]; then
      echo "Timed out waiting for event to finish. event_id=$event_id" >&2
      echo "Try: docker-compose logs -f worker" >&2
      exit 1
    fi

    local ev
    if ! ev="$(curl -sS "$BASE_URL/debug/events/$event_id")"; then
      echo "Failed to fetch debug event. Is ALLOW_DEBUG_ENDPOINTS=true and API reachable?" >&2
      exit 1
    fi

    local status
    status="$(printf '%s' "$ev" | json_get status)"
    local attempts
    attempts="$(printf '%s' "$ev" | json_get attempts)"
    local last_error
    last_error="$(printf '%s' "$ev" | json_get last_error)"

    echo "event_id=$event_id status=$status attempts=$attempts"

    if [[ "$status" == "processed" || "$status" == "ignored" ]]; then
      return 0
    fi
    if [[ "$status" == "failed" ]]; then
      echo "Event failed: $last_error" >&2
      echo "Worker logs: docker-compose logs --tail=200 worker" >&2
      exit 1
    fi

    sleep "$POLL_SECONDS"
  done
}

echo "Checking API health..."
curl -sS "$BASE_URL/healthz" >/dev/null

echo "Read.ai: posting meeting_end payload..."
SESSION_ID="sess-$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')"

READAI_SECRET="$(python3 - <<'PY'
import re
from pathlib import Path
env = Path('.env').read_text() if Path('.env').exists() else ''
m = re.search(r'^READAI_SHARED_SECRET=(.*)$', env, flags=re.M)
print((m.group(1).strip() if m else '').strip())
PY
)"

READAI_HEADERS=(-H "Content-Type: application/json")
if [[ -n "$READAI_SECRET" ]]; then
  READAI_HEADERS+=(-H "X-ReadAI-Secret: $READAI_SECRET")
fi

READAI_RESP="$(
  curl -sS -X POST "$BASE_URL/webhooks/readai" \
    "${READAI_HEADERS[@]}" \
    -d "{
      \"session_id\":\"$SESSION_ID\",
      \"trigger\":\"meeting_end\",
      \"title\":\"GoVisually Demo (Smoke Test)\",
      \"start_time\":\"2025-12-17T10:00:00Z\",
      \"end_time\":\"2025-12-17T10:30:00Z\",
      \"participants\":[
        {\"name\":\"GV Rep\",\"email\":\"rep@govisually.com\"},
        {\"name\":\"Smoke Test Lead\",\"email\":\"alice@example.com\"}
      ],
      \"summary\":\"Smoke test summary.\",
      \"report_url\":\"https://app.read.ai/analytics/meetings/$SESSION_ID\",
      \"transcript\":{
        \"speaker_blocks\":[
          {\"speaker\":{\"name\":\"Lead\"},\"words\":\"We need faster approvals.\"},
          {\"speaker\":{\"name\":\"Rep\"},\"words\":\"GoVisually can help.\"}
        ]
      }
    }"
)"

echo "Read.ai response: $READAI_RESP"
EVENT_ID="$(printf '%s' "$READAI_RESP" | json_get event_id)"
if [[ -z "$EVENT_ID" ]]; then
  echo "No event_id returned. Full response: $READAI_RESP" >&2
  exit 1
fi

poll_event "$EVENT_ID"
echo "Read.ai job completed."

if [[ "$TEST_CALENDLY" == "true" ]]; then
  echo "Calendly: posting invitee.created payload..."

  # Load fixture and adjust email to keep it deterministic.
  CAL_PAYLOAD="$(python3 - <<'PY'
import json
from pathlib import Path
p = Path('tests/fixtures/calendly_invitee_created.json')
data = json.loads(p.read_text())
data['payload']['invitee']['email'] = 'alice@example.com'
print(json.dumps(data))
PY
)"

  # If CALENDLY_SIGNING_KEY is set, create Calendly-Webhook-Signature header (t=...,v1=...).
  printf '%s' "$CAL_PAYLOAD" > .cal_body.json

  CAL_SIG_HEADER="$(python3 - <<'PY'
import hmac, hashlib, time, re
from pathlib import Path
env = Path('.env').read_text() if Path('.env').exists() else ''
m = re.search(r'^CALENDLY_SIGNING_KEY=(.*)$', env, flags=re.M)
key = (m.group(1).strip() if m else '').strip()
if not key:
    print('')
    raise SystemExit(0)
ts = int(time.time())
body = Path('.cal_body.json').read_bytes()
msg = str(ts).encode() + b'.' + body
sig = hmac.new(key.encode(), msg, hashlib.sha256).hexdigest()
print(f't={ts},v1={sig}')
PY
)"

  CAL_HEADERS=(-H "Content-Type: application/json")
  if [[ -n "$CAL_SIG_HEADER" ]]; then
    CAL_HEADERS+=(-H "Calendly-Webhook-Signature: $CAL_SIG_HEADER")
  fi

  CAL_RESP="$(
    curl -sS -X POST "$BASE_URL/webhooks/calendly" \
      "${CAL_HEADERS[@]}" \
      -d @"./.cal_body.json"
  )"

  rm -f .cal_body.json
  echo "Calendly response: $CAL_RESP"
  CAL_EVENT_ID="$(printf '%s' "$CAL_RESP" | json_get event_id)"
  if [[ -n "$CAL_EVENT_ID" ]]; then
    poll_event "$CAL_EVENT_ID"
    echo "Calendly job completed."
  else
    echo "Calendly was ignored or de-duplicated (no event_id returned)."
  fi
fi

echo "All smoke tests completed successfully."


