"""R32: README must carry a Limitations section with the required statements.

The section is located by its ``## Limitations`` heading and checked for a small
list of lowercase substrings, one per limitation R32 requires: the model is
observational; its argmax is not a valid causal pricing policy on real data; all
results are synthetic; and rate limiting is per worker process (D22).
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"

REQUIRED_SUBSTRINGS = [
    "observational",
    "not a valid causal",
    "synthetic",
    "per worker",
]

_LIMITATIONS_RE = re.compile(
    r"^## Limitations\s*$(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL
)


def _limitations_text(readme_text: str) -> str:
    match = _LIMITATIONS_RE.search(readme_text)
    assert match is not None, "README has no '## Limitations' section"
    return match.group(1).lower()


def test_readme_has_limitations_section():
    text = _limitations_text(README.read_text(encoding="utf-8"))
    missing = [phrase for phrase in REQUIRED_SUBSTRINGS if phrase not in text]
    assert missing == [], f"Limitations section is missing: {missing}"
