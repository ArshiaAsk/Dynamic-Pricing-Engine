# R1: Replace the non-functional "Bayesian" optimizer with a real search

**Reference commits:** Ground truth verified against commit `c32841f` (see `.agents/STATE.md`).
This task file belongs to the current planning revision, which sits on top of the working tree at
the current commit (see `git log -1`); no new commit was created for these `.agents/` edits.

## Goal

Make the default price optimizer actually find a revenue-maximizing price for the committed
XGBoost model. Today it calls a gradient-based optimizer (`scipy.optimize.minimize`,
`method='L-BFGS-B'`) on a piecewise-constant tree objective, so it terminates at a price bound
or at the initial midpoint. Replace that with a derivative-free global search (a vectorized
dense price grid is the recommended approach) so that the returned price achieves (near-)maximum
revenue and `optimization_success` reflects reality.

## Current broken behavior

Bug location: `src/pricing/bayesian_optimizer.py:28` (default `method='L-BFGS-B'`) and
`src/pricing/bayesian_optimizer.py:74-80` (the `minimize(...)` call). The objective at
`src/pricing/bayesian_optimizer.py:46-65` is `-price * model.predict(...)`, and the model is an
`XGBRegressor` (piecewise constant), so the numerical gradient is ~0 and the solver stops
immediately.

Reproduce directly against the committed model (run from repo root):

```bash
../venv/bin/python - <<'PY'
import json, joblib, numpy as np, pandas as pd
from src.pricing.bayesian_optimizer import BayesianPriceOptimizer
model = joblib.load("models/demand_model.pkl")
feats = json.load(open("models/features.json"))
base = {"product_id":42,"competitor_price":89.99,"dow":2,"is_weekend":0,"week":15,"month":4,
        "sin_annual":0.5,"cos_annual":0.866,"lag_units_sold_1":45.0,"lag_units_sold_7":42.0,
        "lag_units_sold_14":40.0,"roll_mean_units_7":43.5,"roll_mean_units_14":41.2,
        "roll_mean_units_28":39.8,"roll_std_units_7":5.2,"roll_std_units_14":6.1,
        "roll_std_units_28":7.3}
b = BayesianPriceOptimizer(model, feats)
for lo, hi in [(30,80),(70,110),(10,200),(100,120)]:
    r = b.optimize(base, lo, hi)
    print((lo,hi), "->", round(r["optimal_price"],4), r["optimization_success"], r["optimization_iterations"])
PY
```

Observed output (real model):

```
(30, 80)  -> 80.0  True  1     # returns the upper bound
(70, 110) -> 90.0  False 0     # returns the initial midpoint, solver never moved
(10, 200) -> 200.0 True  2     # returns the upper bound
(100, 120)-> 120.0 True  1     # returns the upper bound
```

So 4 of 5 ranges return a bound/midpoint. The one that lands near the optimum does so
accidentally and reports failure. Because the objective is piecewise-constant, the correct
comparison is on **revenue**, not price: several prices can tie at the same maximum revenue, so
a "within 0.5 of the grid argmax price" test is both fragile and wrong. Compute the reference
maximum over a ≥ 901-point grid **at test time** with the same model and bounds — do not
hardcode a price (the old criteria froze a single number, which any retrain would invalidate;
see CONVENTIONS rule 34).

Same failure through the API (`POST /v1/optimize-price` with `"price_min":70.0, "price_max":110.0`,
`"optimization_method":"bayesian"`) returns `optimal_price=90.0, optimization_success=False,
optimization_iterations=0` (HTTP 200).

## Relevant files

- `src/pricing/bayesian_optimizer.py` — the optimizer to fix (`optimize` at :21, `_build_features` at :106, `optimize_with_constraints` at :142).
- `src/pricing/engine.py` — dispatches the optimizer and sets `optimization_method` on the result (`:129-158`).
- `src/api/schemas.py` — `PricingResponse` fields the result must satisfy (`:79-94`).
- `src/api/router.py` — calls the engine and logs the result (`:60-89`).
- `models/demand_model.pkl`, `models/features.json` — the committed artifact the optimizer must be tested against.
- `src/pricing/optimizer.py` — the existing grid implementation; read for reference only (its bug is a separate task, see Out of scope).

