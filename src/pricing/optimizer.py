import numpy as np
import pandas as pd

from src.pricing.features import build_serving_features


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
            features = build_serving_features(base_features, p, self.feature_columns)

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
