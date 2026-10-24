# Operations

This is the runbook for the current state of the repository. All data is **synthetic**.
Commands are written for a POSIX shell from the repository root.

## Prerequisites

- Python 3.12.
- A virtual environment with the pinned dependencies:
  ```bash
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```
- No database or MLflow server is required for the local API. The model artifact is
  local and MLflow is optional.
- Docker is only needed for the container workflow.

## Build data and model

A fresh clone has no data and no model; both are gitignored.

```bash
# 18,250 raw rows -> 16,500 feature rows
python scripts/regenerate_data.py

# writes models/demand_model.pkl, models/features.json, reports/
python -m src.training.train
```

The training command must be run in module form (`python -m ...`); the data
script inserts the repository root itself. Running `python src/training/train.py`
fails with `ModuleNotFoundError: No module named 'src'` because the repository
root is not on `sys.path`; see Troubleshooting.

The dataset size and seed are in `configs/config.yaml` under `data`
(`n_products: 50`, `days: 365`, `seed: 42`). The seed-42 run produces R² 0.4193,
MAPE 0.3509, MAE 22.70 and RMSE 30.97 on the synthetic validation split.

Optional hyperparameter tuning (requires a reachable MLflow tracking server, because the
script logs the run and registers the model):

```bash
MLFLOW_TRACKING_URI=http://localhost:5000 python scripts/train_with_tuning.py
```

`TUNING_TRIALS` overrides `training.tuning_trials` (50).

## Run the API

```bash
# Module form: reads API_HOST, API_PORT, API_WORKERS, API_RELOAD
python -m src.api.server

# Development form with auto-reload (API_WORKERS is not used here)
uvicorn src.api.server:app --reload --host 0.0.0.0 --port 8000
```

The module form passes `API_WORKERS` to uvicorn; the `uvicorn` command form runs one
worker unless you pass `--workers`.

Interactive documentation is at `http://localhost:8000/docs` and
`http://localhost:8000/redoc`.

## API examples

```bash
# Health, readiness, liveness and metrics
curl http://localhost:8000/v1/health
curl http://localhost:8000/v1/health/ready
curl http://localhost:8000/v1/health/live
curl http://localhost:8000/v1/metrics
```

```bash
curl -X POST "http://localhost:8000/v1/optimize-price" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 42,
    "competitor_price": 2500000.0,
    "dow": 2,
    "is_weekend": 0,
    "week": 15,
    "month": 4,
    "sin_annual": 0.5,
    "cos_annual": 0.866,
    "lag_units_sold_1": 92.0,
    "lag_units_sold_7": 92.0,
    "lag_units_sold_14": 93.0,
    "roll_mean_units_7": 96.4,
    "roll_mean_units_14": 96.9,
    "roll_mean_units_28": 96.9,
    "roll_std_units_7": 37.4,
    "roll_std_units_14": 38.5,
    "roll_std_units_28": 39.2,
    "price_min": 2300000.0,
    "price_max": 2700000.0,
    "cost": 2250000.0,
    "min_margin_pct": 0.15,
    "inventory_limit": 100,
    "optimization_method": "grid_search"
  }'
```

Verified response with the seed-42 artifact:

```json
{
  "optimal_price": 2625159.38,
  "expected_demand": 86.31,
  "expected_revenue": 226564781.23,
  "optimization_method": "grid_search",
  "profit_margin": 0.1429,
  "profit_per_unit": 375159.38,
  "total_profit": 32378187.22
}
```

`product_id` is accepted for compatibility and logging only. It is not a model feature
and does not change the recommendation. `optimization_method` accepts
`grid_search` or `grid`; the legacy value `bayesian` is rejected with HTTP 422.

## Streamlit UI

```bash
streamlit run app.py
```

`.streamlit/config.toml` sets port 7860, headless mode and a light theme. The UI has four
tabs: Quick (a single recommendation), Advanced (request and response inspection), Batch
(one request per row of an uploaded CSV) and About. The API URL is configurable in the
sidebar.

## Tests, coverage and CI scripts

