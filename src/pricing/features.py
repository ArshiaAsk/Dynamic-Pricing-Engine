"""Single source of truth for price-dependent serving features.

Training-time feature construction lives in ``src/features/feature_builder.py``;
this module is its inference-time mirror for the candidate prices an optimizer
evaluates. Both optimizers must build their per-price feature vector here so the
two search strategies can never diverge — that divergence is exactly what caused
the R2 ``KeyError`` (one optimizer built 22 columns, the other 31).

DECISIONS D4 / ROADMAP R4.
"""
from typing import Dict, Optional

import numpy as np


def build_serving_features(
    base_features: Dict,
    price: float,
    feature_columns: Optional[list] = None,
) -> Dict:
    """Build the serving feature dictionary for one candidate price.

    Args:
        base_features: Request-level features (calendar, competitor price, lags).
        price: The candidate price being evaluated.
        feature_columns: When given, the returned dict is restricted to and
            ordered by exactly these columns (the committed
            ``models/features.json`` list), so the model always receives the
            training column set in the training order.

    Returns:
        A feature dictionary for a single candidate price.
    """
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

    # In API inference there is no short-term price history, so fill derived
    # deltas/rolls with stable defaults rather than failing column selection.
    features.setdefault("price_change_1d", 0.0)
    features.setdefault("price_change_7d", 0.0)
    features.setdefault("roll_mean_price_7", price)
    features.setdefault("roll_mean_price_14", price)
    features.setdefault("roll_mean_price_28", price)

    if feature_columns is not None:
        return {column: features[column] for column in feature_columns}
    return features
