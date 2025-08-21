from typing import Dict, Any, List, Optional, ClassVar
from dataclasses import dataclass, field
import copy

from PyQt6.QtCore import QObject, pyqtSignal, Qt, QSize
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLineEdit,
    QSpinBox,
    QGroupBox,
    QPushButton,
    QDialogButtonBox,
    QComboBox,
    QGridLayout,
    QLabel,
    QColorDialog,
    QSlider,
    QTabWidget,
    QWidget,
    QStackedWidget,
    QFrame,
)
from PyQt6.QtGui import QColor, QPixmap, QIcon, QPalette, QPainter, QLinearGradient, QPen

from button_creator import IconButton, SwitchButton
from utils.icon_manager import IconManager

# Predefined gradient orientations used for visual selection
_GRADIENT_STYLES = {
    "Top to Bottom": (0, 0, 0, 1),
    "Bottom to Top": (0, 1, 0, 0),
    "Left to Right": (0, 0, 1, 0),
    "Right to Left": (1, 0, 0, 0),
    "Diagonal TL-BR": (0, 0, 1, 1),
    "Diagonal BL-TR": (0, 1, 1, 0),
}

# ---------------------------------------------------------------------------
# Built-in button styles
# ---------------------------------------------------------------------------
_DEFAULT_STYLES = [
    {
        "id": "default_rounded",
        "name": "Default Rounded",
        "properties": {
            "background_color": "#5a6270",
            "text_color": "#ffffff",
            "border_radius": 20,
        },
    },
    {
        "id": "success_square",
        "name": "Success Square",
        "properties": {
            "background_color": "#4CAF50",
            "text_color": "#ffffff",
            "border_radius": 5,
        },
    },
    {
        "id": "warning_pill",
        "name": "Warning Pill",
        "properties": {
            "background_color": "#ff9800",
            "text_color": "#000000",
            "border_radius": 20,  # Height will make it a pill
        },
    },
    {
        "id": "danger_flat",
        "name": "Danger Flat",
        "properties": {
            "background_color": "#f44336",
            "text_color": "#ffffff",
            "border_radius": 0,
        },
    },
]


def get_styles() -> List[Dict[str, Any]]:
    """Return the list of built-in button style definitions."""
    return _DEFAULT_STYLES


def get_style_by_id(style_id: str) -> Dict[str, Any]:
    """Return a style definition by its unique ID."""
    for style in _DEFAULT_STYLES:
        if style["id"] == style_id:
            return style
    return _DEFAULT_STYLES[0]


@dataclass
class AnimationProperties:
    """Basic animation configuration for button styles."""
    enabled: bool = False
    type: str = "pulse"
    intensity: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "type": self.type,
            "intensity": self.intensity,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnimationProperties":
        return cls(
            enabled=data.get("enabled", False),
            type=data.get("type", "pulse"),
            intensity=data.get("intensity", 1.0),
        )


