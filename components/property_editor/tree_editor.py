"""Tree-based property editor for generic tools."""

from __future__ import annotations

import copy
from typing import Any, Iterable, List

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QLineEdit,
    QStyledItemDelegate,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)


class _ValueDelegate(QStyledItemDelegate):
    """Delegate that chooses an editor widget based on value type."""

    def createEditor(self, parent, option, index):  # type: ignore[override]
        value_type = index.data(Qt.ItemDataRole.UserRole)
        if value_type is bool:
            combo = QComboBox(parent)
            combo.addItems(["False", "True"])
            return combo
        return QLineEdit(parent)

    def setEditorData(self, editor, index):  # type: ignore[override]
        value_type = index.data(Qt.ItemDataRole.UserRole)
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        if value_type is bool and isinstance(editor, QComboBox):
            editor.setCurrentIndex(1 if text.lower() == "true" else 0)
        elif isinstance(editor, QLineEdit):
            editor.setText(text)

    def setModelData(self, editor, model, index):  # type: ignore[override]
        value_type = index.data(Qt.ItemDataRole.UserRole)
        if value_type is bool and isinstance(editor, QComboBox):
            value = editor.currentIndex() == 1
            model.setData(index, "True" if value else "False")
        elif isinstance(editor, QLineEdit):
            model.setData(index, editor.text())


class PropertyTreeWidget(QTreeWidget):
    """Generic tree widget for editing nested property dictionaries."""

    properties_changed = pyqtSignal(dict)

    def __init__(self, properties: dict | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setColumnCount(2)
        self.setHeaderLabels(["Property", "Value"])
        self.setItemDelegate(_ValueDelegate(self))
        self.setEditTriggers(
            QTreeWidget.EditTrigger.DoubleClicked | QTreeWidget.EditTrigger.SelectedClicked
        )
        self._properties: dict = {}
        self._populate(properties or {})
        self.itemChanged.connect(self._handle_item_changed)

    # --- Population helpers -------------------------------------------------
    def _populate(self, props: dict) -> None:
        self.clear()
        self._properties = copy.deepcopy(props)

        def _add_items(parent: QTreeWidgetItem, data: dict, path: Iterable[str]):
            for key, value in data.items():
                item_path = list(path) + [key]
                if isinstance(value, dict):
                    node = QTreeWidgetItem(parent, [str(key)])
                    node.setData(0, Qt.ItemDataRole.UserRole, item_path)
                    _add_items(node, value, item_path)
                else:
                    node = QTreeWidgetItem(parent, [str(key), str(value)])
                    node.setData(0, Qt.ItemDataRole.UserRole, item_path)
                    node.setData(1, Qt.ItemDataRole.UserRole, type(value))
                    node.setFlags(node.flags() | Qt.ItemFlag.ItemIsEditable)

        _add_items(self.invisibleRootItem(), props, [])
        self.expandAll()

    # --- Change handling ----------------------------------------------------
    def _handle_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if column != 1:
            return
        path: List[str] | None = item.data(0, Qt.ItemDataRole.UserRole)
        if not path:
            return
        value_type = item.data(1, Qt.ItemDataRole.UserRole)
        text = item.text(1)
        if value_type is bool:
            value = text.lower() == "true"
        elif value_type is int:
            try:
                value = int(text)
            except ValueError:
                value = 0
        elif value_type is float:
            try:
                value = float(text)
            except ValueError:
                value = 0.0
        else:
            value = text

        target = self._properties
        for key in path[:-1]:
            target = target.setdefault(key, {})
        target[path[-1]] = value
        self.properties_changed.emit(copy.deepcopy(self._properties))

    # --- External API -------------------------------------------------------
    def set_properties(self, props: dict) -> None:
        self._populate(props)


# --- Factory helpers --------------------------------------------------------

def build(host) -> QWidget:
    """Build a tree-based editor widget for the host property editor."""

    widget = PropertyTreeWidget(host.current_properties)

    def _on_props_changed(new_props: dict) -> None:
        from services.command_history_service import command_history_service
        from services.commands import UpdateChildPropertiesCommand

        guard = host._begin_edit()
        try:
            old_props = copy.deepcopy(host.current_properties)
            if host.current_object_id:
                command = UpdateChildPropertiesCommand(
                    host.current_parent_id, host.current_object_id, new_props, old_props
                )
                command_history_service.add_command(command)
                guard.mark_changed()
            host.current_properties = copy.deepcopy(new_props)
        finally:
            guard.end()

    widget.properties_changed.connect(_on_props_changed)
    return widget


def update_fields(editor: PropertyTreeWidget, props: dict) -> None:
    """Refresh the tree from ``props``."""

    editor.set_properties(props or {})
