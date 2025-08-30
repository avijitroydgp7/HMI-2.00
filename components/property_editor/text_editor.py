from PyQt6.QtWidgets import QWidget, QFormLayout, QLineEdit, QComboBox
from PyQt6.QtCore import QSignalBlocker
import copy

from services.command_history_service import command_history_service
from services.commands import UpdateChildPropertiesCommand


def build(host) -> QWidget:
    from tools import text as text_tool

    editor_widget = QWidget()
    layout = QFormLayout(editor_widget)
    layout.setContentsMargins(5, 5, 5, 5)
    layout.setSpacing(5)

    content_edit = QLineEdit(host.current_properties.get("content", ""))
    content_edit.setObjectName("content")
    font_family = QLineEdit(host.current_properties.get("font", {}).get("family", ""))
    font_family.setObjectName("font.family")
    font_size = QLineEdit(str(host.current_properties.get("font", {}).get("size", 0)))
    font_size.setObjectName("font.size")
    bold_combo = QComboBox()
    bold_combo.setObjectName("font.bold")
    bold_combo.addItems(["False", "True"])
    bold_combo.setCurrentText(
        "True" if host.current_properties.get("font", {}).get("bold") else "False"
    )
    italic_combo = QComboBox()
    italic_combo.setObjectName("font.italic")
    italic_combo.addItems(["False", "True"])
    italic_combo.setCurrentText(
        "True" if host.current_properties.get("font", {}).get("italic") else "False"
    )
    color_edit = QLineEdit(host.current_properties.get("color", ""))
    color_edit.setObjectName("color")

    layout.addRow("Content:", content_edit)
    layout.addRow("Font Family:", font_family)
    layout.addRow("Font Size:", font_size)
    layout.addRow("Bold:", bold_combo)
    layout.addRow("Italic:", italic_combo)
    layout.addRow("Color:", color_edit)

    def on_property_changed():
        guard = host._begin_edit()
        try:
            new_props = copy.deepcopy(host.current_properties)
            new_props["content"] = content_edit.text()
            new_props["font"] = {
                "family": font_family.text(),
                "size": int(font_size.text() or 0),
                "bold": bold_combo.currentText() == "True",
                "italic": italic_combo.currentText() == "True",
            }
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
                    text_tool.set_default_properties(new_props)
                host.current_properties = new_props
        finally:
            guard.end()

    content_edit.editingFinished.connect(on_property_changed)
    font_family.editingFinished.connect(on_property_changed)
    font_size.editingFinished.connect(on_property_changed)
    bold_combo.activated.connect(lambda _=None: on_property_changed())
    italic_combo.activated.connect(lambda _=None: on_property_changed())
    color_edit.editingFinished.connect(on_property_changed)

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

    font = props.get("font", {})
    _set_line("content", props.get("content", ""))
    _set_line("font.family", font.get("family", ""))
    _set_line("font.size", font.get("size", 0))
    _set_combo("font.bold", "True" if font.get("bold") else "False")
    _set_combo("font.italic", "True" if font.get("italic") else "False")
    _set_line("color", props.get("color", ""))

