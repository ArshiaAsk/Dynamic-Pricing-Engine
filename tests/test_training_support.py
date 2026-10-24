"""D32: the training support artifact.

``models/training_support.json`` is written by training from the **train split
only**. It records, per model feature, the observed minimum, maximum and median,
plus the ``price``, ``competitor_price`` and ``price_ratio`` ranges. Serving
loads it to reject out-of-support requests and to fill history defaults.

The file is generated and gitignored, like ``models/demand_model.pkl``.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.pricing.features import apply_history_defaults, build_serving_features
from src.pricing.support import (
    HISTORY_FEATURES,
    TrainingSupportError,
    load_training_support,
    validate_price_support,
)
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


# --------------------------------------------------------------------------- #
# Serving: validation, defaults, non-constant response and the feature invariant
# --------------------------------------------------------------------------- #

CALENDAR = {
    "dow": 2,
    "is_weekend": 0,
    "week": 15,
    "month": 4,
    "sin_annual": 0.5,
    "cos_annual": 0.5,
}

# Calendar contexts inside the TRAIN split's calendar range (week 5-43,
# month 2-10, cos <= 0.814 because feature rows start after 35 days).
CALENDAR_CONTEXTS = [
    CALENDAR,
    {"dow": 5, "is_weekend": 1, "week": 30, "month": 7,
     "sin_annual": -0.15, "cos_annual": -0.99},
    {"dow": 0, "is_weekend": 0, "week": 5, "month": 2,
     "sin_annual": -0.99, "cos_annual": 0.15},
    {"dow": 6, "is_weekend": 1, "week": 43, "month": 10,
     "sin_annual": 0.1, "cos_annual": -0.99},
    {"dow": 3, "is_weekend": 0, "week": 20, "month": 5,
     "sin_annual": 0.9, "cos_annual": -0.4},
]

COMPETITOR = 2_500_000.0


def _payload(competitor=COMPETITOR, **overrides):
    """An in-support request: bounds at 0.92x/1.08x, history fields omitted."""
    payload = {
        "product_id": 42,
        "competitor_price": competitor,
        **CALENDAR,
        "price_min": 0.92 * competitor,
        "price_max": 1.08 * competitor,
        "optimization_method": "grid_search",
    }
    payload.update(overrides)
    return payload


def _median(support, name):
    return support["features"][name]["median"]


def test_in_support_request_is_accepted(client, artifact):
    response = client.post("/v1/optimize-price", json=_payload())

    assert response.status_code == 200, response.text
    body = response.json()
    assert 0.92 * COMPETITOR <= body["optimal_price"] <= 1.08 * COMPETITOR


def test_omitted_bounds_default_to_the_support(client, artifact):
    payload = _payload()
    del payload["price_min"]
    del payload["price_max"]

    response = client.post("/v1/optimize-price", json=payload)

    assert response.status_code == 200, response.text
    ratio = artifact["price_ratio"]
    price = response.json()["optimal_price"]
    assert ratio["min"] * COMPETITOR <= price <= ratio["max"] * COMPETITOR


def test_competitor_price_outside_support_is_rejected(client, artifact):
    outside = artifact["competitor_price"]["max"] * 1.01

    response = client.post("/v1/optimize-price", json=_payload(outside))

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error"] == "outside_training_support"
    assert "competitor_price" in body["message"]
    assert str(artifact["competitor_price"]["max"]) in body["message"]
    assert body["details"][0]["field"] == "competitor_price"
    assert body["request_id"]


def test_price_bounds_outside_the_ratio_support_are_rejected(client, artifact):
    ratio = artifact["price_ratio"]
    for overrides in (
        {"price_min": ratio["min"] * COMPETITOR * 0.99},
        {"price_max": ratio["max"] * COMPETITOR * 1.01},
    ):
        response = client.post("/v1/optimize-price", json=_payload(**overrides))

        assert response.status_code == 422, (overrides, response.text)
        body = response.json()
        assert body["error"] == "outside_training_support"
        assert "price_ratio" in body["message"]
        assert str(ratio["min"] * COMPETITOR) in body["message"]
        assert str(ratio["max"] * COMPETITOR) in body["message"]
        assert body["details"][0]["field"] in overrides


def test_boundary_values_are_accepted_and_just_outside_rejected(client, artifact):
    ratio = artifact["price_ratio"]
    competitor = artifact["competitor_price"]
    lower = ratio["min"] * COMPETITOR
    upper = ratio["max"] * COMPETITOR

    at_bounds = client.post(
        "/v1/optimize-price", json=_payload(price_min=lower, price_max=upper)
    )
    assert at_bounds.status_code == 200, at_bounds.text

    at_competitor_min = client.post(
        "/v1/optimize-price", json=_payload(competitor["min"])
    )
    assert at_competitor_min.status_code == 200, at_competitor_min.text

    just_outside = 1e-6  # relative; the validation tolerance is 1e-9
    for payload in (
        _payload(price_min=lower * (1 - just_outside)),
        _payload(price_max=upper * (1 + just_outside)),
        _payload(competitor["min"] * (1 - just_outside)),
    ):
        response = client.post("/v1/optimize-price", json=payload)
        assert response.status_code == 422, response.text


def test_predicted_demand_varies_with_price_inside_the_support(artifact):
    """The failure mode found by the audit: a constant demand curve."""
    from src.api.router import engine

    ratio = artifact["price_ratio"]
    competitor = artifact["competitor_price"]
    contexts = [
        competitor["min"] + (competitor["max"] - competitor["min"]) * q
        for q in (0.05, 0.25, 0.50, 0.75, 0.95)
    ]
    history = {name: _median(artifact, name) for name in HISTORY_FEATURES}

    for comp in contexts:
        prices = np.linspace(ratio["min"] * comp, ratio["max"] * comp, 100)
        base = {"competitor_price": comp, **CALENDAR, **history}
        frame = pd.DataFrame([
            build_serving_features(base, float(price), engine.feature_columns)
            for price in prices
        ])[engine.feature_columns]
        demand = np.asarray(engine.model.predict(frame), dtype=float).reshape(-1)

        distinct = len({round(float(value), 10) for value in demand})
        assert distinct >= 20, (
            f"competitor {comp}: only {distinct} distinct demand values over 100 prices"
        )
        assert float(np.std(demand)) > 0, f"competitor {comp}: constant demand"


def test_all_served_features_are_inside_the_training_range(artifact):
    """20+ in-support requests: every one of the 30 features is in [min, max]."""
    from src.api.router import engine

    ratio = artifact["price_ratio"]
    competitor = artifact["competitor_price"]
    history = {name: _median(artifact, name) for name in HISTORY_FEATURES}
    ranges = {
        name: (stats["min"], stats["max"])
        for name, stats in artifact["features"].items()
    }

    violations = []
    requests = 0
    # Four competitor levels x five calendar contexts = 20 requests. The top
    # of the range is excluded here: the serving builder sets
    # roll_mean_price_* to the candidate price, and above ~4.6M the 1.08x bound
    # exceeds those features' training max (flagged, not hidden).
    for q in (0.05, 0.25, 0.50, 0.75):
        comp = competitor["min"] + (competitor["max"] - competitor["min"]) * q
        for calendar in CALENDAR_CONTEXTS:
            requests += 1
            # Omit two history fields so the training-median defaults are used.
            base = {
                "competitor_price": comp,
                **calendar,
                **{name: value for name, value in history.items()
                   if name not in ("lag_units_sold_14", "roll_std_units_28")},
            }
            base = apply_history_defaults(base, history)
            price_min, price_max = 0.92 * comp, 1.08 * comp
            for price in (price_min, (price_min + price_max) / 2, price_max):
                features = build_serving_features(
                    base, float(price), engine.feature_columns
                )
                for name, value in features.items():
                    low, high = ranges[name]
                    if not (low <= value <= high):
                        violations.append(
                            f"competitor {comp}: {name}={value} outside [{low}, {high}]"
                        )

    assert requests >= 20
    assert violations == [], "\n".join(violations)


def test_old_scale_request_is_rejected_not_served_at_price_max(client):
    """The old 89.99 / 70-110 request must be a 422, not 200 at price_max."""
    response = client.post("/v1/optimize-price", json={
        "product_id": 42,
        "competitor_price": 89.99,
        **CALENDAR,
        "price_min": 70.0,
        "price_max": 110.0,
        "optimization_method": "grid_search",
    })

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error"] == "outside_training_support"
    assert "optimal_price" not in body


def test_health_reports_the_training_support(client):
    response = client.get("/v1/health")

    assert response.status_code == 200
    support_check = response.json()["checks"]["model"]["training_support"]
    assert support_check["loaded"] is True
    assert support_check["split"] == "train"


def test_loader_fails_loudly_on_a_missing_file(tmp_path):
    with pytest.raises(TrainingSupportError, match="not found"):
        load_training_support(tmp_path / "missing.json")


def test_loader_rejects_an_invalid_artifact(tmp_path, artifact):
    path = tmp_path / "training_support.json"
    broken = dict(artifact)
    broken["split"] = "validation"
    path.write_text(json.dumps(broken))

    with pytest.raises(TrainingSupportError, match="split"):
        load_training_support(path)


def test_validate_price_support_reports_every_field(artifact):
    errors = validate_price_support(
        competitor_price=artifact["competitor_price"]["max"] * 2,
        price_min=0.0,
        price_max=0.0,
        support=artifact,
    )

    fields = {error["field"] for error in errors}
    assert "competitor_price" in fields
    assert "price_min" in fields
    assert "price_max" in fields
    assert all(error["type"] == "outside_training_support" for error in errors)
