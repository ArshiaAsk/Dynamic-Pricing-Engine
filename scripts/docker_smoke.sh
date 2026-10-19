#!/usr/bin/env bash
#
# scripts/docker_smoke.sh — the GitHub Actions `docker` job (ROADMAP R27 / D31).
#
# Builds the main image, starts the stack through docker compose and verifies:
#   * http://localhost:8000/v1/health returns 200 with "loaded": true
#   * the pricing-api process uid is not 0
#   * the Docker HEALTHCHECK reports "healthy"
#   * http://localhost:5000/health answers (the mlflow service)
#
# Every wait is bounded and a failure prints the failing service logs before
# exiting non-zero. A trap always runs `docker compose down -v`, so a failure
# never leaves containers or volumes behind.
#
# Environment:
#   IMAGE                 image tag (default: dynamic-pricing:ci)
#   HEALTH_URL            API health endpoint (default: http://localhost:8000/v1/health)
#   MLFLOW_HEALTH_URL     MLflow health endpoint (default: http://localhost:5000/health)
#   MAX_WAIT_SECONDS      API health wait (default: 120)
#   HEALTH_STATUS_WAIT    Docker HEALTHCHECK wait (default: 120)
#   MLFLOW_WAIT_SECONDS   MLflow health wait (default: 240)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

IMAGE="${IMAGE:-dynamic-pricing:ci}"
HEALTH_URL="${HEALTH_URL:-http://localhost:8000/v1/health}"
MLFLOW_HEALTH_URL="${MLFLOW_HEALTH_URL:-http://localhost:5000/health}"
MAX_WAIT_SECONDS="${MAX_WAIT_SECONDS:-120}"
HEALTH_STATUS_WAIT="${HEALTH_STATUS_WAIT:-120}"
MLFLOW_WAIT_SECONDS="${MLFLOW_WAIT_SECONDS:-240}"

WORK="$(mktemp -d)"

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; exit 1; }

cleanup() {
  echo "== docker compose down -v"
  docker compose down -v >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT

show_logs() {
  local service="$1"
  echo "== docker compose logs --tail=80 $service"
  docker compose logs --tail=80 "$service" || true
}

run_step() {
  local name="$1"
  shift
  echo "== $name"
  if "$@"; then pass "$name"; else
    show_logs pricing-api
    fail "$name"
  fi
}

run_service_step() {
  local name="$1"
  local service="$2"
  shift 2
  echo "== $name"
  if "$@"; then pass "$name"; else
    show_logs "$service"
    fail "$name"
  fi
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
    code="$(curl -s -o "$WORK/health.json" -w "%{http_code}" "$HEALTH_URL" || true)"
    if [ "$code" = "200" ] && grep -Eq "\"loaded\"[[:space:]]*:[[:space:]]*true" "$WORK/health.json"; then
      echo "  health: $(cat "$WORK/health.json")"
      return 0
    fi
    sleep 1
  done
  echo "  last HTTP code: ${code:-none}"
  echo "  last body: $(cat "$WORK/health.json" 2>/dev/null || echo "<none>")"
  return 1
}

check_non_root() {
  local uid
  uid="$(docker compose exec -T pricing-api id -u 2>/dev/null | tr -d "[:space:]" || true)"
  echo "  pricing-api uid: ${uid:-<empty>}"
  [ -n "$uid" ] && [ "$uid" != "0" ]
}

wait_for_container_health() {
  local deadline=$((SECONDS + HEALTH_STATUS_WAIT))
  local status=""
  while [ "$SECONDS" -lt "$deadline" ]; do
    status="$(docker inspect --format "{{.State.Health.Status}}" "$(docker compose ps -q pricing-api)" 2>/dev/null || true)"
    echo "  health status: ${status:-<none>}"
    if [ "$status" = "healthy" ]; then
      return 0
    fi
    sleep 2
  done
  echo "  last health status: ${status:-none}"
  return 1
}

wait_for_mlflow() {
  local deadline=$((SECONDS + MLFLOW_WAIT_SECONDS))
  while [ "$SECONDS" -lt "$deadline" ]; do
    if curl -sf "$MLFLOW_HEALTH_URL" >/dev/null; then
      echo "  mlflow health: $MLFLOW_HEALTH_URL OK"
      return 0
    fi
    sleep 2
  done
  return 1
}

run_step "docker build -f Dockerfile -t $IMAGE ." build_image
run_step "docker compose up -d pricing-api" compose_up
run_step "health check (max ${MAX_WAIT_SECONDS}s, 200 + loaded:true)" wait_for_health
run_service_step "non-root uid (must not be 0)" pricing-api check_non_root
run_service_step "Docker health status is healthy (max ${HEALTH_STATUS_WAIT}s)" pricing-api wait_for_container_health
run_service_step "mlflow /health (max ${MLFLOW_WAIT_SECONDS}s)" mlflow wait_for_mlflow

echo "docker_smoke.sh: all steps PASS"
