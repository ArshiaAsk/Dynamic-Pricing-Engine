"""R5 — loud/correct MLflow registry resolution and the promote_model fix.

These tests require mlflow and skip cleanly when it is unavailable
(CONVENTIONS rule 17 — never let collection error). They use an isolated
temporary sqlite tracking store under ``tmp_path`` (mlflow 3.x refuses the
filesystem backend unless ``MLFLOW_ALLOW_FILE_STORE`` is set, which we do not
set), so neither the repo's local registry nor the cwd is ever mutated.

Covered criteria:

* R5(a) — when no Production version/alias exists the engine logs at ERROR
  (not WARNING) and reports ``model_source == "local"`` (exposed by
  ``/v1/health`` as ``checks.model.source``).
* R5(b) — ``scripts/promote_model.py`` uses alias-based APIs only
  (``set_registered_model_alias`` / ``set_model_version_tag``); no deprecated
  ``get_latest_versions`` / ``transition_model_version_stage``.
* R5(c) — after running ``promote_model.py`` the engine loads the registry
  model and reports a non-null ``model_version``.
"""
import logging
from pathlib import Path

import joblib
import pytest

pytest.importorskip("mlflow")

REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = REPO_ROOT / "models" / "demand_model.pkl"
FEATURES_PATH = REPO_ROOT / "models" / "features.json"
SUPPORT_PATH = REPO_ROOT / "models" / "training_support.json"
MODEL_NAME = "demand_forecasting_model"


def _engine_config():
    return {
        "pricing": {
            "model_path": str(MODEL_PATH),
            "feature_columns_path": str(FEATURES_PATH),
            "training_support_path": str(SUPPORT_PATH),
            "registered_model_name": MODEL_NAME,
        }
    }


@pytest.fixture
def temp_registry(tmp_path, monkeypatch):
    """An isolated sqlite registry holding one registered model version."""
    if not MODEL_PATH.exists():
        pytest.skip(f"Committed model not found: {MODEL_PATH}")
    import mlflow
    import mlflow.xgboost

    # A sqlite tracking store in tmp_path (not the file store, which mlflow 3.x
    # rejects). ``tmp_path`` is absolute, so this renders as sqlite:////abs/path.
    uri = f"sqlite:///{tmp_path / 'mlflow.db'}"
    monkeypatch.setenv("MLFLOW_TRACKING_URI", uri)
    mlflow.set_tracking_uri(uri)

    # Pin the experiment's artifact location under tmp_path so log_model does
    # not write artifacts into the repo or the cwd.
    artifact_location = (tmp_path / "artifacts").as_uri()
    experiment_id = mlflow.create_experiment(
        "registry-tests", artifact_location=artifact_location
    )

    model = joblib.load(MODEL_PATH)
    with mlflow.start_run(experiment_id=experiment_id):
        mlflow.xgboost.log_model(model, "model", registered_model_name=MODEL_NAME)
    return uri


def test_engine_serves_local_when_no_production_alias(temp_registry, caplog):
    """R5(a): no production version/alias → ERROR log and source 'local'."""
    from src.pricing.engine import PricingEngine

    with caplog.at_level(logging.ERROR, logger="src.pricing.engine"):
        engine = PricingEngine(_engine_config())

    assert engine.model_source == "local"
    assert engine.model_version is None

    production_messages = [r for r in caplog.records if "Production" in r.getMessage()]
    assert production_messages, "expected a log line about the missing Production model"
    # The fallback must be loud: ERROR, never WARNING.
    assert all(r.levelno >= logging.ERROR for r in production_messages)


def test_engine_loads_registry_model_after_promotion(temp_registry):
    """R5(c): after promote_model.py runs, the engine serves the registry model."""
    from scripts.promote_model import promote_model
    from src.pricing.engine import PricingEngine

    promoted = promote_model()
    assert promoted == "1"

    engine = PricingEngine(_engine_config())
    assert engine.model_source == "mlflow"
    assert engine.model_version == "1"


def test_promote_model_uses_alias_apis_only():
    """R5(b): no deprecated MLflow stage APIs remain in promote_model.py."""
    source = (REPO_ROOT / "scripts" / "promote_model.py").read_text()
    assert "get_latest_versions" not in source
    assert "transition_model_version_stage" not in source
    assert "set_registered_model_alias" in source
    assert "set_model_version_tag" in source


def test_health_exposes_active_model_source(client):
    """R5(a): /v1/health reports checks.model.source for the served artifact."""
    response = client.get("/v1/health")
    assert response.status_code == 200
    model_check = response.json()["checks"]["model"]
    assert model_check["source"] == "local"
    assert model_check["status"] == "ok"
