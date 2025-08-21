# dialogs/custom_widgets.py
# Contains custom, reusable widgets for various dialogs.

from PyQt6.QtWidgets import (
    QLineEdit, QWidget, QHBoxLayout, QVBoxLayout, QComboBox,
    QStackedWidget, QLabel, QFormLayout, QToolButton, QFrame, QSizePolicy
)
from PyQt6.QtGui import QDoubleValidator, QPainter, QColor, QPixmap, QPalette
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from typing import Optional, Dict, List
from enum import Enum

from .tag_browser_dialog import TagBrowserDialog
from services.tag_data_service import tag_data_service
from utils.icon_manager import IconManager

class CollapsibleBox(QWidget):
    """
    A collapsible group box widget with status indicators.
    """
    class Status(Enum):
        NEUTRAL = 0
        OK = 1
        ERROR = 2
        
    toggled = pyqtSignal(bool)

    def __init__(self, title="", parent=None):
        super(CollapsibleBox, self).__init__(parent)

        self.toggle_button = QToolButton(self)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.ArrowType.RightArrow)
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.setAutoRaise(True)
        font = self.toggle_button.font()
        font.setBold(True)
        self.toggle_button.setFont(font)

        self.status_label = QLabel(self)
        self.status_label.setFixedSize(12, 12)

        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0,0,0,0)
        title_layout.setSpacing(5)
        title_layout.addWidget(self.toggle_button)
        title_layout.addStretch()
        title_layout.addWidget(self.status_label)

        self.header_line = QFrame(self)
        self.header_line.setFrameShape(QFrame.Shape.HLine)
        self.header_line.setFrameShadow(QFrame.Shadow.Sunken)

        self.content_area = QWidget(self)
        self.content_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.content_area.setMaximumHeight(0)
        self.content_area.setMinimumHeight(0)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addLayout(title_layout)
        main_layout.addWidget(self.header_line)
        main_layout.addWidget(self.content_area)

        self.toggle_button.toggled.connect(self.toggle)
        self.is_checkable = False
        self.setStatus(self.Status.NEUTRAL)

    def setStatus(self, status: Status):
        pixmap = QPixmap(self.status_label.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        
        if status == self.Status.OK:
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor("#4CAF50")) # Green
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(0, 0, 10, 10)
            painter.end()
        elif status == self.Status.ERROR:
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor("#F44336")) # Red
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(0, 0, 10, 10)
            painter.end()
            
        self.status_label.setPixmap(pixmap)

    def setContent(self, widget: QWidget):
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.addWidget(widget)

    def toggle(self, checked):
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
        
        if checked:
            self.content_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.content_area.setMaximumHeight(16777215)
        else:
            self.content_area.setMaximumHeight(0)
            self.content_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        if self.is_checkable:
            self.toggled.emit(checked)

    def setCheckable(self, checkable: bool):
        self.is_checkable = checkable

    def setChecked(self, checked: bool):
        if self.is_checkable:
            self.toggle_button.setChecked(checked)

    def isChecked(self) -> bool:
        return self.toggle_button.isChecked() if self.is_checkable else True

    def setExpanded(self, expanded: bool):
        self.toggle_button.setChecked(expanded)


class TagLineEdit(QLineEdit):
    """A custom QLineEdit that emits a signal on a double-click event."""
    doubleClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Double-click to select a tag...")

    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit()
        event.accept()

