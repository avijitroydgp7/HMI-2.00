from __future__ import annotations

import copy
from typing import Dict, Any

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QFormLayout, QLineEdit, QPushButton
from PyQt6.QtGui import QDoubleValidator

from services.command_history_service import command_history_service
from services.commands import (
    UpdateChildPropertiesCommand,
    BulkUpdateChildPropertiesCommand,
)
from services.screen_data_service import screen_service

from tools import button as button_tool
from tools.button.button_properties_dialog import (
    value_to_percent,
    ButtonPropertiesDialog,
)


class SimpleButtonEditor(QWidget):
    """Minimal button property editor used in the property panel."""

    properties_changed = pyqtSignal(dict)

    def __init__(self, props: Dict[str, Any], open_dialog_cb=None):
        super().__init__()
        layout = QFormLayout(self)
        self._open_dialog_cb = open_dialog_cb

        self.label_edit = QLineEdit()
        self.label_edit.setObjectName("label")
        layout.addRow("Label", self.label_edit)

        self.bg_color_edit = QLineEdit()
        self.bg_color_edit.setObjectName("default_style.background")
        layout.addRow("Background", self.bg_color_edit)

        self.text_color_edit = QLineEdit()
        self.text_color_edit.setObjectName("default_style.color")
        layout.addRow("Text Color", self.text_color_edit)

        self.pos_x_edit = QLineEdit()
        self.pos_x_edit.setObjectName("position.x")
        layout.addRow("X", self.pos_x_edit)

        self.pos_y_edit = QLineEdit()
        self.pos_y_edit.setObjectName("position.y")
        layout.addRow("Y", self.pos_y_edit)

        self.width_edit = QLineEdit()
        self.width_edit.setObjectName("size.width")
        layout.addRow("Width", self.width_edit)

        self.height_edit = QLineEdit()
        self.height_edit.setObjectName("size.height")
        layout.addRow("Height", self.height_edit)

        for edit in (
            self.pos_x_edit,
            self.pos_y_edit,
            self.width_edit,
            self.height_edit,
        ):
            validator = QDoubleValidator()
            validator.setDecimals(2)
            edit.setValidator(validator)

        self.advanced_button = QPushButton("Actions && Style…")
        self.advanced_button.setObjectName("advanced")
        layout.addRow(self.advanced_button)
        self.advanced_button.clicked.connect(self._open_dialog)

        # Populate initial values
        self.set_properties(props)

        # Emit properties when editing finishes
        for edit in (
            self.label_edit,
            self.bg_color_edit,
            self.text_color_edit,
            self.pos_x_edit,
            self.pos_y_edit,
            self.width_edit,
            self.height_edit,
        ):
            edit.editingFinished.connect(self._emit_change)

    # --- helpers -----------------------------------------------------
    def _emit_change(self) -> None:
        def _to_float(text: str) -> Any:
            try:
                return float(text)
            except Exception:
                return None

        props = {
            "label": self.label_edit.text() or None,
            "default_style": {
                "background": self.bg_color_edit.text() or None,
                "color": self.text_color_edit.text() or None,
            },
            "position": {
                "x": _to_float(self.pos_x_edit.text()),
                "y": _to_float(self.pos_y_edit.text()),
            },
            "size": {
                "width": _to_float(self.width_edit.text()),
                "height": _to_float(self.height_edit.text()),
            },
        }
        self.properties_changed.emit(props)

    def _open_dialog(self) -> None:
        if self._open_dialog_cb:
            self._open_dialog_cb()

    def set_properties(self, props: Dict[str, Any]) -> None:
        def _get(path: str) -> Any:
            parts = path.split(".")
            value: Any = props
            for part in parts:
                if not isinstance(value, dict):
                    return None
                value = value.get(part)
                if value is None:
                    return None
            return value

        fields = [
            (self.label_edit, "label"),
            (self.bg_color_edit, "default_style.background"),
            (self.text_color_edit, "default_style.color"),
            (self.pos_x_edit, "position.x"),
            (self.pos_y_edit, "position.y"),
            (self.width_edit, "size.width"),
            (self.height_edit, "size.height"),
        ]
        for edit, path in fields:
            val = _get(path)
            edit.blockSignals(True)
            edit.setText("" if val is None else str(val))
            edit.blockSignals(False)


