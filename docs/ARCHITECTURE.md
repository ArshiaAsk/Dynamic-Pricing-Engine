# Architecture

This document describes the current state of the repository. Every statement is backed
by a file, a test, a script or the CI workflow named next to it.

## 1. Scope and status

The Dynamic Pricing Engine is a **demo** that:

- generates synthetic e-commerce sales data;
- builds lag, rolling, calendar and price features;
- trains an XGBoost regressor to predict units sold;
- searches a dense price grid for the price that maximizes expected revenue;
- serves that search through a FastAPI API, with a Streamlit UI on top.

It is **not** a production pricing system. It has no authentication, authorization or
TLS, it does not estimate causal price response, and every number it reports comes from
synthetic data. Those limits are expanded in
[LIMITATIONS_AND_NEXT_STEPS.md](LIMITATIONS_AND_NEXT_STEPS.md).

## 2. Data and request flow

```mermaid
flowchart LR
    CFG[configs/config.yaml] --> GEN[scripts/regenerate_data.py]
    GEN --> RAW[data/raw/ecommerce_sales.csv]
    RAW --> FB[src/features/feature_builder.py]
    FB --> FEAT[data/features/training_features.parquet]
    FEAT --> TRAIN[python -m src.training.train]
    TRAIN --> MODEL[models/demand_model.pkl]
    TRAIN --> FJSON[models/features.json]
    TRAIN --> SUPPORT[models/training_support.json]
    TRAIN --> REPORTS[reports/]
    MODEL --> ENGINE[src/pricing/engine.py]
    FJSON --> ENGINE
    SUPPORT --> ENGINE
    ENGINE --> OPT[src/pricing/optimizer.py]
    OPT --> API[FastAPI src/api/server.py]
    API --> UI[Streamlit app.py]
    ENGINE -. optional registry lookup .-> MLF[MLflow tracking and registry]
    MLF -. promoted production alias, otherwise local fallback .-> ENGINE
    API --> LOGS[logs/app.log and logs/predictions]
```

The generator, the feature builder and the trainer are offline steps. The API loads the
resulting model and feature contract at import time and never trains.

## 3. Components

| Module | Responsibility | Key files | Tests that guard it |
|---|---|---|---|
| Synthetic data | Seeded generation of products, prices, demand and inventory. | `src/data/generator.py`, `scripts/regenerate_data.py` | `tests/test_generator_determinism.py` |
| Features | Calendar, price, lag and rolling features; chronological ordering; no `product_id` feature. | `src/features/feature_builder.py` | `tests/test_training_data.py`, `tests/test_serving_features.py` |
| Training | Load features, chronological split, XGBoost fit, evaluation, artifact writing. | `src/training/pipeline.py`, `src/training/dataset.py`, `src/training/trainer.py`, `src/training/evaluate.py`, `src/training/train.py` | `tests/test_training_data.py`, `tests/test_evaluator.py` |
| Tuning | Optuna TPE study with 3-fold cross-validation. | `src/training/hyperparameter_tuning.py`, `scripts/train_with_tuning.py` | Reachability only (`tests/test_import_graph.py`); the Optuna path has no unit test. |
| Serving features | One builder for the price-dependent features of every candidate price. | `src/pricing/features.py` | `tests/test_serving_features.py`, `tests/test_optimizer_real.py` |
| Optimizer | Adaptive dense price-grid search, margin floor, inventory cap. | `src/pricing/optimizer.py` | `tests/test_optimizer.py`, `tests/test_optimizer_real.py`, `tests/test_api.py` |
| Engine | Model and feature-contract loading, optional MLflow registry, method dispatch. | `src/pricing/engine.py` | `tests/test_mlflow_registry.py`, `tests/test_health_model_type.py` |
| API | Routes, schemas, middleware, error handlers. | `src/api/server.py`, `src/api/router.py`, `src/api/schemas.py`, `src/api/middleware.py`, `src/api/error_handlers.py` | `tests/test_api.py`, `tests/test_api_health_metrics.py`, `tests/test_api_middleware.py`, `tests/test_product_id_contract.py` |
| Monitoring | Health probes, system metrics, JSONL prediction log. | `src/monitoring/health_checker.py`, `src/monitoring/prediction_logger.py` | `tests/test_health_checker.py`, `tests/test_health_model_type.py`, `tests/test_prediction_logger.py`, `tests/test_log_rotation.py` |
| UI | Four Streamlit tabs: Quick, Advanced, Batch, About. | `app.py`, `.streamlit/config.toml` | `tests/test_streamlit_contract.py`, `tests/test_product_id_help.py` |
| Operations | Container images, compose stack, local CI scripts, GitHub Actions. | `Dockerfile`, `Dockerfile.mlflow`, `docker-compose.yml`, `scripts/`, `.github/workflows/ci.yml` | `tests/test_ci_workflow.py`, `tests/test_compose_files.py`, `tests/test_dockerfile_hardening.py`, `tests/test_dockerfile_model_build.py`, `tests/test_repo_hygiene.py`, `tests/test_requirements_pinned.py`, `tests/test_verify_readme_script.py` |
| Documentation | This directory and its link/path guards. | `docs/` | `tests/test_docs.py` |

