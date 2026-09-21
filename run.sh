#!/usr/bin/env bash
# Runs the whole thing in Docker: builds both images and starts the API (:8000) and the board (:3000).
# Nothing is installed on the host. Ctrl-C stops the containers.
set -euo pipefail
cd "$(dirname "$0")"

command -v docker >/dev/null 2>&1 || {
  echo "Docker is required. Install Docker Desktop from https://docs.docker.com/get-docker/ and rerun." >&2
  exit 1
}
docker compose version >/dev/null 2>&1 || {
  echo "Docker Compose v2 is required (the 'docker compose' command). Update Docker and rerun." >&2
  exit 1
}
docker info >/dev/null 2>&1 || {
  echo "Docker is installed but not running. Start Docker and rerun." >&2
  exit 1
}

if [ ! -f apps/api/.env ] || ! grep -qE '^(TYPESAFE_API_KEY|AI_GATEWAY_API_KEY)=.+' apps/api/.env; then
  echo "No TYPESAFE_API_KEY or AI_GATEWAY_API_KEY in apps/api/.env: running in mock triage mode."
fi
echo "API   http://localhost:8000/docs"
echo "Board http://localhost:3000"
exec docker compose up --build
