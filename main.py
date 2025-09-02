# main.py
# Main entry point for the HMI Designer application.

import sys
import os
import logging

def main():
    """Initializes the application and starts the event loop."""
    # Defer heavy Qt imports until needed
    from PyQt6.QtCore import Qt, QThreadPool
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QPixmapCache

    # Configure rendering and high-DPI behavior before creating the application
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

    # Request desktop OpenGL so the GPU is engaged from startup
    if hasattr(Qt.ApplicationAttribute, "AA_UseDesktopOpenGL"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    QPixmapCache.setCacheLimit(256 * 1024)

    logging.basicConfig(level=logging.INFO)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Import MainWindow after QApplication has been created
    from main_window import MainWindow

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
