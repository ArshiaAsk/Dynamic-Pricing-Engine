# src/data/generator.py
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
from src.utils.logger import get_logger
from src.utils.paths import RAW_DATA_DIR

logger = get_logger(__name__)

class EcommerceDataGenerator:
    """Generates synthetic e-commerce sales data"""
    def __init__(self, n_products=100, start_date="2023-01-01", days=365):
        self.n_products = n_products
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.days = days
        self.products = self._generate_products()

    def _generate_products(self):
        data = []
        for i in range(self.n_products):
            base_price = np.random.uniform(200_000, 5_000_000)
            elasticity = np.random.uniform(-3, -0.5)
            cost = base_price * np.random.uniform(0.6, 0.85)
            data.append({
                "product_id": i,
                "category": random.choice(["mobile", "laptop", "home", "fashion"]),
                "base_price": base_price,
                "cost": cost,
                "elasticity": elasticity,
            })
        return pd.DataFrame(data)

    def _seasonality(self, day_idx):
        return 1 + 0.2 * np.sin(2 * np.pi * day_idx / 365)

    def generate_sales(self):
        records = []
        for _, product in self.products.iterrows():
            inventory = np.random.randint(50, 300)
            for d in range(self.days):
                date = self.start_date + timedelta(days=d)
                seasonality = self._seasonality(d)
                comp_price = product.base_price * np.random.uniform(0.9, 1.1)
                our_price = comp_price * np.random.uniform(0.95, 1.05)
                marketing_spend = np.random.uniform(0, 5_000_000)
                price_ratio = our_price / product.base_price
                demand = (
                    50 * (price_ratio ** product.elasticity)
                    * seasonality * (1 + np.log1p(marketing_spend) / 10)
                )
                noise = np.random.normal(1, 0.1)
                units_sold = max(0, int(demand * noise))
                units_sold = min(units_sold, inventory)
                inventory -= units_sold
                if inventory < 20:
                    inventory += np.random.randint(100, 300)
                records.append({
                    "date": date,
                    "product_id": product.product_id,
                    "category": product.category,
                    "our_price": our_price,
                    "competitor_price": comp_price,
                    "inventory": inventory,
                    "marketing_spend": marketing_spend,
                    "units_sold": units_sold
                })
        return pd.DataFrame(records)

    def save(self, df):
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        path = RAW_DATA_DIR / "synthetic_sales.csv"
        df.to_csv(path, index=False)
        logger.info(f"✅ Saved raw synthetic data to {path}")


def run():
    gen = EcommerceDataGenerator(n_products=100, days=365)
    df = gen.generate_sales()
    gen.save(df)

if __name__ == "__main__":
    run()
