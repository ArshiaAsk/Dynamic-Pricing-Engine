from fastapi import APIRouter, HTTPException
from src.api.schemas import PricingRequest, PricingResponse
from src.pricing.engine import PricingEngine
from pathlib import Path
import yaml
import pandas as pd
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

CONFIG_PATH = Path("configs/config.yaml")

with open(CONFIG_PATH) as f:
    config = yaml.safe_load(f)

engine = PricingEngine(config)


@router.post("/optimize-price", response_model=PricingResponse)
def optimize_price(payload: PricingRequest):
    """
    Optimize product price based on demand forecasting
    
    Supports both grid search and Bayesian optimization methods.
    Can include business constraints like minimum margin and inventory limits.
    """
    try:
        # Convert request to dict
        features_dict = payload.dict(exclude={'price_min', 'price_max', 'optimization_method', 
                                               'cost', 'min_margin_pct', 'inventory_limit'})
        
        # Remove None values
        features_dict = {k: v for k, v in features_dict.items() if v is not None}
        
        # Get price range from request or config
        price_min = payload.price_min or config["pricing"].get("price_min", 30.0)
        price_max = payload.price_max or config["pricing"].get("price_max", 120.0)
        
        # Optimization kwargs
        opt_kwargs = {}
        if payload.cost is not None:
            opt_kwargs["cost"] = payload.cost
            opt_kwargs["min_margin_pct"] = payload.min_margin_pct
        if payload.inventory_limit is not None:
            opt_kwargs["inventory_limit"] = payload.inventory_limit
        
        # Optimize
        result = engine.get_optimal_price(
            features_dict,
            price_min,
            price_max,
            method=payload.optimization_method,
            **opt_kwargs
        )
        
        logger.info(f"Optimized price for product {payload.product_id}: "
                   f"${result['optimal_price']:.2f}")
        
        return PricingResponse(**result)
    
    except Exception as e:
        logger.error(f"Pricing optimization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": engine.model is not None,
        "features_count": len(engine.feature_columns)
    }
