# components/button/conditional_style_editor_dialog.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox, QGroupBox,
    QPushButton, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QDialogButtonBox, QComboBox, QGridLayout, QLabel,
    QColorDialog, QSlider, QTabWidget, QWidget
)
from PyQt6.QtCore import Qt, QRect, QRectF
from PyQt6.QtGui import QPainter, QBrush, QPen, QColor
from button_creator import IconButton
from typing import Optional
import copy

from .conditional_style import ConditionalStyle, StyleCondition
from dialogs.widgets import TagSelector
from services.tag_data_service import tag_data_service


class PreviewButton(IconButton):
    """Simple button that paints itself using property dictionaries."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self.setText(text)
        self.base_properties = {}
        self.hover_properties = {}
        self.click_properties = {}
        self.setMouseTracking(True)

    # ------------------------------------------------------------------
    # Property setters
    # ------------------------------------------------------------------
    def set_base_properties(self, props: dict):
        self.base_properties = props or {}
        self.update()

    def set_hover_properties(self, props: dict):
        self.hover_properties = props or {}
        self.update()

    def set_click_properties(self, props: dict):
        self.click_properties = props or {}
        self.update()

    # ------------------------------------------------------------------
    # Event handling to update hover/press state
    # ------------------------------------------------------------------
    def enterEvent(self, e):
        super().enterEvent(e)
        self.update()

    def leaveEvent(self, e):
        super().leaveEvent(e)
        self.update()

    def mousePressEvent(self, e):
        self._is_pressed = True
        self.update()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._is_pressed = False
        self.update()
        super().mouseReleaseEvent(e)

    # ------------------------------------------------------------------
    def _current_properties(self):
        props = dict(self.base_properties)
        if self._is_pressed:
            props.update(self.click_properties)
        elif self.underMouse():
            props.update(self.hover_properties)
        return props

    def paintEvent(self, event):
        props = self._current_properties()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg = QColor(props.get("background_color", "#dcdcdc"))
        text_c = QColor(props.get("text_color", "#000000"))
        border_c = QColor(props.get("border_color", "#000000"))
        border_r = int(props.get("border_radius", 0))
        border_w = int(props.get("border_width", 0))

        rect = self.rect().adjusted(border_w // 2, border_w // 2,
                                    -border_w // 2, -border_w // 2)
        if border_w:
            painter.setPen(QPen(border_c, border_w))
        else:
            painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg))
        painter.drawRoundedRect(rect, border_r, border_r)

        font = self.font()
        if "font_size" in props:
            font.setPointSize(int(props["font_size"]))
        painter.setFont(font)
        painter.setPen(QPen(text_c))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())

        renderer = (self.svg_renderer_clicked if self._is_pressed and
                    self.svg_renderer_clicked else self.svg_renderer)
        if renderer:
            icon_rect = QRect(0, 0, self.icon_size.width(), self.icon_size.height())
            icon_rect.moveCenter(self.rect().center())
            renderer.render(painter, QRectF(icon_rect))


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

        # Style tabs
        style_tabs = QTabWidget()
        controls_layout.addWidget(style_tabs)

        # Base tab
        base_tab = QWidget(); base_layout = QGridLayout(base_tab)
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
        style_tabs.addTab(base_tab, "Base")

        # Hover tab
        hover_tab = QWidget(); hover_layout = QGridLayout(hover_tab)
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
        style_tabs.addTab(hover_tab, "Hover")

        # Click tab
        click_tab = QWidget(); click_layout = QGridLayout(click_tab)
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
        style_tabs.addTab(click_tab, "Click")

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
        self.preview_button = PreviewButton("Preview")
        self.preview_button.setMinimumSize(200, 100)
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
        base_props = {
            "background_color": self._button_color(self.bg_color_btn),
            "text_color": self._button_color(self.text_color_btn),
            "font_size": self.font_size_spin.value(),
            "border_radius": self.border_radius_slider.value(),
            "border_width": self.border_width_slider.value(),
            "border_color": self._button_color(self.border_color_btn),
        }

        hover_props = {
            "background_color": self._button_color(self.hover_bg_btn),
            "text_color": self._button_color(self.hover_text_btn),
            "border_radius": self.hover_border_radius_slider.value(),
            "border_width": self.hover_border_width_slider.value(),
            "border_color": self._button_color(self.hover_border_color_btn),
        }

        click_props = {
            "background_color": self._button_color(self.click_bg_btn),
            "text_color": self._button_color(self.click_text_btn),
            "border_radius": self.click_border_radius_slider.value(),
            "border_width": self.click_border_width_slider.value(),
            "border_color": self._button_color(self.click_border_color_btn),
        }

        width = self.width_spin.value() or 200
        height = self.height_spin.value() or 100
        self.preview_button.setFixedSize(width, height)
        self.preview_button.set_base_properties(base_props)
        self.preview_button.set_hover_properties(hover_props)
        self.preview_button.set_click_properties(click_props)

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