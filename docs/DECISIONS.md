# Architecture decision log

This is the historical decision log for the Dynamic Pricing Engine. It records the
decisions that shaped the rebuild, in the order they were made. Each entry has a date, a
status, the context, the decision and its consequences.

**Status values:** `accepted` (approved and in force) · `superseded` (replaced by a later
entry or by a repository rule; the entry links to its successor).

**Current status at P2 closure (2026-10-22):** D1, D2, D4–D13, D15–D21 and D24–D31 are
`accepted`. **D3, D14, D22 and D23 are `superseded`** and are kept for the record. D15 is
historical: the agent records directory it created was replaced by this `docs/` directory.

The implementation pointer for each decision is in the table below. Paths and test names
are current unless the entry says otherwise. The entries themselves are historical and may
mention files that were later deleted; those mentions describe the state at the time.

| ID | Status | Implementation |
|---|---|---|
| D1 | accepted | One optimizer in `src/pricing/optimizer.py`; the alternate optimizer and transformer were deleted (`30e59f9`, `c4b9fb1`). |
| D2 | accepted | `PriceOptimizer` dense grid search; `tests/test_optimizer_real.py`, `tests/test_api.py`. |
| D3 | superseded by D2 | Merged into D2. |
| D4 | accepted | `src/pricing/features.py`; `tests/test_serving_features.py`. |
| D5 | accepted | `product_id` absent from `models/features.json`; `tests/test_product_id_contract.py`, `tests/test_training_data.py`. |
| D6 | accepted | `src/training/dataset.py`; `tests/test_training_data.py`. |
| D7 | accepted | Lazy MLflow import in `src/pricing/engine.py`; `tests/test_mlflow_registry.py`. |
| D8 | accepted | Local artifact fallback and `model_source`; `tests/test_mlflow_registry.py`. |
| D9 | accepted | SQLite ingestion chain deleted; `tests/test_import_graph.py`. |
| D10 | accepted | JSONL prediction log; `tests/test_prediction_logger.py`. |
| D11 | accepted | Single YAML config plus env vars; `tests/test_config.py`, `tests/test_env.py`. |
| D12 | accepted | Dead modules deleted; `tests/test_import_graph.py`. |
| D13 | accepted | Drift code removed; `tests/test_import_graph.py`. |
| D14 | superseded | Covered by convention 26. |
| D15 | accepted (historical) | Agent records were committed, then moved to `docs/` in the P2 closure. |
| D16 | accepted | Public base images in `Dockerfile` and `Dockerfile.mlflow`. |
| D17 | accepted | nginx service removed; `docker-compose.yml`. |
| D18 | accepted | `.github/workflows/ci.yml`; `tests/test_ci_workflow.py`. |
| D19 | accepted | AWS claims removed; `tests/test_readme_truth.py`. |
| D20 | accepted | Streamlit UI kept; `tests/test_streamlit_contract.py`. |
| D21 | accepted | Generic 500 responses; `tests/test_api.py`. |
| D22 | superseded | Documented as a limitation in `docs/LIMITATIONS_AND_NEXT_STEPS.md`. |
| D23 | superseded | Synthetic data is labelled throughout `docs/` and the README. |
| D24 | accepted | Module-form entry points; `scripts/verify_readme.sh`. |
| D25 | accepted | `scripts/check_coverage.py` and the CI coverage gates. |
| D26 | accepted | `configs/config.yaml`; `tests/test_config.py`. |
| D27 | accepted | Pinned `requirements.txt`; `tests/test_requirements_pinned.py`. |
| D28 | accepted | `mlflow.db` ignored; `tests/test_repo_hygiene.py`. |
| D29 | accepted | `.dockerignore` tracked and cleaned; `tests/test_repo_hygiene.py`. |
| D30 | accepted | Seeded generator, config-driven size, model built in the image; `tests/test_generator_determinism.py`, `tests/test_dockerfile_model_build.py`. |
| D31 | accepted | Hardened image, pinned MLflow image, compose hardening; `tests/test_dockerfile_hardening.py`, `tests/test_compose_files.py`, `scripts/docker_smoke.sh`. |

---

## D1: Keep a single canonical price optimizer with one strategy
Date: 2026-09-27 (revised 2026-09-28 to be consistent with D2)
Status: accepted
Context: Three optimizer implementations exist (`BayesianPriceOptimizer`, `PriceOptimizer`, `IntegratedPricingOptimizer`); only the first two are reachable from the API, and the third is dead code tested only by `tests/test_integration.py`. Keeping two reachable strategies ("bayesian" + "grid") is what allowed the misleading label and the divergent feature builders.
Decision: Keep exactly **one** optimizer module exposing exactly **one** strategy — the canonical vectorized dense price-grid search defined in D2 — and delete `src/pricing/integrated_optimizer.py` (plus `src/features/transformer.py`, which exists only to serve it). No second strategy is retained "for later".
Consequences: `tests/test_integration.py` must be deleted or rewritten against the surviving optimizer (ROADMAP R22); no new optimizer may be added without deleting the one it replaces. Consistent with D2 (single canonical search) and ROADMAP R6.

