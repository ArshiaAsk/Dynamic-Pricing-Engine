from fastapi import APIRouter, HTTPException
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
DEBUG_LOG_PATH = Path("/home/arshiaask/projects/Dynamic-Pricing-Engine/.cursor/debug-3d1d61.log")

router = APIRouter()

CONFIG_PATH = Path("configs/config.yaml")

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
            input_data=payload.dict(),
            metadata={'product_id': payload.product_id}
        )
        
        # Record error
        health_checker.record_error()
        
        logger.error(f"Pricing optimization failed (request_id: {request_id}): {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
def health_check():
    """Comprehensive health check endpoint"""
    health = health_checker.check_health(model=engine.model)
    # region agent log
    with DEBUG_LOG_PATH.open("a", encoding="utf-8") as _f:
        _f.write(json.dumps({
            "sessionId": "3d1d61",
            "runId": "pre-fix",
            "hypothesisId": "H4",
            "location": "src/api/router.py:121",
            "message": "health endpoint computed status",
            "data": {
                "status": health.get("status"),
                "model_check": health.get("checks", {}).get("model"),
                "error_rate": health.get("metrics", {}).get("error_rate")
            },
            "timestamp": int(time.time() * 1000)
        }) + "\n")
    # endregion
    
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
