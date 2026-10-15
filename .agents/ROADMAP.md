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
- **Status:** todo
- **Files touched:** `tests/smoke_tests.py`, `scripts/run_smoke_tests.sh`
- **Acceptance criteria:** `pytest tests/smoke_tests.py` collects ≥ 8 tests. Against a locally started API they pass; when no API is reachable they **skip** (not error) via a fixture. The README's smoke-test command is updated.
- **Depends on:** R8

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

### R22 — Dead code: delete or wire+test, file by file
- **Priority:** P1
- **Status:** todo
- **Files touched:** `src/pricing/{integrated_optimizer,revenue,model_loader,optimize}.py`, `src/features/{transformer,feature_pipeline}.py`, `src/monitoring/metrics_tracker.py`, `src/data/{ingest,pipeline_runner,validation}.py`, `src/utils/config.py`, `src/api/error_handlers.py:72-90`, `src/pricing/engine.py:163`
- **Acceptance criteria:** Each file/item above is explicitly dispositioned in a committed table as **deleted** or **wired** (with a test proving reachability). An import-graph test asserts every module under `src/` is reachable from `src.api.server` or a training entry point, or is on an explicit allowlist. STATE.md §3 no longer lists the item. `src/pricing/integrated_optimizer.py` and `src/features/transformer.py` are deleted (DECISIONS D1).
- **Depends on:** R1, R2, R15

### R23 — README truth pass
- **Priority:** P1
- **Status:** todo
- **Files touched:** `README.md`, `scripts/verify_readme.sh` (new)
- **Acceptance criteria:** Every command in README runs successfully on a clean checkout (captured by `scripts/verify_readme.sh`, exit 0). The curl example includes `/v1`. The R² figure is the exact regenerated number and is accompanied by MAPE. Every headline claim maps to a `CONFIRMED` or `PARTIAL` row in STATE.md; no unbacked "production-ready / enterprise-grade" claims remain. The README documents the in-memory rate-limit limitation (single process / per worker) and states plainly that all data and metrics are synthetic (DECISIONS D22/D23, folded into this item).
- **Depends on:** R1, R2, R6, R12, R15, R24

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
- **Status:** in-progress
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
- **R25 acceptance criteria — covered vs not (2026-10-15):**
  - ✅ `docker compose build && docker compose up -d` succeeds — user-run (build 1590 s; three containers Up).
  - ✅ standard public base image (no private mirror) — `python:3.12-slim` (verified `ce4f2e7`).
  - ✅ `curl http://localhost:8000/v1/health` → **200** — user-run 2026-10-15 (the 2026-10-14 HTTP 000 was not reproduced).
  - ✅ `pricing-api` has a `build:` context — `docker-compose.yml:36-38`.
  - ✅ base-image Python (3.12) matches the tested interpreter (3.12.3) — Dockerfiles bumped in `ce4f2e7`.
  - ❌ **"from a clean checkout"** — the build was run in the **working tree**, not a fresh clone. The agent clean-clone investigation (2026-10-15, `/tmp/clean_clone`) shows a fresh clone has **no `models/demand_model.pkl`** (gitignored), so a clean-checkout image would have no model to serve. R25's title scopes to a clean checkout, so this criterion is **not** covered.
  - ⚠️ `mlflow-server` :5000 health — unverified (dependency download incomplete on the throttled network).
  → **R25 stays `in-progress`** (the clean-checkout criterion is unmet).

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

### R34 — `PricingRequest.product_id` is accepted but unused (latent contract mismatch)
- **Priority:** P1
- **Status:** todo
- **Files touched:** `src/api/schemas.py:9`, `app.py`, `tests/test_api.py`, `tests/smoke_tests.py`, `README.md`
- **Acceptance criteria:** Either (a) `product_id` is removed from `PricingRequest` and every caller that sends it is updated in the same PR (UI, tests, README example), **or** (b) it is kept but its `Field` description states plainly that it is accepted for request compatibility and is **not** a model feature, with a test asserting `"product_id"` is absent from the served feature columns. Either way the request schema no longer implies `product_id` influences the predicted demand/price.
- **Depends on:** R12
- **Note:** R12/D5 removed `product_id` from the model feature list, but `PricingRequest` still declares it as a required field (`src/api/schemas.py:9`) and the serving path silently drops it (the feature builder restricts to the committed columns). Harmless today — the tests pass and the response is unaffected — but a latent mismatch: a client sending `product_id` would reasonably expect it to change the price. Flagged here rather than fixed inline because it touches the UI/tests/README contract, not just the schema.

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
- **Status:** todo
- **Files touched:** `.github/workflows/ci.yml` (new), `README.md`
- **Acceptance criteria:** On push, the workflow runs `pytest tests/` (green per R8) and `docker build`, and its status is documented in README. **OR** all CI/CD claims are removed from README. Dead CI metadata in `scripts/train_with_tuning.py:28-35` is removed or actually exercised.
- **Depends on:** R8, R25
- **Note (2026-10-15, clean-clone investigation):** on a fresh clone with no `models/demand_model.pkl` or features parquet, the baseline suite is **54 passed, 33 skipped, 11 errors** (all `FileNotFoundError: models/demand_model.pkl`), and ~**31** tests **skip silently** when the model/parquet is absent. A CI workflow (this item) that runs `pytest tests/` **without first building the data + model would be vacuously green**; it must run `python scripts/regenerate_data.py && python -m src.training.train` before the suite. (Building the data + model in a clean clone then yields 96 passed, 2 skipped — see `.agents/STATE.md` §7.)

