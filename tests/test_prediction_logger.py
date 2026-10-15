"""R17: PredictionLogger must flush at interpreter exit without crashing.

The pre-fix logger flushed from ``__del__``, which runs during interpreter
teardown after ``sys.meta_path`` has been cleared, producing
``ImportError: sys.meta_path is None, Python is likely shutting down``. The fix
removes ``__del__`` and registers ``flush`` with ``atexit`` instead, so the
final flush runs before module teardown.
"""
import atexit
import json
import subprocess
import sys
from pathlib import Path

from src.monitoring.prediction_logger import PredictionLogger

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_no_io_in_del():
    """R17: the ``__del__`` hook (the shutdown-crash source) is gone."""
    assert "__del__" not in PredictionLogger.__dict__


def test_atexit_flushes_buffered_entries(tmp_path, monkeypatch):
    """R17: entries buffered below batch_size are flushed by the atexit hook."""
    registered = []
    monkeypatch.setattr(atexit, "register", lambda fn, *a, **k: registered.append(fn))

    logger = PredictionLogger(log_dir=str(tmp_path), batch_size=100)
    logger.log_optimization(
        request_id="r17-buffered",
        input_data={"product_id": 42},
        result={"optimal_price": 77.0},
        response_time_ms=1.5,
    )

    assert not list(tmp_path.glob("*.jsonl")), "entry should still be buffered"

    assert registered, "PredictionLogger must register an atexit flush"
    for fn in registered:
        fn()

    files = list(tmp_path.glob("*.jsonl"))
    assert files, "atexit flush should have written the buffered entry"
    entries = [
        json.loads(line)
        for line in files[0].read_text().splitlines()
        if line.strip()
    ]
    assert any(e.get("request_id") == "r17-buffered" for e in entries)


def test_interpreter_exit_has_no_shutdown_importerror(tmp_path):
    """R17: a real interpreter exit flushes without the meta_path ImportError."""
    script = (
        "import sys; sys.path.insert(0, {root!r})\n"
        "from src.monitoring.prediction_logger import PredictionLogger\n"
        "lg = PredictionLogger(log_dir={log_dir!r}, batch_size=100)\n"
        "lg.log_optimization(request_id='r17-exit', input_data={{}}, "
        "result={{'optimal_price': 1.0}}, response_time_ms=0.1)\n"
    ).format(root=str(REPO_ROOT), log_dir=str(tmp_path))

    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )

    assert proc.returncode == 0, proc.stderr
    assert "sys.meta_path is None" not in proc.stderr
    files = list(tmp_path.glob("*.jsonl"))
    assert files, "atexit flush at interpreter exit should have written the entry"