## 4. Training pipeline

### 4.1 Data generation

`scripts/regenerate_data.py` reads `configs/config.yaml`:

- `data.n_products: 50`
- `data.days: 365`
- `data.seed: 42`

`src/data/generator.py` uses `numpy.random.default_rng(seed)` for every draw, so the
same config produces the same data. The run writes `data/raw/ecommerce_sales.csv` with
18,250 rows (50 products × 365 days) and then builds features into
`data/features/training_features.parquet` with 16,500 rows.

The generator draws each product's base price from 200,000 to 5,000,000 (the generated
file spans roughly 240,000 to 5,930,000) and its elasticity from −2.5 to −0.8. Demand is
a product of base demand, a power price effect, annual seasonality, marketing spend and
a competitor-price advantage, with multiplicative noise of standard deviation 0.08.
Inventory is finite and restocked when it falls below 20.

### 4.2 Features

`src/features/feature_builder.py` builds, per product and date:

- calendar: `dow`, `is_weekend`, `week`, `month`, `sin_annual`, `cos_annual`;
- price: `price`, `competitor_price`, `price_ratio`, `price_diff_pct`,
  `price_advantage`, `log_price`, `log_comp_price`;
- lags: units at 1, 7 and 14 days (price lags feed the price-change features);
- price changes: `price_change_1d`, `price_change_7d`;
- rolling windows 7, 14 and 28: mean and standard deviation of units, mean price;
- interactions: `price_ratio_sin`, `price_ratio_cos`, `price_advantage_sin`.

The target is `y_units_sold`. `product_id` is used to group lag and rolling
computations but is **not** a model feature. After filtering the first 35 days of each
product (`features.min_history_days`), the frame has 30 model features plus `date` and
the target. `models/features.json` is the tracked feature contract and lists the 30
columns in training order.

### 4.3 Split

`src/training/dataset.py` orders rows by `date` and holds out the most recent
`training.test_size` fraction (0.2). The cut is pushed forward to the end of a calendar
day so no date appears in both sets. Nothing is shuffled.

### 4.4 Model and metrics

`src/training/trainer.py` builds `xgboost.XGBRegressor` with the `model` block of
`configs/config.yaml` (600 trees, depth 6, learning rate 0.05, subsample 0.8,
column subsample 0.8, `reg_lambda` 1, `tree_method="hist"`, `random_state=42`).

`src/training/evaluate.py` computes MAE, RMSE, R², MAPE, directional accuracy, bias, mean
prediction and mean actual, plus train metrics and residual statistics. The pipeline
writes:

- `models/demand_model.pkl` (gitignored);
- `models/features.json` (tracked);
- `models/training_support.json` (gitignored): per-feature min/max/median from the
  **train split only**, plus the `price`, `competitor_price` and `price_ratio` ranges
  (`src/training/support.py`, DECISIONS D32);
