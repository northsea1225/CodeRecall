#!/usr/bin/env bash
# Regenerate docs/openapi.json from FastAPI's live OpenAPI schema.
#
# Run from anywhere; resolves repo root from script location. Writes to
# docs/openapi.json. Run before opening a PR that touches backend routes /
# schemas; the openapi-sync GitHub Actions workflow will block PRs whose
# checked-in JSON drifts from the regenerated output.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT/backend"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "error: backend/.venv not found. Set up the venv first (see docs/release-runbook.md)" >&2
  exit 1
fi

APP_ENV=test .venv/bin/python -c "
import json
from app.main import app
print(json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False))
" > "$REPO_ROOT/docs/openapi.json"

LINES=$(wc -l < "$REPO_ROOT/docs/openapi.json")
echo "wrote docs/openapi.json (${LINES} lines)"