## D2: Single canonical optimizer = vectorized dense price-grid search, named `grid_search`
Date: 2026-09-27 (merged with D3 on 2026-09-28)
Status: accepted
Context: The default optimizer runs `scipy.optimize.minimize(method='L-BFGS-B')` — a gradient method — on a piecewise-constant XGBoost objective, so it returns a bound or midpoint instead of an optimum (`bayesian_optimizer.py:74`; STATE.md §5.3). The same method is labelled "bayesian" although no Bayesian library is used, which is a misleading name (CONVENTIONS rule 24). These were previously two entries (D2 search, D3 naming); they are one decision.
Decision: Use a **vectorized dense price-grid search** as the single canonical optimizer (exact for piecewise-constant models), honestly named `grid_search`, with `grid` accepted as an alias. Remove all gradient-based calls on the tree objective. The name `"bayesian"` is **REJECTED** — the final decision (owner, 2026-09-29) is that `POST /v1/optimize-price` with `optimization_method="bayesian"` (or any unrecognized value) returns HTTP 422; there is no deprecated alias.
Consequences: Requires ROADMAP R1/R2 and their acceptance tests R7/R9; rules out `scipy` gradient methods for the served optimizer. `src/api/schemas.py`'s enum/validator accepts only `"grid_search"` and its alias `"grid"`; `"bayesian"` and any other value are invalid input (HTTP 422 Pydantic/enum validation error), not silently normalized. Supersedes D3.

## D3: Rename optimization methods to match what they do
Date: 2026-09-27
Status: superseded by D2 (merged 2026-09-28)
Context: The method is labelled "bayesian" but no Bayesian library is used; this is a misleading label (CONVENTIONS rule 24).
Decision: (Superseded — folded into D2, which fixes both the search method and its name in one entry: canonical `grid_search`, alias `grid`.)
Consequences: (Superseded — see D2. Unknown method values must return 4xx, not 500; the legacy `"bayesian"` method is rejected with HTTP 422, per D2.)

## D4: One source of truth for feature construction (train and serve)
Date: 2026-09-27 (accepted 2026-10-16)
Status: accepted
Context: Training builds features in `src/features/feature_builder.py`, while serving builds them ad hoc in each optimizer (`bayesian_optimizer._build_features`, `optimizer.optimize`), and a third path lives in `src/features/transformer.py`; the divergence is what caused the grid `KeyError`.
Decision: Define the serving feature set once and have both optimizers consume it, keeping it explicitly consistent with the training feature list in `models/features.json`; delete the unused `transformer.py` path.
Consequences: Requires ROADMAP R4 and a test asserting both optimizers emit identical feature vectors; any feature added to training must be added to the serving builder in the same PR.
Implementation note (2026-10-16): implemented via R4 — `src/pricing/features.py::build_serving_features` is the single serving builder; `transformer.py` and the second optimizer were deleted in R22, so the "both optimizers" wording above is historical.

## D5: Drop `product_id` as a model feature
Date: 2026-09-27 (accepted 2026-09-30)
Status: accepted
Context: `product_id` is a raw model feature (`models/features.json:2`), so the model partly memorizes per-product means and cannot price an unseen product.
Decision: Remove `product_id` from the feature set (or replace it with an out-of-fold target encoding if product-level signal must be retained), and retrain.
Consequences: Requires ROADMAP R12 and a metric re-report; rules out claiming the model generalizes to new products while `product_id` remains a raw feature.

## D6: Use a chronological train/validation split
Date: 2026-09-27 (accepted 2026-09-30)
Status: accepted
Context: The pipeline uses `train_test_split(shuffle=True)` but the README calls it "time-series validation" (STATE.md §1).
Decision: Split chronologically (hold out the last N days) and report the split honestly in the README.
Consequences: Requires ROADMAP R12 and updated metrics; the reported R² will likely change and must be regenerated, not carried over.

## D7: MLflow becomes an optional, lazily-imported dependency
Date: 2026-09-27 (accepted 2026-10-17)
Status: accepted
Context: `import mlflow` at module top level makes the API, the tuning script, and `tests/test_api.py` fail to start when MLflow is unavailable (`engine.py:9`), and the committed registry has no Production version anyway.
Decision: Make MLflow optional and import it lazily; the API must start and serve from the local model artifact with MLflow absent or misconfigured.
Consequences: Requires ROADMAP R3 and a test that imports the API with MLflow unavailable; rules out any top-level unconditional `import mlflow` on the serving path.
Implementation note (2026-10-17): implemented via R3 (mlflow lazy import); the premise about the top-level import is historical.

