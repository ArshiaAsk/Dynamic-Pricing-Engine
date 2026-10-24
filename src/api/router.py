from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from src.api.schemas import PricingRequest, PricingResponse
from src.pricing.engine import PricingEngine
from src.pricing.features import apply_history_defaults
from src.pricing.support import default_price_bounds, validate_price_support
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
        
        # Price range: the request's bounds, or the observed price_ratio support
        # around the request's competitor price (D32). No absolute default.
        default_min, default_max = default_price_bounds(
            payload.competitor_price, engine.training_support
        )
        price_min = payload.price_min if payload.price_min is not None else default_min
        price_max = payload.price_max if payload.price_max is not None else default_max

        # Reject a request outside the model's training support (D32). The body
        # keeps the validation shape: error code, message with the supported
        # ranges, field-level details and the request id.
        support_errors = validate_price_support(
            payload.competitor_price, price_min, price_max, engine.training_support
        )
        if support_errors:
            logger.warning(
                f"Request outside the training support (request_id: {request_id}): "
                f"{[error['message'] for error in support_errors]}"
            )
            return JSONResponse(
                status_code=422,
                content={
                    "error": "outside_training_support",
                    "message": (
                        "Request is outside the model's training support: "
                        + " ".join(error["message"] for error in support_errors)
                    ),
                    "details": support_errors,
                    "request_id": request_id,
                },
            )

        # Omitted history features are filled with the training medians (D32).
        features_dict = apply_history_defaults(features_dict, engine.history_defaults)
        
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
                   f"{result['optimal_price']:.2f} (request_id: {request_id})")
        
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
        training_support=engine.training_support,
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
