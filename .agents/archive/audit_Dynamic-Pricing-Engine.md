# Technical Audit — Dynamic Pricing Engine

**Auditor note:** The "RESUME CLAIMS" section of the request was left as an unfilled
placeholder (`<PASTE THE RESUME BULLET POINTS...>`), and no resume/CV file exists in
the repo or its parent directory. Per the task's own premise — *"the resume text was
AI-generated from an old README"* — I audited every headline claim in `README.md`
(the claimed source of the resume wording) plus the feature claims in `docs/ARCHITECTURE.md`
and `app.py`. If you paste the real bullets, the table below maps 1:1 onto them.
Everything below is verified against source code and runtime behavior, **not** against
comments, docstrings, or docs.

Verification environment: `../venv/bin/python` (xgboost/sklearn/scipy/pandas present;
mlflow is broken in that venv due to a protobuf conflict, which is itself noted below).
Runtime experiments were run directly against the committed `models/demand_model.pkl`.

---

## Actual Architecture Summary

**What actually runs:**

- **Training path (works):**
  `scripts/regenerate_data.py` → `src/data/generator.py` (synthetic data) → `data/raw/ecommerce_sales.csv`
  → `src/features/feature_builder.py` → `data/features/training_features.parquet`
  → `src/training/dataset.py` → `XGBRegressor` (`src/training/trainer.py`) → `joblib.dump` to
  `models/demand_model.pkl` + `reports/training_metrics.json`.
  `scripts/train_with_tuning.py` is the same flow with Optuna (`src/training/hyperparameter_tuning.py`)
  and real MLflow logging (`src/utils/mlflow_tracking.py`).
- **Serving path:** `src/api/server.py:35` builds the FastAPI app; `src/api/router.py:23`
  instantiates `PricingEngine` at import time; `POST /v1/optimize-price`
  (`src/api/router.py:29`) → `PricingEngine.get_optimal_price` (`src/pricing/engine.py:105`)
  → `BayesianPriceOptimizer` (`src/pricing/bayesian_optimizer.py:142`) or `PriceOptimizer`
  (`src/pricing/optimizer.py`) → `model.predict` → `PredictionLogger.log_optimization`
  → `PricingResponse`.
- **Entry points:** `python -m src.api.server` (Dockerfile), `bash start.sh` (MLflow + uvicorn +
  Streamlit, HF Dockerfile), `streamlit run app.py` (UI).
- **Frontend:** `app.py` — Streamlit UI that calls the API over HTTP.

**Real module inventory (root `src/`):**

| Module | Role | Wired into main flow? |
|---|---|---|
| `api/server.py`, `api/router.py`, `api/schemas.py`, `api/middleware.py` | FastAPI app, endpoint, Pydantic schema, rate-limit/timeout/error middleware | Yes |
| `api/error_handlers.py` | Custom exception handlers + `APIError` hierarchy | Handlers registered in `server.py`; the custom error *classes* are never raised |
| `pricing/engine.py` | Model loader + method dispatch | Yes |
| `pricing/bayesian_optimizer.py` | "Bayesian" optimizer | Yes (default method) — **non-functional, see Red Flags** |
| `pricing/optimizer.py` | Grid-search optimizer | Reachable, but **crashes** |
| `pricing/integrated_optimizer.py`, `features/transformer.py` | Alternate optimizer + feature transformer | **Dead** (only used by `tests/test_integration.py`) |
| `pricing/revenue.py`, `pricing/model_loader.py`, `pricing/optimize.py` | Revenue helper / MLflow loader / demo script | **Dead** |
| `monitoring/health_checker.py`, `prediction_logger.py` | Health + prediction audit log | Yes |
| `monitoring/metrics_tracker.py`, `model_monitor.py` | "Prometheus-style" metrics, drift/performance monitor | **Dead** (never imported anywhere) |
| `training/*` | Dataset, trainer, evaluator, Optuna tuning, pipeline | Yes |
| `data/generator.py`, `validation.py`, `ingest.py`, `pipeline_runner.py` | Synthetic data, validation, DB load | Generator used by scripts; `ingest.py`/`pipeline_runner.py` effectively dead |
| `utils/logger.py`, `env_config.py`, `config.py`, `paths.py`, `mlflow_tracking.py` | Infra utils | Logger + env_config + paths used; `config.load_config` used by feature pipeline |

