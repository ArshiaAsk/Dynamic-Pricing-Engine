"""R4 — one canonical serving feature builder consumed by the served optimizer.

After R22 the only optimizer is ``PriceOptimizer`` (``"grid_search"``), so this
file asserts:

(a) the shared builder returns exactly the committed model columns, in order
    (``models/features.json``), and
(b) the served optimizer consumes the shared builder rather than building its
    own ad-hoc price-dependent features.

The tests run against the tracked ``models/features.json`` (CONVENTIONS rule
14); the expected price is a request input, not a model-derived reference
(CONVENTIONS rule 34).
"""
import json
from pathlib import Path

import pytest

from src.pricing.features import build_serving_features

REPO_ROOT = Path(__file__).resolve().parents[1]
FEATURES_PATH = REPO_ROOT / "models" / "features.json"

# Standard serving request inputs (same base_features used across the suite),
# on the training price scale (D32) with the training-median history features.
BASE_FEATURES = {
    "product_id": 42,
    "competitor_price": 2500000.0,
    "dow": 2,
    "is_weekend": 0,
    "week": 15,
    "month": 4,
    "sin_annual": 0.5,
    "cos_annual": 0.866,
    "lag_units_sold_1": 92.0,
    "lag_units_sold_7": 92.0,
    "lag_units_sold_14": 93.0,
    "roll_mean_units_7": 96.4,
    "roll_mean_units_14": 96.9,
    "roll_mean_units_28": 96.9,
    "roll_std_units_7": 37.4,
    "roll_std_units_14": 38.5,
    "roll_std_units_28": 39.2,
}

# A single candidate price (inside the price_ratio support).
PRICE = 2500000.0


@pytest.fixture(scope="module")
def real_feature_columns():
    if not FEATURES_PATH.exists():
        pytest.skip(f"Committed feature list not found: {FEATURES_PATH}")
    with open(FEATURES_PATH) as fh:
        return json.load(fh)


def test_serving_builder_covers_committed_columns_in_order(real_feature_columns):
    """The shared builder returns exactly the committed model columns, in order."""
    features = build_serving_features(BASE_FEATURES, PRICE, real_feature_columns)
    assert list(features.keys()) == list(real_feature_columns)


def test_exactly_one_function_computes_price_dependent_features():
    """R4: the served optimizer does not build its own ad-hoc serving dict."""
    source = (REPO_ROOT / "src" / "pricing" / "optimizer.py").read_text()
    # The ad-hoc price-dependent keys must live only in the shared builder.
    assert "price_advantage_sin" not in source
    assert "log_comp_price" not in source
    # ...and the optimizer must consume the shared builder.
    assert "build_serving_features" in source
