#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
PYTHON_BIN="$BACKEND_DIR/.venv/bin/python"
TMP_DIR="$(mktemp -d)"
DB_PATH="$TMP_DIR/manual-smoke.db"
export DATABASE_URL="sqlite:///$DB_PATH"
PORT="$("$PYTHON_BIN" -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
BASE_URL="http://127.0.0.1:$PORT"
SERVER_PID=""
PASS_COUNT=0
FAIL_COUNT=0

cleanup() {
  if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  rm -rf "$TMP_DIR"
}

trap cleanup EXIT

record_pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  printf '[PASS] %s\n' "$1"
}

record_fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  printf '[FAIL] %s\n' "$1"
  exit 1
}

assert_status() {
  local label="$1"
  local expected="$2"
  local actual="$3"
  if [[ "$actual" != "$expected" ]]; then
    record_fail "$label expected HTTP $expected got $actual"
  fi
}

run_json_request() {
  local method="$1"
  local path="$2"
  local body="${3:-}"
  local body_file="$TMP_DIR/body.$RANDOM.json"
  local status

  if [[ -n "$body" ]]; then
    status="$(curl -sS -o "$body_file" -w '%{http_code}' -X "$method" "$BASE_URL$path" -H 'Content-Type: application/json' -d "$body")"
  else
    status="$(curl -sS -o "$body_file" -w '%{http_code}' -X "$method" "$BASE_URL$path")"
  fi

  printf '%s\n%s\n' "$status" "$body_file"
}

split_result() {
  local result="$1"
  REQUEST_STATUS="${result%%$'\n'*}"
  REQUEST_BODY_FILE="${result#*$'\n'}"
}

json_eval() {
  local file="$1"
  local expression="$2"
  "$PYTHON_BIN" - "$file" "$expression" <<'PY'
import json
import sys

path = sys.argv[1]
expression = sys.argv[2]
with open(path, "r", encoding="utf-8") as handle:
    data = json.load(handle)

result = eval(expression, {"__builtins__": {}}, {"data": data})
if isinstance(result, bool):
    print("True" if result else "False")
    raise SystemExit(0 if result else 1)
print(result)
PY
}

printf '== Manual Smoke ==\n'
printf 'Root: %s\n' "$ROOT_DIR"
printf 'Database: %s\n' "$DATABASE_URL"
printf 'Port: %s\n' "$PORT"

(
  cd "$BACKEND_DIR"
  "$PYTHON_BIN" -m alembic upgrade head
)
record_pass "alembic upgrade head"

"$PYTHON_BIN" "$ROOT_DIR/scripts/seed_demo_data.py"
record_pass "seed demo data"

(
  cd "$BACKEND_DIR"
  PYTHONPATH="$BACKEND_DIR${PYTHONPATH:+:$PYTHONPATH}" \
    "$PYTHON_BIN" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" >"$TMP_DIR/uvicorn.log" 2>&1
) &
SERVER_PID="$!"

"$PYTHON_BIN" - "$BASE_URL" <<'PY'
import json
import sys
import time
from urllib.request import urlopen

base_url = sys.argv[1]
deadline = time.time() + 15
last_error = None
while time.time() < deadline:
    try:
        with urlopen(f"{base_url}/health", timeout=2) as response:
            payload = json.load(response)
        if payload.get("status") == "ok":
            raise SystemExit(0)
    except Exception as exc:  # noqa: BLE001
        last_error = exc
        time.sleep(0.2)
raise SystemExit(f"server not ready: {last_error}")
PY
record_pass "uvicorn start"

split_result "$(run_json_request GET "/health")"
assert_status "GET /health" "200" "$REQUEST_STATUS"
json_eval "$REQUEST_BODY_FILE" "data['status'] == 'ok'" >/dev/null
record_pass "GET /health"

split_result "$(run_json_request GET "/api/v1/mistakes?keyword=python")"
assert_status "GET /mistakes?keyword=python" "200" "$REQUEST_STATUS"
json_eval "$REQUEST_BODY_FILE" "data['total'] >= 1" >/dev/null
record_pass "GET /mistakes?keyword=python"

split_result "$(run_json_request POST "/api/v1/review/sessions" '{"strategy":"random","limit":3}')"
assert_status "POST /review/sessions random" "201" "$REQUEST_STATUS"
RANDOM_SESSION_ID="$(json_eval "$REQUEST_BODY_FILE" "data['id']")"
json_eval "$REQUEST_BODY_FILE" "data['total_count'] == 3" >/dev/null
record_pass "POST /review/sessions random"

split_result "$(run_json_request GET "/api/v1/review/sessions/$RANDOM_SESSION_ID/next")"
assert_status "GET /review/sessions/{id}/next" "200" "$REQUEST_STATUS"
NEXT_MISTAKE_ID="$(json_eval "$REQUEST_BODY_FILE" "data['next_item']['mistake_id']")"
json_eval "$REQUEST_BODY_FILE" "data['progress']['total'] == 3" >/dev/null
record_pass "GET /review/sessions/{id}/next"

SUBMIT_PAYLOAD="$(printf '{"mistake_id":%s,"user_result":"good"}' "$NEXT_MISTAKE_ID")"
split_result "$(run_json_request POST "/api/v1/review/sessions/$RANDOM_SESSION_ID/submit" "$SUBMIT_PAYLOAD")"
assert_status "POST /review/sessions/{id}/submit" "200" "$REQUEST_STATUS"
json_eval "$REQUEST_BODY_FILE" "data['mistake_id'] == $NEXT_MISTAKE_ID and data['user_result'] == 'good'" >/dev/null
record_pass "POST /review/sessions/{id}/submit"

split_result "$(run_json_request POST "/api/v1/review/sessions" '{"strategy":"spaced_repetition","limit":2}')"
assert_status "POST /review/sessions spaced_repetition" "201" "$REQUEST_STATUS"
json_eval "$REQUEST_BODY_FILE" "data['total_count'] >= 1" >/dev/null
record_pass "POST /review/sessions spaced_repetition"

split_result "$(run_json_request GET "/api/v1/review/capability")"
assert_status "GET /review/capability" "200" "$REQUEST_STATUS"
AI_ENABLED="$(json_eval "$REQUEST_BODY_FILE" "data['ai_analysis_enabled']")"
record_pass "GET /review/capability"

if [[ "$AI_ENABLED" != "True" ]]; then
  record_fail "AI capability is disabled; expected enabled=true for real SSE smoke"
fi

AI_STATUS="$(curl -sS -N --max-time 10 -o "$TMP_DIR/ai-stream.txt" -w '%{http_code}' "$BASE_URL/api/v1/ai/analyze/stream?mistake_id=1")"
assert_status "GET /ai/analyze/stream?mistake_id=1" "200" "$AI_STATUS"
grep -q '^data:' "$TMP_DIR/ai-stream.txt" || record_fail "AI SSE stream did not emit any data chunks"
head -n 5 "$TMP_DIR/ai-stream.txt" >"$TMP_DIR/ai-stream-head.txt"
record_pass "GET /ai/analyze/stream?mistake_id=1"

if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
  SERVER_PID=""
fi
record_pass "uvicorn stop"

printf '\n== Smoke Summary ==\n'
printf 'passes=%s failures=%s\n' "$PASS_COUNT" "$FAIL_COUNT"
printf 'random_session_id=%s\n' "$RANDOM_SESSION_ID"
printf 'submitted_mistake_id=%s\n' "$NEXT_MISTAKE_ID"
printf 'ai_enabled=%s\n' "$AI_ENABLED"
printf 'ai_stream_head:\n'
cat "$TMP_DIR/ai-stream-head.txt"
