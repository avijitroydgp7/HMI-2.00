from PyQt6.QtWidgets import QWidget, QFormLayout, QLineEdit
from PyQt6.QtCore import QSignalBlocker
import copy

from services.command_history_service import command_history_service
from services.commands import UpdateChildPropertiesCommand


def build(host) -> QWidget:
    from tools import line as line_tool

    editor_widget = QWidget()
    layout = QFormLayout(editor_widget)
    layout.setContentsMargins(5, 5, 5, 5)
    layout.setSpacing(5)

    start_x = QLineEdit(str(host.current_properties.get("start", {}).get("x", 0)))
    start_x.setObjectName("start.x")
    start_y = QLineEdit(str(host.current_properties.get("start", {}).get("y", 0)))
    start_y.setObjectName("start.y")
    end_x = QLineEdit(str(host.current_properties.get("end", {}).get("x", 0)))
    end_x.setObjectName("end.x")
    end_y = QLineEdit(str(host.current_properties.get("end", {}).get("y", 0)))
    end_y.setObjectName("end.y")
    color_edit = QLineEdit(host.current_properties.get("color", ""))
    color_edit.setObjectName("color")
    width_edit = QLineEdit(str(host.current_properties.get("width", 0)))
    width_edit.setObjectName("width")
    style_edit = QLineEdit(host.current_properties.get("style", ""))
    style_edit.setObjectName("style")

    layout.addRow("Start X:", start_x)
    layout.addRow("Start Y:", start_y)
    layout.addRow("End X:", end_x)
    layout.addRow("End Y:", end_y)
    layout.addRow("Color:", color_edit)
    layout.addRow("Width:", width_edit)
    layout.addRow("Style:", style_edit)

    def on_property_changed():
        guard = host._begin_edit()
        try:
            new_props = copy.deepcopy(host.current_properties)
            new_props["start"] = {
                "x": int(start_x.text() or 0),
                "y": int(start_y.text() or 0),
            }
            new_props["end"] = {
                "x": int(end_x.text() or 0),
                "y": int(end_y.text() or 0),
            }
            new_props["color"] = color_edit.text()
            new_props["width"] = int(width_edit.text() or 0)
            new_props["style"] = style_edit.text()
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
                    line_tool.set_default_properties(new_props)
                host.current_properties = new_props
        finally:
            guard.end()

    for widget in (start_x, start_y, end_x, end_y, color_edit, width_edit, style_edit):
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

    start = props.get("start", {})
    end = props.get("end", {})
    _set_line("start.x", start.get("x", 0))
    _set_line("start.y", start.get("y", 0))
    _set_line("end.x", end.get("x", 0))
    _set_line("end.y", end.get("y", 0))
    _set_line("color", props.get("color", ""))
    _set_line("width", props.get("width", 0))
    _set_line("style", props.get("style", ""))

