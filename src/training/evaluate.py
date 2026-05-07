import numpy as np
from sklearn.metrics import mean_absolute_error
from sklearn.metrics import mean_squared_error
from sklearn.metrics import r2_score
import pandas as pd
from typing import Dict, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ModelEvaluator:
    """Enhanced model evaluator with multiple metrics and analysis"""

    def evaluate(self, model, X_val, y_val, X_train=None, y_train=None) -> Dict:
        """
        Comprehensive model evaluation with multiple metrics
        
        Args:
            model: Trained model
            X_val: Validation features
            y_val: Validation targets
            X_train: Optional training features for train metrics
            y_train: Optional training targets for train metrics
        """
        y_pred = model.predict(X_val)

        # Core metrics
        mae = mean_absolute_error(y_val, y_pred)
        rmse = np.sqrt(mean_squared_error(y_val, y_pred))
        r2 = r2_score(y_val, y_pred)
        
        # MAPE (Mean Absolute Percentage Error)
        mape = self._calculate_mape(y_val, y_pred)
        
        # Directional accuracy (for demand forecasting)
        directional_accuracy = self._calculate_directional_accuracy(y_val, y_pred)
        
        # Bias (systematic over/under prediction)
        bias = np.mean(y_pred - y_val)

        metrics = {
            "MAE": float(mae),
            "RMSE": float(rmse),
            "R2": float(r2),
            "MAPE": float(mape),
            "Directional_Accuracy": float(directional_accuracy),
            "Bias": float(bias),
            "Mean_Prediction": float(np.mean(y_pred)),
            "Mean_Actual": float(np.mean(y_val)),
        }

        # Add training metrics if provided (to detect overfitting)
        if X_train is not None and y_train is not None:
            y_train_pred = model.predict(X_train)
            train_mae = mean_absolute_error(y_train, y_train_pred)
            train_r2 = r2_score(y_train, y_train_pred)
            
            metrics["Train_MAE"] = float(train_mae)
            metrics["Train_R2"] = float(train_r2)
            metrics["Overfit_Gap_MAE"] = float(train_mae - mae)
            metrics["Overfit_Gap_R2"] = float(train_r2 - r2)

        logger.info(f"Validation Metrics - MAE: {mae:.2f}, RMSE: {rmse:.2f}, R2: {r2:.3f}, MAPE: {mape:.2%}")
        
        return metrics

    def _calculate_mape(self, y_true, y_pred) -> float:
        """Mean Absolute Percentage Error (handles zero values)"""
        y_true = np.array(y_true)
        y_pred = np.array(y_pred)
        
        # Avoid division by zero
        mask = y_true != 0
        if not mask.any():
            return 0.0
            
        return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask]))

    def _calculate_directional_accuracy(self, y_true, y_pred) -> float:
        """
        Percentage of predictions that correctly predict direction
        (useful for demand forecasting)
        """
        y_true = np.array(y_true)
        y_pred = np.array(y_pred)
        
        if len(y_true) < 2:
            return 0.0
        
        # Calculate changes
        true_changes = np.diff(y_true)
        pred_changes = np.diff(y_pred)
        
        # Check if directions match (both positive or both negative)
        correct_direction = np.sign(true_changes) == np.sign(pred_changes)
        
        return np.mean(correct_direction)

    def get_feature_importance(self, model, feature_names: list) -> pd.DataFrame:
        """Extract feature importance from tree-based models"""
        try:
            if hasattr(model, 'feature_importances_'):
                importance_df = pd.DataFrame({
                    'feature': feature_names,
                    'importance': model.feature_importances_
                }).sort_values('importance', ascending=False)
                
                logger.info(f"Top 5 features: {importance_df.head()['feature'].tolist()}")
                return importance_df
        except Exception as e:
            logger.warning(f"Could not extract feature importance: {e}")
            
        return pd.DataFrame()

    def analyze_residuals(self, y_true, y_pred) -> Dict:
        """Analyze prediction residuals for patterns"""
        residuals = np.array(y_pred) - np.array(y_true)
        
        return {
            "residual_mean": float(np.mean(residuals)),
            "residual_std": float(np.std(residuals)),
            "residual_min": float(np.min(residuals)),
            "residual_max": float(np.max(residuals)),
            "residual_q25": float(np.percentile(residuals, 25)),
            "residual_q75": float(np.percentile(residuals, 75)),
        }
