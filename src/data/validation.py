# src/data/validation.py
import pandas as pd
from src.utils.logger import get_logger

logger = get_logger(__name__)

def validate_data(df: pd.DataFrame) -> bool:
    expected_cols = [
        "date", "product_id", "category",
        "our_price", "competitor_price",
        "inventory", "marketing_spend", "units_sold"
    ]
    if not all(col in df.columns for col in expected_cols):
        logger.error("❌ Missing columns in dataset")
        return False

    if df.isnull().any().any():
        logger.warning(f"⚠️ Missing values found: {df.isnull().sum().sum()}")
        return False

    if (df["our_price"] <= 0).any() or (df["units_sold"] < 0).any():
        logger.error("❌ Invalid price or units detected")
        return False

    logger.info("✅ Data validation passed")
    return True
