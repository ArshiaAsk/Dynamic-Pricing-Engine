import joblib
import json
import os
from pathlib import Path
from typing import Dict, Optional
from threading import Lock
import time

from src.pricing.optimizer import PriceOptimizer
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
        # Where the currently served model came from: "mlflow" (registry) or
        # "local" (the committed joblib artifact). Exposed via /v1/health.
        self._model_source = "local"
        self._lock = Lock()

        self.load_model(force=True)

    @property
    def model_source(self) -> str:
        """Active model source: ``"mlflow"`` or ``"local"``."""
        return self._model_source

    @property
    def model_version(self) -> Optional[str]:
        """Active registry model version, or ``None`` when serving locally."""
        return self._current_version

    def _resolve_production(self, client):
        """Resolve the production model to ``(version, model_uri)``.

        Prefers the ``production`` alias (what ``scripts/promote_model.py``
        writes), then falls back to the ``stage=Production`` tag. Returns
        ``(None, None)`` when neither exists.
        """
        try:
            model_version = client.get_model_version_by_alias(self.model_name, "production")
            if model_version is not None:
                return str(model_version.version), f"models:/{self.model_name}@production"
        except Exception:
            pass

        versions = client.search_model_versions(
            filter_string=f"name='{self.model_name}' and tags.stage='Production'",
            order_by=["version_number DESC"],
            max_results=1,
        )
        if versions:
            version = versions[0]
            return str(version.version), f"models:/{self.model_name}/{version.version}"
        return None, None

    # Load model and features
    def load_model(self, force=False):
        """Load the MLflow production model, or fall back to the local artifact.

        The fallback is never silent: when no production version/alias exists or
        the registry is unreachable, this logs at ERROR and records
        ``model_source == "local"`` so ``/v1/health`` exposes the degradation.
        """
        with self._lock:
            current_time = time.time()

            if not force and (current_time - self._last_reload_time < self.reload_interval):
                return

            self._model_source = "local"
            self._current_version = None
            loaded_from_registry = False

            try:
                # MLflow is optional: import it lazily so the API can start and
                # serve the local artifact when mlflow is unavailable or broken.
                import mlflow
                from mlflow.tracking import MlflowClient

                # Bound the registry calls so an unreachable/misconfigured
                # tracking server cannot hang the request path (CONVENTIONS
                # rule 31). Users can still override these explicitly.
                os.environ.setdefault("MLFLOW_HTTP_REQUEST_TIMEOUT", "5")
                os.environ.setdefault("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "1")

                mlflow.set_tracking_uri(
                    os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
                )
                client = MlflowClient()

                version, model_uri = self._resolve_production(client)
                if model_uri is not None:
                    logger.info(f"Loading model version {version} from MLflow registry")
                    self.model = mlflow.pyfunc.load_model(model_uri)
                    self._current_version = version
                    self._model_source = "mlflow"
                    loaded_from_registry = True
                else:
                    logger.error(
                        f"No Production version or 'production' alias found in the MLflow "
                        f"registry for '{self.model_name}'. Falling back to the local "
                        f"artifact {self.model_path}."
                    )

            except Exception as e:
                logger.error(
                    f"MLflow registry load failed for '{self.model_name}': {e}. "
                    f"Falling back to the local artifact {self.model_path}."
                )

            if not loaded_from_registry:
                self.model = joblib.load(self.model_path)

            self._last_reload_time = current_time

            # Load features
            with open(self.feature_path) as f:
                self.feature_columns = json.load(f)

            logger.info(
                f"Pricing engine ready | features: {len(self.feature_columns)} | "
                f"source: {self._model_source} | model_version: {self._current_version}"
            )

    def get_optimal_price(
        self, 
        base_features: Dict, 
        price_min: float, 
        price_max: float,
        method: str = "grid_search",
        **kwargs
    ) -> Dict:
        """
        Get the revenue-optimal price with the canonical grid search.

        Args:
            base_features: Base feature dictionary
            price_min: Minimum price
            price_max: Maximum price
            method: "grid_search" (canonical) or "grid" (alias). Any other
                value is invalid input; the API rejects it with HTTP 422 before
                it reaches the engine (DECISIONS D2).
            **kwargs: Optimizer options (``steps``, ``inventory_limit``) and
                business constraints (``cost`` + ``min_margin_pct``)

        Returns:
            Dictionary with optimization results
        """
        # Auto reload check
        self.load_model()

        if method not in ("grid", "grid_search"):
            raise ValueError(f"Unknown optimization method: {method}")

        optimizer = PriceOptimizer(self.model, self.feature_columns)

        # Check if constraints are provided
        if "cost" in kwargs and "min_margin_pct" in kwargs:
            result = optimizer.optimize_with_constraints(
                base_features,
                price_min,
                price_max,
                cost=kwargs["cost"],
                min_margin_pct=kwargs.get("min_margin_pct", 0.1),
                inventory_limit=kwargs.get("inventory_limit"),
            )
        else:
            result = optimizer.optimize(
                base_features,
                price_min,
                price_max,
                steps=kwargs.get("steps", PriceOptimizer.DEFAULT_STEPS),
                inventory_limit=kwargs.get("inventory_limit"),
            )

        result["optimization_method"] = method
        result["model_version"] = self._current_version

        return result
