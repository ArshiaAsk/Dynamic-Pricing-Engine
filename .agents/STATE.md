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
- **Fixed 2026-09-29 (R5):** `mlflow` 2.12.1 was unimportable (protobuf 7.35.1 removed `google.protobuf.service`; setuptools 82 removed `pkg_resources`). Installing `protobuf==4.25.9` + `setuptools<81` into the venv makes `import mlflow` succeed — verified with a file-registry round-trip (register → `set_registered_model_alias` → `pyfunc.load_model`). `pip check` now flags protobuf conflicts for `tensorflow` and `opentelemetry-proto` (which want protobuf>=5); **neither is imported anywhere in this repo**, so they are inert here. The serving path still imports `mlflow` lazily (R3) and, with no Production alias/stage in the configured registry, serves the local pickle.
- Prior audit used as a cross-check: `audit_Dynamic-Pricing-Engine.md` in repo root (the `/mnt/user-data/uploads/audit_Dynamic-Pricing-Engine.md` path given in the task **does not exist**). That file has since been reviewed, judged superseded by this one, and **deleted** (2026-09-28); the corrections it prompted are recorded in §6.

**Status legend:** `CONFIRMED` = real and works · `PARTIAL` = partially real / works with caveats · `FAKE-OR-DEAD` = exists but non-functional or never wired in · `NOT-FOUND` = claimed but absent.

---

## 1. Claim-by-claim verification

