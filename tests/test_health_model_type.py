"""R13 — the health check must validate the *actually-served* model type.

The old probe guessed the model width with
``getattr(model, "n_features_in_", 10)`` and fed a numpy array of that width.
A native ``XGBRegressor`` exposes ``n_features_in_`` (31) and passed, but an
``mlflow.pyfunc`` wrapper does not, so it fell back to 10 columns and raised
``ValueError: Feature shape mismatch, expected: 31, got 10`` → the endpoint
reported ``degraded`` and ``/v1/health`` returned 503.

These tests assert ``/v1/health`` returns 200 with ``checks.model.status == "ok"``
for both model types, driven through the real FastAPI route.
"""
import json
from pathlib import Path

import joblib
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = REPO_ROOT / "models" / "demand_model.pkl"
FEATURES_PATH = REPO_ROOT / "models" / "features.json"


@pytest.fixture(scope="module")
def real_model():
    if not MODEL_PATH.exists():
        pytest.skip(f"Committed model not found: {MODEL_PATH}")
    return joblib.load(MODEL_PATH)


@pytest.fixture(scope="module")
def real_feature_columns():
    if not FEATURES_PATH.exists():
        pytest.skip(f"Committed feature list not found: {FEATURES_PATH}")
    with open(FEATURES_PATH) as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def pyfunc_model(real_model):
    """An mlflow.pyfunc-wrapped copy of the committed model (no registry needed)."""
    mlflow = pytest.importorskip("mlflow")
    import mlflow.pyfunc
    import mlflow.xgboost

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        mlflow.xgboost.save_model(real_model, tmp)
        return mlflow.pyfunc.load_model(tmp)


class _StubEngine:
    """Minimal stand-in for PricingEngine exposing the health-check inputs."""

    def __init__(self, model, feature_columns, source="local", version=None):
        self.model = model
        self.feature_columns = feature_columns
        self.model_source = source
        self.model_version = version


def _install_engine(monkeypatch, model, feature_columns, source="local", version=None):
    import src.api.router as router

    monkeypatch.setattr(router, "engine", _StubEngine(model, feature_columns, source, version))


def test_health_ok_with_native_xgboost(client, monkeypatch, real_model, real_feature_columns):
    """A native XGBRegressor serves health OK."""
    _install_engine(monkeypatch, real_model, real_feature_columns)

    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json()["checks"]["model"]["status"] == "ok"


def test_health_ok_with_pyfunc_model(client, monkeypatch, pyfunc_model, real_feature_columns):
    """An mlflow.pyfunc-wrapped model (no n_features_in_) serves health OK."""
    assert not hasattr(pyfunc_model, "n_features_in_")
    _install_engine(monkeypatch, pyfunc_model, real_feature_columns, source="mlflow", version="1")

    response = client.get("/v1/health")

    assert response.status_code == 200
    model_check = response.json()["checks"]["model"]
    assert model_check["status"] == "ok"
    assert model_check["source"] == "mlflow"


def test_no_hardcoded_feature_width_fallback():
    """R13: the 10-column fallback must be gone."""
    source = (REPO_ROOT / "src" / "monitoring" / "health_checker.py").read_text()
    assert 'n_features_in_", 10' not in source
    assert 'getattr(model, "n_features_in_", 10)' not in source
