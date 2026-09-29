"""R4 — one canonical serving feature builder shared by both optimizers.

Asserts the two optimizer strategies cannot diverge:

(a) fed the same ``(base_features, price)``, both feed the model an identical
    ordered feature vector (the same committed 31 columns, in the same order,
    with the same values), and
(b) both therefore produce identical ``model.predict`` output.

The tests run against the committed ``models/demand_model.pkl`` +
``models/features.json`` (CONVENTIONS rule 14); the expected price is a request
input, not a model-derived reference (CONVENTIONS rule 34).
"""
import json
from pathlib import Path

import joblib
import pytest

from src.pricing.bayesian_optimizer import BayesianPriceOptimizer
from src.pricing.features import build_serving_features
from src.pricing.optimizer import PriceOptimizer

REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = REPO_ROOT / "models" / "demand_model.pkl"
FEATURES_PATH = REPO_ROOT / "models" / "features.json"

# Standard serving request inputs (same base_features used across the suite).
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

# A single candidate price. Both optimizers are asked to evaluate exactly this
# price (a degenerate [price, price] range), so their feature vectors and model
# predictions are directly comparable.
PRICE = 77.0


@pytest.fixture(scope="module")
def real_model():
    if not MODEL_PATH.exists():
        pytest.skip(f"Committed model not found: {MODEL_PATH}")
    return joblib.load(MODEL_PATH)


@pytest.fixture(scope="module")
def real_feature_columns():
    if not FEATURES_PATH.exists():
        pytest.skip(f"Committed feature list not found: {FEATURES_PATH}")
    with open(FEATURES_PATH) as fh:
        return json.load(fh)


class _RecordingModel:
    """Delegates to the real model and records every frame it is asked to predict."""

    def __init__(self, model):
        self._model = model
        self.frames = []

    def predict(self, X):
        self.frames.append(X.copy())
        return self._model.predict(X)


def _grid_frames(real_model, real_feature_columns):
    model = _RecordingModel(real_model)
    PriceOptimizer(model, real_feature_columns).optimize(
        BASE_FEATURES, PRICE, PRICE, steps=1
    )
    return model


def _bayesian_frames(real_model, real_feature_columns):
    model = _RecordingModel(real_model)
    BayesianPriceOptimizer(model, real_feature_columns).optimize(
        BASE_FEATURES, PRICE, PRICE
    )
    return model


def test_both_optimizers_feed_identical_ordered_feature_vectors(real_model, real_feature_columns):
    """R4(a): identical ordered feature vector for the same (base_features, price)."""
    grid_model = _grid_frames(real_model, real_feature_columns)
    bayesian_model = _bayesian_frames(real_model, real_feature_columns)

    assert len(grid_model.frames) == 1
    assert len(bayesian_model.frames) == 1

    grid_row = grid_model.frames[0].iloc[0]
    bayesian_row = bayesian_model.frames[0].iloc[0]

    assert list(grid_row.index) == list(real_feature_columns)
    assert list(bayesian_row.index) == list(real_feature_columns)
    assert grid_row.tolist() == bayesian_row.tolist()


def test_both_optimizers_produce_identical_model_predictions(real_model, real_feature_columns):
    """R4(b): identical model.predict output for the same (base_features, price)."""
    grid_model = _grid_frames(real_model, real_feature_columns)
    bayesian_model = _bayesian_frames(real_model, real_feature_columns)

    grid_prediction = real_model.predict(grid_model.frames[0])[0]
    bayesian_prediction = real_model.predict(bayesian_model.frames[0])[0]
    assert grid_prediction == bayesian_prediction

    grid = PriceOptimizer(real_model, real_feature_columns).optimize(
        BASE_FEATURES, PRICE, PRICE, steps=1
    )
    bayesian = BayesianPriceOptimizer(real_model, real_feature_columns).optimize(
        BASE_FEATURES, PRICE, PRICE
    )
    assert grid["expected_demand"] == bayesian["expected_demand"]
    assert grid["expected_revenue"] == bayesian["expected_revenue"]


def test_serving_builder_covers_committed_columns_in_order(real_feature_columns):
    """The shared builder returns exactly the committed model columns, in order."""
    features = build_serving_features(BASE_FEATURES, PRICE, real_feature_columns)
    assert list(features.keys()) == list(real_feature_columns)


def test_exactly_one_function_computes_price_dependent_features():
    """R4: neither optimizer builds its own ad-hoc serving dict."""
    for relative_path in ("src/pricing/optimizer.py", "src/pricing/bayesian_optimizer.py"):
        source = (REPO_ROOT / relative_path).read_text()
        # The ad-hoc price-dependent keys must live only in the shared builder.
        assert "price_advantage_sin" not in source
        assert "log_comp_price" not in source
        # ...and both optimizers must consume the shared builder.
        assert "build_serving_features" in source
