#!/bin/bash
# Quick End-to-End Test
# Simple one-command test script

echo "🚀 Running End-to-End Test..."
echo ""

python3 scripts/e2e_full_flow.py

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 To see what was sent to Zoho, run:"
echo "   docker-compose logs worker --tail 200 | grep -E '(Creating Zoho|Updating Zoho|fields)'"
echo ""


