import numpy as np
import pandas as pd

from src.pricing.features import build_serving_features


class PriceOptimizer:
    """Canonical served optimizer: an adaptive dense price-grid search.

    The demand model is piecewise constant in price, so revenue is piecewise
    linear and can have a narrow peak. A fixed-width grid can step over that
    peak on a wide price range (the ROADMAP R2 caveat: ratios as low as ~0.971
    on ``(30,120)`` at ``steps=50``). The number of candidates therefore scales
    with the bound width so the spacing stays at or below
    ``TARGET_RESOLUTION``. This is the single optimizer served as
    ``"grid_search"`` (DECISIONS D2 / ROADMAP R6).
    """

    # Target price spacing of the evaluated grid.
    TARGET_RESOLUTION = 0.02
    # Never evaluate fewer candidates than the acceptance reference grid.
    MIN_GRID_POINTS = 901
    # Cap the work for pathologically wide price ranges.
    MAX_GRID_POINTS = 20001
    # Floor for an explicitly requested step count.
    DEFAULT_STEPS = 50

    def __init__(self, model, feature_columns):
        self.model = model
        self.feature_columns = feature_columns

    def optimize(self, base_features, price_min, price_max, steps=DEFAULT_STEPS,
                 inventory_limit=None):
        """Return the revenue-maximizing price on ``[price_min, price_max]``."""
        price_min = float(price_min)
        price_max = float(price_max)

        prices = np.linspace(
            price_min, price_max, self._grid_points(price_min, price_max, steps)
        )

        frame = pd.DataFrame(
            [build_serving_features(base_features, float(p), self.feature_columns)
             for p in prices]
        )[self.feature_columns]

        demands = self._predict_demands(frame)
        if inventory_limit is not None:
            demands = np.minimum(demands, inventory_limit)
        revenues = prices * demands

        best = int(np.argmax(revenues))
        return {
            "optimal_price": float(prices[best]),
            "expected_demand": float(demands[best]),
            "expected_revenue": float(revenues[best]),
        }

    def optimize_with_constraints(self, base_features, price_min, price_max, cost,
                                  min_margin_pct=0.1, inventory_limit=None):
        """Optimize under a minimum-margin floor and an optional inventory cap."""
        min_price_for_margin = cost * (1 + min_margin_pct)
        effective_price_min = max(float(price_min), min_price_for_margin)
        if effective_price_min > price_max:
            effective_price_min = float(price_min)

        result = self.optimize(
            base_features, effective_price_min, price_max,
            inventory_limit=inventory_limit,
        )

        margin = (result["optimal_price"] - cost) / result["optimal_price"]
        result["profit_margin"] = float(margin)
        result["profit_per_unit"] = float(result["optimal_price"] - cost)
        result["total_profit"] = float(result["profit_per_unit"] * result["expected_demand"])
        return result

    def _grid_points(self, price_min, price_max, steps):
        """Number of grid candidates: scales with the bound width.

        A caller-supplied ``steps`` is treated as a floor; the grid is always at
        least ``MIN_GRID_POINTS`` dense and at most ``TARGET_RESOLUTION`` apart.
        A degenerate range collapses to a single candidate.
        """
        span = price_max - price_min
        if span <= 0:
            return 1
        adaptive = int(np.ceil(span / self.TARGET_RESOLUTION)) + 1
        return int(min(
            self.MAX_GRID_POINTS,
            max(self.MIN_GRID_POINTS, int(steps), adaptive),
        ))

    def _predict_demands(self, frame):
        """Predict demand for every row of ``frame``.

        Batched prediction is used when the model supports it. A model whose
        ``predict`` ignores batch shape (e.g. a test double returning a single
        value) is evaluated row by row so the contract still holds.
        """
        predictions = np.asarray(self.model.predict(frame), dtype=float).reshape(-1)
        if predictions.size == len(frame):
            return predictions
        return np.array([
            float(np.asarray(self.model.predict(frame.iloc[[i]])).reshape(-1)[0])
            for i in range(len(frame))
        ])
