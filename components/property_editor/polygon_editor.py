from PyQt6.QtWidgets import QWidget, QFormLayout, QLineEdit
from PyQt6.QtCore import QSignalBlocker
import copy

from services.command_history_service import command_history_service
from services.commands import UpdateChildPropertiesCommand


def build(host) -> QWidget:
    from tools import polygon as polygon_tool

    editor_widget = QWidget()
    layout = QFormLayout(editor_widget)
    layout.setContentsMargins(5, 5, 5, 5)
    layout.setSpacing(5)

    fill_color = QLineEdit(host.current_properties.get("fill_color", ""))
    fill_color.setObjectName("fill_color")
    stroke_color = QLineEdit(host.current_properties.get("stroke_color", ""))
    stroke_color.setObjectName("stroke_color")
    stroke_width = QLineEdit(str(host.current_properties.get("stroke_width", 0)))
    stroke_width.setObjectName("stroke_width")
    stroke_style = QLineEdit(host.current_properties.get("stroke_style", ""))
    stroke_style.setObjectName("stroke_style")

    layout.addRow("Fill Color:", fill_color)
    layout.addRow("Stroke Color:", stroke_color)
    layout.addRow("Stroke Width:", stroke_width)
    layout.addRow("Stroke Style:", stroke_style)

    def on_property_changed():
        guard = host._begin_edit()
        try:
            new_props = copy.deepcopy(host.current_properties)
            new_props["fill_color"] = fill_color.text()
            new_props["stroke_color"] = stroke_color.text()
            new_props["stroke_width"] = int(stroke_width.text() or 0)
            new_props["stroke_style"] = stroke_style.text()
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
                    polygon_tool.set_default_properties(new_props)
                host.current_properties = new_props
        finally:
            guard.end()

    for widget in (fill_color, stroke_color, stroke_width, stroke_style):
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

    _set_line("fill_color", props.get("fill_color", ""))
    _set_line("stroke_color", props.get("stroke_color", ""))
    _set_line("stroke_width", props.get("stroke_width", 0))
    _set_line("stroke_style", props.get("stroke_style", ""))

