"""Tests for API endpoints.

The shared ``client`` fixture lives in ``tests/conftest.py``; the application is
imported lazily there so this module no longer aborts collection when a heavy
optional dependency is unavailable (ROADMAP R3/R8).

The R9 tests additionally verify the served grid path end to end: the response
contract (fields, bounds, method echo) and that the revenue returned through
HTTP is within 1% of a reference optimum computed **at test time** from the
served model and the requested bounds (CONVENTIONS rule 34).
"""
import numpy as np
import pandas as pd
import pytest

from src.api.schemas import PricingResponse

# Standard request payload (same inputs used across the suite). The method is
# filled in per test; the canonical method is "grid_search" (ROADMAP R6).
BASE_PAYLOAD = {
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
    "price_min": 70.0,
    "price_max": 110.0,
}

# Request-only keys the optimizer never sees; the rest are model features.
_OPTIMIZER_KEYS = {"price_min", "price_max", "optimization_method", "cost",
                   "min_margin_pct", "inventory_limit"}

# Minimum reference resolution required by the R9 criterion.
REFERENCE_POINTS = 901
# Revenue tolerance: the served result must be within 1% of the optimum.
REVENUE_RATIO = 0.99


def _payload(**overrides):
    payload = dict(BASE_PAYLOAD)
    payload.update(overrides)
    return payload


def _oracle_serving_features(base_features, price):
    """Independent oracle for the 31-column serving feature contract.

    Deliberately does not call ``src.pricing.features.build_serving_features``
    (the builder the optimizer itself uses), so the R9 reference optimum cannot
    be circular: it mirrors the same arithmetic the way R7's oracle does.
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


def _reference_max_revenue(model, feature_columns, base_features, price_min, price_max):
    """Max revenue over a dense price grid, computed at test time (rule 34)."""
    prices = np.linspace(price_min, price_max, REFERENCE_POINTS)
    frame = pd.DataFrame(
        [_oracle_serving_features(base_features, float(p)) for p in prices]
    )[feature_columns]
    demand = np.asarray(model.predict(frame), dtype=float).reshape(-1)
    return float(np.max(prices * demand))


@pytest.fixture(scope="module")
def served_model():
    """The model the API actually serves (loaded by the engine at import)."""
    from src.api.router import engine

    if engine.model is None:
        pytest.skip("served model unavailable")
    return engine.model


@pytest.fixture(scope="module")
def served_feature_columns():
    """The feature columns the served model expects, in order."""
    from src.api.router import engine

    if not engine.feature_columns:
        pytest.skip("served feature columns unavailable")
    return list(engine.feature_columns)


def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"


def test_optimize_price_endpoint(client):
    """Test price optimization endpoint"""
    response = client.post(
        "/v1/optimize-price",
        json=_payload(optimization_method="grid_search"),
    )

    assert response.status_code == 200
    data = response.json()

    assert "optimal_price" in data
    assert "expected_demand" in data
    assert "expected_revenue" in data
    assert 70.0 <= data["optimal_price"] <= 110.0


def test_optimize_with_constraints(client):
    """Test optimization with business constraints"""
    response = client.post(
        "/v1/optimize-price",
        json=_payload(
            cost=60.0,
            min_margin_pct=0.15,
            inventory_limit=100,
            optimization_method="grid_search",
        ),
    )

    assert response.status_code == 200
    data = response.json()

    assert "profit_margin" in data
    assert "total_profit" in data
    assert data["profit_margin"] >= 0.15 - 0.01  # Allow small numerical error


def test_grid_search_and_alias_accepted(client):
    """R6: the canonical method and its alias both return HTTP 200."""
    for method in ("grid_search", "grid"):
        response = client.post(
            "/v1/optimize-price", json=_payload(optimization_method=method)
        )
        assert response.status_code == 200, method
        data = response.json()
        assert data["optimization_method"] == method
        assert 70.0 <= data["optimal_price"] <= 110.0


def test_legacy_bayesian_method_rejected(client):
    """R6/D2: the legacy "bayesian" method is rejected with HTTP 422, not 500."""
    response = client.post(
        "/v1/optimize-price", json=_payload(optimization_method="bayesian")
    )
    assert response.status_code == 422


def test_unknown_method_rejected(client):
    """R6/D2: any unrecognized method returns HTTP 422, not 500."""
    response = client.post(
        "/v1/optimize-price", json=_payload(optimization_method="not-a-method")
    )
    assert response.status_code == 422


def test_invalid_price_range(client):
    """Test validation for invalid price range"""
    response = client.post(
        "/v1/optimize-price", json=_payload(price_min=110.0, price_max=70.0)
    )

    assert response.status_code == 422  # Validation error


# --------------------------------------------------------------------------- #
# R9 — API contract + grid-path integration
# --------------------------------------------------------------------------- #

def test_grid_path_response_contract(client):
    """R9: grid_search/grid -> 200 with the documented fields and in-bounds price.

    The response must carry ``optimal_price``, ``expected_demand``,
    ``expected_revenue`` and ``optimization_method``, echo the requested method,
    and keep the price within ``[price_min, price_max]``. The legacy
    ``"bayesian"`` method is rejected with HTTP 422 (R6/D2), not 500.
    """
    for method in ("grid_search", "grid"):
        response = client.post(
            "/v1/optimize-price", json=_payload(optimization_method=method)
        )
        assert response.status_code == 200, method
        data = response.json()
        for field in ("optimal_price", "expected_demand", "expected_revenue",
                      "optimization_method"):
            assert field in data, f"{method}: missing {field!r}"
        assert data["optimization_method"] == method
        assert BASE_PAYLOAD["price_min"] <= data["optimal_price"] <= BASE_PAYLOAD["price_max"]
        PricingResponse(**data)  # response validates against the declared schema

    rejected = client.post(
        "/v1/optimize-price", json=_payload(optimization_method="bayesian")
    )
    assert rejected.status_code == 422


def test_grid_path_reaches_reference_optimum(client, served_model, served_feature_columns):
    """R9: grid_search revenue >= 0.99x the test-time reference optimum.

    The reference is computed here from the served model and the requested
    bounds over a >= 901-point grid (CONVENTIONS rule 34); no model-derived
    number is hardcoded, so the test stays valid across a retrain (e.g. R12).
    """
    price_min = BASE_PAYLOAD["price_min"]
    price_max = BASE_PAYLOAD["price_max"]
    base_features = {k: v for k, v in BASE_PAYLOAD.items() if k not in _OPTIMIZER_KEYS}
    reference_max = _reference_max_revenue(
        served_model, served_feature_columns, base_features, price_min, price_max
    )

    response = client.post(
        "/v1/optimize-price", json=_payload(optimization_method="grid_search")
    )
    assert response.status_code == 200
    data = response.json()

    assert data["expected_revenue"] >= REVENUE_RATIO * reference_max
