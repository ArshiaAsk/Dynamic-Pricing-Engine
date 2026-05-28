"""Bayesian optimization for price optimization"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from typing import Dict, Callable
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BayesianPriceOptimizer:
    """
    Advanced price optimizer using Bayesian optimization
    Replaces naive grid search with gradient-based optimization
    """
    
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
        method: str = 'L-BFGS-B'
    ) -> Dict:
        """
        Find optimal price using Bayesian optimization
        
        Args:
            base_features: Base feature dictionary
            price_min: Minimum allowed price
            price_max: Maximum allowed price
            min_margin: Minimum profit margin constraint
            inventory_limit: Maximum units that can be sold
            method: Optimization method
            
        Returns:
            Dictionary with optimal price, demand, and revenue
        """
        
        # Objective function (negative revenue to minimize)
        def objective(price):
            price = float(price[0])
            
            # Build features
            features = self._build_features(base_features, price)
            
            # Convert to DataFrame for model prediction
            X = pd.DataFrame([features])[self.feature_columns]
            
            # Predict demand
            predicted_demand = self.model.predict(X)[0]
            
            # Apply inventory constraint
            if inventory_limit is not None:
                predicted_demand = min(predicted_demand, inventory_limit)
            
            # Calculate revenue (negative for minimization)
            revenue = price * predicted_demand
            
            return -revenue
        
        # Constraints
        bounds = [(price_min, price_max)]
        
        # Initial guess (middle of range)
        x0 = [(price_min + price_max) / 2]
        
        # Run optimization
        result = minimize(
            objective,
            x0,
            method=method,
            bounds=bounds,
            options={'maxiter': 100}
        )
        
        optimal_price = float(result.x[0])
        
        # Calculate final metrics
        features = self._build_features(base_features, optimal_price)
        X = pd.DataFrame([features])[self.feature_columns]
        predicted_demand = self.model.predict(X)[0]
        
        if inventory_limit is not None:
            predicted_demand = min(predicted_demand, inventory_limit)
        
        expected_revenue = optimal_price * predicted_demand
        
        logger.info(f"Optimized price: ${optimal_price:.2f}, "
                   f"Expected demand: {predicted_demand:.1f}, "
                   f"Revenue: ${expected_revenue:.2f}")
        
        return {
            "optimal_price": float(optimal_price),
            "expected_demand": float(predicted_demand),
            "expected_revenue": float(expected_revenue),
            "optimization_success": bool(result.success),
            "optimization_iterations": int(result.nit) if hasattr(result, 'nit') else 0
        }
    
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
