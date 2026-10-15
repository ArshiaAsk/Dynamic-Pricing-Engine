"""Repo-hygiene regression tests for D28.

D28 untracks the stale ``mlflow.db`` (a binary sqlite database that
``scripts/promote_model.py`` rewrites on every promotion) and ignores it, and
de-indents the two ``.dockerignore`` MLflow entries. These tests parse the
ignore files directly; they never shell out to ``git``.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GITIGNORE = REPO_ROOT / ".gitignore"


def _entries(path: Path):
    """Yield the non-blank, non-comment lines of an ignore file."""
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        yield line


def test_gitignore_ignores_mlflow_db():
    """D28: ``.gitignore`` carries an entry that is exactly ``mlflow.db``."""
    entries = list(_entries(GITIGNORE))
    assert "mlflow.db" in entries, (
        f"{GITIGNORE} must contain an entry exactly 'mlflow.db'; got: {entries}"
    )
