from __future__ import annotations

from dataclasses import dataclass, field
import copy
from typing import Any, Callable, Dict, List, Optional, Union

from tools.button.actions.constants import TriggerMode
from tools.button.default_styles import (
    get_all_styles as _get_all_styles,
    get_style_by_id as _get_style_by_id,
)


# Predefined gradient orientations used for visual selection
_GRADIENT_STYLES = {
    "Top to Bottom": (0, 0, 0, 1),
    "Bottom to Top": (0, 1, 0, 0),
    "Left to Right": (0, 0, 1, 0),
    "Right to Left": (1, 0, 0, 0),
    "Diagonal TL-BR": (0, 0, 1, 1),
    "Diagonal BL-TR": (0, 1, 1, 0),
}


def get_styles() -> List[Dict[str, Any]]:
    """Return the list of built-in button style definitions."""
    return _get_all_styles()


def get_style_by_id(style_id: str) -> Dict[str, Any]:
    """Return a style definition by its unique ID."""
    return _get_style_by_id(style_id)


@dataclass(slots=True)
class AnimationProperties:
    """Basic animation configuration for button styles."""

    enabled: bool = False
    type: str = "pulse"
    intensity: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "type": self.type,
            "intensity": self.intensity,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnimationProperties":
        return cls(
            enabled=data.get("enabled", False),
            type=data.get("type", "pulse"),
            intensity=data.get("intensity", 1.0),
        )


