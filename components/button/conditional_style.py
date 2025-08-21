from typing import Dict, Any, List, Optional, ClassVar
from dataclasses import dataclass, asdict, field
import copy
import operator

from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QGroupBox,
    QPushButton,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QDialogButtonBox,
    QComboBox,
    QGridLayout,
    QLabel,
    QColorDialog,
    QSlider,
    QTabWidget,
    QWidget,
    QStackedWidget,
    QFontComboBox,
    QCheckBox,
)
from PyQt6.QtGui import QColor, QPixmap, QIcon, QPalette, QPainter, QLinearGradient, QFont

from button_creator import IconButton, SwitchButton
from services.tag_service import tag_service
from dialogs.widgets import TagSelector
from services.tag_data_service import tag_data_service
from utils.icon_manager import IconManager

_NUMERIC_OPERATORS = {
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
}

_EQUALITY_OPERATORS = {
    "==": operator.eq,
    "!=": operator.ne,
}

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
class StyleCondition:
    """Defines when a style should be active based on tag values"""
    tag_path: str = ""  # Full tag path in form "[db_name]::tag_name"
    operator: str = "=="  # ==, !=, >, <, >=, <=, between, outside
    value: Any = None
    value2: Any = None  # For range operators

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StyleCondition":
        return cls(**data)