## D8: Local model artifact is the serving source of truth
Date: 2026-09-27 (accepted 2026-10-16)
Status: accepted
Context: The engine attempts an MLflow registry load but always falls back to `models/demand_model.pkl`; the registry has no Production stage/alias, so the "versioned model" path is dead at serve time.
Decision: Treat `models/demand_model.pkl` + `models/features.json` as the canonical served artifact; use MLflow only for experiment tracking and, optionally, a registry that must be explicitly promoted.
Consequences: Requires ROADMAP R5 (loud, correct fallback) and R8/R9 (tests run against the local artifact); the README must not imply registry-driven serving until a Production alias actually exists.
Implementation note (2026-10-16): local `models/demand_model.pkl` + `models/features.json` are the canonical served artifact; the MLflow registry lookup (`engine._resolve_production`/`load_model`) stays as an optional, explicitly promoted path (`scripts/promote_model.py`) with a loud fallback; the README must not imply registry-driven serving until a production alias exists (handled in R23).

## D9: Remove the SQLite ingestion path
Date: 2026-09-27 (accepted 2026-10-15)
Status: accepted
Context: `data.db` holds 18,250 rows but no `src/` code reads or writes it; `src/data/ingest.py` is dead and its `__main__` targets a non-existent file.
Decision: Remove the SQLite path — delete `src/data/ingest.py`, `data.db`, `src/data/pipeline_runner.py`, and the DB backup/restore scripts — rather than wire it in, since the demo's state lives in files (parquet/CSV/JSONL).
Consequences: Requires ROADMAP R29 and README cleanup; rules out any claim of database-backed persistence or 7-day retention until a real consumer exists.
Implementation note (user decision, 2026-10-15): The agent must **not** delete the local `data.db`. It is untracked and gitignored (machine-local state), and the owner will remove it themselves. R22/R29 delete `src/data/ingest.py`, `src/data/pipeline_runner.py`, `src/data/validation.py`, and the DB backup/restore scripts (`scripts/backup_database.sh`, `scripts/restore_database.sh`); the README DB claims remain for R23.

## D10: Keep prediction logs as JSONL files
Date: 2026-09-27 (accepted 2026-10-15)
Status: accepted
Context: `PredictionLogger` writes JSONL audit logs and is genuinely wired into the API; the SQLite alternative is orphaned.
Decision: Keep the JSONL prediction log as the audit store and drop the database claims.
Consequences: Depends on D9; log retention/rotation must be handled explicitly (see D11) rather than assumed.

## D11: Pick one configuration mechanism per concern
Date: 2026-09-27 (accepted 2026-10-16)
Status: accepted
Context: The API reads runtime settings from env vars while `configs/config.dev.yaml`/`prod.yaml` carry unread `api:` and `logging:` blocks, and `config.yaml` carries an unread `monitoring:` block.
Decision: Use env vars for runtime toggles (API host/port/workers, rate limit, logging, timeouts) and YAML for model/training/feature parameters; delete every config key that is not read.
Consequences: Requires ROADMAP R18/R19 and a test that fails on any unread YAML key or `.env` variable; rules out keeping decorative config sections.
Implementation note (2026-10-16): implemented via R18/R19/R35 and enforced by `tests/test_config.py` and `tests/test_env.py`.

## D12: Delete dead modules rather than keep them "for later"
Date: 2026-09-27 (accepted 2026-10-15)
Status: accepted
Context: A dozen modules are never reached by the API or training path (`revenue.py`, `metrics_tracker.py`, `utils/config.py`, `features/feature_pipeline.py`, `pricing/model_loader.py`, `data/validation.py`, etc.).
Decision: Delete every orphan module (or wire it into production with a test) in the same PR that touches it; "reachable only from tests" counts as dead.
Consequences: Requires ROADMAP R22 and an import-graph test; rules out committing scaffolding for features that do not exist.

## D13: Drop drift detection and performance-monitoring claims for the demo
Date: 2026-09-27
Status: accepted
Context: `ModelMonitor` (drift + degradation) is never imported, and `tests/test_data_drift.py` asserts that drift exists rather than validating the service.
Decision: Remove the drift/monitoring modules and tests and strike the claims from the README, unless a real consumer (endpoint/CLI with a passing test) is built instead.
Consequences: Requires ROADMAP R15 and README honesty (R23); there is no third state where the code stays dead but the claim stays in the docs. **Accepted 2026-10-07 retroactively, implemented via R15** (delete branch chosen on effort/value; `model_monitor.py` + `tests/test_data_drift.py` deleted and README drift claims struck, commit `2746fa8`).

## D14: One canonical repo root; no nested clone
Date: 2026-09-27
Status: superseded (covered by CONVENTIONS rule 26, 2026-09-28)
Context: A prior audit found a nested, untracked clone of the entire project (now absent); this is a recurring duplication risk for deploy targets like Hugging Face Spaces.
Decision: (Superseded — CONVENTIONS rule 26 already states "there is exactly one canonical repo root; never commit a vendored or nested clone", so this needs no separate decision.)
Consequences: (Superseded — enforcement is CONVENTIONS rule 26, checked in review.)

