#!/usr/bin/env python3
"""Training script with hyperparameter tuning"""
import yaml
from pathlib import Path
import sys
import joblib
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.training.dataset import DatasetBuilder
from src.training.hyperparameter_tuning import HyperparameterTuner
from src.training.evaluate import ModelEvaluator
from src.utils.logger import get_logger
from src.utils.mlflow_tracking import MlflowTracker

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

    tracker = MlflowTracker("demand_forecasting")

    with tracker.start_run(run_name="xgboost_optuna_training"):

        # log config parameters
        tracker.log_params(config["model"])

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

        # log tuning metadata
        tracker.log_params({
            "tuning_trials": n_trials,
            "cv_folds": 3
        })

        # Train final model
        logger.info("Training final model with best parameters...")
        best_model = tuner.get_best_model()

        try:
            best_model.fit(
                X_train,
                y_train,
                eval_set=[(X_val, y_val)],
                verbose=False
            )
        except TypeError:
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

        # log metrics
        tracker.log_metrics(metrics)

        feature_importance = evaluator.get_feature_importance(best_model, features)

        # Save artifacts
        model_dir = Path(config["training"]["model_dir"])
        report_dir = Path(config["training"]["report_dir"])

        model_dir.mkdir(exist_ok=True, parents=True)
        report_dir.mkdir(exist_ok=True, parents=True)

        # Save model locally
        model_path = model_dir / "demand_model.pkl"
        joblib.dump(best_model, model_path)

        # log model to mlflow
        tracker.log_model(best_model)

        # Save features
        feature_file = model_dir / "features.json"
        with open(feature_file, "w") as f:
            json.dump(features, f, indent=2)

        tracker.log_artifact(str(feature_file))

        # Save metrics report
        metrics_file = report_dir / "training_metrics.json"
        with open(metrics_file, "w") as f:
            json.dump(metrics, f, indent=4)

        tracker.log_artifact(str(metrics_file))

        # Feature importance artifact
        if not feature_importance.empty:
            fi_path = report_dir / "feature_importance.csv"
            feature_importance.to_csv(fi_path, index=False)
            tracker.log_artifact(str(fi_path))

        logger.info("=" * 60)
        logger.info(f"Training completed! Final R2: {metrics['R2']:.3f}, MAE: {metrics['MAE']:.2f}")
        logger.info("=" * 60)



if __name__ == "__main__":
    main()
