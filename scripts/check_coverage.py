#!/usr/bin/env python3
"""Per-file coverage gate for the pricing and serving packages (D25 / R30).

Reads the JSON report produced by ``pytest --cov-report=json:...`` (or
``coverage json``) and exits non-zero if any file under ``src/pricing/`` or
``src/api/`` is below THRESHOLD. pytest-cov's ``--cov-fail-under`` only checks
the combined total, so this script is the per-file half of the gate.

Usage:
    python scripts/check_coverage.py [coverage.json]

Environment:
    THRESHOLD   minimum line coverage percent (default 80)

ALLOWLIST is empty: every file in both packages is expected to reach the floor.
An entry is a path -> reason mapping; a reason is mandatory for any exemption.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PACKAGES = ("src/pricing/", "src/api/")
ALLOWLIST: dict[str, str] = {}


def _percent(entry: dict) -> float:
    summary = entry.get("summary", {})
    if "percent_covered" in summary:
        return float(summary["percent_covered"])
    statements = summary.get("num_statements", 0)
    covered = summary.get("covered_lines", 0)
    return 100.0 if statements == 0 else 100.0 * covered / statements


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else Path("coverage.json")
    threshold = float(os.getenv("THRESHOLD", "80"))

    if not path.is_file():
        print(f"FAIL: coverage report not found: {path}")
        return 2

    report = json.loads(path.read_text(encoding="utf-8"))
    files = {
        name.replace(os.sep, "/"): entry
        for name, entry in report.get("files", {}).items()
        if name.replace(os.sep, "/").startswith(PACKAGES)
    }

    if not files:
        print("FAIL: the report contains no files under src/pricing/ or src/api/")
        return 1

    print(f"Per-file coverage gate: >= {threshold:.0f}% (THRESHOLD)")
    failures = []
    for name in sorted(files):
        entry = files[name]
        percent = _percent(entry)
        summary = entry.get("summary", {})
        statements = summary.get("num_statements", 0)
        covered = summary.get("covered_lines", 0)
        reason = ALLOWLIST.get(name)
        ok = percent >= threshold or bool(reason)
        status = "PASS" if ok else "FAIL"
        suffix = f"  (allowlisted: {reason})" if reason else ""
        print(
            f"{status}: {name}: {percent:.0f}% "
            f"({covered}/{statements} statements){suffix}"
        )
        if not ok:
            failures.append(f"{name} {percent:.0f}%")

    if failures:
        print("FAIL: below threshold: " + ", ".join(failures))
        return 1

    print(f"PASS: {len(files)} files at or above {threshold:.0f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
