"""R31: every relative Markdown link in README.md must resolve.

Covers inline links/images (``[text](target)``) and reference-style link
definitions (``[ref]: target``); fenced code blocks are ignored. Absolute
``http(s)://`` and ``mailto:`` URLs are out of scope (they point off-repo).

Relative targets are resolved against the repository root after stripping any
``#fragment``. A same-file anchor (``#section``) is accepted when a heading in
README.md has the matching GitHub-style slug: lowercase, drop every character
that is not a word character, whitespace or hyphen (this also drops emoji), then
turn runs of whitespace into single hyphens.
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"

_FENCED_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_LINK_RE = re.compile(r"!?\[[^\]]*\]\(\s*([^)\s]+)(?:\s+\"[^\"]*\")?\s*\)")
_REF_DEF_RE = re.compile(r"^\s{0,3}\[([^\]]+)\]:\s*(\S+)", re.MULTILINE)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$", re.MULTILINE)

_ABSOLUTE_PREFIXES = ("http://", "https://", "mailto:")


def _strip_fences(text: str) -> str:
    return _FENCED_RE.sub("", text)


def _slug(heading: str) -> str:
    slug = heading.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    return re.sub(r"\s+", "-", slug.strip())


def _heading_slugs(text: str):
    return {_slug(match.group(2)) for match in _HEADING_RE.finditer(text)}


def _link_targets(text: str):
    body = _strip_fences(text)
    targets = [match.group(1) for match in _INLINE_LINK_RE.finditer(body)]
    targets += [match.group(2) for match in _REF_DEF_RE.finditer(body)]
    return targets


def test_readme_relative_links_resolve():
    text = README.read_text(encoding="utf-8")
    headings = _heading_slugs(text)

    broken = []
    for raw_target in _link_targets(text):
        target = raw_target.strip("<>")
        if target.startswith(_ABSOLUTE_PREFIXES):
            continue

        path_part, _, fragment = target.partition("#")
        if not path_part:
            # Same-file anchor: the heading slug must exist.
            if fragment and fragment not in headings:
                broken.append(target)
            continue

        if not (REPO_ROOT / path_part).exists():
            broken.append(target)

    assert broken == [], f"README has broken relative links: {sorted(set(broken))}"
