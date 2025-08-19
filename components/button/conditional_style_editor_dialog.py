# components/button/conditional_style_editor_dialog.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox, QGroupBox,
    QPushButton, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QDialogButtonBox, QComboBox
)
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

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.name_edit = QLineEdit(self.style.name)
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(-100000, 100000)
        self.priority_spin.setValue(self.style.priority)
        # Tooltip is now stored separately from properties
        self.tooltip_edit = QLineEdit(self.style.tooltip)
        form.addRow("Name:", self.name_edit)
        form.addRow("Priority:", self.priority_spin)
        form.addRow("Tooltip:", self.tooltip_edit)
        layout.addLayout(form)

        # Base style group
        base_group = QGroupBox("Base Style")
        base_form = QFormLayout(base_group)
        self.bg_color_edit = QLineEdit(self.style.properties.get("background_color", ""))
        self.text_color_edit = QLineEdit(self.style.properties.get("text_color", ""))
        self.font_size_spin = QSpinBox(); self.font_size_spin.setRange(1, 1000)
        self.font_size_spin.setValue(self.style.properties.get("font_size", 10))
        self.width_spin = QSpinBox(); self.width_spin.setRange(0, 10000)
        self.width_spin.setValue(self.style.properties.get("width", 0))
        self.height_spin = QSpinBox(); self.height_spin.setRange(0, 10000)
        self.height_spin.setValue(self.style.properties.get("height", 0))
        # Shape attributes
        self.border_radius_spin = QSpinBox(); self.border_radius_spin.setRange(0, 1000)
        self.border_radius_spin.setValue(self.style.properties.get("border_radius", 0))
        self.border_width_spin = QSpinBox(); self.border_width_spin.setRange(0, 1000)
        self.border_width_spin.setValue(self.style.properties.get("border_width", 0))
        self.border_color_edit = QLineEdit(self.style.properties.get("border_color", ""))
        base_form.addRow("Background:", self.bg_color_edit)
        base_form.addRow("Text Color:", self.text_color_edit)
        base_form.addRow("Font Size:", self.font_size_spin)
        base_form.addRow("Width:", self.width_spin)
        base_form.addRow("Height:", self.height_spin)
        base_form.addRow("Border Radius:", self.border_radius_spin)
        base_form.addRow("Border Width:", self.border_width_spin)
        base_form.addRow("Border Color:", self.border_color_edit)
        layout.addWidget(base_group)

        # Hover style group
        hover_group = QGroupBox("Hover Style")
        hover_form = QFormLayout(hover_group)
        self.hover_bg_edit = QLineEdit(self.style.hover_properties.get("background_color", ""))
        self.hover_text_edit = QLineEdit(self.style.hover_properties.get("text_color", ""))
        self.hover_border_radius_spin = QSpinBox(); self.hover_border_radius_spin.setRange(0, 1000)
        self.hover_border_radius_spin.setValue(self.style.hover_properties.get("border_radius", 0))
        self.hover_border_width_spin = QSpinBox(); self.hover_border_width_spin.setRange(0, 1000)
        self.hover_border_width_spin.setValue(self.style.hover_properties.get("border_width", 0))
        self.hover_border_color_edit = QLineEdit(self.style.hover_properties.get("border_color", ""))
        hover_form.addRow("Background:", self.hover_bg_edit)
        hover_form.addRow("Text Color:", self.hover_text_edit)
        hover_form.addRow("Border Radius:", self.hover_border_radius_spin)
        hover_form.addRow("Border Width:", self.hover_border_width_spin)
        hover_form.addRow("Border Color:", self.hover_border_color_edit)
        layout.addWidget(hover_group)

        # Click style group
        click_group = QGroupBox("Click Style")
        click_form = QFormLayout(click_group)
        self.click_bg_edit = QLineEdit(self.style.click_properties.get("background_color", ""))
        self.click_text_edit = QLineEdit(self.style.click_properties.get("text_color", ""))
        self.click_border_radius_spin = QSpinBox(); self.click_border_radius_spin.setRange(0, 1000)
        self.click_border_radius_spin.setValue(self.style.click_properties.get("border_radius", 0))
        self.click_border_width_spin = QSpinBox(); self.click_border_width_spin.setRange(0, 1000)
        self.click_border_width_spin.setValue(self.style.click_properties.get("border_width", 0))
        self.click_border_color_edit = QLineEdit(self.style.click_properties.get("border_color", ""))
        click_form.addRow("Background:", self.click_bg_edit)
        click_form.addRow("Text Color:", self.click_text_edit)
        click_form.addRow("Border Radius:", self.click_border_radius_spin)
        click_form.addRow("Border Width:", self.click_border_width_spin)
        click_form.addRow("Border Color:", self.click_border_color_edit)
        layout.addWidget(click_group)

        # Conditions group
        cond_group = QGroupBox("Conditions")
        cond_layout = QVBoxLayout(cond_group)
        self.condition_table = QTableWidget()
        self.condition_table.setColumnCount(4)
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
        add_cond_btn = QPushButton("Add")
        edit_cond_btn = QPushButton("Edit")
        remove_cond_btn = QPushButton("Remove")
        add_cond_btn.clicked.connect(self._add_condition)
        edit_cond_btn.clicked.connect(self._edit_condition)
        remove_cond_btn.clicked.connect(self._remove_condition)
        cond_buttons.addWidget(add_cond_btn)
        cond_buttons.addWidget(edit_cond_btn)
        cond_buttons.addWidget(remove_cond_btn)
        cond_buttons.addStretch()
        cond_layout.addLayout(cond_buttons)
        layout.addWidget(cond_group)

        self._refresh_condition_table()

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

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
            "background_color": self.bg_color_edit.text(),
            "text_color": self.text_color_edit.text(),
            "font_size": self.font_size_spin.value(),
            "width": self.width_spin.value(),
            "height": self.height_spin.value(),
            "border_radius": self.border_radius_spin.value(),
            "border_width": self.border_width_spin.value(),
            "border_color": self.border_color_edit.text(),
        }

        hover_properties = {
            "background_color": self.hover_bg_edit.text(),
            "text_color": self.hover_text_edit.text(),
            "border_radius": self.hover_border_radius_spin.value(),
            "border_width": self.hover_border_width_spin.value(),
            "border_color": self.hover_border_color_edit.text(),
        }

        click_properties = {
            "background_color": self.click_bg_edit.text(),
            "text_color": self.click_text_edit.text(),
            "border_radius": self.click_border_radius_spin.value(),
            "border_width": self.click_border_width_spin.value(),
            "border_color": self.click_border_color_edit.text(),
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