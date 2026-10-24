"""D32: the training support artifact.

``models/training_support.json`` is written by training from the **train split
only**. It records, per model feature, the observed minimum, maximum and median,
plus the ``price``, ``competitor_price`` and ``price_ratio`` ranges. Serving
loads it to reject out-of-support requests and to fill history defaults.

The file is generated and gitignored, like ``models/demand_model.pkl``.
"""
import json
from pathlib import Path

import pandas as pd
import pytest

from src.training.dataset import DatasetBuilder
from src.training.support import compute_training_support

REPO_ROOT = Path(__file__).resolve().parents[1]
SUPPORT_PATH = REPO_ROOT / "models" / "training_support.json"
FEATURES_PATH = REPO_ROOT / "models" / "features.json"
PARQUET = REPO_ROOT / "data" / "features" / "training_features.parquet"


def test_compute_training_support_min_max_median():
    """The pure function reports exact min/max/median per feature."""
    frame = pd.DataFrame({
        "price": [10.0, 20.0, 30.0, 40.0],
        "competitor_price": [12.0, 18.0, 33.0, 36.0],
        "price_ratio": [10.0 / 12.0, 20.0 / 18.0, 30.0 / 33.0, 40.0 / 36.0],
    })

    support = compute_training_support(frame, list(frame.columns))

    assert support["split"] == "train"
    assert support["n_rows"] == 4
    assert support["features"]["price"] == {
        "min": 10.0, "max": 40.0, "median": 25.0,
    }
    assert support["features"]["competitor_price"] == {
        "min": 12.0, "max": 36.0, "median": 25.5,
    }
    for name in ("price", "competitor_price", "price_ratio"):
        assert support[name] == support["features"][name]


def test_compute_training_support_uses_only_the_rows_it_is_given():
    """A single row is its own min, median and max (no hidden full-data read)."""
    frame = pd.DataFrame({"price": [7.0], "competitor_price": [9.0],
                          "price_ratio": [7.0 / 9.0]})

    support = compute_training_support(frame, list(frame.columns))

    assert support["n_rows"] == 1
    assert support["features"]["price"]["min"] == support["features"]["price"]["max"]


@pytest.fixture(scope="module")
def artifact():
    if not SUPPORT_PATH.exists():
        pytest.skip(f"Generated support artifact not found: {SUPPORT_PATH}")
    return json.loads(SUPPORT_PATH.read_text())


def test_artifact_covers_every_committed_feature(artifact):
    columns = json.loads(FEATURES_PATH.read_text())
    missing = [column for column in columns if column not in artifact["features"]]
    assert missing == [], f"training_support.json misses features: {missing}"
    assert artifact["split"] == "train"


def test_artifact_min_median_max_are_ordered(artifact):
    bad = [
        name for name, stats in artifact["features"].items()
        if not (stats["min"] <= stats["median"] <= stats["max"])
    ]
    assert bad == [], f"features with min > median > max violations: {bad}"


def test_artifact_price_ratio_range_matches_the_train_split(artifact):
    """The support is computed from the TRAIN split only (chronological 80/20)."""
    if not PARQUET.exists():
        pytest.skip(f"Generated training features not found: {PARQUET}")

    dataset = DatasetBuilder(PARQUET, test_size=0.2)
    frame = dataset.load()
    X, y, _ = dataset.build(frame)
    X_train, _, _, _ = dataset.split(X, y, frame["date"])

    assert artifact["n_rows"] == len(X_train)
    assert artifact["price_ratio"]["min"] == pytest.approx(float(X_train["price_ratio"].min()))
    assert artifact["price_ratio"]["max"] == pytest.approx(float(X_train["price_ratio"].max()))
    assert artifact["competitor_price"]["min"] == pytest.approx(
        float(X_train["competitor_price"].min())
    )
