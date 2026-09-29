# STATE.md — Ground Truth for the Dynamic Pricing Engine

**Purpose:** This is the single source of truth about what *actually works* in this repo.
Read this **before** trusting `README.md`, `docs/*`, or any code comment/docstring.
Those are aspirational and, in several places, false.

**How this was produced:** Every claim below was verified by reading the actual source,
tracing imports, and (where possible) running the code against the real committed model
`models/demand_model.pkl`. Docs and comments were treated as *hypotheses only*.

**Verification environment (this machine):**
- Python: `/home/arshiaask/projects/venv/bin/python` (3.12.3), cwd = repo root.
- Present & working: xgboost 3.2.0, scikit-learn 1.9.0, scipy 1.17.1, pandas 2.3.3, fastapi 0.136.3, pydantic 2.13.4, optuna 4.8.0, psutil, joblib, pyarrow.
- **Broken:** `mlflow` cannot be imported (protobuf conflict: `ImportError: cannot import name 'service' from 'google.protobuf'`). This is not a code bug per se, but it *does* break every entry point that imports `mlflow` at module top level — which includes the API and the "recommended" training script.
- Prior audit used as a cross-check: `audit_Dynamic-Pricing-Engine.md` in repo root (the `/mnt/user-data/uploads/audit_Dynamic-Pricing-Engine.md` path given in the task **does not exist**). That file has since been reviewed, judged superseded by this one, and **deleted** (2026-09-28); the corrections it prompted are recorded in §6.

**Status legend:** `CONFIRMED` = real and works · `PARTIAL` = partially real / works with caveats · `FAKE-OR-DEAD` = exists but non-functional or never wired in · `NOT-FOUND` = claimed but absent.

---

## 1. Claim-by-claim verification