### R28 — Deployment scripts, or remove the claims
- **Priority:** P2
- **Status:** todo
- **Files touched:** `scripts/deploy.sh`, `scripts/pre_deploy_check.sh` (new) or `README.md`
- **Acceptance criteria:** The scripts exist, are idempotent, and `pre_deploy_check.sh` exits 0 on a healthy checkout and non-zero when a required artifact is missing. **OR** the AWS/deploy references in README are removed.
- **Depends on:** R25

### R29 — SQLite: use it or remove it
- **Priority:** P2
- **Status:** todo
- **Files touched:** `src/data/ingest.py`, `data.db`, `scripts/backup_database.sh`, `scripts/restore_database.sh`, `README.md`
- **Acceptance criteria:** Either the app reads/writes predictions or sales through SQLAlchemy (with a test) and backup/restore is exercised end-to-end, **or** `data.db`, both scripts, the `ingest.py` module, and the README DB claims are removed. No orphan database remains.
- **Depends on:** R22

### R30 — Raise coverage on the pricing/serving path
- **Priority:** P2
- **Status:** todo
- **Files touched:** `tests/*`
- **Acceptance criteria:** `pytest tests/ --cov=src --cov-report=term-missing` reports ≥ 80% for `src/pricing/*` and `src/api/*`, and the number is recorded in README.
- **Depends on:** R7, R8, R9

### R31 — Every documentation link resolves
- **Priority:** P2
- **Status:** todo
- **Files touched:** `docs/API.md`, `docs/OPERATIONS.md`, `DEPLOYMENT.md`, `PRODUCTION_FEATURES.md`, `PRODUCTION_READY.md` (create) or `README.md` (delink)
- **Acceptance criteria:** A link-check test asserts every relative Markdown link in `README.md` resolves to an existing file. Either the missing docs are created or the links are removed.
- **Depends on:** R23

### R32 — Document the causal-inference limitation
- **Priority:** P2
- **Status:** todo
- **Files touched:** `README.md`, `docs/ARCHITECTURE.md` (new)
- **Acceptance criteria:** README contains a "Limitations" section stating (a) the demand model is observational, (b) `argmax_price E[units | price]` is not a valid causal pricing policy on real data, and (c) all results are on synthetic data. A test greps for the section heading and its key phrases. This item also carries the folded-in limitations from DECISIONS D22 (rate limiting is in-memory / per worker) and D23 (all data and metrics are synthetic).
- **Depends on:** R12, R23

### R33 — Decide tracking for `.agents/`
- **Priority:** P2
- **Status:** done
- **Files touched:** `.gitignore:86`, `.agents/STATE.md`, `.agents/ROADMAP.md`
- **Acceptance criteria:** Either `.gitignore` no longer ignores `.agents/` and both files are committed, **or** the ignore is kept and explicitly documented as intentional. `git status` is unambiguous about the decision.
- **Evidence:** 2026-09-28 — the `.agents` entry was removed from `.gitignore`; `git check-ignore .agents/STATE.md` returns nothing; `.agents/` and `AGENTS.md` are committed. (Note: the owner's edit had *added* `.agents` to `.gitignore` rather than removing it; corrected here.)
- **Depends on:** none

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

Last updated: 2026-10-15, against commit `a6170b6` (D29 accepted/implemented — `.dockerignore` now **tracked** (its `.gitignore` entry removed) + de-indented + `.env` excluded (`b174774`/`a6170b6`); R25 user-run 2026-10-15: `curl http://localhost:8000/v1/health` → **HTTP 200** (the 2026-10-14 HTTP 000 was not reproduced), but the **clean-checkout** criterion is unmet (a fresh clone has no `models/demand_model.pkl`) → **R25 stays in-progress**; R27 gained a note on the ~31 silent skips (vacuous-green CI risk); clean-clone open findings recorded in `.agents/STATE.md` §7; earlier: D28 accepted/implemented — `mlflow.db` untracked + ignored `ad64722`/`93bf8da`, Dockerfile BuildKit pip cache mount `88b1e86`; **R21 → done** — user-verified fresh-venv `pip install -r requirements.txt` + `pip check` on 2026-10-14; R24 nginx removed `a1eb669` → done; R21 `c444973`/R25 `ce4f2e7` changes committed 2026-10-13; D16/D17/D26/D27 accepted; R35 `5a8f887`; R26 `7cdbf56`; R18–R20 done 2026-10-08; see `.agents/STATE.md`).
