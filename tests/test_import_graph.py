"""R22 / CONVENTIONS rules 1 & 2: every module under ``src/`` is reachable.

The import graph is built from the **AST only** — no module is imported or
executed — and the test asserts that every module under ``src/`` is reachable
from a real entry point, or is on an explicit allowlist.

Entry points (the reachability roots):

* ``src.api.server`` — the served FastAPI application.
* ``src.training.train`` — the training entry point.
* every ``src.*`` module imported by a ``scripts/*.py`` file. This is the
  explicit extension R22 calls for: ``scripts/regenerate_data.py``,
  ``scripts/train_with_tuning.py`` and ``scripts/promote_model.py`` are the
  repo's documented CLI entry points even though nothing imports them.
* every ``src.*`` module imported by ``app.py`` (the Streamlit UI; it imports
  none today).

Allowlist: a package whose ``__init__.py`` is empty is reachable automatically
(importing any submodule executes the package ``__init__``), so it needs no
entry. Anything else must be listed in ``ALLOWLIST`` with a one-line reason.
The test also asserts the allowlist cannot rot: every entry must exist and must
NOT be reachable.
"""
import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"

# Entry-point modules that seed reachability.
ENTRY_MODULES = ("src.api.server", "src.training.train")

# Non-src entry points whose direct ``src.*`` imports are also roots.
ENTRY_GLOBS = ("scripts/*.py", "app.py")

# Deliberately-unreachable modules: module name -> one-line reason. Empty
# ``__init__.py`` packages are exempt automatically and must not be listed.
ALLOWLIST = {}


def _module_name(path: Path) -> str:
    """Repo-relative dotted module name for ``path``."""
    rel = path.relative_to(REPO_ROOT).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _src_modules():
    """Map every module under ``src/`` to its file path."""
    return {
        _module_name(path): path
        for path in sorted(SRC_DIR.rglob("*.py"))
    }


def _empty_init_packages(modules):
    """Packages whose ``__init__.py`` is empty (reachable automatically)."""
    return {
        name
        for name, path in modules.items()
        if path.name == "__init__.py" and path.read_text().strip() == ""
    }


def _imports_of(path: Path, module_name: str, known):
    """Repo modules directly imported by ``path`` (AST parse only, no import)."""
    tree = ast.parse(path.read_text(), filename=str(path))
    pkg = module_name.rsplit(".", 1)[0] if "." in module_name else ""
    found = set()
    for node in ast.walk(tree):
        candidates = []
        if isinstance(node, ast.Import):
            candidates = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                parts = pkg.split(".") if pkg else []
                up = node.level - 1
                base = parts[: len(parts) - up] if up else parts
                base_s = ".".join(base)
                if node.module:
                    base_s = f"{base_s}.{node.module}" if base_s else node.module
                candidates = [base_s] + [
                    f"{base_s}.{alias.name}" for alias in node.names
                ]
            elif node.module:
                candidates = [node.module] + [
                    f"{node.module}.{alias.name}" for alias in node.names
                ]
        for candidate in candidates:
            if candidate in known:
                found.add(candidate)
    return found


def _roots(modules, known):
    """Reachability roots: the entry-point modules + entry-point script imports."""
    roots = {name for name in ENTRY_MODULES if name in modules}
    for pattern in ENTRY_GLOBS:
        for path in sorted(REPO_ROOT.glob(pattern)):
            roots |= _imports_of(path, _module_name(path), known)
    return roots


def _reachable(modules, roots):
    """Transitive closure over imports, plus package containment."""
    known = set(modules)
    forward = {
        name: _imports_of(path, name, known) for name, path in modules.items()
    }
    reachable = set()
    stack = list(roots)
    while stack:
        name = stack.pop()
        if name in reachable:
            continue
        reachable.add(name)
        # Importing ``a.b.c`` executes the package ``a.b`` (and ``a``).
        parts = name.split(".")
        for i in range(1, len(parts)):
            ancestor = ".".join(parts[:i])
            if ancestor in modules:
                stack.append(ancestor)
        stack.extend(forward.get(name, ()))
    return reachable


def test_every_src_module_is_reachable_or_allowlisted():
    """No module under ``src/`` may be unreachable unless explicitly allowed."""
    modules = _src_modules()
    reachable = _reachable(modules, _roots(modules, set(modules)))
    exempt = _empty_init_packages(modules)

    unreachable = sorted(
        name
        for name in modules
        if name not in reachable
        and name not in exempt
        and name not in ALLOWLIST
    )
    assert unreachable == [], (
        "unreachable modules under src/ — delete them or wire them into an "
        "entry point (CONVENTIONS rules 1/2):\n"
        + "\n".join(
            f"  {name}  ({modules[name].relative_to(REPO_ROOT)})"
            for name in unreachable
        )
    )


def test_allowlist_entries_exist_and_are_unreachable():
    """The allowlist cannot rot: entries must exist, be unreachable, and reasoned."""
    modules = _src_modules()
    reachable = _reachable(modules, _roots(modules, set(modules)))

    problems = []
    for name, reason in ALLOWLIST.items():
        if not (isinstance(reason, str) and reason.strip()):
            problems.append(f"allowlist entry {name!r} needs a one-line reason")
        if name not in modules:
            problems.append(f"allowlist entry {name!r} does not exist (reason: {reason!r})")
        elif name in reachable:
            problems.append(
                f"allowlist entry {name!r} is now reachable — remove it "
                f"(reason: {reason!r})"
            )
    assert problems == [], "\n".join(problems)
