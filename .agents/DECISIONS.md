# DECISIONS.md — Architecture decision log (ADR-lite)

Ongoing log of decisions that shape this project. Each entry is one decision.
**Status values:** `proposed` (recommended, not yet approved) · `accepted` (approved and in force) · `superseded` (replaced by a later entry — link it).

**Reference commits:** Ground truth verified against commit `c32841f` (see `.agents/STATE.md`). This planning revision sits on top of the working tree at the current commit (see `git log -1`); no new commit was created for these `.agents/` edits.

Every entry below is seeded from `.agents/STATE.md` and `.agents/ROADMAP.md`. **D1, D2, D5, D6, and D15 are `accepted` (D15 on 2026-09-28; D1 and D2 on 2026-09-29; D5 and D6 on 2026-09-30, at the owner's direction); D3, D14, D22, and D23 are `superseded` (each links to its successor or to the rule/item that now covers it); every other entry remains `proposed` and awaits the owner's acceptance or override.** Do not implement a proposed decision until it is marked `accepted`.

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
Status: proposed
Context: `ModelMonitor` (drift + degradation) is never imported, and `tests/test_data_drift.py` asserts that drift exists rather than validating the service.
Decision: Remove the drift/monitoring modules and tests and strike the claims from the README, unless a real consumer (endpoint/CLI with a passing test) is built instead.
Consequences: Requires ROADMAP R15 and README honesty (R23); there is no third state where the code stays dead but the claim stays in the docs.

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
Date: 2026-09-27
Status: proposed
Context: `Dockerfile:1` uses the `docker.arvancloud.ir` mirror, which makes builds non-reproducible outside that registry.
Decision: Switch all Dockerfiles to a standard public base image, and align the Python version with the interpreter actually used and tested — **`python:3.12-slim`** (STATE.md's verification environment is Python 3.12.3). The current Dockerfiles pin **3.10** (`Dockerfile:1`, `Dockerfile.hf:3`, `Dockerfile.prod:2,17`), which does not match the tested runtime; ROADMAP R25 must bump them to 3.12 so the image and the verified interpreter agree.
Consequences: Requires ROADMAP R25; rules out builds that depend on a private/regional mirror, and rules out shipping an image whose Python minor version differs from the one the suite is verified on.

## D17: Remove the nginx reverse proxy from the demo
Date: 2026-09-27
Status: proposed
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

---

Last updated: 2026-09-30 (D5/D6 accepted; see `.agents/STATE.md`).
