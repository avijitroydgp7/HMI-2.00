# main.py
# Main entry point for the HMI Designer application.

import sys
import os
import logging
from PyQt6.QtCore import Qt, QThreadPool
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmapCache
from main_window import MainWindow

def main():
    """
    Initializes the QApplication, sets up services, creates the main window,
    and starts the event loop.
    """
    # Configure high-DPI behavior and pixmap cache before creating the application
    # Opt in to high-DPI pixmaps when the attribute exists (Qt5)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

    # Always use pass-through rounding for scale factors
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Increase pixmap cache size (in KB)
    QPixmapCache.setCacheLimit(256 * 1024)

    # Initialize logging
    logging.basicConfig(level=logging.INFO)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Attach a global thread pool to the application
    app.thread_pool = QThreadPool.globalInstance()
    app.thread_pool.setMaxThreadCount(os.cpu_count() or 1)

    # Check for a project file passed as a command-line argument
    initial_project = None
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
        if os.path.exists(project_path):
            initial_project = project_path
        else:
            print(f"Warning: Project file not found at '{project_path}'")

    # Create and show the main window
    main_win = MainWindow(initial_project_path=initial_project)
    main_win.show()

    # Start the application event loop
    sys.exit(app.exec())

if __name__ == '__main__':
    main()