"""Feature transformer for production inference"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FeatureTransformer:
    """
    Transform raw input data into model-ready features
    Handles feature engineering for real-time predictions
    """
    
    def __init__(self, feature_columns: List[str]):
        self.feature_columns = feature_columns
        self.required_inputs = [
            'product_id', 'competitor_price', 'date',
            'lag_units_sold_1', 'lag_units_sold_7', 'lag_units_sold_14',
            'roll_mean_units_7', 'roll_mean_units_14', 'roll_mean_units_28',
            'roll_std_units_7', 'roll_std_units_14', 'roll_std_units_28'
        ]
    
    def transform(self, input_data: Dict, price: float) -> pd.DataFrame:
        """
        Transform input data and price into model features
        
        Args:
            input_data: Dictionary with base features
            price: Price to evaluate
            
        Returns:
            DataFrame with model-ready features
        """
        features = input_data.copy()
        features['price'] = price
        
        # Add calendar features if date provided
        if 'date' in features:
            date = features['date']
            if isinstance(date, str):
                date = pd.to_datetime(date)
            
            features['dow'] = date.dayofweek
            features['is_weekend'] = 1 if date.dayofweek >= 5 else 0
            features['week'] = date.isocalendar()[1]
            features['month'] = date.month
            
            dayofyear = date.timetuple().tm_yday
            features['sin_annual'] = np.sin(2 * np.pi * dayofyear / 365.0)
            features['cos_annual'] = np.cos(2 * np.pi * dayofyear / 365.0)
        
        # Price features
        comp_price = features.get('competitor_price', price)
        features['price_ratio'] = price / comp_price if comp_price > 0 else 1.0
        features['price_diff_pct'] = (price - comp_price) / comp_price if comp_price > 0 else 0.0
        features['price_advantage'] = (comp_price - price) / comp_price if comp_price > 0 else 0.0
        
        # Log prices
        features['log_price'] = np.log1p(price)
        features['log_comp_price'] = np.log1p(comp_price)
        
        # Interaction features
        if 'sin_annual' in features:
            features['price_ratio_sin'] = features['price_ratio'] * features['sin_annual']
            features['price_ratio_cos'] = features['price_ratio'] * features['cos_annual']
            features['price_advantage_sin'] = features['price_advantage'] * features['sin_annual']
        
        # Price change features (if historical prices available)
        if 'lag_price_1' in features:
            features['price_change_1d'] = (price - features['lag_price_1']) / features['lag_price_1']
        else:
            features['price_change_1d'] = 0.0
            
        if 'lag_price_7' in features:
            features['price_change_7d'] = (price - features['lag_price_7']) / features['lag_price_7']
        else:
            features['price_change_7d'] = 0.0
        
        # Rolling price features (if available)
        for w in [7, 14, 28]:
            if f'roll_mean_price_{w}' not in features:
                features[f'roll_mean_price_{w}'] = price
        
        # Convert to DataFrame and select required columns
        df = pd.DataFrame([features])
        
        # Fill missing columns with defaults
        for col in self.feature_columns:
            if col not in df.columns:
                df[col] = 0.0
        
        return df[self.feature_columns]
    
    def validate_input(self, input_data: Dict) -> tuple[bool, Optional[str]]:
        """
        Validate input data has required fields
        
        Returns:
            (is_valid, error_message)
        """
        missing = []
        for field in self.required_inputs:
            if field not in input_data:
                missing.append(field)
        
        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"
        
        return True, None
    
    def get_required_inputs(self) -> List[str]:
        """Get list of required input fields"""
        return self.required_inputs.copy()