| Feature / claim (plain words) | Status | Evidence (file:line) | Gap / note |
|---|---|---|---|
| XGBoost demand-forecasting model | CONFIRMED | `src/training/trainer.py:18` (`XGBRegressor`); `models/demand_model.pkl` loads as `XGBRegressor`, `n_features_in_=31`; `models/features.json` (31 cols) | Real model, but trained on **synthetic** data from `src/data/generator.py`. |
| "~49% R² accuracy" | PARTIAL | `reports/training_metrics.json` → `R2: 0.4682` | "0.49" rounds 0.468 up. Also unreported: `MAPE: 0.40` (40% error), `Train_R2: 0.633`. |
| "Time-series validation" | FAKE-OR-DEAD | `src/training/dataset.py:36-42` → `train_test_split(..., shuffle=True)` | Actual split is a **random** split, not temporal. `TimeSeriesSplit` exists only in `src/training/trainer.py:81` (`cross_validate`), which is gated off by `training.run_cv: false` (`configs/config.yaml:36`) and never called by `train_with_tuning.py` (which uses default KFold `cross_val_score`, `src/training/hyperparameter_tuning.py:43-50`). |
| "Bayesian optimization" finds optimal price | CONFIRMED (fixed 2026-09-29, R1) | `src/pricing/bayesian_optimizer.py` `optimize` → vectorized dense price grid + local refinement; no gradient call remains | Returns the true revenue optimum. Real model (reference grid computed at test time): `(30,80)`, `(70,110)`, `(30,120)` → 77.3725 (revenue 5951.36, ≥ 0.99× the 901-point max); `(10,200)` → 200.0 and `(100,120)` → 120.0, where the true optimum is genuinely the upper bound. All `optimization_success=True`. Still **misleadingly named** — no Bayesian library is used; the rename is DECISIONS D2 / ROADMAP R6. |
| Grid-search optimization method | FAKE-OR-DEAD (crashes) | `src/pricing/optimizer.py:19-28` | Builds only 5 of 31 required columns → `KeyError: "['price_advantage', 'log_price', 'log_comp_price', 'price_advantage_sin', 'price_change_1d', 'price_change_7d', 'roll_mean_price_7', 'roll_mean_price_14', 'roll_mean_price_28'] not in index"`. Reproduced directly and via the API (HTTP 500). |
| Business constraints (min margin, inventory, price bounds) | CONFIRMED | `src/pricing/bayesian_optimizer.py` `optimize_with_constraints` (margin lifts lower bound), `optimize` (inventory caps demand) | Real and now applied to a genuine optimum. Reproduced: `optimize_with_constraints(base, 30, 120, cost=60, min_margin_pct=0.15)` → price 77.3725, `profit_margin=0.2245`; `optimize(..., inventory_limit=50)` → `expected_demand ≤ 50`. |
| Automated feature engineering (calendar/price/temporal) | CONFIRMED | `src/features/feature_builder.py:29-134` | Real lag/rolling/seasonality/price-interaction features using `shift(1)` (no target leakage). Caveat: raw `product_id` is a model feature (`models/features.json:2`) → won't generalize to unseen products. |
| Optuna hyperparameter tuning (up to 50 trials) | CONFIRMED (code) / PARTIAL (runnable) | `src/training/hyperparameter_tuning.py:23-92` (real TPE study); invoked at `scripts/train_with_tuning.py:86` | Genuine Optuna code. **Cannot run in this environment**: `scripts/train_with_tuning.py:9` imports `mlflow` at top → `ImportError` (protobuf). |
| Data drift detection | FAKE-OR-DEAD | `src/monitoring/model_monitor.py:59-120` (`calculate_drift`) | Never imported or called anywhere. The only "drift test" (`tests/test_data_drift.py:19`) asserts `pvalue < 0.01`, i.e. it asserts drift *exists* in random synthetic data, and is not connected to the service. |
| Model performance monitoring / degradation alerts | FAKE-OR-DEAD | `src/monitoring/model_monitor.py:122-204` | `calculate_performance_metrics` / `check_model_degradation` never imported. No actuals feedback loop exists. |
| Prediction logging / audit trail | CONFIRMED | `src/monitoring/prediction_logger.py`; called at `src/api/router.py:72,96`; outputs in `logs/predictions/*.jsonl` | Real JSONL audit log. But all 8 log files present locally (untracked — `logs/` is gitignored, so they are **not** committed) contain **only** `type: "error"` entries (27 total, 0 successful optimizations) — evidence the API was never used successfully end-to-end. |
| Comprehensive metrics (MAE/RMSE/R²/MAPE/directional) | CONFIRMED | `src/training/evaluate.py:15-98`; values in `reports/training_metrics.json` | All computed for real. |
| FastAPI service + Swagger/ReDoc | CONFIRMED (with env caveat) | `src/api/server.py:35-41` (`docs_url="/docs"`, `redoc_url="/redoc"`); router mounted at `/v1` (`server.py:74`) | Works (verified via TestClient with mlflow stubbed). **Cannot start in this env** because `src/pricing/engine.py:9` imports `mlflow` unconditionally → `ImportError`. |
| Health / readiness / liveness endpoints | PARTIAL (buggy) | `src/api/router.py:111-137`; `src/monitoring/health_checker.py` | Real endpoints (verified 200). Bug: model check uses `getattr(model, "n_features_in_", 10)` and predicts on `np.zeros((1,10))` (`health_checker.py:41-43`). An MLflow `pyfunc` model has no `n_features_in_` → wrong width → predict raises → status `degraded` → `/v1/health` returns **503**. |
| `/metrics` endpoint | PARTIAL | `src/api/router.py:140-146` | Returns custom JSON (`health` + `predictions`), **not** Prometheus exposition format. |
| Prometheus integration | FAKE-OR-DEAD | `requirements.txt:38` declares `prometheus-client`; zero imports in repo | `src/monitoring/metrics_tracker.py` is a hand-rolled in-memory dict that is itself never imported. No instrumentation. |
| Rate limiting | CONFIRMED | `src/api/middleware.py:68-108`; enabled at `src/api/server.py:64-67` | Real in-memory per-IP sliding window, toggled by `RATE_LIMIT_ENABLED`. |
| Input validation | CONFIRMED | `src/api/schemas.py:5-77` | Real Pydantic constraints + `price_max > price_min` validator (`:43-48`). |
| Error handling / graceful shutdown | PARTIAL | `src/api/middleware.py`, `src/api/error_handlers.py`, `src/api/server.py:77-92` | Handlers exist. Two problems: `router.py:91-108` catches bare `Exception` and returns `detail=str(e)` (leaks internal errors to clients), and `engine.py:91-94` silently swallows MLflow failures and falls back to the local pickle. |
| Structured JSON logs | CONFIRMED | `src/utils/logger.py:11-44`, `:82-100` | Real JSON formatter + file handler. |
| Log rotation | FAKE-OR-DEAD | `src/utils/logger.py:98` → plain `logging.FileHandler` | No `RotatingFileHandler`/`TimedRotatingFileHandler`. `LOG_ROTATION`/`LOG_RETENTION_DAYS` (`.env:41-42`) are never read. README's "rotation" is a manual `find ... -delete` snippet (`README.md:284`). |
| Docker deployment | CONFIRMED (caveats) | `Dockerfile`, `Dockerfile.hf`, `Dockerfile.prod`, `docker-compose*.yml` | Real images; `Dockerfile.prod:36` runs non-root `appuser`. Caveats: `Dockerfile:1` base is the `docker.arvancloud.ir` mirror; `docker-compose.yml:36` references `image: dynamic-pricing:latest` with **no `build:` context** (needs a pre-built image). |
| Nginx reverse proxy | FAKE-OR-DEAD | `docker-compose.prod.yml:53-54` mounts `./nginx/nginx.conf` and `./nginx/ssl` | `nginx/` **does not exist**. `docker-compose -f docker-compose.prod.yml up` fails on the missing bind mounts. No nginx config anywhere. |
| Automated AWS EC2 deployment + rollback | NOT-FOUND | `README.md:200-218` | `scripts/deploy.sh` and `scripts/pre_deploy_check.sh` are **missing**. Only `health_check.sh`, `metrics.sh`, `logs.sh`, `load_test.sh`, `backup_database.sh`, `restore_database.sh`, `run_smoke_tests.sh` exist. |
| CI/CD (test automation, image builds, smoke tests) | NOT-FOUND | no `.github/` directory, no workflow files | Dead CI metadata code remains at `scripts/train_with_tuning.py:28-35` (`GITHUB_RUN_ID`, etc.). |
| Unit / integration / smoke tests | PARTIAL | `tests/` | `pytest tests/` **aborts at collection** because `tests/test_api.py:4` imports the mlflow-dependent API. With `--ignore=tests/test_api.py`: **17 pass**. `pytest tests/smoke_tests.py` collects **0** (class `SmokeTestRunner` holds methods, not module-level `test_*`). `tests/test_optimizer.py:18` mocks a *smooth* model, so it cannot detect the broken real optimizer. `tests/test_integration.py` exercises the **dead** `IntegratedPricingOptimizer`. Stored coverage: **69%** (`.coverage`, dated Jun 6). |
| SQLite DB + backup/restore, 7-day retention | PARTIAL | `scripts/backup_database.sh`, `scripts/restore_database.sh`, `data.db` | `data.db` exists with a populated `sales_data` table (18,250 rows), but **no `src/` code reads or writes it** (no `DATABASE_URL` usage outside shell scripts). Backup/restore scripts are real; retention defaults to 7 days. |
| MLflow model versioning | PARTIAL / dead at serve time | `src/utils/mlflow_tracking.py`, `scripts/train_with_tuning.py:136-140`, `src/pricing/engine.py:44-94`, `mlruns/`, `mlflow.db` | Registry has `demand_forecasting_model` v1 & v2, but **both have `current_stage: None` and `aliases: []`** (`mlruns/models/demand_forecasting_model/version-*/meta.yaml`). So `search_model_versions(... tags.stage='Production')` and the alias fallback both return nothing → the engine **always** falls back to the local pickle. `scripts/promote_model.py:12-29` uses deprecated `get_latest_versions`/`transition_model_version_stage` and promotes to **Staging**, never Production. README lists MLflow under "Future Enhancements" (`README.md:419`) while the code already depends on it. |
| Streamlit UI (Quick/Advanced/Batch) | PARTIAL / broken integration | `app.py` | UI renders but cannot display a result from the current API: it reads `result['predicted_demand']` (`app.py:203,207,227,229,230,373`) while the API returns `expected_demand` (`src/api/schemas.py:83`) → `KeyError` swallowed by the broad `except` at `app.py:242`. It also sends `"grid_search"` (`app.py:130`) which the engine rejects (`engine.py:155-156` → 500). The Advanced tab shows a hardcoded fake response (`app.py:306-316`) with fields (`confidence_interval`, `optimization_metadata`, `time_ms`) the API never returns. |
| Hugging Face Spaces deployment | PARTIAL | `Dockerfile.hf`, `start.sh` | Real Docker Space setup. Fragile: `start.sh:23-25` loops forever waiting for `/v1/health` to return 2xx with **no retry cap**; if health returns 503 the container hangs and Streamlit never starts. (The nested HF repo mentioned by the prior audit is **no longer present**.) |
| "Enterprise security" / non-root containers | PARTIAL | `Dockerfile.prod:36` (`USER appuser`) | Non-root is real; rate limiting + validation are real. But: no authN/authZ, no TLS (nginx missing), CORS defaults to `*` (`src/api/server.py:50`). |
| Resource limits | COSMETIC | `docker-compose.prod.yml:31-38` | `deploy.resources.limits` is only honored by Swarm / `docker compose --compatibility`; ignored by plain Compose. |
| README example `curl` to optimize price | FAKE-OR-DEAD | `README.md:133` posts to `http://localhost:8000/optimize-price` | Missing the `/v1` prefix → **404**. Real route is `POST /v1/optimize-price`. |
| README training command `python src/training/train.py` | FAKE-OR-DEAD | `README.md:106` | Fails: `ModuleNotFoundError: No module named 'src'` (script does not add repo root to `sys.path`). Only `python -m src.training.train` works. |

