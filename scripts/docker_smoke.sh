#!/usr/bin/env bash
#
# scripts/docker_smoke.sh — the GitHub Actions `docker` job (ROADMAP R27 / D18).
#
# Builds the main image, starts the API through docker compose and waits (max
# 120 s) for http://localhost:8000/v1/health to return 200 with "loaded": true.
# A trap always runs `docker compose down -v`, so a failure never leaves
# containers or volumes behind. Every step prints PASS/FAIL and the script exits
# non-zero at the first failure.
#
# Environment:
#   IMAGE              image tag (default: dynamic-pricing:ci)
#   HEALTH_URL         health endpoint (default: http://localhost:8000/v1/health)
#   MAX_WAIT_SECONDS   bounded wait (default: 120)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

IMAGE="${IMAGE:-dynamic-pricing:ci}"
HEALTH_URL="${HEALTH_URL:-http://localhost:8000/v1/health}"
MAX_WAIT_SECONDS="${MAX_WAIT_SECONDS:-120}"

WORK="$(mktemp -d)"

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; exit 1; }

cleanup() {
  echo "== docker compose down -v"
  docker compose down -v >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT

run_step() {
  local name="$1"
  shift
  echo "== $name"
  if "$@"; then pass "$name"; else fail "$name"; fi
}

echo "docker_smoke.sh: repo=$REPO_ROOT image=$IMAGE url=$HEALTH_URL"

build_image() {
  docker build -f Dockerfile -t "$IMAGE" .
}

compose_up() {
  docker compose up -d pricing-api
}

wait_for_health() {
  local deadline=$((SECONDS + MAX_WAIT_SECONDS))
  local code=""
  while [ "$SECONDS" -lt "$deadline" ]; do
    code="$(curl -s -o "$WORK/health.json" -w '%{http_code}' "$HEALTH_URL" || true)"
    if [ "$code" = "200" ] && grep -Eq '"loaded"[[:space:]]*:[[:space:]]*true' "$WORK/health.json"; then
      echo "  health: $(cat "$WORK/health.json")"
      return 0
    fi
    sleep 1
  done
  echo "  last HTTP code: ${code:-none}"
  echo "  last body: $(cat "$WORK/health.json" 2>/dev/null || echo "<none>")"
  return 1
}

run_step "docker build -f Dockerfile -t $IMAGE ." build_image
run_step "docker compose up -d pricing-api" compose_up
run_step "health check (max ${MAX_WAIT_SECONDS}s, 200 + loaded:true)" wait_for_health

echo "docker_smoke.sh: all steps PASS"
