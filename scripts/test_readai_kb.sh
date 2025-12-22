#!/bin/bash
# Test Read.ai webhook with Knowledge Base integration
# This script sends a sample Read.ai meeting payload and monitors for KB usage

BASE_URL="${BASE_URL:-http://localhost:8000}"
READAI_SECRET="${READAI_SECRET:-your_readai_secret_here}"

# Sample Read.ai payload with FDA compliance discussion (will trigger KB)
PAYLOAD='{
  "session_id": "test-session-kb-'$(date +%s)'",
  "trigger": "meeting_end",
  "title": "FDA Compliance Discussion - Pharma Company",
  "start_time": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
  "end_time": "'$(date -u -v+30M +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '+30 minutes' +%Y-%m-%dT%H:%M:%SZ)'",
  "duration_minutes": 30,
  "participants": [
    { "name": "Sales Rep", "email": "sales@govisually.com" },
    { "name": "John Smith", "email": "john.smith@pharmacorp.com" }
  ],
  "owner": { "name": "Sales Rep", "email": "sales@govisually.com" },
  "summary": "Discussion about FDA compliance challenges in pharmaceutical labeling. Current manual process takes 2-3 weeks per product. Concerns about allergen disclosure errors and net weight requirements.",
  "action_items": [{ "text": "Send FDA Regulatory Agent information" }, { "text": "Provide ROI calculations" }],
  "key_questions": [{ "text": "How does your FDA compliance checking work?" }],
  "topics": [{ "text": "FDA Compliance" }, { "text": "Pharmaceutical Labeling" }],
  "report_url": "https://app.read.ai/analytics/meetings/test-session-kb",
  "transcript": {
    "speakers": [{ "name": "John Smith" }, { "name": "Sales Rep" }],
    "speaker_blocks": [
      {
        "start_time": "1719514000000",
        "end_time": "1719514005000",
        "speaker": { "name": "Sales Rep" },
        "words": "Thanks for joining today. Can you tell me a bit about your current FDA compliance process?"
      },
      {
        "start_time": "1719514006000",
        "end_time": "1719514015000",
        "speaker": { "name": "John Smith" },
        "words": "Sure. We're a pharmaceutical company and we're struggling with FDA compliance. Our current process is very manual - we have to check every label manually for FDA requirements. It takes our team about 2-3 weeks per product, and we're worried about making mistakes."
      },
      {
        "start_time": "1719514016000",
        "end_time": "1719514020000",
        "speaker": { "name": "Sales Rep" },
        "words": "I understand. What kind of errors are you seeing?"
      },
      {
        "start_time": "1719514021000",
        "end_time": "1719514030000",
        "speaker": { "name": "John Smith" },
        "words": "Mostly around allergen disclosures and net weight requirements. We had a close call last year where we almost shipped a product with incorrect allergen information. That would have been a disaster - FDA warning letters, recalls, the whole thing."
      },
      {
        "start_time": "1719514031000",
        "end_time": "1719514035000",
        "speaker": { "name": "Sales Rep" },
        "words": "That's a serious concern. How many products do you launch per year?"
      },
      {
        "start_time": "1719514036000",
        "end_time": "1719514040000",
        "speaker": { "name": "John Smith" },
        "words": "About 50-60 new SKUs annually. Each one goes through this process."
      },
      {
        "start_time": "1719514041000",
        "end_time": "1719514045000",
        "speaker": { "name": "Sales Rep" },
        "words": "And who makes the final decision on compliance tools?"
      },
      {
        "start_time": "1719514046000",
        "end_time": "1719514050000",
        "speaker": { "name": "John Smith" },
        "words": "That would be our VP of Regulatory Affairs, Sarah Johnson. She's the one who approves any new tools or processes."
      },
      {
        "start_time": "1719514051000",
        "end_time": "1719514055000",
        "speaker": { "name": "Sales Rep" },
        "words": "Got it. What's your timeline for finding a solution?"
      },
      {
        "start_time": "1719514056000",
        "end_time": "1719514060000",
        "speaker": { "name": "John Smith" },
        "words": "We'd like to have something in place by Q2. We're evaluating a few vendors, including Workfront and some custom solutions."
      },
      {
        "start_time": "1719514061000",
        "end_time": "1719514065000",
        "speaker": { "name": "Sales Rep" },
        "words": "What are the key criteria you're looking for?"
      },
      {
        "start_time": "1719514066000",
        "end_time": "1719514070000",
        "speaker": { "name": "John Smith" },
        "words": "Definitely FDA compliance checking, integration with our existing systems, and accuracy. We can't afford mistakes."
      },
      {
        "start_time": "1719514071000",
        "end_time": "1719514075000",
        "speaker": { "name": "Sales Rep" },
        "words": "Perfect. Let me send you some information about our FDA Regulatory Agent and ROI calculations. We typically see 85-90% time savings for pharma companies."
      },
      {
        "start_time": "1719514076000",
        "end_time": "1719514080000",
        "speaker": { "name": "John Smith" },
        "words": "That sounds promising. Can you schedule a technical demo?"
      },
      {
        "start_time": "1719514081000",
        "end_time": "1719514085000",
        "speaker": { "name": "Sales Rep" },
        "words": "Absolutely. I'll send a calendar invite."
      }
    ]
  }
}'

echo "============================================================"
echo "Testing Read.ai Webhook with Knowledge Base Integration"
echo "============================================================"
echo ""
echo "Endpoint: $BASE_URL/webhooks/readai"
echo "Secret: ${READAI_SECRET:0:10}..."
echo ""
echo "Sending test payload..."
echo ""

# Send the webhook
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -X POST "$BASE_URL/webhooks/readai" \
  -H "Content-Type: application/json" \
  -H "X-ReadAI-Secret: $READAI_SECRET" \
  -d "$PAYLOAD")

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')

echo "Response:"
echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
echo ""
echo "HTTP Status: $HTTP_CODE"
echo ""

if [ "$HTTP_CODE" = "200" ]; then
    EVENT_ID=$(echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('event_id', 'N/A'))" 2>/dev/null || echo "N/A")
    echo "✅ Webhook accepted!"
    echo "   Event ID: $EVENT_ID"
    echo ""
    echo "============================================================"
    echo "Monitoring Worker Logs for KB Usage"
    echo "============================================================"
    echo ""
    echo "Watch for these log messages:"
    echo "  📚 Using Knowledge Base (File Search)"
    echo "  ✅ Knowledge Base used! Retrieved X chunks"
    echo "  📚 KB files referenced: ..."
    echo ""
    echo "To monitor logs, run:"
    echo "  docker-compose logs -f worker | grep -E 'KB|Knowledge|chunks|MEDDIC'"
    echo ""
    echo "Or check the full worker logs:"
    echo "  docker-compose logs worker --tail=50"
    echo ""
else
    echo "❌ Webhook failed!"
    echo "   Check your READAI_SHARED_SECRET in .env"
    echo "   Make sure the API is running: docker-compose ps"
fi
