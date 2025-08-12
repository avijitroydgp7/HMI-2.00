# main.py
# Main entry point for the HMI Designer application.

import sys
import os
from PyQt6.QtWidgets import QApplication
from main_window import MainWindow

def main():
    """
    Initializes the QApplication, sets up services, creates the main window,
    and starts the event loop.
    """
    app = QApplication(sys.argv)

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