## D15: Commit the agent decision records (historical)
Date: 2026-09-27
Status: accepted (historical)
Context: The project's agent records were untracked and therefore invisible to collaborators and CI.
Decision: Un-ignore and commit the agent records directory. The directory was later removed from the repository root when its records moved to `docs/` during the P2 closure; this entry records the original decision, not a current path.
Consequences: Required editing `.gitignore:86` (R33); ruled out relying on untracked local notes as the source of truth. Accepted 2026-09-28 at the owner's direction. The records now live in `docs/DECISIONS.md`, `docs/REBUILD_HISTORY.md` and `docs/ENGINEERING_CONVENTIONS.md`.

## D16: Use a public base image for Docker builds
Date: 2026-09-27 (accepted 2026-10-13)
Status: accepted
Context: `Dockerfile:1` uses the `docker.arvancloud.ir` mirror, which makes builds non-reproducible outside that registry.
Decision: Switch all Dockerfiles to a standard public base image, and align the Python version with the interpreter actually used and tested — **`python:3.12-slim`** (STATE.md's verification environment is Python 3.12.3). The current Dockerfiles pin **3.10** (`Dockerfile:1`, `Dockerfile.hf:3`, `Dockerfile.prod:2,17`), which does not match the tested runtime; ROADMAP R25 must bump them to 3.12 so the image and the verified interpreter agree.
Consequences: Requires ROADMAP R25; rules out builds that depend on a private/regional mirror, and rules out shipping an image whose Python minor version differs from the one the suite is verified on. **Clean-checkout build dependency (2026-10-13):** R25's acceptance is a build/`pip check` from a clean checkout, but `requirements.txt` does not currently carry the R5 fix that makes `import mlflow` work (R5 installed `protobuf==4.25.9` into the venv, alongside `setuptools<81`; the repo's `requirements.txt` pins neither). Without the `protobuf` pin a fresh image fails `pip check`/`import mlflow` exactly as it did pre-R5, so R25 must pull that minimal `protobuf` pin into `requirements.txt` (or R21 — `requirements.txt` correctness — must land first).

## D17: Remove the nginx reverse proxy from the demo
Date: 2026-09-27 (accepted 2026-10-13)
Status: accepted
Context: `docker-compose.prod.yml` mounts `./nginx/nginx.conf` and `./nginx/ssl`, neither of which exists, so the prod stack cannot start.
Decision: Remove the nginx service and its README claims for the demo rather than add a proxy/TLS stack that is out of scope.
Consequences: Requires ROADMAP R24; rules out any "reverse proxy / TLS termination" claim unless a real config is added later.

## D18: Add a minimal CI pipeline
Date: 2026-09-27 (accepted 2026-10-17)
Status: accepted
Context: No `.github/` directory or workflow exists despite README CI/CD claims, and the test suite currently cannot even collect.
Decision: Add a GitHub Actions workflow that runs `pytest tests/` and `docker build` on push, after the suite is made collectable.
Consequences: Requires ROADMAP R8 and R27; rules out advertising CI/CD until a workflow actually runs green.
Implementation note (2026-10-17): the premise "suite cannot collect" is historical (R8); implemented by R27 as a GitHub Actions workflow whose steps call repo scripts — the test job builds data+model first (`python scripts/regenerate_data.py && python -m src.training.train`), runs the full suite with a zero-skipped-tests gate and the coverage gate, and runs `scripts/verify_readme.sh` (quickstart, live API, smoke tests); a docker job builds the main Dockerfile and runs `docker compose up -d pricing-api` plus a bounded health check. README mentions CI only after the user confirms a green run.

## D19: Remove the AWS deployment claims
Date: 2026-09-27 (accepted 2026-10-17)
Status: accepted
Context: README documents an AWS EC2 deployment flow and references `scripts/deploy.sh` and `scripts/pre_deploy_check.sh`, neither of which exists.
Decision: Delete the AWS deployment section and links from the README rather than build cloud deploy tooling for a demo.
Consequences: Requires ROADMAP R28; rules out "automated deployment / rollback" claims until scripts exist and are tested.
Implementation note (2026-10-17): the README AWS/EC2 sections and the `DEPLOYMENT.md` link were removed (R23, R31); no deployment scripts will be created; R28 closes through its "remove the references" branch.

## D20: Keep and fix the Streamlit UI
Date: 2026-09-27 (accepted 2026-10-17)
Status: accepted
Context: `app.py` is the project's visible demo surface but currently cannot render a result (wrong response field, rejected method, fabricated Advanced-tab response).
Decision: Keep Streamlit as the demo UI and fix the API contract and fabricated data rather than replace it.
Consequences: Requires ROADMAP R10/R11 and a consumer-vs-schema contract test; rules out adding new UI fields without updating the schema test.
Implementation note (2026-10-17): implemented via R10/R11, guarded by `tests/test_streamlit_contract.py`; `app.py:65-66` Product ID input still has no help text (open).

