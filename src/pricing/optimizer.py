import numpy as np
import pandas as pd


class PriceOptimizer:

    def __init__(self, model, feature_columns):
        self.model = model
        self.feature_columns = feature_columns

    def optimize(self, base_features, price_min, price_max, steps=50):
        prices = np.linspace(price_min, price_max, steps)

        best_price = None
        best_revenue = -np.inf
        best_demand = None

        for p in prices:
            features = base_features.copy()

            features["price"] = p
            features["price_ratio"] = p / features["competitor_price"]
            features["price_diff_pct"] = (p - features["competitor_price"]) / features["competitor_price"]
            features["price_ratio_sin"] = features["price_ratio"] * features["sin_annual"]
            features["price_ratio_cos"] = features["price_ratio"] * features["cos_annual"]

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
