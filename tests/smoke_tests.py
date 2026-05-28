#!/usr/bin/env python3
"""Smoke tests for production deployment validation"""
import os
import sys
import requests
import time
from typing import Dict, Optional

# Get API URL from environment or use default
API_URL = os.getenv('API_URL', 'http://localhost:8000')
TIMEOUT = 10  # seconds


class SmokeTestRunner:
    """Run smoke tests against deployed API"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.passed = 0
        self.failed = 0
        self.results = []
    
    def test(self, name: str, func):
        """Run a single test"""
        print(f"\n🧪 Testing: {name}")
        try:
            func()
            print(f"   ✅ PASSED")
            self.passed += 1
            self.results.append({'test': name, 'status': 'PASSED'})
        except AssertionError as e:
            print(f"   ❌ FAILED: {e}")
            self.failed += 1
            self.results.append({'test': name, 'status': 'FAILED', 'error': str(e)})
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            self.failed += 1
            self.results.append({'test': name, 'status': 'ERROR', 'error': str(e)})
    
    def test_health_endpoint(self):
        """Test /health endpoint"""
        response = requests.get(f"{self.base_url}/v1/health", timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data['status'] in ['healthy', 'degraded'], f"Invalid status: {data['status']}"
        assert 'checks' in data, "Missing 'checks' in response"
        print(f"   Status: {data['status']}")
    
    def test_readiness_endpoint(self):
        """Test /health/ready endpoint"""
        response = requests.get(f"{self.base_url}/v1/health/ready", timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data['ready'] == True, "Service not ready"
        print(f"   Ready: {data['ready']}")
    
    def test_liveness_endpoint(self):
        """Test /health/live endpoint"""
        response = requests.get(f"{self.base_url}/v1/health/live", timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data['alive'] == True, "Service not alive"
        print(f"   Alive: {data['alive']}")
    
    def test_metrics_endpoint(self):
        """Test /metrics endpoint"""
        response = requests.get(f"{self.base_url}/v1/metrics", timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert 'health' in data, "Missing 'health' metrics"
        assert 'predictions' in data, "Missing 'predictions' metrics"
        print(f"   Uptime: {data['health'].get('uptime_seconds', 0):.1f}s")
    
    def test_optimize_price_basic(self):
        """Test basic price optimization"""
        payload = {
            "product_id": 1,
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
        
        response = requests.post(
            f"{self.base_url}/v1/optimize-price",
            json=payload,
            timeout=TIMEOUT
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert 'optimal_price' in data, "Missing 'optimal_price'"
        assert 'expected_demand' in data, "Missing 'expected_demand'"
        assert 'expected_revenue' in data, "Missing 'expected_revenue'"
        
        # Validate price is within bounds
        assert 70.0 <= data['optimal_price'] <= 110.0, \
            f"Price {data['optimal_price']} outside bounds [70, 110]"
        
        print(f"   Optimal price: ${data['optimal_price']:.2f}")
        print(f"   Expected demand: {data['expected_demand']:.1f}")
    
    def test_optimize_with_constraints(self):
        """Test optimization with business constraints"""
        payload = {
            "product_id": 1,
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
        
        response = requests.post(
            f"{self.base_url}/v1/optimize-price",
            json=payload,
            timeout=TIMEOUT
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert 'profit_margin' in data, "Missing 'profit_margin'"
        assert data['profit_margin'] >= 0.15 - 0.01, \
            f"Margin {data['profit_margin']:.2%} below minimum 15%"
        
        print(f"   Profit margin: {data['profit_margin']:.1%}")
        print(f"   Total profit: ${data.get('total_profit', 0):.2f}")
    
    def test_response_time(self):
        """Test API response time"""
        payload = {
            "product_id": 1,
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
            "price_max": 110.0
        }
        
        start = time.time()
        response = requests.post(
            f"{self.base_url}/v1/optimize-price",
            json=payload,
            timeout=TIMEOUT
        )
        elapsed_ms = (time.time() - start) * 1000
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert elapsed_ms < 1000, f"Response time {elapsed_ms:.0f}ms exceeds 1000ms"
        
        print(f"   Response time: {elapsed_ms:.0f}ms")
    
    def test_invalid_input(self):
        """Test API handles invalid input gracefully"""
        payload = {
            "product_id": 1,
            "competitor_price": 89.99,
            "price_min": 110.0,
            "price_max": 70.0  # Invalid: max < min
        }
        
        response = requests.post(
            f"{self.base_url}/v1/optimize-price",
            json=payload,
            timeout=TIMEOUT
        )
        
        assert response.status_code == 422, \
            f"Expected 422 for invalid input, got {response.status_code}"
        
        print(f"   Correctly rejected invalid input")
    
    def run_all(self):
        """Run all smoke tests"""
        print("=" * 60)
        print(f"🚀 Running Smoke Tests")
        print(f"API URL: {self.base_url}")
        print("=" * 60)
        
        # Health checks
        self.test("Health Endpoint", self.test_health_endpoint)
        self.test("Readiness Endpoint", self.test_readiness_endpoint)
        self.test("Liveness Endpoint", self.test_liveness_endpoint)
        self.test("Metrics Endpoint", self.test_metrics_endpoint)
        
        # Functional tests
        self.test("Basic Price Optimization", self.test_optimize_price_basic)
        self.test("Optimization with Constraints", self.test_optimize_with_constraints)
        self.test("Response Time", self.test_response_time)
        self.test("Invalid Input Handling", self.test_invalid_input)
        
        # Summary
        print("\n" + "=" * 60)
        print(f"📊 Test Results")
        print("=" * 60)
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"Total: {self.passed + self.failed}")
        print("=" * 60)
        
        return self.failed == 0


if __name__ == "__main__":
    runner = SmokeTestRunner(API_URL)
    success = runner.run_all()
    
    sys.exit(0 if success else 1)