## D21: Return generic errors to API clients
Date: 2026-09-27 (accepted 2026-10-17)
Status: accepted
Context: `src/api/router.py:108` returns raw exception text (including internal column names) to clients.
Decision: Return a generic message plus `request_id` on 5xx and log the exception server-side; specific validation errors keep their field-level detail.
Consequences: Requires ROADMAP R16 and a test asserting no internal error strings appear in responses.
Implementation note (2026-10-17): implemented via R16, guarded by `test_optimizer_failure_returns_generic_error`.

## D22: Keep rate limiting in-memory (single process)
Date: 2026-09-27
Status: superseded (folded into ROADMAP R23/R32 — README/Limitations work item, 2026-09-28)
Context: `RateLimitMiddleware` is a real but per-process in-memory sliding window; it does not share state across workers.
Decision: (Superseded — no separate action. The decision "keep in-memory, document the limitation" is now carried by ROADMAP R23 (README truth pass) and R32 (Limitations section), which must state that rate limits are per process/per worker.)
Consequences: (Superseded — enforced as part of R23/R32; rules out claiming distributed/global rate limiting.)

## D23: Keep synthetic data, but label it as synthetic everywhere
Date: 2026-09-27
Status: superseded (folded into ROADMAP R23/R32 — README/Limitations work item, 2026-09-28)
Context: The model is trained on data from `src/data/generator.py`; README/UI language implies a real e-commerce system.
Decision: (Superseded — no separate action. "Keep synthetic data but label it as synthetic" is now carried by ROADMAP R23 (README truth pass) and R32 (Limitations section), which must state that all data and metrics are synthetic.)
Consequences: (Superseded — enforced as part of R23/R32; rules out presenting the metrics as real-world performance.)

## D24: Standardize on module-form entry points
Date: 2026-09-27 (accepted 2026-10-17)
Status: accepted
Context: `python src/training/train.py` fails with `ModuleNotFoundError` because the script does not add the repo root to `sys.path`, while `python -m src.training.train` works.
Decision: Make `python -m src.training.train` and `python -m src.api.server` the canonical commands and remove or fix the direct-script forms.
Consequences: Requires README updates and `scripts/verify_readme.sh` (ROADMAP R23); rules out documenting commands that are not executed in CI.
Implementation note (2026-10-17): implemented via R23 (README documents `python -m src.training.train` and `python -m src.api.server`; `scripts/verify_readme.sh` runs them).

## D25: Enforce a coverage floor on the pricing and API paths
Date: 2026-09-27 (accepted 2026-10-17)
Status: accepted
Context: Stored coverage is 69% overall, and the modules that matter most (the optimizer, the API contract) are exactly the ones the current tests fail to exercise realistically.
Decision: Require ≥ 80% line coverage for `src/pricing/*` and `src/api/*` and enforce it in CI.
Consequences: Requires ROADMAP R7/R9/R30; rules out adding pricing or API code without tests.
Implementation note (2026-10-17): enforced in CI — >= 80% line coverage for every file under `src/pricing` and `src/api` (per-file check via coverage JSON) plus `--cov-fail-under=80` on the two packages combined; measured baseline before this batch: 89% combined (`error_handlers.py` 63%, `middleware.py` 78%).

## D26: Single config file; drop APP_ENV-driven YAML selection
Date: 2026-10-13
Status: accepted
Context: After R18 deleted the unread `api:`/`logging:` blocks, `configs/config.dev.yaml` and `configs/config.prod.yaml` became key-identical to `configs/config.yaml` — the parsed YAML compares equal (only comments differ), so the `APP_ENV`→file selection in `EnvConfig._load_config` (`src/utils/env_config.py:32-51`) is a no-op. It is also unused by any YAML consumer: `EnvConfig` is instantiated only at `src/api/server.py:25`, which uses it solely for env-var reads (`get_bool`/`get_int`), while the config that actually drives pricing is built in `src/api/router.py:19-24` from a **hardcoded** `configs/config.yaml`; every training/script entry point (`src/training/train.py:7`, `scripts/train_with_tuning.py:24`, `scripts/regenerate_data.py:31`) also hardcodes it. That makes the dev/prod files a duplicate config that is never read (CONVENTIONS rule 27) and a second mechanism for one concern (rule 8).
Decision: Keep exactly one YAML config file, `configs/config.yaml`. Delete `configs/config.dev.yaml` and `configs/config.prod.yaml`; make `EnvConfig` always load `configs/config.yaml` (drop the `APP_ENV`→file `config_map`); and remove the now-readerless `APP_ENV` from `.env`, `.env.example`, and `docker-compose.prod.yml`. Anything that genuinely differs by environment is expressed as an env var, never as a second YAML file.
Consequences: Requires ROADMAP R35 (a test asserts exactly one `configs/*.yaml`; `tests/test_env.py` stays green after `APP_ENV` removal; `/v1/health` and `/v1/optimize-price` still return 200). Rules out committing per-environment YAML copies. The alternative ("keep dev/prod and add env-specific keys") was rejected because there are no genuinely env-specific YAML keys: the remaining keys are model/training/feature hyperparameters and artifact paths, and there is one trained artifact (`models/demand_model.pkl`) and one feature contract (`models/features.json`), so letting dev/prod diverge would desync the served model from its feature contract and silently break pricing. Consistent with D11 and CONVENTIONS rules 8/27.

