# src/data/ingest.py
import pandas as pd
from sqlalchemy import create_engine
from src.utils.logger import get_logger
from src.utils.paths import RAW_DATA_DIR

logger = get_logger(__name__)

def load_to_postgres(csv_path: str, db_url: str = "sqlite:///data.db"):
    df = pd.read_csv(csv_path)
    engine = create_engine(db_url)
    df.to_sql("sales_data", con=engine, if_exists="replace", index=False)
    logger.info(f"✅ Loaded data to database: {db_url}")

if __name__ == "__main__":
    path = RAW_DATA_DIR / "synthetic_sales.csv"
    load_to_postgres(str(path))