> **Interim only — this file is not the optimizer's permanent home.** Fixing
> `src/pricing/bayesian_optimizer.py` in place is a deliberate **interim** step. Per accepted
> decision **D1** ("one optimizer module, one strategy"), once ROADMAP **R6** locks `"bayesian"`
> as a rejected method value (HTTP 422), this module becomes **unreachable from the API** and must
> be retired or merged into the single canonical optimizer by a later task (R4 unification / R22
> dead-code cleanup). **R1 itself must not delete, rename, or merge the file** — it only fixes the
> algorithm inside it. Do not assume this file is its permanent location.

## Acceptance criteria

Against the committed `models/demand_model.pkl` + `models/features.json`, using the standard
`base_features` in the reproduction above, for each bound pair `(30,80)`, `(70,110)`,
`(10,200)`, `(100,120)`, and `(30,120)`:

1. The returned `expected_revenue` is **≥ 0.99 ×** the maximum revenue over a fine grid of **≥ 901 points** on the same bounds, where the reference grid is computed **at test time with the same model and the same bounds** — no hardcoded numbers.
2. `optimization_success` is `True`.
3. The returned `optimal_price` lies within `[price_min, price_max]`.
4. For any range where the reference grid's argmax is **strictly interior** (more than one grid step from both bounds), the returned price must not sit on a bound.
5. No gradient-based call remains on the tree objective: `grep -n "L-BFGS-B\|minimize(" src/pricing/bayesian_optimizer.py` returns nothing that operates on the model output.
6. The return contract is unchanged: a dict containing at least `optimal_price`, `expected_demand`, `expected_revenue`, `optimization_success`, `optimization_iterations`, all JSON-serializable (`PricingResponse(**result)` still validates).
7. `optimize_with_constraints(base, price_min, price_max, cost=60.0, min_margin_pct=0.15)` still returns `profit_margin >= 0.15 - 0.01` and a price inside the (margin-adjusted) bounds.

Verification method for this task: re-run the reproduction command, compute the reference grid
maximum at runtime, and record the observed numbers in `.agents/LOG.md`. The committed,
permanent regression test is ROADMAP **R7** and is a separate task.

## Out of scope

- **Do not fix the grid optimizer.** `src/pricing/optimizer.py`'s `KeyError` is ROADMAP R2. Leave that file alone.
- **Do not fix the frontend/backend field-name mismatch** (`predicted_demand` vs `expected_demand`) — that is ROADMAP R10, a separate item.
- **Do not add or change the canonical method name / alias** (`grid_search`, alias `grid`) — that is ROADMAP R6 / DECISIONS D2.
- **Do not unify feature construction into a shared builder.** Extracting one canonical serving feature builder is ROADMAP R4; for this task use the existing `_build_features` as-is.
- **Do not change the MLflow import/fallback behavior** (`engine.py`). Making mlflow lazy/optional is ROADMAP R3; if the API cannot be started locally due to the mlflow/protobuf conflict, verify through the direct Python reproduction instead of changing the engine.
- **Do not rename the "bayesian" method or relabel it in docs** — that is DECISIONS D2 / ROADMAP R6.
- **Do not modify training code, data generation, or the committed model/metrics artifacts.**
- **Do not create `tests/test_optimizer_real.py`** — the committed regression test is ROADMAP R7.
- **Do not implement any `proposed` decision in `.agents/DECISIONS.md`.** Only D1, D2, and D15
  are currently `accepted` (D15 concerns tracking `.agents/`, not pricing); **every other entry is
  still `proposed` and must not be implemented.** In particular **D6** (chronological
  train/validation split) and **D5** (dropping `product_id` as a model feature) are tempting here
  because R1 touches the optimizer's price feature frame, but both change training / feature
  engineering (ROADMAP R12), which is out of scope. Even the accepted D1/D2 do not license touching
  feature engineering or training code in R1.

---

Last updated: 2026-09-28, against commit c32841f (see `.agents/STATE.md`).
