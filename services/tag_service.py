from typing import Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal

class TagService(QObject):
    """Service for managing tag values and providing them to conditional styles"""
    tag_values_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tag_values: Dict[str, Any] = {}
    
    def set_tag_value(self, tag_path: str, value: Any):
        """Set a tag value"""
        self._tag_values[tag_path] = value
        self.tag_values_changed.emit({tag_path: value})
    
    def get_tag_value(self, tag_path: str) -> Any:
        """Get a tag value"""
        return self._tag_values.get(tag_path)
    
    def get_all_tag_values(self) -> Dict[str, Any]:
        """Get all tag values"""
        return self._tag_values.copy()
    
    def update_tag_values(self, tag_values: Dict[str, Any]):
        """Update multiple tag values"""
        self._tag_values.update(tag_values)
        self.tag_values_changed.emit(tag_values)

# Global instance
tag_service = TagService()
