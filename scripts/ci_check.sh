#!/usr/bin/env bash
#
# scripts/ci_check.sh — the GitHub Actions `test` job, runnable locally
# (ROADMAP R27 / DECISIONS D18). The workflow calls this script so CI and a
# developer run the same steps:
#
#   1. build the data + model a clean checkout does not have;
#   2. run the full suite with coverage, a combined 80% floor and a JUnit report;
#   3. run the per-file coverage gate (src/pricing + src/api);
#   4. fail if any test was skipped (ALLOW_SKIPS=1 for local debugging only);
#   5. run scripts/verify_readme.sh (README quickstart, live API, smoke tests).
#
# Every step prints PASS/FAIL and the script exits non-zero at the first
# failure. Dependencies are installed by the workflow, never here.
#
# Environment:
#   PYTHON       interpreter to use (default: python3)
#   ALLOW_SKIPS  1 disables the zero-skip gate (local debugging only)
#   THRESHOLD    per-file coverage floor passed to check_coverage.py (default 80)

set -euo pipefail

PYTHON="${PYTHON:-python3}"
ALLOW_SKIPS="${ALLOW_SKIPS:-0}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

WORK="$(mktemp -d)"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

COVERAGE_JSON="$WORK/coverage.json"
JUNIT_XML="$WORK/junit.xml"

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; exit 1; }

run_step() {
  local name="$1"
  shift
  echo "== $name"
  if "$@"; then pass "$name"; else fail "$name"; fi
}

echo "ci_check.sh: repo=$REPO_ROOT python=$PYTHON"

build_artifacts() {
  "$PYTHON" scripts/regenerate_data.py && "$PYTHON" -m src.training.train
}

run_tests() {
  COVERAGE_FILE="$WORK/.coverage" "$PYTHON" -m pytest tests -q -rs \
    --cov=src/pricing --cov=src/api \
    --cov-report=term-missing \
    --cov-report="json:$COVERAGE_JSON" \
    --junitxml="$JUNIT_XML" \
    --cov-fail-under=80
}

check_coverage() {
  "$PYTHON" scripts/check_coverage.py "$COVERAGE_JSON"
}

check_no_skips() {
  "$PYTHON" - "$JUNIT_XML" <<'PY'
import sys
import xml.etree.ElementTree as ET

root = ET.parse(sys.argv[1]).getroot()
cases = list(root.iter("testcase"))
skipped = [
    case.get("name", "?")
    for case in cases
    if case.find("skipped") is not None
]
if skipped:
    print(f"skipped tests: {len(skipped)}: {skipped}")
    sys.exit(1)
print(f"no skipped tests ({len(cases)} collected)")
PY
}

allow_skips() {
  echo "ALLOW_SKIPS=1: zero-skip gate disabled for local debugging"
}

verify_readme() {
  PYTHON="$PYTHON" bash scripts/verify_readme.sh
}

run_step "build data + model" build_artifacts
run_step "pytest tests (coverage + JUnit, combined floor 80%)" run_tests
run_step "per-file coverage gate (src/pricing + src/api)" check_coverage
if [ "$ALLOW_SKIPS" = "1" ]; then
  run_step "zero-skip gate" allow_skips
else
  run_step "zero-skip gate" check_no_skips
fi
run_step "README quickstart (scripts/verify_readme.sh)" verify_readme

echo "ci_check.sh: all steps PASS"
