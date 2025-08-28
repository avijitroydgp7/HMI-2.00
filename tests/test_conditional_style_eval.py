import pytest

from components.button.conditional_style import _safe_eval, ConditionalStyleManager
from dialogs.actions.constants import TriggerMode


def test_safe_eval_valid_boolean_arithmetic():
    val, err = _safe_eval("a > 5 and b < 10", {"a": 6, "b": 9})
    assert err is None
    assert val is True


def test_safe_eval_invalid_syntax():
    val, err = _safe_eval("a >", {"a": 1})
    assert val is None
    assert err and "Invalid expression syntax" in err


def test_safe_eval_unknown_variable():
    val, err = _safe_eval("x + 1", {"a": 1})
    assert val is None
    assert err and "Unknown variable 'x'" in err


def test_safe_eval_disallowed_calls():
    # Calls and attribute access must be blocked
    val, err = _safe_eval("__import__('os').system('echo hi')", {})
    assert val is None
    assert err and ("Function calls are not allowed" in err or "Attribute access is not allowed" in err)


def test_evaluate_condition_string_ok_and_error():
    mgr = ConditionalStyleManager()
    ok, err = mgr._evaluate_condition("a > b", {"a": 5, "b": 3})
    assert err is None and ok is True

    ok, err = mgr._evaluate_condition("a > b", {})
    assert ok is False
    assert err and "Unknown variable" in err


def test_evaluate_condition_modes_on_off_range():
    mgr = ConditionalStyleManager()

    # ON mode
    cond = {
        "mode": TriggerMode.ON.value,
        "operand1": {"source": "tag", "value": {"tag_name": "X"}},
    }
    ok, err = mgr._evaluate_condition(cond, {"X": 1})
    assert err is None and ok is True

    ok, err = mgr._evaluate_condition(cond, {})
    assert ok is False and err and "operand1" in err

    # RANGE equality
    cond = {
        "mode": TriggerMode.RANGE.value,
        "operand1": {"source": "tag", "value": {"tag_name": "Y"}},
        "operator": "==",
        "operand2": {"source": "constant", "value": 10},
    }
    ok, err = mgr._evaluate_condition(cond, {"Y": 10})
    assert err is None and ok is True

    # RANGE between
    cond_between = {
        "mode": TriggerMode.RANGE.value,
        "operand1": {"source": "tag", "value": {"tag_name": "Z"}},
        "operator": "between",
        "lower_bound": {"source": "constant", "value": 2},
        "upper_bound": {"source": "constant", "value": 5},
    }
    ok, err = mgr._evaluate_condition(cond_between, {"Z": 3})
    assert err is None and ok is True

