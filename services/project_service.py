# services/project_service.py
import os
import json
import datetime
from typing import Tuple, Optional, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable
from services.screen_data_service import screen_service
from services.tag_data_service import tag_data_service
from services.comment_data_service import comment_data_service
from services.settings_service import settings_service

class ProjectService(QObject):
    """
    Manages all project-related operations such as creating, loading,
    and saving projects by orchestrating other data services.
    """
    project_state_changed = pyqtSignal()
    project_loaded = pyqtSignal()
    project_closed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.project_file_path = None
        self.is_dirty = False
        self.project_info = self._get_default_project_info()

    def new_project(self):
        """
        Resets the project state for a new project.
        """
        self._reset_project_state()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.project_info['creation_date'] = now
        self.project_info['modification_date'] = now
        self.project_info['save_history'] = [f"Project Created on {now}"]
        self.project_file_path = "New Project" 
        self.set_dirty(True)
        self.project_loaded.emit()
        return True

    def load_project(self, file_path: str):
        """
        Loads a project from a given file path.
        Raises exception on error.
        """
        try:
            with open(file_path, 'r') as f:
                project_data = json.load(f)
            self.apply_loaded_project(project_data, file_path)
        except (IOError, json.JSONDecodeError) as e:
            raise e

    def save_project(self, file_path: str):
        """
        Saves the current project to the specified file path.
        Raises exception on error.
        """
        try:
            # Build save payload first (main thread safe snapshot)
            project_data, new_info = self._build_project_data_for_save()
            # Perform write synchronously
            with open(file_path, 'w') as f:
                json.dump(project_data, f, indent=4)
            # Commit changes after successful write
            self._commit_successful_save(file_path, new_info)
            return True
        except IOError as e:
            raise e

    # ---------- Async support (QRunnable-based) ----------
    def load_project_async(self, file_path: str):
        """
        Prepare an async load operation.

        Returns a tuple of (signals, runnable).
        Caller should start the runnable using QThreadPool.globalInstance().start(runnable)
        and connect to the signals to handle result/error/finished.
        """
        runnable = _LoadProjectRunnable(file_path)
        return runnable.signals, runnable

    def save_project_async(self, file_path: str):
        """
        Prepare an async save operation.

        This snapshots current project data on the GUI thread and returns a runnable
        that writes it to disk off the GUI thread.

        Returns a tuple of (signals, runnable).
        """
        project_data, new_info = self._build_project_data_for_save()
        runnable = _SaveProjectRunnable(file_path, project_data, new_info)
        return runnable.signals, runnable
            
    def _get_default_project_info(self):
        return {
            "author": "", "company": "", "description": "",
            "creation_date": "N/A", "modification_date": "N/A", "save_history": []
        }
        
    def get_project_info(self):
        return self.project_info
        
    def is_project_open(self):
        return self.project_file_path is not None
        
    def set_dirty(self, dirty=True):
        if self.is_dirty != dirty:
            self.is_dirty = dirty
            self.project_state_changed.emit()
            
    def _reset_project_state(self, is_loading=False):
        from services.command_history_service import command_history_service
        if not is_loading and self.is_project_open():
             self.project_closed.emit()
        self.project_file_path = None
        self.is_dirty = False
        self.project_info = self._get_default_project_info()
        screen_service.clear_all()
        tag_data_service.clear_all()
        comment_data_service.clear_all()
        command_history_service.clear()
        
    def _perform_update_project_info(self, full_new_info):
        self.project_info = full_new_info

    # ---------- Helpers to apply results on main thread ----------
    def apply_loaded_project(self, project_data: Dict[str, Any], file_path: str):
        """Apply already-parsed project data (must be called on the GUI thread)."""
        self._reset_project_state(is_loading=True)

        self.project_info = project_data.get("project_info", self._get_default_project_info())
        screen_service.load_from_project(project_data)
        tag_data_service.load_from_project(project_data)
        comment_data_service.load_from_project(project_data)

        self.project_file_path = file_path
        self.set_dirty(False)
        settings_service.set_value("paths/last_project_dir", os.path.dirname(file_path))
        settings_service.save()
        self.project_loaded.emit()

    def _build_project_data_for_save(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Create a snapshot of the current project suitable for saving.

        Returns (project_data, updated_project_info_copy)
        """
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_info = dict(self.project_info)
        new_info['modification_date'] = now_str

        save_entry = f"Saved on {now_str}"
        history = list(new_info.get('save_history') or [])
        history.append(save_entry)
        new_info['save_history'] = history

        screen_data = screen_service.serialize_for_project()
        tag_data = tag_data_service.serialize_for_project()
        comment_data = comment_data_service.serialize_for_project()
        project_data = {
            "project_info": new_info,
            **screen_data,
            **tag_data,
            **comment_data,
        }
        return project_data, new_info

    def _commit_successful_save(self, file_path: str, updated_info: Dict[str, Any]):
        """Finalize state after a successful save (call on GUI thread)."""
        self.project_info = updated_info
        self.project_file_path = file_path
        self.set_dirty(False)
        settings_service.set_value("paths/last_project_dir", os.path.dirname(file_path))
        settings_service.save()

project_service = ProjectService()


class _WorkerSignals(QObject):
    """Signals used by background runnables."""
    started = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(object)
    finished = pyqtSignal()


class _LoadProjectRunnable(QRunnable):
    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
        self.signals = _WorkerSignals()

    def run(self):
        self.signals.started.emit()
        try:
            with open(self.file_path, 'r') as f:
                project_data = json.load(f)
            # Send both data and path; main thread applies it via project_service
            self.signals.result.emit({
                'file_path': self.file_path,
                'project_data': project_data,
            })
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()


class _SaveProjectRunnable(QRunnable):
    def __init__(self, file_path: str, project_data: Dict[str, Any], updated_info: Dict[str, Any]):
        super().__init__()
        self.file_path = file_path
        self.project_data = project_data
        self.updated_info = updated_info
        self.signals = _WorkerSignals()

    def run(self):
        self.signals.started.emit()
        try:
            # Ensure directory exists
            target_dir = os.path.dirname(self.file_path)
            if target_dir and not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
            with open(self.file_path, 'w') as f:
                json.dump(self.project_data, f, indent=4)
            self.signals.result.emit({
                'file_path': self.file_path,
                'project_info': self.updated_info,
            })
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()