```bash
# Full suite (offline; no server or Docker build required)
pytest tests -q

# Coverage for the served packages
pytest tests --cov=src/pricing --cov=src/api --cov-report=term-missing

# The whole CI test job, including data/model build, coverage gates,
# zero-skip gate and the README quickstart
PYTHON=$(pwd)/.venv/bin/python bash scripts/ci_check.sh

# README quickstart alone (exports HEAD to a temporary directory)
PYTHON=$(pwd)/.venv/bin/python bash scripts/verify_readme.sh

# Per-file coverage gate (needs the JSON report from pytest-cov)
python scripts/check_coverage.py coverage.json
```

`scripts/ci_check.sh` fails on any skipped test. `tests/smoke_tests.py` is not collected
by `pytest tests` (its filename does not match `test_*.py`); it is run explicitly by
`scripts/verify_readme.sh` against a live API, and skips when no API is reachable.

## Docker Compose

**Everything in this section is a static check only; verified by the CI docker job.**
The commands below were not executed while writing this document.

```bash
docker compose up -d
docker compose ps
docker compose logs -f pricing-api
docker compose down
```

The stack has three services: `pricing-api` on port 8000, `mlflow` on port 5000 and
`mlflow-db` (Postgres 15). The main image builds its own data and model, runs as the
non-root `appuser` (uid 1000) and defines a healthcheck on `/v1/health`. `configs/` is
mounted read-only; logs live in the `app_logs` named volume.

To run only the API image:

```bash
docker build -f Dockerfile -t dynamic-pricing:local .
docker run --rm -p 8000:8000 dynamic-pricing:local
```

## MLflow

MLflow is optional. It has two roles:

- **Tracking:** `scripts/train_with_tuning.py` logs parameters, metrics, the model and
  artifacts to `MLFLOW_TRACKING_URI` (default `http://localhost:5000`).
- **Registry:** `src/pricing/engine.py` looks up the `production` alias (then a
  `stage=Production` tag) of `demand_forecasting_model`. Only an explicitly promoted
  version is served.

`scripts/promote_model.py` uses alias APIs and defaults to a local SQLite store,
`sqlite:///<repo>/mlflow.db`, when `MLFLOW_TRACKING_URI` is unset. MLflow 3 refuses a
filesystem store unless `MLFLOW_ALLOW_FILE_STORE` is set; this repository never sets it.

A local registry workflow:

```bash
export MLFLOW_TRACKING_URI="sqlite:///$(pwd)/mlflow.db"
python scripts/train_with_tuning.py     # registers demand_forecasting_model
python scripts/promote_model.py         # points the production alias at the newest version
python -m src.api.server                # same MLFLOW_TRACKING_URI -> registry model is served
```

With no promoted version, or with an unreachable tracking server, the engine logs an ERROR
and serves `models/demand_model.pkl`. `/v1/health` reports
`checks.model.source` as `"local"`.

## Environment variables

These are the variables read by the application and the tuning script. The defaults are
the code defaults; where `.env.example` ships a different value, the Default cell says so.

