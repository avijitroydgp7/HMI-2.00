from PyQt6.QtCore import QObject, pyqtSignal
import uuid
import copy
from typing import Dict, Any, List


class CommentDataService(QObject):
    """Stores comment groups and their comment entries."""

    comment_group_list_changed = pyqtSignal()
    comments_changed = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._groups: Dict[str, Dict[str, Any]] = {}
        self._number_index: Dict[str, str] = {}
        self._name_index: Dict[str, str] = {}

    # --- Group management -------------------------------------------------
    def clear_all(self) -> None:
        self._groups.clear()
        self._number_index.clear()
        self._name_index.clear()
        self.comment_group_list_changed.emit()

    def get_all_groups(self) -> Dict[str, Dict[str, Any]]:
        return self._groups

    def get_group(self, group_id: str) -> Dict[str, Any] | None:
        return self._groups.get(group_id)

    def is_group_number_unique(self, number: str) -> bool:
        return number not in self._number_index

    def is_group_name_unique(self, name: str) -> bool:
        return name not in self._name_index

    def _perform_add_group(self, group_data: Dict[str, Any], group_id: str | None = None) -> str:
        gid = group_id or str(uuid.uuid4())
        data = copy.deepcopy(group_data)
        data['id'] = gid
        data.setdefault('columns', ["Comment"])
        data.setdefault('comments', [])
        data.setdefault('excel', {})
        self._groups[gid] = data
        number = data.get('number', '')
        if number:
            self._number_index[number] = gid
        name = data.get('name', '')
        if name:
            self._name_index[name] = gid
        return gid

    def add_group(self, number: str, name: str) -> str:
        group_id = self._perform_add_group({
            "number": number,
            "name": name,
            "columns": ["Comment"],
            "comments": [],
            "excel": {},
        })
        self.comment_group_list_changed.emit()
        return group_id

    def _perform_remove_group(self, group_id: str) -> Dict[str, Any] | None:
        if group_id in self._groups:
            group_data = self._groups.pop(group_id)
            number = group_data.get('number', '')
            if number in self._number_index:
                del self._number_index[number]
            name = group_data.get('name', '')
            if name in self._name_index:
                del self._name_index[name]
            return group_data
        return None

    def remove_group(self, group_id: str) -> Dict[str, Any] | None:
        """Remove a comment group and return its data."""
        group_data = self._perform_remove_group(group_id)
        if group_data:
            self.comment_group_list_changed.emit()
        return group_data

    def _perform_rename_group(self, group_id: str, new_name: str, new_number: str) -> bool:
        if group_id in self._groups:
            old_name = self._groups[group_id].get('name', '')
            old_number = self._groups[group_id].get('number', '')
            if new_number != old_number and not self.is_group_number_unique(new_number):
                return False
            if new_name != old_name and not self.is_group_name_unique(new_name):
                return False
            self._groups[group_id]['name'] = new_name
            self._groups[group_id]['number'] = new_number
            if old_number in self._number_index:
                del self._number_index[old_number]
            self._number_index[new_number] = group_id
            if old_name in self._name_index:
                del self._name_index[old_name]
            self._name_index[new_name] = group_id
            return True
        return False

    def rename_group(self, group_id: str, new_name: str, new_number: str) -> bool:
        """Rename a comment group."""
        result = self._perform_rename_group(group_id, new_name, new_number)
        if result:
            self.comment_group_list_changed.emit()
        return result

    # --- Comment management -----------------------------------------------
    def update_comments(
        self, group_id: str, comments: List[List[str]], columns: List[str] | None = None
    ) -> None:
        if group_id in self._groups:
            self._groups[group_id]["comments"] = comments
            if columns is not None:
                self._groups[group_id]["columns"] = columns
            self.comments_changed.emit(group_id)

    # --- Serialization ----------------------------------------------------
    def serialize_for_project(self) -> Dict[str, Any]:
        return {"comment_groups": self._groups}

    def load_from_project(self, project_data: Dict[str, Any]) -> None:
        self.clear_all()
        groups = project_data.get("comment_groups", {})
        for g in groups.values():
            comments = g.get("comments", [])
            if comments and isinstance(comments[0], str):
                g["comments"] = [[c] for c in comments]
            g.setdefault("columns", ["Comment"])
            g.setdefault("excel", {})
        self._groups = groups
        self._number_index = {
            g.get("number", ""): gid for gid, g in groups.items() if g.get("number")
        }
        self._name_index = {
            g.get("name", ""): gid for gid, g in groups.items() if g.get("name")
        }
        self.comment_group_list_changed.emit()


comment_data_service = CommentDataService()