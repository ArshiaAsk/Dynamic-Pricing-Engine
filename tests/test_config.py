"""ROADMAP R18 / CONVENTIONS rule 5: every key in ``configs/*.yaml`` must be
read by first-party code, or be deleted.

The reference scan covers ``src/`` and ``scripts/`` -- the API and training
entry points that actually consume configuration. A key counts as "read" when
its leaf name appears as a string literal in that code, which is the form every
config access in this repo uses (e.g. ``config["pricing"]["model_path"]`` or
``config.get("features", {}).get("lag_days")``).

``ALLOWLIST`` is for keys that are deliberately unread; it is empty today and
every entry must carry a reason.
"""
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "configs"
CODE_DIRS = (REPO_ROOT / "src", REPO_ROOT / "scripts")

# Keys intentionally not read by first-party code, mapped to the reason they
# may remain in the YAML. Keep this empty unless a key genuinely cannot be
# consumed yet.
ALLOWLIST: dict = {}


def _flatten(node, prefix, out):
    if isinstance(node, dict):
        for key, value in node.items():
            _flatten(value, f"{prefix}.{key}" if prefix else key, out)
    else:
        out.add(prefix)


def _yaml_keys():
    """Map each ``configs/*.yaml`` file name -> set of dotted leaf keys."""
    files = {}
    for path in sorted(CONFIG_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text()) or {}
        keys = set()
        _flatten(data, "", keys)
        files[path.name] = keys
    return files


def _code_source():
    return "\n".join(
        path.read_text()
        for directory in CODE_DIRS
        for path in directory.rglob("*.py")
    )


def test_config_directory_is_not_empty():
    assert _yaml_keys(), "no configs/*.yaml files found"


def test_exactly_one_config_file():
    """R35 / DECISIONS D26: there is a single YAML config, configs/config.yaml.

    The former ``config.dev.yaml`` / ``config.prod.yaml`` duplicates and the
    ``APP_ENV``-driven selection were removed, so the config directory must hold
    exactly one file.
    """
    files = sorted(path.name for path in CONFIG_DIR.glob("*.yaml"))
    assert files == ["config.yaml"], (
        f"expected exactly configs/config.yaml, found {files}"
    )


def test_every_yaml_key_is_read_by_code():
    source = _code_source()
    unread = []
    for filename, keys in _yaml_keys().items():
        for key in sorted(keys):
            leaf = key.rsplit(".", 1)[-1]
            if key in ALLOWLIST or leaf in ALLOWLIST:
                continue
            if not re.search(rf"""["']{re.escape(leaf)}["']""", source):
                unread.append(f"{filename}:{key}")
    assert not unread, (
        "config keys defined but never read by src/ or scripts/ "
        f"(delete them or wire them up): {unread}"
    )


def test_allowlist_entries_carry_a_reason():
    for key, reason in ALLOWLIST.items():
        assert reason and reason.strip(), f"allowlist entry {key!r} needs a reason"


def test_unread_runtime_blocks_are_deleted():
    """R18: the never-read api:/monitoring:/logging: blocks were removed."""
    for filename, keys in _yaml_keys().items():
        roots = {key.split(".", 1)[0] for key in keys}
        for block in ("monitoring", "api", "logging"):
            assert block not in roots, f"{filename} still has an unread {block}: block"