---

## 2. Actual data / request flow end-to-end (verified, not as documented)

### Training path (what actually runs)

```
scripts/regenerate_data.py
  → src/data/generator.py:EcommerceDataGenerator(n_products=100, days=365)
  → data/raw/ecommerce_sales.csv              (18,250 data rows)
  → src/features/feature_builder.py:FeatureBuilder.build_features
  → data/features/training_features.parquet   (16,500 × 33 cols)
  → python -m src.training.train
      → src/training/pipeline.py:TrainingPipeline.run()
      → src/training/dataset.py:DatasetBuilder
            .build()  → 31 feature cols (drops `date` + target `y_units_sold`)
            .split()  → train_test_split(shuffle=True, test_size=0.2, random_state=42)
      → src/training/trainer.py:DemandModelTrainer.build_model()  (XGBRegressor, 600 trees)
      → src/training/evaluate.py:ModelEvaluator
      → joblib.dump → models/demand_model.pkl
      → models/features.json, reports/training_metrics.json, reports/feature_importance.csv
```

Verified facts:
- `scripts/regenerate_data.py` **runs cleanly** (exit 0) and rewrites the CSV + parquet.
- `python -m src.training.train` **runs and writes artifacts**. A fresh run produced `R2=0.4550`, `Train_R2=0.8845`, `MAE=26.27` (no effective early stopping; train R² ≫ val R²). The committed artifact has `R2=0.4682`, `Train_R2=0.6332`.
- `scripts/train_with_tuning.py` (the README-"recommended" path) **cannot run here** — dies at `import mlflow` (`scripts/train_with_tuning.py:9`).
- `scripts/promote_model.py` is manual, uses deprecated MLflow APIs, and promotes to Staging only; nothing calls it.

