from __future__ import annotations

from dataclasses import MISSING, dataclass, field, fields
import copy
from typing import Any, Callable, Dict, Iterable, List, Optional, Union

from tools.button.actions.constants import TriggerMode
from services.style_data_service import style_data_service


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
class StyleProperties:
    """Encapsulates the visual properties for a button state."""

    component_type: str = "Standard Button"
    shape_style: str = "Flat"
    background_type: str = "Solid"
    background_color: str = ""
    text_color: str = ""
    border_radius: int = 0
    border_width: int = 0
    border_style: str = "solid"
    border_color: str = ""
    font_family: str = ""
    font_size: int = 0
    bold: bool = False
    italic: bool = False
    underline: bool = False
    text_type: str = "Text"
    text_value: str = ""
    comment_ref: Dict[str, Any] = field(default_factory=dict)
    h_align: str = "center"
    v_align: str = "middle"
    offset: int = 0
    icon: str = ""
    icon_size: int = 0
    icon_align: str = "center"
    icon_color: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    # --- dict-like interface -------------------------------------------------
    def _field_names(self) -> Iterable[str]:
        return [f.name for f in fields(self) if f.name != "extra"]

    def _as_dict(self) -> Dict[str, Any]:
        data = {name: getattr(self, name) for name in self._field_names()}
        data.update(self.extra)
        return data

    def to_dict(self) -> Dict[str, Any]:
        return copy.deepcopy(self._as_dict())

    # Mapping protocol -------------------------------------------------
    def __getitem__(self, key):
        if key in self._field_names():
            return getattr(self, key)
        return self.extra[key]

    def __setitem__(self, key, value):
        if key in self._field_names():
            setattr(self, key, value)
        else:
            self.extra[key] = value

    def get(self, key, default=None):
        if key in self._field_names():
            return getattr(self, key)
        return self.extra.get(key, default)

    def update(self, other: Dict[str, Any]):
        for k, v in other.items():
            self[k] = v

    def __contains__(self, key):
        return key in self._field_names() or key in self.extra

    def __iter__(self):
        return iter(self.to_dict())

    def items(self):
        return self.to_dict().items()

    def keys(self):
        return self.to_dict().keys()

    def values(self):
        return self.to_dict().values()

    # Factory ----------------------------------------------------------
    @staticmethod
    def _normalize(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize legacy keys into the new structure."""
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
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StyleProperties":
        if not data:
            return cls()
        data = cls._normalize(dict(data))
        known = {}
        for field in fields(cls):
            if field.name == "extra":
                continue
            known[field.name] = data.pop(field.name, field.default if field.default is not MISSING else None)
        inst = cls(**known)
        inst.extra = data
        return inst


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
