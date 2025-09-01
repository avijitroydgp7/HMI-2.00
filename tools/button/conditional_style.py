from typing import Dict, Any, List, Optional, ClassVar, Callable, Union, Tuple
from tools.button.actions.constants import TriggerMode
from dataclasses import dataclass, field
import copy
import ast
import logging
from collections import OrderedDict

from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
    Qt,
    QSize,
    QPropertyAnimation,
    QEasingCurve,
    pyqtProperty,
    QPoint,
    QRect,
    QRectF,
)
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
    QTabWidget,
    QWidget,
    QStackedWidget,
    QFrame,
    QTextEdit,
    QToolButton,
    QButtonGroup,
    QHBoxLayout,
    QCheckBox,
    QScrollArea,
    QFileDialog,
    QToolTip,
    QMessageBox,
    QStyle,
)
from PyQt6.QtGui import (
    QColor,
    QPixmap,
    QIcon,
    QPalette,
    QPainter,
    QLinearGradient,
    QPen,
    QFontDatabase,
    QBrush,
)

from PyQt6.QtSvg import QSvgRenderer
from utils.icon_manager import IconManager
from dialogs.icon_picker_dialog import IconPickerDialog
from utils.dpi import dpi_scale
import os
from dialogs.widgets import TagSelector
from services.comment_data_service import comment_data_service

# ---------------------------------------------------------------------------
# Logging setup for condition evaluation
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tiny LRU cache for parsed ASTs to speed up repeated conditions
# ---------------------------------------------------------------------------

_AST_CACHE: "OrderedDict[str, ast.AST]" = OrderedDict()
_AST_CACHE_MAXSIZE = 128


def _get_parsed_ast(expr: str) -> ast.AST:
    node = _AST_CACHE.get(expr)
    if node is not None:
        # mark as recently used
        _AST_CACHE.move_to_end(expr)
        return node
    node = ast.parse(expr, mode="eval")
    _AST_CACHE[expr] = node
    # evict oldest
    if len(_AST_CACHE) > _AST_CACHE_MAXSIZE:
        _AST_CACHE.popitem(last=False)
    return node


