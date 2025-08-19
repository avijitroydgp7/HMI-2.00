from typing import Dict, Any, Optional
from PyQt6.QtCore import QObject, pyqtSignal

from .tag_data_service import tag_data_service


class TagService(QObject):
    """Service for managing tag values and resolving them from tag paths"""

    tag_values_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tag_values: Dict[str, Any] = {}

    def set_tag_value(self, tag_path: str, value: Any):
        """Set a tag value"""
        self._tag_values[tag_path] = value
        self.tag_values_changed.emit({tag_path: value})

    def _resolve_from_path(self, tag_path: str) -> Optional[Any]:
        """Resolve a tag value from a formatted path like ``[DB]::Tag``."""
        if not tag_path.startswith("["):
            return None
        try:
            db_part, tag_part = tag_path.split("]::")
            db_name = db_part.strip("[")
            tag_name = tag_part
        except ValueError:
            return None

        db_id = tag_data_service.find_db_id_by_name(db_name)
        if not db_id:
            return None

        tag = tag_data_service.get_tag(db_id, tag_name)
        if tag:
            return tag.get("value")
        return None

    def get_tag_value(self, tag_path: str) -> Any:
        """Get a tag value, resolving from the tag data service if needed."""
        if tag_path in self._tag_values:
            return self._tag_values.get(tag_path)
        return self._resolve_from_path(tag_path)

    def get_all_tag_values(self) -> Dict[str, Any]:
        """Get all known tag values"""
        return self._tag_values.copy()

    def update_tag_values(self, tag_values: Dict[str, Any]):
        """Update multiple tag values"""
        self._tag_values.update(tag_values)
        self.tag_values_changed.emit(tag_values)


# Global instance
tag_service = TagService()

