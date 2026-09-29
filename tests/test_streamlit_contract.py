"""Streamlit ↔ API contract test (ROADMAP R10).

The Streamlit UI reads fields out of the ``POST /v1/optimize-price`` JSON
response. Historically it read ``predicted_demand`` while the API returns
``expected_demand``, so the Quick tab raised ``KeyError`` and swallowed it
(STATE.md §5.7). Nothing caught that, because no test compared the fields the UI
reads against the API response schema (CONVENTIONS rule 29).

This test parses ``app.py`` as source (importing it would execute the Streamlit
script) and asserts:

* every response field the UI reads is a field of ``PricingResponse``;
* the UI offers only optimization methods the API actually accepts.

A future field rename or a reintroduced rejected method therefore fails CI.
"""
import ast
from pathlib import Path

from src.api.schemas import PricingRequest, PricingResponse

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = REPO_ROOT / "app.py"


def _app_tree():
    return ast.parse(APP_PATH.read_text(), filename=str(APP_PATH))


def _response_keys_read():
    """String keys subscripted off a ``result`` variable, e.g. ``result['x']``."""
    keys = set()
    for node in ast.walk(_app_tree()):
        if not isinstance(node, ast.Subscript):
            continue
        if not (isinstance(node.value, ast.Name) and node.value.id == "result"):
            continue
        slice_node = node.slice
        if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
            keys.add(slice_node.value)
    return keys


def _selectbox_options(label):
    """Literal options passed as the second argument of an ``st.selectbox`` call."""
    for node in ast.walk(_app_tree()):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "selectbox"):
            continue
        if len(node.args) < 2:
            continue
        first = node.args[0]
        if not (isinstance(first, ast.Constant) and first.value == label):
            continue
        options = node.args[1]
        if isinstance(options, ast.List):
            return [
                elt.value
                for elt in options.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            ]
    raise AssertionError(f"selectbox labelled {label!r} not found in app.py")


def test_app_reads_only_pricing_response_fields():
    """R10 / CONVENTIONS rule 29: UI-read keys ⊆ PricingResponse.model_fields."""
    read = _response_keys_read()
    assert read, "app.py reads no response fields — the parser or the UI changed"
    unknown = read - set(PricingResponse.model_fields)
    assert not unknown, (
        f"app.py reads response fields not in PricingResponse: {sorted(unknown)}. "
        "Update the UI or the response schema in the same change."
    )
    # The field the UI must read (not the legacy 'predicted_demand').
    assert "expected_demand" in read
    assert "predicted_demand" not in read


def test_app_offers_only_accepted_optimization_methods():
    """R10 / D2: the UI selectbox must not offer the rejected legacy method."""
    options = _selectbox_options("Optimization Method")
    accepted = set(
        PricingRequest.model_fields["optimization_method"].annotation.__args__
    )
    assert options, "no optimization-method options found in app.py"
    assert set(options) <= accepted, (
        f"app.py offers methods the API rejects: {sorted(set(options) - accepted)}"
    )
    assert "bayesian" not in options
    assert "grid_search" in options


def test_app_source_is_importable_python():
    """Guard: the contract parser above requires app.py to stay valid Python."""
    _app_tree()  # raises SyntaxError if app.py is malformed


def test_contract_test_is_not_vacuous():
    """Sanity: the schema exposes the fields the UI depends on."""
    schema_fields = set(PricingResponse.model_json_schema()["properties"])
    assert {"optimal_price", "expected_demand", "expected_revenue"} <= schema_fields
