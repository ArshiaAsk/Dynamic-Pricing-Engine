"""Tests for price optimizers"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock
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