class ValueSelector(QWidget):
    """A compound widget for selecting either a constant value or a tag."""
    tagChanged = pyqtSignal(object)
    inputChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_tag_info = None
        self.allowed_tag_types = None
        self.allow_arrays = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0,0,0,0)
        input_layout.setSpacing(5)

        self.source_combo = QComboBox()
        self.source_combo.addItems(["Constant", "Tag"])
        
        self.input_stack = QStackedWidget()
        self.constant_input = QLineEdit()
        self.constant_input.setValidator(QDoubleValidator())
        self.tag_input = TagLineEdit()
        
        self.input_stack.addWidget(self.constant_input)
        self.input_stack.addWidget(self.tag_input)
        
        input_layout.addWidget(self.source_combo)
        input_layout.addWidget(self.input_stack, 1)
        layout.addLayout(input_layout)

        self.error_label = QLabel()
        palette = self.error_label.palette()
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#E57373"))
        self.error_label.setPalette(palette)
        self.error_label.setIndent(5)
        self.error_label.setVisible(False)
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        self.source_combo.currentIndexChanged.connect(self.input_stack.setCurrentIndex)
        self.tag_input.doubleClicked.connect(self._browse_for_tag)

        self.source_combo.currentIndexChanged.connect(self.inputChanged.emit)
        self.constant_input.textChanged.connect(self.inputChanged.emit)
        
    def _browse_for_tag(self):
        dialog = TagBrowserDialog(self, allowed_types=self.allowed_tag_types, allow_arrays=self.allow_arrays)
        if dialog.exec():
            self.selected_tag_info = dialog.get_selected_tag_info()
            tag_data = None 
            if self.selected_tag_info:
                db_id, db_name, tag_name = self.selected_tag_info
                self.tag_input.setText(f"[{db_name}]::{tag_name}")
                tag_data = tag_data_service.get_tag(db_id, tag_name)
            else:
                self.tag_input.clear()
            self.tagChanged.emit(tag_data)
            self.inputChanged.emit()

    def set_allowed_tag_types(self, types):
        self.allowed_tag_types = types

    def set_allow_arrays(self, allow: bool):
        self.allow_arrays = allow

    def get_data(self):
        mode = self.source_combo.currentText()
        if mode == "Tag":
            if not self.selected_tag_info: return None
            return {"source": "tag", "value": {"db_id": self.selected_tag_info[0], "db_name": self.selected_tag_info[1], "tag_name": self.selected_tag_info[2]}}
        else:
            text_value = self.constant_input.text()
            if not text_value: return None
            return {"source": "constant", "value": text_value}

    def set_data(self, data: Optional[Dict]):
        if not data:
            self.tagChanged.emit(None)
            return

        source = data.get("source", "constant")
        value = data.get("value")
        
        if source == "tag" and isinstance(value, dict):
            self.source_combo.setCurrentIndex(1)
            db_id, db_name, tag_name = value.get("db_id"), value.get("db_name"), value.get("tag_name")
            self.selected_tag_info = (db_id, db_name, tag_name)
            self.tag_input.setText(f"[{db_name}]::{tag_name}")
            
            tag_data = tag_data_service.get_tag(db_id, tag_name) if db_id and tag_name else None
            self.tagChanged.emit(tag_data)
        else:
            self.source_combo.setCurrentIndex(0)
            self.constant_input.setText(str(value))
            self.tagChanged.emit(None)
    
    def set_mode_fixed(self, mode: str):
        if mode == "Tag":
            self.source_combo.setCurrentIndex(1)
        else:
            self.source_combo.setCurrentIndex(0)
        self.source_combo.setVisible(False)

    def setError(self, message: Optional[str]):
        try:
            if hasattr(self, 'error_label') and self.error_label is not None:
                self.error_label.setText(message or "")
                self.error_label.setVisible(bool(message))
                self.setProperty("error", bool(message))
                self.style().polish(self)
        except (RuntimeError, AttributeError):
            # QLabel has been deleted, ignore the error
            pass