- `reports/training_metrics.json` (gitignored);
- `reports/feature_importance.csv` (gitignored).

For the configured seed 42, the generated metrics are R² 0.4193, MAPE 0.3509, MAE 22.70,
RMSE 30.97 and directional accuracy 0.734. All of these are measurements on synthetic
data. Across data seeds 1–10 the README records R² 0.447 ± 0.029 and MAPE 0.361 ± 0.011,
so seed-to-seed spread is material.

### 4.5 Hyperparameter tuning

`scripts/train_with_tuning.py` runs `src/training/hyperparameter_tuning.py`: an Optuna
TPE study (`TPESampler(seed=42)`) with `training.tuning_trials` trials (50 by default,
overridable with `TUNING_TRIALS`) and 3-fold cross-validation scored by negative MAE. It
logs parameters, metrics, the model and artifacts to the MLflow tracking URI
(`MLFLOW_TRACKING_URI`, default `http://localhost:5000`) and registers the model as
`demand_forecasting_model`. The plain training path does not use MLflow.

## 5. Serving

### 5.1 Request path

1. `src/api/server.py` builds the FastAPI app, installs CORS, logging, error, rate-limit
   and timeout middleware, and mounts the router under `/v1`.
2. `src/api/router.py` loads `configs/config.yaml` and constructs one `PricingEngine`
   at import time. The engine loads the feature contract, a model and the training
   support.
3. `POST /v1/optimize-price` validates the body with `PricingRequest`.
4. The router removes optimization-only fields, takes the price bounds from the request
   or, when they are omitted, derives them from the observed `price_ratio` support
   around the request's competitor price. There is no absolute price default.
5. The router rejects a request outside the training support with HTTP 422 and fills
   omitted history features with the training medians (section 5.3).
6. The engine dispatches to `PriceOptimizer`, logs the result to the JSONL prediction
   log, records the request in the health checker, and returns `PricingResponse`.

### 5.2 Optimizer

`src/pricing/optimizer.py` evaluates a dense grid of candidate prices. The grid
constants are:

| Constant | Value | Meaning |
|---|---|---|
| `TARGET_RESOLUTION` | 0.02 | Maximum price spacing; the number of points scales with the bound width. |
| `MIN_GRID_POINTS` | 901 | Never fewer candidates than the acceptance reference grid. |
| `MAX_GRID_POINTS` | 20001 | Cap for pathologically wide ranges. |
| `DEFAULT_STEPS` | 50 | Floor for a caller-supplied step count. |

The candidate count is `min(20001, max(901, steps, ceil(span / 0.02) + 1))`. For every
candidate, `src/pricing/features.py` builds the price-dependent features from the
request features and the candidate price; the model predicts demand; revenue is
`price × demand`; the argmax is returned. A degenerate range collapses to one candidate.

Constraints:

- **Margin floor:** with `cost` and `min_margin_pct`, the lower bound becomes
  `max(price_min, cost × (1 + min_margin_pct))`. If that exceeds `price_max`, the
  original `price_min` is used.
- **Inventory cap:** if `inventory_limit` is supplied, demand is capped with
  `min(demand, inventory_limit)` before revenue is computed.

The result also includes `profit_margin`, `profit_per_unit` and `total_profit` when
the constrained path runs.

### 5.3 Training support

Training writes `models/training_support.json` (`src/training/support.py`) from the
**train split only**: `n_rows`, `split: "train"`, a `features` map with
`min`/`max`/`median` for each of the 30 model columns, and the same statistics for
`price`, `competitor_price` and `price_ratio`. `PricingEngine.load_model` loads it from
`pricing.training_support_path` and fails loudly when the file is missing or invalid
(`TrainingSupportError`, like a missing model).

`src/pricing/support.py` turns it into serving rules:

- **Competitor range:** `competitor_price` must lie in the observed competitor range.
- **Price bounds:** `price_min` and `price_max` must lie in
  `[price_ratio.min × competitor_price, price_ratio.max × competitor_price]`. The
  comparison uses the stored values with a 1e-9 relative tolerance, so a bound exactly
  on a limit is accepted.
