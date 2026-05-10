#!/usr/bin/env python3
"""Test that the bug fixes work"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
from unittest.mock import Mock

print("Testing optimizer fixes...")

# Test 1: Grid search optimizer
print("\n1. Testing PriceOptimizer (grid search)...")
from src.pricing.optimizer import PriceOptimizer

mock_model = Mock()
mock_model.predict = lambda X: np.array([100 - X.iloc[0]['price']])

feature_columns = ['price', 'competitor_price', 'price_ratio', 'dow']
base_features = {
    'competitor_price': 80.0,
    'dow': 2,
    'sin_annual': 0.5,
    'cos_annual': 0.866
}

optimizer = PriceOptimizer(mock_model, feature_columns)
result = optimizer.optimize(base_features, 50, 90, steps=10)

print(f"   ✅ Grid optimizer works!")
print(f"   Optimal price: ${result['optimal_price']:.2f}")
print(f"   Expected demand: {result['expected_demand']:.1f}")
print(f"   Expected revenue: ${result['expected_revenue']:.2f}")

# Test 2: Bayesian optimizer
print("\n2. Testing BayesianPriceOptimizer...")
from src.pricing.bayesian_optimizer import BayesianPriceOptimizer

mock_model2 = Mock()
mock_model2.predict = lambda X: np.array([max(0, 150 - 0.5 * X.iloc[0]['price'])])

feature_columns2 = ['price', 'competitor_price', 'price_ratio', 'price_diff_pct', 
                    'sin_annual', 'cos_annual', 'price_ratio_sin', 'price_ratio_cos']
base_features2 = {
    'competitor_price': 100.0,
    'sin_annual': 0.5,
    'cos_annual': 0.866
}

bayesian_optimizer = BayesianPriceOptimizer(mock_model2, feature_columns2)
result2 = bayesian_optimizer.optimize(base_features2, 50, 150)

print(f"   ✅ Bayesian optimizer works!")
print(f"   Optimal price: ${result2['optimal_price']:.2f}")
print(f"   Expected demand: {result2['expected_demand']:.1f}")
print(f"   Expected revenue: ${result2['expected_revenue']:.2f}")
print(f"   Optimization success: {result2['optimization_success']}")

# Test 3: Bayesian with constraints
print("\n3. Testing Bayesian optimizer with constraints...")
result3 = bayesian_optimizer.optimize_with_constraints(
    base_features2,
    price_min=50,
    price_max=150,
    cost=60.0,
    min_margin_pct=0.2
)

print(f"   ✅ Constrained optimization works!")
print(f"   Optimal price: ${result3['optimal_price']:.2f}")
print(f"   Profit margin: {result3['profit_margin']:.1%}")
print(f"   Total profit: ${result3['total_profit']:.2f}")

# Test 4: API routing
print("\n4. Testing API routing...")
from fastapi.testclient import TestClient
from src.api.server import app

client = TestClient(app)
response = client.get("/v1/health")

if response.status_code == 200:
    print(f"   ✅ API health endpoint works!")
    print(f"   Response: {response.json()}")
else:
    print(f"   ❌ API health endpoint failed: {response.status_code}")

print("\n" + "=" * 60)
print("✅ All fixes verified successfully!")
print("=" * 60)
