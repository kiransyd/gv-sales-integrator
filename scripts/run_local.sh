#!/usr/bin/env bash
set -euo pipefail

echo "Starting local stack (api + worker + redis)..."
echo "Tip: copy .env.example -> .env and fill required values."
docker compose up --build



