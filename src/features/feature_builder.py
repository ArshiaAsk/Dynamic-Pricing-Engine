# src/features/feature_builder.py
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Optional, Dict
from src.utils.logger import get_logger
from src.utils.paths import RAW_DATA_DIR, FEATURE_DATA_DIR

logger = get_logger(__name__)

class FeatureBuilder:
    def __init__(self, config: Dict):
        self.config = config
        fb_conf = config.get("features", {})
        self.lag_days: List[int] = fb_conf.get("lag_days", [1, 7, 14])
        self.rolling_windows: List[int] = fb_conf.get("rolling_windows", [7, 14, 28])
        self.min_history_days: int = fb_conf.get("min_history_days", 35)

    def load_raw(self, filename: str = "ecommerce_sales.csv") -> pd.DataFrame:
       path = RAW_DATA_DIR / filename
       logger.info(f"Loading raw data from {path}")
       df = pd.read_csv(path, parse_dates=["date"])
       df["product_id"] = df["product_id"].astype(int)
       df["price"] = df["our_price"].astype(float)
       df["competitor_price"] = df["competitor_price"].astype(float)
       df["units_sold"] = df["units_sold"].astype(float)
       return df

    def _add_calendar_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df["dow"] = df["date"].dt.dayofweek
        df["is_weekend"] = (df["dow"] >= 5).astype(int)
        df["week"] = df["date"].dt.isocalendar().week.astype(int)
        df["month"] = df["date"].dt.month
        # Seasonality encoding
        dayofyear = df["date"].dt.dayofyear
        df["sin_annual"] = np.sin(2 * np.pi * dayofyear / 365.0)
        df["cos_annual"] = np.cos(2 * np.pi * dayofyear / 365.0)
        return df

    def _add_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        # Price ratios and differences
        df["price_ratio"] = df["price"] / df["competitor_price"].replace(0, np.nan)
        df["price_ratio"] = df["price_ratio"].replace([np.inf, -np.inf], np.nan).fillna(1.0)
        df["price_diff_pct"] = (df["price"] - df["competitor_price"]) / df["competitor_price"].replace(0, np.nan)
        df["price_diff_pct"] = df["price_diff_pct"].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        
        # Additional price features for better signal
        df["price_advantage"] = (df["competitor_price"] - df["price"]) / df["competitor_price"]
        df["price_advantage"] = df["price_advantage"].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        
        # Log price (helps with non-linear relationships)
        df["log_price"] = np.log1p(df["price"])
        df["log_comp_price"] = np.log1p(df["competitor_price"])
        
        return df

    def _add_group_lags_and_rolls(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.sort_values(["product_id", "date"])
        grp = df.groupby("product_id", group_keys=False)

        # Lags
        for lag in self.lag_days:
            df[f"lag_units_sold_{lag}"] = grp["units_sold"].shift(lag)
            # Also lag price for price change features
            df[f"lag_price_{lag}"] = grp["price"].shift(lag)

        # Price change features
        df["price_change_1d"] = (df["price"] - df["lag_price_1"]) / df["lag_price_1"]
        df["price_change_7d"] = (df["price"] - df["lag_price_7"]) / df["lag_price_7"]
        
        # Rolling windows
        for w in self.rolling_windows:
            df[f"roll_mean_units_{w}"] = grp["units_sold"].apply(
                lambda s: s.shift(1).rolling(window=w, min_periods=w).mean()
            )
            df[f"roll_std_units_{w}"] = grp["units_sold"].apply(
                lambda s: s.shift(1).rolling(window=w, min_periods=w).std()
            )
            # Rolling price features
            df[f"roll_mean_price_{w}"] = grp["price"].apply(
                lambda s: s.shift(1).rolling(window=w, min_periods=w).mean()
            )

        df["row_number"] = grp.cumcount() + 1
        return df

    def _filter_min_history(self, df: pd.DataFrame) -> pd.DataFrame:
        valid = df[df["row_number"] > self.min_history_days]
        drop_cols = ["row_number"]
        return valid.drop(columns=drop_cols)

    def build_features(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Building features...")
        df = raw_df.copy()
        df = self._add_calendar_features(df)
        df = self._add_price_features(df)
        df = self._add_group_lags_and_rolls(df)
        df = self._filter_min_history(df)

        # Interaction features with seasonality
        df["price_ratio_sin"] = df["price_ratio"] * df["sin_annual"]
        df["price_ratio_cos"] = df["price_ratio"] * df["cos_annual"]
        df["price_advantage_sin"] = df["price_advantage"] * df["sin_annual"]
        
        # Target
        df["y_units_sold"] = df["units_sold"]

        # Feature columns
        feature_cols = [
            "product_id", "date",
            "price", "competitor_price",
            "price_ratio", "price_diff_pct", "price_advantage",
            "log_price", "log_comp_price",
            "dow", "is_weekend", "week", "month",
            "sin_annual", "cos_annual",
            "price_ratio_sin", "price_ratio_cos", "price_advantage_sin",
            "price_change_1d", "price_change_7d",
        ]

        # Add lag/rolling features
        lag_cols = [c for c in df.columns if c.startswith("lag_units_sold_")]
        roll_cols = [c for c in df.columns if c.startswith("roll_mean_units_") or c.startswith("roll_std_units_")]
        price_roll_cols = [c for c in df.columns if c.startswith("roll_mean_price_")]
        
        feature_cols += lag_cols + roll_cols + price_roll_cols
        feature_cols += ["y_units_sold"]

        # Drop NaN rows
        before = len(df)
        df = df.dropna(subset=lag_cols + roll_cols + price_roll_cols + ["price_change_1d", "price_change_7d"])
        after = len(df)
        logger.info(f"Dropped {before - after} rows due to insufficient history.")

        return df[feature_cols].sort_values(["product_id", "date"])

    def save_features(self, df: pd.DataFrame, filename: str = "training_features.parquet") -> Path:
        FEATURE_DATA_DIR.mkdir(parents=True, exist_ok=True)
        path = FEATURE_DATA_DIR / filename
        df.to_parquet(path, index=False)
        logger.info(f"Features saved to {path}")
        return path