@dataclass
class ConditionalStyle:
    """A style that can be conditionally applied based on tag values"""
    style_id: str = ""
    conditions: List[StyleCondition] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    tooltip: str = ""
    hover_properties: Dict[str, Any] = field(default_factory=dict)
    click_properties: Dict[str, Any] = field(default_factory=dict)
    animation: AnimationProperties = field(default_factory=AnimationProperties)
    text_type: str = ""
    comment_number: str = ""
    comment_column: int = 0
    comment_row: int = 0
    simple_text: str = ""
    font_family: str = ""
    font_size: int = 0
    font_bold: bool = False
    font_italic: bool = False
    font_underline: bool = False
    align_h: str = ""
    align_v: str = ""
    text_background: str = ""
    frame_offset: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'style_id': self.style_id,
            'conditions': [cond.to_dict() for cond in self.conditions],
            'properties': self.properties,
            'tooltip': self.tooltip,
            'hover_properties': self.hover_properties,
            'click_properties': self.click_properties,
            'animation': self.animation.to_dict(),
            'text_type': self.text_type,
            'comment_number': self.comment_number,
            'comment_column': self.comment_column,
            'comment_row': self.comment_row,
            'simple_text': self.simple_text,
            'font_family': self.font_family,
            'font_size': self.font_size,
            'font_bold': self.font_bold,
            'font_italic': self.font_italic,
            'font_underline': self.font_underline,
            'align_h': self.align_h,
            'align_v': self.align_v,
            'text_background': self.text_background,
            'frame_offset': self.frame_offset,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConditionalStyle':
        style = cls(
            style_id=data.get('style_id', ''),
            conditions=[StyleCondition.from_dict(cond) for cond in data.get('conditions', [])],
            properties=data.get('properties', {}),
            tooltip=data.get('tooltip', ''),
            hover_properties=data.get('hover_properties', {}),
            click_properties=data.get('click_properties', {}),
            text_type=data.get('text_type', ''),
            comment_number=data.get('comment_number', ''),
            comment_column=data.get('comment_column', 0),
            comment_row=data.get('comment_row', 0),
            simple_text=data.get('simple_text', ''),
            font_family=data.get('font_family', ''),
            font_size=data.get('font_size', 0),
            font_bold=data.get('font_bold', False),
            font_italic=data.get('font_italic', False),
            font_underline=data.get('font_underline', False),
            align_h=data.get('align_h', ''),
            align_v=data.get('align_v', ''),
            text_background=data.get('text_background', ''),
            frame_offset=data.get('frame_offset', {}),
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
    _TEXT_KEYS: ClassVar[List[str]] = [
        "text_type",
        "comment_number",
        "comment_column",
        "comment_row",
        "simple_text",
        "font_family",
        "font_size",
        "font_bold",
        "font_italic",
        "font_underline",
        "h_align",
        "v_align",
        "text_bg_color",
        "offset_x",
        "offset_y",
    ]

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
            Current tag values; if not provided, values will be resolved via ``tag_service``.
        state: Optional[str]
            Optional state for which to retrieve additional properties.
            Supported states: ``"hover"`` and ``"click"``.
        """
        tag_values = tag_values or {}

        for style in self.conditional_styles:
            if self._evaluate_conditions(style.conditions, tag_values):
                props = dict(style.properties)

                # Merge dataclass text fields into base properties if they are
                # stored as separate attributes (for backward compatibility).
                for key in self._TEXT_KEYS:
                    val = getattr(style, key, None)
                    if val not in (None, "", {}):
                        props.setdefault(key, val)

                if state:
                    state_props = getattr(style, f"{state}_properties", {})

                    # If text locking is enabled, ensure state specific styles
                    # inherit the base text properties when they are missing.
                    if props.get("text_lock"):
                        for key in self._TEXT_KEYS:
                            if key not in state_props and key in props:
                                state_props[key] = props[key]

                    props.update(state_props)

                if style.tooltip:
                    props["tooltip"] = style.tooltip

                return props

        return dict(self.default_style)
    
    def _evaluate_conditions(self, conditions: List[StyleCondition], tag_values: Dict[str, Any]) -> bool:
        """Evaluate if all conditions are met"""
        if not conditions:
            return True
        
        for condition in conditions:
            if not self._evaluate_single_condition(condition, tag_values):
                return False
        
        return True
    
    def _evaluate_single_condition(self, condition: StyleCondition, tag_values: Dict[str, Any]) -> bool:
        """Evaluate a single condition"""
        tag_value = tag_values.get(condition.tag_path)
        if tag_value is None:
            tag_value = tag_service.get_tag_value(condition.tag_path)
        if tag_value is None:
            return False

        try:
            if condition.operator in _EQUALITY_OPERATORS:
                return _EQUALITY_OPERATORS[condition.operator](tag_value, condition.value)
            if condition.operator in _NUMERIC_OPERATORS:
                return _NUMERIC_OPERATORS[condition.operator](float(tag_value), float(condition.value))
            if condition.operator == "between":
                value = float(tag_value)
                return float(condition.value) <= value <= float(condition.value2)
            if condition.operator == "outside":
                value = float(tag_value)
                low = float(condition.value)
                high = float(condition.value2)
                return value < low or value > high
        except (ValueError, TypeError):
            return False

        return False
    
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

        # Initialize color attributes to prevent AttributeError
        self._bg_color = QColor("#2ecc71")
        self._hover_bg_color = QColor("#58d68d")
        self._border_color = QColor("#27ae60")
        self._bg_color2 = QColor("#16a085")
        self._click_bg_color = self._bg_color.darker(120)

        main_layout = QGridLayout(self)
        main_layout.setColumnStretch(0, 1)
        main_layout.setColumnStretch(1, 1)

        controls_layout = QVBoxLayout()

        info_layout = QGridLayout()
        self.tooltip_edit = QLineEdit(self.style.tooltip)
        info_layout.addWidget(QLabel("Tooltip:"), 0, 0)
        info_layout.addWidget(self.tooltip_edit, 0, 1)
        controls_layout.addLayout(info_layout)

        self.init_colors()

        style_group = QGroupBox("Component Style & background")
        style_layout = QGridLayout()
        style_layout.addWidget(QLabel("Component Type:"), 0, 0)
        self.component_type_combo = QComboBox()
        self.component_type_combo.addItems(["Standard Button", "Circle Button", "Square Button", "Toggle Switch"])
        self.component_type_combo.setCurrentText(self.style.properties.get("component_type", "Standard Button"))
        self.component_type_combo.currentTextChanged.connect(self.update_controls_state)
        style_layout.addWidget(self.component_type_combo, 0, 1, 1, 2)

        self.shape_style_label = QLabel("Shape Style:")
        style_layout.addWidget(self.shape_style_label, 1, 0)
        self.shape_style_combo = QComboBox()
        self.shape_style_combo.addItems(["Flat", "3D", "Glass", "Neumorphic", "Outline"])
        self.shape_style_combo.setCurrentText(self.style.properties.get("shape_style", "Flat"))
        self.shape_style_combo.currentTextChanged.connect(self.update_preview)
        style_layout.addWidget(self.shape_style_combo, 1, 1, 1, 2)

        style_layout.addWidget(QLabel("Background Type:"), 2, 0)
        self.bg_type_combo = QComboBox()
        self.bg_type_combo.addItems(["Solid", "Linear Gradient"])
        self.bg_type_combo.setCurrentText(self.style.properties.get("background_type", "Solid"))
        self.bg_type_combo.currentTextChanged.connect(self.update_controls_state)
        style_layout.addWidget(self.bg_type_combo, 2, 1, 1, 2)

        style_layout.addWidget(QLabel("Main Color:"), 3, 0)
        self.bg_base_color_combo, self.bg_shade_combo = self.create_color_selection_widgets(self.on_bg_color_changed)
        style_layout.addWidget(self.bg_base_color_combo, 3, 1)
        style_layout.addWidget(self.bg_shade_combo, 3, 2)

        # Hidden coordinate spin boxes used internally to build the QSS gradient
        self.x1_spin = self.create_coord_spinbox(self.style.properties.get("gradient_x1", 0))
        self.y1_spin = self.create_coord_spinbox(self.style.properties.get("gradient_y1", 0))
        self.x2_spin = self.create_coord_spinbox(self.style.properties.get("gradient_x2", 0))
        self.y2_spin = self.create_coord_spinbox(self.style.properties.get("gradient_y2", 1))
        for w in [self.x1_spin, self.y1_spin, self.x2_spin, self.y2_spin]:
            w.setVisible(False)

        self.gradient_dir_label = QLabel("Gradient Direction:")
        style_layout.addWidget(self.gradient_dir_label, 4, 0)
        self.gradient_type_combo = QComboBox()
        self._init_gradient_type_combo()
        style_layout.addWidget(self.gradient_type_combo, 4, 1, 1, 2)
        style_group.setLayout(style_layout)
        controls_layout.addWidget(style_group)

        self.border_group = QGroupBox("Border")
        border_layout = QGridLayout()

        self.tl_radius_label = QLabel("Top-Left Radius:")
        border_layout.addWidget(self.tl_radius_label, 0, 0)
        self.tl_radius_spin = self.create_radius_spinbox()
        self.tl_radius_spin.setValue(self.style.properties.get("border_radius_tl", 0))
        border_layout.addWidget(self.tl_radius_spin, 0, 1)

        self.tr_radius_label = QLabel("Top-Right Radius:")
        border_layout.addWidget(self.tr_radius_label, 1, 0)
        self.tr_radius_spin = self.create_radius_spinbox()
        self.tr_radius_spin.setValue(self.style.properties.get("border_radius_tr", 0))
        border_layout.addWidget(self.tr_radius_spin, 1, 1)

        self.br_radius_label = QLabel("Bottom-Right Radius:")
        border_layout.addWidget(self.br_radius_label, 2, 0)
        self.br_radius_spin = self.create_radius_spinbox()
        self.br_radius_spin.setValue(self.style.properties.get("border_radius_br", 0))
        border_layout.addWidget(self.br_radius_spin, 2, 1)

        self.bl_radius_label = QLabel("Bottom-Left Radius:")
        border_layout.addWidget(self.bl_radius_label, 3, 0)
        self.bl_radius_spin = self.create_radius_spinbox()
        self.bl_radius_spin.setValue(self.style.properties.get("border_radius_bl", 0))
        border_layout.addWidget(self.bl_radius_spin, 3, 1)

        self.link_radius_btn = QPushButton()
        self.link_radius_btn.setCheckable(True)
        border_layout.addWidget(self.link_radius_btn, 0, 2, 4, 1)

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

        border_layout.addWidget(QLabel("Border Width (px):"), 4, 0)
        self.border_width_spin = QSpinBox()
        # Allow border width up to 20px, final limit is adjusted dynamically
        self.border_width_spin.setRange(0, 20)
        self.border_width_spin.setValue(self.style.properties.get("border_width", 0))
        self.border_width_spin.valueChanged.connect(self.update_preview)
        border_layout.addWidget(self.border_width_spin, 4, 1)

        self.border_style_label = QLabel("Border Style:")
        border_layout.addWidget(self.border_style_label, 5, 0)
        self.border_style_combo = QComboBox()
        self.border_style_combo.addItems(["none", "solid", "dashed", "dotted", "double", "groove", "ridge"])
        self.border_style_combo.setCurrentText(self.style.properties.get("border_style", "solid"))
        self.border_style_combo.currentTextChanged.connect(self.update_preview)
        border_layout.addWidget(self.border_style_combo, 5, 1)

        self.border_group.setLayout(border_layout)
        controls_layout.addWidget(self.border_group)

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

        # Text group
        text_group = QGroupBox("Text")
        text_layout = QVBoxLayout(text_group)
        self.text_lock_checkbox = QCheckBox("Text base = Hover = Click")
        self.text_lock_checkbox.setChecked(self.style.properties.get("text_lock", True))
        text_layout.addWidget(self.text_lock_checkbox)
        self.text_tabs = QTabWidget()
        self.text_controls = {}
        base_tab, self.text_controls['base'] = self._create_text_tab(self.style.properties)
        hover_tab, self.text_controls['hover'] = self._create_text_tab(self.style.hover_properties)
        click_tab, self.text_controls['click'] = self._create_text_tab(self.style.click_properties)
        self.text_tabs.addTab(base_tab, "Base")
        self.text_tabs.addTab(hover_tab, "Hover")
        self.text_tabs.addTab(click_tab, "Click")
        text_layout.addWidget(self.text_tabs)
        controls_layout.addWidget(text_group)
        controls_layout.addStretch(1)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        controls_layout.addWidget(self.button_box)

        preview_layout = QVBoxLayout()
        preview_group = QGroupBox("Preview")
        preview_group_layout = QVBoxLayout(); preview_group_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_stack = QStackedWidget()
        self.preview_button = PreviewButton("Preview")
        self.preview_button.setMinimumSize(200, 100)
        self.preview_switch = SwitchButton()
        self.preview_stack.addWidget(self.preview_button)
        self.preview_stack.addWidget(self.preview_switch)
        self.text_lock_checkbox.toggled.connect(self._on_text_lock_toggled)
        self._connect_base_text_signals()
        self._on_text_lock_toggled(self.text_lock_checkbox.isChecked())
        preview_group_layout.addWidget(self.preview_stack)
        preview_group.setLayout(preview_group_layout)
        preview_layout.addStretch(1); preview_layout.addWidget(preview_group); preview_layout.addStretch(1)

        main_layout.addLayout(controls_layout, 0, 0)
        main_layout.addLayout(preview_layout, 0, 1)

        for w in [self.font_size_spin, self.width_spin, self.height_spin,
                  self.border_width_spin, self.hover_border_radius_slider, self.hover_border_width_slider,
                  self.click_border_radius_slider, self.click_border_width_slider,
                  self.x1_spin, self.y1_spin, self.x2_spin, self.y2_spin]:
            w.valueChanged.connect(self.update_preview)
        self.component_type_combo.currentTextChanged.connect(self.update_preview)
        self.width_spin.valueChanged.connect(self.update_controls_state)
        self.height_spin.valueChanged.connect(self.update_controls_state)

        self._refresh_condition_table()
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
            if hasattr(self, 'text_controls') and btn is self.text_controls.get('base', {}).get('bg_color_btn'):
                self._sync_locked_text()
            self.update_preview()

    def _button_color(self, btn):
        return btn.property("color") or ""

    # --- Text group helpers -------------------------------------------------

    def _create_text_tab(self, data):
        tab = QWidget()
        layout = QGridLayout(tab)

        text_type_combo = QComboBox()
        text_type_combo.addItems(["Comment", "Simple text"])
        text_type_combo.setCurrentText(data.get("text_type", "Simple text"))

        comment_label = QLabel("Comment #:")
        comment_edit = QLineEdit(data.get("comment_number", ""))
        column_label = QLabel("Column:")
        column_spin = QSpinBox(); column_spin.setRange(1, 1000)
        column_spin.setValue(data.get("comment_column", 1))
        row_label = QLabel("Row:")
        row_spin = QSpinBox(); row_spin.setRange(1, 1000)
        row_spin.setValue(data.get("comment_row", 1))

        text_label = QLabel("Text:")
        text_edit = QLineEdit(data.get("simple_text", ""))

        font_label = QLabel("Font:")
        font_combo = QFontComboBox();
        font_combo.setCurrentFont(QFont(data.get("font_family", self.font().family())))
        size_label = QLabel("Size:")
        font_size_spin = QSpinBox(); font_size_spin.setRange(1, 1000)
        font_size_spin.setValue(data.get("font_size", 10))
        bold_check = QCheckBox("B"); bold_check.setChecked(data.get("font_bold", False))
        italic_check = QCheckBox("I"); italic_check.setChecked(data.get("font_italic", False))
        underline_check = QCheckBox("U"); underline_check.setChecked(data.get("font_underline", False))

        h_align_label = QLabel("H Align:")
        h_align_combo = QComboBox(); h_align_combo.addItems(["Left", "Center", "Right"])
        h_align_combo.setCurrentText(data.get("h_align", "Center"))
        v_align_label = QLabel("V Align:")
        v_align_combo = QComboBox(); v_align_combo.addItems(["Top", "Center", "Bottom"])
        v_align_combo.setCurrentText(data.get("v_align", "Center"))

        bg_label = QLabel("Background:")
        bg_btn = self.create_color_button(data.get("text_bg_color", ""))

        offset_x_label = QLabel("Offset X:")
        offset_x_spin = QSpinBox(); offset_x_spin.setRange(-1000, 1000)
        offset_x_spin.setValue(data.get("offset_x", 0))
        offset_y_label = QLabel("Offset Y:")
        offset_y_spin = QSpinBox(); offset_y_spin.setRange(-1000, 1000)
        offset_y_spin.setValue(data.get("offset_y", 0))

        layout.addWidget(QLabel("Text Type:"), 0, 0)
        layout.addWidget(text_type_combo, 0, 1, 1, 3)
        layout.addWidget(comment_label, 1, 0); layout.addWidget(comment_edit, 1, 1)
        layout.addWidget(column_label, 1, 2); layout.addWidget(column_spin, 1, 3)
        layout.addWidget(row_label, 2, 0); layout.addWidget(row_spin, 2, 1)
        layout.addWidget(text_label, 3, 0); layout.addWidget(text_edit, 3, 1, 1, 3)
        layout.addWidget(font_label, 4, 0); layout.addWidget(font_combo, 4, 1, 1, 3)
        layout.addWidget(size_label, 5, 0); layout.addWidget(font_size_spin, 5, 1)
        style_layout = QHBoxLayout(); style_layout.addWidget(bold_check); style_layout.addWidget(italic_check); style_layout.addWidget(underline_check)
        layout.addLayout(style_layout, 5, 2, 1, 2)
        layout.addWidget(h_align_label, 6, 0); layout.addWidget(h_align_combo, 6, 1)
        layout.addWidget(v_align_label, 6, 2); layout.addWidget(v_align_combo, 6, 3)
        layout.addWidget(bg_label, 7, 0); layout.addWidget(bg_btn, 7, 1)
        layout.addWidget(offset_x_label, 8, 0); layout.addWidget(offset_x_spin, 8, 1)
        layout.addWidget(offset_y_label, 8, 2); layout.addWidget(offset_y_spin, 8, 3)

        controls = {
            'text_type_combo': text_type_combo,
            'comment_label': comment_label,
            'comment_edit': comment_edit,
            'column_label': column_label,
            'column_spin': column_spin,
            'row_label': row_label,
            'row_spin': row_spin,
            'text_label': text_label,
            'text_edit': text_edit,
            'font_combo': font_combo,
            'font_size_spin': font_size_spin,
            'bold_check': bold_check,
            'italic_check': italic_check,
            'underline_check': underline_check,
            'h_align_combo': h_align_combo,
            'v_align_combo': v_align_combo,
            'bg_color_btn': bg_btn,
            'offset_x_spin': offset_x_spin,
            'offset_y_spin': offset_y_spin,
        }

        text_type_combo.currentTextChanged.connect(lambda _: self._on_text_type_changed(controls))
        self._on_text_type_changed(controls)

        return tab, controls

    def _on_text_type_changed(self, controls):
        is_comment = controls['text_type_combo'].currentText() == "Comment"
        for w in [controls['comment_label'], controls['comment_edit'], controls['column_label'], controls['column_spin'], controls['row_label'], controls['row_spin']]:
            w.setVisible(is_comment)
        for w in [controls['text_label'], controls['text_edit']]:
            w.setVisible(not is_comment)

    def _on_text_lock_toggled(self, checked):
        self.text_tabs.setTabEnabled(1, not checked)
        self.text_tabs.setTabEnabled(2, not checked)
        self._sync_locked_text()
        self.update_preview()

    def _sync_locked_text(self):
        if not getattr(self, 'text_controls', None):
            return
        if not self.text_lock_checkbox.isChecked():
            return
        base = self.text_controls['base']
        for key in ['hover', 'click']:
            ctrl = self.text_controls[key]
            ctrl['text_type_combo'].setCurrentText(base['text_type_combo'].currentText())
            ctrl['comment_edit'].setText(base['comment_edit'].text())
            ctrl['column_spin'].setValue(base['column_spin'].value())
            ctrl['row_spin'].setValue(base['row_spin'].value())
            ctrl['text_edit'].setText(base['text_edit'].text())
            ctrl['font_combo'].setCurrentFont(base['font_combo'].currentFont())
            ctrl['font_size_spin'].setValue(base['font_size_spin'].value())
            ctrl['bold_check'].setChecked(base['bold_check'].isChecked())
            ctrl['italic_check'].setChecked(base['italic_check'].isChecked())
            ctrl['underline_check'].setChecked(base['underline_check'].isChecked())
            ctrl['h_align_combo'].setCurrentText(base['h_align_combo'].currentText())
            ctrl['v_align_combo'].setCurrentText(base['v_align_combo'].currentText())
            color = self._button_color(base['bg_color_btn'])
            ctrl['bg_color_btn'].setProperty('color', color)
            self._set_button_color(ctrl['bg_color_btn'], color)
            ctrl['offset_x_spin'].setValue(base['offset_x_spin'].value())
            ctrl['offset_y_spin'].setValue(base['offset_y_spin'].value())
            self._on_text_type_changed(ctrl)

    def _connect_base_text_signals(self):
        base = self.text_controls['base']
        base['text_type_combo'].currentTextChanged.connect(self.update_preview)
        base['text_type_combo'].currentTextChanged.connect(self._sync_locked_text)
        base['comment_edit'].textChanged.connect(self.update_preview)
        base['comment_edit'].textChanged.connect(self._sync_locked_text)
        base['column_spin'].valueChanged.connect(self.update_preview)
        base['column_spin'].valueChanged.connect(self._sync_locked_text)
        base['row_spin'].valueChanged.connect(self.update_preview)
        base['row_spin'].valueChanged.connect(self._sync_locked_text)
        base['text_edit'].textChanged.connect(self.update_preview)
        base['text_edit'].textChanged.connect(self._sync_locked_text)
        base['font_combo'].currentFontChanged.connect(self.update_preview)
        base['font_combo'].currentFontChanged.connect(self._sync_locked_text)
        base['font_size_spin'].valueChanged.connect(self.update_preview)
        base['font_size_spin'].valueChanged.connect(self._sync_locked_text)
        base['bold_check'].toggled.connect(self.update_preview)
        base['bold_check'].toggled.connect(self._sync_locked_text)
        base['italic_check'].toggled.connect(self.update_preview)
        base['italic_check'].toggled.connect(self._sync_locked_text)
        base['underline_check'].toggled.connect(self.update_preview)
        base['underline_check'].toggled.connect(self._sync_locked_text)
        base['h_align_combo'].currentTextChanged.connect(self.update_preview)
        base['h_align_combo'].currentTextChanged.connect(self._sync_locked_text)
        base['v_align_combo'].currentTextChanged.connect(self.update_preview)
        base['v_align_combo'].currentTextChanged.connect(self._sync_locked_text)
        base['offset_x_spin'].valueChanged.connect(self.update_preview)
        base['offset_x_spin'].valueChanged.connect(self._sync_locked_text)
        base['offset_y_spin'].valueChanged.connect(self.update_preview)
        base['offset_y_spin'].valueChanged.connect(self._sync_locked_text)

    def _collect_text_props(self, controls):
        data = {
            'text_type': controls['text_type_combo'].currentText(),
            'font_family': controls['font_combo'].currentFont().family(),
            'font_size': controls['font_size_spin'].value(),
            'font_bold': controls['bold_check'].isChecked(),
            'font_italic': controls['italic_check'].isChecked(),
            'font_underline': controls['underline_check'].isChecked(),
            'h_align': controls['h_align_combo'].currentText(),
            'v_align': controls['v_align_combo'].currentText(),
            'text_bg_color': self._button_color(controls['bg_color_btn']),
            'offset_x': controls['offset_x_spin'].value(),
            'offset_y': controls['offset_y_spin'].value(),
        }
        if data['text_type'] == 'Comment':
            data.update({
                'comment_number': controls['comment_edit'].text(),
                'comment_column': controls['column_spin'].value(),
                'comment_row': controls['row_spin'].value(),
                'simple_text': '',
            })
        else:
            data.update({
                'simple_text': controls['text_edit'].text(),
                'comment_number': '',
                'comment_column': 0,
                'comment_row': 0,
            })
        return data

    def _alignment_flags(self, h_align: str, v_align: str) -> str:
        """Convert alignment options to Qt flag strings for QSS."""
        h_map = {
            'Left': 'AlignLeft',
            'Center': 'AlignHCenter',
            'Right': 'AlignRight'
        }
        v_map = {
            'Top': 'AlignTop',
            'Center': 'AlignVCenter',
            'Bottom': 'AlignBottom'
        }
        return f"{h_map.get(h_align, 'AlignHCenter')} | {v_map.get(v_align, 'AlignVCenter')}"

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

        self.shape_style_label.setVisible(not is_switch)
        self.shape_style_combo.setVisible(not is_switch)
        self.border_group.setVisible(not is_switch)

        is_circle = component_type == "Circle Button"
        for w in [self.tl_radius_label, self.tl_radius_spin, self.tr_radius_label, self.tr_radius_spin,
                  self.bl_radius_label, self.bl_radius_spin, self.br_radius_label, self.br_radius_spin,
                  self.link_radius_btn]:
            w.setEnabled(not is_circle and not is_switch)

        is_gradient = self.bg_type_combo.currentText() == "Linear Gradient"
        for w in [self.gradient_dir_label, self.gradient_type_combo]:
            w.setVisible(is_gradient)

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
        border_style = self.border_style_combo.currentText()
        bg_color = self._bg_color
        hover_bg_color = self._hover_bg_color
        click_bg_color = self._click_bg_color
        border_color = self._border_color

        base_text = self._collect_text_props(self.text_controls['base'])
        hover_text = base_text if self.text_lock_checkbox.isChecked() else self._collect_text_props(self.text_controls['hover'])
        click_text = base_text if self.text_lock_checkbox.isChecked() else self._collect_text_props(self.text_controls['click'])

        text_color = self._button_color(self.text_color_btn) or self.palette().color(QPalette.ColorRole.ButtonText).name()
        hover_text_color = self._button_color(self.hover_text_btn) or text_color
        click_text_color = self._button_color(self.click_text_btn) or text_color

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

        def _text_qss(text_props, color):
            lines = [
                f"color: {color};",
                f"font-size: {text_props.get('font_size', 0)}pt;",
                f"font-family: '{text_props.get('font_family', '')}';",
                f"font-weight: {'bold' if text_props.get('font_bold') else 'normal'};",
                f"font-style: {'italic' if text_props.get('font_italic') else 'normal'};",
                f"text-align: {text_props.get('h_align', 'left').lower()};",
                f"qproperty-alignment: {self._alignment_flags(text_props.get('h_align', 'Center'), text_props.get('v_align', 'Center'))};",
            ]
            if text_props.get('font_underline'):
                lines.append("text-decoration: underline;")
            return lines

        main_qss, hover_qss, pressed_qss = [], [], []
        main_qss.extend([
            f"padding: {padding}px;",
            f"border-top-left-radius: {tl_radius}px;",
            f"border-top-right-radius: {tr_radius}px;",
            f"border-bottom-right-radius: {br_radius}px;",
            f"border-bottom-left-radius: {bl_radius}px;",
        ])
        main_qss.extend(_text_qss(base_text, text_color))

        hover_qss.extend(_text_qss(hover_text, hover_text_color))
        pressed_qss.extend(_text_qss(click_text, click_text_color))

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
        base = self.text_controls['base'] if hasattr(self, 'text_controls') else None
        if base:
            if base['text_type_combo'].currentText() == "Simple text":
                text = base['text_edit'].text()
            else:
                text = f"{base['comment_edit'].text()}[{base['row_spin'].value()},{base['column_spin'].value()}]"
            self.preview_button.setText(text)
            font = base['font_combo'].currentFont()
            font.setPointSize(base['font_size_spin'].value())
            font.setBold(base['bold_check'].isChecked())
            font.setItalic(base['italic_check'].isChecked())
            font.setUnderline(base['underline_check'].isChecked())
            self.preview_button.setFont(font)
        qss = self.generate_qss(component_type)
        if component_type == "Toggle Switch":
            self.preview_switch.setStyleSheet(qss)
        else:
            self.preview_button.setStyleSheet(qss)

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
            "border_style": self.border_style_combo.currentText(),
            "border_color": self._button_color(self.border_color_btn),
        }

        base_text = self._collect_text_props(self.text_controls['base'])
        properties.update(base_text)
        properties["text_lock"] = self.text_lock_checkbox.isChecked()

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

        if self.text_lock_checkbox.isChecked():
            hover_properties.update(base_text)
            click_properties.update(base_text)
        else:
            hover_properties.update(self._collect_text_props(self.text_controls['hover']))
            click_properties.update(self._collect_text_props(self.text_controls['click']))

        style = ConditionalStyle(
            style_id=self.style.style_id,
            conditions=self.conditions,
            properties=properties,
            hover_properties=hover_properties,
            click_properties=click_properties,
            tooltip=self.tooltip_edit.text(),
        )
        return style