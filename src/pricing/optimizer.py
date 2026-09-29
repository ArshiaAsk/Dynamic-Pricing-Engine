import numpy as np
import pandas as pd


class PriceOptimizer:

    def __init__(self, model, feature_columns):
        self.model = model
        self.feature_columns = feature_columns

    def _build_features(self, base_features, price):
        """
        Build the complete price-dependent feature frame for a candidate price.

        Mirrors ``BayesianPriceOptimizer._build_features`` so the grid search
        selects the same 31 columns the model was trained on. Extracting a single
        shared serving builder is ROADMAP R4; this is the interim in-place fix.
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

        # In API inference there is no short-term price history, so fill derived deltas/rolls
        # with stable defaults rather than failing column selection.
        features.setdefault("price_change_1d", 0.0)
        features.setdefault("price_change_7d", 0.0)
        features.setdefault("roll_mean_price_7", price)
        features.setdefault("roll_mean_price_14", price)
        features.setdefault("roll_mean_price_28", price)

        return features

    def optimize(self, base_features, price_min, price_max, steps=50):
        prices = np.linspace(price_min, price_max, steps)

        best_price = None
        best_revenue = -np.inf
        best_demand = None

        for p in prices:
            features = self._build_features(base_features, p)

            # Convert to DataFrame for model prediction
            X = pd.DataFrame([features])[self.feature_columns]

            predicted_demand = self.model.predict(X)[0]

            revenue = p * predicted_demand

            if revenue > best_revenue:
                best_revenue = revenue
                best_price = p
                best_demand = predicted_demand

        return {
            "optimal_price": float(best_price),
            "expected_demand": float(best_demand),
            "expected_revenue": float(best_revenue)
        }
