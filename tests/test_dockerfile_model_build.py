"""DECISIONS D30: the main Dockerfile builds data and model inside the image.

After ``COPY . .`` the image has the source but *not* the gitignored
``models/demand_model.pkl`` / ``data/features/`` artifacts (``.dockerignore``
excludes them), so the main Dockerfile must regenerate the data and retrain the
model at build time — offline — for a clean-checkout image to have a model to
serve.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = REPO_ROOT / "Dockerfile"


def _is_source_copy(line):
    """True for ``COPY . .`` and flag variants (e.g. ``COPY --chown=a:a . .``)."""
    parts = line.split()
    if not parts or parts[0].upper() != "COPY":
        return False
    return [part for part in parts[1:] if not part.startswith("--")] == [".", "."]


def _run_lines_after_copy():
    """The RUN lines that appear after the ``COPY . .`` line."""
    lines = DOCKERFILE.read_text(encoding="utf-8").splitlines()
    copy_idx = next(
        i for i, line in enumerate(lines) if _is_source_copy(line)
    )
    return [
        line for line in lines[copy_idx + 1:]
        if line.strip().upper().startswith("RUN")
    ]


def test_dockerfile_builds_data_and_model_after_copy():
    """A RUN after ``COPY . .`` must build both the data and the model."""
    run_lines = _run_lines_after_copy()
    joined = "\n".join(run_lines)
    assert "scripts/regenerate_data.py" in joined, (
        "no RUN after 'COPY . .' mentions scripts/regenerate_data.py; "
        f"RUN lines after COPY: {run_lines}"
    )
    assert "src.training.train" in joined, (
        "no RUN after 'COPY . .' mentions src.training.train; "
        f"RUN lines after COPY: {run_lines}"
    )
