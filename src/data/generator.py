# src/data/generator.py
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
from src.utils.logger import get_logger
from src.utils.paths import RAW_DATA_DIR

logger = get_logger(__name__)

class EcommerceDataGenerator:
    """Generates synthetic e-commerce sales data with stronger price signals"""
    def __init__(self, n_products=100, start_date="2023-01-01", days=365):
        self.n_products = n_products
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.days = days
        self.products = self._generate_products()

    def _generate_products(self):
        data = []
        for i in range(self.n_products):
            base_price = np.random.uniform(200_000, 5_000_000)
            # Stronger elasticity for better price signal
            elasticity = np.random.uniform(-2.5, -0.8)
            cost = base_price * np.random.uniform(0.6, 0.85)
            # Add base demand level
            base_demand = np.random.uniform(30, 100)
            data.append({
                "product_id": i,
                "category": random.choice(["mobile", "laptop", "home", "fashion"]),
                "base_price": base_price,
                "cost": cost,
                "elasticity": elasticity,
                "base_demand": base_demand,
            })
        return pd.DataFrame(data)

    def _seasonality(self, day_idx):
        # Stronger seasonality
        return 1 + 0.3 * np.sin(2 * np.pi * day_idx / 365)

    def generate_sales(self):
        records = []
        for _, product in self.products.iterrows():
            inventory = np.random.randint(50, 300)
            for d in range(self.days):
                date = self.start_date + timedelta(days=d)
                seasonality = self._seasonality(d)
                
                # Competitor price with some variation
                comp_price = product.base_price * np.random.uniform(0.92, 1.08)
                
                # Our price - sometimes competitive, sometimes not
                price_strategy = np.random.choice(['competitive', 'premium', 'discount'], p=[0.5, 0.25, 0.25])
                if price_strategy == 'competitive':
                    our_price = comp_price * np.random.uniform(0.98, 1.02)
                elif price_strategy == 'premium':
                    our_price = comp_price * np.random.uniform(1.05, 1.15)
                else:  # discount
                    our_price = comp_price * np.random.uniform(0.85, 0.95)
                
                # Marketing spend
                marketing_spend = np.random.uniform(0, 5_000_000)
                
                # Demand calculation with stronger price effect
                price_ratio = our_price / product.base_price
                
                # Base demand affected by:
                # 1. Price elasticity (stronger effect)
                # 2. Seasonality
                # 3. Marketing
                # 4. Competitor price difference
                comp_advantage = (comp_price - our_price) / comp_price
                
                demand = (
                    product.base_demand 
                    * (price_ratio ** product.elasticity)  # Price effect
                    * seasonality  # Seasonal effect
                    * (1 + np.log1p(marketing_spend) / 15)  # Marketing effect
                    * (1 + comp_advantage * 2)  # Competitor price effect (stronger)
                )
                
                # Add less noise for clearer signal
                noise = np.random.normal(1, 0.08)  # Reduced from 0.1
                units_sold = max(0, int(demand * noise))
                units_sold = min(units_sold, inventory)
                
                # Restock
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
        path = RAW_DATA_DIR / "ecommerce_sales.csv"
        df.to_csv(path, index=False)
        logger.info(f"✅ Saved raw synthetic data to {path}")


def run(days=5, append=True):
    gen = EcommerceDataGenerator(n_products=100, days=days)

    new_df = gen.generate_sales()

    path = RAW_DATA_DIR / "ecommerce_sales.csv"
    
    if append and path.exists():
        old_df = pd.read_csv(path)
        df = pd.concat([old_df, new_df], ignore_index=True)
    else:
        df = new_df

    gen.save(df)

if __name__ == "__main__":
    run()
