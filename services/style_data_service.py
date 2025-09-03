# services/style_data_service.py
"""Central storage and management for button style definitions.

This service acts as the single source of truth for all style
configurations used by buttons within the designer.  It exposes a simple
CRUD style API and emits a :data:`styles_changed` signal whenever the set
of styles or one of their definitions changes.  Consumers such as the
property editors or the design canvas can subscribe to this signal to
refresh their UI.

The service also updates any existing button instances when a style is
modified or removed so that changes propagate across the entire project.
"""

from __future__ import annotations

from typing import Dict, Any, List
import copy
import uuid
from dataclasses import dataclass, field, asdict

from PyQt6.QtCore import QObject, pyqtSignal

from .data_context import DataContext, data_context

# ---------------------------------------------------------------------------
# Default style definition
# ---------------------------------------------------------------------------
# The application always provides at least one style – the Qt default
# QPushButton appearance.  Keeping the definition here avoids circular
# imports with modules that expose convenience wrappers around the service.
_QT_DEFAULT_STYLE_ID = "qt_default"


@dataclass
class StyleProperties:
    component_type: str = "Standard Button"
    shape_style: str = "Flat"
    background_type: str = "Solid"
    background_color: str = ""
    text_color: str = ""
    border_radius: int = 0
    border_width: int = 0
    border_style: str = "solid"
    border_color: str = ""
    font_family: str = ""
    font_size: int = 0
    bold: bool = False
    italic: bool = False
    underline: bool = False
    text_type: str = "Text"
    text_value: str = ""
    comment_ref: Dict[str, Any] = field(default_factory=dict)
    h_align: str = "center"
    v_align: str = "middle"
    offset: int = 0
    icon: str = ""
    icon_size: int = 0
    icon_align: str = "center"
    icon_color: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return copy.deepcopy(asdict(self))


def _qt_default_style() -> Dict[str, Any]:
    """Factory for the built-in Qt button style."""

    base_props = StyleProperties(
        background_color="#f0f0f0",
        text_color="#000000",
        border_radius=4,
        border_width=1,
        border_color="#b3b3b3",
        font_size=18,
        icon_size=50,
    )

    properties = base_props.to_dict()
    hover_properties = copy.deepcopy(properties)
    pressed_properties = copy.deepcopy(properties)
    disabled_properties = copy.deepcopy(properties)

    return {
        "id": _QT_DEFAULT_STYLE_ID,
        "name": "Qt Default",
        "properties": properties,
        "hover_properties": hover_properties,
        "pressed_properties": pressed_properties,
        "disabled_properties": disabled_properties,
    }


class StyleDataService(QObject):
    """Manages button style definitions."""

    # Emitted with the ID of the style that changed.  An empty string
    # indicates a bulk change (e.g. project load).
    styles_changed = pyqtSignal(str)

    def __init__(self, bus: DataContext):
        super().__init__()
        self._bus = bus
        self._styles: Dict[str, Dict[str, Any]] = {}

        # Bridge into the shared data context
        self.styles_changed.connect(
            lambda sid: self._bus.styles_changed.emit({"style_id": sid})
        )

        # Ensure the default style exists
        self.add_style(_qt_default_style())

    # ------------------------------------------------------------------
    # Basic CRUD helpers
    # ------------------------------------------------------------------
    def clear_all(self) -> None:
        """Remove all styles and restore the built-in default."""
        self._styles.clear()
        self.add_style(_qt_default_style())
        self.styles_changed.emit("")

    def get_style(self, style_id: str) -> Dict[str, Any] | None:
        """Return a **copy** of the style definition.

        Returning direct references to the internal ``_styles`` mapping meant
        that callers could inadvertently mutate the service's state without
        using :meth:`update_style`.  Such mutations bypassed the usual
        ``styles_changed`` signal and left existing button instances in an
        inconsistent state.  Providing a deep copy ensures external code must
        explicitly update the service if it wants to persist modifications.
        """

        data = self._styles.get(style_id)
        return copy.deepcopy(data) if data is not None else None

    def get_all_styles(self) -> List[Dict[str, Any]]:
        """Return copies of all style definitions."""
        return [copy.deepcopy(s) for s in self._styles.values()]

    def get_default_style(self) -> Dict[str, Any]:
        """Return a copy of the default style definition."""
        data = self._styles.get(_QT_DEFAULT_STYLE_ID)
        return copy.deepcopy(data) if data is not None else _qt_default_style()

    def add_style(self, style_data: Dict[str, Any], style_id: str | None = None) -> str:
        sid = style_id or style_data.get("id") or str(uuid.uuid4())
        data = copy.deepcopy(style_data)
        data["id"] = sid
        self._styles[sid] = data
        self.styles_changed.emit(sid)
        return sid

    def update_style(self, style_id: str, style_data: Dict[str, Any]) -> bool:
        """Replace the definition of an existing style."""
        if style_id not in self._styles:
            return False
        data = copy.deepcopy(style_data)
        data["id"] = style_id
        self._styles[style_id] = data
        self._apply_style_to_buttons(style_id, data)
        self.styles_changed.emit(style_id)
        return True

    def remove_style(self, style_id: str) -> bool:
        """Remove a style and reset buttons to the default style."""
        if style_id == _QT_DEFAULT_STYLE_ID:
            return False
        if style_id in self._styles:
            del self._styles[style_id]
            # Apply the default style to buttons that used the removed one
            self._apply_style_to_buttons(style_id, self.get_default_style())
            self.styles_changed.emit(style_id)
            return True
        return False

    # ------------------------------------------------------------------
    # Project (de)serialization
    # ------------------------------------------------------------------
    def serialize_for_project(self) -> Dict[str, Any]:
        return {"styles": self._styles}

    def load_from_project(self, project_data: Dict[str, Any]) -> None:
        styles = project_data.get("styles", {})
        self._styles = {sid: copy.deepcopy(s) for sid, s in styles.items()}
        # Guarantee the default style exists
        if _QT_DEFAULT_STYLE_ID not in self._styles:
            self._styles[_QT_DEFAULT_STYLE_ID] = _qt_default_style()
        self.styles_changed.emit("")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _apply_style_to_buttons(self, style_id: str, style_def: Dict[str, Any]) -> None:
        """Update all button instances using the given style."""
        try:
            from services.screen_data_service import screen_service
        except Exception:  # pragma: no cover - defensive
            return

        new_id = style_def.get("id", style_id)
        for sid, screen in screen_service.get_all_screens().items():
            changed = False
            for child in screen.get("children", []):
                props = child.get("properties", {})
                if props.get("style_id") != style_id:
                    continue
                props["style_id"] = new_id
                props.update(copy.deepcopy(style_def.get("properties", {})))
                if "hover_properties" in style_def:
                    props["hover_properties"] = copy.deepcopy(style_def["hover_properties"])
                else:
                    props.pop("hover_properties", None)
                if "pressed_properties" in style_def:
                    props["pressed_properties"] = copy.deepcopy(
                        style_def["pressed_properties"]
                    )
                else:
                    props.pop("pressed_properties", None)
                if "disabled_properties" in style_def:
                    props["disabled_properties"] = copy.deepcopy(
                        style_def["disabled_properties"]
                    )
                else:
                    props.pop("disabled_properties", None)
                if style_def.get("icon"):
                    props["icon"] = style_def["icon"]
                else:
                    props.pop("icon", None)
                if style_def.get("hover_icon"):
                    props["hover_icon"] = style_def["hover_icon"]
                else:
                    props.pop("hover_icon", None)
                changed = True
            if changed:
                screen_service.notify_screen_update(sid)


style_data_service = StyleDataService(data_context)
