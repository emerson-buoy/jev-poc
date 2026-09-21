#!/usr/bin/env bash
# Installs what is missing and starts the API (:8000) and the board (:3000).
# Usage: ./run.sh            start both apps in mock mode unless apps/api/.env has a key
#        ./run.sh --check    run tests and linters for both apps instead of starting
set -euo pipefail
cd "$(dirname "$0")"

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing $1. $2" >&2; exit 1; }; }
need node "Install Node 20+: https://nodejs.org"
need pnpm "Install pnpm: npm install -g pnpm"
need uv   "Install uv: https://docs.astral.sh/uv/getting-started/installation/"

[ -d node_modules ] || pnpm install
[ -d apps/api/.venv ] || uv sync --directory apps/api
[ -d apps/web/src/lib/api/generated ] || pnpm generate:client

if [ "${1:-}" = "--check" ]; then
  pnpm test
  pnpm lint
  pnpm --filter web build >/dev/null
  pnpm --filter web typecheck
  echo "All checks passed."
  exit 0
fi

if [ ! -f apps/api/.env ] || ! grep -qE '^AI_GATEWAY_API_KEY=.+' apps/api/.env; then
  echo "No AI_GATEWAY_API_KEY in apps/api/.env: running in mock triage mode."
fi
echo "API   http://localhost:8000/docs"
echo "Board http://localhost:3000"
exec pnpm dev
