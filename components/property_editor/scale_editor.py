from PyQt6.QtWidgets import QWidget, QFormLayout, QLineEdit, QComboBox
from PyQt6.QtCore import QSignalBlocker
import copy

from services.command_history_service import command_history_service
from services.commands import UpdateChildPropertiesCommand


def build(host) -> QWidget:
    from tools import scale as scale_tool

    editor_widget = QWidget()
    layout = QFormLayout(editor_widget)
    layout.setContentsMargins(5, 5, 5, 5)
    layout.setSpacing(5)

    orientation_combo = QComboBox()
    orientation_combo.setObjectName("orientation")
    orientation_combo.addItems(["horizontal", "vertical"])
    orientation_combo.setCurrentText(host.current_properties.get("orientation", "horizontal"))
    length_edit = QLineEdit(str(host.current_properties.get("length", 0)))
    length_edit.setObjectName("length")
    thickness_edit = QLineEdit(str(host.current_properties.get("thickness", 0)))
    thickness_edit.setObjectName("thickness")
    major_ticks = QLineEdit(str(host.current_properties.get("major_ticks", 0)))
    major_ticks.setObjectName("major_ticks")
    minor_ticks = QLineEdit(str(host.current_properties.get("minor_ticks", 0)))
    minor_ticks.setObjectName("minor_ticks")
    tick_spacing = QLineEdit(str(host.current_properties.get("tick_spacing", 0)))
    tick_spacing.setObjectName("tick_spacing")
    units_edit = QLineEdit(host.current_properties.get("units", ""))
    units_edit.setObjectName("units")
    color_edit = QLineEdit(host.current_properties.get("color", ""))
    color_edit.setObjectName("color")

    layout.addRow("Orientation:", orientation_combo)
    layout.addRow("Length:", length_edit)
    layout.addRow("Thickness:", thickness_edit)
    layout.addRow("Major Ticks:", major_ticks)
    layout.addRow("Minor Ticks:", minor_ticks)
    layout.addRow("Tick Spacing:", tick_spacing)
    layout.addRow("Units:", units_edit)
    layout.addRow("Color:", color_edit)

    def on_property_changed():
        guard = host._begin_edit()
        try:
            new_props = copy.deepcopy(host.current_properties)
            new_props["orientation"] = orientation_combo.currentText()
            new_props["length"] = int(length_edit.text() or 0)
            new_props["thickness"] = int(thickness_edit.text() or 0)
            new_props["major_ticks"] = int(major_ticks.text() or 0)
            new_props["minor_ticks"] = int(minor_ticks.text() or 0)
            new_props["tick_spacing"] = int(tick_spacing.text() or 0)
            new_props["units"] = units_edit.text()
            new_props["color"] = color_edit.text()
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
                    scale_tool.set_default_properties(new_props)
                host.current_properties = new_props
        finally:
            guard.end()

    orientation_combo.activated.connect(lambda _=None: on_property_changed())
    for widget in (
        length_edit,
        thickness_edit,
        major_ticks,
        minor_ticks,
        tick_spacing,
        units_edit,
        color_edit,
    ):
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

    def _set_combo(name: str, text_value: str):
        w = editor.findChild(QComboBox, name)
        if w is not None:
            blocker = QSignalBlocker(w)
            try:
                w.setCurrentText(text_value)
            finally:
                del blocker

    _set_combo("orientation", props.get("orientation", "horizontal"))
    _set_line("length", props.get("length", 0))
    _set_line("thickness", props.get("thickness", 0))
    _set_line("major_ticks", props.get("major_ticks", 0))
    _set_line("minor_ticks", props.get("minor_ticks", 0))
    _set_line("tick_spacing", props.get("tick_spacing", 0))
    _set_line("units", props.get("units", ""))
    _set_line("color", props.get("color", ""))