| Name | Default | Effect | Read by |
|---|---|---|---|
| `API_HOST` | `0.0.0.0` | Bind address for the module form. | `src/api/server.py` |
| `API_PORT` | `8000` | Bind port for the module form. | `src/api/server.py` |
| `API_WORKERS` | `1` (example ships 4) | Uvicorn worker count for the module form. | `src/api/server.py` |
| `API_RELOAD` | `false` | Auto-reload for the module form. | `src/api/server.py` |
| `CORS_ENABLED` | `true` | Install CORS middleware. | `src/api/server.py` |
| `CORS_ORIGINS` | `*` (example ships two origins) | Comma-separated allowed origins. | `src/api/server.py` |
| `RATE_LIMIT_ENABLED` | `true` | Install the rate-limit middleware. | `src/api/server.py` |
| `RATE_LIMIT_REQUESTS` | `100` | Requests per minute per client IP. | `src/api/server.py` |
| `REQUEST_TIMEOUT` | `30` | Request timeout in seconds. | `src/api/server.py` |
| `LOG_LEVEL` | `INFO` | Root log level. | `src/utils/logger.py` |
| `LOG_FORMAT` | `json` | `json` or text. | `src/utils/logger.py` |
| `LOG_DIR` | `logs` | Directory for `app.log`. | `src/utils/logger.py` |
| `LOG_ROTATION` | `none` (example ships `daily`) | `size`, `daily` or `none`. | `src/utils/logger.py` |
| `LOG_MAX_BYTES` | `10485760` | Size threshold for `size` rotation. | `src/utils/logger.py` |
| `LOG_BACKUP_COUNT` | `5` (example ships 30) | Rotated files kept. | `src/utils/logger.py` |
| `MLFLOW_TRACKING_URI` | `http://localhost:5000` in the engine; `sqlite:///<repo>/mlflow.db` in `scripts/promote_model.py` | Tracking and registry location. | `src/pricing/engine.py`, `scripts/promote_model.py` |
| `TUNING_TRIALS` | `50` | Optuna trials. | `scripts/train_with_tuning.py` |

`MLFLOW_HTTP_REQUEST_TIMEOUT` (5 seconds) and `MLFLOW_HTTP_REQUEST_MAX_RETRIES` (1) are
set with `setdefault` by the engine if the caller has not set them; they are not part of
`.env.example`.

## Logs and health endpoints

- `logs/app.log`: JSON or text application log, rotated according to `LOG_ROTATION`.
- `logs/predictions/predictions_YYYYMMDD_HH.jsonl`: one JSON object per optimization or
  error, with `request_id`, input, result and response time.
- `GET /v1/health`: model probe plus CPU, memory and disk; 503 when degraded.
- `GET /v1/health/ready`: 503 until a model is loaded.
- `GET /v1/health/live`: 200 while the process runs.
- `GET /v1/metrics`: request/error counters and prediction-log statistics.

## Troubleshooting

These are problems that actually occurred in this project.

### `ModuleNotFoundError: No module named 'src'`

Running `python src/training/train.py` (or `python src/api/server.py`) fails because the
repository root is not on `sys.path`. Use the module form:

```bash
python -m src.training.train
python -m src.api.server
```

### Missing model on a fresh clone

Importing the API raises `FileNotFoundError: models/demand_model.pkl` because the model
is gitignored. Build it first:

```bash
python scripts/regenerate_data.py
python -m src.training.train
```

### The legacy method name is rejected

`optimization_method: "bayesian"` returns HTTP 422. Use `grid_search` (or `grid`).

### MLflow container exits with `No module named 'psycopg'`

SQLAlchemy 2.1 resolves a bare `postgresql://` URI to the psycopg 3 dialect, but the image
installs psycopg2. The fix, in place since commit `0aeb1be`, is the explicit
`postgresql+psycopg2://` URI and the `psycopg2-binary==2.9.13` pin. Static check only;
verified by the CI docker job.

### MLflow registry unreachable

The engine bounds registry calls to 5 seconds with one retry, logs an ERROR and serves the
local pickle. Check `/v1/health`; `checks.model.source == "local"` is expected when no
version has been promoted.

### HTTP 429

The in-memory limiter allows 100 requests per minute per client IP. Wait for the window to
pass or raise `RATE_LIMIT_REQUESTS`. The limit is per worker process.

### The virtual environment does not match `requirements.txt`

A stale environment (for example, plain `xgboost` instead of `xgboost-cpu`) can install
conflicting wheels. Rebuild it from the pinned file:

```bash
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## What CI runs

`.github/workflows/ci.yml`:

- **test:** `pip install -r requirements.txt`, then `bash scripts/ci_check.sh` — build
  data and model, full suite with coverage, combined and per-file 80% gates, zero-skip
  gate, README quickstart.
- **docker:** `bash scripts/docker_smoke.sh` — build the image, start the stack, check
  API health, non-root uid, Docker health status and MLflow health.

Everything in the docker job is a static check only in the local suite; the job itself is
the verification.
