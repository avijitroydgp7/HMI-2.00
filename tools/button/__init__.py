"""Button tool package.

This package consolidates all button-related code:
- `button.py` with default properties helpers
- `conditional_style.py` for conditional styles
- `button_properties_dialog.py` for the properties dialog
- `actions/` for button action dialogs and helpers

Re-export key helpers so existing imports `from tools import button` keep working.
"""

from .button import (
    DEFAULT_PROPERTIES,
    get_default_properties,
    set_default_properties,
)

__all__ = [
    "DEFAULT_PROPERTIES",
    "get_default_properties",
    "set_default_properties",
]

