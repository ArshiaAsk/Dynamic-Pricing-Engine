import pandas as pd
from sklearn.model_selection import train_test_split
from pathlib import Path


class DatasetBuilder:

    def __init__(self, feature_path):

        self.feature_path = Path(feature_path)

    def load(self):

        df = pd.read_parquet(self.feature_path)

        df["date"] = pd.to_datetime(df["date"])

        return df

    def build(self, df):

        target = "y_units_sold"

        feature_cols = [
            c for c in df.columns
            if c not in ["y_units_sold", "date"]
        ]

        X = df[feature_cols]
        y = df[target]

        return X, y, feature_cols

    def split(self, X, y):

        X_train, X_val, y_train, y_val = train_test_split(
            X,
            y,
            test_size=0.2,
            random_state=42,
            shuffle=True
        )

        return X_train, X_val, y_train, y_val
