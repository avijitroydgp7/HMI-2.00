"""
Entry point for the Runtime Simulator executable.

Usage examples:
  - python runtime_simulator/main.py <project_file.hmi>
  - python -m runtime_simulator --project <project_file.hmi>
  - hmi-sim <project_file.hmi>   (after editable install)

If no project file is supplied, the simulator opens a file
dialog to select one, then starts the Qt event loop.
"""

from __future__ import annotations

import os
import sys
import argparse
from typing import Optional

from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt

# Support both module and script execution
try:
    # Executed as a module: python -m runtime_simulator.main
    from .simulator import SimulatorWindow  # type: ignore
except ImportError:
    # Executed as a file: python runtime_simulator/main.py
    # Ensure the repo root (parent of this dir) is on sys.path
    _HERE = os.path.dirname(__file__)
    _ROOT = os.path.dirname(_HERE)
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    from runtime_simulator.simulator import SimulatorWindow  # type: ignore


def _resolve_project_path(arg: Optional[str]) -> Optional[str]:
    if arg and os.path.exists(arg):
        return arg
    if arg:
        # Warn in case a wrong path was provided
        print(f"[runtime] Project file not found: {arg}", file=sys.stderr)
    # Allow interactive selection when launched directly
    file_path, _ = QFileDialog.getOpenFileName(
        None,
        "Open HMI Project",
        "",
        "HMI Project Files (*.hmi)"
    )
    return file_path or None


def main(argv: list[str] | None = None) -> int:
    # Prepare argv for Qt and argparse
    raw_argv = list(sys.argv if argv is None else argv)

    # Create the Qt application up-front so we can show dialogs if needed
    if hasattr(Qt.ApplicationAttribute, "AA_UseDesktopOpenGL"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)

    app = QApplication(raw_argv)
    app.setStyle("Fusion")

    # CLI parsing
    parser = argparse.ArgumentParser(
        prog="hmi-sim",
        description="Run the HMI Runtime Simulator on a .hmi project (JSON).",
    )
    parser.add_argument(
        "project",
        nargs="?",
        help="Path to the .hmi project file (JSON)",
    )
    parser.add_argument(
        "-p",
        "--project",
        dest="project_opt",
        help="Path to the .hmi project file (JSON)",
    )

    args = parser.parse_args(raw_argv[1:])
    arg_path = args.project_opt or args.project

    # Resolve project file (argument or file dialog)
    project_path = _resolve_project_path(arg_path)
    if not project_path:
        # Nothing to load — exit cleanly
        return 2

    # Construct the simulator window (it loads project via shared services)
    try:
        win = SimulatorWindow(project_path)
    except Exception as e:
        QMessageBox.critical(None, "Invalid Project", f"Could not load project:\n{e}")
        return 3
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