### Serving path (what actually runs)

```
uvicorn src.api.server:app
  → src/api/server.py:35  FastAPI app; middleware; router mounted at /v1
  → src/api/router.py:23  PricingEngine(config)  (module-import time)
        → src/pricing/engine.py:41  load_model(force=True)
              tries MLflow registry (engine.py:52-90) → no Production version/alias
              → joblib.load(models/demand_model.pkl)     ← ALWAYS taken with current state
              → loads models/features.json
  → POST /v1/optimize-price  (src/api/router.py:29)
        payload.model_dump(exclude={price_min,price_max,optimization_method,cost,
                                    min_margin_pct,inventory_limit})
        → PricingEngine.get_optimal_price (engine.py:105)
             method == "bayesian" (default) → BayesianPriceOptimizer.optimize (bayesian_optimizer.py)
                                                → vectorized dense price grid + refinement → true optimum
             method == "grid"               → PriceOptimizer.optimize → KeyError → 500
             method == "grid_search"        → ValueError "Unknown optimization method" → 500
        → PredictionLogger.log_optimization (router.py:72) → logs/predictions/*.jsonl
        → HealthChecker.record_request
        → PricingResponse(**result)  (schemas.py:79; extra key `model_version` ignored by Pydantic)
```

Verified: `GET /v1/health` → 200; `GET /v1/health/ready` → 200; `POST /v1/optimize-price` (bayesian, `price_min=70, price_max=110`) → 200 with `optimal_price=77.3725, expected_demand=76.918, expected_revenue=5951.36, optimization_success=True, optimization_iterations=2403` (re-verified 2026-09-29 after R1). The serving path was exercised via FastAPI `TestClient` with `mlflow` stubbed (because the real import is broken here).

