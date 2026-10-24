"""D32: every documented or default input lies inside the model's training support.

The support is read from the generated training features
(``data/features/training_features.parquet``): the observed range of
``competitor_price`` and of ``price_ratio``. Every documented or default input
in the repository is then parsed and checked:

* ``competitor_price`` lies inside the observed competitor range;
* ``price_min`` and ``price_max`` lie inside
  ``[ratio_min * competitor_price, ratio_max * competitor_price]``;
* ``cost`` is positive and below ``price_min`` (the margin floor
  ``cost * (1 + min_margin_pct)`` must be able to bind inside the bounds);
* no absolute price default survives in ``configs/config.yaml`` or in the
  README's config snippet (D32: no absolute price defaults anywhere).

Sources: the ``PricingRequest`` example, the README curl block, ``app.py``
(number_input defaults, the Advanced-tab example request and the Batch-tab row
defaults), ``tests/smoke_tests.py``, ``scripts/load_test.sh``,
``scripts/verify_readme.sh``, ``tests/test_optimizer_real.py`` and
``configs/config.yaml``.

Parsing is static (AST / JSON / YAML); no API is imported and no server starts.
"""
import ast
import json
import re
from pathlib import Path

import pandas as pd
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PARQUET = REPO_ROOT / "data" / "features" / "training_features.parquet"
README = REPO_ROOT / "README.md"
APP = REPO_ROOT / "app.py"
SMOKE = REPO_ROOT / "tests" / "smoke_tests.py"
CONFIG = REPO_ROOT / "configs" / "config.yaml"
LOAD_TEST = REPO_ROOT / "scripts" / "load_test.sh"
VERIFY_README = REPO_ROOT / "scripts" / "verify_readme.sh"

PRICE_FIELDS = {"competitor_price", "price_min", "price_max", "cost"}

# Labels of the Streamlit number inputs that set a price or cost. Matching is by
# substring so the currency-unit wording can change without breaking the parser.
NUMBER_INPUT_LABELS = {
    "Competitor Price": "competitor_price",
    "Minimum Price": "price_min",
    "Maximum Price": "price_max",
    "Product Cost": "cost",
}

_CURL_PAYLOAD_RE = re.compile(r"-d\s*'(\{.*?\})'", re.DOTALL)
_HEREDOC_RE = re.compile(r"PAYLOAD=\$\(cat << 'EOF'\n(.*?)\nEOF", re.DOTALL)
_OPTIMIZE_PAYLOAD_RE = re.compile(r"OPTIMIZE_PAYLOAD='(\{.*?\})'", re.DOTALL)
_YAML_BLOCK_RE = re.compile(r"```yaml\n(.*?)```", re.DOTALL)


@pytest.fixture(scope="module")
def support():
    """Observed ranges from the generated training features."""
    if not PARQUET.exists():
        pytest.skip(f"Generated training features not found: {PARQUET}")
    frame = pd.read_parquet(PARQUET, columns=["competitor_price", "price_ratio"])
    return {
        "competitor_min": float(frame["competitor_price"].min()),
        "competitor_max": float(frame["competitor_price"].max()),
        "ratio_min": float(frame["price_ratio"].min()),
        "ratio_max": float(frame["price_ratio"].max()),
    }


def _violations(name, payload, support, check_bounds=True):
    """Return the support violations of one documented input."""
    problems = []
    competitor = payload.get("competitor_price")
    if competitor is None:
        return problems
    if not (support["competitor_min"] <= competitor <= support["competitor_max"]):
        problems.append(
            f"{name}: competitor_price {competitor} outside "
            f"[{support['competitor_min']}, {support['competitor_max']}]"
        )

    price_min = payload.get("price_min")
    price_max = payload.get("price_max")
    if check_bounds and competitor > 0:
        lower = support["ratio_min"] * competitor
        upper = support["ratio_max"] * competitor
        for field, value in (("price_min", price_min), ("price_max", price_max)):
            if value is None:
                continue
            if not (lower <= value <= upper):
                problems.append(
                    f"{name}: {field} {value} outside [{lower}, {upper}] "
                    f"(price_ratio support x competitor_price {competitor})"
                )

    cost = payload.get("cost")
    if cost is not None:
        if cost <= 0:
            problems.append(f"{name}: cost {cost} is not positive")
        if price_min is not None and cost >= price_min:
            problems.append(f"{name}: cost {cost} is not below price_min {price_min}")
    return problems


def _schema_example():
    from src.api.schemas import PricingRequest

    return [("src/api/schemas.py PricingRequest example",
             PricingRequest.model_config["json_schema_extra"]["example"])]


def _readme_payloads():
    text = README.read_text(encoding="utf-8")
    payloads = []
    for match in _CURL_PAYLOAD_RE.finditer(text):
        payloads.append(("README.md curl example", json.loads(match.group(1))))
    return payloads


