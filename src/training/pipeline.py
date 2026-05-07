from pathlib import Path
import json
import joblib

from src.training.dataset import DatasetBuilder
from src.training.trainer import DemandModelTrainer
from src.training.evaluate import ModelEvaluator
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TrainingPipeline:
    """Enhanced training pipeline with CV and feature importance"""

    def __init__(self, config):
        self.config = config
        self.feature_path = config["data"]["feature_path"]
        self.model_dir = Path(config["training"]["model_dir"])
        self.report_dir = Path(config["training"]["report_dir"])
        self.model_dir.mkdir(exist_ok=True, parents=True)
        self.report_dir.mkdir(exist_ok=True, parents=True)

    def run(self):
        logger.info("=" * 60)
        logger.info("Starting Enhanced Training Pipeline")
        logger.info("=" * 60)
        
        # Load and prepare data
        dataset = DatasetBuilder(self.feature_path)
        df = dataset.load()
        X, y, features = dataset.build(df)
        X_train, X_val, y_train, y_val = dataset.split(X, y)
        
        logger.info(f"Training samples: {len(X_train)}, Validation samples: {len(X_val)}")
        logger.info(f"Features: {len(features)}")

        # Build and train model
        trainer = DemandModelTrainer(self.config["model"])
        model = trainer.build_model()
        
        # Cross-validation (optional, can be slow)
        if self.config.get("training", {}).get("run_cv", False):
            logger.info("Running cross-validation...")
            cv_results = trainer.cross_validate(model, X, y, n_splits=5)
        else:
            cv_results = {}
            logger.info("Skipping cross-validation (set run_cv: true to enable)")
        
        # Train final model
        model = trainer.train(model, X_train, y_train, X_val, y_val)

        # Evaluate
        evaluator = ModelEvaluator()
        metrics = evaluator.evaluate(model, X_val, y_val, X_train, y_train)
        
        # Feature importance
        feature_importance = evaluator.get_feature_importance(model, features)
        
        # Residual analysis
        y_pred = model.predict(X_val)
        residual_stats = evaluator.analyze_residuals(y_val, y_pred)

        # Combine all results
        all_metrics = {
            **metrics,
            **cv_results,
            **residual_stats
        }

        # Save artifacts
        self.save_artifacts(model, all_metrics, features, feature_importance)

        logger.info("=" * 60)
        logger.info("Training Pipeline Completed Successfully")
        logger.info(f"Final R2: {metrics['R2']:.3f}, MAE: {metrics['MAE']:.2f}")
        logger.info("=" * 60)

    def save_artifacts(self, model, metrics, features, feature_importance):
        """Save model, metrics, and analysis artifacts"""
        
        # Save model
        model_path = self.model_dir / "demand_model.pkl"
        joblib.dump(model, model_path)
        logger.info(f"Model saved to {model_path}")

        # Save feature list
        with open(self.model_dir / "features.json", "w") as f:
            json.dump(features, f, indent=2)

        # Save metrics
        with open(self.report_dir / "training_metrics.json", "w") as f:
            json.dump(metrics, f, indent=4)
        logger.info(f"Metrics saved to {self.report_dir / 'training_metrics.json'}")

        # Save feature importance
        if not feature_importance.empty:
            feature_importance.to_csv(
                self.report_dir / "feature_importance.csv", 
                index=False
            )
            logger.info(f"Feature importance saved to {self.report_dir / 'feature_importance.csv'}")
