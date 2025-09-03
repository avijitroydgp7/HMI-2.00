from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from PyQt6.QtCore import QObject, pyqtSignal

from tools.button.actions.constants import TriggerMode
from .models import ConditionalStyle, StyleProperties
from .safe_eval import _safe_eval

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ConditionalStyleManager(QObject):
    """Manages conditional styles for buttons"""

    condition_error = pyqtSignal(str)
    parent: Optional[QObject] = None
    conditional_styles: List[ConditionalStyle] = field(default_factory=list)
    _default_style: StyleProperties = field(default_factory=StyleProperties)

    def __post_init__(self):
        QObject.__init__(self, self.parent)
        
    def renumber_styles(self) -> None:
        for idx, style in enumerate(self.conditional_styles, 1):
            style.style_id = str(idx)

    def add_style(self, style: ConditionalStyle):
        if isinstance(style.properties, dict):
            style.properties = StyleProperties.from_dict(style.properties)
        if isinstance(style.hover_properties, dict):
            style.hover_properties = StyleProperties.from_dict(style.hover_properties)
        self.conditional_styles.append(style)
        self.renumber_styles()
        self.create_default_style_properties()

    def remove_style(self, index: int):
        if 0 <= index < len(self.conditional_styles):
            del self.conditional_styles[index]
            self.renumber_styles()
            self.create_default_style_properties()

    def update_style(self, index: int, style: ConditionalStyle):
        if 0 <= index < len(self.conditional_styles):
            if isinstance(style.properties, dict):
                style.properties = StyleProperties.from_dict(style.properties)
            if isinstance(style.hover_properties, dict):
                style.hover_properties = StyleProperties.from_dict(style.hover_properties)
            self.conditional_styles[index] = style
            self.renumber_styles()
            self.create_default_style_properties()

    @property
    def default_style(self) -> StyleProperties:
        return self._default_style

    @default_style.setter
    def default_style(self, value: Union[StyleProperties, Dict[str, Any]]):
        if isinstance(value, StyleProperties):
            self._default_style = value
        else:
            self._default_style = StyleProperties.from_dict(value)
        self.create_default_style_properties()

    def create_default_style_properties(self) -> None:
        """Ensure the default style defines all keys seen in conditional styles."""
        base = (
            self._default_style.to_dict()
            if isinstance(self._default_style, StyleProperties)
            else dict(self._default_style)
        )
        keys = set(base.keys())
        for style in self.conditional_styles:
            keys.update(style.properties.keys())
            keys.update(style.hover_properties.keys())
        defaults = StyleProperties().to_dict()
        for key in keys:
            if key not in base:
                base[key] = defaults.get(key, "")
        self._default_style = StyleProperties.from_dict(base)

    def get_active_style(
        self, tag_values: Optional[Dict[str, Any]] = None, state: Optional[str] = None
    ) -> Dict[str, Any]:
        tag_values = tag_values or {}
        base = (
            self.default_style.to_dict()
            if isinstance(self.default_style, StyleProperties)
            else dict(self.default_style)
        )
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
                props = base.copy()
                props.update(style.properties.to_dict())
                if state:
                    hover = getattr(style, f"{state}_properties", StyleProperties())
                    if isinstance(hover, StyleProperties):
                        props.update(hover.to_dict())
                    elif isinstance(hover, dict):
                        props.update(hover)
                if style.tooltip:
                    props["tooltip"] = style.tooltip
                return props
        return base

    def get_style_by_index(
        self, index: int, state: Optional[str] = None
    ) -> Dict[str, Any]:
        """Return the style at ``index`` merged with the default style.

        This bypasses condition evaluation and is primarily used for style
        previews in the editor where styles are selected explicitly by their
        list index.
        """

        base = (
            self.default_style.to_dict()
            if isinstance(self.default_style, StyleProperties)
            else dict(self.default_style)
        )

        if not (0 <= index < len(self.conditional_styles)):
            return base

        style = self.conditional_styles[index]
        props = base.copy()
        props.update(style.properties.to_dict())

        if state:
            hover = getattr(style, f"{state}_properties", StyleProperties())
            if isinstance(hover, StyleProperties):
                props.update(hover.to_dict())
            elif isinstance(hover, dict):
                props.update(hover)

        if style.tooltip:
            props["tooltip"] = style.tooltip
        if style.style_sheet:
            props["style_sheet"] = style.style_sheet

        return props

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
            "default_style": self.default_style.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConditionalStyleManager":
        manager = cls()
        manager.conditional_styles = [
            ConditionalStyle.from_dict(style_data)
            for style_data in data.get("conditional_styles", [])
        ]
        manager.default_style = data.get("default_style", {})
        manager.renumber_styles()
        return manager
