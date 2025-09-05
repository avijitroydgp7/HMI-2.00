"""Default properties and helpers for the button tool."""

import copy

from tools.button.conditional_style import get_style_by_id

_default_style = get_style_by_id("qt_default")

_base_props = copy.deepcopy(_default_style.get("properties", {}))
_hover_props = copy.deepcopy(_default_style.get("hover_properties", {}))
if _default_style.get("icon"):
    _base_props["icon"] = _default_style["icon"]
if _default_style.get("hover_icon"):
    _hover_props["icon"] = _default_style["hover_icon"]

# Set default non-zero values for icon_size and font_size
_base_props.setdefault("icon_size", 50)  # 50% of button size
_base_props.setdefault("font_size", 18)  # 18% font size
_hover_props.setdefault("icon_size", 50)
_hover_props.setdefault("font_size", 18)

DEFAULT_PROPERTIES = {
    "label": "Button",
    "size": {"width": 100, "height": 40},
    "default_style": copy.deepcopy(_base_props),
    "conditional_styles": [
        {
            "style_id": _default_style.get("id", ""),
            "properties": copy.deepcopy(_base_props),
            "hover_properties": copy.deepcopy(_hover_props),
        }
    ],
}


def get_default_properties():
    """Return a copy of the current default button properties."""
    return copy.deepcopy(DEFAULT_PROPERTIES)


def set_default_properties(props):
    """Update the default button properties."""
    global DEFAULT_PROPERTIES
    DEFAULT_PROPERTIES = copy.deepcopy(props)
