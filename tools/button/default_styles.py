"""Default button style catalog limited to Qt built-in properties.

This simplified module exposes a single style describing the appearance of a
standard Qt ``QPushButton``. The previous implementation provided a large
catalog of material-inspired palettes and shapes, but that introduced a
third-party look and feel. For conditional styles we now rely solely on Qt's
own button properties so applications can remain consistent with the platform
theme.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Dict, List, OrderedDict as _OrderedDictType

# ---------------------------------------------------------------------------
# Single default style definition
# ---------------------------------------------------------------------------

_QT_DEFAULT_STYLE: Dict = {
    "id": "qt_default",
    "name": "Qt Default",
    "properties": {
        # Basic QPushButton attributes; additional keys are ignored by Qt when
        # left empty. Colors roughly match the palette of the Fusion style.
        "shape_style": "Flat",
        "background_type": "Solid",
        "background_color": "#f0f0f0",
        "text_color": "#000000",
        "border_radius": 4,
        "border_width": 1,
        "border_style": "solid",
        "border_color": "#b3b3b3",
    },
    "hover_properties": {
        "background_color": "#e0e0e0",
        "text_color": "#000000",
    },
}

STYLE_GROUPS: _OrderedDictType[str, List[Dict]] = OrderedDict(
    [("Default", [_QT_DEFAULT_STYLE])]
)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_style_groups() -> "_OrderedDictType[str, List[Dict]]":
    """Return grouped default styles (only Qt defaults)."""
    return STYLE_GROUPS


def get_all_styles() -> List[Dict]:
    """Return a flat list of available styles."""
    return list(STYLE_GROUPS["Default"])


def get_style_by_id(style_id: str) -> Dict:
    """Find a style entry by ID. Falls back to the Qt default."""
    for s in get_all_styles():
        if s.get("id") == style_id:
            return s
    return _QT_DEFAULT_STYLE

