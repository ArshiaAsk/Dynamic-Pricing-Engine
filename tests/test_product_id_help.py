"""D20/R34 follow-up: the Product ID input explains that it is inert."""

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app.py"


def _product_id_calls():
    tree = ast.parse(APP.read_text(encoding="utf-8"))
    calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "number_input"):
            continue
        if node.args and isinstance(node.args[0], ast.Constant):
            if node.args[0].value == "Product ID":
                calls.append(node)
    return calls


def test_product_id_input_has_explanatory_help_text():
    calls = _product_id_calls()
    assert calls, "app.py has no st.number_input(\"Product ID\", ...)"
    help_values = [
        keyword.value for keyword in calls[0].keywords if keyword.arg == "help"
    ]
    assert help_values, "Product ID number_input has no help= text"
    help_node = help_values[0]
    assert isinstance(help_node, ast.Constant) and isinstance(help_node.value, str)
    text = help_node.value.lower()
    assert "not" in text, f"help text does not say the field is inert: {text!r}"
    assert "price" in text, f"help text does not mention the price: {text!r}"
