"""Training-support artifact (DECISIONS D32).

Training writes ``models/training_support.json`` next to the pickle. It records
the observed minimum, maximum and median of every model feature, computed from
the **train split only**, plus the ``price``, ``competitor_price`` and
``price_ratio`` ranges. Serving loads it to reject out-of-support requests and
to fill the history-feature defaults with training medians.

The file is generated and gitignored, like ``models/demand_model.pkl``.
"""
from typing import Dict, Iterable

import pandas as pd

SUPPORT_FILENAME = "training_support.json"

# The three ranges serving needs by name, in addition to the per-feature map.
RANGE_FEATURES = ("price", "competitor_price", "price_ratio")


def compute_training_support(
    X_train: pd.DataFrame, feature_columns: Iterable[str]
) -> Dict:
    """Return the support dictionary for ``feature_columns`` from the train split.

    Args:
        X_train: The chronological training split (never the validation split).
        feature_columns: The model feature columns, in training order.
    """
    features = {}
    for column in feature_columns:
        series = X_train[column]
        features[column] = {
            "min": float(series.min()),
            "max": float(series.max()),
            "median": float(series.median()),
        }

    support = {
        "n_rows": int(len(X_train)),
        "split": "train",
        "features": features,
    }
    for name in RANGE_FEATURES:
        support[name] = dict(features[name])
    return support
