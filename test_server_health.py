#!/usr/bin/env python3
"""
Health check script for the Dynamic Pricing API server.
Run this script to verify the server is working correctly.
"""

import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_root():
    """Test the root endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"✓ Root endpoint: {response.status_code}")
        return True
    except Exception as e:
        print(f"✗ Root endpoint failed: {e}")
        return False

def test_docs():
    """Test the documentation endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        print(f"✓ Docs endpoint: {response.status_code}")
        return True
    except Exception as e:
        print(f"✗ Docs endpoint failed: {e}")
        return False

def test_optimize_price():
    """Test the optimize-price endpoint"""
    payload = {
        "product_id": 1,
        "price": 50.0,
        "competitor_price": 55.0,
        "price_ratio": 0.909,
        "price_diff_pct": -0.091,
        "dow": 2,
        "is_weekend": 0,
        "week": 24,
        "month": 6,
        "sin_annual": 0.5,
        "cos_annual": 0.866,
        "price_ratio_sin": 0.45,
        "price_ratio_cos": 0.79,
        "lag_units_sold_1": 40.0,
        "lag_units_sold_7": 38.0,
        "lag_units_sold_14": 35.0,
        "roll_mean_units_7": 39.0,
        "roll_std_units_7": 2.5,
        "roll_mean_units_14": 40.0,
        "roll_std_units_14": 3.0,
        "roll_mean_units_28": 42.0,
        "roll_std_units_28": 3.5
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/v1/optimize-price",
            json=payload,
            timeout=5
        )
        print(f"✓ API endpoint: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"  Optimal price: ${result['optimal_price']:.2f}")
            print(f"  Expected demand: {result['expected_demand']:.2f} units")
            print(f"  Expected revenue: ${result['expected_revenue']:.2f}")
            return True
        else:
            print(f"  Error: {response.text}")
            return False
    except Exception as e:
        print(f"✗ API endpoint failed: {e}")
        return False

def main():
    print("=" * 50)
    print("Dynamic Pricing API Health Check")
    print("=" * 50)
    print()
    
    results = []
    
    print("Testing endpoints...")
    print()
    
    results.append(test_root())
    results.append(test_docs())
    results.append(test_optimize_price())
    
    print()
    print("=" * 50)
    
    if all(results):
        print("✓ All tests passed! Server is healthy.")
        sys.exit(0)
    else:
        print("✗ Some tests failed. Check the server logs.")
        sys.exit(1)

if __name__ == "__main__":
    main()
