#!/usr/bin/env python3
"""Training script with hyperparameter tuning"""
import yaml
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.training.dataset import DatasetBuilder
from src.training.hyperparameter_tuning import HyperparameterTuner
from src.training.evaluate import ModelEvaluator
from src.utils.logger import get_logger
import joblib
import json

logger = get_logger(__name__)

CONFIG_PATH = Path("configs/config.yaml")


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def main():
    logger.info("=" * 60)
    logger.info("Training with Hyperparameter Tuning")
    logger.info("=" * 60)
    
    config = load_config()
    
    # Load data
    dataset = DatasetBuilder(config["data"]["feature_path"])
    df = dataset.load()
    X, y, features = dataset.build(df)
    X_train, X_val, y_train, y_val = dataset.split(X, y)
    
    logger.info(f"Training samples: {len(X_train)}, Validation samples: {len(X_val)}")
    
    # Hyperparameter tuning
    n_trials = config.get("training", {}).get("tuning_trials", 50)
    tuner = HyperparameterTuner(X_train, y_train, n_trials=n_trials, cv_folds=3)
    
    tuning_results = tuner.tune()
    
    # Train final model with best params
    logger.info("Training final model with best parameters...")
    best_model = tuner.get_best_model()
    
    # XGBoost 2.0+ uses different API for early stopping
    try:
        # Try new API (XGBoost 2.0+)
        best_model.fit(
            X_train, 
            y_train,
            eval_set=[(X_val, y_val)],
            verbose=False
        )
    except TypeError:
        # Fallback to old API
        best_model.fit(
            X_train, 
            y_train,
            eval_set=[(X_val, y_val)],
            early_stopping_rounds=50,
            verbose=False
        )
    
    # Evaluate
    evaluator = ModelEvaluator()
    metrics = evaluator.evaluate(best_model, X_val, y_val, X_train, y_train)
    feature_importance = evaluator.get_feature_importance(best_model, features)
    
    # Save artifacts
    model_dir = Path(config["training"]["model_dir"])
    report_dir = Path(config["training"]["report_dir"])
    model_dir.mkdir(exist_ok=True, parents=True)
    report_dir.mkdir(exist_ok=True, parents=True)
    
    # Save model
    model_path = model_dir / "demand_model.pkl"
    joblib.dump(best_model, model_path)
    logger.info(f"Model saved to {model_path}")
    
    # Save features
    with open(model_dir / "features.json", "w") as f:
        json.dump(features, f, indent=2)
    
    # Save metrics with tuning results
    all_metrics = {**metrics, **tuning_results}
    with open(report_dir / "training_metrics.json", "w") as f:
        json.dump(all_metrics, f, indent=4)
    
    # Save feature importance
    if not feature_importance.empty:
        feature_importance.to_csv(report_dir / "feature_importance.csv", index=False)
    
    logger.info("=" * 60)
    logger.info(f"Training completed! Final R2: {metrics['R2']:.3f}, MAE: {metrics['MAE']:.2f}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
