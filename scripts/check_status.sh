#!/bin/bash
# Check system status dashboard
# Usage: ./scripts/check_status.sh [environment]
# Example: ./scripts/check_status.sh production

ENV=${1:-local}

if [ "$ENV" = "production" ]; then
    # Load BASE_URL from .env.production
    if [ -f .env.production ]; then
        BASE_URL=$(grep -E "^BASE_URL=" .env.production | cut -d '=' -f2-)
    else
        echo "❌ .env.production not found"
        exit 1
    fi
else
    BASE_URL="http://localhost:8000"
fi

echo "🔍 Checking system status: $BASE_URL"
echo ""

# Fetch status
STATUS=$(curl -s "$BASE_URL/debug/status")

# Check if request was successful
if [ $? -ne 0 ]; then
    echo "❌ Failed to fetch status from $BASE_URL/debug/status"
    echo "   Make sure ALLOW_DEBUG_ENDPOINTS=true in your .env"
    exit 1
fi

# Pretty print with jq if available, otherwise raw JSON
if command -v jq &> /dev/null; then
    echo "$STATUS" | jq '.'
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 QUICK SUMMARY"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Server
    SERVER_STATUS=$(echo "$STATUS" | jq -r '.server.status // "unknown"')
    echo "🖥️  Server: $SERVER_STATUS"

    # Redis
    REDIS_STATUS=$(echo "$STATUS" | jq -r '.redis.status // "unknown"')
    echo "💾 Redis: $REDIS_STATUS"

    # Queue
    PENDING=$(echo "$STATUS" | jq -r '.queue.counts.pending // 0')
    STARTED=$(echo "$STATUS" | jq -r '.queue.counts.started // 0')
    FAILED=$(echo "$STATUS" | jq -r '.queue.counts.failed // 0')
    echo "📥 Queue: $PENDING pending, $STARTED processing, $FAILED failed"

    # Workers
    WORKER_COUNT=$(echo "$STATUS" | jq -r '.workers.count // 0')
    WORKER_STATUS=$(echo "$STATUS" | jq -r '.workers.status // "unknown"')
    echo "👷 Workers: $WORKER_COUNT running ($WORKER_STATUS)"

    # Recent events
    EVENT_COUNT=$(echo "$STATUS" | jq -r '.recent_activity.total_events // 0')
    echo "📋 Events: $EVENT_COUNT total"

    # System
    CPU=$(echo "$STATUS" | jq -r '.system.cpu_percent // 0')
    MEM=$(echo "$STATUS" | jq -r '.system.memory_mb // 0')
    UPTIME=$(echo "$STATUS" | jq -r '.system.uptime_seconds // 0')
    echo "💻 System: ${CPU}% CPU, ${MEM}MB RAM, ${UPTIME}s uptime"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Show active jobs if any
    ACTIVE_JOBS=$(echo "$STATUS" | jq -r '.queue.active_jobs // [] | length')
    if [ "$ACTIVE_JOBS" -gt 0 ]; then
        echo "🔄 ACTIVE JOBS:"
        echo "$STATUS" | jq -r '.queue.active_jobs[] | "  • \(.func_name) (started: \(.started_at // "unknown"))"'
        echo ""
    fi

    # Show failed jobs if any
    if [ "$FAILED" -gt 0 ]; then
        echo "❌ RECENT FAILED JOBS:"
        echo "$STATUS" | jq -r '.queue.recent_failed_jobs[] | "  • \(.func_name) - \(.exc_info // "no error info")"'
        echo ""
    fi

else
    echo "$STATUS"
    echo ""
    echo "💡 Tip: Install jq for prettier output: brew install jq"
fi