## D27: Dependency pin policy — pin the installed stack, use `xgboost-cpu`, stay on mlflow 3.x
Date: 2026-10-13
Status: accepted
Context: R21 (`c444973`) added only a `protobuf==4.25.9` pin and left `xgboost>=2.0.0` / `mlflow>=2.9.0` as lower bounds, so a fresh install of `requirements.txt` drifts away from the stack the repo is verified against. On 2026-10-13 a fresh project venv (`.venv`, Python 3.12.3) resolved to `xgboost 3.4.1` and `mlflow 3.17.1`. Two problems followed: (a) xgboost 3.4.1 has a Linux-only hard dependency on `nvidia-nccl-cu13` (`requires_dist`: `nvidia-nccl-cu13; platform_system == "Linux"`), a ~291 MB CUDA/NCCL wheel the demo does not need; (b) mlflow 3.x refuses the filesystem tracking backend unless `MLFLOW_ALLOW_FILE_STORE` is set (`mlflow/store/tracking/file_store.py:224`), which broke the file-store-based `tests/test_mlflow_registry.py` (2 setup errors) and would break `scripts/promote_model.py`, whose default tracking URI is `file://<repo>/mlruns` (`promote_model.py:20`). Pinning mlflow 2.x is not an option: mlflow 2.12.1 declares `numpy<2`, `pandas<3`, and `pyarrow<16` (PyPI `requires_dist`), which conflict with the installed `numpy 2.5.4`, `pandas 3.0.6`, and `pyarrow 24.0.0`.
Decision: Adopt an explicit dependency pin policy:
1. Stay on mlflow 3.x and pin `mlflow==3.17.1`. Pin **all** direct dependencies in `requirements.txt` with `==` to the versions installed in the project venv (taken from `.venv/bin/pip freeze`), keeping extras such as `uvicorn[standard]`; transitive dependencies stay unpinned.
2. Replace `xgboost` with `xgboost-cpu` at the same version (`3.4.1`) to avoid the `nvidia-nccl-cu13` wheel.
3. Keep `protobuf==4.25.9`, but rewrite its comment: it must no longer claim the pin is needed because of the mlflow 2.x / R5 `google.protobuf.service` breakage — it is the version validated with the pinned stack. Do not add `setuptools`.
4. `setuptools<81` (the old R5 fix) is obsolete: it is not installed in the new venv and `import mlflow` works without it. Record this in `docs/REBUILD_HISTORY.md`.
5. The registry tests use a **sqlite** tracking URI in `tmp_path`, not the file store (we do not set `MLFLOW_ALLOW_FILE_STORE` anywhere).
6. `scripts/promote_model.py`'s default tracking URI becomes **sqlite** — `sqlite:////<repo root>/mlflow.db`, the same database `start.sh`'s `mlflow server --backend-store-uri sqlite:///mlflow.db` uses — not `file://`.
7. `docker-compose.yml`'s `mlflow` service pins `mlflow==3.17.1`. `psycopg2-binary`, the `python:3.10` image, and the obsolete `version` key are left untouched (flagged only).
Consequences: Requires ROADMAP R21 (`requirements.txt` correctness) and R25 (Docker/compose); both remain `in-progress` because their remaining acceptance is the owner's fresh-venv `pip install -r requirements.txt && pip check` and `docker compose build && up -d && curl /v1/health` on an unthrottled network. Rules out pinning mlflow 2.x (its `numpy<2`/`pandas<3`/`pyarrow<16` caps are incompatible with the installed data stack) and rules out `xgboost` (which drags in `nvidia-nccl-cu13`). Consistent with D16 (public base image) and CONVENTIONS rules 19/32.

