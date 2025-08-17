# tools/scale.py
"""Default properties for the scale/ruler tool."""

import copy

DEFAULT_PROPERTIES = {
    "orientation": "horizontal",  # default orientation
    "length": 100,  # default length in pixels
    "thickness": 20,  # default thickness in pixels
    "major_ticks": 10,  # number of major divisions
    "minor_ticks": 5,  # number of minor ticks per major division
    "tick_spacing": 10,  # measurement units between major ticks
    "units": "mm",  # measurement units label
    "color": "#000000",  # tick and line color
}


def get_default_properties():
    """Return a copy of the default scale properties."""
    return copy.deepcopy(DEFAULT_PROPERTIES)


def set_default_properties(props):
    """Update the default scale properties."""
    global DEFAULT_PROPERTIES
    DEFAULT_PROPERTIES = copy.deepcopy(props)