from PyQt6.QtWidgets import QWidget, QFormLayout, QLineEdit, QComboBox
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSignalBlocker
import copy

from services.command_history_service import command_history_service
from services.commands import UpdateChildPropertiesCommand


def build(host) -> QWidget:
    from tools import button
    from tools.button import conditional_style as button_styles

    editor_widget = QWidget()
    layout = QFormLayout(editor_widget)
    layout.setContentsMargins(5, 5, 5, 5)
    layout.setSpacing(5)

    label_edit = QLineEdit(host.current_properties.get("label", ""))
    label_edit.setObjectName("label")
    style_combo = QComboBox()
    style_combo.setObjectName("style_id")

    styles = button_styles.get_styles()
    for style in styles:
        icon_path = style.get("icon") or style.get("svg_icon")
        if icon_path:
            style_combo.addItem(QIcon(icon_path), style["name"], style["id"])
        else:
            style_combo.addItem(style["name"], style["id"])

    current_style_id = host.current_properties.get("style_id", "qt_default")
    index = style_combo.findData(current_style_id)
    if index != -1:
        style_combo.setCurrentIndex(index)

    bg_color_edit = QLineEdit(host.current_properties.get("background_color", ""))
    bg_color_edit.setObjectName("background_color")
    text_color_edit = QLineEdit(host.current_properties.get("text_color", ""))
    text_color_edit.setObjectName("text_color")

    layout.addRow("Label:", label_edit)
    layout.addRow("Style:", style_combo)
    layout.addRow("Background Color:", bg_color_edit)
    layout.addRow("Text Color:", text_color_edit)

    def _apply_style_field_updates(style_id: str):
        style_def = button_styles.get_style_by_id(style_id) or {}
        style_props = style_def.get("properties", {})
        blocker_bg = QSignalBlocker(bg_color_edit)
        blocker_text = QSignalBlocker(text_color_edit)
        try:
            bg_color_edit.setText(style_props.get("background_color", ""))
            text_color_edit.setText(style_props.get("text_color", ""))
        finally:
            del blocker_bg
            del blocker_text

    def on_property_changed():
        guard = host._begin_edit()
        try:
            new_props = copy.deepcopy(host.current_properties)
            new_props["label"] = label_edit.text()
            new_props["background_color"] = bg_color_edit.text()
            new_props["text_color"] = text_color_edit.text()

            selected_style_id = style_combo.currentData()
            if selected_style_id != new_props.get("style_id"):
                new_props["style_id"] = selected_style_id
                style_def = button_styles.get_style_by_id(selected_style_id)
                new_props.update(style_def["properties"])
                if "hover_properties" in style_def:
                    new_props["hover_properties"] = copy.deepcopy(style_def["hover_properties"])
                if style_def.get("icon"):
                    new_props["icon"] = style_def["icon"]
                if style_def.get("hover_icon"):
                    new_props["hover_icon"] = style_def["hover_icon"]

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
                    button.set_default_properties(new_props)
                host.current_properties = new_props
        finally:
            guard.end()

    label_edit.editingFinished.connect(on_property_changed)

    def _on_style_activated(_=None):
        selected_style_id = style_combo.currentData()
        _apply_style_field_updates(selected_style_id)
        on_property_changed()

    style_combo.activated.connect(_on_style_activated)
    bg_color_edit.editingFinished.connect(on_property_changed)
    text_color_edit.editingFinished.connect(on_property_changed)

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

    def _set_combo(name: str, text_value: str = None, data_value=None):
        w = editor.findChild(QComboBox, name)
        if w is not None:
            blocker = QSignalBlocker(w)
            try:
                if data_value is not None:
                    idx = w.findData(data_value)
                    if idx != -1:
                        w.setCurrentIndex(idx)
                elif text_value is not None:
                    w.setCurrentText(text_value)
            finally:
                del blocker

    _set_line("label", props.get("label", ""))
    _set_line("background_color", props.get("background_color", ""))
    _set_line("text_color", props.get("text_color", ""))
    _set_combo("style_id", data_value=props.get("style_id"))

