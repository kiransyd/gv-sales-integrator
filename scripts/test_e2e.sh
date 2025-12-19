#!/bin/bash
# Simple End-to-End Test Script
# Tests Calendly booking → Read.ai demo completion → Zoho updates

set -e

echo "=========================================="
echo "  End-to-End Integration Test"
echo "=========================================="
echo ""

# Run the Python test script
python3 scripts/e2e_full_flow.py

echo ""
echo "=========================================="
echo "  Check Results"
echo "=========================================="
echo ""
echo "To verify what was sent to Zoho, check worker logs:"
echo "  docker-compose logs worker --tail 200 | grep -E '(Creating Zoho|Updating Zoho|fields)'"
echo ""
echo "Or check the debug endpoints shown above."



