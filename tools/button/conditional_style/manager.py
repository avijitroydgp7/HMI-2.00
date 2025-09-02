from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from PyQt6.QtCore import QObject, pyqtSignal

from tools.button.actions.constants import TriggerMode
from .models import ConditionalStyle
from .safe_eval import _safe_eval

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ConditionalStyleManager(QObject):
    """Manages conditional styles for buttons"""

    condition_error = pyqtSignal(str)
    parent: Optional[QObject] = None
    conditional_styles: List[ConditionalStyle] = field(default_factory=list)
    default_style: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        QObject.__init__(self, self.parent)

    def _generate_unique_style_id(self, base_id: str) -> str:
        existing = {s.style_id for s in self.conditional_styles}
        base = base_id or "style"
        if base != "style" and base not in existing:
            return base
        suffix = 1
        candidate = f"{base}_{suffix}"
        while candidate in existing:
            suffix += 1
            candidate = f"{base}_{suffix}"
        return candidate

    def add_style(self, style: ConditionalStyle):
        base_id = style.style_id or "style"
        style.style_id = self._generate_unique_style_id(base_id)
        self.conditional_styles.append(style)

    def remove_style(self, index: int):
        if 0 <= index < len(self.conditional_styles):
            del self.conditional_styles[index]

    def update_style(self, index: int, style: ConditionalStyle):
        if 0 <= index < len(self.conditional_styles):
            self.conditional_styles[index] = style

    def get_active_style(
        self, tag_values: Optional[Dict[str, Any]] = None, state: Optional[str] = None
    ) -> Dict[str, Any]:
        tag_values = tag_values or {}
        for style in self.conditional_styles:
            cond_cfg = getattr(style, "condition_data", {"mode": TriggerMode.ORDINARY.value})
            cond = style.condition
            condition = (
                cond_cfg
                if cond_cfg.get("mode", TriggerMode.ORDINARY.value)
                != TriggerMode.ORDINARY.value
                else cond
            )
            match, err = self._evaluate_condition(condition, tag_values)
            if err:
                try:
                    type(self).condition_error.emit(err)
                except Exception:
                    pass
                logger.warning("Condition evaluation error: %s", err)
            if match:
                props = dict(style.properties)
                if state == "hover" and style.hover_icon:
                    props["icon"] = style.hover_icon
                else:
                    props["icon"] = style.icon
                if state:
                    props.update(getattr(style, f"{state}_properties", {}))
                if style.tooltip:
                    props["tooltip"] = style.tooltip
                return props
        return dict(self.default_style)

    def _evaluate_condition(
        self, condition: Any, tag_values: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        if condition is None:
            return True, None

        if isinstance(condition, dict):
            cfg = condition
            mode = cfg.get("mode", TriggerMode.ORDINARY.value)
            if mode == TriggerMode.ORDINARY.value:
                return True, None
            if mode in (TriggerMode.ON.value, TriggerMode.OFF.value):
                op1 = cfg.get("operand1", cfg.get("tag"))
                tag_val = self._extract_value(op1, tag_values)
                if tag_val is None:
                    return False, "ON/OFF condition: operand1 tag value not found"
                return (
                    bool(tag_val) if mode == TriggerMode.ON.value else not bool(tag_val)
                ), None
            if mode == TriggerMode.RANGE.value:
                op1 = cfg.get("operand1", cfg.get("tag"))
                tag_val = self._extract_value(op1, tag_values)
                if tag_val is None:
                    return False, "RANGE condition: operand1 tag value not found"
                operator = cfg.get("operator", "==")
                if operator in ["between", "outside"]:
                    lower = self._extract_value(
                        cfg.get("lower_bound", cfg.get("lower")), tag_values
                    )
                    upper = self._extract_value(
                        cfg.get("upper_bound", cfg.get("upper")), tag_values
                    )
                    try:
                        if operator == "between":
                            return (lower <= tag_val <= upper), None
                        else:
                            return (tag_val < lower or tag_val > upper), None
                    except Exception as exc:
                        return False, f"RANGE condition error: {exc}"
                else:
                    operand = self._extract_value(
                        cfg.get("operand2", cfg.get("operand")), tag_values
                    )
                    if operand is None:
                        return False, "RANGE condition: operand2 value not found"
                    try:
                        if operator == "==":
                            return (tag_val == operand), None
                        if operator == "!=":
                            return (tag_val != operand), None
                        if operator == ">":
                            return (tag_val > operand), None
                        if operator == ">=":
                            return (tag_val >= operand), None
                        if operator == "<":
                            return (tag_val < operand), None
                        if operator == "<=":
                            return (tag_val <= operand), None
                    except Exception as exc:
                        return False, f"RANGE comparison error: {exc}"
                    return False, f"Unsupported operator: {operator}"
            return False, f"Unsupported mode: {mode}"

        if callable(condition):
            try:
                return bool(condition(tag_values)), None
            except Exception as exc:
                return False, f"Callable condition error: {exc}"

        if isinstance(condition, str):
            val, err = _safe_eval(condition, tag_values)
            if err:
                return False, f"Expression error: {err}"
            return bool(val), None

        try:
            return bool(condition), None
        except Exception as exc:
            return False, f"Invalid condition type: {exc}"

    def _extract_value(self, data: Optional[Dict[str, Any]], tag_values: Dict[str, Any]):
        if not data:
            return None
        if "source" in data:
            source = data.get("source")
            value = data.get("value")
        else:
            main = data.get("main_tag", {})
            source = main.get("source")
            value = main.get("value")
        if source == "constant":
            try:
                return float(value)
            except Exception:
                return None
        if source == "tag" and isinstance(value, dict):
            return tag_values.get(value.get("tag_name"))
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conditional_styles": [
                style.to_dict() for style in self.conditional_styles
            ],
            "default_style": self.default_style,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConditionalStyleManager":
        manager = cls()
        manager.conditional_styles = [
            ConditionalStyle.from_dict(style_data)
            for style_data in data.get("conditional_styles", [])
        ]
        manager.default_style = data.get("default_style", {})
        return manager
