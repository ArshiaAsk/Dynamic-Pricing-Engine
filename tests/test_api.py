"""Tests for API endpoints"""
import pytest
from fastapi.testclient import TestClient
from src.api.server import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"


def test_optimize_price_endpoint(client):
    """Test price optimization endpoint"""
    payload = {
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
        "optimization_method": "bayesian"
    }
    
    response = client.post("/optimize-price", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "optimal_price" in data
    assert "expected_demand" in data
    assert "expected_revenue" in data
    assert 70.0 <= data["optimal_price"] <= 110.0


def test_optimize_with_constraints(client):
    """Test optimization with business constraints"""
    payload = {
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
        "cost": 60.0,
        "min_margin_pct": 0.15,
        "inventory_limit": 100,
        "optimization_method": "bayesian"
    }
    
    response = client.post("/optimize-price", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "profit_margin" in data
    assert "total_profit" in data
    assert data["profit_margin"] >= 0.15 - 0.01  # Allow small numerical error


def test_invalid_price_range(client):
    """Test validation for invalid price range"""
    payload = {
        "product_id": 42,
        "competitor_price": 89.99,
        "dow": 2,
        "is_weekend": 0,
        "week": 15,
        "month": 4,
        "sin_annual": 0.5,
        "cos_annual": 0.866,
        "price_min": 110.0,
        "price_max": 70.0  # Invalid: max < min
    }
    
    response = client.post("/optimize-price", json=payload)
    
    assert response.status_code == 422  # Validation error
