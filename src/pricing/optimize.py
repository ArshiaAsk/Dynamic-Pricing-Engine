import yaml
import pandas as pd
from pathlib import Path

from src.pricing.engine import PricingEngine


CONFIG_PATH = Path("configs/config.yaml")


def load_config():

    with open(CONFIG_PATH) as f:

        return yaml.safe_load(f)


if __name__ == "__main__":

    config = load_config()

    engine = PricingEngine(config)

    # example product snapshot
    example = {
        "product_id": 1,
        "price": 50,
        "competitor_price": 55,
        "price_ratio": 50 / 55,
        "price_diff_pct": (50 - 55) / 55,
        "dow": 2,
        "is_weekend": 0,
        "week": 24,
        "month": 6,
        "sin_annual": 0.5,
        "cos_annual": 0.866,
        "price_ratio_sin": (50 / 55) * 0.5,
        "price_ratio_cos": (50 / 55) * 0.866,
        "lag_units_sold_1": 40,
        "lag_units_sold_7": 38,
        "lag_units_sold_14": 35,
        "roll_mean_units_7": 39,
        "roll_std_units_7": 2.5,
        "roll_mean_units_14": 40,
        "roll_std_units_14": 3.0,
        "roll_mean_units_28": 42,
        "roll_std_units_28": 3.5,
    }

    df = pd.DataFrame([example])

    result = engine.get_optimal_price(
        df,
        price_min=30,
        price_max=80
    )

    print(result)
