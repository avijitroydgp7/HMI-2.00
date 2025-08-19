import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QGridLayout,
    QLabel, QSlider,
    QTextEdit, QGroupBox, QComboBox, QSpinBox, QHBoxLayout,
    QCheckBox, QStyle, QScrollArea, QStackedWidget, QFileDialog,
    QListWidget, QListWidgetItem, QDialog, QDialogButtonBox
)
from PyQt6.QtGui import QColor, QPalette, QIcon, QPixmap, QPainter, QBrush, QPen
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QPoint, QEasingCurve, pyqtProperty, QRect, QRectF
from PyQt6.QtSvg import QSvgRenderer, QSvgGenerator

class IconBrowser(QDialog):
    """A graphical dialog to browse and select SVG icons from a folder."""
    def __init__(self, folder_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Icon Browser")
        self.setFixedSize(600, 400)
        self.selected_icon_path = ""

        layout = QVBoxLayout(self)
        self.icon_list = QListWidget()
        self.icon_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.icon_list.setIconSize(QSize(64, 64))
        self.icon_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.icon_list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.icon_list)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.populate_icons(folder_path)

    def populate_icons(self, folder_path):
        for file_name in os.listdir(folder_path):
            if file_name.endswith(".svg"):
                file_path = os.path.join(folder_path, file_name)
                icon = QIcon(file_path)
                item = QListWidgetItem(icon, file_name)
                item.setData(Qt.ItemDataRole.UserRole, file_path)
                self.icon_list.addItem(item)
    
    def accept(self):
        if self.icon_list.currentItem():
            self.selected_icon_path = self.icon_list.currentItem().data(Qt.ItemDataRole.UserRole)
        super().accept()