- **Defaults:** an omitted bound is that same ratio band around the competitor price;
  an omitted history feature (the nine lags and rolling unit statistics) is the
  train-split median.
- **Rejection:** a violation returns HTTP 422 with `error: "outside_training_support"`,
  a message containing the supported ranges, field-level `details` and the
  `request_id`.

`/v1/health` reports `checks.model.training_support` as
`{"loaded": true, "split": "train", "n_rows": 13200}`. The artifact is generated and
gitignored; `.dockerignore` excludes it, so the image builds its own.

The model's price response is identified only inside that support (about ±15% of the
competitor price); a recommendation outside it would be extrapolation. The API also does
not validate calendar features against their training range.

### 5.4 Response contract

`src/api/schemas.py` defines `PricingResponse` with:

`optimal_price`, `expected_demand`, `expected_revenue`, `optimization_method`,
`profit_margin`, `profit_per_unit`, `total_profit`.

A verified call with the README payload returns HTTP 200 and:

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

The engine no longer computes a `model_version`; when a registry model is served, its
version is reported by `/v1/health` as `checks.model.version`.
`product_id` is accepted for compatibility and logging only; it is not a model feature.

### 5.5 Model loading and registry fallback

`src/pricing/engine.py` imports MLflow lazily. On load it:

1. sets a 5-second HTTP timeout and one retry for registry calls;
2. resolves the `production` alias of `demand_forecasting_model`, then falls back to a
   `stage=Production` version tag;
3. loads the registry model if one exists, otherwise logs at ERROR and loads the local
   `models/demand_model.pkl` with joblib;
4. records `model_source` as `"mlflow"` or `"local"` and exposes it on `/v1/health`.

The fallback is never silent: an unreachable registry or a missing promotion produces an
ERROR log and `checks.model.source == "local"`. The local artifact,
`models/features.json` and `models/training_support.json` must exist; otherwise the
engine raises at import time.

### 5.6 Errors, limits and timeouts

- **Validation errors:** HTTP 422 with field-level details and a `request_id`
  (`src/api/error_handlers.py`).
- **Outside the training support:** HTTP 422 with `error: "outside_training_support"`, the
  supported ranges in `message`, field-level `details` and a `request_id`
  (`src/api/router.py`, section 5.3).
- **Unexpected errors:** HTTP 500 with a generic message and `request_id`; the exception
  text is logged server-side and never returned (`src/api/router.py`).
- **Unhandled middleware errors:** HTTP 500 with `error`, `message` and `request_id`.
- **Rate limiting:** in-memory, per client IP, sliding one-minute window, default 100
  requests per minute; returns HTTP 429. The window is per process, so it is not shared
  across workers and resets on restart.
- **Timeout:** a request exceeding `REQUEST_TIMEOUT` seconds returns HTTP 504.
- **Request id:** `RequestLoggingMiddleware` adds `X-Request-ID` to every response.

### 5.7 Health endpoints

| Endpoint | Behaviour |
|---|---|
| `GET /v1/health` | Probes the served model with a DataFrame built from the feature contract, reports CPU, memory and disk, reports whether the training support is loaded (`checks.model.training_support`), and returns 503 when status is not `healthy`. |
| `GET /v1/health/ready` | 200 when a model is loaded, otherwise 503. |
| `GET /v1/health/live` | Always 200 while the process is alive. |
| `GET /v1/metrics` | Health counters plus prediction-log statistics. |

### 5.8 Logging

`src/utils/logger.py` configures the root logger from `LOG_LEVEL`, `LOG_FORMAT`,
`LOG_DIR`, `LOG_ROTATION`, `LOG_MAX_BYTES` and `LOG_BACKUP_COUNT`. `json` produces
one JSON object per line; `size` uses `RotatingFileHandler`, `daily` uses
`TimedRotatingFileHandler` at midnight, and `none` uses a plain `FileHandler`.

`src/monitoring/prediction_logger.py` buffers optimization and error entries and appends
them to `logs/predictions/predictions_YYYYMMDD_HH.jsonl`. Errors flush immediately, and
`atexit` flushes the buffer at interpreter exit.

