# LOG.md — Running session log

Append a new entry at the **top** of the entries section (newest first) at the end of every
session. Do not edit past entries; supersede them with a new one.

## Template

```
## <date> — <one-line summary>
Done:
- ...
Left open / blocked:
- ...
Next session should start with:
- ...
```

---

## 2026-10-17 — D7/D18–D21/D24/D25 accepted; R30 done; R28 done; R27 in-progress (first GitHub run outstanding)

Done:
- **C0 `f355212` — `docs(agents): accept D7, D18, D19, D20, D21, D24, D25`.** `.agents/DECISIONS.md` only (+22/−15). All seven marked `accepted` (2026-10-17) with one implementation note each: D7 via R3 (lazy mlflow import; the top-level-import premise is historical); D18 via R27 (workflow calling repo scripts; data+model build, zero-skip and coverage gates, `verify_readme.sh`, docker job; README only after a green run); D19 via the R28 remove-references branch (no deploy scripts will be created); D20 via R10/R11 (`tests/test_streamlit_contract.py`) with `app.py:65-66` Product ID help text still open; D21 via R16 (`test_optimizer_failure_returns_generic_error`); D24 via R23 (`python -m …` forms run by `scripts/verify_readme.sh`); D25 as the per-file coverage gate (baseline 89% combined, `error_handlers.py` 63%, `middleware.py` 78%). Header accepted list updated.
- **C1 `9164438` — `test(env): stop skipping when .env is absent (R27 prerequisite)`.** `tests/test_env.py` only (+16/−6). The second test now always checks the tracked `.env.example` for variables `src/` never reads and checks `.env` only when it exists — no skip. **Before** (fresh `git clone --no-hardlinks` at `d277cd6`, artifacts built with the repo `.venv` python): `98 passed, 1 skipped`, reason `tests/test_env.py:48: .env is not present (gitignored)`. **After** (fresh clone at `9164438`, artifacts built): **99 passed, 0 skipped**. No `.env.example` variable was missing, so that file was not touched.
- **C2 `f4d5aa6` — `refactor(api): delete never-raised APIError and unreachable handlers (D12, R22 leftover)`.** `src/api/error_handlers.py`, `src/api/server.py` (+1/−60). `grep` found no raiser/reference for `APIError` and no test mention. **Mutation proof** in `/tmp/c2_mut` (copy of HEAD + artifacts): after deleting `APIError`, `api_error_handler`, `generic_exception_handler` and their two registrations, the suite stayed **99 passed**. **Which layer produces the 500:** `ErrorHandlingMiddleware` — a probe route raising `RuntimeError("secret internal detail")` returns `{"error":"internal_server_error","message":"An internal error occurred. Please try again later.","request_id":…}` with `X-Request-ID` **identically before and after** the deletion (the registered `Exception` handler was shadowed by the middleware). The field-level 422 body from `validation_exception_handler` is also byte-identical before/after. Validation handler kept.
- **C3 `dc879c1` — `test(api): cover rate limiting, middleware error paths, health degradation and train-metric evaluation (R30, D25)`.** New `tests/test_api_middleware.py` (4), `tests/test_api_health_metrics.py` (6), `tests/test_health_checker.py` (6), one test appended to `tests/test_evaluator.py` (+337 lines). Mutations in `/tmp/c3_mut`: limiter `>=`→`>` → 429 test fails (`assert 200 == 429`); `ErrorHandlingMiddleware` re-raises instead of returning → 500 test fails. **Coverage** (`COVERAGE_FILE=/tmp/.coverage_c3 pytest tests -q --cov=src/pricing --cov=src/api --cov-report=term-missing --cov-report=json:/tmp/cov_c3.json`): **116 passed**, combined **97%** (389 stmts, 11 missed). Per file: `api/error_handlers.py` 100%, `api/middleware.py` 100% (was 78%), `api/router.py` 100% (was 90%), `api/schemas.py` 100%, `api/server.py` 89% (was 83%), `pricing/engine.py` 96%, `pricing/features.py` 96%, `pricing/optimizer.py` 95%. No file needed an allowlist entry; no padding tests were written (`server.py`'s 5 missed lines are the `__main__` uvicorn block, 97-102).
- **C4 `f66a703` — `chore(scripts): remove dead CI metadata from train_with_tuning.py (R27)`.** `scripts/train_with_tuning.py` only (−17). `get_ci_metadata()` and the MLflow `set_tag` loop removed: `grep` shows no source reference left, no test referenced it, `py_compile` passes, suite green. R27's "removed or actually exercised" is satisfied by removal.
- **C5 `3723295` — `feat(ci): GitHub Actions workflow plus local CI scripts (D18/D25, R27)`.** `.github/workflows/ci.yml`, `scripts/ci_check.sh`, `scripts/check_coverage.py`, `scripts/docker_smoke.sh`, `tests/test_ci_workflow.py` (+426). `tests/test_ci_workflow.py` was **shown failing before the files existed** (`7 errors`, workflow missing) and **passes after** (8 passed). `PYTHON=.venv/bin/python bash scripts/ci_check.sh` in the repo → **exit 0, all PASS, 124 passed, 0 skipped (124 collected)**, combined 97%, per-file gate all PASS, `verify_readme.sh` all PASS (archived suite 116 passed because `git archive HEAD` was still `f66a703`). Same script in `/tmp/ci_prep_clone` **with no model/features/raw artifacts** → **exit 0, 124 passed, 0 skipped**, identical coverage (it built the artifacts itself). Gate mutations in `/tmp` copies: `THRESHOLD=99` → `FAIL: below threshold` exit 1; one added skipped test → `skipped tests: 1: ['test_skipped_mutation']` / `FAIL: zero-skip gate` exit 1. `git status --short` showed only the five intended files; nothing listens on :8765 afterwards.
- **C6 `792627f` — `docs(readme): record the measured coverage (R30)`.** `README.md` only (+18): Coverage subsection under Run Tests with `src/api` 98% (228/233), `src/pricing` 96% (150/156), combined 97% (378/389), the exact `pytest tests --cov=src/pricing --cov=src/api --cov-report=term-missing` command, and one sentence that CI enforces ≥ 80% per file. No CI-status claim or badge. No README-wide test needed a change (`test_readme_truth`, `test_readme_links`, `test_readme_limitations`, `test_verify_readme_script` → 9 passed).
- **C7 (this commit) — docs.** ROADMAP: **R30 → done** (criterion command run literally: 124 passed, every `src/pricing/*` and `src/api/*` file ≥ 80%, lowest 89%; number in README; per-file gate in CI) and **R28 → done** through the remove-the-references branch (no AWS/EC2 or deploy-script references; forbidden-phrase + link tests), with the no-model prod/HF finding carried as a separate open item and the D30 follow-up plan; **R27 → in-progress** (workflow + scripts landed and pass locally; remaining = the owner pushes and reports a green `test` + `docker` run, then README documents CI status); `Last updated`. STATE: tests row → **124 passed, 0 skipped** (fresh clone after data+model **124 passed, 0 skipped**), CI/CD row → PARTIAL (workflow exists, never run on GitHub), measured coverage → 93% `src` / 97% combined with per-file numbers, §7 corrected from "serve no model" to "engine raises `FileNotFoundError` at import and the container exits", `Last verified` → `792627f`. LOG: this entry. Only these three docs; explicit-path staging.
- **Task A (read-only, no commit).** `git log origin/main..HEAD --oneline | wc -l` → **30**; `git diff origin/main --stat | tail -3` → see the batch report (the diffstat tail lists the `.agents/` docs); secret scan with `git grep -In` over tracked files for `password|secret|api_key|token|BEGIN PRIVATE|/home/arshiaask|emails` → see the batch report; no real credential was found. `git status --short` clean before the docs commit.

Left open / blocked:
- **R27** stays `in-progress`: the user must push and report a green run of both jobs; only then does README document CI status. Action versions (`actions/checkout@v4`, `actions/setup-python@v5`) are from memory and unverified offline.
- **Docker was not run** (`scripts/docker_smoke.sh` is `bash -n` only), per the batch instruction; the `docker` job is unverified until the first GitHub run.
- **R29** stays `in-progress` (`data.db` still on disk; the owner deletes it).
- **Open finding (D30 follow-up):** `Dockerfile.prod`, `Dockerfile.hf` and the `./models` mounts of `docker-compose.prod.yml`/`docker-compose.hf.yml` ship no model on a fresh clone → `FileNotFoundError` at import, container exits. Planned fix: the same data+model build step plus removing those mounts, verified by building those images in CI next batch.
- **Flag (C2):** after deleting the shadowed `generic_exception_handler`, an exception raised *inside an outer middleware* (Timeout/RateLimit/RequestLogging) would now surface as Starlette's plain 500 instead of the JSON body. No code path raises there and no response contract covers it; route exceptions are unchanged.
- **Flag (C5):** `scripts/verify_readme.sh` verifies `git archive HEAD`, so during the pre-commit CI run it exercised the previous commit (`f66a703`, 116 tests) rather than the working tree; the CI script's own pytest step exercised the working tree (124).

Next session should start with:
- Ask the owner for the first GitHub Actions run (jobs `test` and `docker`); if green, add the CI-status line to README and mark **R27 `done`**.
- Then the D30 follow-up for `Dockerfile.prod`/`Dockerfile.hf` (build data+model, drop the `./models` mounts) and CI builds of those images.

---

## 2026-10-17 — R31/R32 done; README multi-seed headline; read-only R27/R30/R28 facts

Done:
- **C1 `a67a505` — `docs(readme): lead with the multi-seed metric mean, seed 42 as the reference run (R23 follow-up)`.** README.md only (+11/−8). Executive Summary bullet and Model Performance now state the seeds-1–10 mean first (R² **0.447 ± 0.029**, MAPE **0.361 ± 0.011**) and seed 42 as the reference run (R² 0.419, MAPE 0.351); numbers copied from the STATE.md §1 seed-sweep line (quoted in the commit body). `tests/test_readme_truth.py` + `tests/test_verify_readme_script.py` → 7 passed; full suite → **97 passed, 0 skipped**.
- **C2 `0b57fc4` — `docs(readme): remove links to documentation files that do not exist; add a link-check test (R31)`.** README.md + new `tests/test_readme_links.py` + `tests/test_readme_truth.py` (+71/−17). Delink branch: no `docs/API.md`, `docs/OPERATIONS.md`, `DEPLOYMENT.md`, `PRODUCTION_FEATURES.md`, `PRODUCTION_READY.md` were created; the Documentation table (including the AWS description) and both OPERATIONS.md pointers were removed. New test resolves inline/reference-style relative targets against the repo root and checks same-file anchors via GitHub slugs. **Pre-fix:** `1 failed` — `README has broken relative links: ['DEPLOYMENT.md', 'PRODUCTION_FEATURES.md', 'PRODUCTION_READY.md', 'docs/API.md', 'docs/OPERATIONS.md']`; **after:** `1 passed`. Added whole word `aws` to the forbidden list (no AWS tooling/deployment). Suite → **98 passed, 0 skipped**.
- **C3 `f722b08` — `docs(readme): add a Limitations section (R32)`.** README.md + new `tests/test_readme_limitations.py` + `tests/test_readme_truth.py` (+76/−1). New `## Limitations` covers (a) observational, (b) `argmax_price E[units | price]` not a valid causal policy on real data, (c) synthetic results, plus D22 (in-memory, per worker process, resets on restart) and D23, and only STATE/code-proven extras (no authN/authZ/TLS, CORS `*` at `src/api/server.py:50`; joblib pickle tied to the XGBoost version; optional explicitly-promoted MLflow registry; no drift monitoring/automated retraining, R15/D13). `test_readme_truth.py`'s forbidden scan now skips **only** the Limitations section, documented in its docstring. **Pre-fix:** `AssertionError: README has no '## Limitations' section` (`1 failed`); **after:** `1 passed`. `docs/ARCHITECTURE.md` deliberately not created (R32 lists it; acceptance does not require it — recorded in ROADMAP). Suite → **99 passed, 0 skipped**.
- **C4 (this commit) — docs.** ROADMAP: **R31 → done** (`0b57fc4`) and **R32 → done** (`f722b08`) with each criterion + fail/pass evidence; R28 note that the residual `DEPLOYMENT.md`/AWS link is gone but R28 stays `todo` on proposed D19; read-only notes for R27 (CI facts) and R30 (coverage baseline); `Last updated`. STATE: tests row → **99 passed, 0 skipped** (clean clone 98+1 after data/model; 1 failed/69 passed/16 skipped/13 errors before), measured coverage line (src 87%, pricing+api 89%), AWS row notes the residual link removal, `Last verified` → `f722b08`. LOG: this entry. Only these three docs; explicit-path staging.
- **Task A (read-only, no commit).** `COVERAGE_FILE=/tmp/.coverage_r30` with `--cov=src/pricing --cov=src/api --cov-report=term-missing` → **89% combined** (405 stmts, 45 miss); `--cov=src` → **87%**. Per file: `error_handlers.py` 63% (44-52, 66-69, 74-84 — unused `APIError`/handlers), `middleware.py` 78% (55-65 request-logging except, 91-95 rate-limit 429 warning, 119-128 error middleware, 155-161 timeout), `router.py` 90%, `server.py` 83%, `engine.py` 96%, `features.py` 96%, `optimizer.py` 95%; below 80 outside the two packages: `health_checker.py` 70%, `evaluate.py` 79%. `git status --short` stayed clean; data went to `/tmp`. Enforcement command: `pytest tests -q --cov=src/pricing --cov=src/api --cov-report=term-missing --cov-fail-under=80`; per-file enforcement is not native to pytest-cov and would currently fail on `middleware.py`/`error_handlers.py`.
- **Task B (read-only, no commit).** Clean clone `/tmp/dp_ci_clone` at `f722b08`: `pytest tests -q` before artifacts → **1 failed, 69 passed, 16 skipped, 13 errors** (the failure is `test_product_id_absent_from_served_feature_columns`; `src.api.router` imports the engine, which raises `FileNotFoundError` on the missing pickle). `regenerate_data.py` **2.22 s** (18,250 rows), `python -m src.training.train` **4.65 s** (R² 0.41930 / MAPE 0.35093), suite after build **98 passed, 1 skipped** (**22.96 s**), `scripts/verify_readme.sh` **42.60 s** (all PASS, archive suite 98+1, smoke 8). No `.github/`; branch `main`; `refs/remotes/origin/HEAD` is not a symbolic ref. Docker base and `.venv` are both Python 3.12 (venv 3.12.3). No env vars needed for CI; a sqlite `MLFLOW_TRACKING_URI` is only needed by the server/smoke step.
- **Task C (read-only, no commit).** `Dockerfile.prod` (multi-stage, non-root; only `docker-compose.prod.yml` references it) and `Dockerfile.hf` (FastAPI+Streamlit via `start.sh`; only `docker-compose.hf.yml` references it) still never build data/model. On a fresh clone the prod compose `./models:ro` mount shadows the image with a model-less host directory, and `joblib.load` at `src/pricing/engine.py:131` raises at import — the container exits instead of serving (STATE §7's "would start but serve no model" is imprecise). Minimal fix: add `RUN python scripts/regenerate_data.py && python -m src.training.train` after `COPY . .` in both Dockerfiles **and** drop the `./models` mounts; deleting the files instead breaks `tests/test_compose_files.py`, `tests/test_start_sh.py` (2 tests), and README's compose commands.

Left open / blocked:
- **R27** stays `todo`, blocked on **proposed D18**; **R28** stays `todo`, blocked on **proposed D19** (the residual AWS README link is gone, but the no-model deploy files remain); **R30** stays `todo` (combined coverage already 89%, but D25 is proposed and the number must be recorded in README; per-file `middleware.py`/`error_handlers.py` are below 80%); **R29** stays `in-progress` (`data.db` still on disk).
- **D7, D18–D21, D24, D25 remain `proposed`** — none accepted or implemented in this batch.
- **Flag:** the repo `.venv` was used to run the clean-clone measurements (the clone has no venv); no packages were installed and no Docker command was run.

Next session should start with:
- Accept/override D18, D19, D25 if the owner wants R27/R28/R30 implemented; otherwise pick another P2 item. Re-run `pytest tests -q` (expect 99 passed, 0 skipped) first.

---

## 2026-10-16 — R23 reopened and closed with scripts/verify_readme.sh; local .venv rebuilt from requirements.txt

Done:
- **STEP 0 (precondition, no commit) — the rebuilt `.venv` verified.** `.venv/bin/pip freeze | grep -Ei "xgboost|nvidia|sqlalchemy|mlflow|protobuf|opentelemetry-proto"` → `mlflow==3.17.1`, `mlflow-skinny==3.17.1`, `mlflow-tracing==3.17.1`, `opentelemetry-proto==1.27.0`, `protobuf==4.25.9`, `SQLAlchemy==2.1.4`, `xgboost-cpu==3.4.1` — **no plain `xgboost`, no `nvidia-*`**. `.venv/bin/pip check` → "No broken requirements found." `.venv/bin/python --version` → Python 3.12.3. `pytest tests -q` → **92 passed, 0 skipped** (pre-C1 baseline). Matches the expected rebuilt stack (SQLAlchemy is present only as an mlflow transitive dep).
- **C1 `5e17dbc` — `feat(scripts): verify_readme.sh runs the README quickstart end to end (R23)`.** New `scripts/verify_readme.sh` (mode 100755) + `tests/test_verify_readme_script.py` (5 tests) + `README.md` (9 added lines: module-form server start, `pytest tests -q`, and a pointer to the script). R23's criterion sentence is "(captured by `scripts/verify_readme.sh`, exit 0)"; the script captures it: `git archive HEAD` → `mktemp -d` (never the working tree) → `python scripts/regenerate_data.py` → `python -m src.training.train` → `python -m src.api.server` (127.0.0.1, `API_WORKERS=1`, `API_RELOAD=false`, sqlite `MLFLOW_TRACKING_URI`; bounded 60 s `/v1/health` wait) → the four README API curls (the optimize curl asserts `optimal_price` is present and `optimization_method == "grid_search"`) → `pytest tests -q` → the smoke tests with `API_URL` set → `python -m py_compile app.py`. Uses `${PYTHON:-python3}`, `VERIFY_PORT` (default 8765), `set -euo pipefail`, one PASS/FAIL line per step, exit non-zero on the first failure, and a trap that kills the server + removes the temp dir. `--with-pip` (venv + `pip install -r requirements.txt`) is opt-in and was **not** run. **Test shown to FAIL before the edit** (`5 failed`: script missing; `bash -n` exit 127; README missing `python -m src.api.server` + `pytest tests -q`; README did not mention the script) and **pass after** (`5 passed`). **Real run** (`.venv` python, port 8765, checked free first): all steps PASS, **exit 0** (archive suite **91 passed, 1 skipped**; smoke **8 passed**). **Mutation check** (temp `git clone`, optimize URL → `/optimize-price`): `FAIL: curl POST /v1/optimize-price`, **exit 1**, `(HTTP 404)`; nothing left on 8766. Ports 8765/8766 free after; `git status --short` clean; the repo was not touched. Committed only the three paths (`git diff --cached --stat` = `README.md` +9, `scripts/verify_readme.sh` +189, `tests/test_verify_readme_script.py` +64).
- **C2 — no commit (README already presents both).** Printed every README line stating R²/MAPE/counts/size: the seed-42 reference at lines 20, 290, 293–294 (`R² 0.419` / `MAPE 0.351`) and the seeds-1–10 mean at lines 299–300 (`mean 0.447 ± 0.029`, `MAPE mean 0.361 ± 0.011`), all stated synthetic (lines 7–8, 289). Both the multi-seed mean and the seed-42 reference are already present, so per C2's explicit condition ("If README already presents both, make no commit and say so") **no README change was made**. `tests/test_readme_truth.py` stays green. (Flag: the seed-42 bullets lead the Model Performance section and the mean is the following paragraph, so the mean is not literally "the headline" — see Flags.)
- **C3 (this commit) — docs.** `STATE.md` (§1 correction rewritten: the `.venv` was rebuilt from `requirements.txt` on 2026-10-16 and now matches the pinned stack — `xgboost-cpu==3.4.1`, no `nvidia-*`, `SQLAlchemy==2.1.4` only transitively; the earlier stale-venv sentence is superseded, not contradicted; the AWS-row scripts list gains `verify_readme.sh`; tests row → **97 passed, 0 skipped**; `Last verified` → `5e17dbc`), `ROADMAP.md` (**R23** files-touched + criterion-1 evidence updated with the script, the real run, the mutation check, and a scope note for the residual non-runnable commands; `Last updated`), `LOG.md` (this entry). Only these three docs; explicit-path staging; no branches, no amends.

Left open / blocked:
- **R23 "every command" residual** — Docker / `pip install` / long-running tuning / ops-shell commands are not run by `verify_readme.sh` (this batch forbids Docker and installs; the network is throttled). Recorded as the scope note under R23.
- **C2 emphasis nuance** — the multi-seed mean is a paragraph below the seed-42 bullets, not the section headline (flagged; no edit made per C2's escape clause).
- **`docs/*` links** still in README → **R31**; **R32** (Limitations) not done; **`data.db`** still on disk → **R29 stays `in-progress`**; **D7, D18–D21, D24, D25 remain `proposed`**.

Next session should start with:
- P2: **R31** (resolve/delink the 5 missing `docs/*` links), **R32** (Limitations section), or **R30** (coverage floor).

---

## 2026-10-16 — D4/D8/D11 accepted; unused sqlalchemy pin dropped; R23 (README truth pass) done

Done:
- **C0 `ddc04d2` — `docs(agents): accept D4, D8, D11`.** `.agents/DECISIONS.md` only: D4/D8/D11 → `Status: accepted` (accepted 2026-10-16), header accepted-list + footer updated, and one "Implementation note" line each — D4 (R4: `src/pricing/features.py::build_serving_features` is the single serving builder; `transformer.py` + the second optimizer deleted in R22, so "both optimizers" is historical), D8 (local `models/demand_model.pkl` + `models/features.json` are canonical; MLflow registry is an optional, explicitly promoted path via `scripts/promote_model.py` with a loud fallback), D11 (R18/R19/R35; enforced by `tests/test_config.py` + `tests/test_env.py`).
- **C1 `c936519` — `chore(deps): drop the unused sqlalchemy pin (R21 follow-up)`.** `requirements.txt` only (−3 lines: the comment + `sqlalchemy==2.1.4`). **Dependency audit (direct deps, importing modules in `src/`/`scripts/`/`app.py`/`tests/`):** all 21 direct deps are used at runtime or by tests, **except `sqlalchemy`** (0 importers; its only importer `src/data/ingest.py` was deleted in R22) → removed. Package→import mapping handled explicitly: `pyyaml`→`yaml` (`src/api/router.py:8`, `src/utils/env_config.py:5`, `src/training/train.py:1`, scripts, tests), `python-dotenv`→`dotenv` (`src/utils/env_config.py:6`), `scikit-learn`→`sklearn` (trainer/evaluate), `xgboost-cpu`→`xgboost` (trainer/tuning), `protobuf`→`google.protobuf` (pinned for mlflow). **Kept although not directly imported (documented):** `scipy` (transitive via `scikit-learn`), `pyarrow` (pandas parquet engine for `read_parquet`/`to_parquet`), `httpx` (required by `fastapi.testclient.TestClient`), `protobuf` (mlflow). **Evidence:** `tests/test_requirements_pinned.py` → **3 passed**; `.venv/bin/pip check` → "No broken requirements found."; `pip install --dry-run --ignore-installed -r requirements.txt --report /tmp/pin_report2.json` **could not complete** (this machine throttles `files.pythonhosted.org`; it timed out fetching `gitpython`'s wheel metadata, a `streamlit` transitive dep, across 4 attempts) → a **`--no-deps`** report (21 direct deps) was produced instead: **`xgboost-cpu==3.4.1` present, no `nvidia-*`, `mlflow==3.17.1`, `protobuf==4.25.9`, `requests` exactly once, no plain `xgboost`**. `sqlalchemy` still resolves transitively: `mlflow` 3.17.1 declares `sqlalchemy<3,>=1.4.0` (read from installed METADATA); `xgboost-cpu 3.4.1`'s PyPI `requires_dist` lists no `nvidia`/`nccl`. Suite unchanged (**90 passed**).
- **C2 `f26dee3` — `docs(readme): truth pass — remove false claims, fix commands and numbers (R23)`.** `README.md` + new `tests/test_readme_truth.py`. **Audit (76 rows, `/tmp/r23_audit.md`):** true/kept **30**, false **31**, stale **7**, unverifiable **2**, not-run **1**; actions **fixed 22 / removed 17 / kept 37**. Headline fixes: `production-ready`/`enterprise-grade`/`PRODUCTION READY` removed; R² 0.49 → **0.419 + MAPE 0.351** (seed 42) with the seed-1–10 spread; `python src/training/train.py` → `python scripts/regenerate_data.py` + `python -m src.training.train`; curl path → `/v1/optimize-price` and `"bayesian"` → `"grid_search"`; `default_method`/`run_hyperparameter_tuning` config keys removed; AWS EC2 + pre-deploy + backup/restore-DB sections removed; `Python 3.9+` → `3.12`; D8 serving note added (local artifact; registry optional + explicitly promoted; loud fallback); in-memory/per-worker rate-limit limitation stated; all data/metrics stated synthetic. **Regression test:** `tests/test_readme_truth.py` — (a) every repo-relative path in a README code span/block exists (documented ignore list for gitignored generated artifacts: `models/demand_model.pkl`, `reports/training_metrics.json`, `reports/feature_importance.csv`); (b) forbidden-phrase list (23 entries, one reason each) built from STATE/DECISIONS. **Shown to FAIL on the pre-edit README** (`2 failed`; 5 missing paths `['backups/database/latest.db','scripts/backup_database.sh','scripts/deploy.sh','scripts/pre_deploy_check.sh','scripts/restore_database.sh']` + 18 offenders incl. `bayesian`, `default_method`, `run_hyperparameter_tuning`, `sqlite`, `retention`, `shap`, `model versioning`, `production-ready`, `0.49`, `49%`) and **pass after** (`2 passed`). **Walkthrough (fresh clone `/tmp/readme_walk` of `ddc04d2`, `.venv` python, API on `127.0.0.1:8765`, no `.env`; `pip install`+docker skipped):** `regenerate_data.py` → 18,250 rows; `python -m src.training.train` → R² **0.41930** / MAPE **0.35093** / MAE **22.70** / 30 features; `/v1/health` **200** `source: local`; README path `POST /optimize-price` → **404**; body verbatim `"bayesian"` → **422**; `"grid_search"` → **200** (`optimal_price 78.26`, `expected_revenue 6302.45`); `/v1/health/ready|live` **200**, `/v1/metrics` **200**; `py_compile app.py` exit 0; `pytest tests/test_streamlit_contract.py` **5 passed**; `pytest tests/ -q` → **89 passed, 1 skipped** (skip `tests/test_env.py:48`); API stopped, `ss -ltn | grep 8765` empty. Docker/compose compared statically (service `pricing-api`, port 8000, commands match).
- **C3 `7ca9014` — `fix(scripts): load_test.sh uses grid_search (R23)`.** `scripts/load_test.sh:46` `"bayesian"` → `"grid_search"` (only occurrence). `bash -n` → exit 0. **Proof (curl of the script's extracted payload against the API on `127.0.0.1:8765`):** extracted body → **HTTP 200**; old `"bayesian"` body → **HTTP 422** (`literal_error`). API stopped; `ss -ltn | grep 8765` empty.
- **C4 (this commit) — docs.** `STATE.md` (README curl + training-command rows → CONFIRMED/R23; tests row → **92 passed, 0 skipped** / 89+1 in a clone; SQLite + AWS rows updated; MLflow row updated; §5.4/§5.5 resolved; **§1 correction: the working `.venv` has plain `xgboost==3.4.1` + `nvidia-nccl-cu13==2.32.3`, not `xgboost-cpu`**; `Last verified` → `7ca9014`), `ROADMAP.md` (**R23 → done** with acceptance-criteria coverage + audit + walkthrough + regression test; **R21** follow-up note for the sqlalchemy removal; **R29** note that the README DB claims are now struck; `Last updated`), `LOG.md` (this entry). Only these three docs; explicit-path staging; one commit per code step; no branches, no amends.

Left open / blocked:
- **`docs/*` links kept in README** (`docs/API.md`, `docs/OPERATIONS.md`, `DEPLOYMENT.md`, `PRODUCTION_FEATURES.md`, `PRODUCTION_READY.md`) per the batch instruction — **R31** owns them.
- **R32** (Limitations section) not done — content to cover: synthetic data only, observational model (`argmax_price E[units|price]` is not a causal policy), per-worker in-memory rate limit.
- **`app.py:65-66`** "Product ID" `st.number_input` still has no help text (out of scope; listed).
- **`APIError`** is never raised and no test references it (kept, R22 flag).
- **`data.db`** still exists locally (untracked/gitignored; owner deletes it) → **R29 stays `in-progress`**.
- **`D7, D18, D19, D20, D21, D24, D25` remain `proposed`** (D7 is *also* proposed — not in the batch's list; noted).
- **Full `pip --report` dry-run** not produced (network throttled at `gitpython` metadata); `--no-deps` report + METADATA used instead.
- **P1 status: all P1 items are `done`** (R4, R5, R11–R26, R34, R35); remaining work is P2 (R27, R28, R29, R30, R31, R32).

Next session should start with:
- P2: **R31** (resolve/delink the 5 missing `docs/*` links) or **R32** (Limitations section); or **R30** (coverage floor).

---

## 2026-10-15 — R22 done: all dead code deleted, import-graph test added, D9/D10/D12 accepted; R29 partly resolved

Done:
- **C0 `55ae934` — `docs(agents): accept D9, D10, D12 (R22)`.** `.agents/DECISIONS.md` only: D9/D10/D12 → `Status: accepted` (accepted 2026-10-15), header accepted-list updated, and the D9 "Implementation note (user decision, 2026-10-15)" recording that the local untracked `data.db` is **not** deleted (the owner will remove it). D4/D8/D11 untouched.
- **C1 `0b73403` — `test(optimizer): assert the inventory cap on the live optimizer path (R22 prerequisite)`.** `tests/test_optimizer.py` (+ real-model fixtures) and `tests/test_api.py` each compute the unconstrained optimum, assert the cap is binding (unconstrained demand > limit), then assert `expected_demand <= inventory_limit` on the live path. **Mutation check (throwaway `/tmp/r22_mut`, cap disabled at `src/pricing/optimizer.py:48-49`):** both new tests **FAIL** (`assert 80.53225708007812 <= 40`); real repo → **2 passed**. Suite 102 → **104 passed, 2 skipped**.
- **C2 `c4b9fb1` — `refactor(pricing): delete the unreachable BayesianPriceOptimizer and its tests (D1/D2, R22)`.** Deleted `src/pricing/bayesian_optimizer.py` (216 lines); removed `TestBayesianOptimizer` (3), the 5 Bayesian tests in `tests/test_optimizer_real.py`, and the 2 "both optimizers" tests in `tests/test_serving_features.py`; edited `test_exactly_one_function_computes_price_dependent_features` to reference only `optimizer.py`; updated docstrings. Coverage-preservation table: **no row NONE** (inventory-cap → the C1 tests; near-optimality → the kept R2/R6 tests; margin → `test_api::test_optimize_with_constraints`; schema → `test_grid_path_response_contract`). Evidence: `grep` NO MATCHES; `IMPORT_OK`; `pytest tests/test_optimizer_real.py -v` → **7 passed**; R7 served ratios (kept live tests) 1.00048 / 0.99991 / 1.00000 / 1.00000 / 1.00077. Suite **104 → 88 passed, 0 skipped** (predicted 106 − 18 = 88; the 2 removed skips were the Bayesian bound-hugging parametrizations). **Process note:** the first commit attempt staged only the deletion (a combined `git add` failed on the deleted path), leaving a red commit; it was redone with `git reset --soft HEAD~1` + one green commit (not `git commit --amend`).
- **C3 `3b51851` — `refactor: delete orphan modules revenue, metrics_tracker, optimize, feature_pipeline (D12, R22)`.** No importer/test for any; `IMPORT_OK`; `src.monitoring.prediction_logger`/`src.features.feature_builder` still import. Suite **88 passed**.
- **C4 `026ed00` — `refactor(utils): delete the unused config loader (D12, R22)`.** `src/utils/config.py`; its only importer (`feature_pipeline`) was deleted in C3. `env_config.py` untouched. Suite **88 passed**.
- **C5 `87fdf8a` — `refactor(data): delete the SQLite ingestion chain and DB scripts (D9/D12, R22/R29)`.** Deleted `src/data/{ingest,pipeline_runner,validation}.py` + `scripts/{backup,restore}_database.sh`. Pre-deletion repo-wide `grep` for `backup_database|restore_database|ingest|pipeline_runner|data.validation` → only `.agents/*` and `README.md` prose; the STOP-check (`start.sh`/`Dockerfile*`/compose/`scripts/*`/`tests`/`.github`) → **no matches**. `data.db` **untouched** (untracked/ignored). **Flag:** `sqlalchemy==2.1.4` (`requirements.txt:30`) is now an unused declared dependency (out of scope). Suite **88 passed**.
- **C6 `849a866` — `refactor(pricing): drop the unused model_loader and its import (D12, R22)`.** Deleted `src/pricing/model_loader.py` and only `engine.py:10`; `load_production_model` had no caller. `pytest tests/test_mlflow_registry.py -v` → **4 passed**. Suite **88 passed**.
- **C7 `49243af` — `refactor(api): delete never-raised error subclasses (R22)`.** Removed `ModelNotFoundError`/`OptimizationError`/`InvalidInputError`; kept `APIError` + its registered handler. **Flag:** nothing raises `APIError` and no test references it (`server.py:16,41` register the handler) — kept per instruction. Suite **88 passed**.
- **C8 `fb5e2a5` — `refactor: delete dead symbols log_prediction, load_logs, get_env, EcommerceDataGenerator.run (D12, R22)`.** `PredictionLogger.log_prediction`/`load_logs` (kept the class; also dropped the now-unused `import pandas as pd`), `EnvConfig.get_env`, generator `run()` + its `__main__`. Each grep proved no caller. Suite **88 passed**.
- **C9 `e8da719` — `test(arch): assert every module under src/ is reachable from an entry point (R22)`.** New `tests/test_import_graph.py` (AST-only; roots `src.api.server` + `src.training.train` + the `src.*` imports of `scripts/*.py`/`app.py`; empty, rot-proof allowlist). **Convention 18:** extracted `62333ea` to `/tmp/r22_before`, copied the test in, ran with `.venv` python → **FAILS** listing 11 dead modules (`src.data.ingest`, `pipeline_runner`, `validation`, `features.feature_pipeline`, `features.transformer`, `monitoring.metrics_tracker`, `pricing.bayesian_optimizer`, `pricing.integrated_optimizer`, `pricing.optimize`, `pricing.revenue`, `utils.config`); passes on HEAD. Suite → **90 passed, 0 skipped**.
- **C10 (this commit) — docs.** `STATE.md` (§3 emptied; unit-tests row → **90 passed, 0 skipped**, recording 18 removed / 4 added and the one ported property = inventory cap; `Last verified` → `e8da719`), `ROADMAP.md` (**R22 → done** with the committed disposition table + coverage-preservation note + acceptance-criteria coverage; **R29 → in-progress** with the removal/remaining record; **R23** new stale-README note; D4/D8/D11 still `proposed`; `Last updated`), `LOG.md` (this entry). Only these three docs.

Left open / blocked:
- **R29 stays `in-progress`** — the local untracked `data.db` remains (the owner deletes it) and the README DB claims remain for R23.
- **Flags:** `sqlalchemy` is now an unused declared dependency; `APIError` is never raised and no test references it (kept); the C2 staging redo (see C2).
- **D4/D8/D11 remain `proposed`** and were not implemented.

Next session should start with:
- R23 (README truth pass — the DB/ingestion/validation/backup sentences and the `"bayesian"` strings) or the remaining P2 items per `.agents/ROADMAP.md`.

---

## 2026-10-15 — R22 group 1 done (integrated_optimizer/transformer deleted); R22 group 2 blocked on a coverage gap; R14 follow-up; docs

Done:
- **C1 `7368ef1` — `refactor(pricing): delete integrated_optimizer and transformer (D1, R22)`.** Files (deleted): `src/pricing/integrated_optimizer.py`, `src/features/transformer.py`, `tests/test_integration.py`. **Pre-deletion analysis:** the 5 tests in `tests/test_integration.py` (`test_feature_transformer`, `test_integrated_optimizer`, `test_optimizer_with_constraints`, `test_predict_demand`, `test_evaluate_price_range`) all exercise only the dead `IntegratedPricingOptimizer`/`FeatureTransformer` — neither is on the live path (`PriceOptimizer`/engine/router) — so **no live-path coverage was lost**. **Evidence:** `grep -rn "integrated_optimizer\|features.transformer\|from src.features import" src scripts tests app.py --include=*.py` → **no matches** (only stale, gitignored `.pyc` bytecode matched the unfiltered grep); no `__init__.py` re-export existed in `src/pricing` or `src/features`; `python -c "import src.api.server, src.training.train"` → `IMPORT_OK`; the AST import graph (`/tmp/r22_import_graph.py`) shows the two modules gone and **no other module lost its importer**; suite **107 → 102 passed, 2 skipped, 0 failures**.
- **C2 — STOPPED (no deletion performed).** The coverage-preservation check failed. The property *"the optimizer caps `expected_demand` at `inventory_limit`"* is a **live-optimizer** property (`src/pricing/engine.py:185,193` → `src/pricing/optimizer.py:48-49`) whose **only** asserting test is the to-be-deleted `tests/test_optimizer.py::TestBayesianOptimizer::test_inventory_constraint` (a **mock** test); **no kept test asserts it on the live path** (`tests/test_api.py::test_optimize_with_constraints` passes `inventory_limit=100` but asserts only the margin). Per the batch gate, C2 was stopped and **no tests were ported**. The other properties the deleted tests assert are covered on the live path (revenue ratio ≥ 0.99 for the five R7 ranges → `tests/test_optimizer_real.py::test_served_grid_optimizer_reaches_reference_optimum[5]` + `tests/test_api.py::test_grid_path_reaches_reference_optimum`; the R1 bound-aware rule and "no gradient method on a tree objective" behaviourally guarded by the same kept ratio tests; serving-features column order → `test_serving_builder_covers_committed_columns_in_order` + `test_grid_optimizer_builds_complete_feature_frame`). Full table in `.agents/ROADMAP.md` R22.
- **C3 `9f0dc1d` — `fix(scripts): run smoke tests via python3 -m pytest (R14 follow-up)`.** `scripts/run_smoke_tests.sh:39`: `pytest tests/smoke_tests.py -v` → `python3 -m pytest tests/smoke_tests.py -v` (one line). `bash -n scripts/run_smoke_tests.sh` → exit 0. Suite unchanged (**102 passed, 2 skipped**).
- **C4 (this commit) — docs.** `STATE.md` (removed the `IntegratedPricingOptimizer`/`FeatureTransformer` rows from §3; unit-tests row → **102 passed, 2 skipped (104 collected)**; §3 note on the deletions; `Last verified` → `9f0dc1d`), `ROADMAP.md` (**R22 → `in-progress`** with group 1 done / group 2 blocked; **R23** note that `README.md:157`, `README.md:332`, `scripts/load_test.sh:46` still send/reference `"bayesian"` (HTTP 422 under D2) and `app.py:65-66` shows a "Product ID" input with no help text; `Last updated`), `LOG.md` (this entry). Only these three docs; explicit-path staging; one commit per code step; no branches, no amends.
- **Task A (read-only, no commit) — decisions dump.** Printed D4/D8/D9/D10/D11/D12 verbatim from `.agents/DECISIONS.md` with impact notes, answered the D8 MLflow-registry question (`src/pricing/engine.py:52` `_resolve_production`, `:77` `load_model`), and printed R28–R32.

Left open / blocked:
- **R22 group 2 is blocked** on the inventory-cap coverage gap — the owner must decide whether to accept the gap or add a live-path assertion in a later batch.
- **The rest of R22** (`revenue.py`, `metrics_tracker.py`, `feature_pipeline.py`, `optimize.py`, `src/data/{ingest,pipeline_runner,validation}.py`, `src/utils/config.py`, `model_loader.py`, the dead symbols, the import-graph test + disposition table) is blocked on the `proposed` decisions D4/D8/D9/D10/D11/D12.

Next session should start with:
- Owner decision on **R22 group 2** (accept the inventory-cap coverage gap, or add a live-path assertion), then continue R22 per `.agents/ROADMAP.md`.

---

## 2026-10-15 — R14 + R34 implemented and verified (smoke tests collectable + skip-when-offline; product_id is not a model feature)

Done:
- **C1 `47ea3d6` — `test(smoke): make smoke tests collectable pytest tests with a skip-when-offline fixture (R14)`.** Files: `tests/smoke_tests.py`, `scripts/run_smoke_tests.sh`, `README.md`. **Before:** `pytest tests/smoke_tests.py --collect-only -q` → **0 collected, exit 5**. Removed the `SmokeTestRunner` class + `__main__`; 8 module-level `test_*` checks now share a module-scoped `api_base_url` fixture that probes `/v1/health` once (2 s, no retry loop) and `pytest.skip`s on connection error; base URL from `API_URL` (default `http://localhost:8000`); the two `"bayesian"` payloads → `"grid_search"` (D2 rejects `"bayesian"` with 422). `scripts/run_smoke_tests.sh` → `pytest tests/smoke_tests.py -v` (`bash -n` exit 0); `README.md:174` → `API_URL=http://localhost:8000 pytest tests/smoke_tests.py -v`. **After:** collect-only → **8 collected**; `API_URL=http://127.0.0.1:59999 pytest tests/smoke_tests.py -q -rs` → **8 skipped, exit 0**; live API (`python -m src.api.server`, `API_HOST=127.0.0.1 API_PORT=8765 API_WORKERS=1 API_RELOAD=false MLFLOW_TRACKING_URI=sqlite:////tmp/smoke_mlflow.db`, `/v1/health` 200 after 3 s) → **8 passed in 0.47 s**; server killed, `ss -ltn | grep 8765` empty, no `mlflow.db`/`mlruns` created. **Default discovery:** `pytest.ini` `python_files = test_*.py` does not match `smoke_tests.py`, so a plain `pytest tests -q` does **not** collect it (0 matches); no `pytest.ini` change made. Suite → **103 passed, 2 skipped** (unchanged).
- **C2 `ecb98ac` — `fix(api): state that product_id is not a model feature; add contract tests (R34)`.** Files: `src/api/schemas.py` (Field description only), `tests/test_product_id_contract.py` (new, 4 tests). **Before:** `PricingRequest.model_fields["product_id"].description` → `'Product ID'`; test (i) **FAILS** (`got 'Product ID'`), (ii)/(iii) pass. Description now: `"Product ID, accepted for request compatibility and logging only. It is NOT a model feature and does not influence the predicted demand or price."` (field stays `Field(..., ge=0)`). Served feature list checked as `PricingEngine.feature_columns` (`src/pricing/engine.py:31` declared, `:138` loaded, `:175` passed to `PriceOptimizer`). Behavioural invariance via the `client` TestClient fixture (product_id 1 vs 999 → identical price/demand/revenue) is a **characterization** test that passed before the fix too. **After:** 4 passed; suite → **107 passed, 2 skipped** (+4). UI check (read-only, not edited): `app.py:65-66` show the product-id input in the pricing form with no "ignored" help text.
- **C3 (this commit) — docs.** `STATE.md` (unit-tests row → **107 passed, 2 skipped**; R14 note; §5.15 resolved; `Last verified` → `ecb98ac`), `ROADMAP.md` (**R14 → done**, **R34 → done** with before/after evidence; **R27** note that CI must start the API for the smoke tests to actually run; `Last updated`), `LOG.md` (this entry). Only these three files; explicit-path staging; one commit per code step; no amends, no branches.

Left open / blocked:
- Nothing blocked. **Task A (R22 dead-code brief) was delivered read-only** this session (ast import graph in `/tmp`); no commit.

Next session should start with:
- **R22** (dead code: delete or wire+test, file by file) using the read-only brief — first confirm the `proposed` DECISIONS the user must accept (notably D4 and D9), since a `proposed` decision must not be implemented.

---

## 2026-10-15 — R25 closed (clean-clone build + health verified); seed sweep; convention 35; R14/R34 briefs

Done:
- **C0 (this commit) — docs.** `STATE.md`: the metrics row now records the seed sweep (R² 0.40602–0.50037, mean 0.44650, pop-std 0.02919; MAPE 0.34671–0.37953, mean 0.36080) and the pre-D30 unseeded range (0.4328–0.4750, so 0.475 was one lucky draw) — with the note that the D30 R² shift (≈0.056 ≈ 1.9 seed-σ) is within the seed-to-seed spread; the stale dead-code row (`MlflowTracker.*` "cannot run here") corrected; `Last verified` refreshed. `ROADMAP.md`: **R25 → done** (clean-clone evidence + final covered list + follow-up notes); a **R28** note that `Dockerfile.prod`/`Dockerfile.hf`/the prod `./models:ro` mount ship no model on a fresh clone; `Last updated`. `CONVENTIONS.md`: **rule 35** (every commit leaves the suite green; a config key ships with its reader — example `ae01b35`→`d29dfa8`) and `Last updated`. `LOG.md`: this entry. Only these four files; explicit-path staging; no code/test/Dockerfile/compose edits; `README.md` untouched.
- **Task A (no commit) — honest metric spread across data seeds.** `git clone --no-hardlinks` → `/tmp/sweep`; for seeds 1–10 and 42, a copy of the clone had only its `configs/config.yaml` `data.seed` changed, then `python scripts/regenerate_data.py && python -m src.training.train` (`.venv` python, `MLFLOW_TRACKING_URI` unset, no `.env`, `MLFLOW_ALLOW_FILE_STORE` never set) and `pytest tests/test_optimizer_real.py -q` inside the copy. Never touched the repo working tree. Every seed: regen rc=0, train rc=0.

  | seed | R² | MAPE | MAE | Train_R2 | R7 (`test_optimizer_real.py`) |
  |---|---|---|---|---|---|
  | 1 | 0.430168 | 0.363388 | 23.82 | 0.877289 | 18 passed, 2 skipped |
  | 2 | 0.500369 | 0.347016 | 21.80 | 0.887087 | 19 passed, 1 skipped |
  | 3 | 0.406023 | 0.378840 | 24.89 | 0.868634 | 19 passed, 1 skipped |
  | 4 | 0.437796 | 0.361286 | 23.33 | 0.877851 | 17 passed, 3 skipped |
  | 5 | 0.481213 | 0.355323 | 22.42 | 0.883245 | 19 passed, 1 skipped |
  | 6 | 0.426557 | 0.379533 | 24.81 | 0.866021 | 18 passed, 2 skipped |
  | 7 | 0.464681 | 0.346707 | 22.06 | 0.870945 | 18 passed, 2 skipped |
  | 8 | 0.439796 | 0.356891 | 23.25 | 0.873608 | 18 passed, 2 skipped |
  | 9 | 0.411318 | 0.361696 | 23.36 | 0.871540 | 19 passed, 1 skipped |
  | 10 | 0.467068 | 0.357364 | 22.84 | 0.881110 | 20 passed, 0 skipped |
  | 42 | 0.419302 | 0.350931 | 22.70 | 0.869708 | 18 passed, 2 skipped |

  **R² (seeds 1–10):** mean **0.44650**, pop-std **0.02919** (sample-std 0.03077), min **0.40602** (seed 3), max **0.50037** (seed 2). **MAPE (seeds 1–10):** mean **0.36080**, pop-std **0.01063**, min **0.34671** (seed 7), max **0.37953** (seed 6). **Seed 42** (the configured seed): R² **0.41930** / MAPE **0.35093** — 3rd-lowest R² of 11. **No seed made any R7 test fail** (0 failures/errors everywhere; the 0–3 skips are the R1 bound-hugging cases, which vary with the model). Total wall time ≈1 min 51 s (well inside the 20-min budget).
- **Task B (no commit) — read-only briefs for R14 and R34 + smoke collect.** `pytest tests/smoke_tests.py --collect-only -q` and `pytest tests/smoke_tests.py -q` both collect **0 items** (exit 5; no network touched). Full briefs delivered in the session report (not committed).

Left open / blocked:
- **R14** and **R34** remain `todo` (briefs only; not implemented, per the batch scope).
- `mlflow-server` :5000 health is still unverified — it is **not** an R25 acceptance criterion (see the R25 follow-up notes in `.agents/ROADMAP.md`).
- The clean-clone Docker build reused the Docker cache; a **cold** clean-clone build was not re-run (the cold-build evidence is the earlier working-tree 1590 s run).

Next session should start with:
- Pick up R14 (convert `tests/smoke_tests.py` into a collectable pytest module) or R34 (`product_id` contract), per the briefs. See `.agents/ROADMAP.md`.

---

## 2026-10-15 — D30 implemented (seeded, reproducible data + model; image builds its own model); R25 stays in-progress

Done:
- **D30 accepted and implemented.** Commits: `e0c007e` (docs: accept D30), `ae01b35` (seed the synthetic generator), `d29dfa8` (script reads size+seed from config), `9eccd41` (drop the orphan `.gitignore` `# Docker` header), `ecdb464` (build data+model in the image; keep local artifacts out of the context), plus this docs commit. All on `main`, one commit per step, no amends, no branches, explicit-path staging only.
- **C0 `e0c007e` — D30 recorded in `.agents/DECISIONS.md`** (Status: `accepted`, date 2026-10-15) with the 6 points (seeded generator; config-driven size; regenerate+retrain+R7; main Dockerfile builds data+model; `.dockerignore` excludes local artifacts; prod/hf/compose untouched). Header accepted-list and `Last updated` refreshed. Only that file.
- **C1 `ae01b35` — `src/data/generator.py` seeded.** Added `seed=42` to `__init__` and a local `np.random.default_rng(seed)` created **before** `_generate_products`; replaced every global `np.random.uniform/randint/choice/normal` with `self.rng.*` (`randint`→`integers`, the Generator equivalent) and the stdlib `random.choice` for `category` with `self.rng.choice` (**closest equivalent — flagged**). Column logic and formulas unchanged (columns verified identical). `configs/config.yaml` gained `data.seed: 42`. New `tests/test_generator_determinism.py` (2 tests). **Before:** `pytest tests/test_generator_determinism.py -q` → **2 failed** (`TypeError: EcommerceDataGenerator.__init__() got an unexpected keyword argument 'seed'`); a `/tmp/unseeded_demo.py` run of the pre-fix generator showed `frames equal? False` (a head `[74, 54, 35, 76, 72]` vs `[220, 176, 42, 155, 131]`). **After:** 2 passed. **Flag:** `configs/config.yaml`'s `data.seed` has no reader until C2, so `tests/test_config.py::test_every_yaml_key_is_read_by_code` is red **between C1 and C2** (`['config.yaml:data.seed']`); C2 adds the reader and it goes green. (The user's C1 spec explicitly puts `data.seed` in C1 and its reader in C2.)
- **C2 `d29dfa8` — `scripts/regenerate_data.py` reads size + seed from config.** Loads `configs/config.yaml` once at the top and passes `data.n_products`/`data.days`/`data.seed` (defaults 50/365/42) to the generator; the later duplicate config read is removed. `configs/config.yaml` gained `data.n_products: 50` and `data.days: 365`. **Documented-size grep:** `STATE.md:81` "18,250 data rows", `STATE.md:83` "16,500 × 32 cols", `STATE.md:279` "committed artifacts correspond to **50 products** (18,250 raw / 16,500 feature rows)"; `README.md` — **no** dataset-size statement; `configs/` — none before this change; `scripts/regenerate_data.py:21` hardcoded `n_products=100, days=365`. The working-tree artifacts are **18,250 raw rows (50 products × 365 dates) / 16,500 feature rows / 32 cols** — so the documented size **50** is used. No test added: `main()` writes to the repo's `data/` via `RAW_DATA_DIR`, so per the spec it is proven in a fresh clone instead (Task A). `pytest tests/test_config.py tests/test_generator_determinism.py -q` → **7 passed** (config test green again).
- **TASK A (no commit) — clean-clone reproducibility, `/tmp/clean_a` + `/tmp/clean_b` at `d29dfa8`.** `git clone --no-hardlinks` from the local repo; `MLFLOW_TRACKING_URI` **unset** and **no `.env`**. **Network method:** `unshare -n` is not permitted in this sandbox, so each command ran under `strace -f -e trace=network -o …` — **zero** `connect`/`sendto`/`sendmsg` calls in either `scripts/regenerate_data.py` or `python -m src.training.train` (only thread `exited` lines). Timings: clean_a `regen 2.55 s` (strace overhead) / `train 17.86 s`; clean_b `regen 2.20 s` / `train 3.99 s` (≈6 s for both without strace). **Identical between clones:** `data/raw/ecommerce_sales.csv` sha256 `2f3f72ce1736147b2f14706e29aa67a6d6e7d417051b1733a3e5ed31c10e077a`; `data/features/training_features.parquet` `ed950d964f58207b08e21ca78367a18bf2ba955fdb253109377d8fe1707603c5`; `models/demand_model.pkl` `95347c4f3f069d44309786abc0394cbb42568dfdfa15155d1106b231975a5caf`; `models/features.json` `5d493364…`; `reports/training_metrics.json` **byte-identical**. So the pickle hash is **identical too** (xgboost is deterministic here: `tree_method="hist"`, `random_state=42`, no explicit `n_jobs`). Row counts: **18,250 raw / 16,500 feature / 32 cols** in both. `pytest tests -q` in clean_a → **100 passed, 3 skipped, 0 errors** (the extra skip vs the repo is `tests/test_env.py` — no `.env`).
- **TASK B (no commit) — repo working-tree artifacts.** Backed up `models/`, `data/`, `reports/` to `/tmp/artifact_backup_2026-10-15` (models 2.6 M, data 4.5 M, reports 12 K; old pickle sha256 `e9e81e37…`). Ran `python scripts/regenerate_data.py` (2.17 s) + `python -m src.training.train` (3.73 s) in the repo. `git status --short` → **empty** (no tracked file changed); `models/features.json` **byte-identical** (`5d493364…`). All four artifacts **match clean_a** exactly. `pytest tests -q` → **103 passed, 2 skipped, 177 warnings in 21.96 s** (0 errors); `pytest tests/test_optimizer_real.py -v` → **18 passed, 2 skipped**.
- **New metrics (D30 retrain, 2026-10-15):** `R2 0.41930`, `MAPE 0.35093`, `MAE 22.70`, `Train_R2 0.86971`, `RMSE 30.97`, `Directional_Accuracy 0.7342`. **Old (unseeded):** `R2 0.47498`, `MAPE 0.34581`, `MAE 21.44`, `Train_R2 0.88029`. **ΔR² = −0.0557 (>0.02 → called out); ΔMAPE = +0.0051.** The change is expected: a seeded `Generator` draws a different sequence than the old global RNG.
- **R7 revenue ratios (repo, new model; reference computed at test time, 901-pt grid):** served grid `(30,80)` **1.00048**, `(70,110)` **0.99991**, `(10,200)` **1.00000**, `(100,120)` **1.00000**, `(30,120)` **1.00077** — all ≥ 0.99.
- **Pickle warning:** loading the **backed-up old** pickle emits `UserWarning: … generated by an older version of XGBoost …`; loading the **D30-retrained** pickle emits **no** warning (xgboost 3.4.1).
- **C3 `9eccd41` — dropped the orphan `# Docker` header from `.gitignore`.** Diff is exactly that comment line + one blank line; `git show HEAD:.gitignore` non-comment entries vs the working tree → **no entry differences** (comments/blank only).
- **C4 `ecdb464` — image builds data + model; local artifacts excluded.** (a) Added `tests/test_repo_hygiene.py::test_dockerignore_excludes_local_model_and_features` (`.dockerignore` contains `models/*.pkl` and `data/features/`) and new `tests/test_dockerfile_model_build.py` (the main Dockerfile has a RUN mentioning both `scripts/regenerate_data.py` and `src.training.train` **after** `COPY . .`). **Before:** both **FAIL** (missing entries; no RUN after COPY). (b) `.dockerignore` gained `data/features/` and a `# Models` section with `models/*.pkl` (de-indented, no trailing spaces); the main `Dockerfile` gained `RUN python scripts/regenerate_data.py && python -m src.training.train` after `COPY . .` (pip-install line and CMD untouched). **After:** `pytest tests/test_repo_hygiene.py tests/test_dockerfile_model_build.py -q` → **6 passed**. **Docker was not run** — the real `docker compose build` is the owner's to verify.
- **C5 (this commit) — docs.** `STATE.md`: R² row, XGBoost row, §2 training path + verified facts, the unit-tests row (**103 passed, 2 skipped**), the Docker-deployment row (main Dockerfile now builds data+model; prod/hf/mount do not), §7 (unseeded-generator and non-reproducible-metrics findings → **RESOLVED**; new open finding on prod/hf/mount), and `Last verified`. `ROADMAP.md`: R25 note (stays `in-progress`), R27 note confirmed, `Last updated`. Only these three docs.

Left open / blocked:
- **R25 stays `in-progress`:** the remaining acceptance is the **user's clean-checkout** `docker compose build` + `curl http://localhost:8000/v1/health` → 200 on a fresh clone (the main image now builds its own model from tracked inputs). Not run here (no docker).
- **`Dockerfile.prod`, `Dockerfile.hf`, and `docker-compose.prod.yml`'s `./models:/app/models:ro` mount do not build or contain a model** (open) — reported only; D30 deliberately does not touch them.
- **Transient:** `tests/test_config.py::test_every_yaml_key_is_read_by_code` was red at commit `ae01b35` only (the `data.seed` key's reader lands in `d29dfa8`); green from `d29dfa8` on.
- The seeded data is **different** from the previously committed artifact, so the recorded metrics changed (R² −0.056). Not a regression to chase here — it is the honest, now-reproducible number.

Next session should start with:
- The owner's clean-checkout `docker compose build` + health check to close R25 (the main image now trains its own model), and decide whether `Dockerfile.prod`/`Dockerfile.hf`/the prod mount should build a model too. See `.agents/ROADMAP.md`.

---

## 2026-10-15 — D29 implemented (tracked, clean `.dockerignore`; `.env` excluded); clean-clone investigation + R25 health evidence

Done:
- **D29 accepted and implemented.** Commits: `b174774` (docs: accept D29), `a6170b6` (chore(docker): track `.dockerignore`, de-indent it, exclude `.env`), plus this docs commit. All on `main`, one commit per step, no amends, no branches.
- **C0 `b174774` — D29 recorded in `.agents/DECISIONS.md`** (Status: `accepted`, date 2026-10-15): `.dockerignore` becomes tracked; every line de-indented; `.env` excluded from the image; hygiene tests guard it. Header accepted-list and `Last updated` refreshed. Only that file.
- **C1 `a6170b6` — `.dockerignore` tracked, de-indented, `.env`-excluding.** (a) Saved the pre-change stripped non-blank entry set to `/tmp/dockerignore_before.txt` (**58** entries). (b) Added three tests to `tests/test_repo_hygiene.py`: no `.dockerignore` line carries leading/trailing whitespace (blank lines truly empty); `.dockerignore` contains exactly `.env`, `mlflow.db`, `mlruns/`; `.gitignore` has no entry exactly `.dockerignore`. **Before:** `pytest tests/test_repo_hygiene.py -q` → **3 failed, 1 passed** (the whitespace test listed offending lines **1-71 except 42-43**; the entry test reported `missing ['.env']`; the gitignore test found the `.dockerignore` entry). (c) Removed the `.dockerignore` entry from `.gitignore` (only that line, previously `:73`); rewrote `.dockerignore` — every line stripped, all entries and order kept, plus a `# Local config (never bake into the image)` section with `.env` after `mlflow.db`. (d) **After:** `pytest tests/test_repo_hygiene.py -q` → **4 passed**. Nothing lost: `before − after` = **empty**; `after − before` = **`.env` and `# Local config (never bake into the image)`** only. `git check-ignore -v .dockerignore` → **no output** (exit 1); `git ls-files .dockerignore` → `.dockerignore`; `cat -A .dockerignore` → every line ends `$`, no leading/trailing space, blank lines are `$`. Committed only `.gitignore`, `.dockerignore`, `tests/test_repo_hygiene.py`.
- **C2 (this commit) — docs.** `STATE.md`: Docker-deployment row updated with the 2026-10-15 user-run health success; unit-tests row → **99 passed, 2 skipped**; the stale `scripts/train_with_tuning.py` "cannot run here" line corrected; new **§7 "Open findings — clean-clone investigation"**; `.gitignore:81`→`:80` line refs; `Last verified` refreshed. `ROADMAP.md`: R25 user-run evidence + a covered-vs-not criteria list (**stays `in-progress`**); R27 silent-skip note; `Last updated` refreshed. Only these three docs.
- **User-run facts (2026-10-14/15):** `docker compose build` succeeded earlier. On the latest run `docker compose up -d` + `curl http://localhost:8000/v1/health` returned **HTTP 200** `{"status":"healthy", … "loaded": true, "source": "local"}` (uptime ≈596 s). The **first** attempt returned **HTTP 000** from both host ports and was **not reproduced** in two later runs (cause unknown; no proxy env or `~/.curlrc` output was shown). The `mlflow-server` container (`python:3.10`, `pip install mlflow==3.17.1 psycopg2-binary` at every start) was still downloading after ~10 min on the throttled network, so **port 5000 health is unverified**; the API works without it via the local-pickle fallback.
- **Agent-run clean-clone investigation (2026-10-15, `/tmp/clean_clone`):** a fresh `git clone` has no `.dockerignore`, `.env`, `mlflow.db`, or `models/demand_model.pkl`; baseline suite there = **54 passed, 33 skipped, 11 errors** (all `FileNotFoundError: models/demand_model.pkl`); `python scripts/regenerate_data.py` (3.7 s) + `python -m src.training.train` (4.1 s) → loadable model → **96 passed, 2 skipped**; `scripts/train_with_tuning.py` also works (**5:54, exit 0, no network**) so `STATE.md:97`'s "cannot run here — dies at `import mlflow`" was stale (corrected; `mlflow` 3.17.1 imports cleanly here — re-verified this session). `src/data/generator.py` is **unseeded** → two clean clones produced different models (R2 0.4328 vs 0.4708; MAPE 0.3692 vs 0.3543). `scripts/regenerate_data.py` builds **100 products** (36,500 raw / 33,000 feature rows) while the committed artifacts have **50 products** (18,250 / 16,500), so STATE's R2 0.475 / MAPE 0.346 are **not reproducible with the documented command**. ~31 tests **skip silently** when the model/parquet is missing (a CI that does not build data+model first would be vacuously green — noted under R27). The XGBoost "older version" `UserWarning` disappears when the model is retrained on the current stack. All recorded as **open findings** (no decision numbers invented).
- **Full suite (this session, repo):** `pytest tests/ -q` → **99 passed, 2 skipped, 178 warnings in 21.93 s** (0 errors; = the previous 96 passed + 3 D29 tests, same 2 skips).

Left open / blocked:
- **R25 stays `in-progress`:** the health criterion (`curl http://localhost:8000/v1/health` → 200) is now **met** by the user's 2026-10-15 run, but R25's title scopes to "from a clean checkout": the build ran in the working tree, not a fresh clone, and `models/demand_model.pkl` is gitignored so a clean clone has no model to serve. `mlflow-server` :5000 health is unverified.
- **Open findings (no decision number):** unseeded data generator (non-reproducible metrics); `regenerate_data.py` 100 products vs committed 50; ~31 silent skips → vacuous-green CI risk (noted under R27). See `.agents/STATE.md` §7.
- `.gitignore` now has an orphan `# Docker` header (its only entry, `.dockerignore`, was removed per the instruction to remove only that line) — cosmetic, flagged.

Next session should start with:
- Decide R25's clean-checkout scope (must the build context carry a model, or is a documented data+model build step enough?), and pick the next P1 item. See `.agents/ROADMAP.md`.

---

## 2026-10-14 — D28 implemented (mlflow.db untracked) + Dockerfile BuildKit pip cache (R25); R21 done (user-verified fresh venv); C2 stopped+flagged

Done:
- **D28 accepted and implemented.** Commits: `ad64722` (docs: accept D28), `93bf8da` (chore(git): untrack `mlflow.db` + ignore it), `88b1e86` (build(docker): BuildKit pip cache mount — the user's Dockerfile change), plus this docs commit. All on `main`, one commit per step, no amends, no branches. **C2 was STOPPED and flagged** (below) — no commit.
- **C0 `ad64722` — D28 recorded in `.agents/DECISIONS.md`** (Status: `accepted`, date 2026-10-14) with the untrack/ignore + `.dockerignore` 42-43 decision and its rationale (D27 pointed `promote_model.py` at `mlflow.db`; a tracked binary would change on every promote; its content is stale — 2 runs, `demand_forecasting_model` v1/v2, no alias, machine-specific artifact paths under the gitignored `mlruns/`); header accepted-list and `Last updated` refreshed. Only that file.
- **C1 `93bf8da` — `mlflow.db` untracked and gitignored.** Recorded `sha256sum mlflow.db` = `6ae4f9c5ce227187bb0a6212ad7ea0662b8b1b6fa4cfb3bd9a8c442901b61ba8` (188,416 bytes, mtime Jun 6 14:50). New `tests/test_repo_hygiene.py::test_gitignore_ignores_mlflow_db` parses `.gitignore` and asserts an entry exactly `mlflow.db` (no `git` call): **before** 1 failed, **after** 1 passed. `git rm --cached mlflow.db` + `.gitignore:81` `mlflow.db` (next to the `mlruns/` entry, same `# MLflow` section). Verified: `git check-ignore -v mlflow.db` → `.gitignore:81:mlflow.db`; `git ls-files | grep -i mlflow.db` → empty; `ls -l mlflow.db` still 188,416 bytes; `sha256sum` unchanged. No history rewrite; file stays on disk.
- **C2 STOPPED and flagged (no commit).** The C2 test (no non-blank `.dockerignore` line has leading/trailing whitespace) was added and **fails for all 58 non-blank lines**, not just 42-43 — the whole file is indented by one leading space (verified: `awk` lead=1 on all 71 lines; `grep -cP '^ '` = 71). Per the instruction ("if the test fails for lines other than 42-43 after your fix, flag it and stop instead of editing them") only lines 42-43 were de-indented (kept on disk) and the test was reverted so the suite stays green. **Second blocker:** `.dockerignore` is **untracked and gitignored** (`.gitignore:73`; `git ls-files .dockerignore` empty, `git log -- .dockerignore` empty), so C2's "commit only `.dockerignore` and the test file" is impossible without `git add -f` or a `.gitignore` edit — both out of scope.
- **C3 `88b1e86` — the user's Dockerfile change committed** (BuildKit pip cache mount + `--default-timeout=120 --retries 10`), with the dead `# RUN pip install -r requirements.txt` line deleted. Commit body records the user's successful `docker compose build` (1590 s, throttled network, 2026-10-14). `Dockerfile.hf`/`Dockerfile.prod` untouched.
- **C4 (this commit) — docs.** ROADMAP **R21 → `done`**; **R25 stays `in-progress`**; STATE Docker-deployment row, MLflow row, test-count row and `Last verified` refreshed; ROADMAP `Last updated` → `88b1e86`.
- **R21 acceptance verified by the user (2026-10-14, fresh venv `/tmp/v`, `pip install -r requirements.txt`):** `pip check` → **"No broken requirements found." (exit 0)**; freeze confirms `mlflow==3.17.1`, `mlflow-skinny==3.17.1`, `mlflow-tracing==3.17.1`, `opentelemetry-proto==1.27.0`, `protobuf==4.25.9`, `xgboost-cpu==3.4.1`, **no `nvidia-*`**; static criteria also hold (`requests` once at `:27`; `sqlalchemy==2.1.4` at `:30` with `ingest.py` kept; `shap`/`prometheus-client`/linters absent). All four acceptance criteria covered → **R21 done**.
- **R25 user-run facts (2026-10-14):** `docker compose build` **succeeded** (1590 s); `docker compose up -d` started `mlflow-db`, `mlflow-server` (`python:3.10`) and `pricing-api`; `docker compose ps` showed all three **Up for 7 min**; API logs show **4 workers** with `Application startup complete`. Inside the image `models/` has `demand_model.pkl` + `features.json` and **no `mlflow.db`/`mlruns/`** (`.dockerignore` effective); API startup logs an XGBoost "older version" pickle warning. **`curl http://localhost:8000/v1/health` and `:5000/health` from the host returned HTTP 000** — cause under diagnosis (candidates: host proxy env, server bound to `127.0.0.1` in-container, mlflow still installing). R25 not marked done.

Left open / blocked:
- **C2 (`.dockerignore` whitespace) is stopped and needs the owner's decision:** the whole file is indented, and `.dockerignore` is gitignored/untracked. D28's `.dockerignore` half is applied on disk (lines 42-43 only) but not committed.
- **R25 remains `in-progress`:** the health-check reachability (HTTP 000) is unresolved.
- Flagged, not fixed: `.dockerignore` is untracked while `.gitignore:73` lists it; the mlflow compose service still uses `python:3.10` and the obsolete `version` key.

Next session should start with:
- Diagnose R25's HTTP 000 (host proxy / in-container bind / mlflow readiness), and decide how to handle `.dockerignore` (track it, or drop the whole-file hygiene test). See `.agents/ROADMAP.md`.

---

## 2026-10-13 — D27 dependency pin policy implemented (4 code commits + 2 docs commits; R21/R25 stay in-progress)

Done:
- **D27 accepted and implemented.** Commits: `d304e49` (docs: accept D27), `968c21c` (registry tests → sqlite), `5c62460` (promote default → sqlite), `af7383d` (requirements.txt fully pinned + `xgboost-cpu` + `mlflow==3.17.1`), `3a7e3e9` (compose mlflow pin), plus this docs commit. All on `main`, one commit per step, no amends.
- **C0 `d304e49` — D27 recorded in `.agents/DECISIONS.md`** (Status: `accepted`, date 2026-10-13) with the 7-point pin policy; the header accepted-list and `Last updated` line were refreshed. Only that file.
- **C1 `968c21c` — `tests/test_mlflow_registry.py` fixture `temp_registry` now uses a sqlite tracking store** (`sqlite:////<tmp_path>/mlflow.db`) with an explicit `artifact_location` under `tmp_path`, instead of the file store (mlflow 3.x refuses the filesystem backend unless `MLFLOW_ALLOW_FILE_STORE` is set — which we do not set anywhere). **Before:** 2 passed, 2 errors (`MlflowException: The filesystem tracking backend ...`). **After:** 4 passed; `git status --short` clean (no `mlflow.db`/`mlruns` created in the repo).
- **C2 `5c62460` — `scripts/promote_model.py` default tracking URI → sqlite** (`sqlite:////<repo root>/mlflow.db`, the same DB `start.sh`'s `mlflow server --backend-store-uri sqlite:///mlflow.db` uses), docstring updated; `MLFLOW_TRACKING_URI` still overrides. New `tests/test_promote_default_uri.py` (2 tests): **before** fails (`file:///…/mlruns`), **after** passes. **Flag:** `mlflow.db` is tracked (not gitignored); `mlruns/` is gitignored (`.gitignore:80`). `.gitignore` not edited (out of scope).
- **C3 `af7383d` — `requirements.txt` fully pinned** per D27 pts 1–3: every direct dependency `==`-pinned to the `.venv` versions (extras kept, e.g. `uvicorn[standard]`), `xgboost` → `xgboost-cpu==3.4.1` (avoids the Linux-only `nvidia-nccl-cu13` wheel), `mlflow==3.17.1`, `protobuf==4.25.9` (comment rewritten to "the version validated with the pinned stack"). New `tests/test_requirements_pinned.py` (3 tests): **before** 1 failed / 2 passed (21 unpinned lines); **after** 3 passed. Verified without touching `.venv`: `pip install --dry-run --ignore-installed -r requirements.txt --report` → exit 0, **115 packages**; the report asserts `mlflow==3.17.1`, `protobuf==4.25.9`, `xgboost-cpu==3.4.1`, plain `xgboost` absent, and no `nvidia-*` package.
- **C4 `3a7e3e9` — `docker-compose.yml` mlflow service pins `mlflow==3.17.1`.** New test `tests/test_compose_files.py::test_compose_mlflow_service_pin_matches_requirements` (**before:** fails "does not pin mlflow==X"; **after:** passes) asserts the compose pin equals the `requirements.txt` pin. `tests/test_compose_files.py` → 9 passed. `psycopg2-binary`, the `python:3.10` image, and the obsolete `version` key left untouched (flagged only).
- **Suite after all commits:** `pytest tests/` → **95 passed, 2 skipped, 0 errors** (was 87 passed / 2 skipped / 2 errors). The 2 `test_mlflow_registry.py` errors are fixed; the 2 skips are unchanged (`tests/test_optimizer_real.py:166` — reference optimum on a bound).

Left open / blocked:
- **R21 and R25 remain `in-progress`.** Remaining acceptance is network-bound: R21 — the owner's fresh-venv `pip install -r requirements.txt && pip check`; R25 — `docker compose build && docker compose up -d && curl http://localhost:8000/v1/health`. Neither was run here (no installs into `.venv`; no docker build/up).
- Flagged, not fixed: `mlflow.db` is tracked in git; the mlflow compose service still uses `python:3.10` and the obsolete `version` key.

Next session should start with:
- Close R21/R25 on an unthrottled network (their code is done), or pick the next P1 item (R22, R23, R14, R34). See `.agents/ROADMAP.md`.

---

## 2026-10-13 — R24 done (nginx removed); R21 + R25 code done but left in-progress (PyPI throttled) (3 code commits + this docs commit)

Done:
- **R24 — `done`. Code commit `a1eb669`** ("fix(compose): remove nginx service from prod stack + README claims (R24)"). DECISIONS D17 (accepted): removed the whole `nginx:` service from `docker-compose.prod.yml` (incl. the missing `./nginx/nginx.conf` + `./nginx/ssl` bind mounts) and struck the three README nginx claims (What You Get, Containerization, repo tree). `grep -rin nginx README.md docker-compose.prod.yml` → none; `ls nginx` → no such directory. **`docker compose -f docker-compose.prod.yml config` → exit 0** (services: `pricing-api` only). Also repaired a **regression I introduced in R35 (`5a8f887`)**: the `environment:` indentation there made the file invalid YAML (`yaml: line 3: did not find expected key`); confirmed it was valid pre-R35 (`git show 90039b2:docker-compose.prod.yml | docker compose -f - config` → exit 0).
- **R21 — code done, left `in-progress`. Code commit `c444973`** ("fix(deps): correct requirements.txt …"). Deduped `requests`; removed `prometheus-client` + `shap` (0 imports repo-wide) and the linters `flake8`/`black`/`isort`/`mypy` (0 imports, no config, no CI); declared `sqlalchemy>=2.0.0` (kept `ingest.py`, which imports it directly); added the R5 `protobuf==4.25.9` pin. Resolution verified with `pip install --dry-run --report` → **exit 0, 116 packages, no conflict**; protobuf 4.25.9 honoured and the removed deps absent. **The literal acceptance could not be run:** PyPI (`files.pythonhosted.org`) is throttled to **~40–60 KB/s with stalls** here, so a fresh-venv `pip install -r requirements.txt && pip check` cannot complete (the install ran 32 min, installing nothing). Remaining step: the fresh-venv install on an unthrottled network.
- **R25 — code done, left `in-progress`. Code commit `ce4f2e7`** ("build(docker): public python:3.12-slim base + compose build context (R25)"). Per D16: all Dockerfiles → public **`python:3.12-slim`** (`Dockerfile:1`, `Dockerfile.hf:3`, `Dockerfile.prod:2,17`); `docker-compose.yml` `pricing-api` gained a `build:` context. Verified: the public base image pulls; `docker compose config` renders the build context; `docker compose build --progress=plain` reaches `#6 [1/5] FROM docker.io/library/python:3.12-slim@sha256:…` and runs `#9 RUN pip install -r requirements.txt`. **Acceptance NOT met:** step #9 downloads the full wheel set but is throttled to ~40–61 KB/s (in-build: pandas 10.8 MB ≈ 256 s), and `xgboost 3.4.1` alone pulls `nvidia-nccl-cu13` (**291 MB**) — completion would take hours, so the build was stopped after 19 min and `docker compose up -d` + `curl localhost:8000/v1/health` were never reached. Remaining step: build/up/curl on an unthrottled network.
- **Env fix (outside the repo):** Docker Hub pulls failed with `error getting credentials - err: exec: "docker-credential-desktop": executable file not found`. Root cause: `~/.docker/config.json` had `"credsStore": "desktop"` with no helper installed. Backed it up to `~/.docker/config.json.bak` and removed the stale `credsStore` (anonymous pulls need no helper); `docker pull python:3.12-slim` then succeeded.
- **Docs (this commit):** ROADMAP R24 → `done` with evidence; R21/R25 kept `in-progress` with the exact blocking reason; `Last updated` → `ce4f2e7`. STATE.md — §1 Docker-deployment row (public 3.12 base + build context; build unverified) and Nginx row (REMOVED, R24/D17), §5.10 + §5.18 struck as fixed, top protobuf note (R21 pin), `Last verified` → `ce4f2e7`.
- **Commits:** one per task, no amends, no combining — `a1eb669` (R24), `c444973` (R21), `ce4f2e7` (R25), plus this docs commit. All on `main`.

Left open / blocked:
- **R21** and **R25** are code-complete but unverified: their acceptance requires downloading the full dependency set, which this environment throttles to ~40 KB/s (with stalls). Neither is marked done. Re-run on an unthrottled network: (R21) fresh venv `pip install -r requirements.txt && pip check`; (R25) `docker compose build && docker compose up -d && curl http://localhost:8000/v1/health`.
- **Follow-up found (not changed):** `xgboost>=2.0.0` resolves to 3.4.1, which pulls `nvidia-nccl-cu13` (291 MB) on Linux (STATE's tested env is xgboost 3.2.0); `mlflow>=2.9.0` resolves to 3.17.1 in a fresh install, whereas the R5-validated version is 2.12.1. Pinning both would shrink the image and match the tested env — a candidate for an R21/R25 follow-up.
- README still carries stale non-nginx claims (e.g. `README.md:66` "configs/ # Environment-based configuration (dev/prod)", the AWS/CI claims) — owned by R23.

Next session should start with:
- Re-run R21's and R25's acceptance on an unthrottled network (code already committed) and flip them to `done`, or pick the next unblocked P1 item (R22, R23, R14, R34). See `.agents/ROADMAP.md`.

---

## 2026-10-13 — Docs-only: accept D16/D17; R24/R25 back to `todo` (1 docs commit)

Done:
- **DECISIONS D16 and D17 → `accepted` (owner-approved 2026-10-13).** D16 ("Use a public base image for Docker builds", incl. the Python 3.10→3.12 bump) and D17 ("Remove the nginx reverse proxy from the demo") move from `proposed` to `accepted`; each date line records "(accepted 2026-10-13)". The header accepted-list and the file's `Last updated` line were refreshed.
- **D16 consequences extended with the clean-checkout build dependency.** R25's acceptance is a build/`pip check` from a clean checkout, but `requirements.txt` does not carry the R5 fix (`protobuf==4.25.9`, alongside `setuptools<81`) that makes `import mlflow` work, so a fresh image fails `pip check`/`import mlflow` as it did pre-R5. Recorded that R25 must pull that minimal `protobuf` pin into `requirements.txt`, or R21 (`requirements.txt` correctness) must land first.
- **ROADMAP R24 and R25: `blocked` → `todo`** (the blockers were the proposed decisions, now accepted); the "Blocked by" lines are removed. R25 gained a `Note` spelling out the `protobuf`-pin dependency (and `requirements.txt` was added to its Files touched). ROADMAP `Last updated` refreshed.
- **STATE.md:** corrected the now-stale clause in the `Last verified` line (it said "R24/R25 blocked on proposed D17/D16"; now "D16/D17 accepted → ROADMAP R24/R25 back to `todo`"). No other STATE claim needed changing: it does not assert D16/D17 status, and its R24/R25-relevant rows (nginx FAKE-OR-DEAD, Docker caveats) stay accurate until R24/R25 are implemented.
- **No code touched** — docs only (`.agents/DECISIONS.md`, `.agents/ROADMAP.md`, `.agents/STATE.md`, this LOG entry). All on `main`.

Left open / blocked:
- R24 and R25 are now actionable `todo` P1 items: R24 — add a real nginx config **or** remove the service + README claim; R25 — public base image + Python 3.12 bump **and** pull the R5 `protobuf` pin into `requirements.txt` (or do R21 first).
- Nothing else changed by this docs commit.

Next session should start with:
- R24 and/or R25 now that D16/D17 are accepted (R25 depends on the `protobuf` pin in `requirements.txt` — add it as part of R25, or do R21 first), or the next unblocked P1 item (R21, R22, R14, R34). See `.agents/ROADMAP.md`.

---

## 2026-10-13 — R35 config collapse + R26 bounded `start.sh` loops done; R24/R25 blocked on proposed D17/D16 (2 code commits + this docs commit)

Done:
- **R35 implemented and verified. Code commit `5a8f887`** ("feat(config): collapse to a single config.yaml; drop APP_ENV selection (R35)"), implementing DECISIONS D26.
  - Deleted `configs/config.dev.yaml` + `configs/config.prod.yaml` (key-identical duplicates); `configs/` now holds only `config.yaml`. `EnvConfig._load_config` always loads `configs/config.yaml` — the `APP_ENV`→file `config_map` is gone. Removed the now-broken dead env concept (`self.env`, `is_production`, `is_development`, `reload_config`, all unreachable per STATE §3) and the `config.env` reference in `src/api/server.py`'s startup log. Removed `APP_ENV` from `.env.example`, `.env` (gitignored; cleaned in the working tree), and `docker-compose.prod.yml`. Fixed the `README.md:99` snippet that copied the now-deleted `config.dev.yaml`.
  - New `tests/test_config.py::test_exactly_one_config_file` asserts `sorted(configs/*.yaml) == ["config.yaml"]`. **Pre-fix failure reproduced (rule 18):** with the two files restored from `HEAD` it fails (`expected exactly configs/config.yaml, found ['config.dev.yaml', 'config.prod.yaml', 'config.yaml']`); passes after deletion. `pytest tests/test_config.py` → **5 passed** (was 4); `tests/test_env.py` → **2 passed** (derived read set no longer contains `APP_ENV`).
  - **Behavior provably unchanged:** `GET /v1/health` → **200** (`checks.model = {status:ok, loaded:true, source:local}`); `POST /v1/optimize-price` (`grid_search`, 70–110) → **200**, `optimal_price=77.06`, `expected_revenue=6152.544` — identical to the pre-change R12 value (the three files were key-identical). Suite → **79 passed, 2 skipped** (was 78+2).
- **R26 implemented and verified. Code commit `7cdbf56`** ("fix(ops): bound the start.sh health-wait loops and exit non-zero (R26)").
  - Both loops now call `wait_for_health "<name>" "<url>"`: at most `HEALTH_MAX_ATTEMPTS` (default 60) attempts with `HEALTH_RETRY_INTERVAL` (default 2s) between them, then a clear stderr message and `return 1`, followed by `|| exit 1` (CONVENTIONS rule 31). Health URLs/attempts/interval are env-overridable so the loops can be pointed at a non-2xx endpoint without real services.
  - **Pre-fix failure reproduced (rule 18):** against `HEAD`'s `start.sh` with a stub `curl` that never returns 2xx, `timeout 5 bash start_old.sh` → **still looping after 5s, `exit=124`** (the unbounded bug); the fixed script with the same stub → clear error + **`exit=1`**.
  - New `tests/test_start_sh.py` (2 tests) runs the real script against a stub PATH (no-op `mlflow`/`uvicorn`/`streamlit` + a marker-driven `curl`), covering both loops; each bounds the subprocess at 30s so a hang fails the test. `pytest tests/test_start_sh.py -v` → **2 passed**. Suite → **81 passed, 2 skipped** (was 79+2).
- **R24 NOT done — stopped on purpose.** Checked DECISIONS **D17** ("Remove the nginx reverse proxy") first: it is still **`proposed`**, so neither R24 branch (add a real `nginx/nginx.conf`, or remove the service + README claim) is licensed. Per instruction, stopped on R24 only and reported; no code changed. ROADMAP R24 → `blocked`.
- **R25 NOT done — skipped on purpose.** Checked DECISIONS **D16** ("Use a public base image for Docker builds", incl. the Python 3.10→3.12 bump): still **`proposed`**, so the switch away from the `docker.arvancloud.ir` mirror is not licensed. Per instruction, skipped R25 and reported; no code changed. ROADMAP R25 → `blocked`. (Docker *is* available here — Docker 29.2.0 / Compose v5.0.2 — but that is moot: the gate is the proposed decision, not tooling.)
- **Docs updated once, at the end:** ROADMAP R35/R26 → `done` with evidence, R24/R25 → `blocked`, `Last updated` → `7cdbf56`; STATE.md — §1 unit-tests row → 81 passed + R35/R26 test notes, §1 HF-Spaces row + §5.9 → bounded loops fixed (R26), §4 rewritten for the single `config.yaml` and the 16-variable env read set (`APP_ENV` removed), `Last verified` → `7cdbf56`; this LOG entry.
- **Commits:** one code commit per task, no amends, no combining — `5a8f887` (R35), `7cdbf56` (R26), plus this docs commit. All on `main`; no task branch.

Left open / blocked:
- **R24** blocked on D17; **R25** blocked on D16. Both decisions remain `proposed` and must be accepted/overridden by the owner before either item can be implemented.
- `docker-compose.prod.yml` still carries `MONITORING_ENABLED=true` (unread since R19) and still mounts the missing `./nginx/...` (R24); it cannot `up` until R24 is unblocked.
- No model artifact was retrained this session, so R7's test-time references remain valid (no re-run needed).
- Remaining `todo` P1: R14, R21, R22, R23, R34 (and R24/R25 once unblocked).

Next session should start with:
- The next unblocked P1 item (e.g. R21 `requirements.txt` correctness, R22 dead-code disposition, R14 smoke tests, R34 `product_id`). See `.agents/ROADMAP.md`. Or have the owner accept/override D16/D17 to unblock R25/R24.

---

## 2026-10-13 — Docs-only: record config decision D26 and add ROADMAP R35 (1 docs commit)

Done:
- **DECISIONS D26** ("Single config file; drop APP_ENV-driven YAML selection") added with status `accepted` (owner-approved 2026-10-13). Records why `configs/config{,.dev,.prod}.yaml` are a duplicate: after R18 the three files are key-identical (parsed YAML compares equal; only comments differ), and the `APP_ENV`→file selection in `EnvConfig._load_config` is unused by any YAML consumer (`EnvConfig` is instantiated only at `src/api/server.py:25`, which reads only env vars; the pricing engine is built from a hardcoded `configs/config.yaml` in `src/api/router.py:19-24`, as is every training/script entry point). Decision: keep one `config.yaml`, delete dev/prod, always load `config.yaml`, drop the readerless `APP_ENV`; env-specific values stay env vars. Rejected the "keep three files, add env-specific keys" option because the remaining keys are model/training/feature params that must not diverge per env (one model artifact + one feature contract). Consistent with DECISIONS D11 and CONVENTIONS rules 8/27. Header accepted-list and the file's `Last updated` line refreshed.
- **ROADMAP R35** ("Collapse to a single `config.yaml`") added as a P1 item, status `todo`, depends on R18/R19 (both `done`). Scope: delete `configs/config.dev.yaml`/`config.prod.yaml`; `EnvConfig` always loads `configs/config.yaml`; remove `APP_ENV` from `.env.example`/`.env`/`docker-compose.prod.yml`; add a test asserting exactly one `configs/*.yaml`; keep `tests/test_env.py`/`tests/test_config.py` green; `/v1/health` and `/v1/optimize-price` still 200. Priority counts updated (P1 19→20, total 34→35) and the execution-order section now lists R35 in step 4. This supersedes the prior LOG entry's "Left open" note that the dev/prod duplication was "a candidate for R22/R23" — it is now tracked as R35, so R22/R23 no longer need to re-discover it.
- Docs-only: no code touched, R35 not implemented. `tests/test_config.py` was left unchanged (it globs `configs/*.yaml`, so it keeps working with one file; R35 adds the exactly-one assertion).

Left open / blocked:
- `README.md:326-341` still shows a stale config example (R23 owns it).
- R14, R21–R26, R34, and R35 remain `todo`.

Next session should start with:
- The next P1 item (e.g. R14 smoke tests, R21 `requirements.txt` correctness, R35 config collapse). See `.agents/ROADMAP.md`.

---

## 2026-10-08 — R18, R19, R20 done: config/env hygiene enforced by tests; real log rotation (3 code commits)

Done:
- **R18 implemented and verified. Code commit `97a4f8c`** ("chore(config): delete unread YAML keys + api/monitoring/logging blocks (R18)"), touching `configs/config{,.dev,.prod}.yaml` and `tests/test_config.py` (new).
  - Deleted every key with no reader in `src/`/`scripts/`: the whole `api:` (10 keys) and `logging:` (4 keys) blocks in dev/prod (runtime toggles come from env vars; DECISIONS D11), the orphaned `monitoring:` block (its only consumer, `model_monitor.py`, was deleted in R15), `data.raw_path`/`processed_path`, `model.demand_model`, `pricing.{price_min,price_max}_multiplier`/`price_steps`/`default_method`, `training.cv_folds`/`run_hyperparameter_tuning`, and `features.raw_filename`/`feature_filename` (read only by the dead `feature_pipeline.py`, which uses `.get(..., default)` so nothing breaks).
  - Kept the read set: `data.feature_path`; the nine `model.*` params; `pricing.{model_path,feature_columns_path,price_min,price_max}`; `training.{test_size,model_dir,report_dir,run_cv,tuning_trials}`; `features.{lag_days,rolling_windows,min_history_days}`.
  - New `tests/test_config.py` (4 tests) enumerates every dotted leaf key across `configs/*.yaml` and fails on any leaf name not appearing as a string literal in `src/` or `scripts/`, with an explicit (currently empty) `ALLOWLIST`; it also asserts the `api`/`monitoring`/`logging` blocks are gone. **Pre-fix failure reproduced (rule 18):** against `HEAD` the test fails **2/4** (63 unread keys listed, incl. `config.dev.yaml:api.cors_enabled`, `…:monitoring.enabled`, `…:logging.rotation`, `config.yaml:pricing.default_method`; `config.dev.yaml still has an unread monitoring: block`). After → **4 passed**.
  - **No behavior change:** `GET /v1/health` → 200 `{status:ok, loaded:true, source:local}`; `POST /v1/optimize-price` (`grid_search`, 70–110) → 200 `optimal_price=77.06`.
- **R19 implemented and verified. Code commit `3bb3aef`** ("chore(env): add .env.example for the read set; drop decorative vars (R19)"), touching `.env.example` (new) and `tests/test_env.py` (new). `.env` is gitignored (`.gitignore:65`) and was cleaned in the working tree.
  - Read set (14, scanned from `src/`): `APP_ENV`, `API_HOST`, `API_PORT`, `API_WORKERS`, `API_RELOAD`, `CORS_ENABLED`, `CORS_ORIGINS`, `RATE_LIMIT_ENABLED`, `RATE_LIMIT_REQUESTS`, `REQUEST_TIMEOUT`, `LOG_LEVEL`, `LOG_FORMAT`, `LOG_DIR`, `MLFLOW_TRACKING_URI`. (`CORS_ENABLED` was read by `server.py:48` but missing from STATE §4.)
  - Removed ~23 decorative vars (`APP_NAME`, `APP_VERSION`, `DEBUG`, `CORS_ALLOW_CREDENTIALS`, `RATE_LIMIT_WINDOW`, `DATABASE_URL`, `DATABASE_BACKUP_*`, `MODEL_PATH`, `FEATURES_PATH`, `MODEL_CACHE_ENABLED`, `MODEL_RELOAD_INTERVAL`, `LOG_RETENTION_DAYS`, `MONITORING_ENABLED`, `METRICS_ENABLED`, `HEALTH_CHECK_INTERVAL`, `PREDICTION_LOG_*`, `MODEL_INFERENCE_TIMEOUT`, `CACHE_TTL`, `ALERT_ERROR_THRESHOLD`, `MLFLOW_EXPERIMENT_NAME`, `STREAMLIT_*`). The shell-script vars all have `${VAR:-default}` fallbacks.
  - New `tests/test_env.py` (2 tests) scans `src/` for `os.getenv`/`get_bool`/`get_int`/`get_env`/`os.environ`, asserts `.env.example` == read set and `.env` ⊆ read set (skips if `.env` is absent). **Pre-fix failure reproduced:** both fail (`.env.example is missing`; 13 unread `.env` vars listed). After → **2 passed**.
- **R20 implemented and verified. Code commit `c58b6ab`** ("feat(logging): real log rotation configured from env (R20)"), touching `src/utils/logger.py`, `src/api/server.py`, `.env.example`, `tests/test_log_rotation.py` (new); `.env` updated in the working tree.
  - **Decision: implement rotation** (the first R20 branch). Rationale: it is a small stdlib change; the README already advertises "log rotation" (`README.md:41`); and the roadmap's guiding rule is to make a claimed capability true before advertising it. So the README claim is **kept** (now true), not struck.
  - `setup_logging(..., rotation="none", max_bytes=10 MiB, backup_count=5)` selects `RotatingFileHandler(maxBytes, backupCount)` (`LOG_ROTATION=size`), `TimedRotatingFileHandler(when="midnight")` (`daily`), or a plain `FileHandler` (`none`). New `setup_logging_from_env()` reads `LOG_LEVEL`/`LOG_FORMAT`/`LOG_DIR`/`LOG_ROTATION`/`LOG_MAX_BYTES`/`LOG_BACKUP_COUNT`; `server.py:31` calls it. `.env.example`/`.env` gained `LOG_ROTATION`/`LOG_MAX_BYTES`/`LOG_BACKUP_COUNT` (read set 14 → 17).
  - `tests/test_log_rotation.py` (4 tests): writes past `LOG_MAX_BYTES` and asserts a rotated `app.log.1` appears (direct **and** via the env path), plus handler-class checks for `daily`/`none`. **Pre-fix failure reproduced (rule 18):** against `HEAD`'s logger the module **errors at collection** (`ImportError: cannot import name 'setup_logging_from_env'`) and a direct call raises `TypeError: setup_logging() got an unexpected keyword argument 'rotation'` (no `Rotating*` handler in the module). After → **4 passed**.
- **Full suite (after all three):** `pytest tests/` → **78 passed, 2 skipped**, 0 collection errors (80 collected). Baseline before this session was 68 passed, 2 skipped (70 collected); +4 R18, +2 R19, +4 R20.
- **Docs updated once, after all three:** ROADMAP **R18/R19/R20 → done** with evidence and `Last updated` → `c58b6ab`; STATE.md — §1 (log-rotation row FAKE-OR-DEAD → CONFIRMED; unit-tests row → 78 passed + the R18/R19/R20 tests), §4 rewritten from "defined but never read" to the enforced read set, `Last verified` → `c58b6ab`; CONVENTIONS rules 5 and 6 → `enforced`; this LOG entry.
- **Commits:** three separate code commits, no amends, no combining — `97a4f8c` (R18), `3bb3aef` (R19), `c58b6ab` (R20), plus this docs commit. All on `main` as requested; no task branch.

Left open / blocked:
- `config.dev.yaml` and `config.prod.yaml` are now key-identical to `config.yaml` (their only prior differences were the deleted `api:`/`logging:` blocks). They are still loaded by `EnvConfig` when `APP_ENV` matches, so they are not orphaned, but the duplication is worth revisiting (CONVENTIONS rule 27) — a candidate for R22/R23.
- `README.md:326-341` still shows a stale config example (`default_method: bayesian`, `run_hyperparameter_tuning: false`) whose keys R18 deleted from the YAML; R23 (README truth pass) owns fixing it.
- R14, R21–R26, and R34 remain `todo`.
- No model artifact was retrained this session, so R7's test-time references remain valid (no re-run needed).

Next session should start with:
- The next P1 item (e.g. R14 smoke tests, R21 `requirements.txt` correctness, R34 `product_id`). See `.agents/ROADMAP.md`.

---

## 2026-10-08 — Docs-only follow-up: mark DECISIONS D13 `accepted` (implemented via R15) (1 docs commit)

Done:
- **DECISIONS D13** ("Drop drift detection and performance-monitoring claims for the demo") status `proposed` → `accepted`, with the note **"Accepted 2026-10-07 retroactively, implemented via R15"** recorded in its Consequences (same style as D15's acceptance note). D13 was effectively decided and implemented by R15's delete branch this session; the header accepted-list and the file's `Last updated` line were refreshed accordingly. (The note was first recorded as "2026-09-29" at the owner's initial wording; corrected to the real R15 implementation date, 2026-10-07, after checking the system/git date.)
- No other decision was touched. The prior entry's "Left open" note that D13 remained `proposed` is superseded by this entry.

Left open / blocked:
- `configs/config{,.dev,.prod}.yaml` still contain the dead `monitoring:` block (R18 owns it).
- R14, R18–R26, and R34 remain `todo`.

Next session should start with:
- The next P1 item (e.g. R14 smoke tests, R18 config hygiene, R34 `product_id`). See `.agents/ROADMAP.md`.

---

## 2026-10-07 — R16, R15, R17 done: no error-text leakage; drift detection deleted; atexit flush replaces `__del__` (3 code commits)

Done:
- **R16 implemented and verified. Code commit `85f5944`** ("fix(api): return generic 500 + request_id instead of leaking error text (R16)"), touching `src/api/router.py` and `tests/test_api.py`.
  - `router.py`'s `except Exception` no longer does `raise HTTPException(500, detail=str(e))`. It logs the real exception server-side and returns `JSONResponse(status_code=500, content={"message": "An internal error occurred while processing the request.", "request_id": request_id})` — a generic message plus `request_id` only (CONVENTIONS rule 11 / DECISIONS D21). `HTTPException` is still imported for the health endpoints.
  - **Pre-fix failure reproduced (rule 18):** with `router.py` restored from `HEAD`, the new test **FAILS** — the 500 body was `{'detail': '"[\'price_advantage\', \'log_comp_price\'] not in index"'}` (raw `KeyError` text leaked). After the fix it passes.
  - **Test:** `tests/test_api.py::test_optimizer_failure_returns_generic_error` monkeypatches `engine.get_optimal_price` to raise `KeyError("['price_advantage', 'log_comp_price'] not in index")` and asserts HTTP **500**, a non-empty `request_id` + `message`, and that the response text contains none of `KeyError` / `not in index` / `Traceback`. `pytest tests/test_api.py` → **10 passed** (was 9).
- **R15 implemented and verified. Code commit `2746fa8`** ("chore(monitoring): delete dead drift detection and strike README drift claims (R15)"), touching `src/monitoring/model_monitor.py` (deleted), `tests/test_data_drift.py` (deleted), `README.md`.
  - **Decision: option (b) — delete.** Rationale (effort/value): a real caller would need a stable reference distribution (the training features parquet is gitignored/regenerated, not reliably present), a real traffic-feature source, and a new endpoint/script plus shift-vs-stable tests — yet `ModelMonitor.calculate_drift` was only a normalized mean/std heuristic with **no** statistical test/p-value, so wiring it and calling it "drift detection" would still risk rule 24. For a synthetic-data demo with no actuals feedback loop there is no value to wire; deletion is the honest, low-risk path and matches D13's default. `src/api/router.py` was therefore **not** touched.
  - **Evidence:** `grep -rn "model_monitor\|ModelMonitor" --include=*.py .` → no matches; `grep -rni "drift" README.md` → no matches (pre-fix it matched the "Complete Monitoring" bullet, the "Model Monitoring" bullet, the config `monitoring:` example, and the `# Check data drift` troubleshooting line). The dead README config example's `monitoring:` block was removed too. `pytest tests/` → **65 passed, 2 skipped**.
  - **Left to R18:** `configs/config{,.dev,.prod}.yaml` still carry the unread `monitoring:` block (`drift_threshold` etc.); STATE.md §4 already flags it as never-read and R18 owns deleting/wiring it.
- **R17 implemented and verified. Code commit `42c4d68`** ("fix(monitoring): flush prediction logs via atexit instead of __del__ (R17)"), touching `src/monitoring/prediction_logger.py` and `tests/test_prediction_logger.py` (new).
  - Removed `PredictionLogger.__del__` (which called `flush()` — I/O — during teardown) and added `atexit.register(self.flush)` in `__init__`. atexit callbacks run before module teardown / before `sys.meta_path` is cleared, so the final flush is safe (CONVENTIONS rule 13).
  - **Pre-fix failure reproduced (rule 18):** with `prediction_logger.py` restored from `HEAD`, all three new tests **FAIL** (`__del__` present; no atexit registration; nothing flushed at exit). After the fix `pytest tests/test_prediction_logger.py -v` → **3 passed** (`test_no_io_in_del`, `test_atexit_flushes_buffered_entries`, `test_interpreter_exit_has_no_shutdown_importerror`).
  - **Crash gone:** the pre-session `pytest tests/` printed `Exception ignored in: <function PredictionLogger.__del__ ...> ImportError: sys.meta_path is None, Python is likely shutting down` after the summary; after the fix a full `pytest tests/` run prints no such traceback.
- **Full suite (after all three):** `pytest tests/` → **68 passed, 2 skipped**, 0 collection errors (70 collected). Baseline before this session was 65 passed, 2 skipped (67 collected); +1 R16, −1 R15 (`test_data_drift`), +3 R17.
- **Docs updated once, after all three:** ROADMAP **R15/R16/R17 → done** with evidence and the `Last updated` line → `42c4d68`; STATE.md — §1 (drift + performance-monitoring rows → deleted; error-handling row → CONFIRMED; unit-tests row → 68 passed + R15/R16/R17 notes), §3 (removed the `ModelMonitor` dead-code row), §4 (monitoring-block note), §5.11/§5.13/§5.16 marked fixed, `Last verified` → `42c4d68`; CONVENTIONS rules 11/13/15 → `enforced`; this LOG entry.
- **Commits:** three separate code commits, no amends, no combining — `85f5944` (R16), `2746fa8` (R15), `42c4d68` (R17), plus this docs commit. All on `main` as requested; no task branch.

Left open / blocked:
- `configs/config{,.dev,.prod}.yaml` still contain the now-doubly-dead `monitoring:` block (`drift_threshold`, etc.); R18 (config hygiene) owns deleting/wiring it.
- DECISIONS **D13** ("drop drift detection claims") remains `proposed` — R15 implemented its delete branch at the owner's R15 instruction, but D13 itself was not formally marked `accepted` this session.
- R14 (`tests/smoke_tests.py` collects 0), R18–R26, and R34 remain `todo`.
- No model artifact was retrained this session, so R7's test-time references remain valid (no re-run needed).

Next session should start with:
- The next P1 item (e.g. R14 smoke tests, R18 config hygiene, R34 `product_id`). See `.agents/ROADMAP.md`.

---

## 2026-09-30 — Docs-only: correct "committed model" phrasing; add R34 for the unused `product_id` field (1 docs commit)

Done:
- **Corrected the "committed `models/demand_model.pkl`" phrasing** in the living docs to match reality: the pickle (and `reports/*`, `data/features/*.parquet`) are **gitignored** (`.gitignore:45,51,60-61`) and regenerated in the working tree — only `models/features.json` is tracked.
  - `.agents/STATE.md`: fixed the "How this was produced" line and the R7 row; added an explicit **Artifact tracking** paragraph so any remaining loose "committed" wording is unambiguous.
  - `.agents/ROADMAP.md`: every occurrence in R1/R2/R4/R5/R6/R7/R9/R13/R12 evidence + the sequencing note now reads "working-tree (gitignored) `models/demand_model.pkl`" (or "working-tree artifact/model"); the historical evidence numbers and commit hashes were left unchanged.
  - `.agents/CONVENTIONS.md`: rule 14 now says "working-tree `models/demand_model.pkl` (gitignored, regenerated) + the tracked `models/features.json`".
- **Added ROADMAP R34** (P1, `todo`): "`PricingRequest.product_id` is accepted but unused (latent contract mismatch)". R12/D5 removed `product_id` from the model features, but `src/api/schemas.py:9` still declares it required and the serving path silently drops it — harmless today, but a client sending it would reasonably expect it to affect the price. R34 requires either removing the field (updating UI/tests/README in the same PR) or documenting it as non-model and asserting it is absent from the served feature columns. Updated the ROADMAP priority counts (P1 → 19 items, total → 34), the suggested execution order, and the `Last updated` line.
- **Deliberately left untouched** (per the no-edit rules): past `.agents/LOG.md` entries (LOG header: "Do not edit past entries"), the owner-supplied `.agents/archive/audit_Dynamic-Pricing-Engine.md` (CONVENTIONS rule 33), and the historical task file `.agents/tasks/R1-real-optimizer.md` — their "committed model" wording is a record of what was written at the time; the correction is carried by this entry and the living docs above.
- **No code changed.** Docs-only commit on `main`.

Left open / blocked:
- R34 is new and `todo`; it depends on R12 (done).
- The stale "31 committed columns" number in R4's evidence block (ROADMAP) is left as-is — it is a historical record of R4 (features.json is now 30 columns after R12).

Next session should start with:
- The next P1 item (e.g. R14 smoke tests, R15 drift, R16 error leakage, R34 `product_id`). See `.agents/ROADMAP.md`.

---

## 2026-09-30 — D5/D6 accepted; R12 done: chronological split + `product_id` dropped + retrain; R7 re-verified (2 commits)

Done:
- **D5 and D6 accepted** (`.agents/DECISIONS.md`), docs-only commit **`b3ecf90`** ("docs(agents): accept D5 (drop product_id) and D6 (chronological split)"). Both were `proposed`; the header now lists D1, D2, D5, D6, D15 as `accepted`. No code in this commit.
- **R12 implemented and verified. Code/retrain commit `47162d3`** ("feat(training): chronological split + drop product_id model feature; retrain (R12)").
  - **Chronological split (D6):** `src/training/dataset.py::DatasetBuilder.split(X, y, dates)` sorts rows by `date` (stable `mergesort`) and holds out the most recent `test_size` fraction; whole calendar days are kept together (if the cut lands mid-day the boundary is pushed to that day's end) so no date appears in both sets. `test_size` is read from `configs/config.yaml` (was hardcoded); the obsolete `training.random_state` key was removed from `config.yaml`/`config.dev.yaml`/`config.prod.yaml`. `src/training/pipeline.py` and `scripts/train_with_tuning.py` pass `df["date"]`; the pipeline now logs the train/validation date ranges.
  - **`product_id` dropped (D5):** `src/features/feature_builder.py` still groups the lag/rolling features by `product_id` but no longer emits it (removed from `feature_cols`; the sort moved before column selection). `models/features.json` regenerated with **30 columns (was 31)**.
  - **Evidence — chronological split:** train **13,200 rows 2023-02-05 … 2023-10-26**, validation **3,300 rows 2023-10-27 … 2023-12-31**; `max(train.date) < min(val.date)` → **True**; overlap dates `[]`; `grep -n "shuffle=True\|train_test_split" src/training/dataset.py` → **no matches**.
  - **Evidence — `product_id` / leakage:** `models/features.json` contains no `product_id`; `DatasetBuilder.build` excludes it; retrained model `n_features_in_ == 30`; feature list contains neither `y_units_sold` nor `units_sold`; lag/roll features use `.shift(1)` (no `.shift(0)`).
  - **Regenerated metrics (no carried-over numbers):** `reports/training_metrics.json` → **R2 = 0.47498, MAPE = 0.34581**, MAE = 21.44, RMSE = 30.05, Directional_Accuracy = 0.7587, Train_R2 = 0.88029. Prior artifact: R2 = 0.4682, MAPE = 0.4015, Train_R2 = 0.6332.
  - **New tests:** `tests/test_training_data.py` (5 tests) → **5 passed**: chronological split, no shuffle, `product_id` not a feature, no target leakage, R2+MAPE present.
  - **Retrain method:** features were rebuilt from the **existing** `data/raw/ecommerce_sales.csv` (the raw data was *not* regenerated — the synthetic generator is unseeded, so regenerating would change the dataset and confound the R12 change). Only the feature/split code changed.
- **R7 re-run after the retrain (required by R7's note).** `pytest tests/test_optimizer_real.py -q` → **18 passed, 2 skipped** (references recomputed at test time from the new artifact, per rule 34). Fresh ratios vs a test-time 901-point reference: served grid `(30,80)` **1.00006**, `(70,110)` **0.99673**, `(10,200)` **1.00000**, `(100,120)` **1.00000**, `(30,120)` **1.00078** — all ≥ 0.99; the Bayesian optimizer is ≥ 0.99 on all five with `optimization_success=True`. Served API `grid_search` `(70,110)` → `optimal_price=77.06, expected_demand=79.841, expected_revenue=6152.544`. The 2 skips remain the `(10,200)`/`(100,120)` bound-hugging cases.
- **Full suite:** `pytest tests/` → **65 passed, 2 skipped**, 0 collection errors (was 60+2; +5 R12 tests). Only post-summary noise is the pre-existing `PredictionLogger.__del__` shutdown `ImportError` (STATE §5.11 / R17).
- **Docs updated after the code:** ROADMAP **R12 → done** with the evidence above and the `Last updated` line → `47162d3`; STATE.md — §1 model/`R²`/time-series-validation/grid/constraints/feature-engineering/unit-tests rows, §2 training path + verified note, §5.17 marked fixed, `Last verified` → `47162d3`; this LOG entry.

Left open / blocked:
- **Not committed (repo convention):** `models/demand_model.pkl`, `reports/*.json|csv`, and `data/features/*.parquet` are gitignored (`.gitignore:45,51,60-61`) — they are regenerated in the working tree, not tracked. Only the tracked model contract `models/features.json` (now 30 cols) is committed. This matches how R1–R11 treated the artifacts; STATE.md's phrase "committed `models/demand_model.pkl`" is loose.
- R7 is now valid against the R12 artifact, but must be **re-run again after any later item that rewrites `models/demand_model.pkl`**.
- R9's and R6's ratio tests are retrain-safe (references computed at test time) and passed on the new model; their recorded *numbers* in ROADMAP/STATE were updated.
- Remaining P1 items include R14–R26 (R12 was the last of the R4/R5/R11/R12/R13 cluster).

Next session should start with:
- The next P1 item (e.g. R14 smoke tests, R15 drift, R16 error leakage). See `.agents/ROADMAP.md`.

---

## 2026-09-29 — R10, R11, R9 done: Streamlit↔API contract, fake Advanced-tab response removed, API contract + grid-path test (3 code commits)

Done:
- **R10 implemented and verified. Code commit `bfa06eb`** ("fix(ui): align Streamlit response contract with the API (R10)"), touching `app.py` and `tests/test_streamlit_contract.py` (new).
  - `app.py` now reads `expected_demand` (Quick-tab metrics, details table, batch results) instead of `predicted_demand`, which the API never returned — that mismatch was the `KeyError` swallowed by the broad `except` (STATE.md §5.7).
  - The method selectbox offers `["grid_search", "grid"]` only (the rejected legacy `"bayesian"` is gone); the Advanced/About copy no longer advertises Bayesian optimization (D2/rule 24).
  - **Rendering evidence (live API on `:8000`):** ran `app.py` via `streamlit.testing.v1.AppTest`, clicked "🚀 Optimize Price" → no `at.exception`, no `st.error`; metrics rendered `💰 Optimal Price $77.36`, `📈 Profit Margin 22.4%`, `📊 Predicted Demand 77 units`, `💵 Est. Revenue $5,930`.
  - **Contract test:** `tests/test_streamlit_contract.py` parses `app.py` as source (importing it would execute the Streamlit script) and asserts every `result[...]` key is a `PricingResponse` field (and that `expected_demand` is read, `predicted_demand` is not), and that the selectbox options ⊆ the accepted `Literal` and exclude `"bayesian"`. `pytest tests/test_streamlit_contract.py` → **4 passed** at this commit.
- **R11 implemented and verified. Code commit `b7abaff`** ("fix(ui): remove fabricated Advanced-tab response, show live schema (R11)"), touching `app.py` and `tests/test_streamlit_contract.py`.
  - Removed the hardcoded `example_response` (`confidence_interval`, `optimization_metadata`, `time_ms`) — a fabricated payload presented as a response (rule 25). `grep -n "confidence_interval\|optimization_metadata" app.py` → **no matches**.
  - The Advanced tab now fetches the running API's `/openapi.json` and renders the live `PricingResponse` schema; when the API is unreachable it shows an informational message instead of invented data.
  - **Evidence:** `AppTest` renders the live schema (properties `optimal_price`, `expected_demand`, `expected_revenue`, `optimization_method`, `profit_margin`, `total_profit`, …; no fabricated keys). New `test_app_contains_no_fabricated_response_keys` asserts the source contains none of `confidence_interval` / `optimization_metadata` / `example_response`. `pytest tests/test_streamlit_contract.py` → **5 passed**.
- **R9 implemented and verified. Code commit `bc2f674`** ("test(api): contract + grid-path integration test through HTTP (R9)"), touching `tests/test_api.py`.
  - `test_grid_path_response_contract`: `grid_search` and `grid` → **HTTP 200** with `optimal_price`, `expected_demand`, `expected_revenue`, `optimization_method`; the method is echoed; `70 ≤ optimal_price ≤ 110`; the body validates against `PricingResponse`; `"bayesian"` → **HTTP 422**.
  - `test_grid_path_reaches_reference_optimum`: served `grid_search` `expected_revenue` **5950.3983** vs a test-time **901-point** reference max **5948.3471** (ratio **1.00034 ≥ 0.99**). The reference is computed from the *served* model (`engine.model`) and the requested bounds through an independent oracle feature builder — deliberately not the shared `build_serving_features` — so it is not circular and hardcodes no model-derived number (rule 34).
  - **Suite:** `pytest tests/test_api.py` → **9 passed**; full `pytest tests/` → **60 passed, 2 skipped**, 0 collection errors (was 53+2 after R6). Only post-summary noise is the pre-existing `PredictionLogger.__del__` shutdown `ImportError` (STATE §5.11 / R17).
- **Docs updated once, after all three:** ROADMAP **R9/R10/R11 → done** with the evidence above and the `Last updated` line → `bc2f674`; STATE.md §1 Streamlit row → CONFIRMED (fixed R10/R11) and unit-tests row → 60 passed, §2 frontend path rewritten, §5.7 marked fixed, `Last verified` → `bc2f674`; CONVENTIONS rules 25 and 29 → `enforced` (both now backed by `tests/test_streamlit_contract.py`); this LOG entry.
- **Commits:** three separate code commits, no amends, no combining: `bfa06eb` (R10), `b7abaff` (R11), `bc2f674` (R9), plus this docs commit. All on `main` as requested.

Left open / blocked:
- The full suite is green (**60 passed, 2 skipped**); R7 must still be **re-run after R12** (R12 retrains `models/demand_model.pkl`, invalidating R7's test-time reference — R9's reference is likewise recomputed at test time, so it too is retrain-safe).
- The Batch tab uses the corrected `expected_demand` field but was not exercised end-to-end (no CSV upload in the AppTest); the field contract is covered by the source-parse test.
- `README.md:158,333`, `scripts/load_test.sh:46`, and `tests/smoke_tests.py:100,148` still carry the legacy `"bayesian"` string (R23/R14 own those; `smoke_tests.py` collects 0 tests so the suite is unaffected).
- Remaining P0 is empty now; next P1 items include R12 (temporal split + `product_id`), R14–R26.

Next session should start with:
- R12 (honest temporal split + `product_id` handling) and **re-run R7 after it**. Or R14 (smoke tests) / R15 (drift) — see `.agents/ROADMAP.md`.

---

## 2026-09-29 — R6 done: canonical `grid_search` (alias `grid`), legacy `"bayesian"` → HTTP 422, adaptive grid resolution (1 code commit)

Done:
- **R6 implemented and verified. Code commit `b48d18a`** ("feat(api): canonical grid_search method; reject legacy \"bayesian\" with 422 (R6)"), touching `src/api/schemas.py`, `src/pricing/engine.py`, `src/pricing/optimizer.py`, `configs/config{,.dev,.prod}.yaml`, `tests/test_api.py`, `tests/test_optimizer_real.py`.
  - **Method naming / 422 (D2):** `PricingRequest.optimization_method` is now `Literal["grid_search", "grid"]` defaulting to `"grid_search"`; `"bayesian"` and any unknown value fail Pydantic validation → **HTTP 422** (previously `"bayesian"` was the default and unknown values hit `engine.py`'s `ValueError` → HTTP 500). `engine.get_optimal_price` defaults to `"grid_search"`, dispatches only `grid`/`grid_search` to `PriceOptimizer`, and the `"bayesian"` branch, its now-unused `BayesianPriceOptimizer` import, and the dead `compare_methods()` (it compared a strategy that no longer exists) were removed. `configs/*.yaml`'s unread `default_method` was corrected `bayesian` → `grid_search` (naming honesty, rule 24).
  - **Steps-adaptation fix (the R2 caveat, resolved):** `PriceOptimizer` no longer uses a fixed 50-point grid. `_grid_points()` scales the candidate count with the bound width (target spacing `0.02`, floor `901` points, cap `20001`) and `optimize` now vectorizes `model.predict` over the whole grid. `optimize_with_constraints` (margin floor + inventory cap) was added so the served method keeps the business-constraint contract the retired `"bayesian"` path provided.
  - **R6 status codes** (`POST /v1/optimize-price`, `price_min=70, price_max=110`, `TestClient`): `"grid_search"` → **200** (`optimal_price=77.36`); `"grid"` → **200**; `"bayesian"` → **422**; `"not-a-method"` → **422**; omitted → **200** (defaults to `grid_search`).
  - **R6 revenue ratios** (served `grid_search` vs a test-time 901-point reference, CONVENTIONS rule 34): (30,80) **1.00034**, (70,110) **1.00034**, (10,200) **1.00000**, (100,120) **1.00000**, (30,120) **1.00078** — all ≥ 0.99 and all served prices in bounds. The R2 caveat ratios (e.g. (30,120) 0.97145) no longer occur.
  - **Regression test + pre-fix failure (rule 18):** new `tests/test_optimizer_real.py::test_served_grid_optimizer_reaches_reference_optimum` (all five bounds). Against the pre-fix `optimizer.py` restored from `HEAD` it **fails 2 of 5** — (30,80) `5887.49 < 0.99×5948.35`, (30,120) `5776.03 < 0.99×5945.78` — and passes 5/5 after the fix. `tests/test_api.py` asserts 200 for `grid`/`grid_search` and 422 for `bayesian`/unknown.
  - **Suite:** `pytest tests/` → **53 passed, 2 skipped**, 0 collection errors. Only post-summary noise is the pre-existing `PredictionLogger.__del__` shutdown `ImportError` (STATE §5.11 / R17).
- **Docs updated once, after the code:** ROADMAP **R6 → done** with the status/ratio evidence and the steps-adaptation fix; STATE.md §1 (Bayesian row → no longer served; grid row → R6; constraints row; input-validation row; unit-tests row → 53 passed), §2 serving-path dispatch + verified note, §3 (added `BayesianPriceOptimizer`, removed deleted `compare_methods`), §4 (`default_method`), §5.1/§5.2/§5.3, frontend path, `Last verified` → `b48d18a`; this LOG entry.

Left open / blocked:
- **R9 (API contract test) and R10 (Streamlit contract) remain `todo`.** R6 added status-code + optimizer-level ratio tests; R9 still owes the API-level response-field + ratio-through-HTTP assertions. R10 must also stop `app.py:128-132` offering `"bayesian"` (it now 422s) and fix the `predicted_demand`/`expected_demand` mismatch.
- `README.md:158,333`, `scripts/load_test.sh:46`, and `tests/smoke_tests.py:100,148` still carry the legacy `"bayesian"` string (R23/R14 own those; `smoke_tests.py` collects 0 tests so the suite is unaffected).
- `BayesianPriceOptimizer` (`src/pricing/bayesian_optimizer.py`) is now reachable only from tests; deleting it (and its tests' imports) is D1/R22.
- **R7 must be re-run after R12** (R12 retrains `models/demand_model.pkl`, invalidating R7's test-time reference).
- `git status` at session end: working tree clean after the docs commit; `main` was not moved (all commits on `development`).

Next session should start with:
- R9 (API contract test — 200 grid/grid_search, 422 bayesian, response fields, ratio through HTTP), then R10 (Streamlit contract + method). R7 must be re-run after R12.

---

## 2026-09-29 — R4, R5, R13 done: shared feature builder; loud registry resolution + promote fix; health check by model type (3 code commits)

Done:
- **R4 implemented and verified. Code commit `946eae9`** ("refactor(pricing): single shared serving feature builder for both optimizers (R4)").
  - New `src/pricing/features.py::build_serving_features(base_features, price, feature_columns=None)` is the **only** function that computes price-dependent serving features; both `src/pricing/optimizer.py` and `src/pricing/bayesian_optimizer.py` consume it and their duplicated `_build_features` (the R2 interim copy) is deleted. `grep -n "price_advantage_sin\|log_comp_price" src/pricing/optimizer.py src/pricing/bayesian_optimizer.py` → no matches.
  - **Evidence:** `tests/test_serving_features.py` (new, 4 tests) drives both optimizers over a degenerate `[77.0,77.0]` range with a recording model and asserts the frames fed to `predict` have identical ordered 31 columns/values and identical predictions; `pytest tests/test_serving_features.py -v` → 4 passed. R2's `test_grid_optimizer_builds_complete_feature_frame` was retargeted to the shared builder (criterion unchanged). No behavioral drift: bayesian `(70,110)` → 77.372484/5951.359, grid `(70,110,50)` → 77.346939/5949.394 (same as R1/R2). Suite → **38 passed, 2 skipped**.
- **R5 implemented and verified. Code commit `fdce6c4`** ("fix(pricing): loud, correct MLflow registry resolution + alias-based promote (R5)").
  - **Environment root-cause fix:** `mlflow` 2.12.1 was unimportable (protobuf 7.35.1 dropped `google.protobuf.service`; setuptools 82 dropped `pkg_resources`). Installed `protobuf==4.25.9` + `setuptools<81` into the venv; `import mlflow` now succeeds (verified with a register → alias → `pyfunc.load_model` round-trip). `pip check` now flags protobuf for `tensorflow`/`opentelemetry-proto`, **neither imported anywhere in this repo** (grep). This was chosen over faking mlflow, per the owner's direction, so R5(c) and R13 are verified end-to-end.
  - `engine.load_model`: resolves the `production` alias (fallback `tags.stage='Production'`), loads `models:/<name>@production`; when neither exists or the registry is unreachable it logs at **ERROR**, records `model_source="local"`, and exposes it via `/v1/health` (`checks.model.source`). Bounds registry calls (`MLFLOW_HTTP_REQUEST_TIMEOUT=5`, `_MAX_RETRIES=1`) so a dead `http://localhost:5000` fails fast instead of 504-ing after 30s (pre-hardening: 2 API tests 504, suite ~194s — reproduced under a protobuf shim).
  - `scripts/promote_model.py` rewritten with `set_registered_model_alias` + `set_model_version_tag`, lazy mlflow import, default tracking URI = repo `mlruns/` file store. `grep -rn "get_latest_versions\|transition_model_version_stage" src/ scripts/` → no matches.
  - **Evidence:** direct run — no alias → `ERROR ... No Production version or 'production' alias found ... Falling back to the local artifact` + `source=local, version=None`; `/v1/health` → HTTP 200, `checks.model = {'status':'ok','loaded':True,'source':'local'}`; after `promote_model()` → `source=mlflow, version='1'`. `tests/test_mlflow_registry.py` (new, 4 tests, isolated temp registry, `importorskip("mlflow")`) → 4 passed.
- **R13 implemented and verified. Code commit `efe4d5e`** ("fix(api): health check probes the served model's real feature contract (R13)").
  - `health_checker.py::_probe_model` derives the probe width from the served feature columns (`engine.feature_columns`, passed by `router.py`) instead of `getattr(model, "n_features_in_", 10)`; `grep` for the old expression → no matches.
  - **Pre-fix failure reproduced (CONVENTIONS rule 18):** old probe on a pyfunc model → `{'status':'error','error':'Feature shape mismatch, expected: 31, got 10'}`, overall `degraded` (503); new probe → `ok`/`healthy`.
  - **Evidence:** `tests/test_health_model_type.py` (new, 3 tests) asserts `GET /v1/health` → HTTP 200 + `checks.model.status == "ok"` for a native `XGBRegressor` and for an `mlflow.pyfunc` wrapper (built via `save_model`/`load_model`, no registry) → 3 passed.
- **Cross-task re-check (per instruction):** R4's and R5's tests re-run together with R13 → `pytest tests/test_serving_features.py tests/test_optimizer_real.py tests/test_mlflow_registry.py tests/test_health_model_type.py -q` → **24 passed, 2 skipped**. Full suite `pytest tests/` → **45 passed, 2 skipped**, 0 collection errors.
- **Docs updated once, after all three:** ROADMAP **R4/R5/R13 → done** with evidence (each in its own task commit); STATE.md — mlflow env note, §1 (grid, health, MLflow-versioning, error-handling, Optuna, unit-tests rows), §2 serving path + verified note, §5.6/§5.8/§5.12 marked fixed, `Last verified` → `efe4d5e`; this LOG entry.
- **Commits:** three separate code commits, no amends, no combining: `946eae9` (R4), `fdce6c4` (R5), `efe4d5e` (R13), plus this docs commit. All on `development`; `main` was not moved.

Left open / blocked:
- **Environment caveat:** the venv now has `protobuf==4.25.9`, which conflicts with `tensorflow`/`opentelemetry-proto` per `pip check`. Neither is used by this repo; `requirements.txt` (R21) should record the pin so a fresh install reproduces it.
- R6 (canonical `grid_search`, reject `"bayesian"` with 422, revenue-ratio criterion), R9, R10 remain `todo`. R4 did not unify the two optimizer *strategies* (that is R6/D2) — only their feature construction.
- The R2 coarse-grid caveat on wide bounds is unchanged and is now an explicit R6 criterion.
- **R7 must be re-run after R12** (R12 retrains `models/demand_model.pkl`, invalidating R7's test-time reference).
- The repo's local `mlruns/` registry was touched by exploratory probes during this session (a `production` alias and a `stage=Production` tag were set on version 2). Both were removed afterwards, restoring it to `aliases: []` / no tags / `current_stage: None` for both versions. `mlruns/` is gitignored, so no repo state changed; the tests themselves use isolated temp registries.

Next session should start with:
- R6 (now with the revenue-ratio criterion), then R9/R10. Update `tests/test_api.py`'s `"bayesian"` payload to `"grid_search"` as part of R9 once R6 rejects it.

---

## 2026-09-29 — R7 and R8 done: real-model optimizer regression test; plain `pytest tests/` green (2 code commits)

Done:
- **R7 implemented and verified. Code commit `75151b3`** ("test(pricing): add real-model optimizer regression test (R7)"), new file `tests/test_optimizer_real.py` (15 tests).
  - Loads the committed `models/demand_model.pkl` + `models/features.json`; asserts R1's seven conditions (revenue ≥ 0.99× a 901-point reference grid, `optimization_success`, in-bounds, bound-aware interiority, no `L-BFGS-B`/`minimize(`, result contract + `PricingResponse`, margin constraint) and R2's (complete 31-column frame, grid revenue ratio at `(70,110)` `steps=50`).
  - **No hardcoded model-derived numbers:** the reference optimum is computed at test time from the model on a 901-point grid built by a test-local *oracle* feature builder (`_serving_features`), deliberately independent of the optimizers' own `_build_features` so the reference is not circular (CONVENTIONS rules 14, 34). Only request inputs / criteria constants remain literal.
  - **PASS on current code:** `pytest tests/test_optimizer_real.py -q` → **13 passed, 2 skipped** (the skips are `(10,200)`/`(100,120)`, whose true optimum is on a bound).
  - **FAIL demonstrated against the pre-fix code:** `git checkout c32841f -- src/pricing/bayesian_optimizer.py src/pricing/optimizer.py` → **7 failed, 6 passed, 2 skipped, exit 1** (then restored to HEAD). Failures were exactly the R1/R2 bugs — L-BFGS-B returning a bound/midpoint on `(30,80)`/`(70,110)`/`(30,120)`, the bound-hugging check, `L-BFGS-B` present in source, `AttributeError: 'PriceOptimizer' object has no attribute '_build_features'`, and the exact R2 `KeyError: "['price_advantage', 'log_price', ...9 columns...] not in index"`.
- **R8 implemented and verified. Code commit `8791772`** ("test(api): make plain pytest tests/ collect and pass (R8)"), touching `tests/conftest.py` (new), `tests/test_api.py`, `pytest.ini`.
  - `tests/conftest.py`: repo-root `sys.path` bootstrap + shared `client` fixture that imports `src.api.server` lazily (so a heavy optional dependency cannot break collection of unrelated files). `tests/test_api.py`: local `client` fixture and module-level app import removed. `pytest.ini`: `--strict-config` added.
  - **Evidence:** `/home/arshiaask/projects/venv/bin/pytest tests/` → **exit 0**, `34 passed, 2 skipped`, **0 collection errors**, **36 tests collected** (≥ 20 ✓). `grep -rn "mlflow" tests/` → no matches; forced-unavailable run (`sys.modules['mlflow']=None`) → **34 passed, 2 skipped, exit 0**. The `PredictionLogger.__del__` shutdown `ImportError` (STATE.md §5.11 / R17) still prints after the summary but does not change the exit code — out of R8's scope.
- **Docs updated once, after both:** ROADMAP **R7 → done** and **R8 → done** with the evidence above; STATE.md §1 unit-tests row, §2 serving note, §5.6, and the `Last verified` line → `8791772`; this LOG entry.

Left open / blocked:
- R6 (canonical `grid_search`, reject legacy `"bayesian"` with 422, revenue-ratio criterion), R9 (API contract test), R10 (Streamlit contract) remain `todo`; R8's criterion is met, but R9 must update `tests/test_api.py` when R6 changes the accepted method values (it still posts `"bayesian"`).
- The R2 coarse-grid caveat on wide bounds is unchanged and is now an explicit R6 criterion.
- **R7 must be re-run after R12** (R12 retrains `models/demand_model.pkl`, invalidating R7's test-time reference).
- No branch was created; both code commits plus the docs commit sit on the current branch (`development`, == `main` before this session). `main` was deliberately not moved this session.

Next session should start with:
- R6 (now with the revenue-ratio criterion), then R9/R10. Update `tests/test_api.py`'s `"bayesian"` payload to `"grid_search"` as part of R9 once R6 rejects it.

---

## 2026-09-29 — R6 acceptance criteria amended to require a revenue-ratio check (docs-only)

Done:
- **ROADMAP R6 amended (no code change).** Recorded the coarse-grid finding from R2 and extended R6's acceptance criteria: because D2/R6 make `grid_search` the sole served optimizer, R6 must also verify that, for `(30,80)`, `(70,110)`, `(10,200)`, `(100,120)`, `(30,120)`, the served `expected_revenue` is **≥ 0.99 ×** the maximum over a **≥ 901-point** grid computed at test time (CONVENTIONS rule 34) — not just HTTP 200/422 status codes. This requires raising/adapting `steps` to the bound width or reusing R1's dense-grid + refinement. Files touched now also lists `src/pricing/optimizer.py` as a possible home for the resolution fix.
- **Note recorded (from R2, commit `ffc55fe`):** at the caller-chosen `steps=50` the fixed-width grid undershoots on wide bounds — observed revenue ratios vs the test-time 901-point reference: `(70,110)` 1.00018, `(30,80)` 0.98977, `(30,120)` 0.97145 (see the R2 evidence).

Left open / blocked:
- No roadmap item status changed; R6 remains `todo`. This was a documentation-only amendment to R6's criteria.
- R7, R6, R4, R8/R9/R10 remain `todo`.

Next session should start with:
- R7 (real-model regression test locking in R1 + R2), then R6 (now with the revenue-ratio criterion), then R8/R9/R10. Work is on branch `task/R2-fix-grid-search`.

---

## 2026-09-29 — R2 done: grid search builds the complete 31-column feature frame; API `grid_search` returns 200

Done:
- **R2 implemented and verified. Code commit `ffc55fe`** ("fix(pricing): build complete 31-column feature frame in grid search (R2)"), touching `src/pricing/optimizer.py` and `src/pricing/engine.py`.
  - `optimizer.py`: added `_build_features(base_features, price)` mirroring R1's `BayesianPriceOptimizer._build_features`, and replaced the inline 5-column construction with it, so all 31 `models/features.json` columns are present. Reused R1's feature logic but did **not** merge the optimizers (that is R4).
  - `engine.py`: `elif method == "grid"` → `elif method in ("grid", "grid_search")`, so the canonical `grid_search` name (DECISIONS D2) returns 200. The `"bayesian"` branch is untouched — its 422 rejection and the schema enum are R6.
- **Before (reproduced against the committed model):** `PriceOptimizer(model, feats).optimize(base, 70, 110, 50)` → `KeyError: "['price_advantage', 'log_price', 'log_comp_price', 'price_advantage_sin', 'price_change_1d', 'price_change_7d', 'roll_mean_price_7', 'roll_mean_price_14', 'roll_mean_price_28'] not in index"` — the exact STATE.md §5.1 symptom.
- **After (observed evidence):**
  - Direct: `optimize(base, 70, 110, 50)` → `optimal_price=77.3469`, `expected_demand=76.9183`, `expected_revenue=5949.394`; test-time 901-point reference max revenue `5948.347`; ratio `1.00018 ≥ 0.99`; price within `[70,110]`; no exception.
  - API: `python -m src.api.server` (port 8137) → `GET /v1/health` **200**; `POST /v1/optimize-price` `optimization_method="grid_search"` → **HTTP 200** (`optimal_price=77.3469, expected_revenue=5949.394, optimization_method="grid_search"`); `"grid"` → **HTTP 200** too. The 9-column KeyError no longer occurs (was HTTP 500).
  - `pytest tests/ -q` → **21 passed**.
- Docs updated in the same session: ROADMAP **R2 → done** with the evidence above; STATE.md §1 grid row → CONFIRMED, §2 serving-path dispatch, §5.1 marked fixed, §5.2 and the Streamlit row corrected (the engine now accepts `grid_search`), `Last verified` → `ffc55fe`.
- **Branch:** both commits (`ffc55fe` code, docs) are on `task/R2-fix-grid-search`, 2 commits ahead of `main` (`0adb4e3`); `main` was deliberately **not** moved this session.

Left open / blocked:
- **Caveat (outside R2's stated criterion, recorded honestly):** at the caller-chosen `steps=50` the fixed-width grid can undershoot on wide bounds — observed ratios vs the test-time 901-point reference: `(70,110)` 1.00018 ✓, `(30,80)` 0.98977, `(30,120)` 0.97145. This is inherent to a 50-point grid on a piecewise-constant revenue curve with a narrow peak, not the feature-frame bug R2 fixes. R2's criterion is `(70,110)` and it passes. A dense grid + refinement (as in R1) or a higher default resolution would close the gap; not in R2's scope.
- R6 (canonical `grid_search`, reject `"bayesian"` with 422), R7 (real-model regression test), R4 (shared feature builder), R8/R9/R10 remain `todo`.
- **Note for R6/R7:** after R6, `grid_search` becomes the only served optimizer, so the coarse-grid caveat above becomes user-facing — worth considering a resolution bump there or in a follow-up.

Next session should start with:
- R7 (real-model regression test locking in R1 + R2), then R6, then R8/R9/R10. Workflow: branch from current `main`, prefer merge over amend once a branch exists (see the R1 branch-divergence incident).

---

## 2026-09-29 — R3 done: lazy/optional `mlflow` import; API and `pytest tests/` start without it

Done:
- **R3 implemented and verified. Code commit `0ba7d5a`** ("fix(pricing): import mlflow lazily so serving starts without it (R3)"), touching only `src/pricing/engine.py`, `src/pricing/model_loader.py`, `src/utils/mlflow_tracking.py`.
  - `engine.py`: removed the top-level `import mlflow` / `from mlflow.tracking import MlflowClient`; moved them inside `load_model`'s existing try block (`engine.py:52-53`). When the import fails, the pre-existing `except Exception` fallback loads `models/demand_model.pkl` — behavior unchanged when mlflow is available.
  - `model_loader.py`: removed top-level `import mlflow` / `import mlflow.xgboost`; moved them into `load_production_model` (`:7-8`). This module is on the API import path (`engine.py:11` imports it), which is why it had to be fixed too.
  - `mlflow_tracking.py`: removed top-level imports; each `MlflowTracker` method now imports `mlflow` locally.
  - `src/api/server.py` needed **no edit** — it only reaches mlflow transitively via `router → engine → model_loader`; the ROADMAP "files touched" entry for it is satisfied by making that path lazy.
- **Verified against this revision's criteria (observed evidence):**
  - `python -c "import src.api.server"` → `IMPORT_OK Dynamic Pricing API`, **exit 0**, with the real broken mlflow (protobuf: `cannot import name 'service' from 'google.protobuf'`); log shows the local-pickle fallback.
  - Forced-unavailable: `python -c "import sys; sys.modules['mlflow']=None; sys.modules['mlflow.tracking']=None; import src.api.server"` → **exit 0**.
  - `python -m src.api.server` (port 8123) → `curl /v1/health` → **HTTP 200** `{"status":"healthy",...,"checks":{"model":{"status":"ok","loaded":true}}}`.
  - `grep -n "^import mlflow\|^from mlflow" src/` → **no matches**; only standalone scripts (`scripts/promote_model.py`, `scripts/train_with_tuning.py`) still import mlflow at top level, and neither is on the API import path.
  - Existing suite unaffected: `pytest tests/ --ignore=tests/test_api.py -q` → **17 passed**.
- **Side effect (root-cause fix, not a workaround — CONVENTIONS rule 19):** a plain `pytest tests/` now **collects and passes: 21 passed, exit 0, 0 collection errors**. R3 fixed the `tests/test_api.py:4` import at its root instead of hiding it with `--ignore`/config/conditional imports. R8 is left `todo` (its `conftest.py`/`pytest.ini` and the R6/R9 contract updates are still open; note `test_api.py` still posts the legacy `"bayesian"` method, which R6 will reject → R9 must update it).
- Docs updated in the same session: ROADMAP **R3 → done** with the evidence above; STATE.md §1 (FastAPI row → CONFIRMED, unit-tests row → 21 passing), §2 (serving-path note: no mlflow stub needed), §3 (`load_production_model` line refs), §5.6 (marked fixed for the serving path), top "Broken" note, and the `Last verified` line → `0ba7d5a`.

Left open / blocked:
- `scripts/train_with_tuning.py` still imports `mlflow` at module top level (`:9-11`) and still cannot run here — out of R3's stated scope (not on the serving path); it remains a P1/R21-adjacent concern.
- R2 (grid `KeyError`), R6 (`grid_search`/422), R7 (real-model regression test) remain `todo`. R8's acceptance is now met in practice (21 passed, 0 collection errors) but the item also names `tests/conftest.py` + `pytest.ini` and depends on R6/R9 for the contract updates, so it was **not** marked done.

Next session should start with:
- R2, then R7 (real-model regression test locking in R1 + R2); then R6, then R8/R9/R10. Workflow: branch from current `main`, prefer merge over amend once a branch exists (see the R1 branch-divergence incident).

---

## 2026-09-29 — R1 done; branch-divergence incident (stale branch base) found and resolved

Done:
- **R1 implemented and verified.** Replaced `scipy.optimize.minimize(method='L-BFGS-B')` in `src/pricing/bayesian_optimizer.py` with a vectorized dense price grid + local refinement (first pass targets 0.02 spacing, min 901 points, so it lands in the global basin; later passes zoom in). Batched `model.predict` with a row-by-row fallback for non-vectorized predict doubles. Removed the unused `method` parameter; no gradient call remains. **Code commit `b21e45a`** (see the incident below for why this hash and not the earlier `a325fbd`).
- **Re-verified against *this* revision's criteria** — revenue ≥ 0.99 × a test-time ≥ 901-point reference grid; `optimization_success` True; price within bounds; bound-aware interiority; contract; constraints — **all pass** (see the ROADMAP R1 evidence table). Observed: `(30,80)`/`(70,110)`/`(30,120)` → **77.3725** (ratios 1.00051/1.00051/1.00094 vs the 901-pt max); `(10,200)` → **200.0** and `(100,120)` → **120.0**, where the true optimum is genuinely the upper bound. `optimize_with_constraints(cost=60, min_margin_pct=0.15)` → price 77.3725, margin 0.2245. `pytest tests/ --ignore=tests/test_api.py -q` → **17 passed**. API (mlflow stubbed): `POST /v1/optimize-price` bayesian → 200, `optimal_price=77.3725`.
- **Incident — stale branch base.** The R1 branch was cut from `f4b0921`, but `main` was **amended** (`f4b0921` → `616a6df`) in the previous session (see the "R1 task-file fixes … `--amend`" entry below). Because an amend rewrites the commit, `616a6df` and `f4b0921` are **siblings** (both children of `c32841f`), and `616a6df` was never an ancestor of the branch. The branch therefore carried the **pre-revision** `.agents/` docs: D1/D2/D15 read as `proposed` (D2 un-merged), and R1's old price-equality criteria. Working from those, this session re-discovered the "strictly interior vs. 901-pt argmax" contradiction for `(10,200)`/`(100,120)` that the revision had **already** fixed (revenue-ratio + bound-aware rule), amended the stale ROADMAP copy, and produced a stale docs commit `0c21805`. The optimizer code itself was fine — only the bookkeeping baseline was stale.
- **Resolution:** reset the branch to the code commit `a325fbd`, then `git rebase --onto 616a6df f4b0921`, which replayed **only** the optimizer change onto `main` (new hash `b21e45a`) and **dropped `0c21805` entirely**. Re-read `main`'s actual `tasks/R1-real-optimizer.md` and ROADMAP R1 and re-ran every check against those exact criteria (not the stale-branch numbers). Then one clean docs commit against `main`'s current content (this entry + ROADMAP R1 `done` + STATE.md updates). `main` fast-forwarded to include the code and docs commits.
- Scope confirmed: `b21e45a` touches only `src/pricing/bayesian_optimizer.py`; the `"bayesian"` label and the `engine.py`/`schemas.py` dispatch are untouched, so R6/D2's `grid_search`/HTTP-422 work is entirely open and unimplemented.

Left open / blocked:
- R6/D2 (rename to `grid_search`, reject `"bayesian"` with 422) not started; R2 (grid `KeyError`), R3 (mlflow import), R8 (pytest collection) remain `todo`. A plain `pytest tests/` still aborts collection on `tests/test_api.py` (mlflow).
- No permanent regression test was added — that is ROADMAP **R7** (separate item; R1 must not create `tests/test_optimizer_real.py`).

Next session should start with:
- R2 and R3 (P0), then R7 (real-model regression test locking in R1 + R2). **Workflow hazard to avoid:** always branch from the current `main`, and prefer a merge over an amend once a branch exists — the `--amend` here rewrote the shared base and orphaned the R1 branch.

---

## 2026-09-29 — R1 task-file fixes + git-workflow note; `.agents/`+`AGENTS.md` folded into the planning commit via `--amend`

Done:
- **`.agents/tasks/R1-real-optimizer.md`:**
  - (a) Replaced the stale Out-of-scope example "(e.g. D2 must be `accepted` first)" — D2 is now
    `accepted`, so the example was wrong — with the current state: only D1/D2/D15 are `accepted`,
    **every other entry is still `proposed` and must not be implemented**. Named **D6**
    (chronological train/validation split) and **D5** (dropping `product_id`) as the currently-
    `proposed` decisions that are tempting but out of scope for R1, and stated that even D1/D2 do
    not license touching feature engineering or training code in R1.
  - (b) Added an **"Interim only"** note near "Relevant files": fixing `bayesian_optimizer.py` in
    place is interim — per accepted D1, once R6 locks `"bayesian"` as rejected (HTTP 422) the
    module becomes unreachable from the API and must be retired/merged by a later task (R4/R22);
    **R1 must not delete, rename, or merge the file**, only fix the algorithm inside it.
  - (c) Added a "Reference commits" note using a *relative* self-reference (`git log -1`) while
    keeping `c32841f` as the literal ground-truth citation.
- **Relative self-reference (no hardcoded self-HEAD):** reworded the top "Reference commits" note
  in `AGENTS.md`, `.agents/ROADMAP.md`, `.agents/DECISIONS.md`, and `.agents/CONVENTIONS.md` so it
  no longer hardcodes HEAD `f4b0921` as *the current* commit; it now reads "the current commit
  (see `git log -1`)". `c32841f` remains the literal, unchanging ground-truth citation. Rationale:
  these files are about to be folded into an amended commit, which would immediately stale a
  hardcoded self-referencing SHA. Past (non-top) LOG entries were left untouched.
- **New workflow note (Part 2a):** added a "## Git workflow for `.agents/` edits" section to
  `AGENTS.md`: planning-only edits to `.agents/*.md` + `AGENTS.md` within an active planning phase
  (before any ROADMAP item is `in-progress`) may be amended into the existing planning commit to
  keep one clean snapshot; `.agents/LOG.md` stays the authoritative chronological record regardless
  of commit boundaries; code changes are never amended — each gets its own commit(s).
- **Git history:** the uncommitted `.agents/` + `AGENTS.md` changes in this working tree are being
  folded into the existing planning commit via `git commit --amend` rather than added as a new
  commit, per the workflow note above. **Pre-amend commit: `f4b0921`** ("docs(agents): track
  .agents source-of-truth docs + AGENTS.md entrypoint"). The post-amend hash is deliberately not
  recorded here (it is unknowable before the amend and would be a stale self-reference); read it
  from `git rev-parse HEAD`. The untracked `.agents/archive/audit_Dynamic-Pricing-Engine.md`
  (archived 2026-09-28 per CONVENTIONS rule 33) is also being brought into the commit by
  `git add .agents`, so the tree is left fully clean.
- No code under `src/`, `scripts/`, `tests/`, `app.py`, or configs was changed. No roadmap item was
  started (R1 remains `todo`).

Left open / blocked:
- R1 is still `todo`; implementation was intentionally not started (this session was documentation
  + git hygiene only).
- Every decision except D1, D2, D15 (`accepted`) and D3, D14, D22, D23 (`superseded`) is still
  `proposed` and awaits the owner.
- `mlflow` is still unimportable in the local venv (protobuf conflict); R3/R8 remain blocked on that.

Next session should start with:
- Begin the P0 unblockers R1 (task file at `.agents/tasks/R1-real-optimizer.md`), R2, R3. Mark each
  `in-progress` before starting. R7 must be re-run after R12.

---

## 2026-09-29 — Owner finalized D1/D2 accepted; legacy "bayesian" locked to HTTP 422; reference-commit clarification (no commit)

Done:
- **DECISIONS.md:** D1 and D2 both moved `proposed` → `accepted` at the owner's direction. D2's open owner choice on the legacy `"bayesian"` method is removed and locked: `"bayesian"` (and any unrecognized value) is **REJECTED** with HTTP 422, not a deprecated alias. D2's Consequences now state that `src/api/schemas.py`'s enum/validator accepts only `"grid_search"` and its alias `"grid"`, and that `"bayesian"` / any other value is invalid input rather than silently normalized. D3's superseded note was updated to drop the "open owner choice" phrasing. Header refreshed: **D1, D2, D15 `accepted`; D3, D14, D22, D23 `superseded`; all other entries remain `proposed`.**
- **ROADMAP.md:** R6's acceptance criteria now describe only the accepted branch — `"grid"` and `"grid_search"` → HTTP 200; `"bayesian"` and any other unknown value → HTTP 422 (Pydantic/enum validation error, not 500, not a deprecation-warning alias). R6's title was updated and the two-branch / either-or "OPEN OWNER DECISION" note removed. R9's contract-test description was updated to assert 200 for `grid`/`grid_search` and 422 for `"bayesian"`. No roadmap item status changed (all still `todo` except R33 `done`).
- **Reference-commit clarification (no new commit):** added one consistently-phrased note near the top of `ROADMAP.md`, `DECISIONS.md`, `CONVENTIONS.md`, `AGENTS.md`, and this entry: ground truth is verified against commit `c32841f` (see `.agents/STATE.md`), while this planning revision sits on top of the working tree at HEAD `f4b0921` and was **not** committed. Existing "verified against `c32841f`" lines were left unchanged; `STATE.md` was not touched (it was not re-verified).
- No code under `src/`, `scripts/`, `tests/`, `app.py`, or configs was changed. No roadmap item was started or marked `done`. **No `git add` / `git commit` was run** — all `.agents/` edits remain uncommitted working-tree changes.

Left open / blocked:
- D1, D2, and D15 are now `accepted` and therefore unblocked for implementation, but implementation was intentionally not started in this pass (a separate step).
- Every other decision (D4–D13, D16–D21, D24, D25) is still `proposed` and awaits the owner.
- `mlflow` is still unimportable in the local venv (protobuf conflict); R3/R8 remain blocked on that.

Next session should start with:
- Begin the P0 unblockers R1, R2, R3 (task file at `.agents/tasks/R1-real-optimizer.md`), now that D1/D2 are `accepted`. Mark each `in-progress` before starting. R7 must be re-run after R12.

---

## 2026-09-28 — Revised planning docs: runtime reference grids, single-optimizer decision, enforcement tags

Done:
- **ROADMAP.md:** rewrote R1's acceptance criteria to drop the "strictly interior" price rule and all hardcoded numbers (e.g. 77.30). R1 is now revenue-based: for bounds `(30,80)`, `(70,110)`, `(10,200)`, `(100,120)`, `(30,120)` the returned `expected_revenue` must be ≥ 0.99 × the maximum over a ≥ 901-point reference grid **computed at test time with the same model and bounds**; `optimization_success` True; price within bounds; no bound-hugging where the reference argmax is strictly interior. Applied the same "reference at test time, no hardcoded numbers" principle to R2, R7, R9. Made R7 model-agnostic and noted it must be **re-run after R12** (which retrains the artifact). Re-prioritized: **P0 = R1,R2,R3,R6,R7,R8,R9,R10 (8)**; **P1 = R4,R5,R11–R26 (18)**; **P2 = R27–R33 (7)**; updated the execution-order section. Updated R6/R9/R10 for the single method name (`grid_search`, alias `grid`) and wrote both branches of the legacy-`"bayesian"` open owner decision (HTTP 422 reject vs deprecated alias). All statuses remain `todo`; R33 stays `done`.
- **DECISIONS.md:** merged D2+D3 into one decision — single canonical optimizer = vectorized dense price-grid search named `grid_search` (alias `grid`) — and marked D3 `superseded` by D2. Rewrote D1 to match (one optimizer module, one strategy; delete `integrated_optimizer.py` and `transformer.py`). Marked D14 `superseded` (covered by CONVENTIONS rule 26) and D22/D23 `superseded` (folded into ROADMAP R23/R32). D16 now names `python:3.12-slim` (the interpreter actually tested) and states the current Dockerfiles pin 3.10 and must be bumped. No entry deleted; D15 stays `accepted`; header refreshed.
- **CONVENTIONS.md:** resolved the rule 19 ↔ R3 contradiction (optional/lazy heavy-dep imports in production code are *required*; what is forbidden is hiding a broken dependency in tests via `--ignore`, config overrides, or conditional test imports). Narrowed rule 14 to optimizer/pricing/model-prediction tests (schema/middleware exempt). Added an enforcement status tag to every rule (`enforced` or `target (after Rxx)`). Appended two rules: **33** (owner-supplied files must never be deleted/overwritten without explicit approval — archive under `.agents/archive/`) and **34** (tests must not hardcode model-derived reference values; compute them at test time). Numbering 1–32 preserved.
- **Archived the superseded audit** per new rule 33: moved `/tmp/audit_Dynamic-Pricing-Engine.md.bak` → `.agents/archive/audit_Dynamic-Pricing-Engine.md` (30,266 bytes, MD5 `660b46ed041c1e81486ab11e6cb7476d`). It was present, so no re-supply was needed.
- **Consistency:** updated `.agents/tasks/R1-real-optimizer.md` to match the new R1 criteria; checked `AGENTS.md` (it lists no priorities/counts/file lists, so no change was needed); normalized every "Last updated" line to `2026-09-28, against commit c32841f (see .agents/STATE.md)`; grepped `.agents/*.md` for stale R/D/rule/priority-count references. `STATE.md` was **not** touched (nothing was re-verified).
- No code under `src/`, `scripts/`, `tests/`, `app.py`, or configs was changed. No roadmap item was started.

Left open / blocked:
- **OPEN OWNER DECISIONS:** (1) legacy `"bayesian"` handling — reject with HTTP 422 (recommended) or accept as a deprecated alias (see DECISIONS D2, ROADMAP R6/R9); (2) accept or override the merged D2, the revised D1, and the remaining `proposed` entries.
- R7 must be re-run after R12 (the model artifact is retrained there).
- The historical priority counts in the 2026-09-27 entry below ("14 P0 / 12 P1 / 7 P2") are left as-is: that entry records that session's state and past log entries are not edited.
- `mlflow` is still unimportable in the local venv (protobuf conflict); R3/R8 remain blocked on that.
- `.agents/archive/audit_Dynamic-Pricing-Engine.md` is a read-only archive — do not edit it (rule 33).

Next session should start with:
- Owner to pick the legacy-`"bayesian"` option and accept/override D1/D2, then start the P0 unblockers R1, R2, R3 (task file at `.agents/tasks/R1-real-optimizer.md`). Mark each `in-progress` before starting.

---

## 2026-09-28 — Deleted the superseded audit, corrected STATE.md, and put `.agents/` under git

Done:
- Compared `audit_Dynamic-Pricing-Engine.md` with `.agents/STATE.md`. STATE.md supersedes it: it is more complete and already corrects the audit's two known errors (the "nested clone" and the non-existent `docs/ARCHITECTURE.md`). Backed the audit up to `/tmp/audit_Dynamic-Pricing-Engine.md.bak` and **deleted** it as redundant (two sources of truth violate CONVENTIONS rule 27).
- Fixed errors in `.agents/STATE.md`: (a) the prediction logs were described as "committed" but are untracked (`logs/` is gitignored) — corrected in §1 and §5.1; (b) `reports/feature_importance.csv:31` → `:30` for `product_id` (importance 0.01195); (c) §6 retitled now that the audit is gone; (d) the `.gitignore` bullet updated to the new tracked state; (e) `Last verified` → 2026-09-28.
- `.gitignore`: removed the `.agents` ignore so the directory can be tracked. Note for the record: the owner's edit had actually **added** `.agents` to `.gitignore` (replacing the `docs/` ignore), i.e. the directory was still ignored despite the intent to un-ignore it.
- Committed `.agents/` (`STATE.md`, `ROADMAP.md`, `CONVENTIONS.md`, `DECISIONS.md`, `LOG.md`, `tasks/R1-real-optimizer.md`) and the root `AGENTS.md`.
- Bookkeeping: ROADMAP **R33 → done** (evidence recorded); DECISIONS **D15 → accepted** at the owner's direction; "Last updated" lines refreshed. (Also recording the prior session's unlogged output: `.agents/tasks/R1-real-optimizer.md` was created; no code was written.)

Left open / blocked:
- Every roadmap item except R33 is still `todo`; decisions D1–D14 and D16–D25 are still `proposed`.
- `mlflow` is still unimportable in the local venv (protobuf conflict); R3/R8 remain blocked on that.

Next session should start with:
- Accept or override the remaining `.agents/DECISIONS.md` entries, then start the P0 unblockers: R1 (task file at `.agents/tasks/R1-real-optimizer.md`), R2 (grid fix), R3 (lazy/optional mlflow import). Mark each `in-progress` before starting.

---

## 2026-09-27 — Source-code audit completed; `.agents/` planning docs created (no code changed)

Done:
- Audited the whole repo against actual source and runtime (not README/docs) and wrote `.agents/STATE.md`: a claim-by-claim verification table, the real training/serving flows, a dead-code inventory, unread config/env values, and known-broken behavior. Core finding: the headline "Bayesian optimizer" is `scipy` L-BFGS-B on a tree model and returns a bound/midpoint; the grid optimizer crashes with a `KeyError`.
- Wrote `.agents/ROADMAP.md`: 33 discrete items (14 P0 / 12 P1 / 7 P2), all `todo`, each with priority, files, testable acceptance criteria, and dependencies.
- Wrote `.agents/CONVENTIONS.md`: 32 enforceable rules derived from the observed failure patterns (dead code, config/env hygiene, exception handling, test realism, docs-vs-code sync, single source of truth, contracts, ops).
- Wrote `.agents/DECISIONS.md`: 25 ADR-lite entries (D1–D25), all `proposed`, covering the optimizer consolidation, nested-repo policy, SQLite removal, and MLflow-optional posture, plus 21 more.
- Wrote this `.agents/LOG.md` and the root `AGENTS.md` entrypoint.
- No code changes were made. No roadmap item has been started.

Left open / blocked:
- All 33 roadmap items are `todo`; all 25 decisions are `proposed` and await the owner's accept/override. No implementation may begin on a proposed decision.
- `.agents/` is currently gitignored by `.gitignore:86` (see DECISIONS D15); the four planning files are untracked.
- Environment caveat: `mlflow` cannot be imported in the local venv (protobuf conflict), so `python -m src.api.server`, `scripts/train_with_tuning.py`, and `pytest tests/` (collection) fail until ROADMAP R3/R8 are done.
- Note for the record: during the audit, one probe accidentally ran the training pipeline in the repo root and overwrote the untracked `models/demand_model.pkl` and `reports/*`; they were restored from a pre-run copy (MD5 verified) and `reports/training_metrics.json` is back to `R2=0.4682`. Git state was unaffected.

Next session should start with:
- Have the owner accept or override the entries in `.agents/DECISIONS.md` (at minimum D1, D7, D9, D14).
- Then start the P0 unblockers in `.agents/ROADMAP.md`: R1 (real optimizer), R2 (grid fix), R3 (lazy/optional mlflow import). Mark each `in-progress` before starting.
