from PyQt6.QtCore import QObject, pyqtSignal
import uuid
from typing import Dict, Any, List


class CommentDataService(QObject):
    """Stores comment groups and their comment entries."""

    comment_group_list_changed = pyqtSignal()
    comments_changed = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._groups: Dict[str, Dict[str, Any]] = {}
        self._number_index: Dict[str, str] = {}

    # --- Group management -------------------------------------------------
    def clear_all(self) -> None:
        self._groups.clear()
        self._number_index.clear()
        self.comment_group_list_changed.emit()

    def get_all_groups(self) -> Dict[str, Dict[str, Any]]:
        return self._groups

    def get_group(self, group_id: str) -> Dict[str, Any] | None:
        return self._groups.get(group_id)

    def is_group_number_unique(self, number: str) -> bool:
        return number not in self._number_index

    def add_group(self, number: str, name: str) -> str:
        group_id = str(uuid.uuid4())
        self._groups[group_id] = {
            "id": group_id,
            "number": number,
            "name": name,
            "columns": ["Comment"],
            "comments": [],
            "excel": {},
        }
        self._number_index[number] = group_id
        self.comment_group_list_changed.emit()
        return group_id

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
        self.comment_group_list_changed.emit()


comment_data_service = CommentDataService()