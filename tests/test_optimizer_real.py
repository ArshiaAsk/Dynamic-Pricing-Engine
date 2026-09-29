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

* R1 — the derivative-free optimizer returns the revenue optimum (>= 0.99x a
  >= 901-point reference grid computed here), reports success, stays in bounds,
  does not hug a bound when the reference optimum is interior, keeps the result
  contract, and honours the margin constraint; no gradient method remains.
* R2 — the grid optimizer builds the complete 31-column feature frame (no
  ``KeyError``) and also reaches the reference optimum.
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from src.api.schemas import PricingResponse
from src.pricing.bayesian_optimizer import BayesianPriceOptimizer
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
# R1 — derivative-free optimizer reaches the true revenue optimum
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("price_min,price_max", R1_BOUNDS)
def test_bayesian_reaches_reference_optimum(real_model, real_feature_columns,
                                            price_min, price_max):
    """R1: revenue >= 0.99x the test-time reference max; success; in bounds."""
    _, _, reference_revenue = _reference_curve(
        real_model, real_feature_columns, BASE_FEATURES, price_min, price_max
    )
    reference_max = float(np.max(reference_revenue))

    optimizer = BayesianPriceOptimizer(real_model, real_feature_columns)
    result = optimizer.optimize(BASE_FEATURES, price_min, price_max)

    assert result["optimization_success"] is True
    assert price_min <= result["optimal_price"] <= price_max
    assert result["expected_revenue"] >= REVENUE_RATIO * reference_max


@pytest.mark.parametrize("price_min,price_max", R1_BOUNDS)
def test_bayesian_not_on_bound_when_reference_optimum_is_interior(
        real_model, real_feature_columns, price_min, price_max):
    """R1: when the reference argmax is strictly interior, the result is too."""
    prices, _, reference_revenue = _reference_curve(
        real_model, real_feature_columns, BASE_FEATURES, price_min, price_max
    )
    reference_argmax = float(prices[int(np.argmax(reference_revenue))])
    step = (price_max - price_min) / (REFERENCE_POINTS - 1)
    interior = (reference_argmax - price_min > step) and (price_max - reference_argmax > step)
    if not interior:
        pytest.skip("Reference optimum lies on a bound; bound-hugging rule does not apply")

    optimizer = BayesianPriceOptimizer(real_model, real_feature_columns)
    result = optimizer.optimize(BASE_FEATURES, price_min, price_max)

    assert price_min < result["optimal_price"] < price_max


def test_bayesian_result_contract(real_model, real_feature_columns):
    """R1: result dict has the documented keys, is JSON-safe and schema-valid."""
    optimizer = BayesianPriceOptimizer(real_model, real_feature_columns)
    result = optimizer.optimize(BASE_FEATURES, *GRID_BOUNDS)

    for key in ("optimal_price", "expected_demand", "expected_revenue",
                "optimization_success", "optimization_iterations"):
        assert key in result

    json.dumps(result)  # must be JSON-serializable
    PricingResponse(**result)  # must satisfy the API response contract


def test_bayesian_constraints_respect_margin_and_bounds(real_model, real_feature_columns):
    """R1: the margin-adjusted optimization keeps the margin and stays in bounds."""
    cost, min_margin = 60.0, 0.15
    optimizer = BayesianPriceOptimizer(real_model, real_feature_columns)
    result = optimizer.optimize_with_constraints(
        BASE_FEATURES, 30.0, 120.0, cost=cost, min_margin_pct=min_margin
    )

    assert result["profit_margin"] >= min_margin - 0.01
    assert cost * (1 + min_margin) - 0.01 <= result["optimal_price"] <= 120.0


def test_no_gradient_method_remains_on_tree_objective():
    """R1: the scipy gradient solver must not operate on the tree objective."""
    source = (REPO_ROOT / "src" / "pricing" / "bayesian_optimizer.py").read_text()
    assert "L-BFGS-B" not in source
    assert "minimize(" not in source


# --------------------------------------------------------------------------- #
# R2 — grid optimizer builds the full feature frame and reaches the optimum
# --------------------------------------------------------------------------- #

def test_grid_optimizer_builds_complete_feature_frame(real_model, real_feature_columns):
    """R2: the price-dependent frame contains every committed feature column."""
    optimizer = PriceOptimizer(real_model, real_feature_columns)
    features = optimizer._build_features(BASE_FEATURES, price=77.0)
    missing = [col for col in real_feature_columns if col not in features]
    assert missing == []


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
