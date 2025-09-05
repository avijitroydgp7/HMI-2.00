from __future__ import annotations

from dataclasses import dataclass, field
import copy
from typing import Any, Callable, Dict, List, Optional, Union

from tools.button.actions.constants import TriggerMode
from services.style_data_service import style_data_service
from ..style_properties import StyleProperties


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
    """Return the list of available button style definitions."""
    return style_data_service.get_all_styles()


def get_style_by_id(style_id: str) -> Dict[str, Any]:
    """Return a style definition by its unique ID."""
    return style_data_service.get_style(style_id) or style_data_service.get_default_style()


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
    properties: StyleProperties = field(default_factory=StyleProperties)
    tooltip: str = ""
    hover_properties: StyleProperties = field(default_factory=StyleProperties)
    pressed_properties: StyleProperties = field(default_factory=StyleProperties)
    disabled_properties: StyleProperties = field(default_factory=StyleProperties)
    animation: AnimationProperties = field(default_factory=AnimationProperties)
    style_sheet: str = ""

    def to_dict(self) -> Dict[str, Any]:
        cond = copy.deepcopy(self.condition_data)
        return {
            "style_id": self.style_id,
            "condition": self.condition if isinstance(self.condition, str) else None,
            "condition_data": cond,
            "tooltip": self.tooltip,
            "properties": self.properties.to_dict(),
            "hover_properties": self.hover_properties.to_dict(),
            "pressed_properties": self.pressed_properties.to_dict(),
            "disabled_properties": self.disabled_properties.to_dict(),
            "animation": self.animation.to_dict(),
            "style_sheet": self.style_sheet,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConditionalStyle":
        props = data.get("properties", {})
        hover = data.get("hover_properties", {})
        pressed = data.get("pressed_properties", {})
        disabled = data.get("disabled_properties", {})
        # Backwards compatibility for legacy icon placement
        if "icon" in data and "icon" not in props:
            props = dict(props)
            props["icon"] = data.get("icon")
        if "hover_icon" in data and "icon" not in hover:
            hover = dict(hover)
            hover["icon"] = data.get("hover_icon")
        if "pressed_icon" in data and "icon" not in pressed:
            pressed = dict(pressed)
            pressed["icon"] = data.get("pressed_icon")
        if "disabled_icon" in data and "icon" not in disabled:
            disabled = dict(disabled)
            disabled["icon"] = data.get("disabled_icon")
        style = cls(
            style_id=data.get("style_id", ""),
            condition=data.get("condition"),
            tooltip=data.get("tooltip", ""),
            properties=StyleProperties.from_dict(props),
            hover_properties=StyleProperties.from_dict(hover),
            pressed_properties=StyleProperties.from_dict(pressed),
            disabled_properties=StyleProperties.from_dict(disabled),
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