### Frontend path
`app.py` (Streamlit) → HTTP `POST {api_url}/v1/optimize-price`. Broken contract as noted in §1 (reads `predicted_demand`, sends `grid_search`).

---

## 3. Dead code inventory

Modules/classes/functions defined but **never imported by the real running path** (training scripts + API). "Only tests" means reachable solely from `tests/`.

| Item | File | Referenced by |
|---|---|---|
| `IntegratedPricingOptimizer` | `src/pricing/integrated_optimizer.py` | Only `tests/test_integration.py:7` |
| `FeatureTransformer` | `src/features/transformer.py` | Only `integrated_optimizer.py:6` + `tests/test_integration.py:6` |
| `RevenueCalculator` | `src/pricing/revenue.py` | Nothing (zero references) |
| `load_production_model` | `src/pricing/model_loader.py:7` | Imported at `src/pricing/engine.py:14` but **never called** |
| demo script | `src/pricing/optimize.py` | Nothing |
| `MetricsTracker`, `Timer`, `get_metrics_tracker` | `src/monitoring/metrics_tracker.py` | Nothing |
| `ModelMonitor` (`calculate_drift`, `calculate_performance_metrics`, `check_model_degradation`) | `src/monitoring/model_monitor.py` | Nothing |
| `load_to_postgres` | `src/data/ingest.py:9` | Only `src/data/pipeline_runner.py:4`; its `__main__` points at a non-existent `synthetic_sales.csv` (`ingest.py:16`) |
| `main` | `src/data/pipeline_runner.py` | Nothing |
| `validate_data` | `src/data/validation.py:7` | Only `pipeline_runner.py:3` (+ its own `__main__`) |
| `load_config` | `src/utils/config.py:4` | Only `src/features/feature_pipeline.py:2` |
| `run_feature_pipeline` | `src/features/feature_pipeline.py:8` | Nothing |
| `EnvConfig.get_env` / `is_production` / `is_development` / `reload_config` | `src/utils/env_config.py:92,132,136,153` | Nothing (`get_config`, `get_bool`, `get_int` are used) |
| `ModelNotFoundError`, `OptimizationError`, `InvalidInputError` | `src/api/error_handlers.py:72,79,86` | Never raised. Even the base `APIError` is registered as a handler (`server.py:44`) but never raised — the router raises `HTTPException` instead. |
| `PricingEngine.compare_methods` | `src/pricing/engine.py:163` | Nothing |
| `PredictionLogger.log_prediction`, `load_logs` | `src/monitoring/prediction_logger.py:30,163` | Router uses only `log_optimization` / `log_error` |
| `MlflowTracker.*` | `src/utils/mlflow_tracking.py` | Only `scripts/train_with_tuning.py` (which cannot run here) |

