#!/usr/bin/env python3
"""Smoke tests for production deployment validation.

Collectable pytest module (ROADMAP R14). Every check is a module-level
``test_*`` function that depends on the ``api_base_url`` fixture. The fixture
probes the API once with a short timeout and calls ``pytest.skip`` when nothing
is listening, so a plain ``pytest tests/`` stays green without a running server
(CONVENTIONS rule 17). Point the tests at a live instance with ``API_URL``.
"""
import os
import time

import pytest
import requests

# Get API URL from environment or use default
API_URL = os.getenv("API_URL", "http://localhost:8000")
PROBE_TIMEOUT = 2  # seconds — short probe, no retries loop
TIMEOUT = 10  # seconds — per-request timeout for the real checks


@pytest.fixture(scope="module")
def api_base_url():
    """Base URL of a reachable API, or skip the module when it is offline.

    Probes ``/v1/health`` once with ``PROBE_TIMEOUT`` (<= 2 s, no retry loop).
    When the API is unreachable every smoke test is *skipped* (not errored), so
    collection never fails and the suite stays green without a server.
    """
    base_url = API_URL.rstrip("/")
    try:
        requests.get(f"{base_url}/v1/health", timeout=PROBE_TIMEOUT)
    except requests.RequestException as exc:
        pytest.skip(
            f"API not reachable at {base_url} ({type(exc).__name__}); "
            f"start the API and/or set API_URL"
        )
    return base_url


def test_health_endpoint(api_base_url):
    """Test /health endpoint"""
    response = requests.get(f"{api_base_url}/v1/health", timeout=TIMEOUT)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()
    assert data['status'] in ['healthy', 'degraded'], f"Invalid status: {data['status']}"
    assert 'checks' in data, "Missing 'checks' in response"


def test_readiness_endpoint(api_base_url):
    """Test /health/ready endpoint"""
    response = requests.get(f"{api_base_url}/v1/health/ready", timeout=TIMEOUT)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()
    assert data['ready'] == True, "Service not ready"


def test_liveness_endpoint(api_base_url):
    """Test /health/live endpoint"""
    response = requests.get(f"{api_base_url}/v1/health/live", timeout=TIMEOUT)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()
    assert data['alive'] == True, "Service not alive"


def test_metrics_endpoint(api_base_url):
    """Test /metrics endpoint"""
    response = requests.get(f"{api_base_url}/v1/metrics", timeout=TIMEOUT)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()
    assert 'health' in data, "Missing 'health' metrics"
    assert 'predictions' in data, "Missing 'predictions' metrics"


def test_optimize_price_basic(api_base_url):
    """Test basic price optimization"""
    payload = {
        "product_id": 1,
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
        "price_min": 2300000.0,
        "price_max": 2700000.0,
        "optimization_method": "grid_search"
    }

    response = requests.post(
        f"{api_base_url}/v1/optimize-price",
        json=payload,
        timeout=TIMEOUT
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()
    assert 'optimal_price' in data, "Missing 'optimal_price'"
    assert 'expected_demand' in data, "Missing 'expected_demand'"
    assert 'expected_revenue' in data, "Missing 'expected_revenue'"

    # Validate price is within bounds
    assert 2300000.0 <= data['optimal_price'] <= 2700000.0, \
        f"Price {data['optimal_price']} outside bounds [2300000, 2700000]"


def test_optimize_with_constraints(api_base_url):
    """Test optimization with business constraints"""
    payload = {
        "product_id": 1,
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
        "price_min": 2300000.0,
        "price_max": 2700000.0,
        "cost": 2000000.0,
        "min_margin_pct": 0.15,
        "inventory_limit": 100,
        "optimization_method": "grid_search"
    }

    response = requests.post(
        f"{api_base_url}/v1/optimize-price",
        json=payload,
        timeout=TIMEOUT
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()
    assert 'profit_margin' in data, "Missing 'profit_margin'"
    assert data['profit_margin'] >= 0.15 - 0.01, \
        f"Margin {data['profit_margin']:.2%} below minimum 15%"


def test_response_time(api_base_url):
    """Test API response time"""
    payload = {
        "product_id": 1,
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
        "price_min": 2300000.0,
        "price_max": 2700000.0
    }

    start = time.time()
    response = requests.post(
        f"{api_base_url}/v1/optimize-price",
        json=payload,
        timeout=TIMEOUT
    )
    elapsed_ms = (time.time() - start) * 1000

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert elapsed_ms < 1000, f"Response time {elapsed_ms:.0f}ms exceeds 1000ms"


def test_invalid_input(api_base_url):
    """Test API handles invalid input gracefully"""
    payload = {
        "product_id": 1,
        "competitor_price": 2500000.0,
        "price_min": 2700000.0,
        "price_max": 2300000.0  # Invalid: max < min
    }

    response = requests.post(
        f"{api_base_url}/v1/optimize-price",
        json=payload,
        timeout=TIMEOUT
    )

    assert response.status_code == 422, \
        f"Expected 422 for invalid input, got {response.status_code}"
