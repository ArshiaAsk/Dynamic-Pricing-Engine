#!/usr/bin/env bash
#
# scripts/verify_readme.sh — run the README quickstart end to end (ROADMAP R23).
#
# R23's acceptance criterion: "Every command in README runs successfully on a
# clean checkout (captured by scripts/verify_readme.sh, exit 0)". This script
# executes the README's local quickstart against a throwaway checkout of HEAD
# (never the working tree), so the README cannot drift from what actually runs:
#
#   python scripts/regenerate_data.py
#   python -m src.training.train
#   python -m src.api.server
#   <the README API curls>
#   pytest tests -q
#   pytest tests/smoke_tests.py
#   python -m py_compile app.py
#
# Every step prints one PASS/FAIL line; the script stops (exit non-zero) at the
# first failure. A trap always kills the API server and removes the temp dir.
#
# Usage:
#   scripts/verify_readme.sh [--with-pip]
#
#   --with-pip  also create a venv inside the temp dir and run
#               `pip install -r requirements.txt` before the quickstart.
#               NOT run by default (it needs the network).
#
# Environment:
#   PYTHON       interpreter to use (default: python3)
#   VERIFY_PORT  API port to bind on 127.0.0.1 (default: 8765)

set -euo pipefail

WITH_PIP=0
for arg in "$@"; do
  case "$arg" in
    --with-pip) WITH_PIP=1 ;;
    -h|--help) sed -n '2,32p' "$0"; exit 0 ;;
    *) echo "verify_readme.sh: unknown option: $arg" >&2; exit 2 ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PYTHON="${PYTHON:-python3}"
VERIFY_PORT="${VERIFY_PORT:-8765}"
BASE_URL="http://127.0.0.1:${VERIFY_PORT}"

WORK="$(mktemp -d)"
SERVER_PID=""

cleanup() {
  set +e
  if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null
    wait "$SERVER_PID" 2>/dev/null
  fi
  rm -rf "$WORK"
}
trap cleanup EXIT

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; exit 1; }

# Run a command in the throwaway checkout; print PASS/FAIL and stop on failure.
run_step() {
  local name="$1"; shift
  if "$@"; then pass "$name"; else fail "$name"; fi
}

echo "verify_readme.sh: repo=$REPO_ROOT python=$PYTHON port=$VERIFY_PORT"

# 1. Clone HEAD into a temp dir (tracked files only) and work there.
if git -C "$REPO_ROOT" archive HEAD | tar -x -C "$WORK"; then
  pass "git archive HEAD -> temp checkout"
else
  fail "git archive HEAD -> temp checkout"
fi
cd "$WORK"

# 2. Optional: build a venv and install the pinned requirements (needs network).
if [ "$WITH_PIP" = "1" ]; then
  run_step "python -m venv (--with-pip)" "$PYTHON" -m venv "$WORK/venv"
  run_step "pip install -r requirements.txt (--with-pip)" \
    "$WORK/venv/bin/pip" install -r requirements.txt
  PYTHON="$WORK/venv/bin/python"
fi

# 3. README quickstart: data generation.
run_step "python scripts/regenerate_data.py" "$PYTHON" scripts/regenerate_data.py

# 4. README quickstart: training.
run_step "python -m src.training.train" "$PYTHON" -m src.training.train

# 5. Start the API in the background (module form) on 127.0.0.1.
API_HOST=127.0.0.1 API_PORT="$VERIFY_PORT" API_WORKERS=1 API_RELOAD=false \
  MLFLOW_TRACKING_URI="sqlite:///$WORK/mlflow.db" \
  "$PYTHON" -m src.api.server > "$WORK/api.log" 2>&1 &
SERVER_PID=$!

wait_for_health() {
  local i
  for i in $(seq 1 60); do
    if curl -sf "$BASE_URL/v1/health" > /dev/null 2>&1; then
      return 0
    fi
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
      echo "  server exited early; last log lines:" >&2
      tail -n 20 "$WORK/api.log" >&2 || true
      return 1
    fi
    sleep 1
  done
  return 1
}
run_step "python -m src.api.server (bounded wait for /v1/health, max 60 s)" \
  wait_for_health

# 6. Every curl example in the README's API section.
check_status() {
  local name="$1" expected="$2" url="$3" code
  code="$(curl -s -o /dev/null -w '%{http_code}' "$url")" || code="000"
  if [ "$code" = "$expected" ]; then
    pass "$name (HTTP $code)"
  else
    fail "$name (expected HTTP $expected, got $code)"
  fi
}

check_status "curl /v1/health" 200 "$BASE_URL/v1/health"
check_status "curl /v1/health/ready" 200 "$BASE_URL/v1/health/ready"
check_status "curl /v1/health/live" 200 "$BASE_URL/v1/health/live"
check_status "curl /v1/metrics" 200 "$BASE_URL/v1/metrics"

OPTIMIZE_PAYLOAD='{
  "product_id": 42,
  "competitor_price": 89.99,
  "dow": 2,
  "is_weekend": 0,
  "week": 15,
  "month": 4,
  "sin_annual": 0.5,
  "cos_annual": 0.866,
  "lag_units_sold_1": 45.0,
  "lag_units_sold_7": 42.0,
  "lag_units_sold_14": 40.0,
  "roll_mean_units_7": 43.5,
  "roll_mean_units_14": 41.2,
  "roll_mean_units_28": 39.8,
  "roll_std_units_7": 5.2,
  "roll_std_units_14": 6.1,
  "roll_std_units_28": 7.3,
  "price_min": 70.0,
  "price_max": 110.0,
  "cost": 60.0,
  "min_margin_pct": 0.15,
  "inventory_limit": 100,
  "optimization_method": "grid_search"
}'

check_optimize() {
  local code
  code="$(curl -s -o "$WORK/optimize.json" -w '%{http_code}' \
    -X POST "$BASE_URL/v1/optimize-price" \
    -H 'Content-Type: application/json' \
    -d "$OPTIMIZE_PAYLOAD")" || code="000"
  [ "$code" = "200" ] || { echo "  (HTTP $code)" >&2; return 1; }
  "$PYTHON" - "$WORK/optimize.json" <<'PY'
import json
import sys

with open(sys.argv[1]) as fh:
    body = json.load(fh)
assert "optimal_price" in body, f"response is missing optimal_price: {body}"
method = body.get("optimization_method")
assert method == "grid_search", f"unexpected optimization_method: {method!r}"
PY
}
run_step "curl POST /v1/optimize-price (optimal_price + grid_search)" check_optimize

# 7. README tests: the suite, then the smoke tests against the live server.
run_step "pytest tests -q" "$PYTHON" -m pytest tests -q
run_step "API_URL=$BASE_URL pytest tests/smoke_tests.py" \
  env "API_URL=$BASE_URL" "$PYTHON" -m pytest tests/smoke_tests.py

# 8. README: the Streamlit app compiles.
run_step "python -m py_compile app.py" "$PYTHON" -m py_compile app.py

echo "verify_readme.sh: all steps PASS"
