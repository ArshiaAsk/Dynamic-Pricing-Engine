# DECISIONS.md — Architecture decision log (ADR-lite)

Ongoing log of decisions that shape this project. Each entry is one decision.
**Status values:** `proposed` (recommended, not yet approved) · `accepted` (approved and in force) · `superseded` (replaced by a later entry — link it).

**Reference commits:** Ground truth verified against commit `c32841f` (see `.agents/STATE.md`). This planning revision sits on top of the working tree at the current commit (see `git log -1`); no new commit was created for these `.agents/` edits.

Every entry below is seeded from `.agents/STATE.md` and `.agents/ROADMAP.md`. **D1, D2, D5, D6, D13, D15, D16, D17, D26, D27, D28, and D29 are `accepted` (D15 on 2026-09-28; D1 and D2 on 2026-09-29; D5 and D6 on 2026-09-30; D13 on 2026-10-07 retroactively, implemented via R15, at the owner's direction; D16 and D17 on 2026-10-13; D26 on 2026-10-13; D27 on 2026-10-13; D28 on 2026-10-14; D29 on 2026-10-15); D3, D14, D22, and D23 are `superseded` (each links to its successor or to the rule/item that now covers it); every other entry remains `proposed` and awaits the owner's acceptance or override.** Do not implement a proposed decision until it is marked `accepted`.

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
Date: 2026-09-27
Status: proposed
Context: Training builds features in `src/features/feature_builder.py`, while serving builds them ad hoc in each optimizer (`bayesian_optimizer._build_features`, `optimizer.optimize`), and a third path lives in `src/features/transformer.py`; the divergence is what caused the grid `KeyError`.
Decision: Define the serving feature set once and have both optimizers consume it, keeping it explicitly consistent with the training feature list in `models/features.json`; delete the unused `transformer.py` path.
Consequences: Requires ROADMAP R4 and a test asserting both optimizers emit identical feature vectors; any feature added to training must be added to the serving builder in the same PR.

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
Date: 2026-09-27
Status: proposed
Context: `import mlflow` at module top level makes the API, the tuning script, and `tests/test_api.py` fail to start when MLflow is unavailable (`engine.py:9`), and the committed registry has no Production version anyway.
Decision: Make MLflow optional and import it lazily; the API must start and serve from the local model artifact with MLflow absent or misconfigured.
Consequences: Requires ROADMAP R3 and a test that imports the API with MLflow unavailable; rules out any top-level unconditional `import mlflow` on the serving path.

## D8: Local model artifact is the serving source of truth
Date: 2026-09-27
Status: proposed
Context: The engine attempts an MLflow registry load but always falls back to `models/demand_model.pkl`; the registry has no Production stage/alias, so the "versioned model" path is dead at serve time.
Decision: Treat `models/demand_model.pkl` + `models/features.json` as the canonical served artifact; use MLflow only for experiment tracking and, optionally, a registry that must be explicitly promoted.
Consequences: Requires ROADMAP R5 (loud, correct fallback) and R8/R9 (tests run against the local artifact); the README must not imply registry-driven serving until a Production alias actually exists.

## D9: Remove the SQLite ingestion path
Date: 2026-09-27
Status: proposed
Context: `data.db` holds 18,250 rows but no `src/` code reads or writes it; `src/data/ingest.py` is dead and its `__main__` targets a non-existent file.
Decision: Remove the SQLite path — delete `src/data/ingest.py`, `data.db`, `src/data/pipeline_runner.py`, and the DB backup/restore scripts — rather than wire it in, since the demo's state lives in files (parquet/CSV/JSONL).
Consequences: Requires ROADMAP R29 and README cleanup; rules out any claim of database-backed persistence or 7-day retention until a real consumer exists.

## D10: Keep prediction logs as JSONL files
Date: 2026-09-27
Status: proposed
Context: `PredictionLogger` writes JSONL audit logs and is genuinely wired into the API; the SQLite alternative is orphaned.
Decision: Keep the JSONL prediction log as the audit store and drop the database claims.
Consequences: Depends on D9; log retention/rotation must be handled explicitly (see D11) rather than assumed.

## D11: Pick one configuration mechanism per concern
Date: 2026-09-27
Status: proposed
Context: The API reads runtime settings from env vars while `configs/config.dev.yaml`/`prod.yaml` carry unread `api:` and `logging:` blocks, and `config.yaml` carries an unread `monitoring:` block.
Decision: Use env vars for runtime toggles (API host/port/workers, rate limit, logging, timeouts) and YAML for model/training/feature parameters; delete every config key that is not read.
Consequences: Requires ROADMAP R18/R19 and a test that fails on any unread YAML key or `.env` variable; rules out keeping decorative config sections.

## D12: Delete dead modules rather than keep them "for later"
Date: 2026-09-27
Status: proposed
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

## D15: Commit the `.agents/` decision records
Date: 2026-09-27
Status: accepted
Context: `.gitignore` currently ignores `.agents/`, so `STATE.md`, `ROADMAP.md`, `CONVENTIONS.md`, and this file are untracked and invisible to collaborators and CI.
Decision: Un-ignore `.agents/` and commit these files as the project's living memory.
Consequences: Requires editing `.gitignore:86` (ROADMAP R33); rules out relying on untracked local notes as the source of truth. **Accepted 2026-09-28 at the owner's direction** (the `.agents/` directory and `AGENTS.md` were committed).

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
Date: 2026-09-27
Status: proposed
Context: No `.github/` directory or workflow exists despite README CI/CD claims, and the test suite currently cannot even collect.
Decision: Add a GitHub Actions workflow that runs `pytest tests/` and `docker build` on push, after the suite is made collectable.
Consequences: Requires ROADMAP R8 and R27; rules out advertising CI/CD until a workflow actually runs green.

## D19: Remove the AWS deployment claims
Date: 2026-09-27
Status: proposed
Context: README documents an AWS EC2 deployment flow and references `scripts/deploy.sh` and `scripts/pre_deploy_check.sh`, neither of which exists.
Decision: Delete the AWS deployment section and links from the README rather than build cloud deploy tooling for a demo.
Consequences: Requires ROADMAP R28; rules out "automated deployment / rollback" claims until scripts exist and are tested.

## D20: Keep and fix the Streamlit UI
Date: 2026-09-27
Status: proposed
Context: `app.py` is the project's visible demo surface but currently cannot render a result (wrong response field, rejected method, fabricated Advanced-tab response).
Decision: Keep Streamlit as the demo UI and fix the API contract and fabricated data rather than replace it.
Consequences: Requires ROADMAP R10/R11 and a consumer-vs-schema contract test; rules out adding new UI fields without updating the schema test.

## D21: Return generic errors to API clients
Date: 2026-09-27
Status: proposed
Context: `src/api/router.py:108` returns raw exception text (including internal column names) to clients.
Decision: Return a generic message plus `request_id` on 5xx and log the exception server-side; specific validation errors keep their field-level detail.
Consequences: Requires ROADMAP R16 and a test asserting no internal error strings appear in responses.

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
Date: 2026-09-27
Status: proposed
Context: `python src/training/train.py` fails with `ModuleNotFoundError` because the script does not add the repo root to `sys.path`, while `python -m src.training.train` works.
Decision: Make `python -m src.training.train` and `python -m src.api.server` the canonical commands and remove or fix the direct-script forms.
Consequences: Requires README updates and `scripts/verify_readme.sh` (ROADMAP R23); rules out documenting commands that are not executed in CI.

## D25: Enforce a coverage floor on the pricing and API paths
Date: 2026-09-27
Status: proposed
Context: Stored coverage is 69% overall, and the modules that matter most (the optimizer, the API contract) are exactly the ones the current tests fail to exercise realistically.
Decision: Require ≥ 80% line coverage for `src/pricing/*` and `src/api/*` and enforce it in CI.
Consequences: Requires ROADMAP R7/R9/R30; rules out adding pricing or API code without tests.

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
4. `setuptools<81` (the old R5 fix) is obsolete: it is not installed in the new venv and `import mlflow` works without it. Record this in `.agents/STATE.md`.
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

---

Last updated: 2026-10-15 (D29 accepted — track `.dockerignore`, de-indent every line, and exclude `.env` from the image so local config is never baked in; D28 accepted 2026-10-14 — untrack the stale `mlflow.db` and ignore it, strip the leading spaces from `.dockerignore` lines 42-43, no history rewrite and the file stays on disk; D27 accepted 2026-10-13 — dependency pin policy: pin the installed stack, `xgboost-cpu`, mlflow 3.x with sqlite registry tests/promote default; D16 and D17 accepted earlier that day — public base image for Docker builds, and remove the nginx reverse proxy from the demo; D26 accepted 2026-10-13 — single config file, drop APP_ENV-driven YAML selection; see `.agents/STATE.md`).