@dataclass(slots=True)
class ConditionalStyle:
    """A style that can be applied to a button."""

    style_id: str = ""
    condition: Optional[Union[str, Callable[[Dict[str, Any]], bool]]] = None
    condition_data: Dict[str, Any] = field(
        default_factory=lambda: {"mode": TriggerMode.ORDINARY.value}
    )
    # core text/style attributes
    text_type: str = "Text"
    text_value: str = ""
    comment_ref: Dict[str, Any] = field(default_factory=dict)
    font_family: str = ""
    font_size: int = 0
    bold: bool = False
    italic: bool = False
    underline: bool = False
    background_color: str = ""
    text_color: str = ""
    h_align: str = "center"
    v_align: str = "middle"
    offset: int = 0
    icon: str = ""
    hover_icon: str = ""
    # miscellaneous properties remain grouped
    properties: Dict[str, Any] = field(default_factory=dict)
    tooltip: str = ""
    hover_properties: Dict[str, Any] = field(default_factory=dict)
    animation: AnimationProperties = field(default_factory=AnimationProperties)
    style_sheet: str = ""

    @staticmethod
    def _normalize_state(props: Dict[str, Any]) -> Dict[str, Any]:
        """Return a state dictionary containing the expected keys."""
        defaults = {
            "text_type": "Text",
            "text_value": "",
            "comment_ref": {},
            "font_family": "",
            "font_size": 0,
            "bold": False,
            "italic": False,
            "underline": False,
            "background_color": "",
            "text_color": "",
            "h_align": "center",
            "v_align": "middle",
            "offset": 0,
        }
        if not props:
            return defaults.copy()

        data = dict(props)
        if "text" in data and "text_value" not in data:
            data["text_value"] = data.get("text", "")
        if data.get("text_type") == "Comment" and "comment_ref" not in data:
            data["comment_ref"] = {
                "number": data.get("comment_number", 0),
                "column": data.get("comment_column", 0),
                "row": data.get("comment_row", 0),
            }
        if "horizontal_align" in data and "h_align" not in data:
            data["h_align"] = data.get("horizontal_align")
        if "vertical_align" in data and "v_align" not in data:
            data["v_align"] = data.get("vertical_align")
        if "offset_to_frame" in data and "offset" not in data:
            data["offset"] = data.get("offset_to_frame")

        normalized = defaults.copy()
        for key in normalized.keys():
            normalized[key] = data.get(key, normalized[key])
        return normalized

    def to_dict(self) -> Dict[str, Any]:
        cond = copy.deepcopy(self.condition_data)
        return {
            "style_id": self.style_id,
            "condition": self.condition if isinstance(self.condition, str) else None,
            "condition_data": cond,
            "tooltip": self.tooltip,
            "text_type": self.text_type,
            "text_value": self.text_value,
            "comment_ref": self.comment_ref,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "bold": self.bold,
            "italic": self.italic,
            "underline": self.underline,
            "background_color": self.background_color,
            "text_color": self.text_color,
            "h_align": self.h_align,
            "v_align": self.v_align,
            "offset": self.offset,
            "icon": self.icon,
            "hover_icon": self.hover_icon,
            "properties": self.properties,
            "hover_properties": self._normalize_state(self.hover_properties),
            "animation": self.animation.to_dict(),
            "style_sheet": self.style_sheet,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConditionalStyle":
        props = data.get("properties", {})
        hover = cls._normalize_state(data.get("hover_properties", {}))
        style = cls(
            style_id=data.get("style_id", ""),
            condition=data.get("condition"),
            tooltip=data.get("tooltip", ""),
            icon=data.get("icon", data.get("svg_icon", "")),
            hover_icon=data.get("hover_icon", ""),
            text_type=data.get("text_type", props.get("text_type", "Text")),
            text_value=data.get("text_value", props.get("text", "")),
            comment_ref=data.get(
                "comment_ref",
                (
                    {
                        "number": props.get("comment_number", 0),
                        "column": props.get("comment_column", 0),
                        "row": props.get("comment_row", 0),
                    }
                    if props.get("text_type") == "Comment"
                    else {}
                ),
            ),
            font_family=data.get("font_family", props.get("font_family", "")),
            font_size=data.get("font_size", props.get("font_size", 0)),
            bold=data.get("bold", props.get("bold", False)),
            italic=data.get("italic", props.get("italic", False)),
            underline=data.get("underline", props.get("underline", False)),
            background_color=data.get(
                "background_color", props.get("background_color", "")
            ),
            text_color=data.get("text_color", props.get("text_color", "")),
            h_align=data.get("h_align", props.get("horizontal_align", "center")),
            v_align=data.get("v_align", props.get("vertical_align", "middle")),
            offset=data.get("offset", props.get("offset_to_frame", 0)),
            properties=props,
            hover_properties=hover,
            style_sheet=data.get("style_sheet", ""),
        )
        cond = data.get("condition_data", {"mode": TriggerMode.ORDINARY.value})
        if cond.get("mode") in (TriggerMode.ON.value, TriggerMode.OFF.value):
            if "operand1" not in cond and "tag" in cond:
                cond["operand1"] = cond.pop("tag")
        if cond.get("mode") == TriggerMode.RANGE.value:
            if "operand1" not in cond and "tag" in cond:
                cond["operand1"] = cond.pop("tag")
            if "operand2" not in cond and "operand" in cond:
                cond["operand2"] = cond.pop("operand")
            if "lower_bound" not in cond and "lower" in cond:
                cond["lower_bound"] = cond.pop("lower")
            if "upper_bound" not in cond and "upper" in cond:
                cond["upper_bound"] = cond.pop("upper")
            if "operator" not in cond:
                if (
                    cond.get("lower_bound") is not None
                    or cond.get("upper_bound") is not None
                ):
                    cond["operator"] = "between"
                else:
                    cond["operator"] = "=="

        if cond.get("mode") in (
            TriggerMode.ON.value,
            TriggerMode.OFF.value,
            TriggerMode.RANGE.value,
        ):
            op1 = cond.get("operand1")
            if op1 and "main_tag" not in op1 and "source" in op1:
                cond["operand1"] = {"main_tag": op1, "indices": []}
        style.condition_data = cond
        if "animation" in data:
            style.animation = AnimationProperties.from_dict(data["animation"])
        return style
