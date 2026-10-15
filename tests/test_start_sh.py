"""ROADMAP R26 / CONVENTIONS rule 31: the ``start.sh`` health-wait loops are
bounded.

Each loop must give up after a bounded number of attempts and exit non-zero with
a clear message when a dependency never becomes healthy, instead of waiting
forever. These tests run the real script against a stub ``curl`` that never
returns 2xx, so no real MLflow/uvicorn/Streamlit process is started.
"""
import os
import stat
import subprocess
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
START_SH = REPO_ROOT / "start.sh"


def _write_executable(directory: Path, name: str, body: str) -> None:
    path = directory / name
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


@pytest.fixture
def stub_bin(tmp_path):
    """A PATH entry with no-op services and a controllable ``curl``.

    The stub ``curl`` exits 0 only when one of its arguments contains
    ``$STUB_CURL_OK_SUBSTRING``; otherwise it exits non-zero (a non-2xx
    response). This lets a test make the first loop succeed and the second fail.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("mlflow", "uvicorn", "streamlit"):
        _write_executable(bin_dir, name, "#!/bin/bash\nexit 0\n")
    _write_executable(
        bin_dir,
        "curl",
        "#!/bin/bash\n"
        'if [ -n "${STUB_CURL_OK_SUBSTRING:-}" ]; then\n'
        '  for arg in "$@"; do\n'
        '    case "$arg" in *"${STUB_CURL_OK_SUBSTRING}"*) exit 0 ;; esac\n'
        "  done\n"
        "fi\n"
        "exit 22\n",
    )
    return bin_dir


def _run_start_sh(stub_bin: Path, **overrides):
    env = {
        **os.environ,
        "PATH": f"{stub_bin}{os.pathsep}{os.environ['PATH']}",
        # Bound the loops tightly so the test is fast and deterministic.
        "HEALTH_MAX_ATTEMPTS": "2",
        "HEALTH_RETRY_INTERVAL": "0",
        **overrides,
    }
    started = time.monotonic()
    proc = subprocess.run(
        ["bash", str(START_SH)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,  # a hang would raise TimeoutExpired and fail the test
    )
    return proc, time.monotonic() - started


def test_mlflow_loop_gives_up_and_exits_nonzero(stub_bin):
    proc, elapsed = _run_start_sh(
        stub_bin,
        MLFLOW_HEALTH_URL="http://localhost:9/health",
        API_HEALTH_URL="http://localhost:9/v1/health",
        STUB_CURL_OK_SUBSTRING="",
    )
    output = proc.stdout + proc.stderr
    assert proc.returncode != 0, output
    assert "MLflow did not become healthy" in output
    assert elapsed < 30


def test_api_loop_gives_up_after_mlflow_becomes_healthy(stub_bin):
    proc, elapsed = _run_start_sh(
        stub_bin,
        MLFLOW_HEALTH_URL="http://localhost:5000/health",
        API_HEALTH_URL="http://localhost:9/v1/health",
        STUB_CURL_OK_SUBSTRING="5000",
    )
    output = proc.stdout + proc.stderr
    assert proc.returncode != 0, output
    assert "MLflow is up." in proc.stdout
    assert "uvicorn did not become healthy" in output
    assert elapsed < 30
