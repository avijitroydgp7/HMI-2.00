"""Default properties and helpers for the button tool."""

import copy

from tools.button.conditional_style import get_style_by_id

_default_style = get_style_by_id("default_rounded")
DEFAULT_PROPERTIES = {
    "label": "Button",
    "size": {"width": 100, "height": 40},
    "style_id": _default_style["id"],
    **_default_style["properties"],
}
if "hover_properties" in _default_style:
    DEFAULT_PROPERTIES["hover_properties"] = copy.deepcopy(
        _default_style["hover_properties"]
    )
if _default_style.get("icon"):
    DEFAULT_PROPERTIES["icon"] = _default_style["icon"]
if _default_style.get("hover_icon"):
    DEFAULT_PROPERTIES["hover_icon"] = _default_style["hover_icon"]


def get_default_properties():
    """Return a copy of the current default button properties."""
    return copy.deepcopy(DEFAULT_PROPERTIES)


def set_default_properties(props):
    """Update the default button properties."""
    global DEFAULT_PROPERTIES
    DEFAULT_PROPERTIES = copy.deepcopy(props)