| Feature / claim (plain words) | Status | Evidence (file:line) | Gap / note |
|---|---|---|---|
| XGBoost demand-forecasting model | CONFIRMED | `src/training/trainer.py:18` (`XGBRegressor`); `models/demand_model.pkl` loads as `XGBRegressor`, `n_features_in_=31`; `models/features.json` (31 cols) | Real model, but trained on **synthetic** data from `src/data/generator.py`. |
| "~49% R² accuracy" | PARTIAL | `reports/training_metrics.json` → `R2: 0.4682` | "0.49" rounds 0.468 up. Also unreported: `MAPE: 0.40` (40% error), `Train_R2: 0.633`. |
| "Time-series validation" | FAKE-OR-DEAD | `src/training/dataset.py:36-42` → `train_test_split(..., shuffle=True)` | Actual split is a **random** split, not temporal. `TimeSeriesSplit` exists only in `src/training/trainer.py:81` (`cross_validate`), which is gated off by `training.run_cv: false` (`configs/config.yaml:36`) and never called by `train_with_tuning.py` (which uses default KFold `cross_val_score`, `src/training/hyperparameter_tuning.py:43-50`). |
| "Bayesian optimization" finds optimal price | CONFIRMED (algorithm fixed R1) / no longer served (R6) | `src/pricing/bayesian_optimizer.py` `optimize` → vectorized dense price grid + local refinement; no gradient call remains | The algorithm returns the true revenue optimum (verified R1/R7), but as of R6 `"bayesian"` is rejected at the API with HTTP 422 (DECISIONS D2), so the module is **unreachable from the serving path** and is pending deletion under D1/R22. The served optimizer is `PriceOptimizer` (honest `grid_search`). |
| Grid-search optimization method | CONFIRMED (fixed R2; shared builder R4; adaptive resolution + canonical name R6) | `src/pricing/optimizer.py` (`PriceOptimizer`) is the single served optimizer; `src/pricing/engine.py:150` defaults to `"grid_search"` and dispatches `"grid"`/`"grid_search"`; `src/api/schemas.py` types the method as `Literal["grid_search","grid"]` | No longer crashes (R2) and no longer undershoots (R6): the grid scales its candidate count with the bound width (target spacing 0.02, ≥901 points, cap 20001) and vectorizes `model.predict`. Served `grid_search` ratios vs the test-time 901-pt max: (30,80) 1.00034, (70,110) 1.00034, (10,200) 1.00000, (100,120) 1.00000, (30,120) 1.00078 — all ≥ 0.99. `PriceOptimizer.optimize_with_constraints` covers the margin/inventory contract. |
| Business constraints (min margin, inventory, price bounds) | CONFIRMED | `src/pricing/optimizer.py` `optimize_with_constraints` (margin lifts lower bound) + `optimize(inventory_limit=...)` (inventory caps demand) — the served path since R6; `src/pricing/bayesian_optimizer.py` retains the R1 equivalent | Real and applied to a genuine optimum. Reproduced: `optimize_with_constraints(base, 30, 120, cost=60, min_margin_pct=0.15)` → price 77.36, `profit_margin=0.2244`; `optimize(..., inventory_limit=50)` → `expected_demand ≤ 50`. |
| Automated feature engineering (calendar/price/temporal) | CONFIRMED | `src/features/feature_builder.py:29-134` | Real lag/rolling/seasonality/price-interaction features using `shift(1)` (no target leakage). Caveat: raw `product_id` is a model feature (`models/features.json:2`) → won't generalize to unseen products. |
| Optuna hyperparameter tuning (up to 50 trials) | CONFIRMED (code) / PARTIAL (runnable) | `src/training/hyperparameter_tuning.py:23-92` (real TPE study); invoked at `scripts/train_with_tuning.py:86` | Genuine Optuna code. The former import-time blocker is gone: with mlflow importable (R5 venv fix), `scripts/train_with_tuning.py` now imports cleanly (verified). A full end-to-end tuning run was **not** executed here (long-running), so the script remains "PARTIAL (runnable)". |
| Data drift detection | FAKE-OR-DEAD | `src/monitoring/model_monitor.py:59-120` (`calculate_drift`) | Never imported or called anywhere. The only "drift test" (`tests/test_data_drift.py:19`) asserts `pvalue < 0.01`, i.e. it asserts drift *exists* in random synthetic data, and is not connected to the service. |
| Model performance monitoring / degradation alerts | FAKE-OR-DEAD | `src/monitoring/model_monitor.py:122-204` | `calculate_performance_metrics` / `check_model_degradation` never imported. No actuals feedback loop exists. |
| Prediction logging / audit trail | CONFIRMED | `src/monitoring/prediction_logger.py`; called at `src/api/router.py:72,96`; outputs in `logs/predictions/*.jsonl` | Real JSONL audit log. But all 8 log files present locally (untracked — `logs/` is gitignored, so they are **not** committed) contain **only** `type: "error"` entries (27 total, 0 successful optimizations) — evidence the API was never used successfully end-to-end. |
| Comprehensive metrics (MAE/RMSE/R²/MAPE/directional) | CONFIRMED | `src/training/evaluate.py:15-98`; values in `reports/training_metrics.json` | All computed for real. |
| FastAPI service + Swagger/ReDoc | CONFIRMED | `src/api/server.py:35-41` (`docs_url="/docs"`, `redoc_url="/redoc"`); router mounted at `/v1` (`server.py:74`) | Works with the real (broken) `mlflow`: R3 (2026-09-29) made the `mlflow` import lazy (`src/pricing/engine.py:52-53`), so `python -m src.api.server` starts and `GET /v1/health` → 200 on the local pickle — no stub needed. |
| Health / readiness / liveness endpoints | CONFIRMED (fixed 2026-09-29, R13; source exposed R5) | `src/api/router.py:111-137`; `src/monitoring/health_checker.py::_probe_model` | Real endpoints (verified 200). R13 removed the hardcoded `getattr(model, "n_features_in_", 10)` probe: the model check now predicts on a zero-row DataFrame of the *served* feature columns, so a native `XGBRegressor` **and** an `mlflow.pyfunc` wrapper both report `status: "ok"` (previously the pyfunc case raised `Feature shape mismatch, expected: 31, got 10` → 503). R5 also exposes `checks.model.source` (`"local"`/`"mlflow"`) and `checks.model.version`. |
| `/metrics` endpoint | PARTIAL | `src/api/router.py:140-146` | Returns custom JSON (`health` + `predictions`), **not** Prometheus exposition format. |
| Prometheus integration | FAKE-OR-DEAD | `requirements.txt:38` declares `prometheus-client`; zero imports in repo | `src/monitoring/metrics_tracker.py` is a hand-rolled in-memory dict that is itself never imported. No instrumentation. |
| Rate limiting | CONFIRMED | `src/api/middleware.py:68-108`; enabled at `src/api/server.py:64-67` | Real in-memory per-IP sliding window, toggled by `RATE_LIMIT_ENABLED`. |
| Input validation | CONFIRMED | `src/api/schemas.py:5-77` | Real Pydantic constraints + `price_max > price_min` validator (`:43-48`). `optimization_method` is a `Literal["grid_search","grid"]` (default `grid_search`), so `"bayesian"`/unknown values → HTTP 422 (R6). |
| Error handling / graceful shutdown | PARTIAL | `src/api/middleware.py`, `src/api/error_handlers.py`, `src/api/server.py:77-92` | Handlers exist. Remaining problem: `router.py:91-108` catches bare `Exception` and returns `detail=str(e)` (leaks internal errors to clients) — R16. The former second problem is fixed: `engine.load_model` no longer silently swallows MLflow failures — it logs at **ERROR** and records the degraded source (R5). |
| Structured JSON logs | CONFIRMED | `src/utils/logger.py:11-44`, `:82-100` | Real JSON formatter + file handler. |
| Log rotation | FAKE-OR-DEAD | `src/utils/logger.py:98` → plain `logging.FileHandler` | No `RotatingFileHandler`/`TimedRotatingFileHandler`. `LOG_ROTATION`/`LOG_RETENTION_DAYS` (`.env:41-42`) are never read. README's "rotation" is a manual `find ... -delete` snippet (`README.md:284`). |
| Docker deployment | CONFIRMED (caveats) | `Dockerfile`, `Dockerfile.hf`, `Dockerfile.prod`, `docker-compose*.yml` | Real images; `Dockerfile.prod:36` runs non-root `appuser`. Caveats: `Dockerfile:1` base is the `docker.arvancloud.ir` mirror; `docker-compose.yml:36` references `image: dynamic-pricing:latest` with **no `build:` context** (needs a pre-built image). |
| Nginx reverse proxy | FAKE-OR-DEAD | `docker-compose.prod.yml:53-54` mounts `./nginx/nginx.conf` and `./nginx/ssl` | `nginx/` **does not exist**. `docker-compose -f docker-compose.prod.yml up` fails on the missing bind mounts. No nginx config anywhere. |
| Automated AWS EC2 deployment + rollback | NOT-FOUND | `README.md:200-218` | `scripts/deploy.sh` and `scripts/pre_deploy_check.sh` are **missing**. Only `health_check.sh`, `metrics.sh`, `logs.sh`, `load_test.sh`, `backup_database.sh`, `restore_database.sh`, `run_smoke_tests.sh` exist. |
| CI/CD (test automation, image builds, smoke tests) | NOT-FOUND | no `.github/` directory, no workflow files | Dead CI metadata code remains at `scripts/train_with_tuning.py:28-35` (`GITHUB_RUN_ID`, etc.). |
| Unit / integration / smoke tests | PARTIAL | `tests/` | As of R9/R10/R11 (2026-09-29) a plain `pytest tests/` **exits 0 with 0 collection errors: 60 passed, 2 skipped (62 collected)**. `tests/conftest.py` provides a repo-root `sys.path` bootstrap and the shared lazy-import `client` fixture; `tests/test_api.py` no longer imports `src.api.server` at module level. `tests/test_optimizer_real.py` (R7) runs both optimizers against the committed `models/demand_model.pkl` + `models/features.json` and **fails** when R1/R2 are reverted; R6 added `test_served_grid_optimizer_reaches_reference_optimum` (all five bounds, fails 2/5 pre-fix). R9 added the API-level contract + grid-path ratio tests to `tests/test_api.py`; R10/R11 added `tests/test_streamlit_contract.py` (UI-read keys ⊆ `PricingResponse.model_fields`; no fabricated response keys). Earlier: `tests/test_serving_features.py` (R4), `tests/test_mlflow_registry.py` (R5), `tests/test_health_model_type.py` (R13). Still open: `pytest tests/smoke_tests.py` collects **0** (class `SmokeTestRunner` holds methods, not module-level `test_*`) — R14; `tests/test_optimizer.py:18` mocks a *smooth* model; `tests/test_integration.py` exercises the **dead** `IntegratedPricingOptimizer`. Stored coverage: **69%** (`.coverage`, dated Jun 6). |
| SQLite DB + backup/restore, 7-day retention | PARTIAL | `scripts/backup_database.sh`, `scripts/restore_database.sh`, `data.db` | `data.db` exists with a populated `sales_data` table (18,250 rows), but **no `src/` code reads or writes it** (no `DATABASE_URL` usage outside shell scripts). Backup/restore scripts are real; retention defaults to 7 days. |
| MLflow model versioning | PARTIAL (loud fallback fixed R5; registry not promoted by default) | `src/utils/mlflow_tracking.py`, `scripts/train_with_tuning.py:136-140`, `src/pricing/engine.py`, `scripts/promote_model.py`, `mlruns/`, `mlflow.db` | `mlflow` is importable again (R5 venv fix). The engine resolves the `production` **alias** (fallback: `tags.stage='Production'`) and loads via `models:/<name>@production`; when neither exists it logs at **ERROR** and serves the local pickle, exposing `checks.model.source == "local"`. `scripts/promote_model.py` now uses `set_registered_model_alias`/`set_model_version_tag` (no deprecated calls) and defaults to the repo's local `mlruns/` file store. Registry has `demand_forecasting_model` v1 & v2 with no production alias by default, so the serve-time fallback is still taken unless `promote_model.py` is run. Verified by `tests/test_mlflow_registry.py` (isolated temp registry). README still lists MLflow under "Future Enhancements" (`README.md:419`) while the code depends on it (R23). |
| Streamlit UI (Quick/Advanced/Batch) | CONFIRMED (fixed 2026-09-29, R10/R11) | `app.py` | Reads `expected_demand` — the API field (`src/api/schemas.py:89`) — so the Quick tab renders Optimal Price / Predicted Demand / Est. Revenue with no `KeyError` (verified with `streamlit.testing.v1.AppTest` against a live API). The method selectbox offers only `grid_search`/`grid` (the rejected legacy `"bayesian"` is gone). The Advanced tab renders the live `PricingResponse` schema from `/openapi.json`; the fabricated `example_response` (`confidence_interval`, `optimization_metadata`) is removed. `tests/test_streamlit_contract.py` asserts the UI-read keys ⊆ `PricingResponse.model_fields` and that no fabricated keys remain (CONVENTIONS rules 25/29). |
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
        → src/pricing/engine.py  load_model(force=True)
              lazily imports mlflow (R3); bounds MLFLOW_HTTP_REQUEST_TIMEOUT=5 / _MAX_RETRIES=1 (R5)
              resolves the 'production' alias, else tags.stage='Production' (R5)
              no production version/alias → logger.error(...) → joblib.load(models/demand_model.pkl)
              → sets model_source="local" | _current_version=None  (exposed by /v1/health, R5)
              → loads models/features.json
  → POST /v1/optimize-price  (src/api/router.py:29)
        payload.model_dump(exclude={price_min,price_max,optimization_method,cost,
                                    min_margin_pct,inventory_limit})
        → PricingEngine.get_optimal_price (engine.py:145)
             method in ("grid","grid_search") → PriceOptimizer.optimize (optimizer.py)
                                                → adaptive dense price grid (spacing ≤0.02, ≥901 pts) → real optimum (R2/R6)
             "bayesian"/unknown             → rejected by the PricingRequest schema (Literal) → HTTP 422 (R6)
        → PredictionLogger.log_optimization (router.py:72) → logs/predictions/*.jsonl
        → HealthChecker.record_request
        → PricingResponse(**result)  (schemas.py:79; extra key `model_version` ignored by Pydantic)
```

Verified: `GET /v1/health` → 200 (now including `checks.model.source == "local"`); `GET /v1/health/ready` → 200; `POST /v1/optimize-price` (`optimization_method="grid_search"`, `price_min=70, price_max=110`) → 200 with `optimal_price=77.36, expected_revenue=5950.398` (re-verified 2026-09-29 after R6); `"grid"` → 200; `"bayesian"` and unknown methods → **422**. As of R5 the venv's `mlflow` is importable again; the engine still serves the local pickle because the configured registry has no production alias, but it now logs the fallback at ERROR and exposes the source. `python -m src.api.server` → `GET /v1/health` → 200, and a plain `pytest tests/` collects and passes (as of R6: 55 collected, 53 passed, 2 skipped).

### Frontend path
`app.py` (Streamlit) → HTTP `POST {api_url}/v1/optimize-price`. Contract fixed (R10/R11): the UI reads `expected_demand`, the method selectbox offers only `grid_search`/`grid` (no rejected `"bayesian"`), and the Advanced tab renders the live `PricingResponse` schema from `/openapi.json`. `tests/test_streamlit_contract.py` guards the field/method contract.

---

## 3. Dead code inventory

Modules/classes/functions defined but **never imported by the real running path** (training scripts + API). "Only tests" means reachable solely from `tests/`.

| Item | File | Referenced by |
|---|---|---|
| `IntegratedPricingOptimizer` | `src/pricing/integrated_optimizer.py` | Only `tests/test_integration.py:7` |
| `FeatureTransformer` | `src/features/transformer.py` | Only `integrated_optimizer.py:6` + `tests/test_integration.py:6` |
| `RevenueCalculator` | `src/pricing/revenue.py` | Nothing (zero references) |
| `load_production_model` | `src/pricing/model_loader.py:4` | Imported at `src/pricing/engine.py:11` but **never called** |
| demo script | `src/pricing/optimize.py` | Nothing |
| `MetricsTracker`, `Timer`, `get_metrics_tracker` | `src/monitoring/metrics_tracker.py` | Nothing |
| `ModelMonitor` (`calculate_drift`, `calculate_performance_metrics`, `check_model_degradation`) | `src/monitoring/model_monitor.py` | Nothing |
| `load_to_postgres` | `src/data/ingest.py:9` | Only `src/data/pipeline_runner.py:4`; its `__main__` points at a non-existent `synthetic_sales.csv` (`ingest.py:16`) |
| `main` | `src/data/pipeline_runner.py` | Nothing |
| `validate_data` | `src/data/validation.py:7` | Only `pipeline_runner.py:3` (+ its own `__main__`) |
| `load_config` | `src/utils/config.py:4` | Only `src/features/feature_pipeline.py:2` |
| `run_feature_pipeline` | `src/features/feature_pipeline.py:8` | Nothing |
| `EnvConfig.get_env` / `is_production` / `is_development` / `reload_config` | `src/utils/env_config.py:92,132,136,153` | Nothing (`get_config`, `get_bool`, `get_int` are used) |
| `BayesianPriceOptimizer` | `src/pricing/bayesian_optimizer.py` | Only tests as of R6 (`tests/test_optimizer.py`, `tests/test_serving_features.py`, `tests/test_optimizer_real.py`) |
| `ModelNotFoundError`, `OptimizationError`, `InvalidInputError` | `src/api/error_handlers.py:72,79,86` | Never raised. Even the base `APIError` is registered as a handler (`server.py:44`) but never raised — the router raises `HTTPException` instead. |
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
| `pricing.default_method` | `config.yaml:28` | Unused; the schema default is `"grid_search"` (`schemas.py`). The YAML value was corrected from `bayesian` to `grid_search` in R6 (naming honesty). |
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

1. ~~**Grid optimizer crashes.**~~ **Fixed 2026-09-29 (ROADMAP R2, commit `ffc55fe`):** `PriceOptimizer` now builds the complete 31-column frame, so `optimize(base,70,110,50)` returns a price/revenue and the API `grid_search`/`grid` return HTTP 200. The old symptom was `KeyError: "['price_advantage', 'log_price', 'log_comp_price', 'price_advantage_sin', 'price_change_1d', 'price_change_7d', 'roll_mean_price_7', 'roll_mean_price_14', 'roll_mean_price_28'] not in index"` (reproduced before the fix, directly and via `POST /v1/optimize-price` → HTTP 500); it was the **only** content of the local prediction logs (`logs/predictions/*.jsonl`, untracked). The R2 coarse-grid caveat (fixed 50-point grid undershooting wide bounds) is **resolved 2026-09-29 (R6, `b48d18a`)**: the grid now scales with bound width; all served ratios ≥ 0.99 (see §1 grid row).
2. ~~**UI's grid method is rejected.**~~ **Resolved 2026-09-29 (R2/R6):** the engine accepts `grid_search`/`grid`, and R6 made them the **only** accepted methods (`"bayesian"`/unknown → 422). The remaining UI problem is unrelated: `app.py`'s selectbox still offers `"bayesian"` (`app.py:128-132`) — which now 422s — and it cannot render a successful response because it reads `predicted_demand` while the API returns `expected_demand` (see §5.7; ROADMAP R10).
3. ~~**"Bayesian" optimizer returns a bound or midpoint, never the true optimum.**~~ **Fixed 2026-09-29 (ROADMAP R1):** replaced the `scipy` L-BFGS-B call with a derivative-free dense price grid + local refinement. It now returns the true revenue optimum with `optimization_success=True`; for `(10,200)`/`(100,120)` the optimum is genuinely the upper bound. The misleading label is **resolved 2026-09-29 (R6, `b48d18a`)**: the API's only method is the honestly named `grid_search`, `"bayesian"` is rejected with HTTP 422 (DECISIONS D2), and `BayesianPriceOptimizer` is unreachable from serving (pending deletion, D1/R22).
4. **README's curl example 404s** — `README.md:133` omits `/v1`.
5. **`python src/training/train.py` fails** — `ModuleNotFoundError: No module named 'src'` (`README.md:106`).
6. ~~**mlflow-coupled entry points fail to import in this environment.**~~ **Fully resolved 2026-09-29.** R3 (commit `0ba7d5a`) made the serving path import `mlflow` lazily, and R5 fixed the root cause: `protobuf==4.25.9` + `setuptools<81` are now installed, so `import mlflow` succeeds. `python -m src.api.server`, `tests/test_api.py`, `scripts/promote_model.py`, and `scripts/train_with_tuning.py` all import cleanly (verified). A plain `pytest tests/` collects and passes (as of R4/R5/R13: 47 collected, 45 passed, 2 skipped).
7. ~~**Streamlit cannot render a successful API response**~~ **Fixed 2026-09-29 (ROADMAP R10/R11, commits `bfa06eb`/`b7abaff`):** `app.py` now reads `expected_demand` (the API field), offers only the accepted `grid_search`/`grid` methods, and the Advanced tab shows the live `/openapi.json` schema instead of a fabricated response. Verified by `streamlit.testing.v1.AppTest` (renders all three Quick-tab metrics, no `KeyError`, no `st.error`) and `tests/test_streamlit_contract.py`.
8. ~~**Health check false-degrades with a registry model.**~~ **Fixed 2026-09-29 (ROADMAP R13, commit `efe4d5e`):** the probe no longer uses `getattr(model, "n_features_in_", 10)`; it predicts on a zero-row DataFrame of the *served* feature columns, so a native `XGBRegressor` and an `mlflow.pyfunc` wrapper both report `status: "ok"`. Pre-fix, the pyfunc case raised `Feature shape mismatch, expected: 31, got 10` → 503 (reproduced).
9. **HF container can hang forever.** `start.sh:23-25` waits indefinitely for `/v1/health` 2xx; a 503 response loops with no retry limit and Streamlit never starts.
10. **Prod compose cannot start.** `docker-compose.prod.yml:53-54` bind-mounts `./nginx/nginx.conf` and `./nginx/ssl`, neither of which exists.
11. **`PredictionLogger.__del__` raises at interpreter shutdown:** `prediction_logger.py:203-205` calls `flush()` during teardown → `ImportError: sys.meta_path is None, Python is likely shutting down` (observed).
12. ~~**MLflow misconfiguration is invisible.**~~ **Fixed 2026-09-29 (ROADMAP R5, commit `fdce6c4`):** `engine.load_model` now logs the fallback at **ERROR** (not `warning`), records `model_source == "local"`, and exposes it via `/v1/health` (`checks.model.source`); registry calls are bounded (`MLFLOW_HTTP_REQUEST_TIMEOUT=5`, `_MAX_RETRIES=1`) so a dead tracking server fails fast instead of 504-ing after the 30s request timeout.
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

Last verified: 2026-09-29, against commit `bc2f674` (this session: R9 API contract + grid-path test `bc2f674`, R10 Streamlit response contract `bfa06eb`, R11 Advanced-tab fabricated response removed `b7abaff`); earlier: R6 canonical `grid_search` + HTTP 422 for legacy/unknown methods + adaptive grid resolution `b48d18a`, R4 shared serving feature builder `946eae9`, R5 loud/correct MLflow registry resolution + `promote_model.py` rewrite + mlflow venv fix `fdce6c4`, R13 health-check model-type fix `efe4d5e`, R8 pytest collection `8791772`, R7 real-model regression test `75151b3`, R1 optimizer fix `b21e45a`, R2 grid-search fix `ffc55fe`, R3 lazy mlflow import `0ba7d5a`. All other rows were last verified against `c32841f`.
