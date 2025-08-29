from __future__ import annotations

import os
from typing import Any, Dict

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QStatusBar,
)

from .data_manager import DataManager
from .screens import ScreenRuntime
from services.serialization import load_from_file
from services.screen_data_service import screen_service


class SimulatorWindow(QMainWindow):
    """
    Minimal runtime simulator window.

    Loads a project JSON and prepares the runtime managers. This is a scaffold
    to be expanded with actual rendering and interaction logic.
    """

    def __init__(self, project_path: str):
        super().__init__()
        self.project_path = project_path
        self.project: Dict[str, Any] = {}
        self.data_mgr = DataManager()
        self.screen_rt = ScreenRuntime(self.data_mgr)

        self.setWindowTitle(f"HMI Runtime Simulator - {os.path.basename(project_path)}")
        self.resize(1024, 640)

        # UI scaffold
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        self.info_label = QLabel("Runtime simulator is running.\nProject: …", self)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.info_label)
        self.setCentralWidget(central)

        sb = QStatusBar(self)
        self.setStatusBar(sb)

        self._load_project()

    def _load_project(self):
        # Load via shared services to ensure identical schema handling
        self.project = load_from_file(self.project_path)

        # Initialize data manager from shared tag service/state
        self.data_mgr.initialize_from_services()

        # Prepare screens runtime from shared screen service/state
        screens = screen_service.get_all_screens()
        self.screen_rt.initialize(screens)

        # Derive counts for info
        tag_db = self.project.get("tag_databases", {}) or {}
        tag_count = sum(len((db or {}).get("tags", []) or []) for db in tag_db.values())
        scr_count = len(screens or {})

        self.info_label.setText(
            f"Runtime simulator is running.\n"
            f"Project: {os.path.basename(self.project_path)}\n"
            f"Tags: {tag_count} | Screens: {scr_count}"
        )
