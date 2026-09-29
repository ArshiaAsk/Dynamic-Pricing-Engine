"""Price optimizer using a derivative-free global search.

The public class name and the API's ``"bayesian"`` method label are retained for
backward compatibility; renaming them is tracked separately by DECISIONS D3 /
ROADMAP R6. The implementation is a dense, vectorized price-grid search with
local refinement — exact for the piecewise-constant XGBoost objective, on which
gradient methods stall because the numerical gradient is ~0.
"""
from typing import Dict

import numpy as np
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


class BayesianPriceOptimizer:
    """
    Derivative-free price optimizer (dense price grid + local refinement).

    Evaluates a dense grid of candidate prices, then repeatedly refines around
    the best candidate. The demand model is piecewise constant in price, so
    revenue is piecewise linear and its maximum lies on a price boundary; the
    refinement converges onto that boundary.
    """

    # Target absolute spacing of the first (global) price grid. The objective is
    # piecewise linear in price and very jagged (each XGBoost split is a kink), so
    # the first pass must be dense enough to land in the global basin; a coarse
    # pass can settle on a narrow local peak and refinement then cannot escape it.
    DEFAULT_RESOLUTION = 0.02
    # Never sample more coarsely than a 901-point grid (the acceptance reference).
    MIN_GRID_POINTS = 901
    # Upper bound on candidates in the first pass, for very wide price ranges.
    MAX_GRID_POINTS = 20001
    # Candidate prices per subsequent local-refinement pass, and how many.
    REFINE_GRID_POINTS = 201
    DEFAULT_REFINE_PASSES = 2

    def __init__(self, model, feature_columns):
        self.model = model
        self.feature_columns = feature_columns

    def optimize(
        self,
        base_features: Dict,
        price_min: float,
        price_max: float,
        min_margin: float = 0.0,
        inventory_limit: int = None,
        resolution: float = DEFAULT_RESOLUTION,
        n_refine: int = DEFAULT_REFINE_PASSES,
    ) -> Dict:
        """
        Find the revenue-maximizing price with a derivative-free search.

        Args:
            base_features: Base feature dictionary.
            price_min: Minimum allowed price (inclusive).
            price_max: Maximum allowed price (inclusive).
            min_margin: Retained for signature compatibility; margin is enforced
                by ``optimize_with_constraints``.
            inventory_limit: Maximum units that can be sold.
            resolution: Target spacing of the first (global) price grid.
            n_refine: Number of local-refinement passes after the global pass.

        Returns:
            Dictionary with ``optimal_price``, ``expected_demand``,
            ``expected_revenue``, ``optimization_success`` and
            ``optimization_iterations``.
        """
        price_min = float(price_min)
        price_max = float(price_max)

        if price_max <= price_min:
            demand, revenue = self._evaluate(base_features, price_min, inventory_limit)
            logger.warning(
                f"Invalid price bounds (min={price_min} >= max={price_max}); "
                f"returning price_min."
            )
            return {
                "optimal_price": price_min,
                "expected_demand": float(demand),
                "expected_revenue": float(revenue),
                "optimization_success": False,
                "optimization_iterations": 0,
            }

        span = price_max - price_min
        n_points = min(
            self.MAX_GRID_POINTS,
            max(self.MIN_GRID_POINTS, int(np.ceil(span / resolution)) + 1),
        )

        lo, hi = price_min, price_max
        best_price = price_min
        evaluations = 0

        for pass_index in range(1 + max(0, n_refine)):
            prices = np.linspace(lo, hi, n_points)
            revenues = self._revenue_grid(base_features, prices, inventory_limit)
            evaluations += len(prices)

            best_price = float(prices[int(np.argmax(revenues))])

            step = (hi - lo) / (n_points - 1) if n_points > 1 else 0.0
            if step <= 0.0:
                break
            lo = max(price_min, best_price - step)
            hi = min(price_max, best_price + step)
            # Subsequent passes zoom into the basin found by the dense first pass.
            n_points = self.REFINE_GRID_POINTS

        demand, revenue = self._evaluate(base_features, best_price, inventory_limit)

        logger.info(
            f"Optimized price: ${best_price:.2f}, "
            f"Expected demand: {demand:.1f}, "
            f"Revenue: ${revenue:.2f} "
            f"({evaluations} candidates evaluated)"
        )

        return {
            "optimal_price": float(best_price),
            "expected_demand": float(demand),
            "expected_revenue": float(revenue),
            "optimization_success": True,
            "optimization_iterations": int(evaluations),
        }

    def _revenue_grid(self, base_features: Dict, prices: np.ndarray, inventory_limit) -> np.ndarray:
        """Vectorized revenue for every price in ``prices``."""
        frame = pd.DataFrame(
            [self._build_features(base_features, float(p)) for p in prices]
        )[self.feature_columns]
        demand = self._predict_demands(frame)
        if inventory_limit is not None:
            demand = np.minimum(demand, inventory_limit)
        return prices * demand

    def _evaluate(self, base_features: Dict, price: float, inventory_limit):
        """Return ``(demand, revenue)`` for a single price."""
        frame = pd.DataFrame(
            [self._build_features(base_features, float(price))]
        )[self.feature_columns]
        demand = float(self._predict_demands(frame)[0])
        if inventory_limit is not None:
            demand = min(demand, inventory_limit)
        return demand, float(price) * demand

    def _predict_demands(self, frame: pd.DataFrame) -> np.ndarray:
        """
        Predict demand for every row of ``frame``.

        Batched prediction is used when the model supports it. A model whose
        ``predict`` ignores batch shape (e.g. a test double that returns a single
        value) is evaluated row by row so the contract still holds.
        """
        predictions = np.asarray(self.model.predict(frame), dtype=float).reshape(-1)
        if predictions.size == len(frame):
            return predictions
        return np.array(
            [
                float(np.asarray(self.model.predict(frame.iloc[[i]])).reshape(-1)[0])
                for i in range(len(frame))
            ]
        )

    def _build_features(self, base_features: Dict, price: float) -> Dict:
        """Build feature dictionary with price-dependent features"""
        features = base_features.copy()

        features["price"] = price

        # Price ratio features
        if "competitor_price" in features:
            comp_price = features["competitor_price"]
            features["price_ratio"] = price / comp_price if comp_price > 0 else 1.0
            features["price_diff_pct"] = (price - comp_price) / comp_price if comp_price > 0 else 0.0

        # Interaction with seasonality
        if "sin_annual" in features:
            features["price_ratio_sin"] = features.get("price_ratio", 1.0) * features["sin_annual"]
        if "cos_annual" in features:
            features["price_ratio_cos"] = features.get("price_ratio", 1.0) * features["cos_annual"]
        if "competitor_price" in features:
            comp_price = features["competitor_price"]
            features["price_advantage"] = (comp_price - price) / comp_price if comp_price > 0 else 0.0
            features["log_comp_price"] = float(np.log1p(comp_price)) if comp_price >= 0 else 0.0
        features["log_price"] = float(np.log1p(price)) if price >= 0 else 0.0
        if "sin_annual" in features:
            features["price_advantage_sin"] = features.get("price_advantage", 0.0) * features["sin_annual"]

        # In API inference there is no short-term price history, so fill derived deltas/rolls
        # with stable defaults rather than failing column selection.
        features.setdefault("price_change_1d", 0.0)
        features.setdefault("price_change_7d", 0.0)
        features.setdefault("roll_mean_price_7", price)
        features.setdefault("roll_mean_price_14", price)
        features.setdefault("roll_mean_price_28", price)

        missing_columns = [col for col in self.feature_columns if col not in features]
        return features

    def optimize_with_constraints(
        self,
        base_features: Dict,
        price_min: float,
        price_max: float,
        cost: float,
        min_margin_pct: float = 0.1,
        inventory_limit: int = None
    ) -> Dict:
        """
        Optimize price with business constraints

        Args:
            base_features: Base features
            price_min: Min price
            price_max: Max price
            cost: Product cost
            min_margin_pct: Minimum profit margin (e.g., 0.1 = 10%)
            inventory_limit: Max inventory
        """

        # Adjust price_min to respect margin constraint
        min_price_for_margin = cost * (1 + min_margin_pct)
        effective_price_min = max(price_min, min_price_for_margin)

        if effective_price_min > price_max:
            logger.warning(f"Margin constraint cannot be satisfied. "
                          f"Required min price: ${min_price_for_margin:.2f}, "
                          f"Max allowed: ${price_max:.2f}")
            effective_price_min = price_min

        result = self.optimize(
            base_features,
            effective_price_min,
            price_max,
            inventory_limit=inventory_limit
        )

        # Add margin info
        margin = (result["optimal_price"] - cost) / result["optimal_price"]
        result["profit_margin"] = float(margin)
        result["profit_per_unit"] = float(result["optimal_price"] - cost)
        result["total_profit"] = float(result["profit_per_unit"] * result["expected_demand"])

        return result
