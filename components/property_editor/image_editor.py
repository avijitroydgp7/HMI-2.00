from PyQt6.QtWidgets import QWidget, QFormLayout, QLineEdit
from PyQt6.QtCore import QSignalBlocker
import copy

from services.command_history_service import command_history_service
from services.commands import UpdateChildPropertiesCommand


def build(host) -> QWidget:
    from tools import image as image_tool

    editor_widget = QWidget()
    layout = QFormLayout(editor_widget)
    layout.setContentsMargins(5, 5, 5, 5)
    layout.setSpacing(5)

    path_edit = QLineEdit(host.current_properties.get("path", ""))
    path_edit.setObjectName("path")
    width_edit = QLineEdit(str(host.current_properties.get("size", {}).get("width", 0)))
    width_edit.setObjectName("size.width")
    height_edit = QLineEdit(str(host.current_properties.get("size", {}).get("height", 0)))
    height_edit.setObjectName("size.height")

    layout.addRow("Path:", path_edit)
    layout.addRow("Width:", width_edit)
    layout.addRow("Height:", height_edit)

    def on_property_changed():
        guard = host._begin_edit()
        try:
            new_props = copy.deepcopy(host.current_properties)
            new_props["path"] = path_edit.text()
            new_props["size"] = {
                "width": int(width_edit.text() or 0),
                "height": int(height_edit.text() or 0),
            }
            if new_props != host.current_properties:
                if host.current_object_id:
                    command = UpdateChildPropertiesCommand(
                        host.current_parent_id,
                        host.current_object_id,
                        new_props,
                        host.current_properties,
                    )
                    command_history_service.add_command(command)
                    guard.mark_changed()
                else:
                    image_tool.set_default_properties(new_props)
                host.current_properties = new_props
        finally:
            guard.end()

    for widget in (path_edit, width_edit, height_edit):
        widget.editingFinished.connect(on_property_changed)

    return editor_widget


def update_fields(editor: QWidget, props: dict) -> None:
    def _set_line(name: str, value: str):
        w = editor.findChild(QLineEdit, name)
        if w is not None:
            blocker = QSignalBlocker(w)
            try:
                w.setText(str(value))
            finally:
                del blocker

    size = props.get("size", {})
    _set_line("path", props.get("path", ""))
    _set_line("size.width", size.get("width", 0))
    _set_line("size.height", size.get("height", 0))

