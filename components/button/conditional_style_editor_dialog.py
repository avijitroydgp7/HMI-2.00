# components/button/conditional_style_editor_dialog.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox, QGroupBox,
    QPushButton, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QDialogButtonBox, QComboBox, QGridLayout, QLabel,
    QColorDialog, QSlider
)
from PyQt6.QtCore import Qt
from button_creator import IconButton
from typing import Optional
import copy

from .conditional_style import ConditionalStyle, StyleCondition
from dialogs.widgets import TagSelector
from services.tag_data_service import tag_data_service


class ConditionEditorDialog(QDialog):
    def __init__(self, parent=None, condition: Optional[StyleCondition] = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Condition")
        self.condition = copy.deepcopy(condition) if condition else StyleCondition()

        layout = QFormLayout(self)
        self.tag_selector = TagSelector()
        self.tag_selector.main_tag_selector.set_mode_fixed("Tag")

        # Preload existing tag path if provided
        if self.condition.tag_path:
            try:
                db_part, tag_part = self.condition.tag_path.split("]::")
                db_name = db_part.strip("[")
                tag_name = tag_part
                db_id = tag_data_service.find_db_id_by_name(db_name)
                if db_id:
                    self.tag_selector.set_data({
                        "main_tag": {
                            "source": "tag",
                            "value": {
                                "db_id": db_id,
                                "db_name": db_name,
                                "tag_name": tag_name,
                            },
                        },
                        "indices": [],
                    })
            except ValueError:
                pass

        layout.addRow("Tag Path:", self.tag_selector)

        self.operator_combo = QComboBox()
        self.operator_combo.addItems(["==", "!=", ">", "<", ">=", "<=", "between", "outside"])
        self.operator_combo.setCurrentText(self.condition.operator)
        layout.addRow("Operator:", self.operator_combo)

        self.value_edit = QLineEdit(str(self.condition.value) if self.condition.value is not None else "")
        self.value2_edit = QLineEdit(str(self.condition.value2) if self.condition.value2 is not None else "")
        layout.addRow("Value:", self.value_edit)
        layout.addRow("Value2:", self.value2_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_condition(self) -> StyleCondition:
        tag_data = self.tag_selector.get_data()
        tag_path = ""
        if tag_data and tag_data.get("main_tag", {}).get("source") == "tag":
            value = tag_data["main_tag"]["value"]
            tag_path = f"[{value.get('db_name')}]::{value.get('tag_name')}"

        cond = StyleCondition(
            tag_path=tag_path,
            operator=self.operator_combo.currentText(),
            value=self.value_edit.text() or None,
            value2=self.value2_edit.text() or None,
        )
        return cond


class ConditionalStyleEditorDialog(QDialog):
    def __init__(self, parent=None, style: Optional[ConditionalStyle] = None):
        super().__init__(parent)
        self.setWindowTitle("Conditional Style")
        self.style = copy.deepcopy(style) if style else ConditionalStyle()
        self.conditions = copy.deepcopy(self.style.conditions)

        main_layout = QGridLayout(self)
        main_layout.setColumnStretch(0, 1)
        main_layout.setColumnStretch(1, 1)

        controls_layout = QVBoxLayout()

        info_layout = QGridLayout()
        self.name_edit = QLineEdit(self.style.name)
        self.priority_spin = QSpinBox(); self.priority_spin.setRange(-100000, 100000)
        self.priority_spin.setValue(self.style.priority)
        self.tooltip_edit = QLineEdit(self.style.tooltip)
        info_layout.addWidget(QLabel("Name:"), 0, 0); info_layout.addWidget(self.name_edit, 0, 1)
        info_layout.addWidget(QLabel("Priority:"), 1, 0); info_layout.addWidget(self.priority_spin, 1, 1)
        info_layout.addWidget(QLabel("Tooltip:"), 2, 0); info_layout.addWidget(self.tooltip_edit, 2, 1)
        controls_layout.addLayout(info_layout)

        # Base style group
        base_group = QGroupBox("Base Style")
        base_layout = QGridLayout()
        self.bg_color_btn = self.create_color_button(self.style.properties.get("background_color", ""))
        self.text_color_btn = self.create_color_button(self.style.properties.get("text_color", ""))
        self.font_size_spin = QSpinBox(); self.font_size_spin.setRange(1, 1000)
        self.font_size_spin.setValue(self.style.properties.get("font_size", 10))
        self.width_spin = QSpinBox(); self.width_spin.setRange(0, 10000)
        self.width_spin.setValue(self.style.properties.get("width", 0))
        self.height_spin = QSpinBox(); self.height_spin.setRange(0, 10000)
        self.height_spin.setValue(self.style.properties.get("height", 0))
        self.border_radius_slider = QSlider(Qt.Orientation.Horizontal); self.border_radius_slider.setRange(0, 1000)
        self.border_radius_slider.setValue(self.style.properties.get("border_radius", 0))
        self.border_width_slider = QSlider(Qt.Orientation.Horizontal); self.border_width_slider.setRange(0, 1000)
        self.border_width_slider.setValue(self.style.properties.get("border_width", 0))
        self.border_color_btn = self.create_color_button(self.style.properties.get("border_color", ""))
        base_layout.addWidget(QLabel("Background:"), 0, 0); base_layout.addWidget(self.bg_color_btn, 0, 1)
        base_layout.addWidget(QLabel("Text Color:"), 1, 0); base_layout.addWidget(self.text_color_btn, 1, 1)
        base_layout.addWidget(QLabel("Font Size:"), 2, 0); base_layout.addWidget(self.font_size_spin, 2, 1)
        base_layout.addWidget(QLabel("Width:"), 3, 0); base_layout.addWidget(self.width_spin, 3, 1)
        base_layout.addWidget(QLabel("Height:"), 4, 0); base_layout.addWidget(self.height_spin, 4, 1)
        base_layout.addWidget(QLabel("Border Radius:"), 5, 0); base_layout.addWidget(self.border_radius_slider, 5, 1)
        base_layout.addWidget(QLabel("Border Width:"), 6, 0); base_layout.addWidget(self.border_width_slider, 6, 1)
        base_layout.addWidget(QLabel("Border Color:"), 7, 0); base_layout.addWidget(self.border_color_btn, 7, 1)
        base_group.setLayout(base_layout)
        controls_layout.addWidget(base_group)

        # Hover style group
        hover_group = QGroupBox("Hover Style")
        hover_layout = QGridLayout()
        self.hover_bg_btn = self.create_color_button(self.style.hover_properties.get("background_color", ""))
        self.hover_text_btn = self.create_color_button(self.style.hover_properties.get("text_color", ""))
        self.hover_border_radius_slider = QSlider(Qt.Orientation.Horizontal); self.hover_border_radius_slider.setRange(0, 1000)
        self.hover_border_radius_slider.setValue(self.style.hover_properties.get("border_radius", 0))
        self.hover_border_width_slider = QSlider(Qt.Orientation.Horizontal); self.hover_border_width_slider.setRange(0, 1000)
        self.hover_border_width_slider.setValue(self.style.hover_properties.get("border_width", 0))
        self.hover_border_color_btn = self.create_color_button(self.style.hover_properties.get("border_color", ""))
        hover_layout.addWidget(QLabel("Background:"), 0, 0); hover_layout.addWidget(self.hover_bg_btn, 0, 1)
        hover_layout.addWidget(QLabel("Text Color:"), 1, 0); hover_layout.addWidget(self.hover_text_btn, 1, 1)
        hover_layout.addWidget(QLabel("Border Radius:"), 2, 0); hover_layout.addWidget(self.hover_border_radius_slider, 2, 1)
        hover_layout.addWidget(QLabel("Border Width:"), 3, 0); hover_layout.addWidget(self.hover_border_width_slider, 3, 1)
        hover_layout.addWidget(QLabel("Border Color:"), 4, 0); hover_layout.addWidget(self.hover_border_color_btn, 4, 1)
        hover_group.setLayout(hover_layout)
        controls_layout.addWidget(hover_group)

        # Click style group
        click_group = QGroupBox("Click Style")
        click_layout = QGridLayout()
        self.click_bg_btn = self.create_color_button(self.style.click_properties.get("background_color", ""))
        self.click_text_btn = self.create_color_button(self.style.click_properties.get("text_color", ""))
        self.click_border_radius_slider = QSlider(Qt.Orientation.Horizontal); self.click_border_radius_slider.setRange(0, 1000)
        self.click_border_radius_slider.setValue(self.style.click_properties.get("border_radius", 0))
        self.click_border_width_slider = QSlider(Qt.Orientation.Horizontal); self.click_border_width_slider.setRange(0, 1000)
        self.click_border_width_slider.setValue(self.style.click_properties.get("border_width", 0))
        self.click_border_color_btn = self.create_color_button(self.style.click_properties.get("border_color", ""))
        click_layout.addWidget(QLabel("Background:"), 0, 0); click_layout.addWidget(self.click_bg_btn, 0, 1)
        click_layout.addWidget(QLabel("Text Color:"), 1, 0); click_layout.addWidget(self.click_text_btn, 1, 1)
        click_layout.addWidget(QLabel("Border Radius:"), 2, 0); click_layout.addWidget(self.click_border_radius_slider, 2, 1)
        click_layout.addWidget(QLabel("Border Width:"), 3, 0); click_layout.addWidget(self.click_border_width_slider, 3, 1)
        click_layout.addWidget(QLabel("Border Color:"), 4, 0); click_layout.addWidget(self.click_border_color_btn, 4, 1)
        click_group.setLayout(click_layout)
        controls_layout.addWidget(click_group)

        # Conditions group
        cond_group = QGroupBox("Conditions")
        cond_layout = QVBoxLayout(cond_group)
        self.condition_table = QTableWidget(); self.condition_table.setColumnCount(4)
        self.condition_table.setHorizontalHeaderLabels(["Tag Path", "Operator", "Value", "Value2"])
        self.condition_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.condition_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.condition_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.condition_table.verticalHeader().setVisible(False)
        header = self.condition_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        cond_layout.addWidget(self.condition_table)

        cond_buttons = QHBoxLayout()
        add_cond_btn = QPushButton("Add"); edit_cond_btn = QPushButton("Edit"); remove_cond_btn = QPushButton("Remove")
        add_cond_btn.clicked.connect(self._add_condition)
        edit_cond_btn.clicked.connect(self._edit_condition)
        remove_cond_btn.clicked.connect(self._remove_condition)
        cond_buttons.addWidget(add_cond_btn); cond_buttons.addWidget(edit_cond_btn); cond_buttons.addWidget(remove_cond_btn)
        cond_buttons.addStretch(); cond_layout.addLayout(cond_buttons)
        controls_layout.addWidget(cond_group)

        controls_layout.addStretch(1)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        controls_layout.addWidget(self.button_box)

        preview_layout = QVBoxLayout()
        preview_group = QGroupBox("Preview")
        preview_group_layout = QVBoxLayout(); preview_group_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_button = IconButton(); self.preview_button.setMinimumSize(200, 100)
        preview_group_layout.addWidget(self.preview_button)
        preview_group.setLayout(preview_group_layout)
        preview_layout.addStretch(1); preview_layout.addWidget(preview_group); preview_layout.addStretch(1)

        main_layout.addLayout(controls_layout, 0, 0)
        main_layout.addLayout(preview_layout, 0, 1)

        for w in [self.font_size_spin, self.width_spin, self.height_spin, self.border_radius_slider,
                  self.border_width_slider, self.hover_border_radius_slider, self.hover_border_width_slider,
                  self.click_border_radius_slider, self.click_border_width_slider]:
            w.valueChanged.connect(self.update_preview)

        self._refresh_condition_table()
        self.update_preview()

    def create_color_button(self, initial):
        btn = QPushButton()
        btn.setFixedSize(40, 20)
        btn.setProperty("color", initial)
        self._set_button_color(btn, initial)
        btn.clicked.connect(lambda: self._choose_color(btn))
        return btn

    def _set_button_color(self, btn, color):
        if color:
            btn.setStyleSheet(f"background-color: {color};")
        else:
            btn.setStyleSheet("")

    def _choose_color(self, btn):
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            color_name = color.name()
            btn.setProperty("color", color_name)
            self._set_button_color(btn, color_name)
            self.update_preview()

    def _button_color(self, btn):
        return btn.property("color") or ""

    def update_preview(self):
        base_props = []
        bg = self._button_color(self.bg_color_btn)
        text = self._button_color(self.text_color_btn)
        border_c = self._button_color(self.border_color_btn)
        if bg:
            base_props.append(f"background-color: {bg};")
        if text:
            base_props.append(f"color: {text};")
        base_props.append(f"font-size: {self.font_size_spin.value()}px;")
        base_props.append(f"border-radius: {self.border_radius_slider.value()}px;")
        base_props.append(f"border-width: {self.border_width_slider.value()}px;")
        base_props.append("border-style: solid;")
        if border_c:
            base_props.append(f"border-color: {border_c};")

        hover_props = []
        hbg = self._button_color(self.hover_bg_btn)
        htext = self._button_color(self.hover_text_btn)
        hborder_c = self._button_color(self.hover_border_color_btn)
        if hbg:
            hover_props.append(f"background-color: {hbg};")
        if htext:
            hover_props.append(f"color: {htext};")
        hover_props.append(f"border-radius: {self.hover_border_radius_slider.value()}px;")
        hover_props.append(f"border-width: {self.hover_border_width_slider.value()}px;")
        hover_props.append("border-style: solid;")
        if hborder_c:
            hover_props.append(f"border-color: {hborder_c};")

        click_props = []
        cbg = self._button_color(self.click_bg_btn)
        ctext = self._button_color(self.click_text_btn)
        cborder_c = self._button_color(self.click_border_color_btn)
        if cbg:
            click_props.append(f"background-color: {cbg};")
        if ctext:
            click_props.append(f"color: {ctext};")
        click_props.append(f"border-radius: {self.click_border_radius_slider.value()}px;")
        click_props.append(f"border-width: {self.click_border_width_slider.value()}px;")
        click_props.append("border-style: solid;")
        if cborder_c:
            click_props.append(f"border-color: {cborder_c};")

        width = self.width_spin.value()
        height = self.height_spin.value()
        if width:
            self.preview_button.setFixedWidth(width)
        if height:
            self.preview_button.setFixedHeight(height)

        style = (
            f"QPushButton {{ {' '.join(base_props)} }} "
            f"QPushButton:hover {{ {' '.join(hover_props)} }} "
            f"QPushButton:pressed {{ {' '.join(click_props)} }}"
        )
        self.preview_button.setStyleSheet(style)

    def _refresh_condition_table(self):
        self.condition_table.setRowCount(0)
        for i, cond in enumerate(self.conditions):
            self.condition_table.insertRow(i)
            self.condition_table.setItem(i, 0, QTableWidgetItem(cond.tag_path))
            self.condition_table.setItem(i, 1, QTableWidgetItem(cond.operator))
            self.condition_table.setItem(i, 2, QTableWidgetItem(str(cond.value)))
            self.condition_table.setItem(i, 3, QTableWidgetItem(str(cond.value2) if cond.value2 is not None else ""))

    def _add_condition(self):
        dlg = ConditionEditorDialog(self)
        if dlg.exec():
            self.conditions.append(dlg.get_condition())
            self._refresh_condition_table()

    def _edit_condition(self):
        rows = self.condition_table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        cond = self.conditions[row]
        dlg = ConditionEditorDialog(self, cond)
        if dlg.exec():
            self.conditions[row] = dlg.get_condition()
            self._refresh_condition_table()

    def _remove_condition(self):
        rows = self.condition_table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        if 0 <= row < len(self.conditions):
            del self.conditions[row]
            self._refresh_condition_table()

    def get_style(self) -> ConditionalStyle:
        properties = {
            "background_color": self._button_color(self.bg_color_btn),
            "text_color": self._button_color(self.text_color_btn),
            "font_size": self.font_size_spin.value(),
            "width": self.width_spin.value(),
            "height": self.height_spin.value(),
            "border_radius": self.border_radius_slider.value(),
            "border_width": self.border_width_slider.value(),
            "border_color": self._button_color(self.border_color_btn),
        }

        hover_properties = {
            "background_color": self._button_color(self.hover_bg_btn),
            "text_color": self._button_color(self.hover_text_btn),
            "border_radius": self.hover_border_radius_slider.value(),
            "border_width": self.hover_border_width_slider.value(),
            "border_color": self._button_color(self.hover_border_color_btn),
        }

        click_properties = {
            "background_color": self._button_color(self.click_bg_btn),
            "text_color": self._button_color(self.click_text_btn),
            "border_radius": self.click_border_radius_slider.value(),
            "border_width": self.click_border_width_slider.value(),
            "border_color": self._button_color(self.click_border_color_btn),
        }

        style = ConditionalStyle(
            name=self.name_edit.text(),
            style_id=self.style.style_id,
            conditions=self.conditions,
            properties=properties,
            hover_properties=hover_properties,
            click_properties=click_properties,
            tooltip=self.tooltip_edit.text(),
            priority=self.priority_spin.value(),
        )
        return style