import joblib
import json
from pathlib import Path
from typing import Dict, Optional
from threading import Lock
import time

import mlflow
from mlflow.tracking import MlflowClient

from src.pricing.optimizer import PriceOptimizer
from src.pricing.bayesian_optimizer import BayesianPriceOptimizer
from src.pricing.model_loader import load_production_model
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PricingEngine:
    """Enhanced pricing engine with multiple optimization strategies"""

    def __init__(self, config):
        self.config = config

        self.model_path = Path(config["pricing"]["model_path"])
        self.feature_path = Path(config["pricing"]["feature_columns_path"])
        
        self.model_name = config["pricing"].get(
            "registered_model_name", "demand_forecasting_model"
        )
        self.reload_interval = config["pricing"].get("reload_interval_sec", 60)

        self.model = None
        self.feature_columns = None

        self._last_reload_time = 0
        self._current_version = None
        self._lock = Lock()

        self.load_model(force=True)

    # Load model and features
    def load_model(self, force=False):
        """Load or reload model from MLflow Production stage"""
        with self._lock:
            current_time = time.time()

            if not force and (current_time - self._last_reload_time < self.reload_interval):
                return
            
            try:
                mlflow.set_tracking_uri("http://localhost:5000")
                client = MlflowClient()

                latest = client.get_latest_versions(
                    self.model_name, stages=["Production"]
                )

                if latest:
                    version = latest[0].version

                    if version != self._current_version:
                        logger.info(f"Loading new model version: {version}")

                        model_uri = f"models:/{self.model_name}/Production"
                        self.model = mlflow.pyfunc.load_model(model_uri)

                        self._current_version = version
                        self._last_reload_time = current_time
                    else:
                        logger.warning("No Production model found in mlflow.")

            except Exception as e:
                logger.warning(f"MLflow load failed. Falling back to local model. {e}")
                self.model = joblib.load(self.model_path)

            # Load features
            with open(self.feature_path) as f:
                self.feature_columns = json.load(f)
        
            logger.info(
                    f"Pricing engine ready | features: {len(self.feature_columns)} | "
                    f"model_version: {self._current_version}"
                )

    def get_optimal_price(
        self, 
        base_features: Dict, 
        price_min: float, 
        price_max: float,
        method: str = "bayesian",
        **kwargs
    ) -> Dict:
        """
        Get optimal price using specified optimization method
        
        Args:
            base_features: Base feature dictionary
            price_min: Minimum price
            price_max: Maximum price
            method: "bayesian" or "grid" (default: bayesian)
            **kwargs: Additional arguments for optimizer
            
        Returns:
            Dictionary with optimization results
        """
        # Auto reload check
        self.load_model()

        if method == "bayesian":
            optimizer = BayesianPriceOptimizer(self.model, self.feature_columns)
            
            # Check if constraints are provided
            if "cost" in kwargs and "min_margin_pct" in kwargs:
                result = optimizer.optimize_with_constraints(
                    base_features,
                    price_min,
                    price_max,
                    cost=kwargs["cost"],
                    min_margin_pct=kwargs.get("min_margin_pct", 0.1),
                    inventory_limit=kwargs.get("inventory_limit")
                )
            else:
                result = optimizer.optimize(
                    base_features,
                    price_min,
                    price_max,
                    inventory_limit=kwargs.get("inventory_limit")
                )
        
        elif method == "grid":
            optimizer = PriceOptimizer(self.model, self.feature_columns)
            steps = kwargs.get("steps", 50)
            result = optimizer.optimize(base_features, price_min, price_max, steps)
        
        else:
            raise ValueError(f"Unknown optimization method: {method}")
        
        result["optimization_method"] = method
        result["model_version"] = self._current_version

        return result
    
    def compare_methods(
        self,
        base_features: Dict,
        price_min: float,
        price_max: float
    ) -> Dict:
        """Compare grid search vs Bayesian optimization"""
        
        logger.info("Comparing optimization methods...")
        
        # Grid search
        grid_result = self.get_optimal_price(
            base_features, price_min, price_max, method="grid"
        )
        
        # Bayesian
        bayesian_result = self.get_optimal_price(
            base_features, price_min, price_max, method="bayesian"
        )
        
        comparison = {
            "grid_search": grid_result,
            "bayesian": bayesian_result,
            "revenue_improvement": float(
                bayesian_result["expected_revenue"] - grid_result["expected_revenue"]
            ),
            "price_difference": float(
                bayesian_result["optimal_price"] - grid_result["optimal_price"]
            )
        }
        
        logger.info(f"Revenue improvement (Bayesian vs Grid): "
                   f"${comparison['revenue_improvement']:.2f}")
        
        return comparison
