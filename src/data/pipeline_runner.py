# src/data/pipeline_runner.py
from src.data.generator import EcommerceDataGenerator
from src.data.validation import validate_data 
from src.data.ingest import load_to_postgres
from src.utils.paths import RAW_DATA_DIR

def main():
    # مرحله ۱: ساخت داده
    gen = EcommerceDataGenerator(n_products=50, days=365)
    df = gen.generate_sales()
    df.to_csv(RAW_DATA_DIR / "ecommerce_sales.csv", index=False)

    # مرحله ۲: اعتبارسنجی
    assert validate_data(df), "Data validation failed!"

    # مرحله ۳: بارگذاری
    load_to_postgres(str(RAW_DATA_DIR / "ecommerce_sales.csv"))
    print("✅ Data pipeline executed successfully.")

if __name__ == "__main__":
    main()
