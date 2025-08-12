# main_window/project_actions.py
import os
import copy
from PyQt6.QtWidgets import QFileDialog
from services.project_service import project_service
from services.command_history_service import command_history_service
from services.commands import UpdateProjectInfoCommand
from dialogs import ProjectInfoDialog
from dialogs.custom_message_box import CustomMessageBox
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
        try:
            current_path = project_service.project_file_path
            project_service.load_project(file_path)
            if project_service.project_file_path != current_path:
                tabs._close_all_tabs(win)
        except Exception as e:
            msg_box = CustomMessageBox(win)
            msg_box.setWindowTitle("Error Loading Project")
            msg_box.setText(f"Could not load project file:\n{e}")
            msg_box.exec()

def load_project(win, path):
    """Loads a specific project file, used for command-line loading."""
    from . import tabs
    try:
        current_path = project_service.project_file_path
        project_service.load_project(path)
        if project_service.project_file_path != current_path:
            tabs._close_all_tabs(win)
    except Exception as e:
        print(f"ERROR: Could not load project file '{path}': {e}")

def save_project(win):
    """Handles the 'Save Project' action, now with UI logic."""
    if not project_service.is_project_open() or project_service.project_file_path == "New Project":
        return save_project_as(win)
    
    try:
        project_service.save_project(project_service.project_file_path)
        return True
    except Exception as e:
        msg_box = CustomMessageBox(win)
        msg_box.setWindowTitle("Error Saving Project")
        msg_box.setText(f"Could not save project file:\n{e}")
        msg_box.exec()
        return False

def save_project_as(win):
    """Handles the 'Save Project As' action, now with UI logic."""
    if not project_service.is_project_open():
        return False

    last_dir = settings_service.get_value("paths/last_project_dir", "")
    file_path, _ = QFileDialog.getSaveFileName(win, "Save Project As", last_dir, "HMI Project Files (*.hmi)")
    
    if file_path:
        try:
            project_service.save_project(file_path)
            return True
        except Exception as e:
            msg_box = CustomMessageBox(win)
            msg_box.setWindowTitle("Error Saving Project")
            msg_box.setText(f"Could not save project file:\n{e}")
            msg_box.exec()
    return False

def prompt_to_save_if_dirty(win):
    """Prompts the user to save if the project has unsaved changes."""
    if not project_service.is_dirty:
        return True
    
    msg_box = CustomMessageBox(win)
    msg_box.setWindowTitle("Unsaved Changes")
    msg_box.setText("The current project has been modified.\nDo you want to save your changes?")
    
    reply = msg_box.exec()

    if reply == CustomMessageBox.Save:
        return save_project(win)
    if reply == CustomMessageBox.Cancel:
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
