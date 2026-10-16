"""R23 regression guard for ``scripts/verify_readme.sh``.

R23's acceptance criterion says every README command is "captured by
``scripts/verify_readme.sh``, exit 0". This test keeps the script and the README
from drifting apart, without any network access and without starting a server:

(a) the script exists, is executable, and passes ``bash -n``;
(b) every README quickstart command the script runs (data generation, training,
    the module form of the server start, the pytest and smoke invocations)
    appears **verbatim** in README.md *and* in the script, so neither can drift;
(c) README.md mentions ``scripts/verify_readme.sh``.

The script substitutes ``${PYTHON:-python3}`` for the literal ``python`` at run
time; the canonical (README) command strings below are what the script prints as
its per-step labels and what must stay present in both files.
"""
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
SCRIPT = REPO_ROOT / "scripts" / "verify_readme.sh"

# The README quickstart commands the script must run, verbatim. Each string must
# be present in README.md and in scripts/verify_readme.sh.
REQUIRED_COMMANDS = [
    "python scripts/regenerate_data.py",
    "python -m src.training.train",
    "python -m src.api.server",
    "pytest tests -q",
    "pytest tests/smoke_tests.py",
]


def test_script_exists_and_is_executable():
    assert SCRIPT.is_file(), f"{SCRIPT} is missing"
    assert os.access(SCRIPT, os.X_OK), f"{SCRIPT} is not executable"


def test_script_passes_bash_syntax_check():
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT)], capture_output=True, text=True
    )
    assert result.returncode == 0, f"bash -n {SCRIPT} failed: {result.stderr}"


def test_quickstart_commands_appear_in_readme():
    readme = README.read_text(encoding="utf-8")
    missing = [cmd for cmd in REQUIRED_COMMANDS if cmd not in readme]
    assert missing == [], f"README.md is missing quickstart commands: {missing}"


def test_script_runs_the_readme_quickstart_commands():
    script = SCRIPT.read_text(encoding="utf-8")
    missing = [cmd for cmd in REQUIRED_COMMANDS if cmd not in script]
    assert missing == [], f"{SCRIPT} does not run the README commands: {missing}"


def test_readme_mentions_the_script():
    readme = README.read_text(encoding="utf-8")
    assert "scripts/verify_readme.sh" in readme, (
        "README.md does not mention scripts/verify_readme.sh"
    )
