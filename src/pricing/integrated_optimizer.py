"""Integrated optimizer with feature transformer"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from typing import Dict, Optional
from src.features.transformer import FeatureTransformer
from src.utils.logger import get_logger

logger = get_logger(__name__)


class IntegratedPricingOptimizer:
    """
    Integrated optimizer that combines feature transformation and optimization
    Production-ready with proper error handling and logging
    """
    
    def __init__(self, model, feature_columns: list):
        self.model = model
        self.feature_columns = feature_columns
        self.transformer = FeatureTransformer(feature_columns)
        
    def optimize(
        self,
        input_data: Dict,
        price_min: float,
        price_max: float,
        cost: Optional[float] = None,
        min_margin_pct: float = 0.0,
        inventory_limit: Optional[int] = None,
        method: str = 'L-BFGS-B'
    ) -> Dict:
        """
        Optimize price with integrated feature transformation
        
        Args:
            input_data: Raw input data (will be transformed)
            price_min: Minimum price
            price_max: Maximum price
            cost: Product cost (for margin calculation)
            min_margin_pct: Minimum profit margin
            inventory_limit: Maximum inventory
            method: Optimization method
            
        Returns:
            Optimization results with metadata
        """
        
        # Validate input
        is_valid, error_msg = self.transformer.validate_input(input_data)
        if not is_valid:
            raise ValueError(f"Invalid input data: {error_msg}")
        
        # Adjust price_min for margin constraint
        if cost is not None and min_margin_pct > 0:
            min_price_for_margin = cost * (1 + min_margin_pct)
            effective_price_min = max(price_min, min_price_for_margin)
            
            if effective_price_min > price_max:
                logger.warning(
                    f"Margin constraint cannot be satisfied. "
                    f"Required: ${min_price_for_margin:.2f}, Max: ${price_max:.2f}"
                )
                effective_price_min = price_min
        else:
            effective_price_min = price_min
        
        # Objective function
        def objective(price_array):
            price = float(price_array[0])
            
            try:
                # Transform features
                X = self.transformer.transform(input_data, price)
                
                # Predict demand
                demand = self.model.predict(X)[0]
                
                # Apply inventory constraint
                if inventory_limit is not None:
                    demand = min(demand, inventory_limit)
                
                # Return negative revenue (for minimization)
                revenue = price * demand
                return -revenue
                
            except Exception as e:
                logger.error(f"Error in objective function: {e}")
                return 1e10  # Large penalty for errors
        
        # Optimize
        bounds = [(effective_price_min, price_max)]
        x0 = [(effective_price_min + price_max) / 2]
        
        try:
            result = minimize(
                objective,
                x0,
                method=method,
                bounds=bounds,
                options={'maxiter': 100, 'ftol': 1e-6}
            )
            
            optimal_price = float(result.x[0])
            success = result.success
            iterations = result.nit if hasattr(result, 'nit') else 0
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            # Fallback to midpoint
            optimal_price = (effective_price_min + price_max) / 2
            success = False
            iterations = 0
        
        # Calculate final metrics
        X_final = self.transformer.transform(input_data, optimal_price)
        predicted_demand = self.model.predict(X_final)[0]
        
        if inventory_limit is not None:
            predicted_demand = min(predicted_demand, inventory_limit)
        
        expected_revenue = optimal_price * predicted_demand
        
        # Build result
        result_dict = {
            "optimal_price": float(optimal_price),
            "expected_demand": float(predicted_demand),
            "expected_revenue": float(expected_revenue),
            "optimization_success": bool(success),
            "optimization_iterations": int(iterations),
            "optimization_method": method,
            "price_min": float(effective_price_min),
            "price_max": float(price_max),
        }
        
        # Add margin info if cost provided
        if cost is not None:
            margin = (optimal_price - cost) / optimal_price
            result_dict.update({
                "profit_margin": float(margin),
                "profit_per_unit": float(optimal_price - cost),
                "total_profit": float((optimal_price - cost) * predicted_demand),
                "cost": float(cost),
            })
        
        # Add constraint info
        if inventory_limit is not None:
            result_dict["inventory_limit"] = int(inventory_limit)
            result_dict["inventory_constrained"] = bool(predicted_demand >= inventory_limit)
        
        logger.info(
            f"Optimized: price=${optimal_price:.2f}, "
            f"demand={predicted_demand:.1f}, revenue=${expected_revenue:.2f}"
        )
        
        return result_dict
    
    def predict_demand(self, input_data: Dict, price: float) -> float:
        """
        Predict demand for a given price
        
        Args:
            input_data: Raw input data
            price: Price to evaluate
            
        Returns:
            Predicted demand
        """
        X = self.transformer.transform(input_data, price)
        return float(self.model.predict(X)[0])
    
    def evaluate_price_range(
        self,
        input_data: Dict,
        price_min: float,
        price_max: float,
        steps: int = 20
    ) -> pd.DataFrame:
        """
        Evaluate demand and revenue across price range
        
        Args:
            input_data: Raw input data
            price_min: Minimum price
            price_max: Maximum price
            steps: Number of price points to evaluate
            
        Returns:
            DataFrame with price, demand, revenue
        """
        prices = np.linspace(price_min, price_max, steps)
        results = []
        
        for price in prices:
            demand = self.predict_demand(input_data, price)
            revenue = price * demand
            
            results.append({
                'price': price,
                'demand': demand,
                'revenue': revenue
            })
        
        return pd.DataFrame(results)
