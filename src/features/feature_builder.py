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
        self.min_history_days: int = fb_conf.get("min_history_days", 35)  # برای جلوگیری از leakage

    def load_raw(self, filename: str = "ecommerce_sales.csv") -> pd.DataFrame:
       path = RAW_DATA_DIR / filename
       logger.info(f"Loading raw data from {path}")
       df = pd.read_csv(path, parse_dates=["date"])
       # تایپ‌ها
       df["product_id"] = df["product_id"].astype(int)
       df["price"] = df["our_price"].astype(float)
       df["competitor_price"] = df["competitor_price"].astype(float)
       df["units_sold"] = df["units_sold"].astype(float)
       return df

    def _add_calendar_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df["dow"] = df["date"].dt.dayofweek            # 0=Mon
        df["is_weekend"] = (df["dow"] >= 5).astype(int)
        df["week"] = df["date"].dt.isocalendar().week.astype(int)
        df["month"] = df["date"].dt.month
        # seasonality encoding
        dayofyear = df["date"].dt.dayofyear
        df["sin_annual"] = np.sin(2 * np.pi * dayofyear / 365.0)
        df["cos_annual"] = np.cos(2 * np.pi * dayofyear / 365.0)
        return df

    def _add_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        # نسبت‌ها و تفاوت درصدی
        df["price_ratio"] = df["price"] / df["competitor_price"].replace(0, np.nan)
        df["price_ratio"] = df["price_ratio"].replace([np.inf, -np.inf], np.nan).fillna(1.0)
        df["price_diff_pct"] = (df["price"] - df["competitor_price"]) / df["competitor_price"].replace(0, np.nan)
        df["price_diff_pct"] = df["price_diff_pct"].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        return df

    def _add_group_lags_and_rolls(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.sort_values(["product_id", "date"])
        grp = df.groupby("product_id", group_keys=False)

        # Lags
        for lag in self.lag_days:
            df[f"lag_units_sold_{lag}"] = grp["units_sold"].shift(lag)

        # Rolling windows (past only)
        for w in self.rolling_windows:
            # rolling mean with min_periods=w to avoid partial windows (برای حرفه‌ای بودن)
            df[f"roll_mean_units_{w}"] = grp["units_sold"].apply(
                lambda s: s.shift(1).rolling(window=w, min_periods=w).mean()
            )
            df[f"roll_std_units_{w}"] = grp["units_sold"].apply(
                lambda s: s.shift(1).rolling(window=w, min_periods=w).std()
            )

        # حداقل تاریخ معتبر به ازای هر محصول (محصولاتی که تاریخ کافی ندارند حذف می‌شوند)
        df["row_number"] = grp.cumcount() + 1
        return df

    def _filter_min_history(self, df: pd.DataFrame) -> pd.DataFrame:
        # فقط ردیف‌هایی که حداقل به اندازه min_history_days عقب داده دارند
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

        # تعامل ساده با seasonality
        df["price_ratio_sin"] = df["price_ratio"] * df["sin_annual"]
        df["price_ratio_cos"] = df["price_ratio"] * df["cos_annual"]

        # هدف مدل (y)
        df["y_units_sold"] = df["units_sold"]

        # ستون‌های خروجی و مرتب‌سازی
        # مراقب باشیم ستون‌های leakage نداشته باشیم (ورودی‌ها فقط از گذشته و اطلاعات تقویمی)
        feature_cols = [
            "product_id", "date",
            "price", "competitor_price",
            "price_ratio", "price_diff_pct",
            "dow", "is_weekend", "week", "month",
            "sin_annual", "cos_annual",
            "price_ratio_sin", "price_ratio_cos",
        ]

        # افزودن lag/rolling به feature set
        lag_cols = [c for c in df.columns if c.startswith("lag_units_sold_")]
        roll_cols = [c for c in df.columns if c.startswith("roll_mean_units_") or c.startswith("roll_std_units_")]
        feature_cols += lag_cols + roll_cols

        # ستون هدف را آخر اضافه می‌کنیم
        feature_cols += ["y_units_sold"]

        # حذف سطرهای دارای NaN در ویژگی‌های کلیدی (به خاطر min_periods ممکن است NaN داشته باشیم)
        before = len(df)
        df = df.dropna(subset=lag_cols + roll_cols)
        after = len(df)
        logger.info(f"Dropped {before - after} rows due to insufficient history for rolling/lags.")

        return df[feature_cols].sort_values(["product_id", "date"])

    def save_features(self, df: pd.DataFrame, filename: str = "training_features.parquet") -> Path:
        FEATURE_DATA_DIR.mkdir(parents=True, exist_ok=True)
        path = FEATURE_DATA_DIR / filename
        df.to_parquet(path, index=False)
        logger.info(f"Features saved to {path}")
        return path
