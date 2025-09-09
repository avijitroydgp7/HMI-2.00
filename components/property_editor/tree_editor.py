from __future__ import annotations

"""Lightweight tree-based property editor.

This module provides a minimal ``TreeEditor`` widget used by the main
:class:`PropertyEditor`.  It exposes a two-column ``QTreeWidget`` where the
left column lists property names and the right column holds editable values.

The implementation is intentionally small – it is not a full replacement for
all bespoke property dialogs but offers a unified place to tweak common values
and launch specialised editors such as *Word Action*, *Bit Action* and
*Conditional Style* dialogs.
"""

from typing import Any, Dict, Tuple

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QLineEdit,
)

from services.command_history_service import command_history_service
from services.commands import UpdateChildPropertiesCommand
from services.screen_data_service import screen_service

from tools.button.actions.word_action_dialog import WordActionDialog
from tools.button.actions.bit_action_dialog import BitActionDialog
from tools.button.conditional_style.editor_dialog import (
    ConditionalStyleEditorDialog,
)


class TreeEditor(QWidget):
    """Generic property tree with simple inline editing."""

    properties_changed = pyqtSignal(dict)

    def __init__(self, host):
        super().__init__(parent=None)
        self.host = host
        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Property", "Value"])
        layout = QVBoxLayout(self)
        layout.addWidget(self.tree)

        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)

        self.update_from_props(host.current_properties)

    # ------------------------------------------------------------------ build
    def update_from_props(self, props: Dict[str, Any]) -> None:
        """Populate the tree from the supplied properties."""
        self.tree.blockSignals(True)
        self.tree.clear()

        # Common section
        common = QTreeWidgetItem(self.tree, ["Common Information"])
        common.setFirstColumnSpanned(True)

        # Label
        label = QTreeWidgetItem(common, ["Label", props.get("label", "")])
        label.setFlags(label.flags() | Qt.ItemFlag.ItemIsEditable)
        label.setData(0, Qt.ItemDataRole.UserRole, ("label",))

        # Size subtree
        size = props.get("size", {})
        size_root = QTreeWidgetItem(common, ["Size"])
        size_root.setFirstColumnSpanned(True)
        width_item = QTreeWidgetItem(size_root, ["Width", str(size.get("width", 0))])
        width_item.setFlags(width_item.flags() | Qt.ItemFlag.ItemIsEditable)
        width_item.setData(0, Qt.ItemDataRole.UserRole, ("size", "width"))
        height_item = QTreeWidgetItem(size_root, ["Height", str(size.get("height", 0))])
        height_item.setFlags(height_item.flags() | Qt.ItemFlag.ItemIsEditable)
        height_item.setData(0, Qt.ItemDataRole.UserRole, ("size", "height"))

        # Special dialog launchers -------------------------------------------------
        QTreeWidgetItem(self.tree, ["Word Action", "..."])
        QTreeWidgetItem(self.tree, ["Bit Action", "..."])
        QTreeWidgetItem(self.tree, ["Conditional Style", "..."])

        self.tree.expandAll()
        self.tree.blockSignals(False)

    # ---------------------------------------------------------------- callbacks
    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if not path or column != 1:
            return

        # Build a nested dict patch from the path
        value: Any = item.text(1)
        try:
            value = int(value)
        except ValueError:
            pass

        patch: Dict[str, Any] = {}
        cur = patch
        for key in path[:-1]:
            cur[key] = {}
            cur = cur[key]
        cur[path[-1]] = value

        self.properties_changed.emit(patch)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        if item.text(0) == "Word Action":
            dlg = WordActionDialog(self)
        elif item.text(0) == "Bit Action":
            dlg = BitActionDialog(self)
        elif item.text(0) == "Conditional Style":
            dlg = ConditionalStyleEditorDialog(self.host.current_properties, parent=self)
        else:
            return

        if dlg.exec():
            # Merge dialog result into properties
            result = getattr(dlg, "result", lambda: {})()
            if not isinstance(result, dict):
                return

            guard = self.host._begin_edit()
            try:
                if self.host.current_object_id:
                    instance = screen_service.get_child_instance(
                        self.host.current_parent_id, self.host.current_object_id
                    )
                    if instance is None:
                        return
                    new_props = dict(instance.get("properties", {}))
                    old_props = dict(new_props)
                    self._merge_dict(new_props, result)
                    if new_props != old_props:
                        cmd = UpdateChildPropertiesCommand(
                            self.host.current_parent_id,
                            self.host.current_object_id,
                            new_props,
                            old_props,
                        )
                        command_history_service.add_command(cmd)
                        guard.mark_changed()
                        self.host.current_properties = new_props
                        self.update_from_props(new_props)
            finally:
                guard.end()

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _merge_dict(base: Dict[str, Any], inc: Dict[str, Any]) -> Dict[str, Any]:
        for k, v in inc.items():
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                TreeEditor._merge_dict(base[k], v)
            else:
                base[k] = v
        return base


# --------------------------------------------------------------------------- API

def build(host) -> TreeEditor:
    """Return a configured :class:`TreeEditor` instance."""
    editor = TreeEditor(host)

    def _on_props_changed(patch: Dict[str, Any]) -> None:
        guard = host._begin_edit()
        try:
            if host.current_object_id:
                instance = screen_service.get_child_instance(
                    host.current_parent_id, host.current_object_id
                )
                if instance is None:
                    return
                new_props = dict(instance.get("properties", {}))
                old_props = dict(new_props)
                TreeEditor._merge_dict(new_props, patch)
                if new_props != old_props:
                    cmd = UpdateChildPropertiesCommand(
                        host.current_parent_id, host.current_object_id, new_props, old_props
                    )
                    command_history_service.add_command(cmd)
                    guard.mark_changed()
                    host.current_properties = new_props
            else:
                new_props = dict(host.current_properties)
                TreeEditor._merge_dict(new_props, patch)
                host.current_properties = new_props
        finally:
            guard.end()

    editor.properties_changed.connect(_on_props_changed)
    return editor


def update_fields(widget: TreeEditor, props: Dict[str, Any]) -> None:
    """Refresh the tree from ``props``."""
    widget.update_from_props(props or {})
