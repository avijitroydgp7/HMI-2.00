"""Default button style helpers backed by :mod:`services.style_data_service`."""

from __future__ import annotations

from collections import OrderedDict
from typing import Dict, List, OrderedDict as _OrderedDictType

from services.style_data_service import style_data_service

# Ensure the built in default style is present (service adds it on
# initialization, but calling ``get_default_style`` here documents the
# dependency explicitly.)
style_data_service.get_default_style()


def get_style_groups() -> "_OrderedDictType[str, List[Dict]]":
    """Return grouped styles (single default group)."""
    return OrderedDict([("Default", style_data_service.get_all_styles())])


def get_all_styles() -> List[Dict]:
    """Return a flat list of available styles."""
    return style_data_service.get_all_styles()


def get_style_by_id(style_id: str) -> Dict:
    """Find a style entry by ID. Falls back to the Qt default."""
    return style_data_service.get_style(style_id) or style_data_service.get_default_style()
