"""Promote a registered model version to the production alias.

Uses alias-based MLflow APIs only — ``set_registered_model_alias`` and
``set_model_version_tag``. The deprecated MLflow *stage* APIs are deliberately
not used: stages are deprecated in favour of aliases, and the engine resolves
the ``production`` alias (with a ``stage=Production`` tag as a fallback).

The tracking URI comes from ``MLFLOW_TRACKING_URI`` and defaults to this repo's
local file store (``mlruns/``), which is the registry the engine reads.
"""
import os
from pathlib import Path

MODEL_NAME = "demand_forecasting_model"
PRODUCTION_ALIAS = "production"
REPO_ROOT = Path(__file__).resolve().parents[1]


def _tracking_uri() -> str:
    default = f"file://{REPO_ROOT / 'mlruns'}"
    return os.getenv("MLFLOW_TRACKING_URI", default)


def promote_model(model_name: str = MODEL_NAME, alias: str = PRODUCTION_ALIAS,
                  version: str = None) -> str:
    """Point ``alias`` at the newest (or the given) version of ``model_name``.

    Args:
        model_name: Registered model name.
        alias: Alias to assign (default ``"production"``).
        version: Version to promote; defaults to the newest registered version.

    Returns:
        The promoted version string.

    Raises:
        SystemExit: If the model has no registered versions.
    """
    # MLflow is optional: import it lazily so importing this module never
    # requires mlflow to be installed/importable.
    import mlflow
    from mlflow.tracking import MlflowClient

    mlflow.set_tracking_uri(_tracking_uri())
    client = MlflowClient()

    if version is None:
        versions = client.search_model_versions(f"name='{model_name}'")
        if not versions:
            raise SystemExit(f"No registered versions found for model '{model_name}'")
        version = max(versions, key=lambda v: int(v.version)).version

    version = str(version)
    client.set_registered_model_alias(model_name, alias, version)
    client.set_model_version_tag(model_name, version, "stage", "Production")
    return version


if __name__ == "__main__":
    promoted = promote_model()
    print(f"Promoted {MODEL_NAME} version {promoted} to alias '{PRODUCTION_ALIAS}'")
