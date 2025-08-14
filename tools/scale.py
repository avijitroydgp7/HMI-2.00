# tools/scale.py
# Defines default properties for a scale/ruler component.


def get_default_properties():
    """Return default properties for a new scale item."""
    return {
        "orientation": "horizontal",  # default orientation
        "length": 100,                 # default length in pixels
        "thickness": 20,               # default thickness in pixels
        "major_ticks": 10,             # number of major divisions
        "minor_ticks": 5,              # number of minor ticks per major division
        "tick_spacing": 10,            # measurement units between major ticks
        "units": "mm",                # measurement units label
        "color": "#000000",           # tick and line color
    }