def _safe_eval(expr: str, variables: Dict[str, Any]) -> Tuple[Any, Optional[str]]:
    """Safely evaluate a small Python expression.

    Returns a tuple of (value, error). On success, error is None. On failure,
    value is None and error contains a concise message.

    Only a restricted subset of Python expressions is supported consisting of
    literals, variable names, boolean operations, arithmetic operators and
    comparisons. Any use of function calls, attribute access or other Python
    constructs will result in an error message.
    """

    try:
        tree = _get_parsed_ast(expr)
    except SyntaxError as exc:  # pragma: no cover - syntax error path
        logger.warning("Condition syntax error: %s", exc)
        return None, "Invalid expression syntax"
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Unexpected error parsing condition")
        return None, f"Parse error: {exc}"

    def _eval(node: ast.AST):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.BoolOp):
            values = [_eval(v) for v in node.values]
            if isinstance(node.op, ast.And):
                return all(values)
            if isinstance(node.op, ast.Or):
                return any(values)
            raise ValueError("Unsupported boolean operator")
        if isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.Mod):
                return left % right
            raise ValueError("Unsupported binary operator")
        if isinstance(node, ast.UnaryOp):
            operand = _eval(node.operand)
            if isinstance(node.op, ast.Not):
                return not operand
            if isinstance(node.op, ast.UAdd):
                return +operand
            if isinstance(node.op, ast.USub):
                return -operand
            raise ValueError("Unsupported unary operator")
        if isinstance(node, ast.Compare):
            left = _eval(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = _eval(comparator)
                if isinstance(op, ast.Eq):
                    if not (left == right):
                        return False
                elif isinstance(op, ast.NotEq):
                    if not (left != right):
                        return False
                elif isinstance(op, ast.Lt):
                    if not (left < right):
                        return False
                elif isinstance(op, ast.LtE):
                    if not (left <= right):
                        return False
                elif isinstance(op, ast.Gt):
                    if not (left > right):
                        return False
                elif isinstance(op, ast.GtE):
                    if not (left >= right):
                        return False
                else:  # pragma: no cover - unsupported comparisons
                    raise ValueError("Unsupported comparison operator")
                left = right
            return True
        if isinstance(node, ast.Name):
            if node.id in variables:
                return variables[node.id]
            raise ValueError(f"Unknown variable '{node.id}'")
        if isinstance(node, ast.Call):
            # Disallow any function calls for safety
            raise ValueError("Function calls are not allowed")
        if isinstance(node, ast.Attribute):
            # Disallow attribute access for safety
            raise ValueError("Attribute access is not allowed")
        if isinstance(node, ast.Constant):
            return node.value
        raise ValueError(f"Unsupported expression: {ast.dump(node)}")

    try:
        return _eval(tree), None
    except Exception as exc:
        logger.debug("Condition evaluation error for '%s': %s", expr, exc)
        return None, str(exc)


# ---------------------------------------------------------------------------
# Helper widgets previously provided by button_creator
# ---------------------------------------------------------------------------


class SwitchButton(QPushButton):
    """A custom toggle switch used for previewing switch styles.

    Toggle switches always use a fixed 50px corner radius.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 100)

        self._handle_x_pos = 50
        self.animation = QPropertyAnimation(self, b"handle_x_pos", self)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.setDuration(200)

        self._handle_color = QColor("white")
        self._on_is_left = False  # Default: 'on' state is on the right

        # Set initial state based on default alignment without animation
        self.set_alignment(False)

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
    """Button capable of displaying SVG or QtAwesome icons for previewing styles."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._base_icon = QIcon()
        self._hover_icon = QIcon()
        self.icon_size = QSize(dpi_scale(50), dpi_scale(50))
        self.setIconSize(self.icon_size)

    def set_icon(self, source: str):
        icon = self._create_icon_from_source(source)
        self._base_icon = icon
        self.setIcon(icon)
        self.update()

    def set_hover_icon(self, source: str):
        icon = self._create_icon_from_source(source)
        self._hover_icon = icon
        self.update()

    def set_icon_size(self, size: int):
        self.icon_size = QSize(size, size)
        self.setIconSize(self.icon_size)
        self.update()

    def _create_icon_from_source(self, source: Optional[str]) -> QIcon:
        if not source:
            return QIcon()
        src = str(source)
        if src.startswith("qta:"):
            name = src.split(":", 1)[1]
            return IconManager.create_icon(name)
        ext = os.path.splitext(src)[1].lower()
        if ext == ".svg":
            renderer = QSvgRenderer(src)
            if renderer.isValid():
                pixmap = QPixmap(self.icon_size)
                pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(pixmap)
                renderer.render(painter)
                painter.end()
                return QIcon(pixmap)
            return QIcon()
        pix = QPixmap(src)
        if pix and not pix.isNull():
            return QIcon(pix)
        return QIcon()

    def enterEvent(self, e):
        if not self._hover_icon.isNull():
            self.setIcon(self._hover_icon)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.setIcon(self._base_icon)
        super().leaveEvent(e)


# Predefined gradient orientations used for visual selection
_GRADIENT_STYLES = {
    "Top to Bottom": (0, 0, 0, 1),
    "Bottom to Top": (0, 1, 0, 0),
    "Left to Right": (0, 0, 1, 0),
    "Right to Left": (1, 0, 0, 0),
    "Diagonal TL-BR": (0, 0, 1, 1),
    "Diagonal BL-TR": (0, 1, 1, 0),
}

from tools.button.default_styles import (
    get_all_styles as _get_all_styles,
    get_style_by_id as _get_style_by_id,
)


def get_styles() -> List[Dict[str, Any]]:
    """Return the list of built-in button style definitions."""
    return _get_all_styles()


def get_style_by_id(style_id: str) -> Dict[str, Any]:
    """Return a style definition by its unique ID."""
    return _get_style_by_id(style_id)


@dataclass(slots=True)
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


@dataclass(slots=True)
class ConditionalStyle:
    """A style that can be applied to a button.

    Attributes
    ----------
    condition:
        Boolean expression or callable evaluated against tag values to
        determine when this style is active.  String expressions are evaluated
        with tag names available as variables, while callables receive the
        ``tag_values`` dictionary.  ``None`` means the style always applies.
    """

    style_id: str = ""
    condition: Optional[Union[str, Callable[[Dict[str, Any]], bool]]] = None
    condition_data: Dict[str, Any] = field(
        default_factory=lambda: {"mode": TriggerMode.ORDINARY.value}
    )
    # core text/style attributes
    text_type: str = "Text"
    text_value: str = ""
    comment_ref: Dict[str, Any] = field(default_factory=dict)
    font_family: str = ""
    font_size: int = 0
    bold: bool = False
    italic: bool = False
    underline: bool = False
    background_color: str = ""
    text_color: str = ""
    h_align: str = "center"
    v_align: str = "middle"
    offset: int = 0
    icon: str = ""
    hover_icon: str = ""
    # miscellaneous properties remain grouped
    properties: Dict[str, Any] = field(default_factory=dict)
    tooltip: str = ""
    hover_properties: Dict[str, Any] = field(default_factory=dict)
    animation: AnimationProperties = field(default_factory=AnimationProperties)
    style_sheet: str = ""

    @staticmethod
    def _normalize_state(props: Dict[str, Any]) -> Dict[str, Any]:
        """Return a state dictionary containing the expected keys.

        Older dictionaries may use legacy key names (e.g. ``vertical_align``)
        or include text/comment fields without the new ``text_value`` /
        ``comment_ref`` structure.  This helper converts such dictionaries into
        the unified format used by :class:`ConditionalStyle`.
        """
        defaults = {
            "text_type": "Text",
            "text_value": "",
            "comment_ref": {},
            "font_family": "",
            "font_size": 0,
            "bold": False,
            "italic": False,
            "underline": False,
            "background_color": "",
            "text_color": "",
            "h_align": "center",
            "v_align": "middle",
            "offset": 0,
        }
        if not props:
            return defaults.copy()

        data = dict(props)
        # Map legacy keys to new ones
        if "text" in data and "text_value" not in data:
            data["text_value"] = data.get("text", "")
        if data.get("text_type") == "Comment" and "comment_ref" not in data:
            data["comment_ref"] = {
                "number": data.get("comment_number", 0),
                "column": data.get("comment_column", 0),
                "row": data.get("comment_row", 0),
            }
        if "horizontal_align" in data and "h_align" not in data:
            data["h_align"] = data.get("horizontal_align")
        if "vertical_align" in data and "v_align" not in data:
            data["v_align"] = data.get("vertical_align")
        if "offset_to_frame" in data and "offset" not in data:
            data["offset"] = data.get("offset_to_frame")

        normalized = defaults.copy()
        for key in normalized.keys():
            normalized[key] = data.get(key, normalized[key])
        return normalized

    def to_dict(self) -> Dict[str, Any]:
        cond = copy.deepcopy(self.condition_data)
        return {
            "style_id": self.style_id,
            "condition": self.condition if isinstance(self.condition, str) else None,
            "condition_data": cond,
            "tooltip": self.tooltip,
            "text_type": self.text_type,
            "text_value": self.text_value,
            "comment_ref": self.comment_ref,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "bold": self.bold,
            "italic": self.italic,
            "underline": self.underline,
            "background_color": self.background_color,
            "text_color": self.text_color,
            "h_align": self.h_align,
            "v_align": self.v_align,
            "offset": self.offset,
            "icon": self.icon,
            "hover_icon": self.hover_icon,
            "properties": self.properties,
            "hover_properties": self._normalize_state(self.hover_properties),
            "animation": self.animation.to_dict(),
            "style_sheet": self.style_sheet,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConditionalStyle":
        props = data.get("properties", {})
        hover = cls._normalize_state(data.get("hover_properties", {}))
        style = cls(
            style_id=data.get("style_id", ""),
            condition=data.get("condition"),
            tooltip=data.get("tooltip", ""),
            icon=data.get("icon", data.get("svg_icon", "")),
            hover_icon=data.get("hover_icon", ""),
            text_type=data.get("text_type", props.get("text_type", "Text")),
            text_value=data.get("text_value", props.get("text", "")),
            comment_ref=data.get(
                "comment_ref",
                (
                    {
                        "number": props.get("comment_number", 0),
                        "column": props.get("comment_column", 0),
                        "row": props.get("comment_row", 0),
                    }
                    if props.get("text_type") == "Comment"
                    else {}
                ),
            ),
            font_family=data.get("font_family", props.get("font_family", "")),
            font_size=data.get("font_size", props.get("font_size", 0)),
            bold=data.get("bold", props.get("bold", False)),
            italic=data.get("italic", props.get("italic", False)),
            underline=data.get("underline", props.get("underline", False)),
            background_color=data.get(
                "background_color", props.get("background_color", "")
            ),
            text_color=data.get("text_color", props.get("text_color", "")),
            h_align=data.get("h_align", props.get("horizontal_align", "center")),
            v_align=data.get("v_align", props.get("vertical_align", "middle")),
            offset=data.get("offset", props.get("offset_to_frame", 0)),
            properties=props,
            hover_properties=hover,
            style_sheet=data.get("style_sheet", ""),
        )
        cond = data.get("condition_data", {"mode": TriggerMode.ORDINARY.value})
        if cond.get("mode") in (TriggerMode.ON.value, TriggerMode.OFF.value):
            if "operand1" not in cond and "tag" in cond:
                cond["operand1"] = cond.pop("tag")
        if cond.get("mode") == TriggerMode.RANGE.value:
            if "operand1" not in cond and "tag" in cond:
                cond["operand1"] = cond.pop("tag")
            if "operand2" not in cond and "operand" in cond:
                cond["operand2"] = cond.pop("operand")
            if "lower_bound" not in cond and "lower" in cond:
                cond["lower_bound"] = cond.pop("lower")
            if "upper_bound" not in cond and "upper" in cond:
                cond["upper_bound"] = cond.pop("upper")
            if "operator" not in cond:
                if (
                    cond.get("lower_bound") is not None
                    or cond.get("upper_bound") is not None
                ):
                    cond["operator"] = "between"
                else:
                    cond["operator"] = "=="

        if cond.get("mode") in (
            TriggerMode.ON.value,
            TriggerMode.OFF.value,
            TriggerMode.RANGE.value,
        ):
            op1 = cond.get("operand1")
            if op1 and "main_tag" not in op1 and "source" in op1:
                cond["operand1"] = {"main_tag": op1, "indices": []}
        style.condition_data = cond
        if "animation" in data:
            style.animation = AnimationProperties.from_dict(data["animation"])
        return style


@dataclass(slots=True)
class ConditionalStyleManager(QObject):
    """Manages conditional styles for buttons"""
    # Emitted when a condition fails to evaluate; payload is an error message.
    condition_error = pyqtSignal(str)
    parent: Optional[QObject] = None
    conditional_styles: List[ConditionalStyle] = field(default_factory=list)
    default_style: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        QObject.__init__(self, self.parent)

    def _generate_unique_style_id(self, base_id: str) -> str:
        existing = {s.style_id for s in self.conditional_styles}
        if base_id not in existing:
            return base_id
        suffix = 1
        new_id = f"{base_id}_{suffix}"
        while new_id in existing:
            suffix += 1
            new_id = f"{base_id}_{suffix}"
        return new_id

    def add_style(self, style: ConditionalStyle):
        """Add a new conditional style"""
        style.style_id = self._generate_unique_style_id(style.style_id)
        self.conditional_styles.append(style)

    def remove_style(self, index: int):
        """Remove a conditional style by index"""
        if 0 <= index < len(self.conditional_styles):
            del self.conditional_styles[index]

    def update_style(self, index: int, style: ConditionalStyle):
        """Update an existing conditional style"""
        if 0 <= index < len(self.conditional_styles):
            self.conditional_styles[index] = style

    def get_active_style(
        self, tag_values: Optional[Dict[str, Any]] = None, state: Optional[str] = None
    ) -> Dict[str, Any]:
        """Determine which style should be active based on tag values.

        Styles are checked in the order they appear in ``conditional_styles``.
        The first style whose ``condition`` evaluates to ``True`` is used. A
        condition may be a Python expression string evaluated with ``tag_values``
        as the local namespace, or a callable accepting ``tag_values`` and
        returning ``True``/``False``. If no conditions match, ``default_style``
        is returned.

        Parameters
        ----------
        tag_values: Dict[str, Any], optional
            Current tag values used when evaluating style conditions.
        state: Optional[str]
            Optional visual state for which to retrieve additional properties.
            Supported states: ``"hover"``.  Click styles are no longer
            handled.
        """
        tag_values = tag_values or {}

        for style in self.conditional_styles:
            cond_cfg = getattr(
                style, "condition_data", {"mode": TriggerMode.ORDINARY.value}
            )
            cond = style.condition
            condition = (
                cond_cfg
                if cond_cfg.get("mode", TriggerMode.ORDINARY.value)
                != TriggerMode.ORDINARY.value
                else cond
            )
            match, err = self._evaluate_condition(condition, tag_values)
            if err:
                # Surface via signal and log, but continue to next style.
                try:
                    type(self).condition_error.emit(err)
                except Exception:
                    # In case Qt isn't initialised in some contexts
                    pass
                logger.warning("Condition evaluation error: %s", err)

            if match:
                props = dict(style.properties)
                # Only return the icon relevant for the current state.
                if state == "hover" and style.hover_icon:
                    props["icon"] = style.hover_icon
                else:
                    props["icon"] = style.icon
                if state:
                    props.update(getattr(style, f"{state}_properties", {}))
                if style.tooltip:
                    props["tooltip"] = style.tooltip
                return props

        return dict(self.default_style)

    def _evaluate_condition(
        self, condition: Any, tag_values: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Evaluate a condition using tag values.

        ``condition`` may be one of the following:

        * ``None`` â€“ always ``True``
        * ``dict`` â€“ a configuration dictionary as produced by the editor
        * ``str`` â€“ a Python expression evaluated by :func:`_safe_eval`
        * ``callable`` â€“ a function receiving ``tag_values``
        """

        if condition is None:
            return True, None

        if isinstance(condition, dict):
            cfg = condition
            mode = cfg.get("mode", TriggerMode.ORDINARY.value)
            if mode == TriggerMode.ORDINARY.value:
                return True, None
            if mode in (TriggerMode.ON.value, TriggerMode.OFF.value):
                op1 = cfg.get("operand1", cfg.get("tag"))
                tag_val = self._extract_value(op1, tag_values)
                if tag_val is None:
                    return False, "ON/OFF condition: operand1 tag value not found"
                return (
                    bool(tag_val) if mode == TriggerMode.ON.value else not bool(tag_val)
                ), None
            if mode == TriggerMode.RANGE.value:
                op1 = cfg.get("operand1", cfg.get("tag"))
                tag_val = self._extract_value(op1, tag_values)
                if tag_val is None:
                    return False, "RANGE condition: operand1 tag value not found"
                operator = cfg.get("operator", "==")
                if operator in ["between", "outside"]:
                    lower = self._extract_value(
                        cfg.get("lower_bound", cfg.get("lower")), tag_values
                    )
                    upper = self._extract_value(
                        cfg.get("upper_bound", cfg.get("upper")), tag_values
                    )
                    try:
                        if operator == "between":
                            return (lower <= tag_val <= upper), None
                        else:
                            return (tag_val < lower or tag_val > upper), None
                    except Exception as exc:
                        return False, f"RANGE condition error: {exc}"
                else:
                    operand = self._extract_value(
                        cfg.get("operand2", cfg.get("operand")), tag_values
                    )
                    if operand is None:
                        return False, "RANGE condition: operand2 value not found"
                    try:
                        if operator == "==":
                            return (tag_val == operand), None
                        if operator == "!=":
                            return (tag_val != operand), None
                        if operator == ">":
                            return (tag_val > operand), None
                        if operator == ">=":
                            return (tag_val >= operand), None
                        if operator == "<":
                            return (tag_val < operand), None
                        if operator == "<=":
                            return (tag_val <= operand), None
                    except Exception as exc:
                        return False, f"RANGE comparison error: {exc}"
                    return False, f"Unsupported operator: {operator}"
            return False, f"Unsupported mode: {mode}"

        if callable(condition):
            try:
                return bool(condition(tag_values)), None
            except Exception as exc:
                return False, f"Callable condition error: {exc}"

        if isinstance(condition, str):
            val, err = _safe_eval(condition, tag_values)
            if err:
                return False, f"Expression error: {err}"
            return bool(val), None

        try:
            return bool(condition), None
        except Exception as exc:
            return False, f"Invalid condition type: {exc}"

    def _extract_value(
        self, data: Optional[Dict[str, Any]], tag_values: Dict[str, Any]
    ):
        if not data:
            return None
        if "source" in data:
            source = data.get("source")
            value = data.get("value")
        else:
            main = data.get("main_tag", {})
            source = main.get("source")
            value = main.get("value")
        if source == "constant":
            try:
                return float(value)
            except Exception:
                return None
        if source == "tag" and isinstance(value, dict):
            return tag_values.get(value.get("tag_name"))
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize style data without component identifiers."""
        return {
            "conditional_styles": [
                style.to_dict() for style in self.conditional_styles
            ],
            "default_style": self.default_style,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConditionalStyleManager":
        """Deserialize from dictionary data without component identifiers."""
        manager = cls()
        manager.conditional_styles = [
            ConditionalStyle.from_dict(style_data)
            for style_data in data.get("conditional_styles", [])
        ]
        manager.default_style = data.get("default_style", {})
        return manager


class PreviewButton(IconButton):
    """Preview button that relies on style sheets for rendering."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self.setText(text)


class ConditionalStyleEditorDialog(QDialog):
    _TEXT_KEYS = [
        "text_type_combo",
        "comment_number",
        "comment_column",
        "comment_row",
        "text_edit",
        "font_family_combo",
        "font_size_spin",
        "bold_btn",
        "italic_btn",
        "underline_btn",
        "bg_base_combo",
        "bg_shade_combo",
        "text_base_combo",
        "text_shade_combo",
        "v_align_group",
        "h_align_group",
        "offset_spin",
    ]

    def __init__(self, parent=None, style: Optional[ConditionalStyle] = None):
        super().__init__(parent)
        self.setWindowTitle("Conditional Style")
        self.style = copy.deepcopy(style) if style else ConditionalStyle()
        self._text_color = self.style.properties.get("text_color", "")
        self._hover_text_color = self.style.hover_properties.get("text_color", "")

        # Initialize background-related colors so early update/preview calls
        # have default values to work with.  These will be overwritten once
        # the proper colour scheme is applied via ``set_initial_colors``.
        self._bg_color = QColor()
        self._hover_bg_color = QColor()
        self._bg_color2 = QColor()
        self._border_color = QColor()

        main_layout = QGridLayout(self)
        # Provide consistent padding around the dialog and space between cells
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setHorizontalSpacing(10)
        main_layout.setVerticalSpacing(10)
        # Give the options area more space than the preview pane
        main_layout.setColumnStretch(0, 3)
        main_layout.setColumnStretch(1, 1)
        main_layout.setRowStretch(2, 1)

        # Listen for condition errors emitted by the manager, if any
        try:
            ConditionalStyleManager.condition_error.connect(self.handle_condition_error)
        except Exception:
            # If Qt not fully initialized or signal unavailable, ignore
            pass

        info_group = QGroupBox("General")
        info_layout = QGridLayout()
        info_layout.setContentsMargins(5, 5, 5, 5)
        info_layout.setHorizontalSpacing(8)
        tooltip_label = QLabel("Tooltip:")
        tooltip_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.tooltip_edit = QLineEdit(self.style.tooltip)
        info_layout.addWidget(tooltip_label, 0, 0)
        info_layout.addWidget(self.tooltip_edit, 0, 1)
        info_layout.setColumnStretch(1, 1)
        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group, 0, 0, 1, 2)

        self.init_colors()

        style_group = QGroupBox("Component Style & background")
        style_layout = QGridLayout()
        style_layout.setContentsMargins(5, 5, 5, 5)
        style_layout.setHorizontalSpacing(8)
        style_layout.setVerticalSpacing(6)
        style_layout.setColumnStretch(1, 1)

        component_label = QLabel("Component Type:")
        component_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        style_layout.addWidget(component_label, 0, 0)
        self.component_type_combo = QComboBox()
        self.component_type_combo.addItems(
            [
                "Standard Button",
                "Circle Button",
                "Toggle Switch",
            ]
        )
        self.component_type_combo.setCurrentText(
            self.style.properties.get("component_type", "Standard Button")
        )
        self.component_type_combo.currentTextChanged.connect(self.update_controls_state)
        style_layout.addWidget(self.component_type_combo, 0, 1)

        self.shape_style_label = QLabel("Shape Style:")
        self.shape_style_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        style_layout.addWidget(self.shape_style_label, 1, 0)
        self.shape_style_combo = QComboBox()
        self.shape_style_combo.addItems(
            ["Flat", "3D", "Glass", "Outline"]
        )
        self.shape_style_combo.setCurrentText(
            self.style.properties.get("shape_style", "Flat")
        )
        self.shape_style_combo.currentTextChanged.connect(self.update_preview)
        style_layout.addWidget(self.shape_style_combo, 1, 1)

        bg_type_label = QLabel("Background Type:")
        bg_type_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        style_layout.addWidget(bg_type_label, 2, 0)
        self.bg_type_combo = QComboBox()
        self.bg_type_combo.addItems(["Solid", "Linear Gradient"])
        self.bg_type_combo.setCurrentText(
            self.style.properties.get("background_type", "Solid")
        )
        self.bg_type_combo.currentTextChanged.connect(self.update_controls_state)
        style_layout.addWidget(self.bg_type_combo, 2, 1)

        main_color_label = QLabel("Main Color:")
        main_color_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        style_layout.addWidget(main_color_label, 3, 0)
        self.bg_base_color_combo, self.bg_shade_combo = (
            self.create_color_selection_widgets(
                self.on_bg_color_changed, emit_initial=False
            )
        )
        style_layout.addWidget(self.bg_base_color_combo, 3, 1)
        style_layout.addWidget(self.bg_shade_combo, 4, 1)

        # Hidden coordinate spin boxes used internally to build the QSS gradient
        self.x1_spin = self.create_coord_spinbox(
            self.style.properties.get("gradient_x1", 0)
        )
        self.y1_spin = self.create_coord_spinbox(
            self.style.properties.get("gradient_y1", 0)
        )
        self.x2_spin = self.create_coord_spinbox(
            self.style.properties.get("gradient_x2", 0)
        )
        self.y2_spin = self.create_coord_spinbox(
            self.style.properties.get("gradient_y2", 1)
        )
        for w in [self.x1_spin, self.y1_spin, self.x2_spin, self.y2_spin]:
            w.setVisible(False)

        self.gradient_dir_label = QLabel("Gradient Direction:")
        self.gradient_dir_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        style_layout.addWidget(self.gradient_dir_label, 5, 0)
        self.gradient_type_combo = QComboBox()
        self._init_gradient_type_combo()
        style_layout.addWidget(self.gradient_type_combo, 5, 1)

        style_group.setLayout(style_layout)
        main_layout.addWidget(style_group, 1, 0)

        options_group = QGroupBox("Style Options")
        options_layout = QGridLayout()
        options_layout.setContentsMargins(5, 5, 5, 5)
        options_layout.setHorizontalSpacing(10)
        options_layout.setVerticalSpacing(10)
        options_layout.setColumnStretch(0, 1)
        options_layout.setColumnStretch(1, 1)
        options_group.setLayout(options_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(options_group)

        self.border_group = QGroupBox("Border")
        border_layout = QGridLayout()
        border_layout.setContentsMargins(5, 5, 5, 5)
        border_layout.setHorizontalSpacing(8)
        border_layout.setVerticalSpacing(6)
        border_layout.setColumnStretch(1, 1)

        # Corner radius table
        self.corner_frame = QFrame()
        self.corner_frame.setStyleSheet("QFrame { border: 1px solid #666; }")
        corner_layout = QGridLayout(self.corner_frame)
        corner_layout.setContentsMargins(2, 2, 2, 2)
        corner_layout.setSpacing(2)

        header = QLabel("Corner radius")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        corner_layout.addWidget(header, 0, 0, 1, 3)

        self.link_radius_btn = QPushButton()
        self.link_radius_btn.setCheckable(True)
        # Default to linked corners
        self.link_radius_btn.setChecked(True)
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

        for w in [
            header,
            self.link_radius_btn,
            left_label,
            right_label,
            top_label,
            bottom_label,
        ]:
            w.setStyleSheet("border: 1px solid #666;")

        self.corner_spins = {
            "tl": self.tl_radius_spin,
            "tr": self.tr_radius_spin,
            "br": self.br_radius_spin,
            "bl": self.bl_radius_spin,
        }
        for key, spin in self.corner_spins.items():
            spin.valueChanged.connect(
                lambda val, k=key: self.on_corner_radius_changed(k, val)
            )
        self.link_radius_btn.toggled.connect(self.on_link_radius_toggled)
        # Initialize icon without forcing values to unify on startup
        init_icon = "fa5s.link" if self.link_radius_btn.isChecked() else "fa5s.unlink"
        self.link_radius_btn.setIcon(IconManager.create_icon(init_icon))

        border_layout.addWidget(self.corner_frame, 0, 0, 1, 2)

        border_width_label = QLabel("Border Width (px):")
        border_width_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        border_layout.addWidget(border_width_label, 2, 0)
        self.border_width_spin = QSpinBox()
        # Allow border width up to 20px, final limit is adjusted dynamically
        self.border_width_spin.setRange(0, 20)
        self.border_width_spin.setValue(self.style.properties.get("border_width", 0))
        self.border_width_spin.valueChanged.connect(self.update_preview)
        border_layout.addWidget(self.border_width_spin, 2, 1)

        self.border_style_label = QLabel("Border Style:")
        self.border_style_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        border_layout.addWidget(self.border_style_label, 1, 0)
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
        self.border_style_combo.currentIndexChanged.connect(
            self.on_border_style_changed
        )
        border_layout.addWidget(self.border_style_combo, 1, 1)

        self.border_group.setLayout(border_layout)

        # Style tabs
        style_tabs = QTabWidget()

        self.base_tab, self.base_controls = self._build_state_tab(
            self.style.properties, "base"
        )

        style_tabs.addTab(self.base_tab, "Base")

        self.hover_tab, self.hover_controls = self._build_state_tab(
            self.style.hover_properties, "hover"
        )
        style_tabs.addTab(self.hover_tab, "Hover")
        self.base_controls["icon_edit"].setText(self.style.icon)
        self.hover_controls["icon_edit"].setText(self.style.hover_icon)

        # Convenience shortcuts for commonly used controls
        self.font_size_spin = self.base_controls["font_size_spin"]

        # checkboxes for syncing text properties
        self.copy_hover_chk = QCheckBox("Text base = Hover")
        self.copy_hover_chk.toggled.connect(self.on_copy_hover_toggled)

        # connect base text controls to keep synced when needed
        self._connect_base_text_signals()

        # Condition configuration
        self.condition_group = QGroupBox("Condition")
        condition_layout = QVBoxLayout()
        condition_layout.setContentsMargins(5, 5, 5, 5)
        condition_layout.setSpacing(8)

        self.condition_mode_combo = QComboBox()
        self.condition_mode_combo.addItems(TriggerMode.values())
        condition_layout.addWidget(self.condition_mode_combo)

        self.condition_options_container = QWidget()
        condition_layout.addWidget(self.condition_options_container)

        self.condition_group.setLayout(condition_layout)

        self.condition_mode_combo.currentTextChanged.connect(
            self._on_condition_mode_changed
        )

        initial_mode = self.style.condition_data.get("mode", TriggerMode.ORDINARY.value)
        self.condition_mode_combo.setCurrentText(initial_mode)
        self._on_condition_mode_changed(initial_mode)
        op1_cfg = self.style.condition_data.get("operand1")
        if initial_mode in (TriggerMode.ON.value, TriggerMode.OFF.value) and op1_cfg:
            self.condition_tag_selector.set_data(op1_cfg)
        elif initial_mode == TriggerMode.RANGE.value:
            if op1_cfg:
                self.range_tag_selector.set_data(op1_cfg)
            operator = self.style.condition_data.get("operator")
            if not operator:
                if (
                    self.style.condition_data.get("lower_bound") is not None
                    or self.style.condition_data.get("upper_bound") is not None
                ):
                    operator = "between"
                else:
                    operator = "=="
            self.range_operator_combo.setCurrentText(operator)
            if operator in ["between", "outside"]:
                lower = self.style.condition_data.get("lower_bound")
                upper = self.style.condition_data.get("upper_bound")
                if lower:
                    self.range_lower_selector.set_data(lower)
                if upper:
                    self.range_upper_selector.set_data(upper)
            else:
                operand = self.style.condition_data.get("operand2")
                if operand:
                    self.range_operand_selector.set_data(operand)
        self._validate_condition_section()

        # Tab widget to switch between border and condition options
        config_tabs = QTabWidget()
        config_tabs.addTab(self.border_group, "Border")
        config_tabs.addTab(self.condition_group, "Condition")
        options_layout.addWidget(config_tabs, 0, 0, 1, 2)

        options_layout.addWidget(style_tabs, 1, 0, 1, 2)

        cb_layout = QHBoxLayout()
        cb_layout.setContentsMargins(0, 0, 0, 0)
        cb_layout.setSpacing(6)
        cb_layout.addStretch()
        cb_layout.addWidget(self.copy_hover_chk)
        cb_layout.addStretch()
        options_layout.addLayout(cb_layout, 2, 0, 1, 2)

        main_layout.addWidget(scroll_area, 2, 0, 1, 2)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box, 3, 0, 1, 2)
        self._validate_condition_section()

        self.preview_group = QGroupBox("Preview")
        preview_group_layout = QVBoxLayout()
        preview_group_layout.setContentsMargins(5, 5, 5, 5)
        preview_group_layout.setSpacing(8)
        preview_group_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_stack = QStackedWidget()
        self.preview_button = PreviewButton("Preview")
        self.preview_button.setMinimumSize(dpi_scale(200), dpi_scale(100))
        self.preview_switch = SwitchButton()
        self.preview_stack.addWidget(self.preview_button)
        self.preview_stack.addWidget(self.preview_switch)
        preview_group_layout.addWidget(self.preview_stack)
        self.preview_group.setLayout(preview_group_layout)
        self.preview_group.setFixedWidth(250)
        main_layout.addWidget(self.preview_group, 1, 1)

        # Ensure group boxes line up neatly
        self.condition_group.setMinimumHeight(self.border_group.sizeHint().height())

        for w in [
            self.border_width_spin,
            self.x1_spin,
            self.y1_spin,
            self.x2_spin,
            self.y2_spin,
        ]:
            w.valueChanged.connect(self.update_preview)
        self.component_type_combo.currentTextChanged.connect(self.update_preview)
        self.component_type_combo.currentTextChanged.connect(
            self.adjust_preview_size
        )

        self.set_initial_colors()

        # Initialize copy states after colors and preview widgets are ready
        self.on_copy_hover_toggled(False)

        # Ensure border width enablement reflects current style selection

        self.on_border_style_changed()

        self.update_controls_state()
        self.update_preview()
        self.adjust_preview_size(self.component_type_combo.currentText())

        # Use a wider default size to accommodate grouped controls and tabs
        self.resize(580, 850)

    def _create_alignment_widget(self, options, current):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        group = QButtonGroup(widget)
        for value, icon_name, tooltip in options:
            btn = QToolButton()
            btn.setCheckable(True)
            btn.setIcon(IconManager.create_icon(icon_name))
            btn.setIconSize(QSize(16, 16))
            btn.setToolTip(tooltip)
            btn.setProperty("align_value", value)
            group.addButton(btn)
            layout.addWidget(btn)
            if value == current:
                btn.setChecked(True)
        group.setExclusive(True)
        return widget, group

    def _build_state_tab(self, props, state_name):
        tab = QWidget()
        layout = QGridLayout(tab)

        text_type_combo = QComboBox()
        text_type_combo.addItems(["Comment", "Text"])
        text_type_combo.setCurrentText(props.get("text_type", "Comment"))
        layout.addWidget(QLabel("Text type:"), 0, 0)
        layout.addWidget(text_type_combo, 0, 1)

        stack = QStackedWidget()

        comment_page = QWidget()
        c_layout = QGridLayout(comment_page)
        comment_number = TagSelector(allowed_tag_types=["INT16"])
        comment_number.main_tag_selector.set_allow_arrays(False)
        comment_column = TagSelector(allowed_tag_types=["INT16"])
        comment_column.main_tag_selector.set_allow_arrays(False)
        comment_row = TagSelector(allowed_tag_types=["INT16"])
        comment_row.main_tag_selector.set_allow_arrays(False)
        comment = props.get("comment_ref", {})
        if comment:
            comment_number.set_data(comment.get("number"))
            comment_column.set_data(comment.get("column"))
            comment_row.set_data(comment.get("row"))
        c_layout.addWidget(QLabel("Comment number:"), 0, 0)
        c_layout.addWidget(comment_number, 0, 1)
        c_layout.addWidget(QLabel("Comment column no:"), 1, 0)
        c_layout.addWidget(comment_column, 1, 1)
        c_layout.addWidget(QLabel("Comment row no:"), 2, 0)
        c_layout.addWidget(comment_row, 2, 1)
        c_layout.setColumnStretch(1, 1)

        # --- Populate constant suggestions for comment selectors --------
        def _get_group_by_number(num_str: str) -> Optional[Dict[str, Any]]:
            groups = comment_data_service.get_all_groups()
            for _gid, g in groups.items():
                if g.get("number") == num_str:
                    return g
            return None

        def _update_comment_number_suggestions():
            groups = comment_data_service.get_all_groups()
            items = []
            for g in groups.values():
                number = g.get("number")
                if not number:
                    continue
                name = g.get("name", "")
                label = f"{number} - {name}" if name else str(number)
                items.append((str(number), label))
            # sort by numeric order when possible
            try:
                items.sort(key=lambda t: int(t[0]))
            except Exception:
                items.sort(key=lambda t: t[0])
            comment_number.main_tag_selector.set_constant_suggestions(items)

        def _update_column_row_suggestions():
            data = comment_number.main_tag_selector.get_data()
            # Only available when comment number is a constant
            if not data or data.get("source") != "constant":
                comment_column.main_tag_selector.clear_constant_suggestions()
                comment_row.main_tag_selector.clear_constant_suggestions()
                return
            num_str = str(data.get("value", "")).strip()
            group = _get_group_by_number(num_str)
            if not group:
                comment_column.main_tag_selector.clear_constant_suggestions()
                comment_row.main_tag_selector.clear_constant_suggestions()
                return
            # Columns
            cols = group.get("columns", ["Comment"]) or ["Comment"]
            col_items = []
            for idx, name in enumerate(cols, start=1):
                label = f"{idx} - {name}" if name else str(idx)
                col_items.append((str(idx), label))
            comment_column.main_tag_selector.set_constant_suggestions(col_items)
            # Rows
            rows = group.get("comments", []) or []
            row_items = [(str(i), str(i)) for i in range(1, len(rows) + 1)]
            comment_row.main_tag_selector.set_constant_suggestions(row_items)

        # Initial fill and live updates
        _update_comment_number_suggestions()
        _update_column_row_suggestions()
        try:
            comment_data_service.comment_group_list_changed.connect(
                _update_comment_number_suggestions
            )
            comment_data_service.comments_changed.connect(
                lambda _gid: _update_column_row_suggestions()
            )
        except Exception:
            pass
        # Also react when the number selector changes
        try:
            comment_number.inputChanged.connect(_update_column_row_suggestions)
        except Exception:
            pass

        text_page = QWidget()
        t_layout = QGridLayout(text_page)
        text_edit = QTextEdit()
        text_edit.setPlaceholderText("Enter text...")
        text_edit.setPlainText(props.get("text_value", props.get("text", "")))
        t_layout.addWidget(text_edit, 0, 0)
        t_layout.setColumnStretch(0, 1)

        stack.addWidget(comment_page)
        stack.addWidget(text_page)
        layout.addWidget(stack, 1, 0, 1, 6)

        text_type_combo.currentIndexChanged.connect(stack.setCurrentIndex)

        layout.addWidget(QLabel("Font:"), 2, 0)
        font_combo = QComboBox()
        font_combo.setEditable(True)
        font_combo.addItems(QFontDatabase.families())
        if props.get("font_family"):
            font_combo.setCurrentText(props.get("font_family"))
        layout.addWidget(font_combo, 2, 1)

        layout.addWidget(QLabel("Font Size:"), 2, 2)
        font_size_spin = QSpinBox()
        font_size_spin.setRange(1, 1000)
        font_size_spin.setValue(props.get("font_size", 10))
        layout.addWidget(font_size_spin, 2, 3)

        bold_btn = QToolButton()
        bold_btn.setCheckable(True)
        bold_btn.setChecked(props.get("bold", False))
        bold_btn.setIcon(IconManager.create_icon("mdi.format-bold"))
        bold_btn.setIconSize(QSize(16, 16))
        bold_btn.setToolTip("Bold")

        italic_btn = QToolButton()
        italic_btn.setCheckable(True)
        italic_btn.setChecked(props.get("italic", False))
        italic_btn.setIcon(IconManager.create_icon("mdi.format-italic"))
        italic_btn.setIconSize(QSize(16, 16))
        italic_btn.setToolTip("Italic")

        underline_btn = QToolButton()
        underline_btn.setCheckable(True)
        underline_btn.setChecked(props.get("underline", False))
        underline_btn.setIcon(IconManager.create_icon("mdi.format-underline"))
        underline_btn.setIconSize(QSize(16, 16))
        underline_btn.setToolTip("Underline")

        v_widget, v_group = self._create_alignment_widget(
            [
                ("top", "mdi.format-align-top", "Top"),
                ("middle", "mdi.format-align-middle", "Middle"),
                ("bottom", "mdi.format-align-bottom", "Bottom"),
            ],
            props.get("v_align", props.get("vertical_align", "middle")),
        )

        h_widget, h_group = self._create_alignment_widget(
            [
                ("left", "mdi.format-align-left", "Left"),
                ("center", "mdi.format-align-center", "Center"),
                ("right", "mdi.format-align-right", "Right"),
            ],
            props.get("h_align", props.get("horizontal_align", "center")),
        )

        # Group text style buttons for consistent alignment
        layout.addWidget(QLabel("Text Style:"), 3, 0)
        text_style_widget = QWidget()
        text_style_layout = QHBoxLayout(text_style_widget)
        text_style_layout.setContentsMargins(0, 0, 0, 0)
        text_style_layout.addWidget(bold_btn)
        text_style_layout.addWidget(italic_btn)
        text_style_layout.addWidget(underline_btn)
        text_style_layout.addStretch()
        layout.addWidget(text_style_widget, 3, 1, 1, 4)

        # Group alignment controls to reduce spacing
        layout.addWidget(QLabel("Alignment:"), 4, 0)
        alignment_widget = QWidget()
        alignment_layout = QHBoxLayout(alignment_widget)
        alignment_layout.setContentsMargins(0, 0, 0, 0)
        alignment_layout.addWidget(QLabel("X:"))
        alignment_layout.addWidget(h_widget)
        alignment_layout.addWidget(QLabel("Y:"))
        alignment_layout.addWidget(v_widget)
        alignment_layout.addStretch()
        layout.addWidget(alignment_widget, 4, 1, 1, 4)

        layout.addWidget(QLabel("Background Colour:"), 5, 0)
        bg_base_combo, bg_shade_combo = self.create_color_selection_widgets(
            lambda n, c: self.on_state_bg_color_changed(state_name, c),
            props.get("background_color", ""),
            emit_initial=False,
        )
        layout.addWidget(bg_base_combo, 5, 1)
        layout.addWidget(bg_shade_combo, 5, 2)
        layout.addWidget(QLabel("Text Colour:"), 6, 0)
        text_base_combo, text_shade_combo = self.create_color_selection_widgets(
            lambda n, c: self.on_state_text_color_changed(state_name, c),
            props.get("text_color", ""),
            emit_initial=False,
        )
        layout.addWidget(text_base_combo, 6, 1)
        layout.addWidget(text_shade_combo, 6, 2)

        layout.addWidget(QLabel("Offset To Frame:"), 7, 0)
        offset_spin = QSpinBox()
        offset_spin.setRange(-1000, 1000)
        offset_spin.setValue(props.get("offset", props.get("offset_to_frame", 0)))
        layout.addWidget(offset_spin, 7, 1)

        layout.addWidget(QLabel("Icon:"), 8, 0)
        icon_edit = QLineEdit()
        icon_btn = QToolButton()
        icon_btn.setText("...")
        # Open custom icon picker (QtAwesome or SVG from lib/icon)
        icon_btn.clicked.connect(lambda _=None, e=icon_edit: self._open_icon_picker(e))
        icon_layout = QHBoxLayout()
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.addWidget(icon_edit)
        icon_layout.addWidget(icon_btn)
        icon_widget = QWidget()
        icon_widget.setLayout(icon_layout)
        layout.addWidget(icon_widget, 8, 1, 1, 2)

        icon_edit.textChanged.connect(self.update_preview)

        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        layout.setColumnStretch(3, 1)
        layout.setColumnStretch(4, 1)

        if text_type_combo.currentText() == "Text":
            stack.setCurrentIndex(1)
        else:
            stack.setCurrentIndex(0)

        text_type_combo.currentIndexChanged.connect(self.update_preview)
        comment_number.tag_selected.connect(lambda *_: self.update_preview())
        comment_number.inputChanged.connect(self.update_preview)
        comment_column.tag_selected.connect(lambda *_: self.update_preview())
        comment_column.inputChanged.connect(self.update_preview)
        comment_row.tag_selected.connect(lambda *_: self.update_preview())
        comment_row.inputChanged.connect(self.update_preview)
        text_edit.textChanged.connect(self.update_preview)
        font_combo.currentTextChanged.connect(self.update_preview)
        font_size_spin.valueChanged.connect(self.update_preview)
        bold_btn.toggled.connect(self.update_preview)
        italic_btn.toggled.connect(self.update_preview)
        underline_btn.toggled.connect(self.update_preview)
        v_group.buttonToggled.connect(lambda *_: self.update_preview())
        h_group.buttonToggled.connect(lambda *_: self.update_preview())
        offset_spin.valueChanged.connect(self.update_preview)

        controls = {
            "text_type_combo": text_type_combo,
            "comment_number": comment_number,
            "comment_column": comment_column,
            "comment_row": comment_row,
            "text_edit": text_edit,
            "font_family_combo": font_combo,
            "font_size_spin": font_size_spin,
            "bold_btn": bold_btn,
            "italic_btn": italic_btn,
            "underline_btn": underline_btn,
            "bg_base_combo": bg_base_combo,
            "bg_shade_combo": bg_shade_combo,
            "text_base_combo": text_base_combo,
            "text_shade_combo": text_shade_combo,
            "v_align_group": v_group,
            "h_align_group": h_group,
            "offset_spin": offset_spin,
            "icon_edit": icon_edit,
            "stack": stack,
        }
        return tab, controls

    def _connect_base_text_signals(self):
        bc = self.base_controls
        bc["text_type_combo"].currentIndexChanged.connect(self.on_base_text_changed)
        bc["comment_number"].tag_selected.connect(self.on_base_text_changed)
        bc["comment_number"].inputChanged.connect(self.on_base_text_changed)
        bc["comment_column"].tag_selected.connect(self.on_base_text_changed)
        bc["comment_column"].inputChanged.connect(self.on_base_text_changed)
        bc["comment_row"].tag_selected.connect(self.on_base_text_changed)
        bc["comment_row"].inputChanged.connect(self.on_base_text_changed)
        bc["text_edit"].textChanged.connect(self.on_base_text_changed)
        bc["font_family_combo"].currentTextChanged.connect(self.on_base_text_changed)
        bc["font_size_spin"].valueChanged.connect(self.on_base_text_changed)
        bc["bold_btn"].toggled.connect(self.on_base_text_changed)
        bc["italic_btn"].toggled.connect(self.on_base_text_changed)
        bc["underline_btn"].toggled.connect(self.on_base_text_changed)
        bc["bg_base_combo"].currentIndexChanged.connect(self.on_base_text_changed)
        bc["bg_shade_combo"].currentIndexChanged.connect(self.on_base_text_changed)
        bc["text_base_combo"].currentIndexChanged.connect(self.on_base_text_changed)
        bc["text_shade_combo"].currentIndexChanged.connect(self.on_base_text_changed)
        bc["v_align_group"].buttonToggled.connect(
            lambda *_: self.on_base_text_changed()
        )
        bc["h_align_group"].buttonToggled.connect(
            lambda *_: self.on_base_text_changed()
        )
        bc["offset_spin"].valueChanged.connect(self.on_base_text_changed)
        bc["icon_edit"].textChanged.connect(self.on_base_text_changed)

    def _set_state_controls_enabled(self, controls, enabled):
        for key in self._TEXT_KEYS:
            w = controls.get(key)
            if not w:
                continue
            if key in ["v_align_group", "h_align_group"]:
                for btn in w.buttons():
                    btn.setEnabled(enabled)
            else:
                w.setEnabled(enabled)

    def _enable_color_controls(self, controls):
        for key in (
            "bg_base_combo",
            "bg_shade_combo",
            "text_base_combo",
            "text_shade_combo",
        ):
            w = controls.get(key)
            if w:
                w.setEnabled(True)

    def copy_base_to_state(self, target, copy_colors=True):
        src = self.base_controls
        for key in self._TEXT_KEYS:
            if key not in src or key not in target:
                continue
            s, t = src[key], target[key]
            if key == "text_type_combo":
                t.setCurrentText(s.currentText())
                target["stack"].setCurrentIndex(src["stack"].currentIndex())
            elif key in ["bg_base_combo", "text_base_combo"]:
                if copy_colors:
                    t.setCurrentText(s.currentText())
            elif key in ["bg_shade_combo", "text_shade_combo"]:
                if copy_colors:
                    t.setCurrentIndex(s.currentIndex())
            elif key.endswith("_combo"):
                t.setCurrentText(s.currentText())
            elif key.endswith("_spin"):
                t.setValue(s.value())
            elif key.endswith("_btn"):
                t.setChecked(s.isChecked())
            elif key.endswith("_group"):
                checked = s.checkedButton()
                if checked:
                    value = checked.property("align_value")
                    for btn in t.buttons():
                        if btn.property("align_value") == value:
                            btn.setChecked(True)
                            break
            elif key in ["comment_number", "comment_column", "comment_row"]:
                t.set_data(s.get_data())
            elif key == "text_edit":
                t.setPlainText(s.toPlainText())
        if "icon_edit" in src and "icon_edit" in target:
            target["icon_edit"].setText(src["icon_edit"].text())

    def _on_condition_mode_changed(self, mode: str):
        self.condition_options_container.setVisible(False)
        for child in self.condition_options_container.findChildren(QWidget):
            child.deleteLater()

        layout = self.condition_options_container.layout()
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                w = item.widget()
                if w:
                    w.deleteLater()
        else:
            layout = QVBoxLayout(self.condition_options_container)
            self.condition_options_container.setLayout(layout)
        layout.setContentsMargins(0, 10, 0, 0)

        for attr in [
            "condition_tag_selector",
            "range_tag_selector",
            "range_operand_selector",
            "range_lower_selector",
            "range_upper_selector",
            "range_operator_combo",
            "range_rhs_stack",
        ]:
            if hasattr(self, attr):
                getattr(self, attr).deleteLater()
                delattr(self, attr)

        if mode in (TriggerMode.ON.value, TriggerMode.OFF.value):
            self.condition_tag_selector = TagSelector()
            self.condition_tag_selector.set_allowed_tag_types(["BOOL"])
            self.condition_tag_selector.main_tag_selector.set_mode_fixed("Tag")
            self.condition_tag_selector.inputChanged.connect(
                self._validate_condition_section
            )
            layout.addWidget(self.condition_tag_selector)
        elif mode == TriggerMode.RANGE.value:
            self._build_range_condition_options(layout)

        self.condition_options_container.setVisible(True)
        self._validate_condition_section()

    def _build_range_condition_options(self, parent_layout):
        range_group = QGroupBox("Range Configuration")
        range_group.setObjectName("CardGroup")
        layout = QGridLayout(range_group)
        layout.setSpacing(10)

        allowed = ["INT16", "INT32", "REAL"]

        tag_layout = QVBoxLayout()
        self.range_tag_selector = TagSelector(allowed_tag_types=allowed)
        self.range_tag_selector.main_tag_selector.set_mode_fixed("Tag")
        tag_layout.addWidget(QLabel("Tag"))
        tag_layout.addWidget(self.range_tag_selector)
        tag_layout.addStretch(1)

        op_layout = QVBoxLayout()
        self.range_operator_combo = QComboBox()
        self.range_operator_combo.addItems(
            ["==", "!=", ">", ">=", "<", "<=", "between", "outside"]
        )
        op_layout.addWidget(QLabel("Operator"))
        op_layout.addWidget(self.range_operator_combo)
        op_layout.addStretch(1)

        self.range_rhs_stack = QStackedWidget()

        op2_page = QWidget()
        op2_layout = QVBoxLayout(op2_page)
        op2_layout.setContentsMargins(0, 0, 0, 0)
        self.range_operand_selector = TagSelector(allowed_tag_types=allowed)
        op2_layout.addWidget(QLabel("Operand"))
        op2_layout.addWidget(self.range_operand_selector)
        op2_layout.addStretch(1)
        self.range_rhs_stack.addWidget(op2_page)

        between_page = QWidget()
        between_layout = QGridLayout(between_page)
        between_layout.setContentsMargins(0, 0, 0, 0)
        self.range_lower_selector = TagSelector(allowed_tag_types=allowed)
        self.range_upper_selector = TagSelector(allowed_tag_types=allowed)
        between_layout.addWidget(QLabel("Lower Bound"), 0, 0)
        between_layout.addWidget(self.range_lower_selector, 1, 0)
        between_layout.addWidget(QLabel("Upper Bound"), 0, 1)
        between_layout.addWidget(self.range_upper_selector, 1, 1)
        between_layout.setRowStretch(2, 1)
        self.range_rhs_stack.addWidget(between_page)

        layout.addLayout(tag_layout, 0, 0)
        layout.addLayout(op_layout, 0, 1)
        layout.addWidget(
            self.range_rhs_stack, 0, 2, alignment=Qt.AlignmentFlag.AlignTop
        )
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(2, 1)

        parent_layout.addWidget(range_group)

        self.range_tag_selector.inputChanged.connect(self._validate_condition_section)
        self.range_operator_combo.currentTextChanged.connect(
            self._on_range_operator_changed
        )
        self.range_operand_selector.inputChanged.connect(
            self._validate_condition_section
        )
        self.range_lower_selector.inputChanged.connect(self._validate_condition_section)
        self.range_upper_selector.inputChanged.connect(self._validate_condition_section)

        self._on_range_operator_changed(self.range_operator_combo.currentText())

    def _on_range_operator_changed(self, operator: str):
        if hasattr(self, "range_rhs_stack"):
            self.range_rhs_stack.setCurrentIndex(
                1 if operator in ["between", "outside"] else 0
            )
        self._validate_condition_section()

    def _validate_condition_section(self, *args):
        mode = self.condition_mode_combo.currentText()
        valid = True
        if mode in (TriggerMode.ON.value, TriggerMode.OFF.value):
            valid = (
                hasattr(self, "condition_tag_selector")
                and self.condition_tag_selector.get_data() is not None
            )
        elif mode == TriggerMode.RANGE.value:
            operator = (
                self.range_operator_combo.currentText()
                if hasattr(self, "range_operator_combo")
                else ""
            )
            if operator in ["between", "outside"]:
                valid = all(
                    [
                        hasattr(self, "range_tag_selector")
                        and self.range_tag_selector.get_data() is not None,
                        hasattr(self, "range_lower_selector")
                        and self.range_lower_selector.get_data() is not None,
                        hasattr(self, "range_upper_selector")
                        and self.range_upper_selector.get_data() is not None,
                    ]
                )
            else:
                valid = all(
                    [
                        hasattr(self, "range_tag_selector")
                        and self.range_tag_selector.get_data() is not None,
                        hasattr(self, "range_operand_selector")
                        and self.range_operand_selector.get_data() is not None,
                    ]
                )
        ok_btn = None
        if hasattr(self, "button_box"):
            ok_btn = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setEnabled(valid)
        return valid

    def on_copy_hover_toggled(self, checked):
        self._set_state_controls_enabled(self.hover_controls, not checked)
        if "icon_edit" in self.hover_controls:
            self.hover_controls["icon_edit"].setEnabled(not checked)
        if checked:
            self.copy_base_to_state(self.hover_controls)
            self._enable_color_controls(self.hover_controls)
        self.update_preview()

    def on_base_text_changed(self, *args):
        if self.copy_hover_chk.isChecked():
            self.copy_base_to_state(self.hover_controls, copy_colors=False)

    def on_state_bg_color_changed(self, state, color):
        if state == "base":
            self._bg_color = color
            # Keep border colour in sync with the base background colour
            self._border_color = color.darker(150)
            txt = self.get_contrast_color(self._bg_color)
            self._text_color = txt.name()
            self.set_combo_selection(
                self.base_controls["text_base_combo"],
                self.base_controls["text_shade_combo"],
                txt,
            )
        elif state == "hover":
            self._hover_bg_color = color
            txt = self.get_contrast_color(self._hover_bg_color)
            self._hover_text_color = txt.name()
            self.set_combo_selection(
                self.hover_controls["text_base_combo"],
                self.hover_controls["text_shade_combo"],
                txt,
            )
        self.update_preview()

    def on_state_text_color_changed(self, state, color):
        name = color.name() if isinstance(color, QColor) else str(color)
        if state == "base":
            self._text_color = name
        elif state == "hover":
            self._hover_text_color = name
        self.update_preview()

    def init_colors(self):
        self.color_schemes = {
            "Blue": {
                "main": QColor("#3498db"),
                "hover": QColor("#5dade2"),
                "border": QColor("#2980b9"),
                "gradient2": QColor("#8e44ad"),
            },
            "Red": {
                "main": QColor("#e74c3c"),
                "hover": QColor("#ec7063"),
                "border": QColor("#c0392b"),
                "gradient2": QColor("#d35400"),
            },
            "Green": {
                "main": QColor("#2ecc71"),
                "hover": QColor("#58d68d"),
                "border": QColor("#27ae60"),
                "gradient2": QColor("#16a085"),
            },
            "Orange": {
                "main": QColor("#e67e22"),
                "hover": QColor("#eb984e"),
                "border": QColor("#d35400"),
                "gradient2": QColor("#f39c12"),
            },
            "Cyan": {
                "main": QColor("#1abc9c"),
                "hover": QColor("#48c9b0"),
                "border": QColor("#16a085"),
                "gradient2": QColor("#1abc9c"),
            },
            "Purple": {
                "main": QColor("#9b59b6"),
                "hover": QColor("#af7ac5"),
                "border": QColor("#8e44ad"),
                "gradient2": QColor("#3498db"),
            },
            "Pink": {
                "main": QColor("#fd79a8"),
                "hover": QColor("#fd9db4"),
                "border": QColor("#e75c90"),
                "gradient2": QColor("#9b59b6"),
            },
            "Teal": {
                "main": QColor("#008080"),
                "hover": QColor("#009688"),
                "border": QColor("#00695C"),
                "gradient2": QColor("#4DB6AC"),
            },
            "Indigo": {
                "main": QColor("#3F51B5"),
                "hover": QColor("#5C6BC0"),
                "border": QColor("#303F9F"),
                "gradient2": QColor("#7986CB"),
            },
            "Crimson": {
                "main": QColor("#DC143C"),
                "hover": QColor("#E53935"),
                "border": QColor("#C62828"),
                "gradient2": QColor("#EF5350"),
            },
            "Gray": {
                "main": QColor("#95a5a6"),
                "hover": QColor("#bdc3c7"),
                "border": QColor("#7f8c8d"),
                "gradient2": QColor("#bdc3c7"),
            },
            "Black": {
                "main": QColor("#34495e"),
                "hover": QColor("#4a6276"),
                "border": QColor("#2c3e50"),
                "gradient2": QColor("#2c3e50"),
            },
            "White": {
                "main": QColor("#ecf0f1"),
                "hover": QColor("#ffffff"),
                "border": QColor("#bdc3c7"),
                "gradient2": QColor("#bdc3c7"),
            },
        }
        self.base_colors = {
            name: scheme["main"] for name, scheme in self.color_schemes.items()
        }

    def get_shades(self, color_name):
        base_color = self.base_colors.get(color_name, QColor("#000000"))
        shades = []
        for i in range(16):
            factor = 1.2 - (i / 15.0) * 0.6
            shades.append(
                base_color.lighter(int(100 * factor))
                if factor > 1.0
                else base_color.darker(int(100 / factor))
            )

        return shades

    def get_contrast_color(self, color: QColor) -> QColor:
        r, g, b, _ = color.getRgb()
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return QColor("#000000") if luminance > 0.55 else QColor("#ffffff")

    def create_color_selection_widgets(
        self, final_slot, initial_color=None, emit_initial=True
    ):
        base_combo = QComboBox()
        for color_name, color_value in self.base_colors.items():
            pixmap = QPixmap(16, 16)
            pixmap.fill(color_value)
            base_combo.addItem(QIcon(pixmap), color_name)

        shade_combo = QComboBox()

        def update_shades(color_name, select_index=None, emit=True):
            shade_combo.blockSignals(True)
            shade_combo.clear()
            shades = self.get_shades(color_name)
            for i, shade in enumerate(shades):
                pixmap = QPixmap(16, 16)
                pixmap.fill(shade)
                shade_combo.addItem(QIcon(pixmap), f"Shade {i+1}")
                shade_combo.setItemData(i, shade)
            shade_combo.setCurrentIndex(select_index if select_index is not None else 7)
            shade_combo.blockSignals(False)
            if emit:
                final_slot(color_name, shade_combo.currentData())

        # Configure initial selection before connecting signals to avoid
        # premature emissions that would call ``final_slot`` while widgets
        # are still being constructed.
        if initial_color:
            found_name, found_idx = None, None
            for name in self.base_colors:
                shades = self.get_shades(name)
                for i, shade in enumerate(shades):
                    if shade.name().lower() == str(initial_color).lower():
                        found_name, found_idx = name, i
                        break
                if found_name:
                    break
            if found_name:
                base_combo.setCurrentText(found_name)
                update_shades(found_name, found_idx, emit=emit_initial)
            else:
                base_combo.setCurrentIndex(0)
                update_shades(base_combo.currentText(), emit=emit_initial)
        else:
            base_combo.setCurrentIndex(0)
            update_shades(base_combo.currentText(), emit=emit_initial)

        base_combo.currentTextChanged.connect(lambda name: update_shades(name))
        shade_combo.currentIndexChanged.connect(
            lambda: final_slot(base_combo.currentText(), shade_combo.currentData())
        )

        return base_combo, shade_combo

    def set_combo_selection(self, base_combo, shade_combo, color):
        color_hex = color.name() if isinstance(color, QColor) else str(color)
        found_name, found_idx = None, 7
        for name in self.base_colors:
            shades = self.get_shades(name)
            for i, shade in enumerate(shades):
                if shade.name().lower() == color_hex.lower():
                    found_name, found_idx = name, i
                    break
            if found_name:
                break
        if not found_name:
            found_name = base_combo.currentText()
        base_combo.blockSignals(True)
        shade_combo.blockSignals(True)
        base_combo.setCurrentText(found_name)
        shade_combo.clear()
        for i, shade in enumerate(self.get_shades(found_name)):
            pixmap = QPixmap(16, 16)
            pixmap.fill(shade)
            shade_combo.addItem(QIcon(pixmap), f"Shade {i+1}")
            shade_combo.setItemData(i, shade)
        shade_combo.setCurrentIndex(found_idx)
        base_combo.blockSignals(False)
        shade_combo.blockSignals(False)
        final_color = shade_combo.currentData()
        if base_combo is self.base_controls.get("bg_base_combo"):
            self.on_state_bg_color_changed("base", final_color)
        elif base_combo is self.hover_controls.get("bg_base_combo"):
            self.on_state_bg_color_changed("hover", final_color)
        elif base_combo is self.base_controls.get("text_base_combo"):
            self.on_state_text_color_changed("base", final_color)
        elif base_combo is self.hover_controls.get("text_base_combo"):
            self.on_state_text_color_changed("hover", final_color)

    def on_bg_color_changed(self, color_name, color):
        if not color:
            return
        self._bg_color = color
        self._hover_bg_color = color.lighter(120)
        self._border_color = color.darker(150)
        self._bg_color2 = color.lighter(130)

        base_text = self.get_contrast_color(self._bg_color)
        hover_text = self.get_contrast_color(self._hover_bg_color)
        self._text_color = base_text.name()
        self._hover_text_color = hover_text.name()

        self.set_combo_selection(
            self.base_controls["bg_base_combo"],
            self.base_controls["bg_shade_combo"],
            self._bg_color,
        )
        self.set_combo_selection(
            self.hover_controls["bg_base_combo"],
            self.hover_controls["bg_shade_combo"],
            self._hover_bg_color,
        )
        self.set_combo_selection(
            self.base_controls["text_base_combo"],
            self.base_controls["text_shade_combo"],
            base_text,
        )
        self.set_combo_selection(
            self.hover_controls["text_base_combo"],
            self.hover_controls["text_shade_combo"],
            hover_text,
        )
        self.update_preview()

    def set_initial_colors(self):
        self.bg_base_color_combo.blockSignals(True)
        self.bg_base_color_combo.setCurrentText("Green")
        self.bg_base_color_combo.blockSignals(False)
        scheme = self.color_schemes.get("Green")
        self._bg_color = scheme["main"] if scheme else QColor("#2ecc71")

        orig_base_text = self._text_color
        orig_hover_text = self._hover_text_color

        self.on_bg_color_changed("Green", self._bg_color)

        if orig_base_text:
            self.set_combo_selection(
                self.base_controls["text_base_combo"],
                self.base_controls["text_shade_combo"],
                QColor(orig_base_text),
            )
        if orig_hover_text:
            self.set_combo_selection(
                self.hover_controls["text_base_combo"],
                self.hover_controls["text_shade_combo"],
                QColor(orig_hover_text),
            )

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

    def _select_icon_file(self, edit: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Icon", "", "Images (*.svg *.png *.jpg *.jpeg)"
        )
        if path:
            edit.setText(path)

    def _open_icon_picker(self, edit: QLineEdit):
        # Restrict SVG selection to lib/icon directory, and allow QtAwesome icons.
        try:
            base_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..")
            )
            icons_root = os.path.join(base_dir, "lib", "icon")
        except Exception:
            icons_root = os.path.join(os.getcwd(), "lib", "icon")
        dlg = IconPickerDialog(icons_root, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            value = dlg.selected_value()
            if value:
                edit.setText(value)

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
            self.on_corner_radius_changed("tl", self.tl_radius_spin.value())

    def _create_gradient_icon(self, coords):
        pixmap = QPixmap(40, 20)
        gradient = QLinearGradient(
            coords[0] * 40, coords[1] * 20, coords[2] * 40, coords[3] * 20
        )
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

    def on_border_style_changed(self):
        style = self.border_style_combo.currentData()
        allow_width = bool(style) and style != "none"
        self.border_width_spin.setEnabled(allow_width)
        if not allow_width:
            self.border_width_spin.setValue(0)
        self.update_preview()

    def _init_gradient_type_combo(self):
        for name, coords in _GRADIENT_STYLES.items():
            self.gradient_type_combo.addItem(self._create_gradient_icon(coords), name)
        default_type = self.style.properties.get("gradient_type")
        if default_type and default_type in _GRADIENT_STYLES:
            self.gradient_type_combo.setCurrentText(default_type)
            self._set_gradient_coords(_GRADIENT_STYLES[default_type])
        else:
            # Set from existing coordinates and detect matching type
            current = (
                self.x1_spin.value(),
                self.y1_spin.value(),
                self.x2_spin.value(),
                self.y2_spin.value(),
            )
            for name, coords in _GRADIENT_STYLES.items():
                if coords == current:
                    self.gradient_type_combo.setCurrentText(name)
                    break
            else:
                self.gradient_type_combo.setCurrentText("Top to Bottom")
                self._set_gradient_coords(_GRADIENT_STYLES["Top to Bottom"])
        self.gradient_type_combo.currentTextChanged.connect(
            self._on_gradient_type_changed
        )

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
            for spin in (
                self.tl_radius_spin,
                self.tr_radius_spin,
                self.br_radius_spin,
                self.bl_radius_spin,
            ):
                # Toggle switches always use a fixed 50px corner radius
                spin.setValue(50)
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

    def adjust_preview_size(self, component_type: str):
        if component_type == "Toggle Switch":
            widget = self.preview_switch
        else:
            widget = self.preview_button

        size = widget.size()
        if not size.isValid() or size == QSize(0, 0):
            size = widget.sizeHint()

        self.preview_stack.setFixedSize(size)
        width = self.preview_group.width() or self.preview_group.sizeHint().width()

        margins = self.preview_group.layout().contentsMargins()
        top = margins.top()
        bottom = margins.bottom()
        title_height = self.preview_group.style().pixelMetric(
            QStyle.PixelMetric.PM_TitleBarHeight
        )
        height = size.height() + top + bottom + title_height
        self.preview_group.setFixedSize(width, height)

    def update_dynamic_ranges(self):
        width = dpi_scale(200)
        height = dpi_scale(100)
        # Corner radii can be up to half of the smaller dimension.
        radius_limit = min(width, height) // 2
        # Border widths are limited to 10% of the smaller dimension, capped at 20px.
        border_limit = min(dpi_scale(20), max(1, min(width, height) // 10))
        for s in [
            self.tl_radius_spin,
            self.tr_radius_spin,
            self.br_radius_spin,
            self.bl_radius_spin,
        ]:
            s.setMaximum(radius_limit)
        self.border_width_spin.setMaximum(border_limit)

    def generate_qss(self, component_type, props=None):
        # Determine current horizontal alignment. When ``props`` is provided
        # (e.g. when building a style object), prefer its values; otherwise use
        # the live state from the alignment controls so preview updates
        # immediately when the user toggles alignment buttons.
        if props is None:
            h_btn = self.base_controls["h_align_group"].checkedButton()
            h_align = h_btn.property("align_value") if h_btn else "center"
        else:
            h_align = props.get("h_align", props.get("horizontal_align", "center"))

        shape_style = self.shape_style_combo.currentText()
        bg_type = self.bg_type_combo.currentText()
        width = dpi_scale(200)
        height = dpi_scale(100)
        padding = min(width, height) // 10
        tl_radius = self.tl_radius_spin.value()
        tr_radius = self.tr_radius_spin.value()
        br_radius = self.br_radius_spin.value()
        bl_radius = self.bl_radius_spin.value()
        border_width = self.border_width_spin.value()
        border_style = self.border_style_combo.currentData()
        bg_color = self._bg_color
        hover_bg_color = self._hover_bg_color
        border_color = self._border_color
        text_color = (
            self._text_color
            or self.palette().color(QPalette.ColorRole.ButtonText).name()
        )
        hover_text_color = self._hover_text_color or text_color
        font_size = self.font_size_spin.value()
        font_family = self.base_controls["font_family_combo"].currentText()
        font_weight = "bold" if self.base_controls["bold_btn"].isChecked() else "normal"
        font_style = (
            "italic" if self.base_controls["italic_btn"].isChecked() else "normal"
        )
        text_decoration = (
            "underline" if self.base_controls["underline_btn"].isChecked() else "none"
        )

        if component_type == "Circle Button":
            size = max(width, height)
            radius = size // 2
            tl_radius = tr_radius = br_radius = bl_radius = radius
            self.preview_button.setFixedSize(size, size)
        elif component_type == "Toggle Switch":
            # Toggle switches always use a fixed 50px corner radius
            tl_radius = tr_radius = br_radius = bl_radius = 50
            self.preview_switch.setFixedSize(width, height)
        else:
            self.preview_button.setFixedSize(width, height)

        main_qss, hover_qss = [], []
        text_align = {
            "left": "left",
            "center": "center",
            "right": "right"
        }.get(h_align, "center")

        main_qss.extend(
            [
                f"padding: {padding}px;",
                f"border-top-left-radius: {tl_radius}px;",
                f"border-top-right-radius: {tr_radius}px;",
                f"border-bottom-right-radius: {br_radius}px;",
                f"border-bottom-left-radius: {bl_radius}px;",
                f"color: {text_color};",
                f"font-size: {font_size}pt;",
                f"font-family: '{font_family}';",
                f"font-weight: {font_weight};",
                f"font-style: {font_style};",
                f"text-decoration: {text_decoration};",
                f"text-align: {text_align};",
            ]
        )

        if shape_style == "Glass":
            light_color, dark_color = bg_color.lighter(150).name(), bg_color.name()
            border_c = self._border_color.name()
            main_qss.append(
                f"background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {light_color}, stop:1 {dark_color});"
            )
            main_qss.append(f"border: 1px solid {border_c};")
            hover_qss.extend(
                [
                    f"background-color: {hover_bg_color.name()};",
                    f"color: {hover_text_color};",
                ]
            )
        elif shape_style == "3D":
            main_qss.extend(
                [
                    f"border-width: {border_width}px;",
                    f"border-color: {border_color.name()};",
                    "border-style: outset;",
                ]
            )
            if bg_type == "Solid":
                main_qss.append(f"background-color: {bg_color.name()};")
            else:
                x1, y1, x2, y2 = (
                    self.x1_spin.value(),
                    self.y1_spin.value(),
                    self.x2_spin.value(),
                    self.y2_spin.value(),
                )
                main_qss.append(
                    f"background-color: qlineargradient(x1:{x1}, y1:{y1}, x2:{x2}, y2:{y2}, stop:0 {bg_color.name()}, stop:1 {self._bg_color2.name()});"
                )
            hover_qss.extend(
                [
                    f"background-color: {hover_bg_color.name()};",
                    f"color: {hover_text_color};",
                ]
            )
        elif shape_style == "Outline":
            main_qss.extend(
                [
                    "background-color: transparent;",
                    f"border: {border_width}px solid {bg_color.name()};",
                    f"color: {text_color};",
                ]
            )
            hover_qss.extend(
                [
                    f"background-color: {hover_bg_color.name()};",
                    f"color: {hover_text_color};",
                ]
            )
        else:
            main_qss.extend(
                [
                    f"border-width: {border_width}px;",
                    f"border-style: {border_style};",
                    f"border-color: {border_color.name()};",
                ]
            )
            if bg_type == "Solid":
                main_qss.append(f"background-color: {bg_color.name()};")
            else:
                x1, y1, x2, y2 = (
                    self.x1_spin.value(),
                    self.y1_spin.value(),
                    self.x2_spin.value(),
                    self.y2_spin.value(),
                )
                main_qss.append(
                    f"background-color: qlineargradient(x1:{x1}, y1:{y1}, x2:{x2}, y2:{y2}, stop:0 {bg_color.name()}, stop:1 {self._bg_color2.name()});"
                )
            hover_qss.extend(
                [
                    f"background-color: {hover_bg_color.name()};",
                    f"color: {hover_text_color};",
                ]
            )

        main_qss_str = "\n    ".join(main_qss)
        hover_qss_str = "\n    ".join(hover_qss) if hover_qss else ""
        final_qss = f"QPushButton {{\n    {main_qss_str}\n}}\n"
        if hover_qss_str:
            final_qss += f"QPushButton:hover {{\n    {hover_qss_str}\n}}\n"
        return final_qss

    def update_preview(self):
        component_type = self.component_type_combo.currentText()
        qss = self.generate_qss(component_type)
        preview_map = {
            "Toggle Switch": self.preview_switch,
            "Circle Button": self.preview_button,
            "Standard Button": self.preview_button,
        }
        widget = preview_map.get(component_type, self.preview_button)
        widget.setStyleSheet(qss)

        # Set text alignment on the preview widget based on controls
        h_align = self.base_controls["h_align_group"].checkedButton()
        v_align = self.base_controls["v_align_group"].checkedButton()
        if h_align and v_align:
            h_val = h_align.property("align_value")
            v_val = v_align.property("align_value")
            alignment = Qt.AlignmentFlag.AlignAbsolute
            if h_val == "left":
                alignment |= Qt.AlignmentFlag.AlignLeft
            elif h_val == "center":
                alignment |= Qt.AlignmentFlag.AlignHCenter
            elif h_val == "right":
                alignment |= Qt.AlignmentFlag.AlignRight
            if v_val == "top":
                alignment |= Qt.AlignmentFlag.AlignTop
            elif v_val == "middle":
                alignment |= Qt.AlignmentFlag.AlignVCenter
            elif v_val == "bottom":
                alignment |= Qt.AlignmentFlag.AlignBottom
            # Only set alignment if widget supports it (e.g., SwitchButton)
            if hasattr(widget, "setAlignment"):
                widget.setAlignment(alignment)

        if component_type != "Toggle Switch":
            self.preview_button.set_icon(self.base_controls["icon_edit"].text())
            self.preview_button.set_hover_icon(self.hover_controls["icon_edit"].text())
            icon_sz = self.style.properties.get("icon_size", 48)
            self.preview_button.set_icon_size(icon_sz)
            text = ""
            if self.base_controls["text_type_combo"].currentText() == "Text":
                text = self.base_controls["text_edit"].toPlainText()
            elif self.base_controls["text_type_combo"].currentText() == "Comment":
                # Try to resolve constant comment reference for preview
                try:
                    num_data = self.base_controls["comment_number"].get_data()
                    col_data = self.base_controls["comment_column"].get_data()
                    row_data = self.base_controls["comment_row"].get_data()
                    if (
                        num_data
                        and col_data
                        and row_data
                        and num_data.get("main_tag", {}).get("source") == "constant"
                        and col_data.get("main_tag", {}).get("source") == "constant"
                        and row_data.get("main_tag", {}).get("source") == "constant"
                    ):
                        number = str(num_data["main_tag"].get("value", "")).strip()
                        col = int(float(col_data["main_tag"].get("value", 0)))
                        row = int(float(row_data["main_tag"].get("value", 0)))
                        groups = comment_data_service.get_all_groups()
                        group = None
                        for g in groups.values():
                            if g.get("number") == number:
                                group = g
                                break
                        if group and row > 0 and col > 0:
                            comments = group.get("comments", [])
                            columns = group.get("columns", ["Comment"]) or ["Comment"]
                            if row - 1 < len(comments):
                                row_vals = comments[row - 1]
                                if col - 1 < len(row_vals):
                                    text = str(row_vals[col - 1])
                except Exception:
                    pass
            self.preview_button.setText(text or "Preview")

    def get_style(self) -> ConditionalStyle:
        if self.copy_hover_chk.isChecked():
            self.copy_base_to_state(self.hover_controls, copy_colors=False)

        properties = {
            "component_type": self.component_type_combo.currentText(),
            "shape_style": self.shape_style_combo.currentText(),
            "background_type": self.bg_type_combo.currentText(),
            "background_color": self._bg_color.name(),
            "background_color2": self._bg_color2.name(),
            "gradient_type": self.gradient_type_combo.currentText(),
            "gradient_x1": self.x1_spin.value(),
            "gradient_y1": self.y1_spin.value(),
            "gradient_x2": self.x2_spin.value(),
            "gradient_y2": self.y2_spin.value(),
            "text_color": self._text_color,
            "font_size": self.base_controls["font_size_spin"].value(),
            "font_family": self.base_controls["font_family_combo"].currentText(),
            "bold": self.base_controls["bold_btn"].isChecked(),
            "italic": self.base_controls["italic_btn"].isChecked(),
            "underline": self.base_controls["underline_btn"].isChecked(),
            "vertical_align": (
                self.base_controls["v_align_group"]
                .checkedButton()
                .property("align_value")
                if self.base_controls["v_align_group"].checkedButton()
                else "middle"
            ),
            "horizontal_align": (
                self.base_controls["h_align_group"]
                .checkedButton()
                .property("align_value")
                if self.base_controls["h_align_group"].checkedButton()
                else "center"
            ),
            "offset_to_frame": self.base_controls["offset_spin"].value(),
            "border_radius_tl": self.tl_radius_spin.value(),
            "border_radius_tr": self.tr_radius_spin.value(),
            "border_radius_br": self.br_radius_spin.value(),
            "border_radius_bl": self.bl_radius_spin.value(),
            "border_width": self.border_width_spin.value(),
            "border_style": self.border_style_combo.currentData(),
            "border_color": self._border_color.name(),
            "text_type": self.base_controls["text_type_combo"].currentText(),
        }
        if properties["text_type"] == "Comment":
            properties["comment_number"] = self.base_controls[
                "comment_number"
            ].get_data()
            properties["comment_column"] = self.base_controls[
                "comment_column"
            ].get_data()
            properties["comment_row"] = self.base_controls["comment_row"].get_data()
        else:
            properties["text"] = self.base_controls["text_edit"].toPlainText()

        # mirror new-style keys alongside legacy ones
        properties["h_align"] = properties.get("horizontal_align", "center")
        properties["v_align"] = properties.get("vertical_align", "middle")
        properties["offset"] = properties.get("offset_to_frame", 0)
        if properties["text_type"] == "Comment":
            properties["comment_ref"] = {
                "number": properties.get("comment_number", 0),
                "column": properties.get("comment_column", 0),
                "row": properties.get("comment_row", 0),
            }
        else:
            properties["text_value"] = properties.get("text", "")

        hover_properties = {
            "background_color": self._hover_bg_color.name(),
            "text_color": self._hover_text_color,
            "font_size": self.hover_controls["font_size_spin"].value(),
            "font_family": self.hover_controls["font_family_combo"].currentText(),
            "bold": self.hover_controls["bold_btn"].isChecked(),
            "italic": self.hover_controls["italic_btn"].isChecked(),
            "underline": self.hover_controls["underline_btn"].isChecked(),
            "v_align": (
                self.hover_controls["v_align_group"]
                .checkedButton()
                .property("align_value")
                if self.hover_controls["v_align_group"].checkedButton()
                else "middle"
            ),
            "h_align": (
                self.hover_controls["h_align_group"]
                .checkedButton()
                .property("align_value")
                if self.hover_controls["h_align_group"].checkedButton()
                else "center"
            ),
            "offset": self.hover_controls["offset_spin"].value(),
            "text_type": self.hover_controls["text_type_combo"].currentText(),
        }
        if hover_properties["text_type"] == "Comment":
            hover_properties["comment_ref"] = {
                "number": self.hover_controls["comment_number"].get_data(),
                "column": self.hover_controls["comment_column"].get_data(),
                "row": self.hover_controls["comment_row"].get_data(),
            }
        else:
            hover_properties["text_value"] = self.hover_controls[
                "text_edit"
            ].toPlainText()

        condition_cfg = {"mode": self.condition_mode_combo.currentText()}
        if condition_cfg["mode"] in (TriggerMode.ON.value, TriggerMode.OFF.value):
            data = (
                self.condition_tag_selector.get_data()
                if hasattr(self, "condition_tag_selector")
                else None
            )
            condition_cfg["operand1"] = data if data else None
        elif condition_cfg["mode"] == TriggerMode.RANGE.value:
            data = (
                self.range_tag_selector.get_data()
                if hasattr(self, "range_tag_selector")
                else None
            )
            condition_cfg["operand1"] = data if data else None
            operator = (
                self.range_operator_combo.currentText()
                if hasattr(self, "range_operator_combo")
                else "=="
            )
            condition_cfg["operator"] = operator
            if operator in ["between", "outside"]:
                condition_cfg["lower_bound"] = (
                    self.range_lower_selector.get_data()
                    if hasattr(self, "range_lower_selector")
                    else None
                )
                condition_cfg["upper_bound"] = (
                    self.range_upper_selector.get_data()
                    if hasattr(self, "range_upper_selector")
                    else None
                )
            else:
                condition_cfg["operand2"] = (
                    self.range_operand_selector.get_data()
                    if hasattr(self, "range_operand_selector")
                    else None
                )

        component_type = properties.get("component_type")
        style = ConditionalStyle(
            style_id=self.style.style_id,
            tooltip=self.tooltip_edit.text(),
            icon=self.base_controls["icon_edit"].text(),
            hover_icon=self.hover_controls["icon_edit"].text(),
            text_type=properties.get("text_type", "Text"),
            text_value=properties.get("text_value", properties.get("text", "")),
            comment_ref=properties.get(
                "comment_ref",
                (
                    {
                        "number": properties.get("comment_number", 0),
                        "column": properties.get("comment_column", 0),
                        "row": properties.get("comment_row", 0),
                    }
                    if properties.get("text_type") == "Comment"
                    else {}
                ),
            ),
            font_family=properties.get("font_family", ""),
            font_size=properties.get("font_size", 0),
            bold=properties.get("bold", False),
            italic=properties.get("italic", False),
            underline=properties.get("underline", False),
            background_color=properties.get("background_color", ""),
            text_color=properties.get("text_color", ""),
            h_align=properties.get(
                "h_align", properties.get("horizontal_align", "center")
            ),
            v_align=properties.get(
                "v_align", properties.get("vertical_align", "middle")
            ),
            offset=properties.get("offset", properties.get("offset_to_frame", 0)),
            properties=properties,
            hover_properties=hover_properties,
            condition_data=condition_cfg,
        )
        # Generate the style sheet using the freshly collected properties so
        # that saved styles reflect the current alignment and other settings.
        style.style_sheet = self.generate_qss(component_type, properties)
        return style

    # ------------------------------------------------------------------
    # Error surfacing from condition evaluation
    # ------------------------------------------------------------------
    def handle_condition_error(self, message: str):
        """Show a brief tooltip and a warning dialog for condition errors."""
        try:
            QToolTip.showText(self.mapToGlobal(QPoint(12, 12)), message, self)
        except Exception:
            pass
        try:
            QMessageBox.warning(self, "Condition Error", message)
        except Exception:
            # In headless contexts or during tests, QMessageBox may fail.
            logger.warning("Condition Error: %s", message)