## 6. Configuration

`configs/config.yaml` is the only YAML configuration file. It has five blocks:

| Block | Keys |
|---|---|
| `data` | `feature_path`, `n_products`, `days`, `seed` |
| `model` | `n_estimators`, `max_depth`, `learning_rate`, `subsample`, `colsample_bytree`, `min_child_weight`, `gamma`, `reg_alpha`, `reg_lambda` |
| `pricing` | `model_path`, `feature_columns_path`, `training_support_path` |
| `training` | `test_size`, `model_dir`, `report_dir`, `run_cv`, `tuning_trials` |
| `features` | `lag_days`, `rolling_windows`, `min_history_days` |

Every key is read by `src/` or `scripts/` code (`tests/test_config.py`). Runtime
toggles are environment variables; the full table is in
[OPERATIONS.md](OPERATIONS.md#environment-variables).

## 7. Containers and CI

**Everything in this section is a static check only; verified by the CI docker job.**
The suite reads the Dockerfiles, the compose file and the workflow as text; it does not
build or start containers.

### 7.1 Main image

`Dockerfile` has two stages:

1. `python:3.12-slim AS builder` installs `requirements.txt` into `/install` with a
   pip cache mount.
2. `python:3.12-slim` creates `appuser` (uid 1000), copies the installed packages,
   copies the sources with `--chown=appuser:appuser`, switches to `appuser`, and runs
   `python scripts/regenerate_data.py && python -m src.training.train` **inside the
   image**. The model is therefore built at image-build time, not mounted from the host.

The runtime stage exposes port 8000, defines a `HEALTHCHECK` against
`http://127.0.0.1:8000/v1/health`, and starts `python -m src.api.server`.
`.dockerignore` excludes `models/*.pkl`, `data/features/`, `.env`, `.git` and the
documentation, so local artifacts and secrets never enter the build context.

### 7.2 MLflow image and compose stack

`Dockerfile.mlflow` pins `mlflow==3.17.1`, `protobuf==4.25.9` and
`psycopg2-binary==2.9.13`, runs as the non-root `mlflow` user, and serves
`postgresql+psycopg2://mlflow:mlflow@mlflow-db:5432/mlflow` with artifacts in
`/mlflow/artifacts`. The explicit `+psycopg2` driver matters: SQLAlchemy 2.1 resolves a
bare `postgresql://` URI to the psycopg 3 dialect, which is not installed.

`docker-compose.yml` defines three services:

| Service | Image / build | Port | Notes |
|---|---|---|---|
| `mlflow-db` | `postgres:15` | — | Named volume `mlflow_db`. |
| `mlflow` | built from `Dockerfile.mlflow` | 5000 | Depends on `mlflow-db`; artifacts in the `mlflow_artifacts` volume. |
| `pricing-api` | built from `Dockerfile` | 8000 | `MLFLOW_TRACKING_URI=http://mlflow:5000`; `configs/` mounted read-only; logs in the `app_logs` volume. |

All services use `restart: unless-stopped`. There is no top-level `version` key.

### 7.3 CI workflow

`.github/workflows/ci.yml` runs on pushes and pull requests to `main`, with
`contents: read` permissions and a concurrency group. It has two jobs:

- **test** (20-minute timeout): installs `requirements.txt` and runs
  `bash scripts/ci_check.sh`.
- **docker** (30-minute timeout, `needs: test`): runs `bash scripts/docker_smoke.sh`.

`scripts/ci_check.sh` performs every gate in order and exits at the first failure:

1. build data and model (`scripts/regenerate_data.py`, then `python -m src.training.train`);
2. `pytest tests` with coverage for `src/pricing` and `src/api`, a combined
   `--cov-fail-under=80`, a JSON coverage report and a JUnit report;
3. `scripts/check_coverage.py`: **every file** under `src/pricing/` and `src/api/` must
   reach 80% line coverage;
4. zero-skipped-tests gate, read from the JUnit report;
5. `scripts/verify_readme.sh`: exports `git archive HEAD` to a temporary directory,
   runs the README quickstart, starts the API on port 8765, checks every README curl,
   runs the suite and the smoke tests, and compiles `app.py`.

`scripts/docker_smoke.sh` builds the main image, starts `pricing-api` through compose,
and checks: HTTP 200 with `"loaded": true` on `/v1/health`, a non-zero uid, the Docker
health status `healthy`, and `/health` on the MLflow service. Every wait is bounded.

## 8. Testing strategy

The suite is offline by default: no network, no Docker build, no running server. It has
four kinds of checks:

| Category | Examples | What it protects |
|---|---|---|
| Behavioural | `tests/test_api.py`, `tests/test_optimizer.py`, `tests/test_optimizer_real.py`, `tests/test_training_support.py` | The served optimizer reaches at least 0.99× a test-time 901-point reference optimum, respects bounds, the margin floor and the inventory cap; out-of-support requests are rejected and in-support demand varies with price. |
| Contract | `tests/test_serving_features.py`, `tests/test_streamlit_contract.py`, `tests/test_product_id_contract.py`, `tests/test_documented_inputs_in_support.py` | Feature order, response fields the UI reads, `product_id` not being a feature, no fabricated UI payloads, every documented/default input inside the training support. |
| Static / architecture | `tests/test_import_graph.py`, `tests/test_config.py`, `tests/test_env.py`, `tests/test_ci_workflow.py`, `tests/test_compose_files.py`, `tests/test_dockerfile_hardening.py`, `tests/test_dockerfile_model_build.py`, `tests/test_repo_hygiene.py`, `tests/test_requirements_pinned.py` | Reachability, config/env read sets, workflow shape, compose validity, non-root/healthcheck, ignore files, pinned dependencies. |
| Documentation | `tests/test_readme_links.py`, `tests/test_readme_truth.py`, `tests/test_readme_limitations.py`, `tests/test_docs.py` | Links resolve, README paths exist, no removed claims, limitations present, docs paths exist. |

Notable guards:

- **Reference-ratio tests** compute the reference optimum at test time from the loaded
  model, so a retrain does not invalidate a hardcoded number.
- **Inventory cap** is asserted on the live optimizer path, not only on a mock.
- **Import graph** asserts every module under `src/` is reachable from an entry point or
  explicitly allowlisted with a reason.
- **Compose validation** parses YAML and checks services; it also keeps the exact broken
  R35 fixture and proves the validator rejects it.
- **Requirements pinning** asserts every direct dependency uses `==` and that plain
  `xgboost` is not used.

The suite has no test that builds or starts a container. The Docker behaviour is verified
by the CI `docker` job.

## 9. Repository layout

```
.
├── .github/workflows/ci.yml   # CI: test + docker jobs
├── app.py                     # Streamlit UI
├── configs/config.yaml        # single configuration file
├── docker-compose.yml         # API + MLflow + Postgres
├── Dockerfile                 # hardened main image, builds data and model
├── Dockerfile.mlflow          # pinned MLflow server image
├── docs/                      # this documentation
├── models/features.json       # tracked feature contract
├── pytest.ini
├── requirements.txt           # every direct dependency pinned
├── scripts/                   # data, training, CI and operations scripts
├── src/                       # api, data, features, training, pricing, monitoring, utils
├── tests/                     # offline test suite
└── .streamlit/config.toml     # UI theme and port
```

**Tracked:** all paths above, plus `.env.example`, `.gitignore` and `.dockerignore`.

**Generated and gitignored:** `data/raw/ecommerce_sales.csv`,
`data/features/training_features.parquet`, `models/demand_model.pkl`,
`models/training_support.json`,
`reports/training_metrics.json`, `reports/feature_importance.csv`, `logs/`, `mlruns/`,
`mlflow.db`, `htmlcov/`, `.coverage`, `.venv/` and `__pycache__/`. A fresh clone has
none of them; run the data and training commands in [OPERATIONS.md](OPERATIONS.md) first.
