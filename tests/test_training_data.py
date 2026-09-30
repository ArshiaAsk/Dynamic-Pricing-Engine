"""ROADMAP R12 — honest chronological split + ``product_id`` handling.

Covers the R12 acceptance criteria:

* the train/validation split is chronological — ``max(train.date) <
  min(val.date)`` — and the random shuffled split is gone;
* ``product_id`` is not a model feature (DECISIONS D5) and the target is not
  leaked into the feature list;
* ``reports/training_metrics.json`` reports both ``R2`` and ``MAPE``.

The split assertions run against the regenerated feature parquet and the
committed ``models/features.json``; both are skipped (not errored) when the
gitignored data artifacts are absent, so a plain ``pytest tests/`` stays green
on a clean checkout (CONVENTIONS rule 17).
"""
import json
from pathlib import Path

import pytest

from src.training.dataset import DatasetBuilder

REPO_ROOT = Path(__file__).resolve().parents[1]
FEATURE_PATH = REPO_ROOT / "data" / "features" / "training_features.parquet"
FEATURES_JSON = REPO_ROOT / "models" / "features.json"
METRICS_JSON = REPO_ROOT / "reports" / "training_metrics.json"

TEST_SIZE = 0.2


@pytest.fixture(scope="module")
def features_df():
    if not FEATURE_PATH.exists():
        pytest.skip(f"Feature parquet not found: {FEATURE_PATH}")
    return DatasetBuilder(FEATURE_PATH).load()


def test_split_is_chronological(features_df):
    """R12: every training row precedes every validation row in time."""
    builder = DatasetBuilder(FEATURE_PATH, test_size=TEST_SIZE)
    X, y, _ = builder.build(features_df)
    X_train, X_val, y_train, y_val = builder.split(X, y, features_df["date"])

    assert len(X_train) > 0
    assert len(X_val) > 0

    train_dates = features_df.loc[X_train.index, "date"]
    val_dates = features_df.loc[X_val.index, "date"]

    assert train_dates.max() < val_dates.min()


def test_split_does_not_shuffle():
    """R12: the random shuffled split is gone from the dataset builder."""
    source = (REPO_ROOT / "src" / "training" / "dataset.py").read_text()
    assert "shuffle=True" not in source
    assert "train_test_split" not in source


def test_product_id_is_not_a_model_feature(features_df):
    """R12/D5: product_id is in neither features.json nor the built feature set."""
    with open(FEATURES_JSON) as fh:
        committed = json.load(fh)
    assert "product_id" not in committed

    _, _, feature_cols = DatasetBuilder(FEATURE_PATH).build(features_df)
    assert "product_id" not in feature_cols


def test_no_target_leakage(features_df):
    """R12: the target is absent from the feature list (no same-row leakage).

    The lag/rolling features must be built from *shifted* history; a ``shift(0)``
    (or an unshifted rolling window) would leak the current row's target.
    """
    with open(FEATURES_JSON) as fh:
        committed = set(json.load(fh))
    assert committed.isdisjoint({"y_units_sold", "units_sold"})

    _, _, feature_cols = DatasetBuilder(FEATURE_PATH).build(features_df)
    assert "y_units_sold" not in feature_cols

    source = (REPO_ROOT / "src" / "features" / "feature_builder.py").read_text()
    assert "shift(1)" in source
    assert ".shift(0)" not in source


def test_training_metrics_report_r2_and_mape():
    """R12: the regenerated metrics artifact reports both R2 and MAPE."""
    if not METRICS_JSON.exists():
        pytest.skip(f"Metrics report not found: {METRICS_JSON}")
    with open(METRICS_JSON) as fh:
        metrics = json.load(fh)
    assert "R2" in metrics
    assert "MAPE" in metrics
    assert 0.0 <= metrics["MAPE"] <= 1.0
