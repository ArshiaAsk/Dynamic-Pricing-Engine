"""ROADMAP R19 / CONVENTIONS rule 6: every variable in ``.env`` must be read by
application code, and ``.env.example`` must list exactly that read set.

The read set is derived by scanning ``src/`` for the env-access idioms this repo
uses: ``os.getenv("NAME", ...)``, ``os.environ["NAME"]``,
``os.environ.get("NAME")``, and ``EnvConfig``'s ``get_bool`` / ``get_int`` /
``get_env`` helpers. ``scripts/``-only and CI-provided variables (e.g.
``TUNING_TRIALS``, ``GITHUB_*``) are deliberately out of scope: ``.env`` covers
the application's runtime configuration, not build/CI inputs.
"""
import re
from pathlib import Path

import pytest
from dotenv import dotenv_values

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
ENV_FILE = REPO_ROOT / ".env"
ENV_EXAMPLE = REPO_ROOT / ".env.example"

_ENV_READ = re.compile(
    r"""(?:os\.getenv|get_bool|get_int|get_env|os\.environ\.get|os\.environ)
        \s*[\(\[]\s*["']([A-Z][A-Z0-9_]*)["']""",
    re.VERBOSE,
)


def _read_set():
    names = set()
    for path in SRC_DIR.rglob("*.py"):
        names.update(_ENV_READ.findall(path.read_text()))
    return names


def test_env_example_lists_exactly_the_read_set():
    assert ENV_EXAMPLE.exists(), ".env.example is missing"
    example = set(dotenv_values(ENV_EXAMPLE))
    assert example == _read_set(), (
        "mismatch between .env.example and the variables src/ reads; "
        f"only-in-example={sorted(example - _read_set())}, "
        f"only-in-code={sorted(_read_set() - example)}"
    )


def test_env_has_no_unread_variables():
    if not ENV_FILE.exists():
        pytest.skip(".env is not present (gitignored); run on a configured checkout")
    unused = set(dotenv_values(ENV_FILE)) - _read_set()
    assert not unused, f".env defines variables no src/ code reads: {sorted(unused)}"
