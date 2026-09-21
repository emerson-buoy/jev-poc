#!/usr/bin/env bash
# One command to get the board running from a fresh clone.
#   ./run.sh            install or update everything, then start the API (:8000) and the board (:3000)
#   ./run.sh --check    install or update everything, then run tests, linters, typecheck and build
#   ./run.sh --setup    install or update everything and stop
set -euo pipefail
cd "$(dirname "$0")"

say() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }

need_node() {
  command -v node >/dev/null 2>&1 || {
    echo "Node 20+ is required and was not found. Install it from https://nodejs.org or with your package manager." >&2
    exit 1
  }
  local major; major=$(node -p 'process.versions.node.split(".")[0]')
  [ "$major" -ge 20 ] || { echo "Node $major found, 20 or newer is required." >&2; exit 1; }
}

ensure_pnpm() {
  command -v pnpm >/dev/null 2>&1 && return
  say "pnpm not found, enabling it through corepack"
  if command -v corepack >/dev/null 2>&1; then
    corepack enable && corepack prepare pnpm@latest --activate
  else
    npm install -g pnpm
  fi
}

ensure_uv() {
  command -v uv >/dev/null 2>&1 && return
  echo "uv (Python package manager) is required and was not found."
  read -r -p "Install it now with the official script from astral.sh? [y/N] " answer
  case "$answer" in
    [yY]*) curl -LsSf https://astral.sh/uv/install.sh | sh; export PATH="$HOME/.local/bin:$PATH" ;;
    *) echo "Install uv from https://docs.astral.sh/uv/getting-started/installation/ and rerun." >&2; exit 1 ;;
  esac
  command -v uv >/dev/null 2>&1 || { echo "uv still not on PATH. Open a new shell and rerun." >&2; exit 1; }
}

# A venv breaks silently when the folder is renamed: its scripts keep the old absolute path.
venv_broken() {
  local venv=$1 first path
  [ -d "$venv" ] || return 1
  "$venv/bin/python" -c 'import sys' >/dev/null 2>&1 || return 0
  for script in "$venv"/bin/*; do
    first=$(head -n1 "$script" 2>/dev/null) || continue
    case "$first" in
      '#!/'*) path=${first#\#!}; path=${path%% *}; [ -x "$path" ] || return 0 ;;
    esac
  done
  return 1
}

setup() {
  need_node
  ensure_pnpm
  ensure_uv
  say "JavaScript dependencies"
  pnpm install --frozen-lockfile 2>/dev/null || pnpm install
  say "Python 3.13 and API dependencies"
  if venv_broken apps/api/.venv; then
    say "Existing virtualenv points at a path that no longer exists (moved folder?), recreating it"
    rm -rf apps/api/.venv
  fi
  uv sync --directory apps/api
  say "OpenAPI document and generated client"
  pnpm --silent export:openapi >/dev/null
  pnpm --silent generate:client >/dev/null
  say "Setup complete"
}

setup

case "${1:-}" in
  --setup) exit 0 ;;
  --check)
    pnpm test
    pnpm lint
    pnpm --filter web build >/dev/null
    pnpm --filter web typecheck
    say "All checks passed"
    exit 0 ;;
esac

if [ ! -f apps/api/.env ] || ! grep -qE '^(TYPESAFE_API_KEY|AI_GATEWAY_API_KEY)=.+' apps/api/.env; then
  echo "No TYPESAFE_API_KEY or AI_GATEWAY_API_KEY in apps/api/.env: running in mock triage mode."
fi
echo "API   http://localhost:8000/docs"
echo "Board http://localhost:3000"
exec pnpm dev
