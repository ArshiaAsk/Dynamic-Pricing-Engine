from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from src.api.schemas import PricingRequest, PricingResponse
from src.pricing.engine import PricingEngine
from src.monitoring.prediction_logger import get_prediction_logger
from src.monitoring.health_checker import get_health_checker
from pathlib import Path
import yaml
import pandas as pd
import time
import json
import uuid
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

CONFIG_PATH = Path("configs/config.yaml")

# Default price window when a request omits price_min/price_max, as a fraction of
# the request's competitor price. The band lies inside the observed price_ratio
# training support (D32), so a default request never extrapolates. There is no
# absolute price default anywhere.
DEFAULT_PRICE_RATIO_MIN = 0.92
DEFAULT_PRICE_RATIO_MAX = 1.08

with open(CONFIG_PATH) as f:
    config = yaml.safe_load(f)

engine = PricingEngine(config)
prediction_logger = get_prediction_logger()
health_checker = get_health_checker()


@router.post("/optimize-price", response_model=PricingResponse)
def optimize_price(payload: PricingRequest):
    """
    Optimize product price based on demand forecasting
    
    Supports both grid search and Bayesian optimization methods.
    Can include business constraints like minimum margin and inventory limits.
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        # Convert request to dict
        features_dict = payload.model_dump(exclude={'price_min', 'price_max', 'optimization_method', 
                                               'cost', 'min_margin_pct', 'inventory_limit'})
        
        # Remove None values
        features_dict = {k: v for k, v in features_dict.items() if v is not None}
        
        # Get the price range from the request, or derive it from the competitor
        # price inside the training support (D32). No absolute default.
        price_min = (
            payload.price_min
            if payload.price_min is not None
            else payload.competitor_price * DEFAULT_PRICE_RATIO_MIN
        )
        price_max = (
            payload.price_max
            if payload.price_max is not None
            else payload.competitor_price * DEFAULT_PRICE_RATIO_MAX
        )
        
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
        
        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000
        
        # Log prediction
        prediction_logger.log_optimization(
            request_id=request_id,
            input_data=features_dict,
            result=result,
            response_time_ms=response_time_ms,
            metadata={
                'product_id': payload.product_id,
                'optimization_method': payload.optimization_method
            }
        )
        
        # Record successful request
        health_checker.record_request()
        
        logger.info(f"Optimized price for product {payload.product_id}: "
                   f"${result['optimal_price']:.2f} (request_id: {request_id})")
        
        return PricingResponse(**result)
    
    except Exception as e:
        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000
        
        # Log error
        prediction_logger.log_error(
            request_id=request_id,
            error_type=type(e).__name__,
            error_message=str(e),
            input_data=payload.model_dump(),
            metadata={'product_id': payload.product_id}
        )
        
        # Record error
        health_checker.record_error()
        
        logger.error(f"Pricing optimization failed (request_id: {request_id}): {str(e)}")

        # R16 / DECISIONS D21: never leak internal error text to the client. The
        # exception is logged server-side above; the response carries only a
        # generic message and the request id (rule 11).
        return JSONResponse(
            status_code=500,
            content={
                "message": "An internal error occurred while processing the request.",
                "request_id": request_id,
            },
        )


@router.get("/health")
def health_check():
    """Comprehensive health check endpoint"""
    health = health_checker.check_health(
        model=engine.model,
        model_source=engine.model_source,
        model_version=engine.model_version,
        feature_columns=engine.feature_columns,
    )
    
    # Return 503 if unhealthy
    if health['status'] != 'healthy':
        raise HTTPException(status_code=503, detail=health)
    
    return health


@router.get("/health/ready")
def readiness_check():
    """Readiness check for load balancer"""
    ready = health_checker.check_readiness(model=engine.model)
    
    if not ready['ready']:
        raise HTTPException(status_code=503, detail=ready)
    
    return ready


@router.get("/health/live")
def liveness_check():
    """Liveness check for container orchestration"""
    return health_checker.check_liveness()


@router.get("/metrics")
def get_metrics():
    """Get system metrics"""
    return {
        'health': health_checker.get_metrics(),
        'predictions': prediction_logger.get_stats()
    }
