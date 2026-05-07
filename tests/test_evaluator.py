"""Tests for model evaluator"""
import pytest
import numpy as np
import pandas as pd
from src.training.evaluate import ModelEvaluator


class TestModelEvaluator:
    """Test model evaluation metrics"""
    
    @pytest.fixture
    def evaluator(self):
        return ModelEvaluator()
    
    @pytest.fixture
    def mock_model(self):
        """Mock model that returns predictions"""
        class MockModel:
            def predict(self, X):
                # Return simple predictions for testing
                return np.array([50, 55, 45, 60, 52])
        return MockModel()
    
    def test_basic_metrics(self, evaluator, mock_model):
        """Test basic evaluation metrics"""
        X_val = pd.DataFrame({'feature1': [1, 2, 3, 4, 5]})
        y_val = np.array([48, 52, 47, 58, 50])
        
        metrics = evaluator.evaluate(mock_model, X_val, y_val)
        
        assert 'MAE' in metrics
        assert 'RMSE' in metrics
        assert 'R2' in metrics
        assert 'MAPE' in metrics
        assert 'Bias' in metrics
        assert metrics['MAE'] >= 0
        assert metrics['RMSE'] >= 0
    
    def test_mape_calculation(self, evaluator):
        """Test MAPE calculation"""
        y_true = np.array([100, 200, 150])
        y_pred = np.array([110, 190, 160])
        
        mape = evaluator._calculate_mape(y_true, y_pred)
        
        expected_mape = np.mean([0.1, 0.05, 0.0667])
        assert abs(mape - expected_mape) < 0.01
    
    def test_mape_with_zeros(self, evaluator):
        """Test MAPE handles zero values"""
        y_true = np.array([0, 100, 200])
        y_pred = np.array([10, 110, 190])
        
        mape = evaluator._calculate_mape(y_true, y_pred)
        
        # Should only calculate for non-zero values
        assert mape >= 0
        assert not np.isnan(mape)
    
    def test_directional_accuracy(self, evaluator):
        """Test directional accuracy calculation"""
        y_true = np.array([10, 15, 12, 18, 20])
        y_pred = np.array([11, 16, 13, 17, 21])
        
        accuracy = evaluator._calculate_directional_accuracy(y_true, y_pred)
        
        # All predictions should have correct direction
        assert accuracy == 1.0
    
    def test_feature_importance(self, evaluator):
        """Test feature importance extraction"""
        class MockModelWithImportance:
            feature_importances_ = np.array([0.5, 0.3, 0.2])
        
        model = MockModelWithImportance()
        features = ['price', 'competitor_price', 'dow']
        
        importance_df = evaluator.get_feature_importance(model, features)
        
        assert not importance_df.empty
        assert len(importance_df) == 3
        assert 'feature' in importance_df.columns
        assert 'importance' in importance_df.columns
        # Should be sorted by importance
        assert importance_df.iloc[0]['importance'] >= importance_df.iloc[1]['importance']
    
    def test_residual_analysis(self, evaluator):
        """Test residual analysis"""
        y_true = np.array([50, 55, 45, 60, 52])
        y_pred = np.array([48, 52, 47, 58, 50])
        
        residuals = evaluator.analyze_residuals(y_true, y_pred)
        
        assert 'residual_mean' in residuals
        assert 'residual_std' in residuals
        assert 'residual_min' in residuals
        assert 'residual_max' in residuals
        assert 'residual_q25' in residuals
        assert 'residual_q75' in residuals
