import pandas as pd
from scipy.stats import ks_2samp
from src.utils.paths import RAW_DATA_DIR


def test_price_distribution():

    path = RAW_DATA_DIR / "ecommerce_sales.csv"
    df = pd.read_csv(path)

    recent = df.tail(500)
    historical = df.iloc[:-500]

    stat, pvalue = ks_2samp(
        historical["our_price"],
        recent["our_price"]
    )

    assert pvalue < 0.01