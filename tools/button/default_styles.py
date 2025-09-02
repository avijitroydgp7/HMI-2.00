"""Minimal set of built-in button styles.

This project previously exposed a catalog of decorative button styles that
mirrored various Material-like themes.  For environments that require only the
standard Qt appearance, the catalog is reduced to a single entry representing
Qt's default button look.  Consumers querying this module receive only that
style, ensuring no third‑party styling is applied.
"""

from collections import OrderedDict
from typing import Dict, List, OrderedDict as _OrderedDictType

# Only expose Qt's default push button style.  No colors, gradients or other
# customisations are defined so the native QStyle implementation handles the
# rendering entirely.
STYLE_GROUPS: "_OrderedDictType[str, List[Dict]]" = OrderedDict(
    {
        "Qt": [
            {
                "id": "qt_default",
                "name": "Qt Default",
                "properties": {},
                "hover_properties": {},
            }
        ]
    }
)


def get_style_groups() -> "_OrderedDictType[str, List[Dict]]":
    """Return grouped default styles.

    Only the native Qt style group is provided to avoid any external styling
    dependencies.
    """

    return STYLE_GROUPS


def get_all_styles() -> List[Dict]:
    """Return a flat list of all available styles."""

    return [style for group in STYLE_GROUPS.values() for style in group]


def get_style_by_id(style_id: str) -> Dict:
    """Lookup a style definition by its unique ID.

    Falls back to the first (and only) style when an unknown ID is supplied.
    """

    for style in get_all_styles():
        if style.get("id") == style_id:
            return style
    return get_all_styles()[0]

