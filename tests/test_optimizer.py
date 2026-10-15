"""Tests for price optimizers"""
import json
from pathlib import Path

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock
import joblib

from src.pricing.optimizer import PriceOptimizer
from src.pricing.bayesian_optimizer import BayesianPriceOptimizer


class TestPriceOptimizer:
    """Test grid search optimizer"""
    
    @pytest.fixture
    def mock_model(self):
        """Create a mock demand model"""
        model = Mock()
        # Simple linear demand: demand = 100 - price
        model.predict = lambda X: np.array([100 - X.iloc[0]['price']])
        return model
    
    @pytest.fixture
    def feature_columns(self):
        return ['price', 'competitor_price', 'price_ratio', 'dow']
    
    @pytest.fixture
    def base_features(self):
        return {
            'competitor_price': 80.0,
            'dow': 2,
            'sin_annual': 0.5,
            'cos_annual': 0.866
        }
    
    def test_optimizer_basic(self, mock_model, feature_columns, base_features):
        """Test basic optimization"""
        optimizer = PriceOptimizer(mock_model, feature_columns)
        
        result = optimizer.optimize(base_features, 50, 90, steps=10)
        
        assert 'optimal_price' in result
        assert 'expected_demand' in result
        assert 'expected_revenue' in result
        assert 50 <= result['optimal_price'] <= 90
        assert result['expected_revenue'] > 0
    
    def test_optimizer_price_bounds(self, mock_model, feature_columns, base_features):
        """Test that optimizer respects price bounds"""
        optimizer = PriceOptimizer(mock_model, feature_columns)
        
        result = optimizer.optimize(base_features, 60, 70, steps=5)
        
        assert 60 <= result['optimal_price'] <= 70


class TestBayesianOptimizer:
    """Test Bayesian optimizer"""
    
    @pytest.fixture
    def mock_model(self):
        model = Mock()
        # Quadratic demand curve: demand = 150 - 0.5 * price
        model.predict = lambda X: np.array([max(0, 150 - 0.5 * X.iloc[0]['price'])])
        return model
    
    @pytest.fixture
    def feature_columns(self):
        return ['price', 'competitor_price', 'price_ratio', 'price_diff_pct', 
                'sin_annual', 'cos_annual', 'price_ratio_sin', 'price_ratio_cos']
    
    @pytest.fixture
    def base_features(self):
        return {
            'competitor_price': 100.0,
            'sin_annual': 0.5,
            'cos_annual': 0.866
        }
    
    def test_bayesian_basic(self, mock_model, feature_columns, base_features):
        """Test Bayesian optimization"""
        optimizer = BayesianPriceOptimizer(mock_model, feature_columns)
        
        result = optimizer.optimize(base_features, 50, 150)
        
        assert 'optimal_price' in result
        assert 'expected_demand' in result
        assert 'expected_revenue' in result
        assert 'optimization_success' in result
        assert 50 <= result['optimal_price'] <= 150
    
    def test_bayesian_with_constraints(self, mock_model, feature_columns, base_features):
        """Test optimization with business constraints"""
        optimizer = BayesianPriceOptimizer(mock_model, feature_columns)
        
        cost = 60.0
        min_margin = 0.2  # 20% minimum margin
        
        result = optimizer.optimize_with_constraints(
            base_features,
            price_min=50,
            price_max=150,
            cost=cost,
            min_margin_pct=min_margin
        )
        
        assert 'profit_margin' in result
        assert 'total_profit' in result
        # Check margin constraint (with small tolerance for numerical errors)
        assert result['profit_margin'] >= min_margin - 0.01
        assert result['optimal_price'] >= cost * (1 + min_margin) - 0.01
    
    def test_inventory_constraint(self, mock_model, feature_columns, base_features):
        """Test inventory limit constraint"""
        optimizer = BayesianPriceOptimizer(mock_model, feature_columns)
        
        result = optimizer.optimize(
            base_features,
            price_min=50,
            price_max=150,
            inventory_limit=50
        )
        
        # Demand should not exceed inventory
        assert result['expected_demand'] <= 50


# --------------------------------------------------------------------------- #
# R22 prerequisite — the inventory cap is enforced on the LIVE optimizer path
# --------------------------------------------------------------------------- #
# The served engine passes ``inventory_limit`` straight to
# ``PriceOptimizer.optimize`` (``src/pricing/engine.py:185,193``); the cap
# itself lives at ``src/pricing/optimizer.py:48-49``. This asserts the property
# against the real working-tree model (CONVENTIONS rule 14), so it is not a
# mock-only check. The limit is chosen at run time *below* the unconstrained
# optimum's demand, so the cap is provably binding.

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MODEL_PATH = _REPO_ROOT / "models" / "demand_model.pkl"
_FEATURES_PATH = _REPO_ROOT / "models" / "features.json"

_LIVE_BASE_FEATURES = {
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


@pytest.fixture(scope="module")
def real_model():
    """The committed demand model (skip only if the artifact is absent)."""
    if not _MODEL_PATH.exists():
        pytest.skip(f"Committed model not found: {_MODEL_PATH}")
    return joblib.load(_MODEL_PATH)


@pytest.fixture(scope="module")
def real_feature_columns():
    """The committed feature-column list the model was trained on."""
    if not _FEATURES_PATH.exists():
        pytest.skip(f"Committed feature list not found: {_FEATURES_PATH}")
    with open(_FEATURES_PATH) as fh:
        return json.load(fh)


def test_inventory_cap_binds_on_live_optimizer_path(real_model, real_feature_columns):
    """R22: ``PriceOptimizer.optimize`` caps ``expected_demand`` at the limit.

    The unconstrained optimum is computed first; the limit is set to half its
    demand so the cap is provably binding, then the capped run must not exceed
    the limit. A feasible price always exists (the cap only clips demand).
    """
    optimizer = PriceOptimizer(real_model, real_feature_columns)

    unconstrained = optimizer.optimize(_LIVE_BASE_FEATURES, 70.0, 110.0)
    limit = max(1, int(unconstrained["expected_demand"] * 0.5))
    assert unconstrained["expected_demand"] > limit, (
        "test precondition: the cap must be binding "
        f"(unconstrained demand {unconstrained['expected_demand']} <= limit {limit})"
    )

    capped = optimizer.optimize(_LIVE_BASE_FEATURES, 70.0, 110.0, inventory_limit=limit)

    assert capped["expected_demand"] <= limit
    assert capped["expected_demand"] <= unconstrained["expected_demand"]
