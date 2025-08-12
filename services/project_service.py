# services/project_service.py
import os
import json
import datetime
from PyQt6.QtCore import QObject, pyqtSignal
from services.screen_data_service import screen_service
from services.tag_data_service import tag_data_service
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
            
            self._reset_project_state(is_loading=True)
            
            self.project_info = project_data.get("project_info", self._get_default_project_info())
            screen_service.load_from_project(project_data)
            tag_data_service.load_from_project(project_data)

            self.project_file_path = file_path
            self.set_dirty(False)
            settings_service.set_value("paths/last_project_dir", os.path.dirname(file_path))
            settings_service.save()
            self.project_loaded.emit()
        except (IOError, json.JSONDecodeError) as e:
            raise e

    def save_project(self, file_path: str):
        """
        Saves the current project to the specified file path.
        Raises exception on error.
        """
        try:
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.project_info['modification_date'] = now_str
            
            save_entry = f"Saved on {now_str}"
            if 'save_history' not in self.project_info:
                self.project_info['save_history'] = []
            self.project_info['save_history'].append(save_entry)

            screen_data = screen_service.serialize_for_project()
            tag_data = tag_data_service.serialize_for_project()
            project_data = {
                "project_info": self.project_info,
                **screen_data, 
                **tag_data
            }

            with open(file_path, 'w') as f:
                json.dump(project_data, f, indent=4)
            
            self.project_file_path = file_path
            self.set_dirty(False)
            settings_service.set_value("paths/last_project_dir", os.path.dirname(file_path))
            settings_service.save()
            return True
        except IOError as e:
            raise e
            
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
        command_history_service.clear()
        
    def _perform_update_project_info(self, full_new_info):
        self.project_info = full_new_info

project_service = ProjectService()
