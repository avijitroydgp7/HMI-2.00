"""Button tool package.

This package consolidates all button-related code:
- `button.py` with default properties helpers
- `conditional_style/` package for conditional styles
- `button_properties_dialog.py` for the properties dialog
- `actions/` for button action dialogs and helpers

Re-export key helpers so existing imports `from tools import button` keep working.
"""


def __getattr__(name):
    if name in {
        "DEFAULT_PROPERTIES",
        "get_default_properties",
        "set_default_properties",
    }:
        from .button import (
            DEFAULT_PROPERTIES,
            get_default_properties,
            set_default_properties,
        )

        return {
            "DEFAULT_PROPERTIES": DEFAULT_PROPERTIES,
            "get_default_properties": get_default_properties,
            "set_default_properties": set_default_properties,
        }[name]
    raise AttributeError(name)


__all__ = [
    "DEFAULT_PROPERTIES",
    "get_default_properties",
    "set_default_properties",
]