## D28: Untrack the stale `mlflow.db`; ignore it (and de-indent the `.dockerignore` MLflow entries)
Date: 2026-10-14
Status: accepted
Context: D27 point 6 pointed `scripts/promote_model.py`'s default tracking URI at the repo's local `mlflow.db` (`sqlite:////<repo root>/mlflow.db`), the same database `start.sh`'s `mlflow server --backend-store-uri sqlite:///mlflow.db` uses; D27's C2 commit (`5c62460`) flagged that `mlflow.db` is **tracked** in git while `mlruns/` is gitignored (`.gitignore:80`). A tracked binary database that `promote_model.py` rewrites on every promote would change on every promotion, and its committed content is stale: it holds 2 runs (`demand_forecasting_model` v1 and v2) with **no** production alias, and its artifact locations are absolute, machine-specific paths under `mlruns/` — which is itself gitignored. On a clean clone those model versions therefore point at artifacts that are not present, so the tracked DB is worse than useless as a versioned artifact. `mlflow.db` is also already excluded from the Docker build context (`.dockerignore:43`).
Decision: (1) Untrack `mlflow.db` (`git rm --cached`) and add `mlflow.db` to `.gitignore` next to the existing `mlruns/` entry (same `# MLflow` section). (2) Strip the leading spaces from `.dockerignore` lines 42-43 (the `mlruns/` and `mlflow.db` entries) so those two patterns match at the root of the build context. (3) Do **not** rewrite git history (no `filter-branch`/`filter-repo`); the blob stays in past commits. (4) The file **stays on disk** in the working tree — it is ignored, not deleted.
Consequences: `mlflow.db` is no longer a committed artifact; the registry's state is machine-local and is recreated locally by `scripts/promote_model.py` and by `start.sh`'s `mlflow server` (both default to `sqlite:///mlflow.db`). No history rewrite, so the stale blob remains reachable in old commits — accepted because it is stale and small (~184 KB) and rewriting history would rewrite every subsequent commit SHA. Enforcement is a repo-hygiene test (`tests/test_repo_hygiene.py`) that parses `.gitignore` and asserts it carries an entry that is exactly `mlflow.db` (and, for the `.dockerignore` half, that no non-blank line carries leading/trailing whitespace). Consistent with CONVENTIONS rule 27 (do not commit a second copy of state) and D27 point 6.

## D29: Track `.dockerignore` and clean it; never bake local config into the image
Date: 2026-10-15
Status: accepted
Context: `.dockerignore` is listed in `.gitignore` (`.gitignore:73`), so it is untracked: a clean `git clone` has **no** `.dockerignore` at all, and the Docker build context silently differs between the developer's tree (which has the file) and a clean checkout (which does not). The local `.dockerignore` is also indented by one leading space on every line (blank lines hold a single space), so the patterns do not match at the build-context root the way the author intended — D28's C2 de-indented only lines 42-43 on disk and left the rest indented and uncommitted (69 of 71 lines were still indented at the time of this change). And because `.env` is not excluded, the developer's local `.env` (`API_WORKERS=4`, `localhost` values) is copied into the image, so the image silently diverges from the code defaults.
Decision: (1) Make `.dockerignore` a **tracked** file: remove its entry from `.gitignore` (`.gitignore:73`). (2) De-indent **every** line of `.dockerignore` — strip leading/trailing whitespace so blank lines become truly empty — keeping every existing entry and its order. (3) Add `.env` to `.dockerignore` (a short `# Local config (never bake into the image)` section placed next to the other local-state entries) so local config is never baked into the image. (4) Guard all of this with repo-hygiene tests in `tests/test_repo_hygiene.py`: no `.dockerignore` line carries leading/trailing whitespace (blank lines are truly empty); `.dockerignore` contains the entries exactly `.env`, `mlflow.db`, and `mlruns/`; and `.gitignore` has no entry that is exactly `.dockerignore`.
Consequences: On a clean clone the build context now matches the developer's (`.dockerignore` is present and clean), so build inputs live in git — and only the right ones. Because `.env` is excluded from the image, env-driven settings that compose does not set (e.g. `API_WORKERS`; `docker-compose.yml`'s `pricing-api` sets only `MLFLOW_TRACKING_URI` and `PYTHONUNBUFFERED`) fall back to the code defaults instead of the developer's local values, so the image is reproducible from tracked inputs alone. Consistent with CONVENTIONS rule 27 (do not commit a second copy of state) and D28.