Note: the stored coverage report omits `revenue.py`, `optimize.py`, `data/*`, `training/{trainer,dataset,pipeline}.py`, `utils/config.py`, `utils/mlflow_tracking.py`, `features/feature_builder.py`, `features/feature_pipeline.py` — consistent with them never being imported in the coverage run.

---

## 4. Config / env values defined but never read

Cross-referenced `configs/*.yaml` and `.env` against actual reads in `src/`.

### `configs/config.yaml` (also in dev/prod) — defined, never read

| Key | Where defined | Reality |
|---|---|---|
| `data.raw_path`, `data.processed_path` | `config.yaml:2-3` | Unused; paths come from `src/utils/paths.py` (`ROOT_DIR`). |
| `model.demand_model` | `config.yaml:7` | Unused. |
| `pricing.price_min_multiplier`, `price_max_multiplier`, `price_steps` | `config.yaml:19-21` | Unused; grid `steps` defaults to 50 in `engine.py:152`. |
| `pricing.default_method` | `config.yaml:28` | Unused; the schema default is `"bayesian"` (`schemas.py:36`). |
| `training.test_size`, `random_state` | `config.yaml:31-32` | Unused; hardcoded `0.2` / `42` in `dataset.py:39-40`. |
| `training.cv_folds` | `config.yaml:37` | Unused; hardcoded 5 (`pipeline.py:45`) and 3 (`train_with_tuning.py:86`). |
| `training.run_hyperparameter_tuning` | `config.yaml:39` | Unused; `train_with_tuning.py` always tunes. |
| entire `monitoring:` block (5 keys) | `config.yaml:49-54` | Unused by any `src/` code. |

Keys read by code but **absent** from config.yaml (rely on `.get` defaults): `pricing.registered_model_name` (`engine.py:29-31`), `pricing.reload_interval_sec` (`engine.py:32`).

### `configs/config.dev.yaml` / `config.prod.yaml` — defined, never read

| Block | Where | Reality |
|---|---|---|
| entire `api:` block (`host, port, workers, reload, timeout, cors_enabled, cors_origins, rate_limit_*`) | `config.dev.yaml:53-63`, `config.prod.yaml:53-63` | Never read. `src/api/server.py:48-71,108-111` reads these from **env vars** via `EnvConfig.get_bool/get_int` / `os.getenv`. |
| entire `logging:` block (`level, format, rotation, retention_days`) | `config.dev.yaml:65-69`, `config.prod.yaml:65-69` | Never read. `server.py:28-30` reads `LOG_LEVEL`/`LOG_FORMAT`/`LOG_DIR` from env. |

`EnvConfig._load_config` (`env_config.py:32-51`) loads dev/prod YAML only when `APP_ENV` matches, and validates only `model`/`pricing`/`features`; the `api:`/`logging:` sections are parsed but never consumed.

### `.env` variables

**Read by `src/`:** `APP_ENV`, `API_HOST`, `API_PORT`, `API_WORKERS`, `API_RELOAD`, `CORS_ORIGINS`, `RATE_LIMIT_ENABLED`, `RATE_LIMIT_REQUESTS`, `LOG_LEVEL`, `LOG_FORMAT`, `LOG_DIR`, `REQUEST_TIMEOUT`, `MLFLOW_TRACKING_URI`. (`TUNING_TRIALS` is read by `train_with_tuning.py:81` but is **not** in `.env`.)