class SwitchButton(QPushButton):
    """A custom toggle switch that inherits from QPushButton for styling."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 100)

        self._handle_x_pos = 50
        self.animation = QPropertyAnimation(self, b"handle_x_pos", self)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.setDuration(200)

        self._handle_color = QColor("white")
        self._on_is_left = False # Default: 'on' state is on the right
        
        self.set_alignment(False) # Set initial state based on default alignment

    @pyqtProperty(int)
    def handle_x_pos(self):
        return self._handle_x_pos

    @handle_x_pos.setter
    def handle_x_pos(self, pos):
        self._handle_x_pos = pos
        self.update()

    def set_alignment(self, on_is_left):
        """Sets the toggle direction and initial state."""
        self._on_is_left = on_is_left
        # Immediately move handle to the 'off' position without animation
        off_pos = self.width() - 50 if self._on_is_left else 50
        self.handle_x_pos = off_pos

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        brush = QBrush(self._handle_color)
        painter.setBrush(brush)
        painter.setPen(Qt.PenStyle.NoPen)
        
        handle_y = self.height() / 2
        handle_center = QPoint(self.handle_x_pos, int(handle_y))
        painter.drawEllipse(handle_center, 40, 40)

    def mousePressEvent(self, e):
        on_pos = 50 if self._on_is_left else self.width() - 50
        self.animation.setEndValue(on_pos)
        self.animation.start()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        off_pos = self.width() - 50 if self._on_is_left else 50
        self.animation.setEndValue(off_pos)
        self.animation.start()
        super().mouseReleaseEvent(e)

class IconButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.svg_renderer = None
        self.svg_renderer_clicked = None
        self.icon_size = QSize(50, 50)
        self._is_pressed = False

    def set_icon(self, path):
        if path:
            self.svg_renderer = QSvgRenderer(path)
        else:
            self.svg_renderer = None
        self.update()

    def set_icon_clicked(self, path):
        if path:
            self.svg_renderer_clicked = QSvgRenderer(path)
        else:
            self.svg_renderer_clicked = None
        self.update()

    def set_icon_size(self, size):
        self.icon_size = QSize(size, size)
        self.update()

    def mousePressEvent(self, e):
        self._is_pressed = True
        self.update()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self._is_pressed = False
        self.update()
        super().mouseReleaseEvent(e)

    def paintEvent(self, event):
        super().paintEvent(event)
        
        renderer = self.svg_renderer_clicked if self._is_pressed and self.svg_renderer_clicked else self.svg_renderer

        if renderer:
            painter = QPainter(self)
            target_rect = self.rect()
            icon_rect = QRect(0, 0, self.icon_size.width(), self.icon_size.height())
            icon_rect.moveCenter(target_rect.center())
            renderer.render(painter, QRectF(icon_rect))


class ComponentDesignerApp(QWidget):
    """
    An application for interactively designing UI components using PyQt6.
    """
    def __init__(self):
        super().__init__()
        self._ui_ready = False
        self.init_paths()
        self.init_colors()
        self.init_ui()

    def init_paths(self):
        """Defines and checks for the required svg folder."""
        try:
            # For running from a script
            script_dir = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            # For running in interactive environments
            script_dir = os.getcwd()
        self.icon_folder_path = os.path.join(script_dir, 'svg')
        if not os.path.isdir(self.icon_folder_path):
            print(f"Warning: 'svg' folder not found at {self.icon_folder_path}")
            self.icon_folder_path = None

    def init_colors(self):
        """Initialize predefined color schemes."""
        self.color_schemes = {
            "Blue": {"main": QColor("#3498db"), "hover": QColor("#5dade2"), "border": QColor("#2980b9"), "gradient2": QColor("#8e44ad")},
            "Red": {"main": QColor("#e74c3c"), "hover": QColor("#ec7063"), "border": QColor("#c0392b"), "gradient2": QColor("#d35400")},
            "Green": {"main": QColor("#2ecc71"), "hover": QColor("#58d68d"), "border": QColor("#27ae60"), "gradient2": QColor("#16a085")},
            "Orange": {"main": QColor("#e67e22"), "hover": QColor("#eb984e"), "border": QColor("#d35400"), "gradient2": QColor("#f39c12")},
            "Cyan": {"main": QColor("#1abc9c"), "hover": QColor("#48c9b0"), "border": QColor("#16a085"), "gradient2": QColor("#1abc9c")},
            "Purple": {"main": QColor("#9b59b6"), "hover": QColor("#af7ac5"), "border": QColor("#8e44ad"), "gradient2": QColor("#3498db")},
            "Pink": {"main": QColor("#fd79a8"), "hover": QColor("#fd9db4"), "border": QColor("#e75c90"), "gradient2": QColor("#9b59b6")},
            "Teal": {"main": QColor("#008080"), "hover": QColor("#009688"), "border": QColor("#00695C"), "gradient2": QColor("#4DB6AC")},
            "Indigo": {"main": QColor("#3F51B5"), "hover": QColor("#5C6BC0"), "border": QColor("#303F9F"), "gradient2": QColor("#7986CB")},
            "Crimson": {"main": QColor("#DC143C"), "hover": QColor("#E53935"), "border": QColor("#C62828"), "gradient2": QColor("#EF5350")},
            "Gray": {"main": QColor("#95a5a6"), "hover": QColor("#bdc3c7"), "border": QColor("#7f8c8d"), "gradient2": QColor("#bdc3c7")},
            "Black": {"main": QColor("#34495e"), "hover": QColor("#4a6276"), "border": QColor("#2c3e50"), "gradient2": QColor("#2c3e50")},
            "White": {"main": QColor("#ecf0f1"), "hover": QColor("#ffffff"), "border": QColor("#bdc3c7"), "gradient2": QColor("#bdc3c7")}
        }
        self.base_colors = {name: scheme["main"] for name, scheme in self.color_schemes.items()}


    def get_shades(self, color_name):
        """Generate 16 shades for a given base color."""
        base_color = self.base_colors.get(color_name, QColor("#000000"))
        shades = []
        for i in range(16):
            factor = 1.2 - (i / 15.0) * 0.6
            shades.append(base_color.lighter(int(100 * factor)) if factor > 1.0 else base_color.darker(int(100 / factor)))
        return shades


    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle('PyQt Component Designer')
        self.setGeometry(100, 100, 900, 700)

        main_layout = QGridLayout(self)
        main_layout.setColumnStretch(0, 1)
        main_layout.setColumnStretch(1, 1)

        preview_layout = QVBoxLayout()
        preview_group = QGroupBox()
        preview_group.setStyleSheet("background-color: #4a4a4a; border: none;")
        preview_group_layout = QVBoxLayout()
        preview_group_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.preview_stack = QStackedWidget()
        self.preview_button = IconButton("")
        self.preview_button.setMinimumSize(200, 100)
        self.preview_switch = SwitchButton()

        self.preview_stack.addWidget(self.preview_button)
        self.preview_stack.addWidget(self.preview_switch)

        preview_group_layout.addWidget(self.preview_stack)
        preview_group.setLayout(preview_group_layout)
        
        preview_layout.addStretch(1)
        preview_layout.addWidget(preview_group)
        preview_layout.addStretch(1)

        code_group = QGroupBox("Generated QSS Code")
        code_group_layout = QVBoxLayout()
        self.code_display = QTextEdit()
        self.code_display.setReadOnly(True)
        self.code_display.setMinimumHeight(100) # Ensure visibility
        copy_button = QPushButton("Copy to Clipboard")
        copy_button.clicked.connect(self.copy_code_to_clipboard)
        export_button = QPushButton("Export to SVG")
        export_button.clicked.connect(self.export_to_svg)
        export_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1abc9c;
            }
        """)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(copy_button)
        button_layout.addWidget(export_button)
        
        code_group_layout.addWidget(self.code_display)
        code_group_layout.addLayout(button_layout)
        preview_layout.addWidget(code_group, 1)

        main_layout.addLayout(preview_layout, 0, 1)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content_widget = QWidget()
        controls_layout = QVBoxLayout(scroll_content_widget)

        style_group = QGroupBox("Component Style")
        style_layout = QGridLayout()
        style_layout.addWidget(QLabel("Component Type:"), 0, 0)
        self.component_type_combo = QComboBox()
        self.component_type_combo.addItems(["Standard Button", "Circle Button", "Square Button", "Toggle Switch"])
        self.component_type_combo.currentTextChanged.connect(self.update_controls_state)
        style_layout.addWidget(self.component_type_combo, 0, 1)

        self.shape_style_label = QLabel("Shape Style:")
        style_layout.addWidget(self.shape_style_label, 1, 0)
        self.shape_style_combo = QComboBox()
        self.shape_style_combo.addItems(["Flat", "3D", "Glass", "Neumorphic", "Outline"])
        self.shape_style_combo.currentTextChanged.connect(self.update_controls_state)
        style_layout.addWidget(self.shape_style_combo, 1, 1)
        
        self.align_label = QLabel("On Click Align:")
        style_layout.addWidget(self.align_label, 2, 0)
        self.align_combo = QComboBox()
        self.align_combo.addItems(["Right", "Left"])
        self.align_combo.currentTextChanged.connect(self.on_alignment_changed)
        style_layout.addWidget(self.align_combo, 2, 1)
        
        style_group.setLayout(style_layout)
        controls_layout.addWidget(style_group)

        # SVG Icon Controls
        self.icon_group = QGroupBox("SVG Icon")
        icon_layout = QGridLayout()
        self.icon_checkbox = QCheckBox("Enable SVG Icon")
        self.icon_checkbox.toggled.connect(self.update_controls_state)
        icon_layout.addWidget(self.icon_checkbox, 0, 0, 1, 2)
        
        self.icon_path_button = QPushButton("Choose Icon")
        self.icon_path_button.clicked.connect(self.choose_icon)
        icon_layout.addWidget(self.icon_path_button, 1, 0, 1, 2)

        self.use_different_icon_checkbox = QCheckBox("Use Different Icon on Click")
        self.use_different_icon_checkbox.toggled.connect(self.update_controls_state)
        icon_layout.addWidget(self.use_different_icon_checkbox, 2, 0, 1, 2)

        self.icon_path_button_clicked = QPushButton("Choose Clicked Icon")
        self.icon_path_button_clicked.clicked.connect(self.choose_icon_clicked)
        icon_layout.addWidget(self.icon_path_button_clicked, 3, 0, 1, 2)

        icon_layout.addWidget(QLabel("Icon Size (px):"), 4, 0)
        self.icon_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.icon_size_slider.setRange(10, 100)
        self.icon_size_slider.setValue(50)
        self.icon_size_slider.valueChanged.connect(self.on_icon_size_changed)
        icon_layout.addWidget(self.icon_size_slider, 4, 1)
        
        self.icon_group.setLayout(icon_layout)
        controls_layout.addWidget(self.icon_group)

        if not self.icon_folder_path:
            self.icon_group.setEnabled(False)
            self.icon_group.setTitle("SVG Icon (folder not found)")

        self.background_group = QGroupBox("Background & Padding")
        background_layout = QGridLayout()
        background_layout.addWidget(QLabel("Background Type:"), 0, 0)
        self.bg_type_combo = QComboBox()
        self.bg_type_combo.addItems(["Solid", "Linear Gradient"])
        self.bg_type_combo.currentTextChanged.connect(self.update_controls_state)
        background_layout.addWidget(self.bg_type_combo, 0, 1)

        background_layout.addWidget(QLabel("Main Color:"), 1, 0)
        self.bg_base_color_combo, self.bg_shade_combo = self.create_color_selection_widgets(self.on_bg_color_changed)
        background_layout.addWidget(self.bg_base_color_combo, 1, 1)
        background_layout.addWidget(self.bg_shade_combo, 2, 1)

        self.gradient_coords_label = QLabel("Gradient Coords (x1,y1,x2,y2):")
        background_layout.addWidget(self.gradient_coords_label, 3, 0, 1, 2)
        coords_layout = QHBoxLayout()
        self.x1_spin, self.y1_spin = self.create_coord_spinbox(), self.create_coord_spinbox()
        self.x2_spin, self.y2_spin = self.create_coord_spinbox(0), self.create_coord_spinbox(1)
        coords_layout.addWidget(self.x1_spin); coords_layout.addWidget(self.y1_spin)
        coords_layout.addWidget(self.x2_spin); coords_layout.addWidget(self.y2_spin)
        background_layout.addLayout(coords_layout, 4, 0, 1, 2)
        self.gradient_spread_label = QLabel("Gradient Spread:")
        background_layout.addWidget(self.gradient_spread_label, 5, 0)
        self.spread_combo = QComboBox()
        self.spread_combo.addItems(["pad", "reflect", "repeat"])
        self.spread_combo.currentTextChanged.connect(self.update_button_style)
        background_layout.addWidget(self.spread_combo, 5, 1)
        
        self.padding_label = QLabel("Padding (px):")
        background_layout.addWidget(self.padding_label, 6, 0)
        self.padding_slider = QSlider(Qt.Orientation.Horizontal)
        self.padding_slider.setRange(0, 50); self.padding_slider.setValue(15)
        self.padding_slider.valueChanged.connect(self.update_button_style)
        background_layout.addWidget(self.padding_slider, 6, 1)
        self.background_group.setLayout(background_layout)
        controls_layout.addWidget(self.background_group)

        self.border_group = QGroupBox("Border")
        border_layout = QGridLayout()

        self.tl_radius_label = QLabel("Top-Left Radius:")
        border_layout.addWidget(self.tl_radius_label, 0, 0)
        self.tl_radius_slider = self.create_radius_slider()
        border_layout.addWidget(self.tl_radius_slider, 0, 1)

        self.tr_radius_label = QLabel("Top-Right Radius:")
        border_layout.addWidget(self.tr_radius_label, 1, 0)
        self.tr_radius_slider = self.create_radius_slider()
        border_layout.addWidget(self.tr_radius_slider, 1, 1)

        self.br_radius_label = QLabel("Bottom-Right Radius:")
        border_layout.addWidget(self.br_radius_label, 2, 0)
        self.br_radius_slider = self.create_radius_slider()
        border_layout.addWidget(self.br_radius_slider, 2, 1)

        self.bl_radius_label = QLabel("Bottom-Left Radius:")
        border_layout.addWidget(self.bl_radius_label, 3, 0)
        self.bl_radius_slider = self.create_radius_slider()
        border_layout.addWidget(self.bl_radius_slider, 3, 1)

        border_layout.addWidget(QLabel("Border Width (px):"), 4, 0)
        self.border_width_slider = QSlider(Qt.Orientation.Horizontal)
        self.border_width_slider.setRange(0, 10); self.border_width_slider.setValue(2)
        self.border_width_slider.valueChanged.connect(self.update_button_style)
        border_layout.addWidget(self.border_width_slider, 4, 1)

        self.border_style_label = QLabel("Border Style:")
        border_layout.addWidget(self.border_style_label, 5, 0)
        self.border_style_combo = QComboBox()
        self.border_style_combo.addItems(["none", "solid", "dashed", "dotted", "double", "groove", "ridge"])
        self.border_style_combo.currentTextChanged.connect(self.update_button_style)
        border_layout.addWidget(self.border_style_combo, 5, 1)

        self.border_group.setLayout(border_layout)
        controls_layout.addWidget(self.border_group)

        controls_layout.addStretch(1)

        scroll_area.setWidget(scroll_content_widget)
        main_layout.addWidget(scroll_area, 0, 0)
        
        self._ui_ready = True
        self.set_initial_colors()
        self.update_controls_state()

    def create_color_selection_widgets(self, final_slot):
        base_combo = QComboBox()
        for color_name, color_value in self.base_colors.items():
            pixmap = QPixmap(16, 16)
            pixmap.fill(color_value)
            base_combo.addItem(QIcon(pixmap), color_name)

        shade_combo = QComboBox()

        def update_shades(color_name):
            shade_combo.blockSignals(True)
            shade_combo.clear()
            shades = self.get_shades(color_name)
            for i, shade in enumerate(shades):
                pixmap = QPixmap(16, 16)
                pixmap.fill(shade)
                shade_combo.addItem(QIcon(pixmap), f"Shade {i+1}")
                shade_combo.setItemData(i, shade)
            shade_combo.setCurrentIndex(7)
            shade_combo.blockSignals(False)
            final_slot(color_name, shade_combo.currentData())

        base_combo.currentTextChanged.connect(update_shades)
        shade_combo.currentIndexChanged.connect(lambda: final_slot(base_combo.currentText(), shade_combo.currentData()))

        return base_combo, shade_combo

    def on_bg_color_changed(self, color_name, color):
        if not self._ui_ready or not color: return
        
        scheme = self.color_schemes.get(color_name)
        if scheme:
            self._bg_color = color
            self._hover_bg_color = scheme["hover"]
            self._border_color = scheme["border"]
            self._bg_color2 = scheme["gradient2"]
        
        self.update_button_style()
        
    def on_alignment_changed(self, text):
        if not self._ui_ready: return
        self.preview_switch.set_alignment(text == "Left")

    def _open_icon_browser(self):
        if self.icon_folder_path:
            browser = IconBrowser(self.icon_folder_path, self)
            if browser.exec():
                return browser.selected_icon_path
        return None

    def choose_icon(self):
        icon_path = self._open_icon_browser()
        if icon_path:
            self.preview_button.set_icon(icon_path)

    def choose_icon_clicked(self):
        icon_path = self._open_icon_browser()
        if icon_path:
            self.preview_button.set_icon_clicked(icon_path)

    def on_icon_size_changed(self, value):
        if not self._ui_ready: return
        self.preview_button.set_icon_size(value)

    def set_initial_colors(self):
        self.bg_base_color_combo.setCurrentText("Green")
        # Initialize color attributes
        scheme = self.color_schemes.get("Green")
        if scheme:
            self._bg_color = scheme["main"]
            self._hover_bg_color = scheme["hover"]
            self._border_color = scheme["border"]
            self._bg_color2 = scheme["gradient2"]
        else:
            # Fallback colors
            self._bg_color = QColor("#2ecc71")
            self._hover_bg_color = QColor("#58d68d")
            self._border_color = QColor("#27ae60")
            self._bg_color2 = QColor("#16a085")

    def create_coord_spinbox(self, value=0):
        spinbox = QSpinBox()
        spinbox.setRange(0, 1)
        spinbox.setSingleStep(1)
        spinbox.setValue(value)
        spinbox.valueChanged.connect(self.update_button_style)
        return spinbox

    def create_radius_slider(self):
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(8)
        slider.valueChanged.connect(self.update_button_style)
        return slider

    def update_controls_state(self):
        if not self._ui_ready: return

        component_type = self.component_type_combo.currentText()
        is_switch = component_type == "Toggle Switch"
        
        if is_switch:
            self.preview_stack.setCurrentWidget(self.preview_switch)
            self.preview_switch.set_alignment(self.align_combo.currentText() == "Left")
        else:
            self.preview_stack.setCurrentWidget(self.preview_button)

        self.icon_group.setVisible(not is_switch)

        is_icon_enabled = self.icon_checkbox.isChecked()
        use_different_icon = self.use_different_icon_checkbox.isChecked()

        self.icon_path_button.setEnabled(is_icon_enabled)
        self.icon_size_slider.setEnabled(is_icon_enabled)
        self.use_different_icon_checkbox.setEnabled(is_icon_enabled)
        self.icon_path_button_clicked.setEnabled(is_icon_enabled and use_different_icon)
        
        if not is_icon_enabled:
            self.preview_button.set_icon(None)
            self.preview_button.set_icon_clicked(None)
        
        if not use_different_icon:
            self.preview_button.set_icon_clicked(None)

        self.shape_style_label.setVisible(not is_switch)
        self.shape_style_combo.setVisible(not is_switch)
        self.padding_label.setVisible(not is_switch)
        self.padding_slider.setVisible(not is_switch)
        self.border_group.setVisible(not is_switch)
        self.align_label.setVisible(is_switch)
        self.align_combo.setVisible(is_switch)

        is_circle = component_type == "Circle Button"
        
        for w in [self.tl_radius_label, self.tl_radius_slider, self.tr_radius_label, self.tr_radius_slider, 
                  self.bl_radius_label, self.bl_radius_slider, self.br_radius_label, self.br_radius_slider]:
            w.setEnabled(not is_circle and not is_switch)

        is_gradient = self.bg_type_combo.currentText() == "Linear Gradient"
        for w in [self.gradient_coords_label, self.x1_spin, self.y1_spin, self.x2_spin, self.y2_spin,
                  self.gradient_spread_label, self.spread_combo]:
            w.setVisible(is_gradient and not is_switch)

        self.update_button_style()

    def update_button_style(self):
        if not self._ui_ready: return
        if not all(hasattr(self, attr) for attr in ['_bg_color', '_hover_bg_color', '_border_color', '_bg_color2']):
            return

        self.generate_qss()

    def generate_qss(self):
        component_type = self.component_type_combo.currentText()
        is_switch = component_type == "Toggle Switch"
        shape_style = self.shape_style_combo.currentText()
        padding = self.padding_slider.value()

        if component_type == "Circle Button":
            self.preview_button.setFixedSize(150, 150)
            radius = 75
            tl_radius, tr_radius, br_radius, bl_radius = radius, radius, radius, radius
        elif component_type == "Square Button":
            self.preview_button.setFixedSize(150, 150)
            tl_radius = self.tl_radius_slider.value()
            tr_radius = self.tr_radius_slider.value()
            br_radius = self.br_radius_slider.value()
            bl_radius = self.bl_radius_slider.value()
        elif is_switch:
            self.preview_switch.setFixedSize(200, 100)
            radius = 50
            tl_radius, tr_radius, br_radius, bl_radius = radius, radius, radius, radius
        else: # Standard Button
            self.preview_button.setFixedSize(QSize())
            self.preview_button.setMinimumSize(200, 100)
            tl_radius = self.tl_radius_slider.value()
            tr_radius = self.tr_radius_slider.value()
            br_radius = self.br_radius_slider.value()
            bl_radius = self.bl_radius_slider.value()

        main_qss, hover_qss, pressed_qss = [], [], []
        main_qss.extend([
            f"padding: {padding}px;",
            f"border-top-left-radius: {tl_radius}px;",
            f"border-top-right-radius: {tr_radius}px;",
            f"border-bottom-right-radius: {br_radius}px;",
            f"border-bottom-left-radius: {bl_radius}px;"
        ])

        main_qss.append(f"color: {self.palette().color(QPalette.ColorRole.ButtonText).name()};")

        if shape_style == "Glass":
            light_color, dark_color = self._bg_color.lighter(150).name(), self._bg_color.name()
            border_color = self._bg_color.darker(120).name()
            main_qss.append(f"background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 {light_color}, stop:1 {dark_color});")
            main_qss.append(f"border: 1px solid {border_color};")
            hover_qss.append(f"background-color: {self._bg_color.lighter(120).name()};")
            pressed_qss.append(f"background-color: {self._bg_color.darker(120).name()};")
        elif shape_style == "3D":
            main_qss.extend([f"border-width: {self.border_width_slider.value()}px;",
                             f"border-color: {self._border_color.name()};", "border-style: outset;"])
            if self.bg_type_combo.currentText() == "Solid":
                main_qss.append(f"background-color: {self._bg_color.name()};")
            else:
                spread, x1, y1, x2, y2 = self.spread_combo.currentText(), self.x1_spin.value(), self.y1_spin.value(), self.x2_spin.value(), self.y2_spin.value()
                main_qss.append(f"background-color: qlineargradient(spread:{spread}, x1:{x1}, y1:{y1}, x2:{x2}, y2:{y2}, stop:0 {self._bg_color.name()}, stop:1 {self._bg_color2.name()});")
            hover_qss.append(f"background-color: {self._hover_bg_color.name()};")
            pressed_qss.extend([f"border-style: inset;", f"background-color: {self._bg_color.darker(120).name()};"])
        elif shape_style == "Neumorphic":
            base_color = self.palette().color(QPalette.ColorRole.Window)
            main_qss.extend([f"background-color: {base_color.name()};", f"border: 2px solid {base_color.name()};"])
            pressed_qss.extend([f"border: 2px solid {base_color.darker(115).name()};",
                                f"border-top-color: {base_color.lighter(115).name()};",
                                f"border-left-color: {base_color.lighter(115).name()};"])
        elif shape_style == "Outline":
            border_width, border_color = self.border_width_slider.value(), self._border_color.name()
            main_qss.extend(["background-color: transparent;", f"border: {border_width}px solid {border_color};", f"color: {border_color};"])
            hover_qss.extend([f"background-color: {border_color};", f"color: {self.palette().color(QPalette.ColorRole.Window).name()};"])
            pressed_qss.extend([f"background-color: {self._border_color.darker(120).name()};", f"color: {self.palette().color(QPalette.ColorRole.Window).name()};"])
        else: # Flat Style
            main_qss.extend([f"border-width: {self.border_width_slider.value()}px;",
                             f"border-style: {self.border_style_combo.currentText()};",
                             f"border-color: {self._border_color.name()};"])
            if self.bg_type_combo.currentText() == "Solid":
                main_qss.append(f"background-color: {self._bg_color.name()};")
            else:
                spread, x1, y1, x2, y2 = self.spread_combo.currentText(), self.x1_spin.value(), self.y1_spin.value(), self.x2_spin.value(), self.y2_spin.value()
                main_qss.append(f"background-color: qlineargradient(spread:{spread}, x1:{x1}, y1:{y1}, x2:{x2}, y2:{y2}, stop:0 {self._bg_color.name()}, stop:1 {self._bg_color2.name()});")
            hover_qss.append(f"background-color: {self._hover_bg_color.name()};")
            pressed_qss.append(f"background-color: {self._bg_color.darker(120).name()};")

        main_qss_str = "\n    ".join(main_qss)
        hover_qss_str = "\n    ".join(hover_qss) if hover_qss else ""
        pressed_qss_str = "\n    ".join(pressed_qss) if pressed_qss else ""
        final_qss = f"QPushButton {{\n    {main_qss_str}\n}}\n"
        if hover_qss_str: final_qss += f"QPushButton:hover {{\n    {hover_qss_str}\n}}\n"
        if pressed_qss_str: final_qss += f"QPushButton:pressed {{\n    {pressed_qss_str}\n}}\n"
        
        if is_switch:
            self.preview_switch.setStyleSheet(final_qss)
            self.code_display.setText("/* QSS for the switch background */\n" + final_qss.strip() + "\n\n/* The handle animation is handled by the custom SwitchButton class. */")
        else:
            self.preview_button.setStyleSheet(final_qss)
            self.code_display.setText(final_qss.strip())

    def copy_code_to_clipboard(self):
        QApplication.clipboard().setText(self.code_display.toPlainText())

    def export_to_svg(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save SVG", "", "SVG Files (*.svg)")
        if file_name:
            generator = QSvgGenerator()
            generator.setFileName(file_name)
            generator.setSize(self.preview_stack.currentWidget().size())
            generator.setViewBox(self.preview_stack.currentWidget().rect())
            
            painter = QPainter(generator)
            self.preview_stack.currentWidget().render(painter)
            painter.end()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    app.setPalette(palette)

    ex = ComponentDesignerApp()
    ex.show()
    sys.exit(app.exec())