@dataclass
class ConditionalStyle:
    """A style that can be applied to a button"""
    style_id: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    tooltip: str = ""
    hover_properties: Dict[str, Any] = field(default_factory=dict)
    click_properties: Dict[str, Any] = field(default_factory=dict)
    animation: AnimationProperties = field(default_factory=AnimationProperties)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'style_id': self.style_id,
            'properties': self.properties,
            'tooltip': self.tooltip,
            'hover_properties': self.hover_properties,
            'click_properties': self.click_properties,
            'animation': self.animation.to_dict(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConditionalStyle':
        style = cls(
            style_id=data.get('style_id', ''),
            properties=data.get('properties', {}),
            tooltip=data.get('tooltip', ''),
            hover_properties=data.get('hover_properties', {}),
            click_properties=data.get('click_properties', {}),
        )
        if 'animation' in data:
            style.animation = AnimationProperties.from_dict(data['animation'])
        return style

@dataclass
class ConditionalStyleManager(QObject):
    """Manages conditional styles for buttons"""
    styles_changed: ClassVar[pyqtSignal] = pyqtSignal()
    parent: Optional[QObject] = None
    conditional_styles: List[ConditionalStyle] = field(default_factory=list)
    default_style: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        super().__init__(self.parent)
    
    def add_style(self, style: ConditionalStyle):
        """Add a new conditional style"""
        self.conditional_styles.append(style)
        self.styles_changed.emit()
    
    def remove_style(self, index: int):
        """Remove a conditional style by index"""
        if 0 <= index < len(self.conditional_styles):
            del self.conditional_styles[index]
            self.styles_changed.emit()
    
    def update_style(self, index: int, style: ConditionalStyle):
        """Update an existing conditional style"""
        if 0 <= index < len(self.conditional_styles):
            self.conditional_styles[index] = style
            self.styles_changed.emit()
    
    def get_active_style(self, tag_values: Optional[Dict[str, Any]] = None, state: Optional[str] = None) -> Dict[str, Any]:
        """Determine which style should be active based on tag values.

        Parameters
        ----------
        tag_values: Dict[str, Any], optional
            Current tag values (reserved for future use).
        state: Optional[str]
            Optional state for which to retrieve additional properties.
            Supported states: ``"hover"`` and ``"click"``.
        """
        tag_values = tag_values or {}

        if self.conditional_styles:
            style = self.conditional_styles[0]
            props = dict(style.properties)
            if state:
                props.update(getattr(style, f"{state}_properties", {}))
            if style.tooltip:
                props['tooltip'] = style.tooltip
            return props

        return dict(self.default_style)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            'conditional_styles': [style.to_dict() for style in self.conditional_styles],
            'default_style': self.default_style
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConditionalStyleManager':
        """Deserialize from dictionary"""
        manager = cls()
        manager.conditional_styles = [
            ConditionalStyle.from_dict(style_data)
            for style_data in data.get('conditional_styles', [])
        ]
        manager.default_style = data.get('default_style', {})
        return manager



class PreviewButton(IconButton):
    """Preview button that relies on style sheets for rendering."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self.setText(text)


class ConditionalStyleEditorDialog(QDialog):
    def __init__(self, parent=None, style: Optional[ConditionalStyle] = None):
        super().__init__(parent)
        self.setWindowTitle("Conditional Style")
        self.style = copy.deepcopy(style) if style else ConditionalStyle()

        main_layout = QGridLayout(self)
        main_layout.setColumnStretch(0, 1)
        main_layout.setColumnStretch(1, 1)
        main_layout.setRowStretch(3, 1)

        info_layout = QGridLayout()
        self.tooltip_edit = QLineEdit(self.style.tooltip)
        info_layout.addWidget(QLabel("Tooltip:"), 0, 0)
        info_layout.addWidget(self.tooltip_edit, 0, 1)
        main_layout.addLayout(info_layout, 0, 0, 1, 2)

        self.init_colors()

        style_group = QGroupBox("Component Style & background")
        style_layout = QGridLayout()
        style_layout.addWidget(QLabel("Component Type:"), 0, 0)
        self.component_type_combo = QComboBox()
        self.component_type_combo.addItems(["Standard Button", "Circle Button", "Square Button", "Toggle Switch"])
        self.component_type_combo.setCurrentText(self.style.properties.get("component_type", "Standard Button"))
        self.component_type_combo.currentTextChanged.connect(self.update_controls_state)
        style_layout.addWidget(self.component_type_combo, 0, 1)

        self.shape_style_label = QLabel("Shape Style:")
        style_layout.addWidget(self.shape_style_label, 1, 0)
        self.shape_style_combo = QComboBox()
        self.shape_style_combo.addItems(["Flat", "3D", "Glass", "Neumorphic", "Outline"])
        self.shape_style_combo.setCurrentText(self.style.properties.get("shape_style", "Flat"))
        self.shape_style_combo.currentTextChanged.connect(self.update_preview)
        style_layout.addWidget(self.shape_style_combo, 1, 1)

        style_layout.addWidget(QLabel("Background Type:"), 2, 0)
        self.bg_type_combo = QComboBox()
        self.bg_type_combo.addItems(["Solid", "Linear Gradient"])
        self.bg_type_combo.setCurrentText(self.style.properties.get("background_type", "Solid"))
        self.bg_type_combo.currentTextChanged.connect(self.update_controls_state)
        style_layout.addWidget(self.bg_type_combo, 2, 1)

        style_layout.addWidget(QLabel("Main Color:"), 3, 0)
        self.bg_base_color_combo, self.bg_shade_combo = self.create_color_selection_widgets(self.on_bg_color_changed)
        style_layout.addWidget(self.bg_base_color_combo, 3, 1)
        style_layout.addWidget(self.bg_shade_combo, 4, 1)

        # Hidden coordinate spin boxes used internally to build the QSS gradient
        self.x1_spin = self.create_coord_spinbox(self.style.properties.get("gradient_x1", 0))
        self.y1_spin = self.create_coord_spinbox(self.style.properties.get("gradient_y1", 0))
        self.x2_spin = self.create_coord_spinbox(self.style.properties.get("gradient_x2", 0))
        self.y2_spin = self.create_coord_spinbox(self.style.properties.get("gradient_y2", 1))
        for w in [self.x1_spin, self.y1_spin, self.x2_spin, self.y2_spin]:
            w.setVisible(False)

        self.gradient_dir_label = QLabel("Gradient Direction:")
        style_layout.addWidget(self.gradient_dir_label, 5, 0)
        self.gradient_type_combo = QComboBox()
        self._init_gradient_type_combo()
        style_layout.addWidget(self.gradient_type_combo, 5, 1)

        style_group.setLayout(style_layout)
        main_layout.addWidget(style_group, 1, 0)

        self.border_group = QGroupBox("Border")
        border_layout = QGridLayout()

        # Corner radius table
        self.corner_frame = QFrame()
        self.corner_frame.setStyleSheet("QFrame { border: 1px solid #666; }")
        corner_layout = QGridLayout(self.corner_frame)
        corner_layout.setContentsMargins(0, 0, 0, 0)
        corner_layout.setSpacing(0)

        header = QLabel("Corner radius")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        corner_layout.addWidget(header, 0, 0, 1, 3)

        self.link_radius_btn = QPushButton()
        self.link_radius_btn.setCheckable(True)
        corner_layout.addWidget(self.link_radius_btn, 1, 0)

        left_label = QLabel("Left")
        left_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        corner_layout.addWidget(left_label, 1, 1)
        right_label = QLabel("Right")
        right_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        corner_layout.addWidget(right_label, 1, 2)

        top_label = QLabel("Top")
        top_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        corner_layout.addWidget(top_label, 2, 0)
        bottom_label = QLabel("Bottom")
        bottom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        corner_layout.addWidget(bottom_label, 3, 0)

        self.tl_radius_spin = self.create_radius_spinbox()
        self.tl_radius_spin.setValue(self.style.properties.get("border_radius_tl", 0))
        corner_layout.addWidget(self.tl_radius_spin, 2, 1)
        self.tr_radius_spin = self.create_radius_spinbox()
        self.tr_radius_spin.setValue(self.style.properties.get("border_radius_tr", 0))
        corner_layout.addWidget(self.tr_radius_spin, 2, 2)
        self.bl_radius_spin = self.create_radius_spinbox()
        self.bl_radius_spin.setValue(self.style.properties.get("border_radius_bl", 0))
        corner_layout.addWidget(self.bl_radius_spin, 3, 1)
        self.br_radius_spin = self.create_radius_spinbox()
        self.br_radius_spin.setValue(self.style.properties.get("border_radius_br", 0))
        corner_layout.addWidget(self.br_radius_spin, 3, 2)

        for w in [header, self.link_radius_btn, left_label, right_label, top_label, bottom_label]:
            w.setStyleSheet("border: 1px solid #666;")

        self.corner_spins = {
            "tl": self.tl_radius_spin,
            "tr": self.tr_radius_spin,
            "br": self.br_radius_spin,
            "bl": self.bl_radius_spin,
        }
        for key, spin in self.corner_spins.items():
            spin.valueChanged.connect(lambda val, k=key: self.on_corner_radius_changed(k, val))
        self.link_radius_btn.toggled.connect(self.on_link_radius_toggled)
        self.on_link_radius_toggled(self.link_radius_btn.isChecked())

        border_layout.addWidget(self.corner_frame, 0, 0, 1, 2)

        border_layout.addWidget(QLabel("Border Width (px):"), 1, 0)
        self.border_width_spin = QSpinBox()
        # Allow border width up to 20px, final limit is adjusted dynamically
        self.border_width_spin.setRange(0, 20)
        self.border_width_spin.setValue(self.style.properties.get("border_width", 0))
        self.border_width_spin.valueChanged.connect(self.update_preview)
        border_layout.addWidget(self.border_width_spin, 1, 1)

        self.border_style_label = QLabel("Border Style:")
        border_layout.addWidget(self.border_style_label, 2, 0)
        self.border_style_combo = QComboBox()
        self.border_style_combo.setIconSize(QSize(60, 12))
        _styles = ["none", "solid", "dashed", "dotted", "double", "groove", "ridge"]
        for s in _styles:
            self.border_style_combo.addItem(self._create_border_style_icon(s), "")
            index = self.border_style_combo.count() - 1
            self.border_style_combo.setItemData(index, s)
        current_style = self.style.properties.get("border_style", "solid")
        if current_style in _styles:
            self.border_style_combo.setCurrentIndex(_styles.index(current_style))
        self.border_style_combo.currentIndexChanged.connect(self.update_preview)
        border_layout.addWidget(self.border_style_combo, 2, 1)

        self.border_group.setLayout(border_layout)
        main_layout.addWidget(self.border_group, 2, 0)

        # Style tabs
        style_tabs = QTabWidget()

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
        self.border_color_btn = self.create_color_button(self.style.properties.get("border_color", ""))
        base_layout.addWidget(QLabel("Background:"), 0, 0); base_layout.addWidget(self.bg_color_btn, 0, 1)
        base_layout.addWidget(QLabel("Text Color:"), 1, 0); base_layout.addWidget(self.text_color_btn, 1, 1)
        base_layout.addWidget(QLabel("Font Size:"), 2, 0); base_layout.addWidget(self.font_size_spin, 2, 1)
        base_layout.addWidget(QLabel("Width:"), 3, 0); base_layout.addWidget(self.width_spin, 3, 1)
        base_layout.addWidget(QLabel("Height:"), 4, 0); base_layout.addWidget(self.height_spin, 4, 1)
        base_layout.addWidget(QLabel("Border Color:"), 5, 0); base_layout.addWidget(self.border_color_btn, 5, 1)
        style_tabs.addTab(base_tab, "Base")

        # Hover tab
        hover_tab = QWidget(); hover_layout = QGridLayout(hover_tab)
        self.hover_bg_btn = self.create_color_button(self.style.hover_properties.get("background_color", ""))
        self.hover_text_btn = self.create_color_button(self.style.hover_properties.get("text_color", ""))
        self.hover_border_radius_slider = QSlider(Qt.Orientation.Horizontal); self.hover_border_radius_slider.setRange(0, 1000)
        self.hover_border_radius_slider.setValue(self.style.hover_properties.get("border_radius", 0))
        self.hover_border_width_slider = QSlider(Qt.Orientation.Horizontal); self.hover_border_width_slider.setRange(0, 20)
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
        self.click_border_width_slider = QSlider(Qt.Orientation.Horizontal); self.click_border_width_slider.setRange(0, 20)
        self.click_border_width_slider.setValue(self.style.click_properties.get("border_width", 0))
        self.click_border_color_btn = self.create_color_button(self.style.click_properties.get("border_color", ""))
        click_layout.addWidget(QLabel("Background:"), 0, 0); click_layout.addWidget(self.click_bg_btn, 0, 1)
        click_layout.addWidget(QLabel("Text Color:"), 1, 0); click_layout.addWidget(self.click_text_btn, 1, 1)
        click_layout.addWidget(QLabel("Border Radius:"), 2, 0); click_layout.addWidget(self.click_border_radius_slider, 2, 1)
        click_layout.addWidget(QLabel("Border Width:"), 3, 0); click_layout.addWidget(self.click_border_width_slider, 3, 1)
        click_layout.addWidget(QLabel("Border Color:"), 4, 0); click_layout.addWidget(self.click_border_color_btn, 4, 1)
        style_tabs.addTab(click_tab, "Click")

        # Conditions group - left empty for future use
        cond_group = QGroupBox("Conditions")
        QVBoxLayout(cond_group)
        main_layout.addWidget(cond_group, 2, 1)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(style_tabs, 3, 0, 1, 2)
        main_layout.addWidget(self.button_box, 4, 0, 1, 2)

        preview_group = QGroupBox("Preview")
        preview_group_layout = QVBoxLayout(); preview_group_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_stack = QStackedWidget()
        self.preview_button = PreviewButton("Preview")
        self.preview_button.setMinimumSize(200, 100)
        self.preview_switch = SwitchButton()
        self.preview_stack.addWidget(self.preview_button)
        self.preview_stack.addWidget(self.preview_switch)
        preview_group_layout.addWidget(self.preview_stack)
        preview_group.setLayout(preview_group_layout)
        main_layout.addWidget(preview_group, 1, 1)

        # Ensure group boxes line up neatly
        preview_group.setMinimumHeight(style_group.sizeHint().height())
        cond_group.setMinimumHeight(self.border_group.sizeHint().height())

        for w in [self.font_size_spin, self.width_spin, self.height_spin,
                  self.border_width_spin, self.hover_border_radius_slider, self.hover_border_width_slider,
                  self.click_border_radius_slider, self.click_border_width_slider,
                  self.x1_spin, self.y1_spin, self.x2_spin, self.y2_spin]:
            w.valueChanged.connect(self.update_preview)
        self.component_type_combo.currentTextChanged.connect(self.update_preview)
        self.width_spin.valueChanged.connect(self.update_controls_state)
        self.height_spin.valueChanged.connect(self.update_controls_state)

        self.set_initial_colors()
        self.update_controls_state()
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
            if btn is self.bg_color_btn:
                self._bg_color = QColor(color_name)
            elif btn is self.hover_bg_btn:
                self._hover_bg_color = QColor(color_name)
            elif btn in [self.border_color_btn, self.hover_border_color_btn, self.click_border_color_btn]:
                self._border_color = QColor(color_name)
            elif btn is self.click_bg_btn:
                self._click_bg_color = QColor(color_name)
            self.update_preview()

    def _button_color(self, btn):
        return btn.property("color") or ""

    def init_colors(self):
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
            "White": {"main": QColor("#ecf0f1"), "hover": QColor("#ffffff"), "border": QColor("#bdc3c7"), "gradient2": QColor("#bdc3c7")},
        }
        self.base_colors = {name: scheme["main"] for name, scheme in self.color_schemes.items()}

    def get_shades(self, color_name):
        base_color = self.base_colors.get(color_name, QColor("#000000"))
        shades = []
        for i in range(16):
            factor = 1.2 - (i / 15.0) * 0.6
            shades.append(base_color.lighter(int(100 * factor)) if factor > 1.0 else base_color.darker(int(100 / factor)))
        return shades

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
        if not color:
            return
        scheme = self.color_schemes.get(color_name)
        if scheme:
            self._bg_color = color
            self._hover_bg_color = scheme["hover"]
            self._border_color = scheme["border"]
            self._bg_color2 = scheme["gradient2"]
            self._click_bg_color = self._bg_color.darker(120)
            self._set_button_color(self.bg_color_btn, self._bg_color.name())
            self.bg_color_btn.setProperty("color", self._bg_color.name())
            self._set_button_color(self.hover_bg_btn, self._hover_bg_color.name())
            self.hover_bg_btn.setProperty("color", self._hover_bg_color.name())
            self._set_button_color(self.border_color_btn, self._border_color.name())
            self.border_color_btn.setProperty("color", self._border_color.name())
            self._set_button_color(self.hover_border_color_btn, self._border_color.name())
            self.hover_border_color_btn.setProperty("color", self._border_color.name())
            self._set_button_color(self.click_border_color_btn, self._border_color.name())
            self.click_border_color_btn.setProperty("color", self._border_color.name())
            self._set_button_color(self.click_bg_btn, self._click_bg_color.name())
            self.click_bg_btn.setProperty("color", self._click_bg_color.name())
        self.update_preview()

    def set_initial_colors(self):
        self.bg_base_color_combo.setCurrentText("Green")
        scheme = self.color_schemes.get("Green")
        if scheme:
            self._bg_color = scheme["main"]
            self._hover_bg_color = scheme["hover"]
            self._border_color = scheme["border"]
            self._bg_color2 = scheme["gradient2"]
            self._click_bg_color = self._bg_color.darker(120)
        else:
            self._bg_color = QColor("#2ecc71")
            self._hover_bg_color = QColor("#58d68d")
            self._border_color = QColor("#27ae60")
            self._bg_color2 = QColor("#16a085")
            self._click_bg_color = self._bg_color.darker(120)
        self.on_bg_color_changed("Green", self._bg_color)

    def create_coord_spinbox(self, value=0):
        spinbox = QSpinBox()
        spinbox.setRange(0, 1)
        spinbox.setSingleStep(1)
        spinbox.setValue(value)
        return spinbox

    def create_radius_spinbox(self):
        spinbox = QSpinBox()
        spinbox.setRange(0, 1000)
        spinbox.setValue(0)
        return spinbox

    def on_corner_radius_changed(self, corner, value):
        if self.link_radius_btn.isChecked():
            for key, spin in self.corner_spins.items():
                if key != corner:
                    spin.blockSignals(True)
                    spin.setValue(value)
                    spin.blockSignals(False)
        self.update_preview()

    def on_link_radius_toggled(self, checked):
        icon_name = "fa5s.link" if checked else "fa5s.unlink"
        self.link_radius_btn.setIcon(IconManager.create_icon(icon_name))
        if checked:
            self.on_corner_radius_changed('tl', self.tl_radius_spin.value())

    def _create_gradient_icon(self, coords):
        pixmap = QPixmap(40, 20)
        gradient = QLinearGradient(coords[0] * 40, coords[1] * 20, coords[2] * 40, coords[3] * 20)
        gradient.setColorAt(0, QColor("#000000"))
        gradient.setColorAt(1, QColor("#ffffff"))
        painter = QPainter(pixmap)
        painter.fillRect(pixmap.rect(), gradient)
        painter.end()
        return QIcon(pixmap)

    def _create_border_style_icon(self, style_name: str) -> QIcon:
        pixmap = QPixmap(60, 12)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        pen = QPen(QColor("#ffffff"), 2)
        if style_name == "double":
            painter.setPen(pen)
            painter.drawLine(0, 4, 60, 4)
            painter.drawLine(0, 8, 60, 8)
        elif style_name == "groove":
            painter.setPen(pen)
            painter.drawLine(0, 4, 60, 4)
            pen.setColor(QColor("#888888"))
            painter.setPen(pen)
            painter.drawLine(0, 8, 60, 8)
        elif style_name == "ridge":
            painter.setPen(QPen(QColor("#888888"), 2))
            painter.drawLine(0, 4, 60, 4)
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.drawLine(0, 8, 60, 8)
        elif style_name != "none":
            if style_name == "dashed":
                pen.setStyle(Qt.PenStyle.DashLine)
            elif style_name == "dotted":
                pen.setStyle(Qt.PenStyle.DotLine)
            else:
                pen.setStyle(Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawLine(0, 6, 60, 6)
        painter.end()
        return QIcon(pixmap)

    def _init_gradient_type_combo(self):
        for name, coords in _GRADIENT_STYLES.items():
            self.gradient_type_combo.addItem(self._create_gradient_icon(coords), name)
        default_type = self.style.properties.get("gradient_type")
        if default_type and default_type in _GRADIENT_STYLES:
            self.gradient_type_combo.setCurrentText(default_type)
            self._set_gradient_coords(_GRADIENT_STYLES[default_type])
        else:
            # Set from existing coordinates and detect matching type
            current = (self.x1_spin.value(), self.y1_spin.value(),
                       self.x2_spin.value(), self.y2_spin.value())
            for name, coords in _GRADIENT_STYLES.items():
                if coords == current:
                    self.gradient_type_combo.setCurrentText(name)
                    break
            else:
                self.gradient_type_combo.setCurrentText("Top to Bottom")
                self._set_gradient_coords(_GRADIENT_STYLES["Top to Bottom"])
        self.gradient_type_combo.currentTextChanged.connect(self._on_gradient_type_changed)

    def _set_gradient_coords(self, coords):
        self.x1_spin.setValue(coords[0])
        self.y1_spin.setValue(coords[1])
        self.x2_spin.setValue(coords[2])
        self.y2_spin.setValue(coords[3])

    def _on_gradient_type_changed(self, text):
        if text in _GRADIENT_STYLES:
            self._set_gradient_coords(_GRADIENT_STYLES[text])
        self.update_preview()

    def update_controls_state(self):
        component_type = self.component_type_combo.currentText()
        is_switch = component_type == "Toggle Switch"
        if is_switch:
            self.preview_stack.setCurrentWidget(self.preview_switch)
        else:
            self.preview_stack.setCurrentWidget(self.preview_button)

        self.shape_style_label.setEnabled(not is_switch)
        self.shape_style_combo.setEnabled(not is_switch)
        self.border_group.setEnabled(not is_switch)

        is_circle = component_type == "Circle Button"
        self.corner_frame.setEnabled(not is_circle and not is_switch)

        is_gradient = self.bg_type_combo.currentText() == "Linear Gradient"
        for w in [self.gradient_dir_label, self.gradient_type_combo]:
            w.setEnabled(is_gradient)

        self.update_dynamic_ranges()
        self.update_preview()

    def update_dynamic_ranges(self):
        width = self.width_spin.value() or 200
        height = self.height_spin.value() or 100
        # Corner radii can be up to half of the smaller dimension.
        radius_limit = min(width, height) // 2
        # Border widths are limited to 10% of the smaller dimension, capped at 20px.
        border_limit = min(20, max(1, min(width, height) // 10))
        for s in [self.tl_radius_spin, self.tr_radius_spin, self.br_radius_spin, self.bl_radius_spin,
                  self.hover_border_radius_slider, self.click_border_radius_slider]:
            s.setMaximum(radius_limit)
        for s in [self.border_width_spin, self.hover_border_width_slider, self.click_border_width_slider]:
            s.setMaximum(border_limit)

    def generate_qss(self, component_type):
        shape_style = self.shape_style_combo.currentText()
        bg_type = self.bg_type_combo.currentText()
        width = self.width_spin.value() or 200
        height = self.height_spin.value() or 100
        padding = min(width, height) // 10
        tl_radius = self.tl_radius_spin.value()
        tr_radius = self.tr_radius_spin.value()
        br_radius = self.br_radius_spin.value()
        bl_radius = self.bl_radius_spin.value()
        border_width = self.border_width_spin.value()
        border_style = self.border_style_combo.currentData()
        bg_color = self._bg_color
        hover_bg_color = self._hover_bg_color
        click_bg_color = self._click_bg_color
        border_color = self._border_color
        text_color = self._button_color(self.text_color_btn) or self.palette().color(QPalette.ColorRole.ButtonText).name()
        font_size = self.font_size_spin.value()
        hover_border_color = QColor(self._button_color(self.hover_border_color_btn) or border_color.name())
        click_border_color = QColor(self._button_color(self.click_border_color_btn) or border_color.name())

        if component_type == "Circle Button":
            size = max(self.width_spin.value() or 150, self.height_spin.value() or 150)
            radius = size // 2
            tl_radius = tr_radius = br_radius = bl_radius = radius
            self.preview_button.setFixedSize(size, size)
        elif component_type == "Square Button":
            size = max(self.width_spin.value() or 150, self.height_spin.value() or 150)
            self.preview_button.setFixedSize(size, size)
        elif component_type == "Toggle Switch":
            self.preview_switch.setFixedSize(self.width_spin.value() or 200, self.height_spin.value() or 100)
        else:
            self.preview_button.setFixedSize(self.width_spin.value() or 200, self.height_spin.value() or 100)

        main_qss, hover_qss, pressed_qss = [], [], []
        main_qss.extend([
            f"padding: {padding}px;",
            f"border-top-left-radius: {tl_radius}px;",
            f"border-top-right-radius: {tr_radius}px;",
            f"border-bottom-right-radius: {br_radius}px;",
            f"border-bottom-left-radius: {bl_radius}px;",
            f"color: {text_color};",
            f"font-size: {font_size}pt;"
        ])

        if shape_style == "Glass":
            light_color, dark_color = bg_color.lighter(150).name(), bg_color.name()
            border_c = bg_color.darker(120).name()
            main_qss.append(
                f"background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {light_color}, stop:1 {dark_color});"
            )
            main_qss.append(f"border: 1px solid {border_c};")
            hover_qss.append(f"background-color: {bg_color.lighter(120).name()};")
            pressed_qss.append(f"background-color: {bg_color.darker(120).name()};")
        elif shape_style == "3D":
            main_qss.extend([f"border-width: {border_width}px;", f"border-color: {border_color.name()};", "border-style: outset;"])
            if bg_type == "Solid":
                main_qss.append(f"background-color: {bg_color.name()};")
            else:
                x1, y1, x2, y2 = self.x1_spin.value(), self.y1_spin.value(), self.x2_spin.value(), self.y2_spin.value()
                main_qss.append(
                    f"background-color: qlineargradient(x1:{x1}, y1:{y1}, x2:{x2}, y2:{y2}, stop:0 {bg_color.name()}, stop:1 {self._bg_color2.name()});"
                )
            hover_qss.append(f"background-color: {hover_bg_color.name()};")
            pressed_qss.extend(["border-style: inset;", f"background-color: {bg_color.darker(120).name()};"])
        elif shape_style == "Neumorphic":
            base_color = self.palette().color(QPalette.ColorRole.Window)
            main_qss.extend([f"background-color: {base_color.name()};", f"border: 2px solid {base_color.name()};"])
            pressed_qss.extend([f"border: 2px solid {base_color.darker(115).name()};",
                                f"border-top-color: {base_color.lighter(115).name()};",
                                f"border-left-color: {base_color.lighter(115).name()};"])
        elif shape_style == "Outline":
            main_qss.extend(["background-color: transparent;",
                             f"border: {border_width}px solid {border_color.name()};",
                             f"color: {border_color.name()};"])
            hover_qss.extend([f"background-color: {border_color.name()};",
                              f"color: {self.palette().color(QPalette.ColorRole.Window).name()};"])
            pressed_qss.extend([f"background-color: {border_color.darker(120).name()};",
                                f"color: {self.palette().color(QPalette.ColorRole.Window).name()};"])
        else:
            main_qss.extend([f"border-width: {border_width}px;",
                             f"border-style: {border_style};",
                             f"border-color: {border_color.name()};"])
            if bg_type == "Solid":
                main_qss.append(f"background-color: {bg_color.name()};")
            else:
                x1, y1, x2, y2 = self.x1_spin.value(), self.y1_spin.value(), self.x2_spin.value(), self.y2_spin.value()
                main_qss.append(
                    f"background-color: qlineargradient(x1:{x1}, y1:{y1}, x2:{x2}, y2:{y2}, stop:0 {bg_color.name()}, stop:1 {self._bg_color2.name()});"
                )
            hover_qss.append(f"background-color: {hover_bg_color.name()};")
            pressed_qss.append(f"background-color: {click_bg_color.name()};")

        if hover_border_color != border_color:
            hover_qss.append(f"border-color: {hover_border_color.name()};")
        if click_border_color != border_color:
            pressed_qss.append(f"border-color: {click_border_color.name()};")

        main_qss_str = "\n    ".join(main_qss)
        hover_qss_str = "\n    ".join(hover_qss) if hover_qss else ""
        pressed_qss_str = "\n    ".join(pressed_qss) if pressed_qss else ""
        final_qss = f"QPushButton {{\n    {main_qss_str}\n}}\n"
        if hover_qss_str:
            final_qss += f"QPushButton:hover {{\n    {hover_qss_str}\n}}\n"
        if pressed_qss_str:
            final_qss += f"QPushButton:pressed {{\n    {pressed_qss_str}\n}}\n"
        return final_qss

    def update_preview(self):
        component_type = self.component_type_combo.currentText()
        qss = self.generate_qss(component_type)
        if component_type == "Toggle Switch":
            self.preview_switch.setStyleSheet(qss)
        else:
            self.preview_button.setStyleSheet(qss)


    def get_style(self) -> ConditionalStyle:
        properties = {
            "component_type": self.component_type_combo.currentText(),
            "shape_style": self.shape_style_combo.currentText(),
            "background_type": self.bg_type_combo.currentText(),
            "background_color": self._button_color(self.bg_color_btn),
            "background_color2": self._bg_color2.name(),
            "gradient_type": self.gradient_type_combo.currentText(),
            "gradient_x1": self.x1_spin.value(),
            "gradient_y1": self.y1_spin.value(),
            "gradient_x2": self.x2_spin.value(),
            "gradient_y2": self.y2_spin.value(),
            "text_color": self._button_color(self.text_color_btn),
            "font_size": self.font_size_spin.value(),
            "width": self.width_spin.value(),
            "height": self.height_spin.value(),
            "border_radius_tl": self.tl_radius_spin.value(),
            "border_radius_tr": self.tr_radius_spin.value(),
            "border_radius_br": self.br_radius_spin.value(),
            "border_radius_bl": self.bl_radius_spin.value(),
            "border_width": self.border_width_spin.value(),
            "border_style": self.border_style_combo.currentData(),
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
            style_id=self.style.style_id,
            properties=properties,
            hover_properties=hover_properties,
            click_properties=click_properties,
            tooltip=self.tooltip_edit.text(),
        )
        return style