**Defined but never read by any code** (decorative): `APP_NAME`, `APP_VERSION`, `DEBUG`, `CORS_ALLOW_CREDENTIALS`, `RATE_LIMIT_WINDOW`, `DATABASE_URL`, `DATABASE_BACKUP_ENABLED`, `DATABASE_BACKUP_INTERVAL`, `MODEL_PATH`, `FEATURES_PATH`, `MODEL_CACHE_ENABLED`, `MODEL_RELOAD_INTERVAL`, `LOG_ROTATION`, `LOG_RETENTION_DAYS`, `MONITORING_ENABLED`, `METRICS_ENABLED`, `HEALTH_CHECK_INTERVAL`, `PREDICTION_LOG_ENABLED`, `PREDICTION_LOG_DIR`, `PREDICTION_LOG_BATCH_SIZE`, `MODEL_INFERENCE_TIMEOUT`, `CACHE_TTL`, `ALERT_ERROR_THRESHOLD`, `MLFLOW_EXPERIMENT_NAME`.

**Read only by shell scripts (not `src/`):** `DATABASE_URL`, `DATABASE_BACKUP_RETENTION_DAYS`, `BACKUP_DIR`, `API_URL`, `LOG_DIR`, `CONCURRENT_REQUESTS`, `TOTAL_REQUESTS`. **`STREAMLIT_*`** are consumed by Streamlit itself.

---

## 5. Known-broken behavior (exact symptoms)

1. **Grid optimizer crashes.** `src/pricing/optimizer.py:28` → `KeyError: "['price_advantage', 'log_price', 'log_comp_price', 'price_advantage_sin', 'price_change_1d', 'price_change_7d', 'roll_mean_price_7', 'roll_mean_price_14', 'roll_mean_price_28'] not in index"`. Reproduced directly and via `POST /v1/optimize-price` with `optimization_method="grid"` → HTTP 500. This same KeyError is the **only** content of the local prediction logs (`logs/predictions/*.jsonl`, untracked).
2. **UI's grid method is rejected.** `app.py:130` sends `"grid_search"`; `engine.py:155-156` raises `ValueError: Unknown optimization method: grid_search` → HTTP 500.
3. ~~**"Bayesian" optimizer returns a bound or midpoint, never the true optimum.**~~ **Fixed 2026-09-29 (ROADMAP R1):** replaced the `scipy` L-BFGS-B call with a derivative-free dense price grid + local refinement. It now returns the true revenue optimum with `optimization_success=True`; for `(10,200)`/`(100,120)` the optimum is genuinely the upper bound. The method label is still misleading (DECISIONS D2 / R6).
4. **README's curl example 404s** — `README.md:133` omits `/v1`.
5. **`python src/training/train.py` fails** — `ModuleNotFoundError: No module named 'src'` (`README.md:106`).
6. **mlflow-coupled entry points fail to import in this environment:** `python -m src.api.server`, `scripts/train_with_tuning.py`, and `tests/test_api.py` all die with `ImportError: cannot import name 'service' from 'google.protobuf'`. Consequently `pytest tests/` **aborts at collection** (0 tests run); only `pytest tests/ --ignore=tests/test_api.py` yields the 17 passing tests.
7. **Streamlit cannot render a successful API response** — reads `result['predicted_demand']` (`app.py:203,207,227,229,230,373`) but API returns `expected_demand`; error swallowed by `except Exception` at `app.py:242`.
8. **Health check false-degrades with a registry model.** `health_checker.py:41-43` assumes `n_features_in_` (default 10) and feeds `np.zeros((1,10))`; an MLflow `pyfunc` wrapper lacks that attribute → predict raises → `/v1/health` returns 503.
9. **HF container can hang forever.** `start.sh:23-25` waits indefinitely for `/v1/health` 2xx; a 503 response loops with no retry limit and Streamlit never starts.
10. **Prod compose cannot start.** `docker-compose.prod.yml:53-54` bind-mounts `./nginx/nginx.conf` and `./nginx/ssl`, neither of which exists.
11. **`PredictionLogger.__del__` raises at interpreter shutdown:** `prediction_logger.py:203-205` calls `flush()` during teardown → `ImportError: sys.meta_path is None, Python is likely shutting down` (observed).
12. **MLflow misconfiguration is invisible.** `engine.py:91-94` catches bare `Exception` and logs a `warning`, then silently loads the local pickle — a broken registry looks like success. (And per §1, with the current registry state the fallback is *always* taken anyway.)
13. **Internal error strings leak to clients.** `router.py:108` returns `HTTPException(500, detail=str(e))`, exposing raw exception text (e.g. the full column list).
14. **SQLite is an orphan.** `data.db` holds 18,250 rows in `sales_data`, but no `src/` code reads or writes it; `src/data/ingest.py` is dead and its `__main__` targets a non-existent `synthetic_sales.csv`.
15. **`tests/smoke_tests.py` collects 0 tests** under pytest (class `SmokeTestRunner`, methods are not `test_*` functions). README's `pytest tests/smoke_tests.py` is wrong.
16. **`tests/test_data_drift.py` asserts drift exists** (`pvalue < 0.01`) in synthetic data and is not wired to the service.
17. **`product_id` is a model feature** (`models/features.json:2`; low importance 0.01195 in `reports/feature_importance.csv:30`) → the model cannot price an unseen product.
18. **`docker-compose.yml` has no build context** for `pricing-api` (`docker-compose.yml:35-36`) — requires a pre-built `dynamic-pricing:latest` image.

