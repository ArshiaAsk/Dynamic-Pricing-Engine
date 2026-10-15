"""Real-model optimizer regression tests (ROADMAP R7).

These are the tests that would have caught the R1 and R2 optimizer bugs. They
run against the committed artifacts ``models/demand_model.pkl`` and
``models/features.json`` — never against a mock — so a mock that happens to be
smooth cannot hide a broken optimizer (CONVENTIONS rule 14).

Every reference value (the revenue-optimum of the model on a given bound pair)
is computed **at test time** from the loaded model and the given bounds
(CONVENTIONS rule 34). No model-derived number is hardcoded, so this file stays
valid across retrains such as ROADMAP R12.

Covered acceptance criteria:

* R2 — the grid optimizer builds the complete feature frame (no ``KeyError``)
  and reaches the reference optimum.
* R6 — the served grid optimizer (adaptive default resolution, no caller-chosen
  step count) reaches the reference optimum on narrow and wide bounds alike, so
  making ``grid_search`` the sole served method does not regress revenue.

The former R1 tests exercised the (now-deleted) Bayesian optimizer, which R22
removed as unreachable from serving (DECISIONS D1/D2). The near-optimality
property those tests asserted is now carried by the R2/R6 tests against the
served ``PriceOptimizer``.
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from src.pricing.optimizer import PriceOptimizer

REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = REPO_ROOT / "models" / "demand_model.pkl"
FEATURES_PATH = REPO_ROOT / "models" / "features.json"

# Minimum reference resolution required by the R1/R2 criteria.
REFERENCE_POINTS = 901
# Revenue tolerance from the criteria: result must be within 1% of the optimum.
REVENUE_RATIO = 0.99

# Standard serving input (the same base_features used to verify R1/R2).
# These are request inputs, not model-derived reference values.
BASE_FEATURES = {
    "product_id": 42,
    "competitor_price": 89.99,
    "dow": 2,
    "is_weekend": 0,
    "week": 15,
    "month": 4,
    "sin_annual": 0.5,
    "cos_annual": 0.866,
    "lag_units_sold_1": 45.0,
    "lag_units_sold_7": 42.0,
    "lag_units_sold_14": 40.0,
    "roll_mean_units_7": 43.5,
    "roll_mean_units_14": 41.2,
    "roll_mean_units_28": 39.8,
    "roll_std_units_7": 5.2,
    "roll_std_units_14": 6.1,
    "roll_std_units_28": 7.3,
}

R1_BOUNDS = [(30.0, 80.0), (70.0, 110.0), (10.0, 200.0), (100.0, 120.0), (30.0, 120.0)]
GRID_BOUNDS = (70.0, 110.0)
GRID_STEPS = 50


@pytest.fixture(scope="module")
def real_model():
    """The committed demand model (skip only if the artifact is absent)."""
    if not MODEL_PATH.exists():
        pytest.skip(f"Committed model not found: {MODEL_PATH}")
    return joblib.load(MODEL_PATH)


@pytest.fixture(scope="module")
def real_feature_columns():
    """The committed feature-column list the model was trained on."""
    if not FEATURES_PATH.exists():
        pytest.skip(f"Committed feature list not found: {FEATURES_PATH}")
    with open(FEATURES_PATH) as fh:
        return json.load(fh)


def _serving_features(base_features, price):
    """Independent oracle for the 31-column serving feature contract.

    Deliberately does not call the optimizers' ``_build_features`` so the
    reference optimum is not derived from the code under test: on the pre-R2
    code that builder dropped 9 columns, and a circular reference would have
    hidden the bug.
    """
    features = dict(base_features)
    features["price"] = price

    comp_price = features.get("competitor_price")
    if comp_price is not None:
        features["price_ratio"] = price / comp_price if comp_price > 0 else 1.0
        features["price_diff_pct"] = (price - comp_price) / comp_price if comp_price > 0 else 0.0

    features["price_ratio_sin"] = features.get("price_ratio", 1.0) * features["sin_annual"]
    features["price_ratio_cos"] = features.get("price_ratio", 1.0) * features["cos_annual"]

    if comp_price is not None:
        features["price_advantage"] = (comp_price - price) / comp_price if comp_price > 0 else 0.0
        features["log_comp_price"] = float(np.log1p(comp_price)) if comp_price >= 0 else 0.0
    features["log_price"] = float(np.log1p(price)) if price >= 0 else 0.0
    features["price_advantage_sin"] = features.get("price_advantage", 0.0) * features["sin_annual"]

    features.setdefault("price_change_1d", 0.0)
    features.setdefault("price_change_7d", 0.0)
    features.setdefault("roll_mean_price_7", price)
    features.setdefault("roll_mean_price_14", price)
    features.setdefault("roll_mean_price_28", price)
    return features


def _reference_curve(model, feature_columns, base_features, price_min, price_max,
                     points=REFERENCE_POINTS):
    """Revenue for a dense price grid, computed at test time from the model."""
    prices = np.linspace(price_min, price_max, points)
    frame = pd.DataFrame(
        [_serving_features(base_features, float(p)) for p in prices]
    )[feature_columns]
    demand = np.asarray(model.predict(frame), dtype=float).reshape(-1)
    return prices, demand, prices * demand


# --------------------------------------------------------------------------- #
# R2 — grid optimizer builds the full feature frame and reaches the optimum
# --------------------------------------------------------------------------- #

def test_grid_optimizer_builds_complete_feature_frame(real_feature_columns):
    """R2: the price-dependent frame contains every committed feature column.

    As of R4 both optimizers share a single builder
    (:func:`src.pricing.features.build_serving_features`), so this asserts the
    shared frame is complete and ordered for the committed model columns.
    """
    from src.pricing.features import build_serving_features

    features = build_serving_features(BASE_FEATURES, price=77.0, feature_columns=real_feature_columns)
    missing = [col for col in real_feature_columns if col not in features]
    assert missing == []
    assert list(features.keys()) == list(real_feature_columns)


def test_grid_optimizer_reaches_reference_optimum(real_model, real_feature_columns):
    """R2: optimize(base, 70, 110, 50) returns without raising and is near-optimal."""
    _, _, reference_revenue = _reference_curve(
        real_model, real_feature_columns, BASE_FEATURES, *GRID_BOUNDS
    )
    reference_max = float(np.max(reference_revenue))

    optimizer = PriceOptimizer(real_model, real_feature_columns)
    result = optimizer.optimize(BASE_FEATURES, *GRID_BOUNDS, steps=GRID_STEPS)

    assert GRID_BOUNDS[0] <= result["optimal_price"] <= GRID_BOUNDS[1]
    assert result["expected_revenue"] >= REVENUE_RATIO * reference_max


# --------------------------------------------------------------------------- #
# R6 — the served grid optimizer reaches the optimum across all bound widths
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("price_min,price_max", R1_BOUNDS)
def test_served_grid_optimizer_reaches_reference_optimum(
        real_model, real_feature_columns, price_min, price_max):
    """R6: the served grid search (adaptive default resolution) is near-optimal.

    ``grid_search`` is the only method served after R6, so it must reach
    >= 0.99x the test-time 901-point reference on narrow and wide bounds alike —
    the fixed 50-point grid undershot wide ranges (e.g. ~0.971 on ``(30,120)``).
    """
    _, _, reference_revenue = _reference_curve(
        real_model, real_feature_columns, BASE_FEATURES, price_min, price_max
    )
    reference_max = float(np.max(reference_revenue))

    optimizer = PriceOptimizer(real_model, real_feature_columns)
    result = optimizer.optimize(BASE_FEATURES, price_min, price_max)

    assert price_min <= result["optimal_price"] <= price_max
    assert result["expected_revenue"] >= REVENUE_RATIO * reference_max
