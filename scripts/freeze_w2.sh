#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

run_backend_tests() {
  (
    cd "$BACKEND_DIR"
    source .venv/bin/activate
    pytest tests/ -q
  )
}

run_frontend_checks() {
  (
    cd "$FRONTEND_DIR"
    npx tsc --noEmit
    npx vitest run
    npm run build
  )
}

main() {
  run_backend_tests
  run_frontend_checks
  echo 'frozen ok'
}

main "$@"