**Data flow end-to-end (serving):** JSON request → Pydantic validation → dict of features →
`PricingEngine` (loads model from MLflow registry, else local `.pkl`) → optimizer builds a
1-row DataFrame selecting `models/features.json` columns → `XGBRegressor.predict` → revenue =
price × demand → logger appends JSONL → response. Because the optimizer is broken (below),
the "optimal price" is effectively a function of the *input bounds*, not of demand.

**Second copy:** `Dynamic-Pricing-Engine/` is a nested, **untracked** clone of the same source
(`diff -rq src Dynamic-Pricing-Engine/src` is empty) that is the Hugging Face Space repo. It
contains committed `__pycache__` and a stale `revnue.cpython-312.pyc` (a renamed file). Keep one
source of truth.

---

## Claim-by-Claim Verification

| Claim | Status | Evidence / File | Notes |
|---|---|---|---|
| XGBoost demand forecasting, ~49% R² | **CONFIRMED (slightly overstated)** | `src/training/trainer.py:16`, `src/training/pipeline.py:24`; `reports/training_metrics.json` | Real `XGBRegressor`, 31 features, 16,500 rows. Actual val **R² = 0.468**, train R² = 0.633. "0.49" is a rounding-up of 0.47. MAPE = 0.40 (40%), which the README never mentions. |
| "Time-series validation" | **FAKE / NOT FOUND in real path** | `src/training/dataset.py:36-42` | The actual split is `train_test_split(..., shuffle=True)` — a **random split**, not time-series. `TimeSeriesSplit` exists only in `trainer.cross_validate` (`trainer.py:81`) which is **disabled** (`run_cv: false`) and never called by `train_with_tuning.py` (that uses Optuna `cross_val_score` with default KFold). |
| Bayesian optimization | **FAKE (non-functional)** | `src/pricing/bayesian_optimizer.py:46-82` | No Bayesian library anywhere (`bayes_opt`, `skopt`, GP — zero matches). It is `scipy.optimize.minimize(method='L-BFGS-B')` on a **non-differentiable tree model**, so the numerical gradient is zero and it terminates immediately. Empirically (real model): range (30,80)→**80.0**, (70,110)→**90.0** (success=False, iters=0), (10,200)→**200.0**, (100,120)→**120.0**. It returns a bound or the midpoint, not an optimum. |
| Grid search method | **PARTIAL (broken)** | `src/pricing/optimizer.py:28` | Reproduced a hard failure: `KeyError ['price_advantage','log_price','log_comp_price',...] not in index` — it only synthesizes 5 of the 31 required columns. The identical KeyError is the **only** thing in the production prediction logs (27 occurrences, 0 successful optimizations). |
| Business constraints (margin, inventory, price range) | **PARTIAL** | `src/pricing/bayesian_optimizer.py:142-186` | Margin raises the lower bound and inventory caps demand — these code paths work. But because the optimizer itself is broken, constraints are applied to a meaningless "optimum". `tests/test_optimizer.py` passes only because the broken output (a midpoint/bound) happens to satisfy the asserted margin. |
| Automated feature engineering (calendar/price/temporal) | **CONFIRMED** | `src/features/feature_builder.py:29-134` | Real lag/rolling/seasonality/price-interaction features with proper `shift(1)` (no target leakage). Uses raw `product_id` as a feature — entity leakage / won't generalize to unseen products. |
| Optuna hyperparameter tuning (up to 50 trials) | **CONFIRMED** | `src/training/hyperparameter_tuning.py:23-92`, `scripts/train_with_tuning.py:76-92` | Genuine Optuna TPE study, `n_trials` from config/env. |
| Data drift detection | **PARTIAL / not wired** | `src/monitoring/model_monitor.py:59-120` | `ModelMonitor.calculate_drift` exists but is **never imported or called** anywhere. The only "drift test" (`tests/test_data_drift.py`) is a standalone KS test on the synthetic CSV that asserts `pvalue < 0.01` (i.e. it asserts drift *exists* in random synthetic data) and is not connected to the service. |
| Model performance monitoring / degradation alerts | **NOT FOUND in service** | `src/monitoring/model_monitor.py:122-204` | `calculate_performance_metrics` / `check_model_degradation` are dead code. Nothing consumes actuals; there is no feedback loop. |
| Prediction logging / audit trail | **CONFIRMED** | `src/monitoring/prediction_logger.py`, used at `src/api/router.py:72,96`; `logs/predictions/*.jsonl` | Real JSONL audit log with error and optimization entries. |
| Comprehensive metrics (MAE/RMSE/R²/MAPE/directional accuracy) | **CONFIRMED** | `src/training/evaluate.py:15-98` | All computed for real. |
| FastAPI production API + Swagger/ReDoc | **CONFIRMED** | `src/api/server.py:35-41` | Real FastAPI, `/docs`, `/redoc`, versioned router at `/v1`. |
| Health / readiness / liveness checks | **CONFIRMED** | `src/api/router.py:111-137`, `src/monitoring/health_checker.py` | Real endpoints; system CPU/mem/disk via psutil. Fragile: model check does `model.predict(np.zeros((1, n_features_in_ or 10)))` (`health_checker.py:41-43`) — will report degraded for an MLflow pyfunc model. |
| `/metrics` endpoint | **PARTIAL** | `src/api/router.py:140-146` | Returns custom JSON from `HealthChecker`/`PredictionLogger`, **not** Prometheus exposition format. |
| Prometheus integration | **COSMETIC** | `requirements.txt:38`; `src/monitoring/metrics_tracker.py:1` | `prometheus-client` is declared but **never imported**. `MetricsTracker` is a hand-rolled in-memory dict that is itself never used. No `/metrics` Prometheus format, no instrumentation. |
| Rate limiting | **CONFIRMED** | `src/api/middleware.py:68-108`, `src/api/server.py:64-67` | In-memory per-IP sliding window, enabled via `RATE_LIMIT_ENABLED`. |
| Input validation | **CONFIRMED** | `src/api/schemas.py` | Real Pydantic constraints and a `price_max > price_min` validator. |
| Error handling / graceful shutdown | **CONFIRMED (with caveat)** | `src/api/middleware.py`, `src/api/error_handlers.py`, `src/api/server.py:77-92` | Handlers exist. Caveat: `router.py:91-108` catches bare `Exception`, logs it, then re-raises as a 500 — it **does not swallow**, but it also returns raw internal error strings to clients (`detail=str(e)`). `PricingEngine.load_model` (`engine.py:91-94`) *does* silently swallow MLflow errors and falls back to a local model. |
| Structured JSON logs | **CONFIRMED** | `src/utils/logger.py:11-44, 82-100` | Real JSON formatter + file handler. |
| Log rotation | **FAKE** | `src/utils/logger.py:98` | Plain `logging.FileHandler` — no `RotatingFileHandler`/`TimedRotatingFileHandler`. "Rotation" is a manual `find ... -mtime +7 -delete` snippet in the README. `LOG_ROTATION`/`LOG_RETENTION_DAYS` env vars are never read. |
| Docker deployment | **CONFIRMED** | `Dockerfile`, `Dockerfile.hf`, `Dockerfile.prod`, `docker-compose*.yml` | Real images; `.prod` is genuinely multi-stage and runs as non-root `appuser`. |
| Nginx reverse proxy | **COSMETIC / broken** | `docker-compose.prod.yml:45-54` | Compose mounts `./nginx/nginx.conf` and `./nginx/ssl`, but **`nginx/` does not exist**. `docker-compose -f docker-compose.prod.yml up` will fail on the missing bind mounts. No nginx config anywhere in the repo. |
| Automated AWS EC2 deployment + rollback | **NOT FOUND** | README `:200,214,224,466` | `scripts/deploy.sh` and `scripts/pre_deploy_check.sh` are **missing**. `DEPLOYMENT.md`, `docs/API.md`, `docs/OPERATIONS.md`, `PRODUCTION_FEATURES.md`, `PRODUCTION_READY.md`, `requirements-hf.txt` are all **missing** despite being linked/mentioned. |
| CI/CD (testing automation, image builds, smoke tests) | **NOT FOUND** | — | **No `.github/` directory and no workflow files** anywhere (despite git history messages "Update CI/CD Pipeline", "try to fix workflows"). `.dockerignore` and docs mention CI/CD; no implementation remains. |
| Unit / integration / smoke tests | **PARTIAL** | `tests/` | 17 tests pass (optimizer/evaluator/integration/data-drift). But: `tests/test_integration.py` tests the **dead** `IntegratedPricingOptimizer`, not the served engine; `tests/test_optimizer.py` uses toy mock models and cannot detect the broken real optimizer; `tests/smoke_tests.py` is a **standalone script whose class is `SmokeTestRunner`**, so `pytest tests/smoke_tests.py` collects **0 tests** (README's command is wrong). `tests/test_api.py` imports `src.api.server`, which imports `mlflow` at module load — untestable in this venv and coupled to a running MLflow. Stored coverage: **69%**. |
| SQLite database + backup/restore, 7-day retention | **PARTIAL** | `scripts/backup_database.sh`, `scripts/restore_database.sh`, `data.db`, `src/data/ingest.py` | Backup/restore scripts are real. But the API/engine **never reads or writes the database** — `data.db` is an orphan. `ingest.py` is named `load_to_postgres` yet writes `sqlite:///data.db`, and its `__main__` points at a non-existent `synthetic_sales.csv` (`ingest.py:16`). |
| MLflow model versioning | **PARTIAL** | `src/utils/mlflow_tracking.py`, `scripts/train_with_tuning.py`, `src/pricing/engine.py:44-94`, `mlruns/`, `mlflow.db` | Real MLflow logging during tuning and real registry lookup at serve time, and `mlruns/models/demand_forecasting_model` has versions. But: `scripts/promote_model.py` uses the **removed/deprecated** `get_latest_versions` + `transition_model_version_stage` API; `engine.py` uses `search_model_versions(filter_string="...tags.stage='Production'")` and silently falls back to the local `.pkl` on any error. The README lists MLflow under **"Future Enhancements"** while the code already depends on it — documentation and code disagree. |
| Streamlit UI (Quick/Advanced/Batch) | **PARTIAL / broken integration** | `app.py` | UI renders, but it **cannot display a result from the current API**: `app.py:203,207,227,229,230,373` read `result['predicted_demand']`, while the API returns `expected_demand` (`src/api/schemas.py:83`). Every successful call raises `KeyError` inside the broad `except` at `app.py:242` → user sees an error. Also the dropdown sends `"grid_search"` (`app.py:130`) but `engine.py:155` only accepts `"grid"` → 500. The Advanced tab shows a hardcoded fake response (`app.py:306-316`) with fields (`confidence_interval`, `optimization_metadata`, `time_ms`) the API never returns. |
| Hugging Face Spaces deployment | **PARTIAL** | `Dynamic-Pricing-Engine/`, `Dockerfile.hf`, `start.sh` | Real Docker Space setup. Fragile: `start.sh` loops forever waiting for `/v1/health` to be 2xx; if health returns 503, Streamlit never starts and the Space hangs. |
| "Enterprise security" / non-root containers | **PARTIAL** | `Dockerfile.prod` | Non-root user is real. Rate limiting + validation are real. No authN/authZ, no TLS config (nginx missing), CORS defaults to `*`. |
| Resource limits | **COSMETIC** | `docker-compose.prod.yml` | `deploy.resources.limits` is only honored by Swarm / `docker compose --compatibility`; ignored by plain Compose. |

---

## Red Flags (AI-boilerplate signs, dead code, fake functionality)

**Core product is fake / broken (most important):**

1. **The "Bayesian optimization" returns a bound or the midpoint, never an optimum.**
   `bayesian_optimizer.py:74` minimizes with L-BFGS-B, a gradient method, over a step-function
   objective. Verified against the real committed model: (30,80)→80.0, (70,110)→90.0 with
   `optimization_success=False, optimization_iterations=0`, (10,200)→200.0, (100,120)→120.0.
   The README's own example claims `$95.50`; the code returns `90.0` for that exact range.
   **This is the headline capability and it does not work.**
2. **Grid search crashes** with the exact `KeyError` recorded 27 times in `logs/predictions/*.jsonl`
   — and those logs contain **zero successful optimizations**, only errors.
3. **Frontend/backend contract mismatch**: `predicted_demand` vs `expected_demand`, and
   `grid_search` vs `grid`. The demo UI cannot show a result.
4. **Random train/test split** (`shuffle=True`) reported as "time-series validation". With
   `product_id` as a feature and all products in both splits, the reported R² is optimistic.

**Dead code (defined, never called from the real pipeline):**

- `src/pricing/integrated_optimizer.py` + `src/features/transformer.py` — used **only** by tests.
- `src/pricing/revenue.py` (`RevenueCalculator`), `src/pricing/model_loader.py`
  (`load_production_model`), `src/pricing/optimize.py` (demo), `PricingEngine.compare_methods`.
- `src/monitoring/metrics_tracker.py` (`MetricsTracker`, `Timer`) — zero references.
- `src/monitoring/model_monitor.py` (`ModelMonitor`) — zero references.
- `src/data/ingest.py`, `src/data/pipeline_runner.py` (and `ingest.py`'s `__main__` is broken).
- `src/utils/config.py` `load_config` is used only by `feature_pipeline.py`.
- `api/error_handlers.py` classes `ModelNotFoundError`, `OptimizationError`, `InvalidInputError`
  are never raised anywhere.
- `EnvConfig.get_env`, `is_production`, `is_development`, `reload_config` — unused.

**Config values defined but never read (dead config):**

- `pricing.price_min_multiplier`, `price_max_multiplier`, `price_steps`, `default_method`.
- `training.test_size` (hardcoded 0.2 in `dataset.py:39`), `random_state` (hardcoded 42),
  `cv_folds` (hardcoded 5 in `trainer.py:81`, 3 in tuning).
- The entire `monitoring:` block (`enabled`, `log_dir`, `drift_threshold`,
  `performance_degradation_threshold`, `check_interval_hours`).
- The entire `api:` block in `config.dev.yaml`/`config.prod.yaml` — the app reads these from
  **env vars** via `EnvConfig.get_bool/get_int`, never from YAML. `model.demand_model` unused.
- `.env` defines ~30 vars; only a handful are read (`APP_ENV`, `MLFLOW_TRACKING_URI`,
  `RATE_LIMIT_ENABLED`, `RATE_LIMIT_REQUESTS`, `REQUEST_TIMEOUT`, `CORS_ENABLED`, `LOG_*`,
  `API_*`). `DATABASE_*`, `MODEL_CACHE_ENABLED`, `CACHE_TTL`, `ALERT_*`, `METRICS_ENABLED`,
  `HEALTH_CHECK_INTERVAL`, `PREDICTION_LOG_*`, `MONITORING_ENABLED` are decorative.

**Swallowed errors / generic handling:**

- `PricingEngine.load_model` catches bare `Exception` and silently falls back to the local
  pickle (`engine.py:91-94`) — a real MLflow misconfiguration looks like success.
- `health_checker.check_health` catches all exceptions and downgrades to "degraded"
  (`health_checker.py:46-48`).
- `integrated_optimizer.objective` returns `1e10` on any error (`integrated_optimizer.py:87-89`)
  — a silent "penalty" that hides bugs (this file is dead, but it is the pattern).

**Tests that don't test the claim:**

- `tests/test_optimizer.py` mocks the model with `lambda X: np.array([100 - X.iloc[0]['price']])`
  — a smooth function. The real XGBoost model is non-smooth; the tests pass while the real
  optimizer is broken.
- `tests/test_integration.py` exercises the dead `IntegratedPricingOptimizer`, not the served
  `BayesianPriceOptimizer`.
- `tests/test_data_drift.py` asserts drift *exists* (`pvalue < 0.01`) in synthetic data and is
  disconnected from the service.
- `tests/smoke_tests.py` is not collectable by pytest (class `SmokeTestRunner`); the README's
  `pytest tests/smoke_tests.py` collects nothing.

**Boilerplate / consistency smells:**

- `src/api/router.py:1-12` imports `from pathlib import Path` twice.
- `requirements.txt:26,35` lists `requests` twice; `sqlalchemy` is imported by `ingest.py` but
  never declared (it only works transitively via MLflow); `shap`, `prometheus-client`, `mypy`,
  `flake8`, `black`, `isort` are declared but unused.
- Commit history ("try to fix workflows 2", ":))", ":)", "other update") and a leftover
  `revnue.cpython-312.pyc` indicate iteration without cleanup.
- README documents files that do not exist (see above) — classic "docs written ahead of code".
- Two full copies of the repo (root + nested `Dynamic-Pricing-Engine/`), one untracked.

**Fundamental modeling issue (not boilerplate, but an interviewer will catch it):**

- The optimizer treats an **observational** demand model as a **causal** price-response curve.
  In the synthetic generator demand is literally a function of price (`generator.py:75-81`), so
  the exercise is internally consistent — but on real e-commerce data price and demand are
  jointly confounded, and `argmax_price E[units | price]` is not a valid pricing policy.
- `product_id` is a raw model feature, so the model cannot price a new product and partly
  memorizes per-product means.

---

## External Tools/Infra: Real vs Cosmetic

| Tool / Infra | Present? | Real integration? | Verdict |
|---|---|---|---|
| **XGBoost** | Yes | Trained, persisted, served | **Real** |
| **scikit-learn** | Yes | Metrics, splits, CV | **Real** |
| **Optuna** | Yes | `HyperparameterTuner`, invoked by `train_with_tuning.py` | **Real** |
| **MLflow** | Yes (`mlruns/`, `mlflow.db`, tracking code) | Training logs runs/models; engine attempts registry load | **Partial** — silent fallback, deprecated promote API, README calls it "future" |
| **FastAPI / Uvicorn / Pydantic** | Yes | Core serving stack | **Real** |
| **Streamlit** | Yes (`app.py`) | Calls API, but response-field mismatch breaks it | **Partial/broken** |
| **Docker / Docker Compose** | Yes (3 Dockerfiles, 3 compose files) | Images real; prod compose references missing nginx config | **Partial** |
| **Nginx** | Referenced only | `./nginx/nginx.conf` mount does not exist | **Cosmetic** |
| **Prometheus** | Dependency only | Never imported; no Prometheus metrics format | **Cosmetic** |
| **psutil** | Yes | Used in `health_checker` | **Real** |
| **SQLite** | `data.db` + scripts | App never touches DB; backup script real | **Partial/orphan** |
| **GitHub Actions / CI-CD** | No files | No workflows | **Not found** |
| **Grafana** | No | Zero references | **Not found** |
| **Evidently** | No | Zero references | **Not found** |
| **ONNX Runtime** | No | Zero references | **Not found** |
| **AWS EC2 deploy scripts** | No | `deploy.sh` missing | **Not found** |
| **Hugging Face Spaces** | Yes (nested repo) | Docker Space; fragile startup | **Partial** |

---

## Honest Maturity Assessment

**Intermediate-level Python packaging with an advanced-sounding surface and a non-functional core.**

What is genuinely good: the code is organized into a real package layout (`api`/`data`/`features`/
`training`/`pricing`/`monitoring`/`utils`), the synthetic-data + feature-engineering + XGBoost
training pipeline actually runs and produces real artifacts (R² 0.47, feature importances,
MLflow runs), the FastAPI layer has real validation/middleware/logging, and there are working
unit tests for the evaluator and the toy optimizers. This is above "script in a notebook".

What is not: the single most important claim — that the system finds an optimal price — is
false. The optimizer returns a bound or the midpoint. The second method crashes. The UI can't
render a result. The "drift detection", "Prometheus metrics", "Nginx proxy", "AWS deployment",
"CI/CD", and "time-series validation" are either dead code, missing files, or renamed
L-BFGS-B. The documentation describes an aspirational system, not this repository. Advanced
library names (Prometheus, Nginx, MLflow stages, Bayesian optimization) were bolted on without
being wired in — the textbook signature of AI-generated scaffolding.

Bottom line: **a solid MLOps-shaped skeleton with a broken brain.** Do not present the pricing
optimization, monitoring, or deployment claims as working.

---

## Interview-Readiness Questions I Should Be Able to Answer

Based **only** on what is in the code:

1. Walk me through what happens to a request to `POST /v1/optimize-price`. Which function
   actually produces the number returned as `optimal_price`?
2. Why does the "Bayesian optimizer" use `scipy.optimize.minimize(method='L-BFGS-B')`, and what
   happens when the objective is a tree ensemble (piecewise constant)? (Be ready to admit it
   returns a bound/midpoint.)
3. Reproduce the `KeyError` in `PriceOptimizer.optimize` and explain why the grid method is
   broken while the Bayesian method is not (both build feature frames differently).
4. Your prediction logs contain 27 errors and zero successful optimizations. What does that say
   about whether this API was ever used end-to-end?
5. The Streamlit app reads `result['predicted_demand']` but the API returns `expected_demand`.
   How did this ship, and why didn't the tests catch it?
6. You split data with `train_test_split(shuffle=True)` but describe it as time-series
   validation. Why does that matter for a demand-forecasting model, and what would you change?
7. `product_id` is a model feature. What happens when you price a product the model has never
   seen? Why is that a problem for a "dynamic pricing engine"?
8. Your model is trained on observational price/demand data. Why is `argmax_p price * E[units|p]`
   not a valid pricing decision in the real world, and what would you need (experiments, IV,
   uplift modeling) to fix it?
9. Explain the MLflow load path in `PricingEngine.load_model`. What exactly happens if the
   registry is down or no Production model exists, and why is that dangerous?
10. `scripts/promote_model.py` calls `get_latest_versions` and `transition_model_version_stage`.
    What is wrong with that in current MLflow?
11. Which classes in `src/monitoring/` are never imported by the running service? How would you
    wire drift detection to real traffic?
12. `prometheus-client` is in `requirements.txt`. Where is it used? What would real Prometheus
    instrumentation require (and why does `/v1/metrics` return JSON instead)?
13. `docker-compose.prod.yml` mounts `./nginx/nginx.conf`. What happens when you run it? Which
    files does the README reference that don't exist?
14. The HF `start.sh` waits for `/v1/health` to return 2xx. If health returns 503, what happens
    to the container? Is there a timeout?
15. What is your actual test coverage, which tests target dead code, and why does
    `pytest tests/smoke_tests.py` collect zero tests?
16. Which config keys in `configs/config.yaml` are never read by any code? How would you detect
    that systematically?
17. What is the real R² on validation vs train, and what is the MAPE? Why does the README only
    advertise R²?

---

## Recommended Next Steps

### A. Fix the resume wording (do this first — cheap, honest, removes the landmines)

- **Remove** "Bayesian optimization", "optimal price", "maximizes revenue/profit" until the
  optimizer actually works. Replace with: *"Prototyped a price-optimization service; demand model
  trained with XGBoost; optimization component incomplete."*
- **Remove** "time-series validation" → say *"random train/test split"* or delete.
- **Remove** "data drift detection", "Prometheus", "Grafana", "Nginx reverse proxy", "AWS EC2
  deployment", "CI/CD", "log rotation", "production-ready". None are functional.
- **Downgrade** "production-ready / enterprise-grade" to *"learning/portfolio project"*.
- Keep and sharpen the truthful parts: *XGBoost demand model (R²≈0.47), FastAPI service with
  Pydantic validation + rate limiting + structured logging + health endpoints, Optuna tuning,
  MLflow experiment tracking, Dockerized.*
- Replace the "49% R²" with the exact number and add MAPE so it isn't cherry-picked.

### B. Fix the code (in priority order)

1. **Replace the optimizer with something that actually optimizes.** For a tree model, use a
   dense price grid (vectorized `model.predict` over all candidate prices) or a proper
   derivative-free global optimizer (Optuna/TPE, `scipy.optimize.differential_evolution`).
   Assert that the returned price is an interior optimum, not a bound. This single fix makes the
   headline claim true.
2. **Fix grid search** (`src/pricing/optimizer.py:19-28`): build the same complete feature frame
   as `bayesian_optimizer._build_features` (or reuse `FeatureTransformer`), then select columns.
   Add a regression test that runs **both** methods against the real `models/demand_model.pkl`.
3. **Fix the frontend contract**: change `app.py` to read `expected_demand`, send `"grid"` (or
   make the engine accept `"grid_search"`), and delete the fake hardcoded response in the
   Advanced tab.
4. **Fix the train/validation split**: use a time-based split (`TimeSeriesSplit` or sort by date
   and hold out the last N days), drop `product_id` from features (or target-encode with
   out-of-fold), and re-report metrics honestly.
5. **Delete or wire dead code.** Remove `integrated_optimizer.py`, `transformer.py`,
   `revenue.py`, `model_loader.py`, `optimize.py`, `metrics_tracker.py`, `model_monitor.py`,
   `ingest.py`, `pipeline_runner.py`, and the unused error classes — or integrate them and test
   them. Decide on **one** optimizer and **one** feature-transform path.
6. **Make MLflow fallback loud**: log at ERROR and expose a health flag instead of silently
   loading the local pickle. Update `promote_model.py` to the alias-based MLflow API.
7. **Fix config wiring**: either read `configs/*.yaml` `api:`/`monitoring:` sections in the app
   or delete them. Remove unused keys and env vars. Add a test that fails on unknown/unused keys.
8. **Make the test suite meaningful**: add a real-model optimizer test, an API test that asserts
   the response contract, a Streamlit/API contract test (field names), and convert
   `smoke_tests.py` into a pytest module. Raise coverage on the pricing path.
9. **Fix deployment artifacts**: add `nginx/nginx.conf` (or drop the nginx service), add the
   missing `scripts/deploy.sh`/`pre_deploy_check.sh` or remove them from the README, add the
   missing docs links or delete them, and add a GitHub Actions workflow (or drop CI/CD claims).
10. **Clean repo hygiene**: remove the nested duplicate repo, remove committed `__pycache__`,
    add `sqlalchemy` to `requirements.txt` (or remove `ingest.py`), de-duplicate `requests`,
    and drop unused deps (`shap`, `prometheus-client`, linters if not used).

### C. If you only have one hour

Fix items **B1** and **B2** (make the optimizer real and testable) and **B3** (frontend contract),
then rewrite the resume bullet as: *"Built an XGBoost demand-forecasting model (R²≈0.47) and a
FastAPI pricing service with Pydantic validation, rate limiting, structured logging, health
endpoints, Optuna tuning, and MLflow tracking; optimization uses a vectorized price search."*
That statement is defensible in an interview. The current one is not.
