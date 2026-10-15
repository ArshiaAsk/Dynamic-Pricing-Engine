"""Repo-hygiene regression tests for D28 and D29.

D28 untracks the stale ``mlflow.db`` (a binary sqlite database that
``scripts/promote_model.py`` rewrites on every promotion) and ignores it, and
de-indents the two ``.dockerignore`` MLflow entries. D29 tracks ``.dockerignore``
itself, de-indents every line, and excludes ``.env`` from the image. These tests
parse the ignore files directly; they never shell out to ``git``.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GITIGNORE = REPO_ROOT / ".gitignore"
DOCKERIGNORE = REPO_ROOT / ".dockerignore"


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


def test_dockerignore_has_no_surrounding_whitespace():
    """D29: no ``.dockerignore`` line has leading/trailing whitespace.

    Blank lines must be truly empty (no stray spaces).
    """
    offending = [
        (lineno, raw)
        for lineno, raw in enumerate(
            DOCKERIGNORE.read_text(encoding="utf-8").splitlines(), start=1
        )
        if raw != raw.strip()
    ]
    assert not offending, (
        f"{DOCKERIGNORE} has lines with leading/trailing whitespace "
        f"(line, raw): {offending}"
    )


def test_dockerignore_excludes_env_and_local_state():
    """D29: ``.dockerignore`` contains the entries exactly ``.env``, ``mlflow.db``, ``mlruns/``."""
    entries = set(_entries(DOCKERIGNORE))
    required = {".env", "mlflow.db", "mlruns/"}
    missing = required - entries
    assert not missing, (
        f"{DOCKERIGNORE} must contain the entries {sorted(required)}; "
        f"missing {sorted(missing)}; got {sorted(entries)}"
    )


def test_gitignore_does_not_ignore_dockerignore():
    """D29: ``.gitignore`` has no entry that is exactly ``.dockerignore``."""
    entries = list(_entries(GITIGNORE))
    assert ".dockerignore" not in entries, (
        f"{GITIGNORE} must not contain an entry exactly '.dockerignore'; got: {entries}"
    )


def test_dockerignore_excludes_local_model_and_features():
    """D30: ``.dockerignore`` excludes local model pickles and built features.

    The main image builds its own model (``RUN python scripts/regenerate_data.py
    && python -m src.training.train``), so the gitignored local artifacts must
    never enter the build context.
    """
    entries = set(_entries(DOCKERIGNORE))
    required = {"models/*.pkl", "data/features/"}
    missing = required - entries
    assert not missing, (
        f"{DOCKERIGNORE} must contain the entries {sorted(required)}; "
        f"missing {sorted(missing)}; got {sorted(entries)}"
    )

