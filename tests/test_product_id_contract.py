"""Contract tests for ``PricingRequest.product_id`` (ROADMAP R34).

``product_id`` is accepted for request compatibility and logging only; it is
**not** a model feature and must not influence the predicted demand or price.
"""
import json
from pathlib import Path

from src.api.schemas import PricingRequest

REPO_ROOT = Path(__file__).resolve().parents[1]
FEATURES_JSON = REPO_ROOT / "models" / "features.json"


def test_product_id_description_states_not_a_model_feature():
    """The schema must state plainly that product_id is not a model feature."""
    description = PricingRequest.model_fields["product_id"].description or ""
    lowered = description.lower()
    assert "not a model feature" in lowered, (
        f"product_id description must state it is not a model feature; "
        f"got {description!r}"
    )
    assert "compat" in lowered, (
        f"product_id description must mention request compatibility; "
        f"got {description!r}"
    )


def test_product_id_absent_from_committed_feature_contract():
    """product_id is not in the tracked model feature contract."""
    columns = json.loads(FEATURES_JSON.read_text())
    assert "product_id" not in columns, (
        f"product_id must not be a model feature; features.json has {len(columns)} cols"
    )


def test_product_id_absent_from_served_feature_columns():
    """product_id is not in the feature columns the running engine serves.

    The served list is ``PricingEngine.feature_columns``
    (``src/pricing/engine.py:31`` declared, ``:138`` loaded from
    ``models/features.json``, ``:175`` passed to ``PriceOptimizer``).
    """
    from src.api.router import engine

    assert "product_id" not in engine.feature_columns, (
        f"product_id must not be served as a model feature; engine serves "
        f"{len(engine.feature_columns)} columns"
    )


def test_product_id_does_not_change_prediction(client):
    """Behavioural invariance (characterization): product_id is ignored.

    The same valid optimize payload is posted twice with only ``product_id``
    differing (1 vs 999); the predicted demand/price fields must be identical.
    """
    base = {
        "competitor_price": 89.99,
        "dow": 2,
        "is_weekend": 0,
        "week": 15,
        "month": 4,
        "sin_annual": 0.5,
        "cos_annual": 0.866,
        "lag_units_sold_1": 45.0,
        "lag_units_sold_7": 42.0,
        "lag_units_sold_14": 40.0,
        "roll_mean_units_7": 43.5,
        "roll_mean_units_14": 41.2,
        "roll_mean_units_28": 39.8,
        "roll_std_units_7": 5.2,
        "roll_std_units_14": 6.1,
        "roll_std_units_28": 7.3,
        "price_min": 70.0,
        "price_max": 110.0,
    }

    resp_a = client.post("/v1/optimize-price", json=dict(base, product_id=1))
    resp_b = client.post("/v1/optimize-price", json=dict(base, product_id=999))
    assert resp_a.status_code == 200, resp_a.text
    assert resp_b.status_code == 200, resp_b.text

    data_a, data_b = resp_a.json(), resp_b.json()
    for field in ("optimal_price", "expected_demand", "expected_revenue"):
        assert data_a[field] == data_b[field], (
            f"{field} changed with product_id: {data_a[field]} != {data_b[field]}"
        )
