# main_window/project_actions.py
import os
import copy
import sys
import subprocess
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QApplication
from PyQt6.QtCore import QThreadPool, Qt
from services.project_service import project_service
from services.command_history_service import command_history_service
from services.commands import UpdateProjectInfoCommand
from dialogs import ProjectInfoDialog
from services.settings_service import settings_service

def new_project(win):
    """Handles the 'New Project' action, now with UI logic."""
    from . import tabs
    if not prompt_to_save_if_dirty(win):
        return
    
    project_service.new_project()
    tabs._close_all_tabs(win)

def open_project(win):
    """Handles the 'Open Project' action, now with UI logic."""
    from . import tabs
    if not prompt_to_save_if_dirty(win):
        return

    last_dir = settings_service.get_value("paths/last_project_dir", "")
    file_path, _ = QFileDialog.getOpenFileName(win, "Open Project", last_dir, "HMI Project Files (*.hmi)")
    
    if file_path:
        _load_project_async_ui(win, file_path)

def load_project(win, path):
    """Loads a specific project file, used for command-line loading."""
    _load_project_async_ui(win, path)

def save_project(win):
    """Handles the 'Save Project' action, now with UI logic."""
    if not project_service.is_project_open() or project_service.project_file_path == "New Project":
        return save_project_as(win)

    return _save_project_async_ui(win, project_service.project_file_path)

def save_project_as(win):
    """Handles the 'Save Project As' action, now with UI logic."""
    if not project_service.is_project_open():
        return False

    last_dir = settings_service.get_value("paths/last_project_dir", "")
    file_path, _ = QFileDialog.getSaveFileName(win, "Save Project As", last_dir, "HMI Project Files (*.hmi)")
    
    if file_path:
        return _save_project_async_ui(win, file_path)
    return False

def prompt_to_save_if_dirty(win):
    """Prompts the user to save if the project has unsaved changes."""
    if not project_service.is_dirty:
        return True
    
    msg_box = QMessageBox(win)
    msg_box.setWindowTitle("Unsaved Changes")
    msg_box.setText("The current project has been modified.\nDo you want to save your changes?")
    msg_box.setStandardButtons(
        QMessageBox.StandardButton.Save
        | QMessageBox.StandardButton.Discard
        | QMessageBox.StandardButton.Cancel
    )

    reply = msg_box.exec()

    if reply == QMessageBox.StandardButton.Save:
        return save_project(win)
    if reply == QMessageBox.StandardButton.Cancel:
        return False
    return True

def update_window_title(win):
    title = "HMI Designer"
    file_name = "New Project"
    if project_service.is_project_open() and project_service.project_file_path:
        file_name = os.path.basename(project_service.project_file_path)
    elif not project_service.is_project_open():
        file_name = "No Project"
    dirty_marker = " *" if project_service.is_dirty else ""
    win.setWindowTitle(f"{title} - {file_name}{dirty_marker}")
    
def edit_project_info(win):
    old_info_full = project_service.get_project_info()
    dialog = ProjectInfoDialog(old_info_full, win)
    if dialog.exec():
        new_info_partial = dialog.get_data()
        new_info_full = copy.deepcopy(old_info_full)
        new_info_full.update(new_info_partial)
        if new_info_full != old_info_full:
            command = UpdateProjectInfoCommand(new_info_full, old_info_full)
            command_history_service.add_command(command)


def run_simulator(win):
    """Launch the runtime simulator in a separate process/window.

    Ensures the project is saved, then spawns:
        python runtime_simulator/main.py <project_path>
    """
    # Require an open project
    if not project_service.is_project_open():
        QMessageBox.information(win, "Run Simulator", "Open or create a project first.")
        return

    # Prompt to save unsaved changes
    if not prompt_to_save_if_dirty(win):
        return

    # If still not persisted, force Save As
    project_path = project_service.project_file_path
    if not project_path or project_path == "New Project":
        if not save_project_as(win):
            return
        project_path = project_service.project_file_path

    # Spawn runtime simulator as a separate process via -m for reliable imports
    cmd = [sys.executable, "-m", "runtime_simulator.main", project_path]
    try:
        # Start detached; do not block the designer
        subprocess.Popen(cmd, cwd=os.getcwd())
    except Exception as e:
        msg_box = QMessageBox(win)
        msg_box.setWindowTitle("Error Launching Simulator")
        msg_box.setText(f"Could not start simulator:\n{e}")
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.exec()


# ------------------------ Async helpers ------------------------

def _set_busy(win, text: str):
    try:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    except Exception:
        pass
    if hasattr(win, 'status_bar'):
        win.status_bar.showMessage(text)


def _clear_busy(win):
    try:
        QApplication.restoreOverrideCursor()
    except Exception:
        pass
    if hasattr(win, 'status_bar'):
        win.status_bar.clearMessage()


def _load_project_async_ui(win, file_path: str):
    from . import tabs
    current_path = project_service.project_file_path
    signals, runnable = project_service.load_project_async(file_path)

    def on_started():
        _set_busy(win, "Loading project...")

    def on_result(payload):
        try:
            pdata = payload.get('project_data')
            fpath = payload.get('file_path')
            project_service.apply_loaded_project(pdata, fpath)
            # Close tabs if project path changed
            if project_service.project_file_path != current_path:
                tabs._close_all_tabs(win)
        except Exception as e:
            _show_error(win, "Error Loading Project", f"Could not load project file:\n{e}")

    def on_error(message):
        _show_error(win, "Error Loading Project", f"Could not load project file:\n{message}")

    def on_finished():
        _clear_busy(win)
        update_window_title(win)
        tabs.update_central_widget(win)

    signals.started.connect(on_started)
    signals.result.connect(on_result)
    signals.error.connect(on_error)
    signals.finished.connect(on_finished)

    QThreadPool.globalInstance().start(runnable)


def _save_project_async_ui(win, file_path: str) -> bool:
    signals, runnable = project_service.save_project_async(file_path)

    def on_started():
        _set_busy(win, "Saving project...")

    def on_result(payload):
        try:
            fpath = payload.get('file_path')
            info = payload.get('project_info')
            project_service._commit_successful_save(fpath, info)
        except Exception as e:
            _show_error(win, "Error Saving Project", f"Could not save project file:\n{e}")

    def on_error(message):
        _show_error(win, "Error Saving Project", f"Could not save project file:\n{message}")

    def on_finished():
        _clear_busy(win)
        update_window_title(win)

    signals.started.connect(on_started)
    signals.result.connect(on_result)
    signals.error.connect(on_error)
    signals.finished.connect(on_finished)

    QThreadPool.globalInstance().start(runnable)
    return True


def _show_error(win, title: str, text: str):
    msg_box = QMessageBox(win)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.exec()
