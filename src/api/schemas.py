from pydantic import BaseModel, Field, validator
from typing import Literal, Optional


class PricingRequest(BaseModel):
    """Enhanced pricing request with validation"""
    
    # Product info
    product_id: int = Field(
        ...,
        ge=0,
        description=(
            "Product ID, accepted for request compatibility and logging only. "
            "It is NOT a model feature and does not influence the predicted "
            "demand or price."
        ),
    )
    
    # Price features
    competitor_price: float = Field(..., gt=0, description="Competitor price")
    
    # Calendar features
    dow: int = Field(..., ge=0, le=6, description="Day of week (0=Monday)")
    is_weekend: int = Field(..., ge=0, le=1, description="Is weekend (0 or 1)")
    week: int = Field(..., ge=1, le=53, description="Week of year")
    month: int = Field(..., ge=1, le=12, description="Month")
    sin_annual: float = Field(..., ge=-1, le=1, description="Annual seasonality (sin)")
    cos_annual: float = Field(..., ge=-1, le=1, description="Annual seasonality (cos)")
    
    # Historical features (lags and rolling)
    lag_units_sold_1: Optional[float] = Field(None, ge=0)
    lag_units_sold_7: Optional[float] = Field(None, ge=0)
    lag_units_sold_14: Optional[float] = Field(None, ge=0)
    roll_mean_units_7: Optional[float] = Field(None, ge=0)
    roll_mean_units_14: Optional[float] = Field(None, ge=0)
    roll_mean_units_28: Optional[float] = Field(None, ge=0)
    roll_std_units_7: Optional[float] = Field(None, ge=0)
    roll_std_units_14: Optional[float] = Field(None, ge=0)
    roll_std_units_28: Optional[float] = Field(None, ge=0)
    
    # Optimization parameters
    price_min: Optional[float] = Field(None, gt=0, description="Minimum price")
    price_max: Optional[float] = Field(None, gt=0, description="Maximum price")
    optimization_method: Literal["grid_search", "grid"] = Field(
        "grid_search",
        description=(
            "Optimization method: 'grid_search' (canonical) or its alias 'grid'. "
            "Any other value (including the legacy 'bayesian') is rejected with 422."
        ),
    )
    
    # Business constraints
    cost: Optional[float] = Field(None, ge=0, description="Product cost")
    min_margin_pct: Optional[float] = Field(0.1, ge=0, le=1, description="Min profit margin")
    inventory_limit: Optional[int] = Field(None, ge=0, description="Max inventory")
    
    @validator('price_max')
    def price_max_greater_than_min(cls, v, values):
        if 'price_min' in values and values['price_min'] is not None and v is not None:
            if v <= values['price_min']:
                raise ValueError('price_max must be greater than price_min')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "product_id": 42,
                "competitor_price": 2500000.0,
                "dow": 2,
                "is_weekend": 0,
                "week": 15,
                "month": 4,
                "sin_annual": 0.5,
                "cos_annual": 0.866,
                "lag_units_sold_1": 92.0,
                "lag_units_sold_7": 92.0,
                "lag_units_sold_14": 93.0,
                "roll_mean_units_7": 96.4,
                "roll_mean_units_14": 96.9,
                "roll_mean_units_28": 96.9,
                "roll_std_units_7": 37.4,
                "roll_std_units_14": 38.5,
                "roll_std_units_28": 39.2,
                "price_min": 2300000.0,
                "price_max": 2700000.0,
                "cost": 2250000.0,
                "min_margin_pct": 0.15,
                "inventory_limit": 100
            }
        }
    }

class PricingResponse(BaseModel):
    """Enhanced pricing response"""
    
    optimal_price: float = Field(..., description="Optimal price")
    expected_demand: float = Field(..., description="Expected demand at optimal price")
    expected_revenue: float = Field(..., description="Expected revenue")
    optimization_method: Optional[str] = Field(None, description="Method used")
    
    # Optional fields for constrained optimization
    profit_margin: Optional[float] = Field(None, description="Profit margin")
    profit_per_unit: Optional[float] = Field(None, description="Profit per unit")
    total_profit: Optional[float] = Field(None, description="Total expected profit")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "optimal_price": 2625159.38,
                "expected_demand": 86.31,
                "expected_revenue": 226564781.23,
                "optimization_method": "grid_search",
                "profit_margin": 0.1429,
                "profit_per_unit": 375159.38,
                "total_profit": 32378187.22
            }
        }
    }
