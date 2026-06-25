#!/usr/bin/env bash
# Start the PolyLife core.  Run:  scripts/bash/start-core.sh
# Builds the frontend + backend in Docker and serves on http://localhost:8000
set -euo pipefail
cd "$(dirname "$0")/../.."
[ -f .env ] || { cp .env.example .env; echo "Created .env"; }
docker compose up --build