def _readme_config_defaults():
    """Absolute price defaults in the README's config snippet (if any)."""
    problems = []
    for block in _YAML_BLOCK_RE.findall(README.read_text(encoding="utf-8")):
        data = yaml.safe_load(block) or {}
        pricing = data.get("pricing") if isinstance(data, dict) else None
        if not isinstance(pricing, dict):
            continue
        for key in ("price_min", "price_max"):
            if key in pricing:
                problems.append(
                    f"README.md config snippet: absolute price default {key}: {pricing[key]}"
                )
    return problems


def _numeric(value):
    return isinstance(value, ast.Constant) and isinstance(value.value, (int, float))         and not isinstance(value.value, bool)


def _app_inputs():
    tree = ast.parse(APP.read_text(encoding="utf-8"), filename=str(APP))
    inputs = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            keys = [k.value for k in node.keys
                    if isinstance(k, ast.Constant) and isinstance(k.value, str)]
            if "competitor_price" in keys:
                payload = {
                    key.value: value.value
                    for key, value in zip(node.keys, node.values)
                    if isinstance(key, ast.Constant) and isinstance(key.value, str)
                    and _numeric(value)
                }
                if "competitor_price" in payload:
                    inputs.append(("app.py example_request", payload))
            continue

        if not isinstance(node, ast.Call):
            continue
        func = node.func

        if isinstance(func, ast.Attribute) and func.attr == "number_input":
            if not node.args or not isinstance(node.args[0], ast.Constant):
                continue
            label = node.args[0].value
            field = next(
                (target for prefix, target in NUMBER_INPUT_LABELS.items()
                 if isinstance(label, str) and prefix in label),
                None,
            )
            if field is None:
                continue
            value = next(
                (kw.value.value for kw in node.keywords
                 if kw.arg == "value" and _numeric(kw.value)),
                None,
            )
            if value is not None:
                inputs.append((f"app.py number_input {label!r}", {field: value}))

        # Batch tab: float(row.get('price_min', 70.0))
        if isinstance(func, ast.Attribute) and func.attr == "get" and len(node.args) >= 2:
            key, default = node.args[0], node.args[1]
            if (isinstance(key, ast.Constant) and key.value in PRICE_FIELDS
                    and _numeric(default)):
                inputs.append(
                    (f"app.py batch default {key.value!r}", {key.value: default.value})
                )

    return inputs


def _smoke_payloads():
    tree = ast.parse(SMOKE.read_text(encoding="utf-8"), filename=str(SMOKE))
    payloads = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        keys = [k.value for k in node.keys
                if isinstance(k, ast.Constant) and isinstance(k.value, str)]
        if "competitor_price" not in keys:
            continue
        payload = {
            key.value: value.value
            for key, value in zip(node.keys, node.values)
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
            and _numeric(value)
        }
        payloads.append(("tests/smoke_tests.py payload", payload))
    return payloads


def _script_payloads():
    payloads = []
    load_text = LOAD_TEST.read_text(encoding="utf-8")
    for match in _HEREDOC_RE.finditer(load_text):
        payloads.append(("scripts/load_test.sh PAYLOAD", json.loads(match.group(1))))

    verify_text = VERIFY_README.read_text(encoding="utf-8")
    for match in _OPTIMIZE_PAYLOAD_RE.finditer(verify_text):
        payloads.append(
            ("scripts/verify_readme.sh OPTIMIZE_PAYLOAD", json.loads(match.group(1)))
        )
    return payloads


def _optimizer_test_inputs():
    from tests.test_optimizer_real import BASE_FEATURES, GRID_BOUNDS, R1_BOUNDS

    competitor = BASE_FEATURES["competitor_price"]
    inputs = [("tests/test_optimizer_real.py BASE_FEATURES", dict(BASE_FEATURES))]
    for price_min, price_max in list(R1_BOUNDS) + [GRID_BOUNDS]:
        inputs.append((
            f"tests/test_optimizer_real.py bounds ({price_min}, {price_max})",
            {
                "competitor_price": competitor,
                "price_min": price_min,
                "price_max": price_max,
            },
        ))
    return inputs


def _config_violations():
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    pricing = config.get("pricing", {})
    return [
        f"configs/config.yaml: absolute price default {key}: {pricing[key]}"
        for key in ("price_min", "price_max")
        if key in pricing
    ]


def test_every_documented_input_is_in_support(support):
    """Every documented/default input lies inside the training support."""
    violations = []
    for name, payload in (
        _schema_example()
        + _readme_payloads()
        + _app_inputs()
        + _smoke_payloads()
        + _script_payloads()
        + _optimizer_test_inputs()
    ):
        check_bounds = not (
            payload.get("price_min") is not None
            and payload.get("price_max") is not None
            and payload["price_max"] <= payload["price_min"]
        )
        violations.extend(_violations(name, payload, support, check_bounds=check_bounds))
    violations.extend(_readme_config_defaults())
    violations.extend(_config_violations())

    assert violations == [], (
        "documented/default inputs outside the training support "
        f"(competitor [{support['competitor_min']}, {support['competitor_max']}], "
        f"price_ratio [{support['ratio_min']}, {support['ratio_max']}]):\n"
        + "\n".join(f"  {item}" for item in violations)
    )