def _ensure_percentage_props(props: Dict) -> Dict:
    """Ensure numeric style properties are stored as percentages."""
    p = copy.deepcopy(props)
    size = p.get("size", {})
    w = size.get("width", 100)
    h = size.get("height", 40)
    min_dim = min(w, h)

    def conv(key, base):
        val = p.get(key)
        if val is None:
            return
        # Values greater than 100 are assumed to be absolute pixels
        if isinstance(val, (int, float)) and val > 100:
            p[key] = value_to_percent(val, base)

    conv("font_size", h)
    conv("border_radius", min_dim)
    conv("border_width", min_dim)
    conv("icon_size", min_dim)
    for k in ("border_radius_tl", "border_radius_tr", "border_radius_br", "border_radius_bl"):
        conv(k, min_dim)
    return p


def _merge_into(base: Dict[str, Any], inc: Dict[str, Any]) -> Dict[str, Any]:
    """Overlay ``inc`` onto ``base`` ignoring ``None`` values (recursive)."""
    for k, v in inc.items():
        if v is None:
            continue
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge_into(base[k], v)
        else:
            base[k] = copy.deepcopy(v)
    return base


def build(host) -> QWidget:
    """Build the simplified button property editor."""

    widget = SimpleButtonEditor(_ensure_percentage_props(host.current_properties))

    def _open_full_dialog():
        dlg = ButtonPropertiesDialog(host.current_properties, widget)
        if dlg.exec():
            widget.properties_changed.emit(dlg.get_data())

    widget._open_dialog_cb = _open_full_dialog

    def _on_props_changed(new_props: Dict) -> None:
        guard = host._begin_edit()
        try:
            processed = _ensure_percentage_props(new_props)
            if processed != host.current_properties:
                if host.current_object_id:
                    if isinstance(host.current_object_id, list):
                        update_list = []
                        for inst_id in host.current_object_id:
                            instance = screen_service.get_child_instance(
                                host.current_parent_id, inst_id
                            )
                            if instance is None:
                                continue
                            base_props = copy.deepcopy(instance.get("properties", {}))
                            old_props = copy.deepcopy(base_props)
                            _merge_into(base_props, processed)
                            if base_props != old_props:
                                update_list.append((inst_id, base_props, old_props))
                        if update_list:
                            command = BulkUpdateChildPropertiesCommand(
                                host.current_parent_id, update_list
                            )
                            command_history_service.add_command(command)
                            guard.mark_changed()
                            _merge_into(host.current_properties, processed)
                    else:
                        base_props = copy.deepcopy(host.current_properties)
                        old_props = copy.deepcopy(base_props)
                        _merge_into(base_props, processed)
                        if base_props != old_props:
                            command = UpdateChildPropertiesCommand(
                                host.current_parent_id,
                                host.current_object_id,
                                base_props,
                                old_props,
                            )
                            command_history_service.add_command(command)
                            guard.mark_changed()
                        host.current_properties = copy.deepcopy(base_props)
                else:
                    base_props = copy.deepcopy(host.current_properties)
                    _merge_into(base_props, processed)
                    button_tool.set_default_properties(base_props)
                    host.current_properties = copy.deepcopy(base_props)
        finally:
            guard.end()

    widget.properties_changed.connect(_on_props_changed)
    return widget


def update_fields(editor: SimpleButtonEditor, props: dict) -> None:
    """Refresh the editor from ``props``. Fields with ``None`` are cleared."""

    editor.set_properties(props)

