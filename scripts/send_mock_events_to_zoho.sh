#!/usr/bin/env bash
set -euo pipefail

# Sends mock Calendly + Read.ai events to the local API and verifies the resulting Zoho Lead.
#
# Prereqs:
# - docker-compose stack running (api reachable at BASE_URL)
# - ALLOW_DEBUG_ENDPOINTS=true in .env
# - DRY_RUN=false in .env (otherwise Zoho won’t be updated)
#
# Usage:
#   ./scripts/send_mock_events_to_zoho.sh
#   TEST_EMAIL=you+zoho-test@yourdomain.com ./scripts/send_mock_events_to_zoho.sh
#   BASE_URL=http://localhost:8000 ./scripts/send_mock_events_to_zoho.sh

BASE_URL="${BASE_URL:-http://localhost:8000}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-600}"
POLL_SECONDS="${POLL_SECONDS:-2}"
TEST_EMAIL="${TEST_EMAIL:-}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 1; }
}

require_cmd curl
require_cmd python3

env_get() {
  python3 - "$1" <<'PY'
import re, sys
from pathlib import Path
key = sys.argv[1]
env = Path(".env").read_text() if Path(".env").exists() else ""
m = re.search(rf"^{re.escape(key)}=(.*)$", env, flags=re.M)
print((m.group(1).strip() if m else "").strip())
PY
}

json_get() {
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
    local now elapsed
    now="$(python3 -c 'import time; print(int(time.time()))')"
    elapsed=$((now - start))
    if [[ "$elapsed" -ge "$TIMEOUT_SECONDS" ]]; then
      echo "Timed out waiting for event. event_id=$event_id" >&2
      echo "Try: docker-compose logs --tail=200 worker" >&2
      exit 1
    fi

    local ev status attempts last_error
    ev="$(curl -sS "$BASE_URL/debug/events/$event_id")"
    status="$(printf '%s' "$ev" | json_get status)"
    attempts="$(printf '%s' "$ev" | json_get attempts)"
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

DRY_RUN="$(env_get DRY_RUN)"
if [[ "$DRY_RUN" != "false" ]]; then
  echo "DRY_RUN is not false in .env. Set DRY_RUN=false to test Zoho writes." >&2
  exit 1
fi

echo "Checking API health..."
curl -sS "$BASE_URL/healthz" >/dev/null

if [[ -z "$TEST_EMAIL" ]]; then
  TEST_EMAIL="zoho-e2e-$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')@example.com"
fi
echo "Using TEST_EMAIL=$TEST_EMAIL"

# 1) Calendly invitee.created (Demo Booked)
CAL_BODY="$(python3 - <<PY
import json, uuid
from pathlib import Path
p = Path("tests/fixtures/calendly_invitee_created.json")
data = json.loads(p.read_text())
data["payload"]["invitee"]["email"] = "${TEST_EMAIL}"
data["payload"]["invitee"]["name"] = "Zoho E2E Lead"
data["payload"]["invitee"]["uuid"] = str(uuid.uuid4())
data["payload"]["event"]["uuid"] = str(uuid.uuid4())
print(json.dumps(data))
PY
)"

echo "Posting Calendly invitee.created..."
CAL_RESP="$(curl -sS -X POST "$BASE_URL/webhooks/calendly" -H "Content-Type: application/json" -d "$CAL_BODY")"
echo "Calendly response: $CAL_RESP"
CAL_EVENT_ID="$(printf '%s' "$CAL_RESP" | json_get event_id)"
if [[ -n "$CAL_EVENT_ID" ]]; then
  poll_event "$CAL_EVENT_ID"
else
  echo "Calendly was ignored or de-duplicated (no event_id returned)."
fi

# 2) Read.ai meeting_end (Demo Complete)
SESSION_ID="sess-$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')"
READAI_SECRET="$(env_get READAI_SHARED_SECRET)"

READAI_HEADERS=(-H "Content-Type: application/json")
if [[ -n "$READAI_SECRET" ]]; then
  READAI_HEADERS+=(-H "X-ReadAI-Secret: $READAI_SECRET")
fi

READAI_BODY="$(python3 - <<PY
import json
from pathlib import Path
p = Path("tests/fixtures/readai_meeting_end.json")
data = json.loads(p.read_text())
data["session_id"] = "${SESSION_ID}"
data["participants"] = [
  {"name": "GV Rep", "email": "rep@govisually.com"},
  {"name": "Zoho E2E Lead", "email": "${TEST_EMAIL}"},
]
data["owner"] = {"name": "GV Rep", "email": "rep@govisually.com"}
print(json.dumps(data))
PY
)"

echo "Posting Read.ai meeting_end..."
READAI_RESP="$(
  curl -sS -X POST "$BASE_URL/webhooks/readai" \
    "${READAI_HEADERS[@]}" \
    -d "$READAI_BODY"
)"
echo "Read.ai response: $READAI_RESP"
READAI_EVENT_ID="$(printf '%s' "$READAI_RESP" | json_get event_id)"
poll_event "$READAI_EVENT_ID"

echo "Fetching Lead from Zoho by email (to verify fields)..."
python3 scripts/zoho_fetch_lead_by_email.py --email "$TEST_EMAIL"

echo "Done."