class TagSelector(QWidget):
    """An advanced widget that handles selecting a main tag and its array indices."""
    tag_selected = pyqtSignal(object)
    inputChanged = pyqtSignal()

    def __init__(self, parent=None, allowed_tag_types: Optional[List[str]] = None):
        super().__init__(parent)
        self.main_tag_info = None
        self.index_selectors = []
        self.allowed_tag_types = None
        self.current_tag_data = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)
        
        self.main_tag_selector = ValueSelector()
        self.main_tag_selector.tagChanged.connect(self._on_main_tag_changed)
        self.main_tag_selector.inputChanged.connect(self.inputChanged.emit)

        self.main_tag_frame = QFrame()
        self.main_tag_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.main_tag_frame.setLineWidth(1)
        frame_layout = QVBoxLayout(self.main_tag_frame)
        frame_layout.setContentsMargins(2, 2, 2, 2)
        frame_layout.addWidget(self.main_tag_selector)
        main_layout.addWidget(self.main_tag_frame)
        
        self.index_widget = QWidget()
        self.index_layout = QFormLayout(self.index_widget)
        self.index_layout.setContentsMargins(10, 5, 0, 0)
        self.index_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        self.index_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        main_layout.addWidget(self.index_widget)
        
        main_layout.addStretch(1)

        self.setObjectName("TagSelector")
        
        self._update_index_fields(None)
        
        if allowed_tag_types:
            self.set_allowed_tag_types(allowed_tag_types)

    def _on_main_tag_changed(self, tag_data: Optional[Dict]):
        self.current_tag_data = tag_data
        if tag_data:
            self.main_tag_info = (tag_data.get('db_id'), tag_data.get('db_name'), tag_data.get('name'))
        else:
            self.main_tag_info = None
            
        self._update_index_fields(tag_data)
        self.tag_selected.emit(tag_data)

    def _update_index_fields(self, tag_data: Optional[Dict]):
        while self.index_layout.count():
            item = self.index_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.index_selectors.clear()
        
        is_array = tag_data and tag_data.get("array_dims")
        self.index_widget.setVisible(bool(is_array))
        if not is_array:
            return

        for i, dim_size in enumerate(tag_data["array_dims"]):
            index_selector = ValueSelector()
            index_selector.set_allowed_tag_types(["INT16"])
            index_selector.set_allow_arrays(False)
            index_selector.inputChanged.connect(self.inputChanged.emit)
            self.index_layout.addRow(f"Index {i+1}:", index_selector)
            self.index_selectors.append(index_selector)

    def set_allowed_tag_types(self, types: list):
        self.allowed_tag_types = types
        self.main_tag_selector.set_allowed_tag_types(types)
        
        if self.current_tag_data:
            current_type = self.current_tag_data.get("data_type")
            type_map = {"INT": "INT16", "DINT": "INT32"}
            current_type = type_map.get(current_type, current_type)
            
            if current_type not in types:
                self.main_tag_selector.tag_input.clear()
                self._on_main_tag_changed(None)
    
    def get_data(self) -> Optional[Dict]:
        main_tag_data = self.main_tag_selector.get_data()
        if not main_tag_data: return None

        if main_tag_data.get("source") == "constant":
            return {"main_tag": main_tag_data, "indices": []}

        if not self.current_tag_data: return None

        data = {"main_tag": main_tag_data, "indices": []}
        for index_selector in self.index_selectors:
            index_data = index_selector.get_data()
            if not index_data: return None
            data["indices"].append(index_data)
        
        return data

    def set_data(self, data: Optional[Dict]):
        if not data:
            self.main_tag_selector.set_data(None)
            return

        self.main_tag_selector.set_data(data.get("main_tag"))
        indices_data = data.get("indices", [])
        if len(indices_data) == len(self.index_selectors):
            for i, index_data in enumerate(indices_data):
                self.index_selectors[i].set_data(index_data)
    
    def setError(self, message: Optional[str]):
        try:
            self.main_tag_selector.setError(message)
            self.setProperty("error", bool(message))
            self.style().polish(self)
        except (RuntimeError, AttributeError):
            # Widget has been deleted, ignore the error
            pass

    def clear_errors_recursive(self):
        try:
            self.setError(None)
            for selector in self.index_selectors:
                try:
                    selector.setError(None)
                except (RuntimeError, AttributeError):
                    # Selector has been deleted, skip it
                    pass
        except (RuntimeError, AttributeError):
            # Widget has been deleted, ignore the error
            pass