---

## 6. Corrections vs the prior audit (now removed)

The prior audit (`audit_Dynamic-Pricing-Engine.md`) was used as a hypothesis list and has since
been deleted (2026-09-28) as superseded by this file. Its findings agreed on the core
conclusions, with these corrections:

- **Nested duplicate repo:** the prior audit claims an untracked nested `Dynamic-Pricing-Engine/` clone with committed `__pycache__`. It is **not present** in this working tree (`ls Dynamic-Pricing-Engine` → No such file or directory). Disregard that item.
- **`docs/ARCHITECTURE.md` and `docs/`:** the prior audit cites feature claims "from `docs/ARCHITECTURE.md`", and the task prompt references it too. There is **no `docs/ARCHITECTURE.md`**; `docs/` is an empty directory. `README.md:351-357` links `docs/API.md`, `docs/OPERATIONS.md`, `DEPLOYMENT.md`, `PRODUCTION_FEATURES.md`, `PRODUCTION_READY.md` — all **missing**.
- **"17 tests pass":** true only with `--ignore=tests/test_api.py`. A plain `pytest tests/` **errors during collection** (mlflow import in `test_api.py`) and runs nothing. The prior audit understated this.
- **`.gitignore`:** as of 2026-09-28 it no longer ignores `.agents/` (so this directory is tracked) and no longer ignores `docs/` (previously `docs/` was ignored). See DECISIONS D15 / ROADMAP R33.
- **Bayesian results:** reproduced the prior audit's exact numbers: `(30,80)→80.0`, `(70,110)→90.0`, `(10,200)→200.0`, `(100,120)→120.0`.
- **Grid KeyError:** reproduced exactly (9 missing columns).
- **Prediction logs:** reproduced 27 error entries / 0 successful optimizations across the 8 committed JSONL files.
- **Stored coverage 69%:** confirmed via `coverage report` against the committed `.coverage`.
- **`configs/*.yaml`:** confirmed the entire `api:` and `logging:` blocks in dev/prod are never read, and the `monitoring:` block is never read.

---

Last verified: 2026-09-29, against commit b21e45a (ROADMAP R1 optimizer fix); all other rows were last verified against c32841f.
