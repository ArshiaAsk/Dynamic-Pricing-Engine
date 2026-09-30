import pandas as pd
from pathlib import Path


class DatasetBuilder:

    def __init__(self, feature_path, test_size=0.2):

        self.feature_path = Path(feature_path)
        self.test_size = test_size

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

    def split(self, X, y, dates):
        """Chronological train/validation split (DECISIONS D6 / ROADMAP R12).

        The earliest ``1 - test_size`` fraction of the timeline is the training
        set and the most recent ``test_size`` fraction is the validation set.
        Rows are ordered by ``dates`` (stable, so ties keep their input order);
        nothing is shuffled, so the reported metrics measure forward-looking
        generalization instead of interpolation between neighbouring days.
        """
        dates = pd.to_datetime(dates)
        order = dates.sort_values(kind="mergesort").index

        X = X.loc[order]
        y = y.loc[order]
        ordered_dates = dates.loc[order]

        split_idx = int(len(X) * (1 - self.test_size))

        # Keep whole calendar days together: if the cut lands mid-day (several
        # products share a date), push it forward to that day's end so no date
        # appears in both the training and validation sets.
        if 0 < split_idx < len(X):
            boundary_date = ordered_dates.iloc[split_idx - 1]
            split_idx = int((ordered_dates <= boundary_date).sum())

        X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]

        return X_train, X_val, y_train, y_val
