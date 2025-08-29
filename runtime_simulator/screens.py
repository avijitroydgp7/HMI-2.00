from __future__ import annotations

from typing import Dict, Any

from .data_manager import DataManager


class ScreenRuntime:
    """
    Placeholder for runtime screen management.

    Maps serialized screen definitions to runtime-renderable views.
    """

    def __init__(self, data_mgr: DataManager):
        self.data_mgr = data_mgr
        self._screens: Dict[str, Dict[str, Any]] = {}

    def initialize(self, screens: Dict[str, Any]):
        self._screens = screens or {}

    def get_screen_ids(self):
        return list(self._screens.keys())

