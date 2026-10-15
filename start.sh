#!/bin/bash
set -e

# Health-wait configuration. Overridable so the bounded-loop behavior can be
# exercised without real services (ROADMAP R26 / CONVENTIONS rule 31).
MLFLOW_HEALTH_URL="${MLFLOW_HEALTH_URL:-http://localhost:5000/health}"
API_HEALTH_URL="${API_HEALTH_URL:-http://localhost:8000/v1/health}"
HEALTH_MAX_ATTEMPTS="${HEALTH_MAX_ATTEMPTS:-60}"
HEALTH_RETRY_INTERVAL="${HEALTH_RETRY_INTERVAL:-2}"

# Wait for a URL to answer with 2xx, up to a bounded number of attempts. Exits
# non-zero with a clear message when the dependency never becomes healthy,
# instead of waiting forever.
wait_for_health() {
  local name="$1"
  local url="$2"
  local attempt=0

  echo "Waiting for ${name} at ${url} (up to ${HEALTH_MAX_ATTEMPTS} attempts)..."
  while [ "${attempt}" -lt "${HEALTH_MAX_ATTEMPTS}" ]; do
    if curl -sf "${url}" > /dev/null 2>&1; then
      echo "${name} is up."
      return 0
    fi
    attempt=$((attempt + 1))
    sleep "${HEALTH_RETRY_INTERVAL}"
  done

  echo "ERROR: ${name} did not become healthy at ${url} after ${HEALTH_MAX_ATTEMPTS} attempts; giving up." >&2
  return 1
}

# 1. Start MLflow server in background
mlflow server \
  --backend-store-uri sqlite:///mlflow.db \
  --default-artifact-root ./mlruns \
  --host 0.0.0.0 \
  --port 5000 &
wait_for_health "MLflow" "${MLFLOW_HEALTH_URL}" || exit 1

# 2. Start uvicorn in background
uvicorn src.api.server:app --reload --host 0.0.0.0 --port 8000 &
wait_for_health "uvicorn" "${API_HEALTH_URL}" || exit 1

# 3. Start Streamlit in foreground (keeps container alive)
streamlit run app.py --server.port 7860
