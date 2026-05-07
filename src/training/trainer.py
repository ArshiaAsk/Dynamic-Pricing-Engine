from xgboost import XGBRegressor
from sklearn.model_selection import TimeSeriesSplit
import numpy as np
from typing import Dict, Optional, Tuple
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DemandModelTrainer:
    """Enhanced trainer with cross-validation and early stopping"""

    def __init__(self, config):
        self.config = config

    def build_model(self):
        """Build XGBoost model with enhanced configuration"""
        model = XGBRegressor(
            n_estimators=self.config.get("n_estimators", 600),
            max_depth=self.config.get("max_depth", 6),
            learning_rate=self.config.get("learning_rate", 0.05),
            subsample=self.config.get("subsample", 0.8),
            colsample_bytree=self.config.get("colsample_bytree", 0.8),
            objective="reg:squarederror",
            tree_method="hist",
            random_state=42,
            # Enhanced parameters
            min_child_weight=self.config.get("min_child_weight", 1),
            gamma=self.config.get("gamma", 0),
            reg_alpha=self.config.get("reg_alpha", 0),
            reg_lambda=self.config.get("reg_lambda", 1),
        )
        return model

    def train(self, model, X_train, y_train, X_val, y_val):
        """Train with early stopping"""
        logger.info(f"Training model with {len(X_train)} samples")
        
        model.fit(
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            early_stopping_rounds=50,
            verbose=False
        )
        
        logger.info(f"Training completed. Best iteration: {model.best_iteration}")
        return model

    def cross_validate(self, model, X, y, n_splits=5) -> Dict:
        """
        Perform time-series cross-validation
        
        Args:
            model: Model to validate
            X: Features
            y: Target
            n_splits: Number of CV splits
            
        Returns:
            Dictionary with CV scores
        """
        from sklearn.metrics import mean_absolute_error, r2_score
        
        tscv = TimeSeriesSplit(n_splits=n_splits)
        
        mae_scores = []
        r2_scores = []
        
        logger.info(f"Starting {n_splits}-fold time-series cross-validation")
        
        for fold, (train_idx, val_idx) in enumerate(tscv.split(X), 1):
            X_train_cv, X_val_cv = X.iloc[train_idx], X.iloc[val_idx]
            y_train_cv, y_val_cv = y.iloc[train_idx], y.iloc[val_idx]
            
            # Clone and train model
            from sklearn.base import clone
            model_cv = clone(model)
            model_cv.fit(X_train_cv, y_train_cv, verbose=False)
            
            # Evaluate
            y_pred = model_cv.predict(X_val_cv)
            mae = mean_absolute_error(y_val_cv, y_pred)
            r2 = r2_score(y_val_cv, y_pred)
            
            mae_scores.append(mae)
            r2_scores.append(r2)
            
            logger.info(f"Fold {fold}: MAE={mae:.2f}, R2={r2:.3f}")
        
        cv_results = {
            "cv_mae_mean": float(np.mean(mae_scores)),
            "cv_mae_std": float(np.std(mae_scores)),
            "cv_r2_mean": float(np.mean(r2_scores)),
            "cv_r2_std": float(np.std(r2_scores)),
            "cv_mae_scores": [float(s) for s in mae_scores],
            "cv_r2_scores": [float(s) for s in r2_scores],
        }
        
        logger.info(f"CV Results: MAE={cv_results['cv_mae_mean']:.2f}±{cv_results['cv_mae_std']:.2f}, "
                   f"R2={cv_results['cv_r2_mean']:.3f}±{cv_results['cv_r2_std']:.3f}")
        
        return cv_results
