"""Default properties and helpers for the button tool."""

import copy

from . import button_styles

_default_style = button_styles.get_style_by_id("default_rounded")
DEFAULT_PROPERTIES = {
    "label": "Button",
    "size": {"width": 100, "height": 40},
    "style_id": _default_style["id"],
    **_default_style["properties"],
}


def get_default_properties():
    """Return a copy of the current default button properties."""
    return copy.deepcopy(DEFAULT_PROPERTIES)


def set_default_properties(props):
    """Update the default button properties."""
    global DEFAULT_PROPERTIES
    DEFAULT_PROPERTIES = copy.deepcopy(props)