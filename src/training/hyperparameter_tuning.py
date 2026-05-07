"""Hyperparameter tuning with Optuna"""
import optuna
from optuna.samplers import TPESampler
from xgboost import XGBRegressor
from sklearn.model_selection import cross_val_score
import numpy as np
from typing import Dict
from src.utils.logger import get_logger

logger = get_logger(__name__)


class HyperparameterTuner:
    """Hyperparameter optimization using Optuna"""
    
    def __init__(self, X_train, y_train, n_trials=50, cv_folds=3):
        self.X_train = X_train
        self.y_train = y_train
        self.n_trials = n_trials
        self.cv_folds = cv_folds
        self.best_params = None
        
    def objective(self, trial):
        """Optuna objective function"""
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 100, 1000, step=100),
            'max_depth': trial.suggest_int('max_depth', 3, 10),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
            'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
            'gamma': trial.suggest_float('gamma', 0, 5),
            'reg_alpha': trial.suggest_float('reg_alpha', 0, 10),
            'reg_lambda': trial.suggest_float('reg_lambda', 0, 10),
            'objective': 'reg:squarederror',
            'tree_method': 'hist',
            'random_state': 42,
        }
        
        model = XGBRegressor(**params)
        
        # Use negative MAE as score (higher is better for optuna)
        scores = cross_val_score(
            model, 
            self.X_train, 
            self.y_train, 
            cv=self.cv_folds,
            scoring='neg_mean_absolute_error',
            n_jobs=-1
        )
        
        return scores.mean()
    
    def tune(self) -> Dict:
        """Run hyperparameter optimization"""
        logger.info(f"Starting hyperparameter tuning with {self.n_trials} trials")
        
        study = optuna.create_study(
            direction='maximize',
            sampler=TPESampler(seed=42)
        )
        
        study.optimize(
            self.objective, 
            n_trials=self.n_trials,
            show_progress_bar=True
        )
        
        self.best_params = study.best_params
        
        logger.info(f"Best MAE: {-study.best_value:.2f}")
        logger.info(f"Best parameters: {self.best_params}")
        
        return {
            'best_params': self.best_params,
            'best_score': float(-study.best_value),
            'n_trials': self.n_trials
        }
    
    def get_best_model(self):
        """Build model with best parameters"""
        if self.best_params is None:
            raise ValueError("Must run tune() first")
        
        params = {
            **self.best_params,
            'objective': 'reg:squarederror',
            'tree_method': 'hist',
            'random_state': 42
        }
        
        return XGBRegressor(**params)
