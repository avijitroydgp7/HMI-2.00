"""Simplified property editor showing only geometry fields."""

from __future__ import annotations

import copy

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QFormLayout, QSpinBox, QVBoxLayout, QWidget

from services.command_history_service import command_history_service
from services.commands import MoveChildCommand, UpdateChildPropertiesCommand
from services.data_context import data_context
from services.screen_data_service import screen_service
from utils.editing_guard import EditingGuard


class PropertyEditor(QWidget):
    """Property panel that only manages X, Y, Width and Height."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_object_id: str | None = None
        self.current_parent_id: str | None = None
        self.current_properties: dict = {}
        self.current_position = {"x": 0, "y": 0}
        self.current_size = {"width": 0, "height": 0}
        self._is_editing = False

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        self.x_spin = QSpinBox()
        self.y_spin = QSpinBox()
        self.width_spin = QSpinBox()
        self.height_spin = QSpinBox()
        for sb in (self.x_spin, self.y_spin):
            sb.setRange(-100000, 100000)
        for sb in (self.width_spin, self.height_spin):
            sb.setRange(0, 100000)
        form_layout.addRow("X", self.x_spin)
        form_layout.addRow("Y", self.y_spin)
        form_layout.addRow("W", self.width_spin)
        form_layout.addRow("H", self.height_spin)
        self.geometry_form = QWidget()
        self.geometry_form.setLayout(form_layout)
        layout.addWidget(self.geometry_form)

        self.x_spin.valueChanged.connect(lambda v: self._on_position_changed("x", v))
        self.y_spin.valueChanged.connect(lambda v: self._on_position_changed("y", v))
        self.width_spin.valueChanged.connect(lambda v: self._on_size_changed("width", v))
        self.height_spin.valueChanged.connect(lambda v: self._on_size_changed("height", v))

        self._update_geometry_fields(None)
        data_context.screens_changed.connect(self._handle_screen_event)

    # ------------------------------------------------------------------
    # Geometry helpers
    def _block_geometry_signals(self, block: bool) -> None:
        for sb in (self.x_spin, self.y_spin, self.width_spin, self.height_spin):
            sb.blockSignals(block)

    def _update_geometry_fields(self, selection_data) -> None:
        if not selection_data or isinstance(selection_data, list):
            self._block_geometry_signals(True)
            self.x_spin.setValue(0)
            self.y_spin.setValue(0)
            self.width_spin.setValue(0)
            self.height_spin.setValue(0)
            self._block_geometry_signals(False)
            self.geometry_form.setDisabled(True)
            self.current_position = {"x": 0, "y": 0}
            self.current_size = {"width": 0, "height": 0}
            return

        pos = selection_data.get("position") or selection_data.get("properties", {}).get("position", {})
        size = selection_data.get("properties", {}).get("size", {})
        x = int(pos.get("x", 0) or 0)
        y = int(pos.get("y", 0) or 0)
        w = int(size.get("width", 0) or 0)
        h = int(size.get("height", 0) or 0)

        self.geometry_form.setDisabled(False)
        self._block_geometry_signals(True)
        self.x_spin.setValue(x)
        self.y_spin.setValue(y)
        self.width_spin.setValue(w)
        self.height_spin.setValue(h)
        self._block_geometry_signals(False)
        self.current_position = {"x": x, "y": y}
        self.current_size = {"width": w, "height": h}

    def _on_position_changed(self, key: str, value: int) -> None:
        if not self.current_object_id or isinstance(self.current_object_id, list):
            return
        old_pos = dict(self.current_position)
        if old_pos.get(key) == value:
            return
        new_pos = dict(old_pos)
        new_pos[key] = value
        guard = self._begin_edit()
        try:
            command = MoveChildCommand(
                self.current_parent_id,
                self.current_object_id,
                new_pos,
                old_pos,
            )
            command_history_service.add_command(command)
            guard.mark_changed()
            self.current_position = new_pos
        finally:
            guard.end()

    def _on_size_changed(self, key: str, value: int) -> None:
        if not self.current_object_id or isinstance(self.current_object_id, list):
            return
        old_props = copy.deepcopy(self.current_properties)
        new_props = copy.deepcopy(self.current_properties)
        size = new_props.setdefault("size", {})
        if size.get(key) == value:
            return
        size[key] = value
        guard = self._begin_edit()
        try:
            command = UpdateChildPropertiesCommand(
                self.current_parent_id,
                self.current_object_id,
                new_props,
                old_props,
            )
            command_history_service.add_command(command)
            guard.mark_changed()
            self.current_properties = new_props
            self.current_size = size
        finally:
            guard.end()

    # ------------------------------------------------------------------
    # Editing guards
    def _active_canvas_widget(self):
        try:
            win = self.window()
            if hasattr(win, "tab_widget"):
                return win.tab_widget.currentWidget()
        except Exception:
            return None
        return None

    def _begin_edit(self) -> EditingGuard:
        active_widget = self._active_canvas_widget()

        def _emit_final():
            try:
                if self.current_parent_id and self.current_object_id:
                    screen_service.screen_modified.emit(self.current_parent_id)
            except Exception:
                pass

        return EditingGuard(
            self, screen_service, active_widget=active_widget, emit_final=_emit_final
        ).begin()

    # ------------------------------------------------------------------
    # External API
    def _handle_screen_event(self, event: dict) -> None:
        if event.get("action") == "screen_modified":
            self._on_screen_modified(event.get("screen_id", ""))

    def _on_screen_modified(self, screen_id: str) -> None:
        if self._is_editing or screen_id != self.current_parent_id or not self.current_object_id:
            return
        instance = screen_service.get_child_instance(
            self.current_parent_id, self.current_object_id
        )
        if instance is not None:
            selection = {
                "instance_id": instance.get("instance_id"),
                "properties": copy.deepcopy(instance.get("properties") or {}),
                "position": instance.get("position") or {},
            }
            self.current_properties = selection.get("properties", {})
            self._update_geometry_fields(selection)
        else:
            self._clear_selection()

    def _clear_selection(self) -> None:
        self.current_object_id = None
        self.current_parent_id = None
        self.current_properties = {}
        self._update_geometry_fields(None)

    @pyqtSlot(str, object)
    def set_current_object(self, parent_id: str, selection_data: object) -> None:
        if self._is_editing:
            return
        if not selection_data:
            self._clear_selection()
            return
        if isinstance(selection_data, list):
            if len(selection_data) == 1:
                selection_data = selection_data[0]
            else:
                self._clear_selection()
                return
        self.current_object_id = selection_data.get("instance_id")
        self.current_parent_id = parent_id
        self.current_properties = copy.deepcopy(selection_data.get("properties") or {})
        self._update_geometry_fields(selection_data)

    def set_active_tool(self, tool_id) -> None:  # compatibility stub
        pass

