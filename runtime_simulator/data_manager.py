from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
from PyQt6.QtCore import QObject, pyqtSignal

from services.tag_data_service import tag_data_service
from services.tag_service import tag_service


@dataclass(slots=True)
class Tag:
    name: str
    type: str
    value: Any


class DataManager(QObject):
    """
    Minimal tag data manager for runtime.

    Provides a signal-based interface to observe tag changes. Intended to be
    expanded with type enforcement, limits, arrays, etc.
    """

    tag_changed = pyqtSignal(str, object)

    def __init__(self):
        super().__init__()
        # Local cache keyed by tag path (e.g. "[DB]::Tag") or plain name (legacy)
        self._tags: Dict[str, Tag] = {}

    def initialize(self, tags_def: Dict[str, Any]):
        """Legacy initializer kept for backward compatibility."""
        self._tags.clear()
        for name, meta in (tags_def or {}).items():
            t = str(meta.get("type", "any"))
            init = meta.get("init")
            self._tags[name] = Tag(name=name, type=t, value=init)

    def initialize_from_services(self):
        """
        Populate initial tag values from shared services.tag_data_service.

        Uses the canonical path format "[DB_NAME]::TAG_NAME" for keys.
        """
        self._tags.clear()
        for db_id, db in (tag_data_service.get_all_tag_databases() or {}).items():
            db_name = db.get("name") or db_id
            for tag in db.get("tags", []) or []:
                name = tag.get("name")
                if not name:
                    continue
                path = f"[{db_name}]::" + name
                value = tag.get("value")
                # Data type information isn't strictly needed for runtime cache
                self._tags[path] = Tag(name=path, type=str(tag.get("data_type", "any")), value=value)

    # --- Tag access -----------------------------------------------------
    def _parse_path(self, key: str) -> Optional[Tuple[str, str]]:
        """Parse "[DB]::Tag" -> (db_name, tag_name)."""
        if not key or not key.startswith("["):
            return None
        try:
            db_part, tag = key.split("]::", 1)
            return db_part.strip("["), tag
        except ValueError:
            return None

    def _resolve_plain_to_path(self, name: str) -> Optional[str]:
        """Resolve a plain tag name to a canonical "[DB]::Tag" path.

        If multiple DBs contain the same tag name, the first one encountered
        will be returned.
        """
        for db_id, db in (tag_data_service.get_all_tag_databases() or {}).items():
            db_name = db.get("name") or db_id
            for tag in db.get("tags", []) or []:
                if tag.get("name") == name:
                    return f"[{db_name}]::" + name
        return None

    def get(self, name: str) -> Any:
        # Canonical path lookup uses shared tag_service for resolution
        parsed = self._parse_path(name)
        if parsed:
            return tag_service.get_tag_value(name)
        # Fallback for legacy plain names (try to resolve to a path)
        path = self._resolve_plain_to_path(name)
        if path:
            return tag_service.get_tag_value(path)
        # Finally, local cache fallback
        return self._tags.get(name).value if name in self._tags else None

    def set(self, name: str, value: Any):
        # Normalize to canonical path when possible
        path = name
        if not self._parse_path(name):
            maybe = self._resolve_plain_to_path(name)
            if maybe:
                path = maybe

        # Update shared tag service (emits its own signal, but we keep our simple one)
        tag_service.set_tag_value(path, value)

        # Update underlying tag_data_service value if we can parse the path
        parsed = self._parse_path(path)
        if parsed:
            db_name, tag_name = parsed
            db_id = tag_data_service.find_db_id_by_name(db_name)
            if db_id:
                try:
                    # indices=[] -> set whole value
                    tag_data_service._perform_update_tag_element_value(db_id, tag_name, [], value)  # type: ignore[attr-defined]
                except Exception:
                    pass

        # Maintain local cache and emit simplified signal
        t = self._tags.get(path) or Tag(name=path, type="any", value=None)
        if t.value != value:
            t.value = value
            self._tags[path] = t
            self.tag_changed.emit(path, value)
