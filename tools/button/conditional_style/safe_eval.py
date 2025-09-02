from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
import ast
import logging
from collections import OrderedDict

logger = logging.getLogger(__name__)

_AST_CACHE: "OrderedDict[str, ast.AST]" = OrderedDict()
_AST_CACHE_MAXSIZE = 128


def _get_parsed_ast(expr: str) -> ast.AST:
    node = _AST_CACHE.get(expr)
    if node is not None:
        _AST_CACHE.move_to_end(expr)
        return node
    node = ast.parse(expr, mode="eval")
    _AST_CACHE[expr] = node
    if len(_AST_CACHE) > _AST_CACHE_MAXSIZE:
        _AST_CACHE.popitem(last=False)
    return node


def _safe_eval(expr: str, variables: Dict[str, Any]) -> Tuple[Any, Optional[str]]:
    """Safely evaluate a small Python expression.

    Returns (value, error).  On success error is None, otherwise value is None
    and error contains a message.
    """
    try:
        tree = _get_parsed_ast(expr)
    except SyntaxError as exc:  # pragma: no cover - syntax error path
        logger.warning("Condition syntax error: %s", exc)
        return None, "Invalid expression syntax"
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Unexpected error parsing condition")
        return None, f"Parse error: {exc}"

    def _eval(node: ast.AST):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.BoolOp):
            values = [_eval(v) for v in node.values]
            if isinstance(node.op, ast.And):
                return all(values)
            if isinstance(node.op, ast.Or):
                return any(values)
            raise ValueError("Unsupported boolean operator")
        if isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.Mod):
                return left % right
            raise ValueError("Unsupported binary operator")
        if isinstance(node, ast.UnaryOp):
            operand = _eval(node.operand)
            if isinstance(node.op, ast.Not):
                return not operand
            if isinstance(node.op, ast.UAdd):
                return +operand
            if isinstance(node.op, ast.USub):
                return -operand
            raise ValueError("Unsupported unary operator")
        if isinstance(node, ast.Compare):
            left = _eval(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = _eval(comparator)
                if isinstance(op, ast.Eq):
                    if not (left == right):
                        return False
                elif isinstance(op, ast.NotEq):
                    if not (left != right):
                        return False
                elif isinstance(op, ast.Lt):
                    if not (left < right):
                        return False
                elif isinstance(op, ast.LtE):
                    if not (left <= right):
                        return False
                elif isinstance(op, ast.Gt):
                    if not (left > right):
                        return False
                elif isinstance(op, ast.GtE):
                    if not (left >= right):
                        return False
                else:  # pragma: no cover - unsupported comparisons
                    raise ValueError("Unsupported comparison operator")
                left = right
            return True
        if isinstance(node, ast.Name):
            if node.id in variables:
                return variables[node.id]
            raise ValueError(f"Unknown variable '{node.id}'")
        if isinstance(node, ast.Call):
            raise ValueError("Function calls are not allowed")
        if isinstance(node, ast.Attribute):
            raise ValueError("Attribute access is not allowed")
        if isinstance(node, ast.Constant):
            return node.value
        raise ValueError(f"Unsupported expression: {ast.dump(node)}")

    try:
        return _eval(tree), None
    except Exception as exc:
        logger.debug("Condition evaluation error for '%s': %s", expr, exc)
        return None, str(exc)
