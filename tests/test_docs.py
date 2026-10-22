"""Documentation guards for the docs/ directory.

The checks are deliberately static: they read Markdown files from disk and never
run git, a network call or Docker (convention 36).

(a) Every required document exists.
(b) Every relative Markdown link in ``docs/**/*.md`` resolves to an existing file.
    Absolute ``http(s)://`` and ``mailto:`` targets are out of scope, and a
    ``#fragment`` is stripped before the path is resolved.
(c) In the CURRENT-STATE documents (``ARCHITECTURE.md``, ``OPERATIONS.md`` and
    ``LIMITATIONS_AND_NEXT_STEPS.md``) every repo-relative path written in an
    inline code span must exist. A small documented ignore list covers artifacts
    that are generated and gitignored. Historical documents are exempt: the
    decision log, the rebuild history and the archive deliberately mention files
    that were deleted, and the archive is a byte-for-byte copy that must not be
    edited.
(d) The archived original audit is non-empty.
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs"

REQUIRED = [
    "docs/README.md",
    "docs/ARCHITECTURE.md",
    "docs/OPERATIONS.md",
    "docs/DECISIONS.md",
    "docs/ENGINEERING_CONVENTIONS.md",
    "docs/REBUILD_HISTORY.md",
    "docs/LIMITATIONS_AND_NEXT_STEPS.md",
    "docs/archive/AUDIT_ORIGINAL.md",
]

CURRENT_STATE = [
    DOCS / "ARCHITECTURE.md",
    DOCS / "OPERATIONS.md",
    DOCS / "LIMITATIONS_AND_NEXT_STEPS.md",
]

# Generated, gitignored artifacts that current-state docs may name.
IGNORE_PREFIXES = (
    "models/demand_model.pkl",
    "data/",
    "reports/",
    "logs/",
    "mlruns/",
    "mlflow.db",
    "htmlcov/",
    ".coverage",
    ".venv/",
    "__pycache__/",
    "backups/",
)

# Repo-relative path families that must exist when named in a current-state doc.
PATH_PREFIXES = (
    "src/",
    "scripts/",
    "tests/",
    "configs/",
    "docs/",
    ".github/",
    "Dockerfile",
    "docker-compose",
    "requirements.txt",
    "models/features.json",
    "pytest.ini",
)

_FENCED_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_LINK_RE = re.compile(
    r"!?\[[^\]]*\]\(\s*([^)\s]+)(?:\s+\"[^\"]*\")?\s*\)"
)
_REF_DEF_RE = re.compile(r"^\s{0,3}\[([^\]]+)\]:\s*(\S+)", re.MULTILINE)
_CODE_SPAN_RE = re.compile(r"`([^`\n]+)`")
_ABSOLUTE = ("http://", "https://", "mailto:")


def _read(path):
    return path.read_text(encoding="utf-8")


def test_required_documents_exist():
    missing = [name for name in REQUIRED if not (REPO_ROOT / name).is_file()]
    assert missing == [], f"missing required documentation: {missing}"


def _markdown_files():
    return sorted(DOCS.rglob("*.md"))


def _link_targets(text):
    body = _FENCED_RE.sub("", text)
    targets = [match.group(1) for match in _INLINE_LINK_RE.finditer(body)]
    targets += [match.group(2) for match in _REF_DEF_RE.finditer(body)]
    return targets


def test_relative_links_resolve():
    broken = []
    for path in _markdown_files():
        for raw_target in _link_targets(_read(path)):
            target = raw_target.strip("<>")
            if target.startswith(_ABSOLUTE):
                continue
            path_part, _, _fragment = target.partition("#")
            if not path_part:
                continue
            resolved = (path.parent / path_part).resolve()
            if not resolved.exists():
                broken.append(f"{path.relative_to(REPO_ROOT)} -> {target}")
    assert broken == [], f"broken relative links in docs/: {broken}"


def _code_spans(text):
    body = _FENCED_RE.sub("", text)
    for match in _CODE_SPAN_RE.finditer(body):
        yield match.group(1).strip()


def _is_repo_path(token):
    if not token or any(ch in token for ch in "<>*$"):
        return False
    if any(ch.isspace() for ch in token):
        return False
    return token.startswith(PATH_PREFIXES)


def test_current_state_paths_exist():
    missing = []
    for path in CURRENT_STATE:
        for token in _code_spans(_read(path)):
            token = token.rstrip(".,;:)")
            token = re.sub(r":\d+(?:-\d+)?$", "", token)
            if not _is_repo_path(token):
                continue
            if token.startswith(IGNORE_PREFIXES):
                continue
            if not (REPO_ROOT / token).exists():
                missing.append(f"{path.relative_to(REPO_ROOT)} -> {token}")
    assert missing == [], (
        "current-state docs name repo paths that do not exist "
        f"(add generated artifacts to IGNORE_PREFIXES): {missing}"
    )


def test_archived_audit_is_non_empty():
    archive = DOCS / "archive" / "AUDIT_ORIGINAL.md"
    assert archive.is_file(), "docs/archive/AUDIT_ORIGINAL.md is missing"
    assert archive.stat().st_size > 1000, "the archived audit is suspiciously small"