## D30: Reproducible data and model — seed the generator, config-driven dataset size, build data + model in the image
Date: 2026-10-15
Status: accepted
Context: The clean-clone investigation (2026-10-15, `docs/REBUILD_HISTORY.md` §7) found three coupled reproducibility gaps. (a) `src/data/generator.py` draws every value from the **global unseeded** NumPy RNG (`np.random.uniform`/`randint`/`choice`/`normal`, plus stdlib `random.choice` for `category`), so two runs on identical inputs produce different data and different models — two clean clones trained to R2 **0.4328** vs **0.4708** (MAPE 0.3692 vs 0.3543). (b) The documented dataset size does not match the script: `scripts/regenerate_data.py:21` hardcodes `EcommerceDataGenerator(n_products=100, days=365)` → **36,500** raw / **33,000** feature rows, while the committed working-tree artifacts and `STATE.md` describe **50 products × 365 days = 18,250** raw / **16,500** feature rows, so the recorded R2 0.475 / MAPE 0.346 cannot be reproduced by the documented command. (c) A clean checkout has no `models/demand_model.pkl` (gitignored), so a clean-checkout Docker build has no model to serve (the unmet R25 criterion). The single `configs/config.yaml` (D26) is the right home for the size/seed so the script and any test read one source.
Decision:
1. `EcommerceDataGenerator` takes a `seed` (default `42`) and creates one local `numpy.random.Generator` via `np.random.default_rng(seed)` in `__init__`; **every** random draw uses that generator instead of the global `np.random.*`. The generator's column logic and formulas are unchanged.
2. The dataset size and seed live in `configs/config.yaml` under `data:` — `data.n_products: 50`, `data.days: 365`, `data.seed: 42` — and `scripts/regenerate_data.py` reads them (no hardcoded size in the script).
3. After seeding, the data is regenerated and the model retrained once; R7 (`docs/REBUILD_HISTORY.md`) is re-run and the new real R2/MAPE/MAE are recorded in `docs/REBUILD_HISTORY.md`. If the new metrics differ from R2 0.475 / MAPE 0.346 by more than 0.02, that is stated prominently.
4. The **main** `Dockerfile` builds data and model after `COPY . .` with `RUN python scripts/regenerate_data.py && python -m src.training.train`, so a clean-checkout image carries a model built from tracked inputs (no dependency on local artifacts).
5. `.dockerignore` excludes `models/*.pkl` and `data/features/`, so the local (gitignored) artifacts never enter the build context and the image always builds its own.
6. `Dockerfile.prod`, `Dockerfile.hf`, and `docker-compose.prod.yml`'s `./models:/app/models:ro` mount are **not** touched by this decision; their clean-clone behaviour is only reported.
Consequences: Two clean clones now produce byte-identical data and (metrics-)identical models; the recorded metrics are reproducible with the documented command. The regenerated data is **different** from the previously committed artifact (a seeded `Generator` draws a different sequence than the global RNG), so the recorded R2/MAPE change and are re-reported rather than carried over (CONVENTIONS rule 22). The main image is larger/slower to build (it trains at build time, offline) but no longer needs local artifacts; `Dockerfile.prod`/`Dockerfile.hf` still ship without a built model, which is recorded as an open item. Requires ROADMAP R25 (stays `in-progress`: the remaining acceptance is the owner's clean-checkout `docker compose build` + health check). Consistent with D16, D26, D29, and CONVENTIONS rules 7/22.

## D31: One hardened container image: merge Dockerfile.prod's essentials into the main Dockerfile
Date: 2026-10-18 (accepted 2026-10-18)
Status: accepted
Context: `Dockerfile.prod` (multi-stage, non-root `appuser`, `HEALTHCHECK` at `Dockerfile.prod:41`) and `docker-compose.prod.yml` duplicate the main image path, but they ship **no model** on a fresh clone: `.dockerignore` excludes `models/*.pkl` and `data/features/`, neither file runs the data+model build, and `docker-compose.prod.yml:19` bind-mounts an empty `./models`; `PricingEngine.load_model` calls `joblib.load` at import (`src/pricing/engine.py:131`), so the container exits with `FileNotFoundError` instead of serving. `docker-compose.prod.yml` also carries `MONITORING_ENABLED=true` (`:17`), which no code reads, and a `./backups` mount (`:23`) for scripts deleted in R22. Meanwhile the **main** image — the only one that builds a model — runs as root and has no `HEALTHCHECK`.
Decision: Keep **one** `Dockerfile` that (a) builds data+model after `COPY . .`, (b) installs dependencies in a builder stage, (c) runs as a non-root user, and (d) defines a `HEALTHCHECK`; add `restart: unless-stopped` and a read-only `configs` mount to `docker-compose.yml`; delete `Dockerfile.prod` and `docker-compose.prod.yml`. CI's `docker` job verifies the image builds, the service becomes healthy, and the process uid is not 0.
Consequences: README's "non-root" claim and compose commands are updated; this rules out maintaining two production image paths; `logs/` and any mounted directory must be writable by the non-root user (otherwise the JSONL prediction logger and the read-only config mount fail). **Do not implement until this entry is marked `accepted`** (a repository hard rule).
Implementation note (2026-10-19): implemented by this batch's commits C1 `1d45e8e` (main `Dockerfile`: builder stage + non-root `appuser` + `HEALTHCHECK`), C2 `39fc31e` (compose restart policy / read-only `configs` / `app_logs` named volume / `version` key and `./data` mount removed), C3 `06f62f3` (pinned `Dockerfile.mlflow`, no pip-install-at-start), C4 `1b09d21` (deletion of `Dockerfile.prod` and `docker-compose.prod.yml`, README update) and C5 `4496ca7` (smoke script checks uid != 0, Docker health status and MLflow `/health`). **User-reported:** after pushing `caae3aa`, both CI jobs (`test`, `docker`) ran green; the `docker` job built the main image, started `pricing-api` and got `/v1/health` 200. That validates the existing smoke path, **not** the D31 hardening. **D31 docker-job result (user-reported 2026-10-19):** the builder stage, non-root uid 1000, in-image model build and Docker `HEALTHCHECK` are verified (all PASSED); the mlflow service was **NOT** healthy - `mlflow /health` failed because the container restart-looped with `ModuleNotFoundError: No module named 'psycopg'` from `sqlalchemy/dialects/postgresql/psycopg.py` (SQLAlchemy 2.1 maps a bare `postgresql://` to psycopg v3). Fixed in `0aeb1be` by naming the driver (`postgresql+psycopg2://`); the mlflow service will be re-verified by the next CI run after the fix. All other Docker claims remain **static check only**.

---
