"""Tests for API endpoints.

The shared ``client`` fixture lives in ``tests/conftest.py``; the application is
imported lazily there so this module no longer aborts collection when a heavy
optional dependency is unavailable (ROADMAP R3/R8).
"""

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


def _payload(**overrides):
    payload = dict(BASE_PAYLOAD)
    payload.update(overrides)
    return payload


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
