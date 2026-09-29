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
