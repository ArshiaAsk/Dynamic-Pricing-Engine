"""Integration tests for end-to-end workflows"""
import pytest
import joblib
import json
from pathlib import Path
from src.features.transformer import FeatureTransformer
from src.pricing.integrated_optimizer import IntegratedPricingOptimizer


class TestIntegration:
    """Test integrated workflows"""
    
    @pytest.fixture
    def model(self):
        """Load trained model"""
        model_path = Path("models/demand_model.pkl")
        if not model_path.exists():
            pytest.skip("Model not found")
        return joblib.load(model_path)
    
    @pytest.fixture
    def feature_columns(self):
        """Load feature columns"""
        features_path = Path("models/features.json")
        if not features_path.exists():
            pytest.skip("Features not found")
        with open(features_path) as f:
            return json.load(f)
    
    @pytest.fixture
    def sample_input(self):
        """Sample input data"""
        return {
            'product_id': 1,
            'competitor_price': 89.99,
            'date': '2024-05-15',
            'lag_units_sold_1': 45.0,
            'lag_units_sold_7': 42.0,
            'lag_units_sold_14': 40.0,
            'roll_mean_units_7': 43.5,
            'roll_mean_units_14': 41.2,
            'roll_mean_units_28': 39.8,
            'roll_std_units_7': 5.2,
            'roll_std_units_14': 6.1,
            'roll_std_units_28': 7.3,
        }
    
    def test_feature_transformer(self, feature_columns, sample_input):
        """Test feature transformer"""
        transformer = FeatureTransformer(feature_columns)
        
        # Validate input
        is_valid, error = transformer.validate_input(sample_input)
        assert is_valid, f"Input validation failed: {error}"
        
        # Transform features
        X = transformer.transform(sample_input, price=85.0)
        
        assert len(X) == 1, "Should return single row"
        assert len(X.columns) == len(feature_columns), "Column count mismatch"
        assert not X.isnull().any().any(), "Should not have null values"
    
    def test_integrated_optimizer(self, model, feature_columns, sample_input):
        """Test integrated optimizer"""
        optimizer = IntegratedPricingOptimizer(model, feature_columns)
        
        # Optimize price
        result = optimizer.optimize(
            sample_input,
            price_min=70.0,
            price_max=110.0
        )
        
        assert 'optimal_price' in result
        assert 'expected_demand' in result
        assert 'expected_revenue' in result
        assert 70.0 <= result['optimal_price'] <= 110.0
        assert result['expected_demand'] >= 0
        assert result['expected_revenue'] >= 0
    
    def test_optimizer_with_constraints(self, model, feature_columns, sample_input):
        """Test optimizer with business constraints"""
        optimizer = IntegratedPricingOptimizer(model, feature_columns)
        
        result = optimizer.optimize(
            sample_input,
            price_min=70.0,
            price_max=110.0,
            cost=60.0,
            min_margin_pct=0.15,
            inventory_limit=100
        )
        
        assert 'profit_margin' in result
        assert 'total_profit' in result
        assert result['profit_margin'] >= 0.15 - 0.01  # Allow small numerical error
        assert result['expected_demand'] <= 100  # Inventory constraint
    
    def test_predict_demand(self, model, feature_columns, sample_input):
        """Test demand prediction"""
        optimizer = IntegratedPricingOptimizer(model, feature_columns)
        
        demand = optimizer.predict_demand(sample_input, price=85.0)
        
        assert isinstance(demand, float)
        assert demand >= 0
    
    def test_evaluate_price_range(self, model, feature_columns, sample_input):
        """Test price range evaluation"""
        optimizer = IntegratedPricingOptimizer(model, feature_columns)
        
        df = optimizer.evaluate_price_range(
            sample_input,
            price_min=70.0,
            price_max=110.0,
            steps=10
        )
        
        assert len(df) == 10
        assert 'price' in df.columns
        assert 'demand' in df.columns
        assert 'revenue' in df.columns
        assert df['price'].min() >= 70.0
        assert df['price'].max() <= 110.0
