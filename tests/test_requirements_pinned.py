"""D27 points 1-3: every direct dependency in ``requirements.txt`` is exactly pinned.

D27 pins all direct dependencies with ``==`` (transitive deps stay unpinned),
replaces ``xgboost`` with ``xgboost-cpu``, and keeps ``protobuf==4.25.9``.
"""
import re
from pathlib import Path

REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements.txt"

# name[extras]==version  (name may contain - _ . ; extras in [ ... ])
PIN_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*(\[[A-Za-z0-9._,-]+\])?==[^\s=<>!~;]+$"
)


def _requirement_lines():
    for raw in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-"):  # options such as -r/--index-url
            continue
        yield line


def test_at_least_one_requirement():
    assert list(_requirement_lines()), "requirements.txt has no requirements"


def test_every_requirement_is_exactly_pinned():
    bad = [line for line in _requirement_lines() if not PIN_RE.match(line)]
    assert bad == [], f"unpinned or malformed requirement lines: {bad}"


def test_plain_xgboost_is_not_used():
    offenders = [
        line
        for line in _requirement_lines()
        if line.split("==")[0].split("[")[0].strip() == "xgboost"
    ]
    assert offenders == [], (
        f"plain 'xgboost' must be 'xgboost-cpu' (avoids nvidia-nccl-cu13): {offenders}"
    )
