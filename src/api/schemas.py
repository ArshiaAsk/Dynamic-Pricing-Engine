from pydantic import BaseModel, Field, validator
from typing import Optional


class PricingRequest(BaseModel):
    """Enhanced pricing request with validation"""
    
    # Product info
    product_id: int = Field(..., ge=0, description="Product ID")
    
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
    optimization_method: Optional[str] = Field("bayesian", description="Optimization method")
    
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
    
    class Config:
        schema_extra = {
            "example": {
                "product_id": 42,
                "competitor_price": 89.99,
                "dow": 2,
                "is_weekend": 0,
                "week": 15,
                "month": 4,
                "sin_annual": 0.5,
                "cos_annual": 0.866,
                "lag_units_sold_1": 45.0,
                "lag_units_sold_7": 42.0,
                "lag_units_sold_14": 40.0,
                "roll_mean_units_7": 43.5,
                "roll_mean_units_14": 41.2,
                "roll_mean_units_28": 39.8,
                "roll_std_units_7": 5.2,
                "roll_std_units_14": 6.1,
                "roll_std_units_28": 7.3,
                "price_min": 70.0,
                "price_max": 110.0,
                "cost": 60.0,
                "min_margin_pct": 0.15,
                "inventory_limit": 100
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
    
    # Optimization metadata
    optimization_success: Optional[bool] = Field(None, description="Optimization succeeded")
    optimization_iterations: Optional[int] = Field(None, description="Number of iterations")
    
    class Config:
        schema_extra = {
            "example": {
                "optimal_price": 87.50,
                "expected_demand": 48.3,
                "expected_revenue": 4226.25,
                "optimization_method": "bayesian",
                "profit_margin": 0.314,
                "profit_per_unit": 27.50,
                "total_profit": 1328.25,
                "optimization_success": True,
                "optimization_iterations": 12
            }
        }
