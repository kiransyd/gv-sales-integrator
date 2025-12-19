#!/usr/bin/env bash
set -euo pipefail

if ! command -v ngrok >/dev/null 2>&1; then
  echo "ngrok not found. Install with:"
  echo "  brew install ngrok/ngrok/ngrok"
  exit 1
fi

echo "Starting ngrok tunnel to http://localhost:8000 ..."
echo "Once running, copy the HTTPS forwarding URL and set:"
echo "  BASE_URL=https://xxxx.ngrok-free.app"
echo "Then configure webhooks:"
echo "  Calendly: {BASE_URL}/webhooks/calendly"
echo "  Read.ai:  {BASE_URL}/webhooks/readai"
ngrok http 8000






