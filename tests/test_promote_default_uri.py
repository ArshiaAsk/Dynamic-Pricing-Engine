"""D27 point 6: ``scripts/promote_model.py`` defaults to a sqlite tracking store.

The default must be a sqlite URI (the ``mlflow.db`` that ``start.sh``'s MLflow
server uses), not a ``file://`` URI: mlflow 3.x refuses the filesystem backend
unless ``MLFLOW_ALLOW_FILE_STORE`` is set, which this repo does not set.
"""
import pytest


def test_default_tracking_uri_is_sqlite(monkeypatch):
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)

    from scripts.promote_model import _tracking_uri

    uri = _tracking_uri()
    assert uri.startswith("sqlite:"), uri
    assert not uri.startswith("file:"), uri


def test_env_var_overrides_default(monkeypatch):
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "sqlite:///override.db")

    from scripts.promote_model import _tracking_uri

    assert _tracking_uri() == "sqlite:///override.db"
