# ROADMAP.md — From broken prototype to honest, working demo

This is the prioritized backlog for taking the Dynamic Pricing Engine from
"learning prototype with a fake core" to "honest, working, resume-appropriate
production demo." It is derived from `.agents/STATE.md` (verified ground truth).

**Reference commits:** Ground truth verified against commit `c32841f` (see `.agents/STATE.md`). This planning revision sits on top of the working tree at the current commit (see `git log -1`); no new commit was created for these `.agents/` edits.

**Guiding rule:** the headline capability must become true before anything is advertised.
Do not present a claim as working until an item below that makes it true is `done`.

**Priorities (re-set 2026-09-28; R34 added 2026-09-30; R35 added 2026-10-13):** P0 = R1, R2, R3, R6, R7, R8, R9, R10
(8 items — the core must be true and the suite must run). P1 = R4, R5, R11–R26, R34, R35 (20 items).
P2 = R27–R33 (7 items). Total: 35 items.

---

## How to use this file

1. **Before starting an item**, set its `Status:` to `in-progress`. Do not start two
   items that depend on the same unfinished item unless they are truly independent.
2. **Move an item to `done` only after its Acceptance criteria are verified** by actually
   running the stated check (command, test, or assertion) and observing the stated result.
   Paste the observed evidence (command + output) under the item, or reference the test
   name and its pass.
3. **Never mark something `done` based on the item's description alone.** A title like
   "Fix the optimizer" is not evidence. The acceptance criterion is the evidence.
4. If an item's acceptance cannot be met, leave it `in-progress` or split it into smaller
   checkable items; do not silently weaken the criterion.
5. If you change the code, re-verify the relevant rows in `.agents/STATE.md` and update
   the `Last verified` line there.
6. **Reference values that derive from a model artifact must be computed at test time**
   (see CONVENTIONS rule 34). Acceptance criteria below therefore state *how* to compute a
   reference, never a frozen number — any retrain (e.g. R12) would invalidate a frozen one.

**Status values:** `todo` (all items start here) · `in-progress` · `done` · `blocked`.

**Dependency notation:** "Depends on: R1, R2" means those must be `done` first.

---

## P0 — Core is fake or blocks everything else

### R1 — Replace the non-functional "Bayesian" optimizer with a real search
- **Priority:** P0
- **Status:** done
- **Files touched:** `src/pricing/bayesian_optimizer.py` (the optional `src/pricing/search.py` was not needed)
- **Acceptance criteria:** Against the working-tree (gitignored) `models/demand_model.pkl` + `models/features.json`, using the standard `base_features` from STATE.md §2, for bounds `(30,80)`, `(70,110)`, `(10,200)`, `(100,120)`, and `(30,120)`: the returned `expected_revenue` is **>= 0.99 ×** the maximum revenue over a fine grid of **>= 901 points** on the same bounds, where the reference grid is computed **at test time with the same model and the same bounds** (no hardcoded numbers); `optimization_success` is `True`; and the returned price lies within the bounds. Additionally, for any range where the reference grid's argmax is strictly interior, the returned price must not sit on a bound. (Comparing **revenue** rather than price is required because a tree model's revenue curve is piecewise and has plateaus — distinct prices can tie at the same revenue, so a price-equality test would be both fragile and wrong.) No `scipy.optimize.minimize(method='L-BFGS-B')` (or any gradient method) remains on the tree objective.
- **Depends on:** none
- **Evidence (2026-09-29, commit `b21e45a`, working-tree (gitignored) `models/demand_model.pkl`; reference grid computed at test time per CONVENTIONS rule 34):**

  | bounds | optimal_price | expected_revenue | 901-pt ref max | revenue ratio | ref argmax interior? | bound-aware rule |
  |---|---|---|---|---|---|---|
  | (30,80) | 77.3725 | 5951.359 | 5948.347 | 1.00051 | yes | not on a bound ✓ |
  | (70,110) | 77.3725 | 5951.359 | 5948.347 | 1.00051 | yes | not on a bound ✓ |
  | (10,200) | 200.0000 | 7562.641 | 7562.641 | 1.00000 | no (argmax is the bound) | n/a ✓ |
  | (100,120) | 120.0000 | 4471.819 | 4471.819 | 1.00000 | no (argmax is the bound) | n/a ✓ |
  | (30,120) | 77.3725 | 5951.359 | 5945.783 | 1.00094 | yes | not on a bound ✓ |

  All ranges: `optimization_success=True`, price within bounds, and `expected_revenue >= 0.99 ×` the reference max. Cross-checked against a 200,001-point grid: true global max 5951.35 for the three peaked ranges; the `(10,200)`/`(100,120)` optima are genuinely on the bound (revenue rises monotonically there).
  `grep -n "L-BFGS-B\|minimize(" src/pricing/bayesian_optimizer.py` → no matches.
  Contract unchanged: required keys present, `json.dumps` OK, `PricingResponse(**result)` validates.
  `optimize_with_constraints(base, 30, 120, cost=60.0, min_margin_pct=0.15)` → price 77.3725, `profit_margin=0.2245`, inside the margin-adjusted bounds.
  Existing suite unaffected: `pytest tests/ --ignore=tests/test_api.py -q` → 17 passed (`test_api.py` still aborts collection on the pre-existing mlflow issue, R3/R8).
  The `"bayesian"` method label and the `engine.py`/`schemas.py` dispatch are untouched — the rename/422 work is R6/D2, not R1.

### R2 — Fix grid search to build the complete 31-column feature frame
- **Priority:** P0
- **Status:** done
- **Files touched:** `src/pricing/optimizer.py`, `src/pricing/engine.py` (the engine alias was required by the API criterion below)
- **Acceptance criteria:** `PriceOptimizer(model, feats).optimize(base, 70, 110, 50)` returns a dict without raising, with `70 <= optimal_price <= 110` and `expected_revenue >= 0.99 * (max revenue over a >= 901-point grid on the same bounds, computed **at test time with the same model and bounds** — no hardcoded reference)`. `POST /v1/optimize-price` with `optimization_method="grid_search"` (canonical; `"grid"` is an accepted alias, per DECISIONS D2) returns HTTP 200 (not 500). The 9-column `KeyError` from STATE.md §5.1 no longer occurs.
- **Depends on:** none
- **Evidence (2026-09-29, commit `ffc55fe`, working-tree (gitignored) `models/demand_model.pkl`; reference grid computed at test time per CONVENTIONS rule 34):**
  - **Before (reproduced):** `PriceOptimizer(model, feats).optimize(base, 70, 110, 50)` → `KeyError: "['price_advantage', 'log_price', 'log_comp_price', 'price_advantage_sin', 'price_change_1d', 'price_change_7d', 'roll_mean_price_7', 'roll_mean_price_14', 'roll_mean_price_28'] not in index"` (the exact STATE.md §5.1 symptom).
  - **After (direct):** `optimize(base, 70, 110, 50)` → `optimal_price=77.3469`, `expected_demand=76.9183`, `expected_revenue=5949.394`; test-time 901-point reference max revenue `5948.347`; ratio `1.00018 >= 0.99` ✓; `70 <= 77.3469 <= 110` ✓; no exception. The `_build_features` mirror selects all 31 `models/features.json` columns.
  - **After (API):** `python -m src.api.server` (port 8137) → `GET /v1/health` → **HTTP 200**; `POST /v1/optimize-price` `optimization_method="grid_search"` → **HTTP 200**, body `optimal_price=77.3469, expected_revenue=5949.394, optimization_method="grid_search"`; `"grid"` → **HTTP 200** as well. Previously both the grid path (KeyError) and `grid_search` (ValueError → 500) failed.
  - Existing suite unaffected: `pytest tests/ -q` → **21 passed**.
  - **Caveat (outside the stated criterion, recorded honestly):** at the caller-chosen `steps=50` the fixed-width grid can undershoot on wide bounds — observed ratios vs the test-time 901-point reference: `(70,110)` 1.00018, `(30,80)` 0.98977, `(30,120)` 0.97145. This is inherent to a fixed 50-point grid on a piecewise-constant revenue curve with a narrow peak, not the feature-frame bug R2 fixes. R2's criterion is `(70,110)` and it passes; a dense grid + refinement (as in R1) or a higher default resolution would close the gap and is left to a later item (relevant once R6 makes `grid_search` the only served method).

### R3 — Make `mlflow` import lazy/optional so serving and tests start without it
- **Priority:** P0
- **Status:** done
- **Files touched:** `src/pricing/engine.py:9`, `src/pricing/model_loader.py:1-2`, `src/utils/mlflow_tracking.py:1-2`, `src/api/server.py`
- **Acceptance criteria:** In an environment where importing `mlflow` fails (or with `sys.modules["mlflow"] = None` forced), `python -c "import src.api.server"` exits 0, and `python -m src.api.server` serves `GET /v1/health` → HTTP 200 using the local pickle. No top-level unconditional `import mlflow` remains on the API import path. (Optional/lazy imports of heavy dependencies in production code are *required* — see CONVENTIONS rule 19.)
- **Depends on:** none
- **Evidence (2026-09-29, code commit `0ba7d5a`; `mlflow` is genuinely unimportable in this env — protobuf conflict):**
  - `python -c "import src.api.server"` → `IMPORT_OK Dynamic Pricing API`, **exit 0**. Logged `MLflow load failed. Falling back to local model. cannot import name 'service' from 'google.protobuf'`.
  - Forced-unavailable path: `python -c "import sys; sys.modules['mlflow']=None; sys.modules['mlflow.tracking']=None; import src.api.server"` → `IMPORT_OK_FORCED_NONE Dynamic Pricing API`, **exit 0**.
  - `python -m src.api.server` (port 8123) → `curl /v1/health` → **HTTP 200**, body `{"status":"healthy",...,"checks":{"model":{"status":"ok","loaded":true}}}`; server log shows the local-pickle fallback was taken. (`server.py` needed no edit — it only reaches `mlflow` via `router` → `engine` → `model_loader`; those are now lazy.)
  - No top-level unconditional `import mlflow` remains on the API import path: `grep -n "^import mlflow\|^from mlflow" src/` → no matches. The only remaining top-level mlflow imports are standalone scripts (`scripts/promote_model.py`, `scripts/train_with_tuning.py`), which are not on the API import path.
  - Side effect (root-cause fix, not a test workaround — CONVENTIONS rule 19): a plain `pytest tests/` now collects and passes — **21 passed, exit 0, 0 collection errors** (previously aborted at collection on `tests/test_api.py`'s mlflow import). R8's remaining work (conftest/`pytest.ini`, R6/R9 contract updates) is unaffected; R8 stays `todo`.
  - Existing suite unaffected: `pytest tests/ --ignore=tests/test_api.py -q` → 17 passed.

### R6 — One canonical search method name: `grid_search` (alias `grid`); legacy `"bayesian"` is rejected
- **Priority:** P0
- **Status:** done
- **Files touched:** `src/api/schemas.py`, `src/pricing/engine.py`, `src/pricing/optimizer.py`, `configs/config{,.dev,.prod}.yaml` (default-method honesty), `tests/test_api.py`, `tests/test_optimizer_real.py`
- **Acceptance criteria:** There is exactly one canonical search method, honestly named `grid_search`, with `grid` accepted as an alias (DECISIONS D2). `POST /v1/optimize-price` with each of `"grid_search"` and `"grid"` returns HTTP 200 and a price within the requested bounds. The legacy `"bayesian"` method is **rejected**: `"bayesian"` → HTTP 422 validation error, not 500 and not a deprecation-warning alias. Any other unknown method also returns HTTP 422, not 500. **Because R6 makes `grid_search` the only served optimizer, its correctness — not just its status code — must be verified:** for each bound pair in `(30,80)`, `(70,110)`, `(10,200)`, `(100,120)`, `(30,120)`, the served result's `expected_revenue` must be **≥ 0.99 ×** the maximum revenue over a **≥ 901-point** grid computed **at test time with the same model and the same bounds** (CONVENTIONS rule 34; no hardcoded reference). This requires raising `steps` / making it adaptive to the bound width, or reusing R1's dense-grid + local-refinement approach, so the default 50-point grid no longer undershoots wide ranges.
- **Depends on:** R2
- **Evidence (2026-09-29, code commit `b48d18a`, working-tree (gitignored) `models/demand_model.pkl`; references computed at test time per CONVENTIONS rule 34):**
  - **Implementation:** `src/api/schemas.py` now types `optimization_method` as `Literal["grid_search", "grid"]` with default `"grid_search"`, so `"bayesian"` and any unknown value fail Pydantic validation → **HTTP 422** (previously `"bayesian"` was the default and unknown values reached `engine.py`'s `ValueError` → HTTP 500). `src/pricing/engine.py` defaults to `"grid_search"`, dispatches only `grid`/`grid_search` to `PriceOptimizer`, and the `"bayesian"` branch, its now-unused `BayesianPriceOptimizer` import, and the dead `compare_methods()` were removed. `configs/*.yaml`'s unread `default_method` was corrected from `bayesian` to `grid_search` (naming honesty, rule 24).
  - **Steps-adaptation fix (the R2 caveat):** `PriceOptimizer` no longer takes a fixed 50-point grid. `_grid_points()` scales the candidate count with the bound width (target spacing `0.02`, floor `901` points, cap `20001`) and `optimize` now vectorizes `model.predict` over the whole grid in one call. `optimize_with_constraints` (margin floor + inventory cap) was added so the served method keeps the business-constraint contract that the retired `"bayesian"` path used to provide.
  - **R6 status codes** (`POST /v1/optimize-price`, `price_min=70, price_max=110`, via `TestClient`):

    | `optimization_method` | HTTP | notes |
    |---|---|---|
    | `"grid_search"` | **200** | body `optimization_method="grid_search"`, `optimal_price=77.36` |
    | `"grid"` | **200** | body `optimization_method="grid"`, `optimal_price=77.36` |
    | `"bayesian"` | **422** | Pydantic validation error (legacy method rejected) |
    | `"not-a-method"` | **422** | unknown value rejected (not 500) |
    | omitted | **200** | defaults to `"grid_search"` |

  - **R6 revenue ratio** — served result (method `grid_search`) vs a test-time 901-point reference, across the R1/R2 bounds:

    | bounds | served price | served revenue | 901-pt ref max | ratio | ≥ 0.99? |
    |---|---|---|---|---|---|
    | (30,80) | 77.3600 | 5950.398 | 5948.347 | **1.00034** | ✓ |
    | (70,110) | 77.3600 | 5950.398 | 5948.347 | **1.00034** | ✓ |
    | (10,200) | 200.0000 | 7562.641 | 7562.641 | **1.00000** | ✓ |
    | (100,120) | 120.0000 | 4471.819 | 4471.819 | **1.00000** | ✓ |
    | (30,120) | 77.3600 | 5950.398 | 5945.783 | **1.00078** | ✓ |

    All served prices are within their requested bounds. The pre-fix ratios from the R2 note (e.g. `(30,120)` 0.97145) no longer occur.
  - **Regression test + pre-fix failure (CONVENTIONS rule 18):** new `tests/test_optimizer_real.py::test_served_grid_optimizer_reaches_reference_optimum` is parametrized over all five bounds and asserts the served grid optimizer's `expected_revenue ≥ 0.99 ×` the test-time 901-point reference. Against the pre-fix `optimizer.py` (restored from `HEAD`) it **fails 2 of 5** — `(30,80)` (`5887.49 < 0.99×5948.35`) and `(30,120)` (`5776.03 < 0.99×5945.78`) — and passes 5/5 after the fix. `tests/test_api.py` asserts 200 for `grid`/`grid_search` and 422 for `bayesian`/unknown.
  - **Suite:** `pytest tests/` → **53 passed, 2 skipped**, 0 collection errors (the 2 skips are R7's bound-hugging cases). The only post-summary noise is the pre-existing `PredictionLogger.__del__` shutdown `ImportError` (STATE.md §5.11 / R17); it does not change the exit code.
  - **Left to their own items (not R6):** `app.py:128-132` still offers `"bayesian"` in its method selectbox (R10 fixes the UI contract; it will now get 422 for that option); `README.md:158,333`, `scripts/load_test.sh:46`, and `tests/smoke_tests.py:100,148` still carry the legacy string (R23/R14 respectively). `tests/smoke_tests.py` collects 0 tests, so none affect the suite.

### R7 — Real-model optimizer regression test (the test that would have caught the bug)
- **Priority:** P0
- **Status:** done
- **Files touched:** `tests/test_optimizer_real.py` (new)
- **Acceptance criteria:** The test loads the working-tree (gitignored) `models/demand_model.pkl` + `models/features.json` and asserts every condition in R1 and R2. All reference values are computed **at test time** from the loaded artifact and the given bounds — **no hardcoded numbers** — so the test is model-agnostic and remains valid after any retrain. It is demonstrated to **FAIL** against commit `c32841f` (or with R1/R2 temporarily reverted) and to **PASS** after R1/R2.
- **Note:** R7 must be **re-run after R12** (R12 retrains the model and changes the artifact that R7's reference is derived from).
- **Depends on:** R1, R2
- **Evidence (2026-09-29, working-tree (gitignored) `models/demand_model.pkl`; references computed at test time per CONVENTIONS rule 34):**
  - **New file:** `tests/test_optimizer_real.py` (15 tests). Loads the working-tree artifact via fixtures; the R1/R2 reference optimum is computed from the model on a 901-point grid built by a test-local *oracle* feature builder (`_serving_features`), deliberately independent of the optimizers' own `_build_features` so the reference cannot be circular. The only constants are request inputs (the standard `base_features`), the bound pairs, `REFERENCE_POINTS = 901`, `REVENUE_RATIO = 0.99`, `cost=60`, `min_margin_pct=0.15` — no model-derived numbers.
  - **PASS on current code:** `/home/arshiaask/projects/venv/bin/python -m pytest tests/test_optimizer_real.py -q` → **13 passed, 2 skipped** (the 2 skips are `(10,200)`/`(100,120)`, where the reference argmax genuinely lies on a bound, so the R1 bound-hugging rule does not apply). Covers R1 criteria 1–7 (revenue ratio, `optimization_success`, in-bounds, interiority, no `L-BFGS-B`/`minimize(`, result contract + `PricingResponse`, margin constraint) and R2 (complete 31-column frame + grid revenue ratio at `(70,110)`, `steps=50`).
  - **FAIL against the pre-fix code (demonstrated):** `git checkout c32841f -- src/pricing/bayesian_optimizer.py src/pricing/optimizer.py` then re-run → **7 failed, 6 passed, 2 skipped, exit code 1**, then restored to HEAD. Failures are exactly the R1/R2 bugs: `test_bayesian_reaches_reference_optimum[30.0-80.0|70.0-110.0|30.0-120.0]` (L-BFGS-B returns a bound/midpoint, revenue below the 0.99x reference), `test_bayesian_not_on_bound_when_reference_optimum_is_interior[30.0-80.0]`, `test_no_gradient_method_remains_on_tree_objective` (`L-BFGS-B` present), `test_grid_optimizer_builds_complete_feature_frame` (`AttributeError: 'PriceOptimizer' object has no attribute '_build_features'`), and `test_grid_optimizer_reaches_reference_optimum` (`KeyError: "['price_advantage', 'log_price', 'log_comp_price', 'price_advantage_sin', 'price_change_1d', 'price_change_7d', 'roll_mean_price_7', 'roll_mean_price_14', 'roll_mean_price_28'] not in index"` — the exact STATE.md §5.1 symptom). The `(10,200)`/`(100,120)` Bayesian cases correctly still pass pre-fix because their true optimum is on the bound.
  - Existing suite unaffected: `pytest tests/ -q` → **34 passed, 2 skipped**.

### R8 — Default `pytest tests/` collects and passes
- **Priority:** P0
- **Status:** done
- **Files touched:** `tests/test_api.py`, `tests/conftest.py` (new), `pytest.ini`
- **Acceptance criteria:** `pytest tests/` (no flags) exits 0 with 0 collection errors and ≥ 20 tests. The mlflow-dependent import in `tests/test_api.py` no longer aborts collection.
- **Depends on:** R3
- **Evidence (2026-09-29, code commit; venv `/home/arshiaask/projects/venv`):**
  - **Plain run:** `/home/arshiaask/projects/venv/bin/pytest tests/` → **exit 0**, `34 passed, 2 skipped`, **0 collection errors**; `--collect-only` → **36 tests collected** (≥ 20 ✓). The 2 skips are R7's bound-hugging cases where the optimum is genuinely on a bound.
  - **mlflow-independent collection:** `grep -rn "mlflow" tests/` → **no matches**; the module-level `src.api.server` import (the old collection-abort path) is removed from `tests/test_api.py`. Forced-unavailable run `python -c "import sys; sys.modules['mlflow']=None; sys.modules['mlflow.tracking']=None; import pytest; raise SystemExit(pytest.main(['tests/','-q']))"` → **34 passed, 2 skipped, exit 0** — collection and execution no longer depend on mlflow.
  - **Changes:** `tests/conftest.py` (new) bootstraps the repo root onto `sys.path` and provides the shared `client` fixture, importing the app lazily so a heavy dependency cannot break collection of unrelated files (CONVENTIONS rule 19); `tests/test_api.py` drops its local `client` fixture and module-level app import; `pytest.ini` adds `--strict-config` so a malformed config fails the default run instead of being silently ignored.
  - **Known, unrelated pre-existing noise (not R8):** `PredictionLogger.__del__` raises `ImportError: sys.meta_path is None` at interpreter shutdown (STATE.md §5.11, ROADMAP R17). It prints after the summary and does **not** change the exit code (still 0).

### R9 — API contract + grid-path integration test
- **Priority:** P0
- **Status:** done
- **Files touched:** `tests/test_api.py`
- **Acceptance criteria:** Test asserts HTTP 200 for both `grid_search` and `grid`, and HTTP 422 for the legacy `"bayesian"` method; the response contains `optimal_price`, `expected_demand`, `expected_revenue`, `optimization_method`; the price is within the requested `[price_min, price_max]`; `grid_search` revenue ≥ 0.99 × the vectorized optimum computed **at test time with the same model and bounds** (no hardcoded reference).
- **Depends on:** R6, R8
- **Evidence (2026-09-29, commit `bc2f674`, working-tree (gitignored) `models/demand_model.pkl`; reference computed at test time per CONVENTIONS rule 34):**
  - **`tests/test_api.py::test_grid_path_response_contract`** — `grid_search` and `grid` → **HTTP 200**; the body contains `optimal_price`, `expected_demand`, `expected_revenue`, `optimization_method`; the method is echoed; `70 ≤ optimal_price ≤ 110`; the body validates against `PricingResponse`. Legacy `"bayesian"` → **HTTP 422**.
  - **`tests/test_api.py::test_grid_path_reaches_reference_optimum`** — served `grid_search` `expected_revenue` **5950.3983** vs a test-time 901-point reference max **5948.3471** (ratio **1.00034 ≥ 0.99**). The reference is built from the *served* model (`engine.model`) and the requested bounds through an independent oracle feature builder (`_oracle_serving_features`, deliberately not the shared `build_serving_features`), so it is not circular and contains no hardcoded model-derived number.
  - **Observed (TestClient):** `grid_search` → 200 `optimal_price=77.3600, expected_demand=76.9183, expected_revenue=5950.3983`; `grid` → 200 same; `bayesian` → 422.
  - **Suite:** `pytest tests/test_api.py` → **9 passed**; full `pytest tests/` → **60 passed, 2 skipped**, 0 collection errors.

### R10 — Fix the Streamlit ↔ API response contract
- **Priority:** P0
- **Status:** done
- **Files touched:** `app.py:203,207,227,229,230,373`, `app.py:369-375`
- **Acceptance criteria:** With the API running, the Quick tab renders Optimal Price / Predicted Demand / Est. Revenue with no `KeyError`. `app.py` sends the canonical `grid_search` method (not a rejected legacy string). A test asserts `set(keys read by app.py) ⊆ set(PricingResponse.model_fields)`, so any future field rename fails CI.
- **Depends on:** R6
- **Evidence (2026-09-29, commit `bfa06eb`, live API on `:8000`):**
  - **Field fix:** `app.py` now reads `expected_demand` (Quick-tab metrics, details table, batch results). `grep -n "predicted_demand" app.py` → no field reads remain.
  - **Method fix:** the selectbox offers `["grid_search", "grid"]` only; the rejected legacy `"bayesian"` is gone, and the Advanced/About copy no longer advertises Bayesian optimization.
  - **Rendering (AppTest, live API):** ran `app.py` via `streamlit.testing.v1.AppTest`, clicked "🚀 Optimize Price" → no `at.exception`, no `st.error`; metrics rendered `💰 Optimal Price $77.36`, `📈 Profit Margin 22.4%`, `📊 Predicted Demand 77 units`, `💵 Est. Revenue $5,930`.
  - **Contract test (new `tests/test_streamlit_contract.py`):** `test_app_reads_only_pricing_response_fields` parses `app.py` as source and asserts every `result[...]` key is a `PricingResponse` field (and that `expected_demand` is read, `predicted_demand` is not); `test_app_offers_only_accepted_optimization_methods` asserts the selectbox options ⊆ the accepted `Literal` and exclude `"bayesian"`. `pytest tests/test_streamlit_contract.py` → **4 passed** at this commit.

---

## P1 — Honesty, correctness, and operability

*(R4, R5, R11–R14 were moved here from P0 on 2026-09-28 — they are not on the critical path for making the core true and the suite runnable.)*

### R4 — One canonical serving feature builder shared by both optimizers
- **Priority:** P1
- **Status:** done
- **Files touched:** `src/pricing/features.py` (new), `src/pricing/bayesian_optimizer.py`, `src/pricing/optimizer.py`, `tests/test_serving_features.py` (new), `tests/test_optimizer_real.py` (R2 test retargeted to the shared builder)
- **Acceptance criteria:** A unit test passes the same `(base_features, price)` to both optimizers and asserts (a) identical ordered feature vectors (same 31 columns, same values) and (b) identical `model.predict` output. Exactly one function computes price-dependent serving features; neither optimizer builds its own ad-hoc dict.
- **Depends on:** R1, R2
- **Evidence (2026-09-29, working-tree (gitignored) `models/demand_model.pkl` + `models/features.json`):**
  - **New module** `src/pricing/features.py::build_serving_features(base_features, price, feature_columns=None)` is the only function that computes price-dependent serving features; when `feature_columns` is given it returns exactly the committed `models/features.json` columns in order.
  - **Both optimizers consume it:** `src/pricing/optimizer.py:4,21` and `src/pricing/bayesian_optimizer.py:14,137,147` import and call `build_serving_features`; the per-optimizer `_build_features` methods (the R2 interim duplication) are deleted. `grep -n "price_advantage_sin\|log_comp_price" src/pricing/optimizer.py src/pricing/bayesian_optimizer.py` → **no matches** (no ad-hoc dict remains).
  - **R4(a) identical ordered feature vectors:** `tests/test_serving_features.py::test_both_optimizers_feed_identical_ordered_feature_vectors` drives both optimizers over a degenerate `[77.0, 77.0]` range with a recording model and asserts the exact frames fed to `predict` have the same index (`list(...) == list(real_feature_columns)`, 31 columns) and identical values. **PASSED.**
  - **R4(b) identical predictions:** `test_both_optimizers_produce_identical_model_predictions` asserts `real_model.predict(grid_frame)[0] == real_model.predict(bayesian_frame)[0]` and that `expected_demand`/`expected_revenue` are equal. **PASSED.**
  - `test_exactly_one_function_computes_price_dependent_features` asserts neither optimizer source assigns the ad-hoc keys and both reference the shared builder. `test_serving_builder_covers_committed_columns_in_order` asserts the builder returns the 31 committed columns in order. **PASSED.**
  - **No behavioral drift:** direct re-run against the working-tree model — `BayesianPriceOptimizer.optimize(base,70,110)` → `77.372484` / revenue `5951.359`; `PriceOptimizer.optimize(base,70,110,50)` → `77.346939` / `5949.394` — identical to the R1/R2 STATE.md values.
  - **Suite:** `pytest tests/test_serving_features.py -v` → **4 passed**; `pytest tests/` → **38 passed, 2 skipped** (was 34+2; +4 R4 tests), 0 collection errors. R2's `test_grid_optimizer_builds_complete_feature_frame` was retargeted to the shared builder (R2's criterion — the complete 31-column frame — is unchanged and still asserted).

### R5 — Correct and loud MLflow registry resolution (and fix `promote_model.py`)
- **Priority:** P1
- **Status:** done
- **Files touched:** `src/pricing/engine.py`, `scripts/promote_model.py`, `src/monitoring/health_checker.py`, `src/api/router.py:111-120`, `tests/test_mlflow_registry.py` (new). Environment: `protobuf==4.25.9` + `setuptools<81` installed into the venv so `mlflow` 2.12.1 imports (see STATE.md).
- **Acceptance criteria:** (a) When no Production stage/alias exists, the engine logs at **ERROR** (not WARNING) and exposes the active model source (e.g. `/v1/health` reports `checks.model.source == "local"`). (b) `scripts/promote_model.py` uses alias-based APIs (`set_registered_model_alias` / `set_model_version_tag`) with zero deprecated calls (`get_latest_versions`, `transition_model_version_stage`). (c) After running `promote_model.py`, the engine loads the registry model (non-null `model_version`) — verified by a test.
- **Depends on:** R3
- **Evidence (2026-09-29, isolated temp file-store registry; working-tree (gitignored) `models/demand_model.pkl`):**
  - **Environment unblock (root-cause, not a workaround — CONVENTIONS rule 19):** `mlflow` 2.12.1 was unimportable (protobuf 7.35.1 removed `google.protobuf.service`; setuptools 82 removed `pkg_resources`). Installed `protobuf==4.25.9` + `setuptools<81` into the venv; `import mlflow` now succeeds. The engine bounds registry calls (`MLFLOW_HTTP_REQUEST_TIMEOUT=5`, `MLFLOW_HTTP_REQUEST_MAX_RETRIES=1` via `os.environ.setdefault`) so a dead tracking server fails fast instead of hanging the 30s request timeout (the pre-hardening behaviour was a 504 after ~194s — reproduced under a shim).
  - **R5(a):** direct run against a registry with a registered version but **no** production alias →
    `ERROR src.pricing.engine: No Production version or 'production' alias found in the MLflow registry for 'demand_forecasting_model'. Falling back to the local artifact models/demand_model.pkl.` → `source=local, version=None`. `GET /v1/health` → **HTTP 200**, `checks.model = {'status': 'ok', 'loaded': True, 'source': 'local'}`.
  - **R5(b):** `grep -rn "get_latest_versions\|transition_model_version_stage" src/ scripts/` → **no matches**. `promote_model.py` uses `client.set_registered_model_alias(...)` + `client.set_model_version_tag(..., "stage", "Production")` and `search_model_versions` (not deprecated).
  - **R5(c):** after `promote_model()` → `Loading model version 1 from MLflow registry` → engine `source=mlflow, version='1'` (non-null). Covered by `tests/test_mlflow_registry.py::test_engine_loads_registry_model_after_promotion`.
  - **Tests:** `pytest tests/test_mlflow_registry.py -v` → **4 passed** (`test_engine_serves_local_when_no_production_alias`, `test_engine_loads_registry_model_after_promotion`, `test_promote_model_uses_alias_apis_only`, `test_health_exposes_active_model_source`); the module `pytest.importorskip("mlflow")`s so it skips cleanly if mlflow is absent. `pytest tests/` → **42 passed, 2 skipped**, 0 collection errors, no 504/hang.
  - Note: with mlflow importable, `MLFLOW_TRACKING_URI` still defaults to `http://localhost:5000` (no server here), so the engine logs the ERROR and serves local — the intended R5 behaviour.

### R11 — Remove the hardcoded fake Advanced-tab response
- **Priority:** P1
- **Status:** done
- **Files touched:** `app.py:304-316`
- **Acceptance criteria:** `grep -n "confidence_interval\|optimization_metadata" app.py` returns nothing. The Advanced tab shows either the live OpenAPI schema (`/openapi.json`) or a real response from a live call. A test asserts those fabricated keys never appear in the UI source.
- **Depends on:** none
- **Evidence (2026-09-29, commit `b7abaff`, live API on `:8000`):**
  - `grep -n "confidence_interval\|optimization_metadata" app.py` → **no matches** (the `example_response` dict is removed).
  - The Advanced tab now fetches the running API's `/openapi.json` and renders the live `PricingResponse` schema; if the API is unreachable it shows an informational message instead of invented data.
  - **AppTest:** the Advanced tab renders the live schema — properties `optimal_price`, `expected_demand`, `expected_revenue`, `optimization_method`, `profit_margin`, `total_profit`, …; no `confidence_interval`/`optimization_metadata`.
  - **Test:** new `tests/test_streamlit_contract.py::test_app_contains_no_fabricated_response_keys` asserts `confidence_interval`, `optimization_metadata`, and `example_response` never appear in the UI source. `pytest tests/test_streamlit_contract.py` → **5 passed** at this commit.

### R12 — Honest temporal train/validation split + `product_id` handling
- **Priority:** P1
- **Status:** done
- **Files touched:** `src/training/dataset.py:34-44`, `src/features/feature_builder.py:109-126`, `src/training/pipeline.py`, `scripts/train_with_tuning.py`, `configs/config.yaml:31-32` (+ `configs/config.{dev,prod}.yaml`), `tests/test_training_data.py` (new), `models/features.json` (regenerated)
- **Acceptance criteria:** The split is chronological — a test asserts `max(train.date) < min(val.date)` (no `shuffle=True`). `product_id` is removed from the model feature list (or replaced by an out-of-fold target encoding with no leakage; assert no target leakage). `reports/training_metrics.json` is regenerated and contains both `R2` and `MAPE`.
- **Note:** This item retrains the model, changing the working-tree (gitignored) artifact. **Re-run R7 after R12** — R7's references are recomputed at test time, so it must be re-run rather than left as a stale pass.
- **Depends on:** D5, D6 (both `accepted` 2026-09-30, commit `b3ecf90`)
- **Evidence (2026-09-30, code commit `47162d3`; retrained on the same raw CSV, features rebuilt from it):**
  - **Chronological split (D6).** `DatasetBuilder.split(X, y, dates)` sorts by `date` (stable) and holds out the most recent `test_size` fraction; whole calendar days are kept together so no date appears in both sets. Observed on the regenerated parquet: **train 13,200 rows 2023-02-05 … 2023-10-26**, **validation 3,300 rows 2023-10-27 … 2023-12-31**; `max(train.date) < min(val.date)` → **True**; overlap dates → `[]`. `grep -n "shuffle=True\|train_test_split" src/training/dataset.py` → **no matches**. `test_size` is read from `configs/config.yaml`; the obsolete `training.random_state` key was removed from `config.yaml`/`config.dev.yaml`/`config.prod.yaml`.
  - **`product_id` removed (D5).** `FeatureBuilder` still groups the lag/rolling features by `product_id` but no longer emits it; `models/features.json` is regenerated with **30 columns (was 31)**, no `product_id`; `DatasetBuilder.build` excludes it; the served model has `n_features_in_ == 30`. `test_product_id_is_not_a_model_feature` PASS. No target leakage: the feature list contains neither `y_units_sold` nor `units_sold`, and lag/rolling features are built with `.shift(1)` (no `.shift(0)`); `test_no_target_leakage` PASS.
  - **Regenerated metrics (R2 + MAPE, no carried-over numbers).** `reports/training_metrics.json`: **R2 = 0.47498**, **MAPE = 0.34581**, MAE = 21.44, RMSE = 30.05, Directional_Accuracy = 0.7587, Train_R2 = 0.88029. (Previous artifact: R2 = 0.4682, MAPE = 0.4015.) `test_training_metrics_report_r2_and_mape` PASS.
  - **New tests:** `tests/test_training_data.py` (5 tests) → **5 passed** (`test_split_is_chronological`, `test_split_does_not_shuffle`, `test_product_id_is_not_a_model_feature`, `test_no_target_leakage`, `test_training_metrics_report_r2_and_mape`). They skip (not error) when the gitignored parquet/report is absent.
  - **Suite:** `pytest tests/` → **65 passed, 2 skipped**, 0 collection errors (was 60+2; +5 R12 tests). The 2 skips are R7's bound-hugging cases. Only post-summary noise is the pre-existing `PredictionLogger.__del__` shutdown `ImportError` (STATE §5.11 / R17).
  - **R7 re-run after the retrain (see R7 note):** `pytest tests/test_optimizer_real.py -q` → **18 passed, 2 skipped** (references recomputed at test time from the new artifact). Fresh ratios vs a test-time 901-point reference: served grid `(30,80)` **1.00006**, `(70,110)` **0.99673**, `(10,200)` **1.00000**, `(100,120)` **1.00000**, `(30,120)` **1.00078** — all ≥ 0.99; Bayesian optimizer all ≥ 0.99 with `optimization_success=True`. Served API `grid_search` `(70,110)` → `optimal_price=77.06, expected_revenue=6152.54`.
  - **Not committed (by repo convention):** `models/demand_model.pkl`, `reports/*.json|csv`, and `data/features/*.parquet` are gitignored (`.gitignore:45,51,60-61`); they are regenerated in the working tree, not tracked. The tracked model contract `models/features.json` is committed in `47162d3`.

### R13 — Health check validates the actually-served model type
- **Priority:** P1
- **Status:** done
- **Files touched:** `src/monitoring/health_checker.py:36-51`, `src/api/router.py:111-120`, `tests/test_health_model_type.py` (new)
- **Acceptance criteria:** With a native `XGBRegressor` **and** with an `mlflow.pyfunc`-wrapped model, `GET /v1/health` returns 200 and `checks.model.status == "ok"`. No hardcoded `10`-column fallback (`getattr(model, "n_features_in_", 10)`) remains.
- **Depends on:** R3
- **Evidence (2026-09-29, working-tree (gitignored) `models/demand_model.pkl` + `models/features.json`):**
  - **Fix:** the probe now derives its width from the *served feature list* (`health_checker.py::_probe_model`, passed `engine.feature_columns` by `router.py:114-119`) and predicts on a zero-row `DataFrame` of those columns — accepted by both a native `XGBRegressor` and a `pyfunc` wrapper. The hardcoded fallback is gone: `grep` for `getattr(model, "n_features_in_", 10)` / `n_features_in_", 10` → **no matches**.
  - **Pre-fix failure (CONVENTIONS rule 18), reproduced:** with the old probe, a pyfunc model (no `n_features_in_`) → `{'status': 'error', 'loaded': True, 'error': 'Feature shape mismatch, expected: 31, got 10'}` and overall `degraded` (→ HTTP 503). New probe on the same model → `{'status': 'ok', 'loaded': True}` / `healthy`.
  - **Tests:** `pytest tests/test_health_model_type.py -v` → **3 passed** — `test_health_ok_with_native_xgboost` (HTTP 200, `status == "ok"`), `test_health_ok_with_pyfunc_model` (asserts the wrapper has no `n_features_in_`, then HTTP 200, `status == "ok"`, `source == "mlflow"`), `test_no_hardcoded_feature_width_fallback`. The pyfunc case builds the wrapper with `mlflow.xgboost.save_model` + `mlflow.pyfunc.load_model` (no registry needed) and `pytest.importorskip("mlflow")`s.
  - **Suite:** `pytest tests/` → **45 passed, 2 skipped**, 0 collection errors. R4 and R5 tests re-run together with R13: `pytest tests/test_serving_features.py tests/test_optimizer_real.py tests/test_mlflow_registry.py tests/test_health_model_type.py -q` → **24 passed, 2 skipped**.

### R14 — Convert smoke tests into a collectable pytest module
- **Priority:** P1
- **Status:** done
- **Files touched:** `tests/smoke_tests.py`, `scripts/run_smoke_tests.sh`, `README.md:174`
- **Acceptance criteria:** `pytest tests/smoke_tests.py` collects ≥ 8 tests. Against a locally started API they pass; when no API is reachable they **skip** (not error) via a fixture. The README's smoke-test command is updated.
- **Depends on:** R8
- **Evidence (2026-10-15, code commit `47ea3d6`):**
  - **Before:** `pytest tests/smoke_tests.py --collect-only -q` → **0 items collected, exit 5** (class `SmokeTestRunner` held methods, not module-level `test_*`).
  - **Change:** removed the `SmokeTestRunner` class and its `__main__` runner (no duplicate execution path); the 8 checks are now module-level `test_*` functions sharing a module-scoped `api_base_url` fixture. The fixture probes `/v1/health` **once** with a 2 s timeout (no retry loop) and calls `pytest.skip(reason)` on `requests.RequestException`; base URL from `API_URL` (default `http://localhost:8000`). The two payloads that sent `"optimization_method": "bayesian"` now send `"grid_search"` (D2 rejects `"bayesian"` with 422). `scripts/run_smoke_tests.sh` now runs `pytest tests/smoke_tests.py -v` (its API-readiness `curl` wait is unchanged; it does not use docker). `README.md:174` → `API_URL=http://localhost:8000 pytest tests/smoke_tests.py -v`.
  - **After (a) collect:** `pytest tests/smoke_tests.py --collect-only -q` → **8 tests collected** (`test_health_endpoint`, `test_readiness_endpoint`, `test_liveness_endpoint`, `test_metrics_endpoint`, `test_optimize_price_basic`, `test_optimize_with_constraints`, `test_response_time`, `test_invalid_input`).
  - **After (b) offline skip:** `API_URL=http://127.0.0.1:59999 pytest tests/smoke_tests.py -q -rs` → **8 skipped, exit 0** (each with reason `API not reachable at http://127.0.0.1:59999 (ConnectionError); start the API and/or set API_URL`); no errors.
  - **After (c) live API:** started `python -m src.api.server` from the repo root with `API_HOST=127.0.0.1 API_PORT=8765 API_WORKERS=1 API_RELOAD=false MLFLOW_TRACKING_URI=sqlite:////tmp/smoke_mlflow.db`; `/v1/health` → **200** after 3 s; `API_URL=http://127.0.0.1:8765 pytest tests/smoke_tests.py -v` → **8 passed in 0.47 s**. Server then killed; `ss -ltn | grep 8765` → nothing listening; `git status --short` shows no `mlflow.db`/`mlruns` created.
  - **Default-discovery answer:** `pytest.ini` sets `python_files = test_*.py`, which does **not** match `smoke_tests.py`, so a plain `pytest tests -q` does **not** collect it (`pytest tests --collect-only -q | grep -c smoke_tests` → 0). No `pytest.ini` change was needed (and none made).
  - **Suite:** `pytest tests -q` → **103 passed, 2 skipped** (unchanged; smoke tests are outside default discovery). `bash -n scripts/run_smoke_tests.sh` → exit 0.

### R15 — Drift detection: wire it to real traffic or delete it (no third state)
- **Priority:** P1
- **Status:** done
- **Files touched:** `src/monitoring/model_monitor.py` (deleted), `tests/test_data_drift.py` (deleted), `README.md` (option (b) chosen; `src/api/router.py` **not** touched)
- **Acceptance criteria:** Either (a) a real caller exists (endpoint `GET /v1/drift` or `scripts/check_drift.py`) with a test that feeds known-shifted data and asserts `drift_detected == True` and known-stable data asserts `False`; or (b) `model_monitor.py` and `tests/test_data_drift.py` are deleted and every README "drift detection" claim is removed. A README claim may not exist without a passing test.
- **Depends on:** R8
- **Decision: option (b) — delete.** Rationale (effort/value): a real caller would need a stable reference distribution (the training features parquet is gitignored and regenerated, so not reliably present), a real traffic-feature source, and a new endpoint/script plus shift-vs-stable tests — yet `ModelMonitor.calculate_drift` is only a normalized mean/std heuristic with **no** statistical test or p-value, so wiring it and calling it "drift detection" would still risk CONVENTIONS rule 24. For a synthetic-data demo with no actuals feedback loop there is no real value to wire; deletion is the honest, low-risk path and matches DECISIONS D13's default ("unless a real consumer is built instead").
- **Evidence (2026-10-07, code commit `2746fa8`):**
  - **Files deleted:** `src/monitoring/model_monitor.py` and `tests/test_data_drift.py` (the latter asserted `pvalue < 0.01`, i.e. that drift *exists* in random synthetic data — CONVENTIONS rule 15).
  - **No dangling references:** `grep -rn "model_monitor\|ModelMonitor" --include=*.py .` → **no matches**.
  - **README drift claims struck:** `grep -rni "drift" README.md` → **no matches** (pre-fix it matched the "Complete Monitoring" bullet, the "Model Monitoring" bullet, the config `monitoring:` example, and the `# Check data drift` troubleshooting line). The dead config example's `monitoring:` block was removed with it.
  - **Suite:** `pytest tests/` → **65 passed, 2 skipped**, 0 collection errors (67 collected; −1 `test_data_drift`, +1 R16 test vs the pre-session 67).
  - **Left to R18 (config hygiene, not R15):** `configs/config{,.dev,.prod}.yaml` still carry the unread `monitoring:` block (`drift_threshold` etc.); STATE.md §4 already flags it as never-read and R18 owns deleting or wiring it.

### R16 — Stop leaking internal error strings from the API
- **Priority:** P1
- **Status:** done
- **Files touched:** `src/api/router.py:91-113`, `tests/test_api.py`
- **Acceptance criteria:** A forced optimizer failure returns HTTP 500 whose body contains a generic message and `request_id` only. A test asserts the body contains none of `{"KeyError", "not in index", "Traceback"}`.
- **Depends on:** R8
- **Evidence (2026-10-07, code commit `85f5944`):**
  - **Fix:** `router.py`'s `except Exception` block no longer does `raise HTTPException(status_code=500, detail=str(e))`. It logs the real exception server-side (`logger.error("Pricing optimization failed (request_id: ...): ...")`) and returns `JSONResponse(status_code=500, content={"message": "An internal error occurred while processing the request.", "request_id": request_id})` — a generic message plus `request_id` only (CONVENTIONS rule 11 / DECISIONS D21).
  - **Pre-fix failure reproduced (rule 18):** with `router.py` restored from `HEAD`, `test_optimizer_failure_returns_generic_error` **FAILS** — the body is `{'detail': '"[\'price_advantage\', \'log_comp_price\'] not in index"'}` (raw `KeyError` text leaked). After the fix it **passes**.
  - **Test:** new `tests/test_api.py::test_optimizer_failure_returns_generic_error` monkeypatches `engine.get_optimal_price` to raise `KeyError("['price_advantage', 'log_comp_price'] not in index")`, posts to `/v1/optimize-price`, and asserts HTTP **500**, a non-empty `request_id` and a `message`, and that the response text contains none of `KeyError` / `not in index` / `Traceback`.
  - **Suite:** `pytest tests/test_api.py` → **10 passed** (was 9). Full `pytest tests/` → **66 passed, 2 skipped**, 0 collection errors (was 65+2).

### R17 — Fix the `PredictionLogger` shutdown crash
- **Priority:** P1
- **Status:** done
- **Files touched:** `src/monitoring/prediction_logger.py:19-28` (atexit registration), `tests/test_prediction_logger.py` (new)
- **Acceptance criteria:** Interpreter exit produces no `ImportError: sys.meta_path is None, Python is likely shutting down` traceback. A test flushes via `atexit` and asserts buffered entries were written to disk.
- **Depends on:** none
- **Evidence (2026-10-07, code commit `42c4d68`):**
  - **Fix:** removed `PredictionLogger.__del__` (which called `flush()` — I/O — during teardown) and registered the flush with `atexit` in `__init__` (`atexit.register(self.flush)`). atexit callbacks run before module teardown / before `sys.meta_path` is cleared, so the final flush is safe (CONVENTIONS rule 13).
  - **New tests `tests/test_prediction_logger.py` (3):** `test_no_io_in_del` asserts `"__del__" not in PredictionLogger.__dict__`; `test_atexit_flushes_buffered_entries` captures the atexit callback and asserts the buffered entry (below `batch_size`) is written to disk only after the callback runs; `test_interpreter_exit_has_no_shutdown_importerror` runs a real `python -c` subprocess, asserts exit 0, asserts stderr contains no `sys.meta_path is None`, and asserts the buffered entry was flushed at exit.
  - **Pre-fix failure reproduced (rule 18):** with `prediction_logger.py` restored from `HEAD`, all three tests **FAIL** (`__del__` present; no atexit registration; nothing flushed at exit). After the fix: `pytest tests/test_prediction_logger.py -v` → **3 passed**.
  - **Crash gone at interpreter exit:** the pre-session `pytest tests/` printed `Exception ignored in: <function PredictionLogger.__del__ ...> ImportError: sys.meta_path is None, Python is likely shutting down` after the summary; after the fix, a full `pytest tests/` run prints no such traceback.
  - **Suite:** `pytest tests/` → **68 passed, 2 skipped**, 0 collection errors (was 65+2; +1 R16, −1 R15, +3 R17).

### R18 — Config: every YAML key is read, or removed
- **Priority:** P1
- **Status:** done
- **Files touched:** `configs/config.yaml`, `configs/config.dev.yaml`, `configs/config.prod.yaml`, `tests/test_config.py` (new)
- **Acceptance criteria:** A test enumerates every key in `configs/*.yaml` and fails if any key is not referenced in `src/` (with an explicit, documented allowlist). The `api:`, `monitoring:`, and `logging:` blocks are either consumed by code or deleted. STATE.md §4 must be empty of "defined but never read" entries.
- **Depends on:** R3
- **Evidence (2026-10-08, code commit `97a4f8c`):**
  - **New test `tests/test_config.py`** enumerates every dotted leaf key across `configs/*.yaml` and asserts each leaf name appears as a string literal in `src/` or `scripts/` (the API + training entry points). Explicit `ALLOWLIST` (empty; every entry must carry a reason). `pytest tests/test_config.py` → **4 passed**.
  - **Pre-fix failure reproduced (rule 18):** against the `HEAD` configs the test **fails 2/4** — 63 unread keys listed (`config.dev.yaml:api.cors_enabled`, `…:monitoring.enabled`, `…:logging.rotation`, `config.yaml:pricing.default_method`, `…:data.raw_path`, …) and `test_unread_runtime_blocks_are_deleted` fails on `config.dev.yaml still has an unread monitoring: block`. After the fix → **4 passed**.
  - **Deleted (no reader in `src/`/`scripts/`):** the whole `api:` (10 keys) and `logging:` (4 keys) blocks in dev/prod (runtime toggles come from env vars via `EnvConfig`; DECISIONS D11); the orphaned `monitoring:` block (5 keys; its only consumer `model_monitor.py` was deleted in R15); `data.raw_path`/`data.processed_path`; `model.demand_model`; `pricing.price_min_multiplier`/`price_max_multiplier`/`price_steps`/`default_method`; `training.cv_folds`/`run_hyperparameter_tuning`; `features.raw_filename`/`feature_filename` (read only by the dead `feature_pipeline.py`, which `uses .get(..., default)` so nothing breaks; R22 will delete that module).
  - **Kept (read):** `data.feature_path`; `model.{n_estimators,max_depth,learning_rate,subsample,colsample_bytree,min_child_weight,gamma,reg_alpha,reg_lambda}`; `pricing.{model_path,feature_columns_path,price_min,price_max}`; `training.{test_size,model_dir,report_dir,run_cv,tuning_trials}` (`tuning_trials` read by `scripts/train_with_tuning.py:87`); `features.{lag_days,rolling_windows,min_history_days}`.
  - **No behavior change:** API still starts and serves — `GET /v1/health` → 200 `checks.model={'status':'ok','loaded':True,'source':'local'}`; `POST /v1/optimize-price` (`grid_search`, 70–110) → 200 `optimal_price=77.06`.
  - **Suite:** `pytest tests/` → **72 passed, 2 skipped** (was 68+2; +4 R18 tests).

### R19 — Env: every `.env` var is read, or removed; add `.env.example`
- **Priority:** P1
- **Status:** done
- **Files touched:** `.env` (gitignored; cleaned in the working tree), `.env.example` (new), `tests/test_env.py` (new)
- **Acceptance criteria:** A test enumerates `.env` keys and fails on any unused var. Decorative vars from STATE.md §4 are removed. `.env.example` lists exactly the variables the code reads (and nothing else).
- **Depends on:** R18
- **Evidence (2026-10-08, code commit `3bb3aef`):**
  - **Read set (derived by scanning `src/`, 14 vars):** `APP_ENV`, `API_HOST`, `API_PORT`, `API_WORKERS`, `API_RELOAD`, `CORS_ENABLED`, `CORS_ORIGINS`, `RATE_LIMIT_ENABLED`, `RATE_LIMIT_REQUESTS`, `REQUEST_TIMEOUT`, `LOG_LEVEL`, `LOG_FORMAT`, `LOG_DIR`, `MLFLOW_TRACKING_URI`. (`CORS_ENABLED` was previously read but undocumented in STATE.md §4.)
  - **New `.env.example`** lists exactly those 14 (committed; `.env` itself is gitignored — `.gitignore:65`). The local `.env` is rewritten in the working tree to the same 14.
  - **Removed decorative vars** (~23): `APP_NAME`, `APP_VERSION`, `DEBUG`, `CORS_ALLOW_CREDENTIALS`, `RATE_LIMIT_WINDOW`, `DATABASE_URL`, `DATABASE_BACKUP_ENABLED`, `DATABASE_BACKUP_INTERVAL`, `DATABASE_BACKUP_RETENTION_DAYS`, `MODEL_PATH`, `FEATURES_PATH`, `MODEL_CACHE_ENABLED`, `MODEL_RELOAD_INTERVAL`, `LOG_ROTATION`, `LOG_RETENTION_DAYS`, `MONITORING_ENABLED`, `METRICS_ENABLED`, `HEALTH_CHECK_INTERVAL`, `PREDICTION_LOG_ENABLED`, `PREDICTION_LOG_DIR`, `PREDICTION_LOG_BATCH_SIZE`, `MODEL_INFERENCE_TIMEOUT`, `CACHE_TTL`, `ALERT_ERROR_THRESHOLD`, `MLFLOW_EXPERIMENT_NAME`, `STREAMLIT_SERVER_*`. Shell-script vars (`API_URL`, `CONCURRENT_REQUESTS`, `TOTAL_REQUESTS`, `BACKUP_DIR`) all have `${VAR:-default}` fallbacks and are not app runtime config.
  - **New `tests/test_env.py`** derives the read set by scanning `src/` for `os.getenv` / `get_bool` / `get_int` / `get_env` / `os.environ` and asserts `.env.example` == read set and `.env` ⊆ read set (skips if `.env` absent). `pytest tests/test_env.py` → **2 passed**.
  - **Pre-fix failure reproduced (rule 18):** with the original `.env` and no `.env.example`, both tests **fail** — `.env.example is missing` and `.env defines variables no src/ code reads: ['APP_NAME', 'APP_VERSION', 'CORS_ALLOW_CREDENTIALS', 'DATABASE_URL', 'DEBUG', 'LOG_RETENTION_DAYS', 'LOG_ROTATION', 'MLFLOW_EXPERIMENT_NAME', 'MODEL_PATH', 'MONITORING_ENABLED', 'PREDICTION_LOG_ENABLED', 'RATE_LIMIT_WINDOW', 'STREAMLIT_SERVER_PORT']`. After → **2 passed**.
  - **Suite:** `pytest tests/` → **74 passed, 2 skipped** (was 72+2; +2 R19 tests).

### R20 — Log rotation: implement it or delete the claim
- **Priority:** P1
- **Status:** done
- **Files touched:** `src/utils/logger.py`, `src/api/server.py`, `tests/test_log_rotation.py` (new), `.env.example` (+ the gitignored `.env` in the working tree)
- **Acceptance criteria:** Either `RotatingFileHandler`/`TimedRotatingFileHandler` is configured from env, with a test that writes past the size limit and asserts a rotated `.1` file appears; or the rotation claims and `LOG_ROTATION`/`LOG_RETENTION_DAYS` are removed from README and `.env`.
- **Depends on:** R19
- **Decision: implement rotation** (first branch). Rationale (effort/value): it is a small, well-understood stdlib change, the README already advertises "log rotation" (`README.md:41`), and the roadmap's guiding rule is to make a claimed capability true before advertising it. Deleting the claim would have been less work but leaves a useful operability feature missing. So the README claim is **kept** (now true) rather than struck.
- **Evidence (2026-10-08, code commit `c58b6ab`):**
  - **Implementation:** `setup_logging(..., rotation="none", max_bytes=10 MiB, backup_count=5)` selects `RotatingFileHandler(maxBytes, backupCount)` for `LOG_ROTATION=size`, `TimedRotatingFileHandler(when="midnight", backupCount)` for `daily`, else a plain `FileHandler`. New `setup_logging_from_env()` reads `LOG_LEVEL`/`LOG_FORMAT`/`LOG_DIR`/`LOG_ROTATION`/`LOG_MAX_BYTES`/`LOG_BACKUP_COUNT`; `src/api/server.py` calls it instead of reading the logging env vars inline.
  - **Size-rotation test (the acceptance criterion):** `tests/test_log_rotation.py::test_size_rotation_produces_a_backup_file` configures `max_bytes=200`, writes 50 log records, and asserts `app.log` **and** `app.log.1` exist; `test_setup_logging_from_env_honours_size_rotation` does the same through the env path (`LOG_ROTATION=size`, `LOG_MAX_BYTES=200`). `test_daily_rotation_uses_timed_handler` and `test_none_uses_a_plain_file_handler` assert the handler class per mode. `pytest tests/test_log_rotation.py` → **4 passed**.
  - **Pre-fix failure reproduced (rule 18):** against `HEAD`'s `logger.py`, `tests/test_log_rotation.py` **errors at collection** (`ImportError: cannot import name 'setup_logging_from_env'`), and a direct call shows `TypeError: setup_logging() got an unexpected keyword argument 'rotation'` with **no** `Rotating*` handler class in the module. After the fix → **4 passed**.
  - **No behavior regression:** API still starts and serves — `GET /v1/health` → 200; `POST /v1/optimize-price` → 200 `optimal_price=77.06`.
  - **Suite:** `pytest tests/` → **78 passed, 2 skipped** (was 74+2; +4 R20 tests). Warnings unchanged from baseline (the `datetime.utcnow()` deprecation in `JSONFormatter` is pre-existing and untouched).

### R21 — `requirements.txt` correctness
- **Priority:** P1
- **Status:** done
- **Files touched:** `requirements.txt`
- **Acceptance criteria:** In a fresh venv, `pip install -r requirements.txt && pip check` succeeds. `requests` appears exactly once. `sqlalchemy` is either declared (if `ingest.py` is kept) or `ingest.py` is deleted. `shap`, `prometheus-client`, and linters are either actually used (verified by grep) or removed.
- **Depends on:** R3
- **Evidence (2026-10-13, code commit `c444973`) — change complete, literal acceptance blocked by network:**
  - **Edits:** `requests` deduped (appeared on lines 26 and 35 → once). Removed `prometheus-client` and `shap` (repo-wide grep for `import`/`from` → 0 hits; STATE.md §1 marks Prometheus FAKE-OR-DEAD). Removed the linters `flake8`/`black`/`isort`/`mypy` (0 imports, no `.flake8`/`setup.cfg`/`pyproject.toml`/`mypy.ini`, no CI). Declared `sqlalchemy>=2.0.0` (kept `src/data/ingest.py`, which imports it directly — the "declare" branch). Added the R5 `protobuf==4.25.9` pin (see DECISIONS D16).
  - **Resolution verified:** `pip install --dry-run --report` (metadata only) → **exit 0, 116 packages resolved with no conflict**; the report shows `protobuf 4.25.9` honoured and **no** `prometheus-client`/`shap`/`flake8`/`black`/`isort`/`mypy` in the resolved set.
  - **Literal acceptance NOT run — why:** `pip install -r requirements.txt` in a fresh venv requires downloading the full wheel set, but this environment throttles `files.pythonhosted.org` to **~40–60 KB/s with stalls** (measured: 1.8 MB in 28.9 s; a 10.8 MB wheel took ~256 s). The install ran 32 min and had installed nothing (still resolving/downloading) before being stopped. `pip check` therefore could not be observed on a real fresh venv. **Remaining to close R21:** run `python -m venv /tmp/v && /tmp/v/bin/pip install -r requirements.txt && /tmp/v/bin/pip check` on an unthrottled network.
  - **Follow-up noted (not changed here):** `xgboost>=2.0.0` now resolves to **3.4.1**, which on Linux requires `nvidia-nccl-cu13` (**291 MB**); the tested env (STATE.md) is xgboost 3.2.0. Worth pinning in a follow-up if image size matters.
- **Note (D27, 2026-10-13):** D27 pins every direct dependency and adds `tests/test_requirements_pinned.py`; the pin set is verified by `pip install --dry-run --ignore-installed -r requirements.txt --report` → 115 packages, `mlflow==3.17.1`, `xgboost-cpu==3.4.1`, no `nvidia-*`, `protobuf==4.25.9` (code commit `af7383d`). R21 stays `in-progress`; **remaining acceptance = the owner's fresh-venv `pip install -r requirements.txt && pip check` on an unthrottled network.**
- **Acceptance verified by the user (2026-10-14, fresh venv `/tmp/v`, `pip install -r requirements.txt`):** `pip check` → **"No broken requirements found." (exit 0)**. The freeze confirms the pinned stack — `mlflow==3.17.1`, `mlflow-skinny==3.17.1`, `mlflow-tracing==3.17.1`, `opentelemetry-proto==1.27.0`, `protobuf==4.25.9`, `xgboost-cpu==3.4.1`, and **no `nvidia-*` package**. The static criteria also hold in `requirements.txt`: `requests` appears exactly once (`:27`); `sqlalchemy==2.1.4` is declared (`:30`, `ingest.py` kept); `shap`/`prometheus-client`/`flake8`/`black`/`isort`/`mypy` are absent (`grep` → no matches). The user also ran the full suite in that venv: `pytest tests/ -q` → **95 passed, 2 skipped, 178 warnings in 22.05 s**. → **R21 `done`.**
- **Follow-up (2026-10-16, commit `c936519`) — unused pin removed:** `sqlalchemy==2.1.4` was deleted from `requirements.txt`. Its only importer (`src/data/ingest.py`) was deleted in R22, and a repo-wide grep found zero `import sqlalchemy` in `src/`, `scripts/`, `app.py`, `tests/`. It is **not** lost: `mlflow` still declares `sqlalchemy<3,>=1.4.0` (read from the installed `mlflow` METADATA), so it resolves transitively. Verified: `tests/test_requirements_pinned.py` → 3 passed; `.venv/bin/pip check` → "No broken requirements found."; a `--no-deps` `--report` resolution (21 direct deps) shows `xgboost-cpu==3.4.1` present, **no `nvidia-*`**, `mlflow==3.17.1`, `protobuf==4.25.9`, `requests` exactly once. The **full** (transitive) `--report` dry-run could not complete — this machine throttles `files.pythonhosted.org` and timed out fetching `gitpython`'s wheel metadata (a `streamlit` transitive dep) after repeated retries; `xgboost-cpu 3.4.1`'s own `requires_dist` (PyPI JSON) lists numpy/scipy/pandas extras and **no `nvidia`/`nccl`**. Other dependencies that *look* directly unused but were **kept**: `scipy` (no first-party import, but a direct dependency of `scikit-learn`, which the code uses), `pyarrow` (the pandas parquet engine for `read_parquet`/`to_parquet`), `httpx` (required by `fastapi.testclient.TestClient` in tests), `protobuf` (pinned for `mlflow`). **Flag:** the working `.venv` does **not** match `requirements.txt` — it has plain `xgboost==3.4.1` + `nvidia-nccl-cu13==2.32.3`, not `xgboost-cpu` (see STATE.md §1 correction).

### R22 — Dead code: delete or wire+test, file by file
- **Priority:** P1
- **Status:** done
- **Files touched:** `src/pricing/{integrated_optimizer,revenue,model_loader,optimize}.py`, `src/features/{transformer,feature_pipeline}.py`, `src/monitoring/metrics_tracker.py`, `src/data/{ingest,pipeline_runner,validation}.py`, `src/utils/config.py`, `src/api/error_handlers.py:72-90`, `src/pricing/engine.py:163`
- **Acceptance criteria:** Each file/item above is explicitly dispositioned in a committed table as **deleted** or **wired** (with a test proving reachability). An import-graph test asserts every module under `src/` is reachable from `src.api.server` or a training entry point, or is on an explicit allowlist. STATE.md §3 no longer lists the item. `src/pricing/integrated_optimizer.py` and `src/features/transformer.py` are deleted (DECISIONS D1).
- **Depends on:** R1, R2, R15
- **Done (2026-10-15). DECISIONS D1, D2, D9, D10, D12 (accepted `55ae934`).** Commits: group 1 `30e59f9`; group 2 `0b73403` (prerequisite live-path tests), `c4b9fb1` (Bayesian), `3b51851` (orphan modules), `026ed00` (`utils/config`), `87fdf8a` (SQLite chain + DB scripts), `849a866` (`model_loader`), `49243af` (error subclasses), `fb5e2a5` (dead symbols), `e8da719` (import-graph test). Suite **104 → 90 passed, 0 skipped**: group 2 removed 18 tests (all exercised only the deleted `BayesianPriceOptimizer`; 2 were the suite's only skips) and added 4 (2 live-path inventory-cap tests + 2 import-graph tests).
- **Coverage-preservation (C2).** The gate that blocked group 2 is resolved by the C1 prerequisite: the one live-path property the deleted mock test asserted — *the optimizer caps `expected_demand` at `inventory_limit`* (`src/pricing/engine.py:185,193` → `src/pricing/optimizer.py:48-49`) — is now asserted live by `tests/test_optimizer.py::test_inventory_cap_binds_on_live_optimizer_path` and `tests/test_api.py::test_inventory_cap_binds_on_served_path`. Every other property the deleted tests asserted is covered on the live path: near-optimality ≥ 0.99× the R7 reference → `tests/test_optimizer_real.py::test_served_grid_optimizer_reaches_reference_optimum[5]` + `tests/test_api.py::test_grid_path_reaches_reference_optimum`; the served margin → `tests/test_api.py::test_optimize_with_constraints`; serving-features column order → `tests/test_serving_features.py::test_serving_builder_covers_committed_columns_in_order` + `tests/test_optimizer_real.py::test_grid_optimizer_builds_complete_feature_frame`; the result schema → `tests/test_api.py::test_grid_path_response_contract`. The `test_no_gradient_method_remains_on_tree_objective` row is N/A (the file it read is deleted). No row was NONE, so the deletion proceeded.
- **Committed disposition table (every R22 "Files touched" item + `BayesianPriceOptimizer`, the DB scripts, and the dead symbols):**

| item | disposition | commit | proof |
|---|---|---|---|
| `src/pricing/integrated_optimizer.py` | deleted | `30e59f9` | grep no matches; import graph shows no lost importer |
| `src/features/transformer.py` | deleted | `30e59f9` | grep no matches; import graph |
| `tests/test_integration.py` (5 dead-class tests) | deleted | `30e59f9` | only exercised the dead `IntegratedPricingOptimizer`/`FeatureTransformer` |
| `src/pricing/bayesian_optimizer.py` (`BayesianPriceOptimizer`) | deleted | `c4b9fb1` | `grep` NO MATCHES; graph; `pytest tests/test_optimizer_real.py` → 7 passed |
| `tests/test_optimizer.py::TestBayesianOptimizer` (3 tests) | deleted | `c4b9fb1` | inventory-cap property re-asserted live (`0b73403`) |
| 5 Bayesian tests in `tests/test_optimizer_real.py` | deleted | `c4b9fb1` | grid/live tests kept (R2/R6) |
| 2 "both optimizers" tests in `tests/test_serving_features.py` | deleted | `c4b9fb1` | shared-builder test kept |
| `src/pricing/revenue.py` (`RevenueCalculator`) | deleted | `3b51851` | no importer; graph |
| `src/monitoring/metrics_tracker.py` | deleted | `3b51851` | no importer; graph |
| `src/pricing/optimize.py` | deleted | `3b51851` | no importer; graph |
| `src/features/feature_pipeline.py` | deleted | `3b51851` | no importer; graph |
| `src/utils/config.py` (`load_config`) | deleted | `026ed00` | only importer was `feature_pipeline` (deleted `3b51851`) |
| `src/data/ingest.py` | deleted | `87fdf8a` | no importer; graph |
| `src/data/pipeline_runner.py` | deleted | `87fdf8a` | no importer; graph |
| `src/data/validation.py` | deleted | `87fdf8a` | no importer; graph |
| `scripts/backup_database.sh` | deleted | `87fdf8a` | `grep` across start.sh/Dockerfile*/compose/scripts/tests/.github → none |
| `scripts/restore_database.sh` | deleted | `87fdf8a` | same |
| `src/pricing/model_loader.py` (`load_production_model`) | deleted | `849a866` | no caller; engine import removed; `test_mlflow_registry.py` → 4 passed |
| `src/pricing/engine.py:10` (the unused import) | deleted | `849a866` | engine loads via `joblib.load` |
| `src/api/error_handlers.py:72-90` (`ModelNotFoundError`, `OptimizationError`, `InvalidInputError`) | deleted | `49243af` | never raised; base `APIError` + handler kept |
| `src/monitoring/prediction_logger.py` `log_prediction`, `load_logs` | deleted | `fb5e2a5` | no caller (router uses `log_optimization`/`log_error`) |
| `src/utils/env_config.py` `get_env` | deleted | `fb5e2a5` | no caller (`is_production`/`is_development`/`reload_config` already gone, R35) |
| `src/data/generator.py` `run()` | deleted | `fb5e2a5` | only its own `__main__` called it |
| `src/pricing/engine.py:163` (`compare_methods`) | deleted earlier | `b48d18a` (R6) | already gone before R22 |
| import-graph test (`tests/test_import_graph.py`) | added | `e8da719` | FAILS on pre-R22 `62333ea` (lists 11 dead modules), passes on HEAD |

- **Acceptance-criteria coverage:** (1) disposition table — the table above; (2) import-graph test — `tests/test_import_graph.py` (AST-only; roots `src.api.server`/`src.training.train` + the `src.*` modules imported by `scripts/*.py`/`app.py`; empty allowlist that cannot rot); (3) STATE.md §3 — emptied; (4) `integrated_optimizer.py`/`transformer.py` deleted — group 1 `30e59f9`. **All four covered → R22 `done`.**
- **Flag:** `sqlalchemy==2.1.4` is still declared in `requirements.txt:30` but its only importer (`src/data/ingest.py`) is deleted — an unused declared dependency, outside R22's file scope (R21/requirements follow-up).
- **Still `proposed` (not implemented in this batch):** D4, D8, D11 — R22 implemented only the accepted decisions.

### R23 — README truth pass
- **Priority:** P1
- **Status:** done
- **Files touched:** `README.md`, `tests/test_readme_truth.py` (new), `scripts/verify_readme.sh` (new, R23 C1 `5e17dbc`), `tests/test_verify_readme_script.py` (new, R23 C1 `5e17dbc`)
- **Acceptance criteria:** Every command in README runs successfully on a clean checkout (captured by `scripts/verify_readme.sh`, exit 0). The curl example includes `/v1`. The R² figure is the exact regenerated number and is accompanied by MAPE. Every headline claim maps to a `CONFIRMED` or `PARTIAL` row in STATE.md; no unbacked "production-ready / enterprise-grade" claims remain. The README documents the in-memory rate-limit limitation (single process / per worker) and states plainly that all data and metrics are synthetic (DECISIONS D22/D23, folded into this item).
- **Depends on:** R1, R2, R6, R12, R15, R24
- **Note (2026-10-15):** the legacy `"bayesian"` string still appears in `README.md:157` (curl example body), `README.md:332` (a `default_method: bayesian` YAML snippet — doubly stale, since `pricing.default_method` was **removed** in R18), and `scripts/load_test.sh:46` (load-test payload). All three now send/reference a method that returns **HTTP 422** under D2 and must be corrected in the README/script truth pass. Separately, `app.py:65-66` renders a `"Product ID"` `st.number_input` with **no help text** although `product_id` does not influence the prediction (R34/D5) — the UI weakly implies it matters; fix under this item or the UI work.
- **Note (2026-10-15, R22):** R22 deleted the modules and scripts the README still advertises, so new stale sentences to fix here: `README.md:59` (repo-tree line `data/  # Data generation, ingestion, validation` — the `ingestion`/`validation` modules are gone), `README.md:274` (`./scripts/backup_database.sh`) and `:277` (`./scripts/restore_database.sh backup_file.db`) — both scripts deleted, `README.md:377` (`./scripts/restore_database.sh backups/database/latest.db`), and `README.md:457` (commands table `| Backup database | ./scripts/backup_database.sh |`). `docs/` is empty, so there are no `docs/*.md` mentions. The `README.md:157`/`:332` and `scripts/load_test.sh:46` `"bayesian"` strings (above) still stand.
- **Done (2026-10-16, commit `f26dee3`; `scripts/load_test.sh` in `7ca9014`; `scripts/verify_readme.sh` + `tests/test_verify_readme_script.py` in `5e17dbc`).** Acceptance-criteria coverage:
  1. **Every README command runs on a clean checkout** — verified *by doing* in a fresh clone (`git clone --no-hardlinks` → `/tmp/readme_walk`, `.venv/bin/python`, API on `127.0.0.1:8765`): `python scripts/regenerate_data.py` (18,250 rows) → `python -m src.training.train` (R² 0.41930 / MAPE 0.35093 / 30 features) → `python -m src.api.server` (`/v1/health` **200**, `source: local`) → every README curl (see 2 and below) → `pytest tests/ -q` (**89 passed, 1 skipped** — the skip is `tests/test_env.py:48`, `.env` absent in a clean clone) → `python -m py_compile app.py` (exit 0) + `pytest tests/test_streamlit_contract.py` (**5 passed**). Docker/compose sections compared statically with `docker-compose*.yml`/`Dockerfile*` (service `pricing-api`, port 8000, `logs -f pricing-api` all match). **Deviation (flagged, now resolved):** at `f26dee3` the criterion named `scripts/verify_readme.sh` but the batch committed only `README.md` + `tests/test_readme_truth.py`, so the regression test substituted for the script — the commands were still run for real (raw output in `LOG.md`). **Resolved 2026-10-16 (C1 `5e17dbc`):** `scripts/verify_readme.sh` now exists and captures this criterion. It clones HEAD (`git archive HEAD` → `mktemp -d`, never the working tree) and runs there: `python scripts/regenerate_data.py` → `python -m src.training.train` → `python -m src.api.server` (127.0.0.1, `API_WORKERS=1`, `API_RELOAD=false`, sqlite `MLFLOW_TRACKING_URI`; bounded 60 s wait for `/v1/health`) → all four README API curls (the optimize curl also asserts `optimal_price` is present and `optimization_method == "grid_search"`) → `pytest tests -q` → the smoke tests with `API_URL` set → `python -m py_compile app.py`. It prints one PASS/FAIL line per step, exits non-zero on the first failure, and a trap always kills the server and removes the temp dir. **Real run (`.venv` python, port 8765): all steps PASS, exit 0** (archive suite **91 passed, 1 skipped** — the skip is `tests/test_env.py:48`, `.env` absent in a clean checkout); **mutation check** (temp clone, optimize URL → `/optimize-price`): `FAIL: curl POST /v1/optimize-price`, exit 1, nothing left listening. `tests/test_verify_readme_script.py` (5 tests) asserts the script exists and is executable, `bash -n` passes, every quickstart command it runs appears verbatim in README.md, the script runs those commands, and README mentions the script. **Scope note (the residual of "every command"):** the script covers the README's locally runnable commands (quickstart, API examples, test commands, `py_compile`); the Docker / `pip install` / long-running-tuning / ops-shell commands are outside its default scope — `pip install` is opt-in (`--with-pip`) and Docker is not run here (this batch forbids installs and Docker, and the network is throttled).
  2. **Curl example includes `/v1`** — `README.md` now posts to `http://localhost:8000/v1/optimize-price`; the old path returned **404** in the clone.
  3. **R² is the exact regenerated number + MAPE** — README states R² **0.419** / MAPE **0.351** (seed 42), plus the seed-1–10 spread (R² mean 0.447 ± 0.029, MAPE mean 0.361 ± 0.011) — all quoted from STATE.md §1.
  4. **Headline claims map to STATE rows; no unbacked adjectives** — full audit table in `LOG.md` (76 rows: **30 true/kept, 31 false, 7 stale, 2 unverifiable, 1 not-run**; actions **fixed 22 / removed 17 / kept 37**). `production-ready`, `production ready`, `enterprise-grade`, `~49%`, `Bayesian`, AWS/EC2, nginx, Prometheus, drift, SQLite/backup/restore, CI/CD and `run_hyperparameter_tuning`/`default_method` are gone.
  5. **Rate-limit limitation + synthetic data stated** — `README.md` states rate limiting is an in-memory, per-process sliding window (not shared across workers) and that all data/metrics are synthetic (top of file + Model Performance). (No `Limitations` heading — that is R32.)
- **Regression guard:** `tests/test_readme_truth.py` (2 tests) — (a) every repo-relative path in a README code span/block exists on disk (documented ignore list for gitignored generated artifacts); (b) a forbidden-phrase list built from STATE/DECISIONS. **Shown to FAIL on the pre-edit README** (`2 failed`, listing 5 missing paths + 18 offenders) and pass after. R23 C1 (`5e17dbc`) adds `tests/test_verify_readme_script.py` (5 tests) as the README↔`scripts/verify_readme.sh` drift guard; it was **shown to FAIL before** the script/README edit (`5 failed`: script missing, `bash -n` exit 127, README missing `python -m src.api.server` + `pytest tests -q`, README did not mention the script) and **pass after** (`5 passed`). Repo suite **92 → 97 passed, 0 skipped**.
- **Evidence (dependency audit, R21 follow-up, commit `c936519`):** `sqlalchemy==2.1.4` removed from `requirements.txt` (its only importer, `src/data/ingest.py`, was deleted in R22). `mlflow` still requires `sqlalchemy<3,>=1.4.0` (verified from installed metadata), so it resolves transitively. The `--report` dry-run for the **full** set could not complete (network throttled at `gitpython` metadata — see LOG); a `--no-deps` report (21 direct deps) confirms `xgboost-cpu==3.4.1` present, no `nvidia-*`, `mlflow==3.17.1`, `protobuf==4.25.9`, `requests` exactly once.
- **Open items carried forward (not R23):** `docs/API.md`, `docs/OPERATIONS.md`, `DEPLOYMENT.md`, `PRODUCTION_FEATURES.md`, `PRODUCTION_READY.md` links are **left in place** (per the batch instruction) and remain for **R31**; `app.py:65-66` "Product ID" input still has no help text; `data.db` still exists locally (untracked, owner deletes it — R29 stays `in-progress`).

### R24 — nginx: add a real config or remove the service
- **Priority:** P1
- **Status:** done
- **Files touched:** `docker-compose.prod.yml` (nginx service removed; `environment:` indentation fixed), `README.md` (3 nginx claims struck)
- **Acceptance criteria:** `docker compose -f docker-compose.prod.yml config` succeeds; `up` starts nginx and `curl http://localhost:80/v1/health` returns 200 through the proxy. **OR** the nginx service block is removed and the README nginx claim is deleted.
- **Depends on:** R3, R5
- **Evidence (2026-10-13, code commit `a1eb669`) — remove branch (DECISIONS D17, accepted):**
  - **nginx service removed** from `docker-compose.prod.yml` (the whole `nginx:` block, incl. the `./nginx/nginx.conf` + `./nginx/ssl` bind mounts); `grep -rin nginx README.md docker-compose.prod.yml` → **no matches**; `ls nginx` → **No such file or directory**.
  - **README claims struck:** the three nginx mentions (What You Get `README.md:21`, Containerization `:42`, repo tree `:72`) are gone; the tree's last entry is now `└── docker-compose.prod.yml`.
  - **`docker compose -f docker-compose.prod.yml config` → exit 0** (rendered services: `pricing-api` only).
  - **Regression fixed:** the R35 commit (`5a8f887`) had corrupted the `environment:` indentation, making the file invalid YAML (`yaml: line 3: did not find expected key`). This commit normalizes the file; `config` now exits 0. (Pre-R35 the file was valid — verified with `git show 90039b2:docker-compose.prod.yml | docker compose -f - config` → exit 0.)

### R25 — Docker build/compose works from a clean checkout
- **Priority:** P1
- **Status:** done
- **Files touched:** `Dockerfile:1`, `Dockerfile.hf:3`, `Dockerfile.prod:2,17`, `docker-compose.yml:35-40`, `requirements.txt` (protobuf pin — done in R21)
- **Acceptance criteria:** `docker compose build && docker compose up -d` succeeds using a standard public base image (no `docker.arvancloud.ir` or other private mirror), and `curl http://localhost:8000/v1/health` returns 200. `pricing-api` has a `build:` context. The base image Python version matches the interpreter used and tested (3.12 — see DECISIONS D16); the current Dockerfiles pin 3.10 and must be bumped.
- **Depends on:** R3, R13
- **Note:** A clean-checkout build also depends on the R5 `protobuf` pin landing in `requirements.txt`. R5 made `import mlflow` work by installing `protobuf==4.25.9` (plus `setuptools<81`) into the venv; `requirements.txt` carries neither, so a fresh image fails `pip check`/`import mlflow` exactly as it did pre-R5. R25 must pull that minimal `protobuf` pin into `requirements.txt` (or R21 — `requirements.txt` correctness — must land first). See DECISIONS D16 consequences.
- **Evidence (2026-10-13, code commit `ce4f2e7`) — change complete, acceptance NOT met (network):**
  - **Edits:** all three Dockerfiles switched off the `docker.arvancloud.ir` mirror to the public **`python:3.12-slim`** (`Dockerfile:1`, `Dockerfile.hf:3`, `Dockerfile.prod:2,17` — builder + final), matching the verified interpreter (3.12.3). `docker-compose.yml` `pricing-api` gained a `build: {context: ., dockerfile: Dockerfile}` context, so the stack no longer needs a pre-built image.
  - **Verified:** the public base image pulls (`docker pull python:3.12-slim` → downloaded, no arvancloud/private registry). `docker compose config` renders `pricing-api.build.context = <repo>` and `dockerfile: Dockerfile`. The build itself starts correctly: `docker compose build --progress=plain` reaches `#6 [1/5] FROM docker.io/library/python:3.12-slim@sha256:…`, then `#7 WORKDIR`, `#8 COPY requirements.txt .`, `#9 RUN pip install -r requirements.txt`, and resolves the dependency graph from PyPI.
  - **Acceptance NOT met — why:** step `#9` must download the full wheel set, but this environment throttles `files.pythonhosted.org` to **~40–61 KB/s** (measured in-build: pandas 10.8 MB in ~256 s; the log's progress bars read `39.9 kB/s`, `61.3 kB/s`). After 19 min the build had downloaded only a handful of wheels and was still on `numpy`; with `xgboost 3.4.1` alone pulling `nvidia-nccl-cu13` (**291 MB**), completion would take hours. The build was stopped. `docker compose up -d` + `curl localhost:8000/v1/health` were therefore never reached.
  - **Remaining to close R25:** run `docker compose build && docker compose up -d && curl http://localhost:8000/v1/health` on an unthrottled network (expect 200). No code change is pending; only the verification is outstanding.
- **Note (D27, 2026-10-13):** the mlflow service now pins `mlflow==3.17.1` (code commit `3a7e3e9`), asserted by `tests/test_compose_files.py::test_compose_mlflow_service_pin_matches_requirements`. `psycopg2-binary`, the `python:3.10` image, and the obsolete `version` key are intentionally untouched (flagged only). R25 stays `in-progress`; **remaining acceptance = `docker compose build && docker compose up -d && curl http://localhost:8000/v1/health` on an unthrottled network.**
- **User-run evidence (2026-10-14):** `docker compose build` **succeeded** with the BuildKit pip-cache-mount Dockerfile (C3, code commit `88b1e86`) — **1590 s on a throttled network**. `docker compose up -d` started `mlflow-db`, `mlflow-server` (`python:3.10`) and `pricing-api`; `docker compose ps` showed all three **Up for 7 minutes**, and the API logs show **4 worker processes** with `Application startup complete`. Inside the image `models/` contains `demand_model.pkl` and `features.json` and there is **no `mlflow.db` and no `mlruns/`** (so the `.dockerignore` entries take effect); the API startup logs an XGBoost warning that the pickle was produced by an older xgboost version. **Acceptance still NOT met:** `curl http://localhost:8000/v1/health` and `http://localhost:5000/health` from the host both returned **HTTP 000 (no connection)**; the cause is not yet known and is under diagnosis (candidate causes: host proxy env, the server bound to `127.0.0.1` inside the container, mlflow still installing). R25 stays `in-progress`.
- **User-run evidence (2026-10-15) — the HTTP-000 issue is resolved:** on a later run, `docker compose up -d` + `curl http://localhost:8000/v1/health` returned **HTTP 200** `{"status":"healthy", … "loaded": true, "source": "local"}` (uptime ≈596 s). The earlier **HTTP 000** from both host ports was **not reproduced** in two later runs; the cause was never established (no proxy env or `~/.curlrc` output was shown). The `mlflow-server` (`python:3.10`, `pip install mlflow==3.17.1 psycopg2-binary` at every start) was still downloading dependencies after ~10 min on the throttled network, so **port 5000 health is unverified**; the API serves without it via the local-pickle fallback.
- **R25 acceptance criteria — covered vs not (2026-10-15, *superseded by the clean-clone evidence below*):**
  - ✅ `docker compose build && docker compose up -d` succeeds — user-run (build 1590 s; three containers Up).
  - ✅ standard public base image (no private mirror) — `python:3.12-slim` (verified `ce4f2e7`).
  - ✅ `curl http://localhost:8000/v1/health` → **200** — user-run 2026-10-15 (the 2026-10-14 HTTP 000 was not reproduced).
  - ✅ `pricing-api` has a `build:` context — `docker-compose.yml:36-38`.
  - ✅ base-image Python (3.12) matches the tested interpreter (3.12.3) — Dockerfiles bumped in `ce4f2e7`.
  - ⏳ **"from a clean checkout"** — at this point unmet: the build ran in the **working tree**, not a fresh clone, and a fresh clone has **no `models/demand_model.pkl`** (gitignored). **Now covered** by the clean-clone run below.
  - ⚠️ `mlflow-server` :5000 health — unverified (dependency download incomplete on the throttled network); still unverified below (not an acceptance criterion).
  → At this point **R25 stayed `in-progress`** (the clean-checkout criterion was unmet); the clean-clone run below closes it.
- **Note (D30, 2026-10-15):** the **main** `Dockerfile` now builds the data + model inside the image after `COPY . .` (`RUN python scripts/regenerate_data.py && python -m src.training.train`, offline — strace shows no network — ≈6 s), and `.dockerignore` excludes `models/*.pkl` + `data/features/`, so a clean-checkout image no longer depends on local artifacts. The remaining acceptance is the **owner's** clean-checkout `docker compose build && docker compose up -d && curl http://localhost:8000/v1/health` (expect 200). `Dockerfile.prod`, `Dockerfile.hf`, and `docker-compose.prod.yml`'s `./models:/app/models:ro` mount are **not** touched and still ship no model (open). **R25 was left `in-progress` by D30; it is closed by the clean-clone run below.**
- **User-run evidence (2026-10-15) — the clean-checkout criterion is met:** on a fresh `git clone --no-hardlinks` of this repo into `/tmp/dp_clone`, `docker compose build pricing-api && docker compose up -d pricing-api` succeeded: the image built in **8.7 s** (the pip layers came from the Docker **cache** — this is not a cold build; the earlier cold build was 1590 s), the model was produced **inside the image** (`/app/models/demand_model.pkl`, 2,658,806 bytes; `/app/models/features.json`, 592 bytes), and `curl http://localhost:8000/v1/health` returned **HTTP 200** `{"status":"healthy", … "loaded": true, "source": "local"}` (uptime 1.8 s). `/app/.env` is **not** present in the image, and `/app/mlflow.db` is not either (verified earlier).
- **R25 acceptance criteria — covered vs not (final, 2026-10-15):**
  - ✅ `docker compose build && docker compose up -d` succeeds — clean-clone run above (build 8.7 s cached; earlier cold build 1590 s, three containers Up).
  - ✅ standard public base image (no private mirror) — `python:3.12-slim` (`ce4f2e7`).
  - ✅ `curl http://localhost:8000/v1/health` → **200** — clean-clone run above.
  - ✅ `pricing-api` has a `build:` context — `docker-compose.yml:36-38`.
  - ✅ base-image Python (3.12) matches the tested interpreter (3.12.3) — `ce4f2e7`.
  - ✅ **"from a clean checkout"** — fresh clone run above (the model is built inside the image).
  → **R25 is `done`.** Remaining caveats are operational follow-ups, not acceptance criteria: the clean-clone build reused the Docker cache (a *cold* clean-clone build was not re-run), and `mlflow-server` :5000 health is still unverified.
- **R25 follow-up notes (2026-10-15; not new R-numbers):**
  - The `mlflow` service runs `pip install mlflow==3.17.1 psycopg2-binary` on `python:3.10` at **every** start (`docker-compose.yml:17,22-28`) — slow, not reproducible, and `python:3.10` is nearing end of life (**check support status**; no EOL date asserted here).
  - The obsolete `version: "3.8"` key is still present in both compose files (`docker-compose.yml:1`, `docker-compose.prod.yml:1`).
  - `MONITORING_ENABLED=true` in `docker-compose.prod.yml:17` has **no reader** (unread since R19).
  - `Dockerfile.prod`, `Dockerfile.hf`, and `docker-compose.prod.yml`'s `./models:/app/models:ro` mount still ship **no model** on a fresh clone (only the main `Dockerfile` builds one — D30). Recorded under **R28** (deployment files), below.
  - **All follow-ups closed (2026-10-19, D31):** `Dockerfile.mlflow` pins `mlflow==3.17.1`, `protobuf==4.25.9` and `psycopg2-binary==2.9.13` on `python:3.12-slim`, and the compose `mlflow` service no longer runs `pip install` at start; the obsolete `version` key is removed from `docker-compose.yml`; `MONITORING_ENABLED` is gone with `docker-compose.prod.yml`; `python:3.10` is resolved because the MLflow image is now `python:3.12-slim` (the same base as the API and CI).

### R26 — Bounded startup in `start.sh`
- **Priority:** P1
- **Status:** done
- **Files touched:** `start.sh:11-26`, `tests/test_start_sh.py` (new)
- **Acceptance criteria:** Both wait loops have a maximum attempt count/timeout and exit non-zero with a clear message when the dependency never becomes healthy. A test that points the script at a non-2xx health endpoint asserts it terminates within the timeout instead of hanging.
- **Depends on:** none
- **Evidence (2026-10-13, code commit `7cdbf56`):**
  - **Implementation:** both loops now call `wait_for_health "<name>" "<url>"`, which retries at most `HEALTH_MAX_ATTEMPTS` (default 60) times with `HEALTH_RETRY_INTERVAL` (default 2s) between attempts and, on exhaustion, prints `ERROR: <name> did not become healthy at <url> after N attempts; giving up.` to stderr and `return 1`; each call is followed by `|| exit 1`, so the script exits non-zero (CONVENTIONS rule 31). Health URLs/attempts/interval are overridable env vars so the loops can be pointed at a non-2xx endpoint without real services.
  - **Pre-fix failure reproduced (rule 18):** against `HEAD`'s `start.sh` with a stub `curl` that never returns 2xx, `timeout 5 bash start_old.sh` → **still looping after 5s, `exit=124`** (the unbounded bug). With the fixed script and the same stub: `HEALTH_MAX_ATTEMPTS=2 HEALTH_RETRY_INTERVAL=0 timeout 5 bash start.sh` → prints the clear error and **`exit=1`**.
  - **Test:** new `tests/test_start_sh.py` (2 tests) runs the real `start.sh` with a stub PATH (no-op `mlflow`/`uvicorn`/`streamlit` + a `curl` that returns 2xx only for a marker substring): `test_mlflow_loop_gives_up_and_exits_nonzero` (non-2xx MLflow → non-zero, "MLflow did not become healthy") and `test_api_loop_gives_up_after_mlflow_becomes_healthy` (MLflow 2xx, API non-2xx → "MLflow is up." then non-zero, "uvicorn did not become healthy"). Both bound the subprocess at 30s, so a hang fails the test. `pytest tests/test_start_sh.py -v` → **2 passed**.
  - **Suite:** `pytest tests/` → **81 passed, 2 skipped**, 0 collection errors (was 79+2 after R35; +2 R26 tests).

- **Note (2026-10-17) — artifact deleted.** `start.sh` and `tests/test_start_sh.py` were deleted with the HF deployment files (C2 `5aa5d58`, user decision). R26's bounded-loop behaviour no longer exists because the script does; the rule remains CONVENTIONS 31. The R26 evidence above is historical.

### R34 — `PricingRequest.product_id` is accepted but unused (latent contract mismatch)
- **Priority:** P1
- **Status:** done
- **Files touched:** `src/api/schemas.py:9` (Field description), `tests/test_product_id_contract.py` (new, 4 tests)
- **Decision: option (b) — keep `product_id` (required, `ge=0`), rewrite its description.** `app.py`, `tests/test_api.py`, and `README.md` were **not** touched.
- **Acceptance criteria:** Either (a) `product_id` is removed from `PricingRequest` and every caller that sends it is updated in the same PR (UI, tests, README example), **or** (b) it is kept but its `Field` description states plainly that it is accepted for request compatibility and is **not** a model feature, with a test asserting `"product_id"` is absent from the served feature columns. Either way the request schema no longer implies `product_id` influences the predicted demand/price.
- **Depends on:** R12
- **Note:** R12/D5 removed `product_id` from the model feature list, but `PricingRequest` still declares it as a required field (`src/api/schemas.py:9`) and the serving path silently drops it (the feature builder restricts to the committed columns). Harmless today — the tests pass and the response is unaffected — but a latent mismatch: a client sending `product_id` would reasonably expect it to change the price. Flagged here rather than fixed inline because it touches the UI/tests/README contract, not just the schema.
- **Evidence (2026-10-15, code commit `ecb98ac`):**
  - **Before:** `PricingRequest.model_fields["product_id"].description` → `'Product ID'` (no mention of compatibility or that it is unused).
  - **Change (option (b), `src/api/schemas.py` only):** description is now `"Product ID, accepted for request compatibility and logging only. It is NOT a model feature and does not influence the predicted demand or price."`; the field stays `Field(..., ge=0)` (required, `>= 0`).
  - **Tests (`tests/test_product_id_contract.py`, 4):** (i) the description contains `"not a model feature"` (case-insensitive) and `"compat"` — **FAILED before the fix** (`AssertionError: ... got 'Product ID'`), passes after; (ii) `"product_id"` absent from the tracked `models/features.json` columns **and** from the served feature list — the attribute is `PricingEngine.feature_columns` (`src/pricing/engine.py:31` declared, `:138` loaded from `models/features.json`, `:175` passed to `PriceOptimizer`); (iii) behavioural invariance through the `client` fixture (TestClient): posting the same valid optimize payload with `product_id=1` vs `999` yields identical `optimal_price`/`expected_demand`/`expected_revenue` — a **characterization** test that passed before the fix too (product_id already did not influence the output).
  - **UI check (read-only, not edited):** `app.py:65-66` render `st.subheader("📦 Product Information")` then `product_id = st.number_input("Product ID", value=1, min_value=0, step=1)` inside the pricing form, with no help text saying it is ignored — so the UI weakly implies the product id matters. Left for R23/UI work (option (b) is schema-only).
  - **Suite:** `pytest tests -q` → **107 passed, 2 skipped** (was 103 passed, 2 skipped; +4).

### R35 — Collapse to a single `config.yaml`
- **Priority:** P1
- **Status:** done
- **Files touched:** `configs/config.dev.yaml` (delete), `configs/config.prod.yaml` (delete), `src/utils/env_config.py:32-51`, `src/api/server.py:77-83`, `.env.example`, `.env`, `docker-compose.prod.yml:14`, `tests/test_config.py`, `README.md:99`
- **Acceptance criteria:** Exactly one file exists in `configs/` (`configs/config.yaml`), asserted by a test (e.g. `len(list(Path("configs").glob("*.yaml"))) == 1`). `EnvConfig._load_config` always loads `configs/config.yaml` — no `APP_ENV`→file `config_map` remains. `APP_ENV` is removed from `.env.example`, `.env`, and `docker-compose.prod.yml`, and `tests/test_env.py` is still green (its read-set equality no longer includes `APP_ENV`). After the change, `GET /v1/health` returns 200 and `POST /v1/optimize-price` (`grid_search`) returns 200 with a price within bounds (behavior provably unchanged, since the three files were key-identical). `tests/test_config.py` remains green.
- **Depends on:** R18, R19
- **Note:** Implements DECISIONS D26. The three files are currently key-identical (parsed YAML compares equal; only comments differ), so this is a pure deduplication with no behavior change. `APP_ENV` becomes readerless once the file selection is removed (`is_production`/`is_development` are already dead per STATE §3), so it must be dropped from the env read set in the same change or `tests/test_env.py` (CONVENTIONS rule 6) will flag it.
- **Evidence (2026-10-13, code commit `5a8f887`):**
  - **One config file:** `configs/config.dev.yaml` and `configs/config.prod.yaml` deleted (`git rm`); `ls configs/` → `config.yaml` only. New `tests/test_config.py::test_exactly_one_config_file` asserts `sorted(Path("configs").glob("*.yaml")) == ["config.yaml"]`. **Pre-fix failure reproduced (rule 18):** with the two files restored from `HEAD` the test **fails** — `expected exactly configs/config.yaml, found ['config.dev.yaml', 'config.prod.yaml', 'config.yaml']`; after deletion it **passes**. `pytest tests/test_config.py` → **5 passed** (was 4).
  - **`_load_config` always loads `configs/config.yaml`:** the `config_map` and the `APP_ENV` read are gone — `grep -n "config_map\|APP_ENV" src/` → no matches. The now-broken dead env concept (`self.env`, `is_production()`, `is_development()`, `reload_config()` — all unreachable per STATE §3) was removed with it, and `src/api/server.py`'s startup log no longer references `config.env`.
  - **`APP_ENV` removed from the read set:** removed from `.env.example`, `.env` (gitignored, cleaned in the working tree), and `docker-compose.prod.yml`. `pytest tests/test_env.py` → **2 passed** (the derived read set no longer contains `APP_ENV`).
  - **Behavior provably unchanged:** `GET /v1/health` → **HTTP 200** (`checks.model = {'status':'ok','loaded':True,'source':'local'}`); `POST /v1/optimize-price` (`grid_search`, 70–110) → **HTTP 200**, `optimal_price=77.06`, `expected_revenue=6152.544` — identical to the pre-change R12 value.
  - **Suite:** `pytest tests/` → **79 passed, 2 skipped**, 0 collection errors (was 78+2; +1 R35 test).
  - **README:** the `cp configs/config.dev.yaml configs/config.yaml` snippet (`README.md:99`) referenced a now-deleted file and was corrected to state the single-file config; the full README truth pass remains R23.

---

## P2 — Polish and resume hardening

### R27 — CI workflow (or remove CI claims)
- **Priority:** P2
- **Status:** done
- **Files touched:** `.github/workflows/ci.yml` (new), `README.md`
- **Acceptance criteria:** On push, the workflow runs `pytest tests/` (green per R8) and `docker build`, and its status is documented in README. **OR** all CI/CD claims are removed from README. Dead CI metadata in `scripts/train_with_tuning.py:28-35` is removed or actually exercised.
- **Depends on:** R8, R25
- **Note (2026-10-15, clean-clone investigation):** on a fresh clone with no `models/demand_model.pkl` or features parquet, the baseline suite is **54 passed, 33 skipped, 11 errors** (all `FileNotFoundError: models/demand_model.pkl`), and ~**31** tests **skip silently** when the model/parquet is absent. A CI workflow (this item) that runs `pytest tests/` **without first building the data + model would be vacuously green**; it must run `python scripts/regenerate_data.py && python -m src.training.train` before the suite. (Building the data + model in a clean clone then yields 96 passed, 2 skipped — see `.agents/STATE.md` §7.)
- **Note (2026-10-15, R14 follow-up):** the smoke tests (`tests/smoke_tests.py`) are **not** in default `pytest tests` discovery (`pytest.ini` `python_files = test_*.py`), and even when run explicitly they **skip** unless an API is reachable (R14's `api_base_url` fixture). For CI to actually exercise them, the workflow must **start the API** (e.g. `python -m src.api.server` with a sqlite `MLFLOW_TRACKING_URI`) and run them with `API_URL` set — otherwise they report as skipped and prove nothing.
- **Note (2026-10-17, read-only CI facts; no workflow created):** no `.github/` directory; branch `main`; `git symbolic-ref refs/remotes/origin/HEAD` → **not a symbolic ref** (no local default-branch ref). In a clean clone at `f722b08`: `pytest tests -q` **before** building artifacts → **1 failed, 69 passed, 16 skipped, 13 errors**; `scripts/regenerate_data.py` **2.22 s**, `python -m src.training.train` **4.65 s**, suite after building **98 passed, 1 skipped** (22.96 s), `scripts/verify_readme.sh` **42.60 s** (all PASS). The Docker base (`python:3.12-slim`) and `.venv` (3.12.3) agree. CI needs **no** env vars; a sqlite `MLFLOW_TRACKING_URI` is only needed for the server/smoke steps. D18 remains `proposed`.
- **Evidence (2026-10-17, D18 accepted `f355212`; code `9164438`, `f66a703`, `3723295`, `dc879c1`, `792627f`):** `.github/workflows/ci.yml` defines the `test` job (checkout → setup-python `3.12` with pip cache → `pip install -r requirements.txt` → `bash scripts/ci_check.sh`) and the `docker` job (`needs: test` → `bash scripts/docker_smoke.sh`), with `permissions: contents: read`, a concurrency group that cancels older runs of the same ref, timeouts 20/30 min, and no error suppression. `scripts/ci_check.sh` builds data+model, runs `pytest tests -q -rs --cov=src/pricing --cov=src/api --cov-report=term-missing --cov-report=json:… --junitxml=… --cov-fail-under=80`, runs `scripts/check_coverage.py` (per-file ≥80%), the zero-skip gate (JUnit; `ALLOW_SKIPS=1` for local debugging only) and `scripts/verify_readme.sh`. `tests/test_ci_workflow.py` (8 static tests) parses the YAML (handling PyYAML's `on:`→`True`), asserts triggers/jobs/`needs`/timeouts, `python-version '3.12'` == the Dockerfile base, the scripts exist + are executable + pass `bash -n`, no `continue-on-error`/`|| true`, read-only permissions, and that `.github` is not gitignored; it was **shown failing before the files existed** (7 errors) and passes after (8 passed). **Local evidence:** `PYTHON=.venv/bin/python bash scripts/ci_check.sh` → exit 0, all PASS, **124 passed, 0 skipped (124 collected)**, 97% combined, per-file gate all PASS; the same run in `/tmp/ci_prep_clone` **without artifacts** (the script builds them) → exit 0, 124 passed, 0 skipped, identical per-file numbers. Gate mutations in `/tmp` copies: `THRESHOLD=99` → `check_coverage.py` exits 1; one added skipped test → the zero-skip gate fails. Dead CI metadata (`get_ci_metadata` / `GITHUB_*` tags) removed from `scripts/train_with_tuning.py` (`f66a703`). **Why not `done`:** the criterion also requires the workflow to run on push and its status to be documented in README; neither has happened — README deliberately makes no CI-status claim until the owner pushes and reports a green run. **Remaining acceptance = the owner pushes and reports a green run of both jobs (`test`, `docker`); README then documents the CI status.** The action versions (`actions/checkout@v4`, `actions/setup-python@v5`) are from memory and were not verified offline; `scripts/docker_smoke.sh` was `bash -n`-checked only (no Docker in this environment).

- **Note (2026-10-18) — first GitHub run and fix.** The first `test` job run (2026-10-17, user-reported; Python 3.12.15, pytest 9.1.1, pytest-cov 7.1.0) passed build data+model, 124 tests, coverage 97.17%, the per-file gate (9 files) and the zero-skip gate, then failed in `scripts/verify_readme.sh`: inside its `git archive HEAD` checkout (no `.git`) `tests/test_ci_workflow.py::test_workflow_file_is_not_gitignored` ran `git check-ignore` → exit 128. Fixed in `caae3aa` by parsing `.gitignore` in pure Python (verified in the repo and in a `/tmp` archive export; mutation: appending `.github/` to a copy's `.gitignore` makes it fail, removing it passes). `bash scripts/ci_check.sh` at `caae3aa` → exit 0, all PASS, 124 passed, 97% combined, archive checkout PASS. `actions/checkout@v4`/`actions/setup-python@v5` worked; the `docker` job did not run. **R27 stays `in-progress`** until the owner reports a fully green run of both jobs after the push.

- **Done (2026-10-19).** The owner reported that after pushing `caae3aa` **both** GitHub Actions jobs of `.github/workflows/ci.yml` ran green: the `test` job ran `scripts/ci_check.sh` (build data+model, full suite, coverage gate, zero-skip gate, README quickstart) and the `docker` job ran `scripts/docker_smoke.sh` (`docker build` of the main Dockerfile, `docker compose up -d pricing-api`, `/v1/health` → 200). The workflow runs on push and pull request to `main`, so the "runs `pytest tests/` and `docker build` on push" criterion is covered. README now documents CI status with a badge and a `## Continuous Integration` section (C7, 2026-10-19). Dead CI metadata was removed in `f66a703`. → **R27 done.** The green runs are user-reported; no Docker command was run in the authoring environment.

### R28 — Deployment scripts, or remove the claims
- **Priority:** P2
- **Status:** done
- **Files touched:** `scripts/deploy.sh`, `scripts/pre_deploy_check.sh` (new) or `README.md`
- **Acceptance criteria:** The scripts exist, are idempotent, and `pre_deploy_check.sh` exits 0 on a healthy checkout and non-zero when a required artifact is missing. **OR** the AWS/deploy references in README are removed.
- **Depends on:** R25
- **Note (2026-10-15) — deploy files ship no model on a fresh clone:** `Dockerfile.prod`, `Dockerfile.hf`, and `docker-compose.prod.yml`'s `./models:/app/models:ro` mount still **lack a model** on a fresh clone. The model is gitignored and only the **main** `Dockerfile` builds one (D30); `.dockerignore` excludes `models/*.pkl` + `data/features/`, so `Dockerfile.prod`/`Dockerfile.hf` copy the source but never train, and the prod compose mount points at an empty `./models` — the API would start and serve no model. **Placed here (deployment files)** rather than under R25 (now `done`). Also tracked as an open finding in `.agents/STATE.md` §7.
- **Note (2026-10-17) — the residual `DEPLOYMENT.md`/AWS Documentation-table link is gone.** R31 removed the whole Documentation table (commit `0b57fc4`), including the "AWS deployment guide" description of `DEPLOYMENT.md`; `tests/test_readme_truth.py` now also forbids the whole word `aws`. **R28 itself stays `todo`:** it is blocked on **proposed D19** (not accepted in this batch), and the no-model deploy files remain.
- **Note (2026-10-17, read-only deploy-file audit; no edits):** `Dockerfile.prod` (multi-stage, non-root `appuser`, referenced only by `docker-compose.prod.yml:7`) and `Dockerfile.hf` (FastAPI + Streamlit via `start.sh`, referenced only by `docker-compose.hf.yml:7`) never build data/model. On a fresh clone `.dockerignore` excludes `models/*.pkl` and `data/features/`, and `docker-compose.prod.yml:19` bind-mounts the host `./models` over the image; `PricingEngine.load_model` then calls `joblib.load('models/demand_model.pkl')` without a fallback (`src/pricing/engine.py:131`), so the container exits with `FileNotFoundError` at import rather than serving. **Minimal fix:** add the main Dockerfile's `RUN python scripts/regenerate_data.py && python -m src.training.train` after `COPY . .` in both Dockerfiles **and** drop the `./models` mounts (`docker-compose.prod.yml:19`, `docker-compose.hf.yml:18`), otherwise the empty host directory shadows the built model. **Deleting instead would break:** `tests/test_compose_files.py` (a compose `build.dockerfile` must exist), `tests/test_start_sh.py` (2 tests, `start.sh`), and the README compose commands (their code-span paths must exist).
- **Evidence (2026-10-17, remove-the-references branch; D19 accepted `f355212`):** the AWS deployment branch is closed by removal, not by writing `scripts/deploy.sh`/`scripts/pre_deploy_check.sh` (neither exists; `tests/test_readme_truth.py` forbids the phrases `deploy.sh`, `pre_deploy_check`, `deploy to aws`, `aws` and `ec2`). The README AWS/EC2 sections were deleted in R23 (`f26dee3`) and the residual `DEPLOYMENT.md`/AWS Documentation-table line in R31 (`0b57fc4`); `grep -in 'aws\|ec2' README.md` → no matches. `tests/test_readme_links.py` resolves every relative link, and `tests/test_verify_readme_script.py` keeps the remaining commands executable. **What remains in README is the Docker path** ("Docker Deployment", "Deployment & Operations", `# Deploy new model`) — real, tested behaviour (R25/D30), not an AWS/cloud or deploy-script claim. **Acceptance criteria coverage:** (1) scripts exist + idempotent + `pre_deploy_check.sh` exit codes — **not chosen** (the OR branch); (2) "the AWS/deploy references in README are removed" — **chosen and covered** as above. → **R28 `done`.** **Carried open finding (not an R28 criterion):** `Dockerfile.prod`, `Dockerfile.hf` and the `./models` mounts of `docker-compose.prod.yml`/`docker-compose.hf.yml` still ship no model on a fresh clone — the engine raises `FileNotFoundError` at import and the container exits. Planned fix (D30 follow-up): the same data+model build step plus removing those mounts, verified by building those images in CI in the next batch.

- **Note (2026-10-17) — HF half removed.** `Dockerfile.hf`, `docker-compose.hf.yml`, `start.sh`, and `tests/test_start_sh.py` are deleted (C2 `5aa5d58`). The remaining no-model deploy path is `Dockerfile.prod` + `docker-compose.prod.yml` (proposed D31).

- **Note (2026-10-19) — prod/HF follow-up resolved (D31).** `Dockerfile.prod` and `docker-compose.prod.yml` are deleted (C4); the HF files were deleted earlier (`5aa5d58`). The one remaining image is the main `Dockerfile`, which builds data+model, runs non-root and has a `HEALTHCHECK`. No deployment image ships without a model. This is a carried finding, not an R28 acceptance criterion; R28 remains `done` through its remove-the-references branch.

### R29 — SQLite: use it or remove it
- **Priority:** P2
- **Status:** done
- **Files touched:** `src/data/ingest.py`, `data.db`, `scripts/backup_database.sh`, `scripts/restore_database.sh`, `README.md`
- **Acceptance criteria:** Either the app reads/writes predictions or sales through SQLAlchemy (with a test) and backup/restore is exercised end-to-end, **or** `data.db`, both scripts, the `ingest.py` module, and the README DB claims are removed. No orphan database remains.
- **Depends on:** R22
- **Progress (2026-10-15) — partly resolved, kept open:**
  - **Removed (R22, commit `87fdf8a`, DECISIONS D9):** `src/data/ingest.py` (the only SQLAlchemy consumer), `src/data/pipeline_runner.py`, `src/data/validation.py`, and both DB scripts `scripts/backup_database.sh` / `scripts/restore_database.sh`. `grep` across `start.sh` / `Dockerfile*` / `docker-compose*.yml` / `scripts/*` / `tests` / `.github` → no references.
  - **Remaining:** the local `data.db` still exists on disk (untracked and gitignored; `git status` clean). Per the user's decision recorded as the "Implementation note" under DECISIONS D9, the agent must **not** delete it — the owner will remove it. The README DB claims (`README.md:274,277,377,457` and the `data/ # … ingestion, validation` tree line `:59`) were **struck in R23** (2026-10-16, commit `f26dee3`).
  - **Also flagged (now resolved):** `sqlalchemy==2.1.4` (`requirements.txt:30`) was an unused declared dependency — **removed 2026-10-16** (commit `c936519`, R21 follow-up).
  - **Done (2026-10-18).** The owner deleted `data.db`: `ls -l data.db` → `ls: cannot access 'data.db': No such file or directory` (exit 2). `ls -d .venv.old` → also absent (informational). `src/data/ingest.py`, `scripts/backup_database.sh`, `scripts/restore_database.sh` → absent; `git grep -F 'data.db' -- ':!.agents'` → only `.gitignore:81` (the ignore rule, not a file); `grep -inE 'database|data\.db|backup|restore' README.md` → no matches; `grep -in sqlite README.md` → no matches; `tests/test_readme_truth.py` forbids `sqlite`, `backup_database`, `restore_database`. No orphan database remains → **R29 done**.

### R30 — Raise coverage on the pricing/serving path
- **Priority:** P2
- **Status:** done
- **Files touched:** `tests/*`
- **Acceptance criteria:** `pytest tests/ --cov=src --cov-report=term-missing` reports ≥ 80% for `src/pricing/*` and `src/api/*`, and the number is recorded in README.
- **Depends on:** R7, R8, R9
- **Note (2026-10-17, read-only baseline; no commit):** `COVERAGE_FILE=/tmp/.coverage_r30 ... --cov=src/pricing --cov=src/api --cov-report=term-missing` → combined **89%** (405 statements, 45 missed). Per file: `engine.py` 96%, `features.py` 96%, `optimizer.py` 95%, `router.py` 90%, `server.py` 83%, `middleware.py` 78% (missing 55-65, 91-95, 119-128, 155-161), `error_handlers.py` 63% (missing 44-52, 66-69, 74-84). `--cov=src` overall **87%**. The combined number meets ≥80; **per-file enforcement would fail** on `middleware.py` and `error_handlers.py` (pytest-cov's `--cov-fail-under` applies to the combined total, so a per-file gate needs a custom `coverage json` check). Enforcing command: `pytest tests -q --cov=src/pricing --cov=src/api --cov-report=term-missing --cov-fail-under=80`. R30 stays `todo` (it also requires the number recorded in README); D25 remains `proposed`.
- **Evidence (2026-10-17; tests `dc879c1`, README `792627f`, CI gate `3723295`; D25 accepted `f355212`):** new behaviour-level tests cover the previously missed lines — `tests/test_api_middleware.py` (rate-limit 429 body/window + per-client isolation, `ErrorHandlingMiddleware` generic 500 with `X-Request-ID`, `RequestLoggingMiddleware` error branch + re-raise, `TimeoutMiddleware` 504 in <2 s), `tests/test_api_health_metrics.py` (lifespan/root, readiness, liveness, `/metrics`, 503 degraded/not-ready), `tests/test_health_checker.py` (degraded when the model is missing or the probe raises, readiness, metrics), one `tests/test_evaluator.py` train-metric/overfit-gap test. Mutation checks in a `/tmp` copy: `>=`→`>` in the limiter fails the 429 test; re-raising in `ErrorHandlingMiddleware` fails the 500 test. **Criterion command, run literally:** `pytest tests --cov=src --cov-report=term-missing` → **124 passed**, `src` 93% (784 stmts, 51 missed) and every file under `src/pricing/*` and `src/api/*` ≥ 80%: `api/error_handlers.py` 100%, `api/middleware.py` 100%, `api/router.py` 100%, `api/schemas.py` 100%, `api/server.py` 89% (`97-102` = the `__main__` uvicorn block), `pricing/engine.py` 96%, `pricing/features.py` 96%, `pricing/optimizer.py` 95%. Combined `src/pricing` + `src/api`: **97%** (378/389; `src/api` 98% = 228/233, `src/pricing` 96% = 150/156). The number is recorded in README (Coverage subsection: per package + combined + the exact command). Enforcement is **per file**, not just combined: `scripts/check_coverage.py` reads the coverage JSON and fails any file under either package below 80% (empty allowlist; C3 flagged no file), and `--cov-fail-under=80` covers the combined total. **Acceptance criteria coverage:** (1) ≥ 80% for `src/pricing/*` and `src/api/*` — covered per file (lowest 89%), not only combined; (2) the number is recorded in README — covered (`792627f`). → **R30 `done`.**

### R31 — Every documentation link resolves
- **Priority:** P2
- **Status:** done
- **Files touched:** `README.md`, `tests/test_readme_links.py` (new), `tests/test_readme_truth.py`
- **Acceptance criteria:** A link-check test asserts every relative Markdown link in `README.md` resolves to an existing file. Either the missing docs are created or the links are removed.
- **Depends on:** R23
- **Evidence (2026-10-17, commit `0b57fc4`):** delink branch — no docs were created. README's Documentation table and the two `OPERATIONS.md` pointers were removed, including the `DEPLOYMENT.md`/AWS line. `tests/test_readme_links.py` resolves every inline/reference-style relative target against the repo root after stripping `#fragment`; same-file anchors are checked against GitHub-style heading slugs. **Pre-fix failure (rule 18):** `1 failed` — `README has broken relative links: ['DEPLOYMENT.md', 'PRODUCTION_FEATURES.md', 'PRODUCTION_READY.md', 'docs/API.md', 'docs/OPERATIONS.md']`; **after:** `1 passed`. `tests/test_readme_truth.py` gained the whole word `aws` (no AWS tooling/deployment exists).

### R32 — Document the causal-inference limitation
- **Priority:** P2
- **Status:** done
- **Files touched:** `README.md`, `tests/test_readme_limitations.py` (new), `tests/test_readme_truth.py`
- **Acceptance criteria:** README contains a "Limitations" section stating (a) the demand model is observational, (b) `argmax_price E[units | price]` is not a valid causal pricing policy on real data, and (c) all results are on synthetic data. A test greps for the section heading and its key phrases. This item also carries the folded-in limitations from DECISIONS D22 (rate limiting is in-memory / per worker) and D23 (all data and metrics are synthetic).
- **Depends on:** R12, R23
- **Evidence (2026-10-17, commit `f722b08`):** README has `## Limitations` stating (a) observational, (b) `argmax_price E[units | price]` is not a valid causal policy on real data, (c) all results synthetic, plus D22 (in-memory, **per worker process**, resets on restart) and D23 (synthetic). Additional items are limited to STATE.md/code-proven facts: no authN/authZ or TLS and CORS defaults to `*` (`src/api/server.py:50`); the joblib pickle is tied to the XGBoost version; the MLflow registry is optional and explicitly promoted; no drift monitoring or automated retraining (R15/D13). `tests/test_readme_limitations.py` greps the heading and the key substrings — **pre-fix:** `AssertionError: README has no '## Limitations' section` (`1 failed`), **after:** `1 passed`. `tests/test_readme_truth.py`'s forbidden scan skips **only** the Limitations section (documented in its docstring). `docs/ARCHITECTURE.md` was **not** created: R32 lists it as a file, but its acceptance criteria do not require it.

### R33 — Decide tracking for `.agents/`
- **Priority:** P2
- **Status:** done
- **Files touched:** `.gitignore:86`, `.agents/STATE.md`, `.agents/ROADMAP.md`
- **Acceptance criteria:** Either `.gitignore` no longer ignores `.agents/` and both files are committed, **or** the ignore is kept and explicitly documented as intentional. `git status` is unambiguous about the decision.
- **Evidence:** 2026-09-28 — the `.agents` entry was removed from `.gitignore`; `git check-ignore .agents/STATE.md` returns nothing; `.agents/` and `AGENTS.md` are committed. (Note: the owner's edit had *added* `.agents` to `.gitignore` rather than removing it; corrected here.)
- **Depends on:** none

### P2 status (2026-10-19)

| Item | Final status | Evidence |
|---|---|---|
| R27 — CI workflow | done | Both jobs green after pushing `caae3aa` (user-reported); README CI section + badge (C7); dead metadata removed (`f66a703`). |
| R28 — Deployment scripts or remove claims | done | Remove-the-references branch; the prod/HF no-model follow-up is resolved by D31 and `5aa5d58`. |
| R29 — SQLite use or remove | done | `data.db` deleted by the owner; no consumer remains; README/scripts gone. |
| R30 — Coverage on pricing/serving | done | Every file under `src/pricing` and `src/api` ≥ 80%; number in README; CI per-file gate. |
| R31 — Every documentation link resolves | done | `tests/test_readme_links.py`; missing docs links removed. |
| R32 — Causal-inference limitation | done | `## Limitations` + `tests/test_readme_limitations.py`. |
| R33 — `.agents/` tracking | done | `.agents/` un-ignored and committed. |

**P0/P1/P2:** every item is `done`; nothing remains `todo`, `in-progress` or `blocked` in this roadmap. R27 was the last open item.

## Post-P2 review (parked, not started)

Waiting for the user's go-ahead; no item below is scheduled or implemented.

- ML: compute the noise ceiling of the synthetic generator (oracle R²) to put R²/MAPE in context.
- ML: compare XGBoost against a log-log elasticity baseline.
- ML: consider a monotonic constraint on price.
- ML: evaluate pricing decisions by regret against the generator's true optimum.
- ML: add a small ablation table (features removed).
- Product: define the user, the decision, the success metric (revenue uplift vs a baseline policy) and guardrails (max price change).
- Product: explanations of a recommendation.
- Product: an experiment / A-B plan.
- Optional: replace synthetic data with a public retail dataset that has real price variation.

---

## Suggested execution order (dependency-respecting)

1. **Unblock the core:** R1, R2, R3 (independent — can run in parallel).
2. **Lock in the fix:** R6, R7, R8, R9, R10.
3. **Make the demo coherent:** R4, R5, R11, R12, R13, R14.
4. **Make it honest and operable:** R15–R26, R34, R35.
5. **Polish:** R27–R33.

**Sequencing note:** R12 (step 3) retrains the model. **Re-run R7 after R12** — R7 derives
its reference from the working-tree (gitignored) artifact at test time, so its prior pass is invalidated by
the retrain. R7 must also be re-run after any other item that rewrites
`models/demand_model.pkl`.

**Definition of done for the whole roadmap:** `pytest tests/` is green; R7's real-model
test passes; the Streamlit Quick tab returns a real optimum end-to-end; `README.md`
contains only claims that map to `CONFIRMED`/`PARTIAL` rows in `.agents/STATE.md`; and
`docker compose up` brings up a working, health-checked API from a clean checkout.

---

Last updated: 2026-10-17, against commit `792627f` (this batch: **D7, D18–D21, D24, D25 accepted** (`f355212`); **R30 → done** — per-file coverage with the criterion command (every file ≥ 80%, lowest `server.py` 89%; combined 97%), recorded in README and enforced by `scripts/check_coverage.py` + `--cov-fail-under=80`; **R28 → done** through the remove-the-references branch (no AWS/EC2 or deploy-script references; forbidden-phrase + link tests); **R27 → in-progress** — workflow + local CI scripts landed (`3723295`) and `bash scripts/ci_check.sh` passes locally and in a fresh clone (124 passed, 0 skipped, 97%), but the first GitHub run and the README CI-status line are still outstanding. Suite **99 → 124 passed, 0 skipped**. Previous: 2026-10-17, against commit `f722b08` (**R31 → done** (`0b57fc4`) and **R32 → done** (`f722b08`) — the five missing docs links were delinked (no docs created) and a link-check test was added; a `## Limitations` section and its test were added; C1 `a67a505` made the multi-seed mean the headline and seed 42 the reference run; suite **97 → 99 passed, 0 skipped**. R27/R28/R30 gained read-only notes; R28 stays open on proposed D19. Previous session: 2026-10-16, against commit `5e17dbc` (**R23 reopened and properly closed** — C1 `5e17dbc` added `scripts/verify_readme.sh` (README quickstart end-to-end on a clean HEAD checkout; real run all-PASS, exit 0; mutation check → FAIL, exit 1) + `tests/test_verify_readme_script.py` (5 tests) + a minimal README alignment; C2 no commit (README already presents both the seed-1–10 mean and the seed-42 reference); C3 docs; **`.venv` rebuilt from `requirements.txt` by the owner**; suite **92 → 97 passed, 0 skipped**. Previous: **D4/D8/D11 accepted** (`ddc04d2`); **unused `sqlalchemy` pin removed** (`c936519`, R21 follow-up); **R23 → done** (`f26dee3` README truth pass + `tests/test_readme_truth.py`, `7ca9014` `scripts/load_test.sh` `bayesian`→`grid_search`) — full audit table + fresh-clone walkthrough in LOG.md, suite **90 → 92 passed, 0 skipped**; **all P1 items are now done**. Previous: 2026-10-15, against commit `e8da719` (this session: **R22 → done** — D9/D10/D12 accepted (`55ae934`); added the live-path inventory-cap tests (`0b73403`, mutation-checked); deleted `BayesianPriceOptimizer` + its 18 dead tests (`c4b9fb1`), the orphan modules `revenue`/`metrics_tracker`/`optimize`/`feature_pipeline` (`3b51851`), `utils/config` (`026ed00`), the SQLite chain `data/{ingest,pipeline_runner,validation}` + `scripts/{backup,restore}_database.sh` (`87fdf8a`), `pricing/model_loader` + its engine import (`849a866`), the never-raised error subclasses (`49243af`), and the dead symbols `log_prediction`/`load_logs`/`get_env`/`EcommerceDataGenerator.run` (`fb5e2a5`); added `tests/test_import_graph.py` (`e8da719`, FAILS on pre-R22 `62333ea` listing 11 dead modules); R22 carries the committed disposition table; suite **104 → 90 passed, 0 skipped**; **R29 → in-progress** (ingestion + DB scripts removed, `data.db` kept per the D9 note, README DB claims left for R23); R23 gained the new stale-README sentences; **D4/D8/D11 remain `proposed`**. Previous: **R22 group 1 → done** (DECISIONS D1) — deleted `src/pricing/integrated_optimizer.py`, `src/features/transformer.py`, `tests/test_integration.py` (commit `7368ef1`); suite **107 → 102 passed, 2 skipped**; **R22 group 2 (Bayesian) BLOCKED** — the coverage-preservation check found the live-optimizer inventory-cap property asserted only by a to-be-deleted mock test, so nothing was deleted (see R22); **R14 follow-up → done** — `scripts/run_smoke_tests.sh` now runs `python3 -m pytest` (commit `9f0dc1d`); R23 gained a note on the three remaining `"bayesian"` strings and the `app.py` product-id input. Previous: **R14 → done, R34 → done** — `tests/smoke_tests.py` is now a collectable pytest module (8 tests; `--collect-only` was 0/exit 5; offline → 8 skipped, exit 0; against a live API on `127.0.0.1:8765` → 8 passed) with a skip-when-offline fixture, and `PricingRequest.product_id`'s description now states it is accepted for compatibility only and is **not** a model feature (`tests/test_product_id_contract.py`, 4 tests); suite → **107 passed, 2 skipped**; R27 gained a note that CI must start the API for the smoke tests to actually run. Previous: **R25 → done** — a fresh `git clone --no-hardlinks` into `/tmp/dp_clone` + `docker compose build/up pricing-api` built the model **inside the image** (`/app/models/demand_model.pkl`, 2,658,806 bytes) and served `curl http://localhost:8000/v1/health` → **HTTP 200** (build 8.7 s **cached**, not a cold build; the earlier cold build was 1590 s); `/app/.env` and `/app/mlflow.db` absent from the image — so the **clean-checkout** criterion is now met and R25 is `done`. R25 follow-up notes added (the `mlflow` service's per-start `pip install` on `python:3.10`; the obsolete `version:` key; the unread `MONITORING_ENABLED`; and the prod/hf/no-model gap recorded under **R28**). **Task A seed sweep** (read-only, fresh clones, seeds 1–10 + 42): R² **0.40602–0.50037** (mean **0.44650**, std 0.02919), MAPE **0.34671–0.37953** (mean 0.36080); seed 42 → R² 0.41930 / MAPE 0.35093; every seed's R7 suite green. Convention 35 added. Previous: D30 accepted/implemented — the synthetic generator is seeded (`seed` default 42), `scripts/regenerate_data.py` reads `data.n_products`/`data.days`/`data.seed` from `configs/config.yaml`, and the **main** `Dockerfile` builds data + model after `COPY . .` while `.dockerignore` excludes `models/*.pkl` + `data/features/`; two clean clones at `d29dfa8` produce byte-identical data and an identical pickle (`95347c4f…`), offline; the retrained artifact is `R2 0.41930 / MAPE 0.35093` (was 0.475/0.346 — R² moved ≈0.056); the XGBoost "older version" warning is gone; unit-tests row → **103 passed, 2 skipped**). **R25 stays `in-progress`** — the main image now builds its own model, so the remaining acceptance is the **owner's** clean-checkout `docker compose build` + health check; `Dockerfile.prod`/`Dockerfile.hf`/the prod `./models` mount still ship no model (open). Earlier same day: D29 accepted/implemented — `.dockerignore` now **tracked** (its `.gitignore` entry removed) + de-indented + `.env` excluded (`b174774`/`a6170b6`); R25 user-run 2026-10-15: `curl http://localhost:8000/v1/health` → **HTTP 200** (the 2026-10-14 HTTP 000 was not reproduced), but the **clean-checkout** criterion is unmet (a fresh clone has no `models/demand_model.pkl`) → **R25 stays in-progress**; R27 gained a note on the ~31 silent skips (vacuous-green CI risk); clean-clone open findings recorded in `.agents/STATE.md` §7; earlier: D28 accepted/implemented — `mlflow.db` untracked + ignored `ad64722`/`93bf8da`, Dockerfile BuildKit pip cache mount `88b1e86`; **R21 → done** — user-verified fresh-venv `pip install -r requirements.txt` + `pip check` on 2026-10-14; R24 nginx removed `a1eb669` → done; R21 `c444973`/R25 `ce4f2e7` changes committed 2026-10-13; D16/D17/D26/D27 accepted; R35 `5a8f887`; R26 `7cdbf56`; R18–R20 done 2026-10-08; see `.agents/STATE.md`).
