# components/screen/graphics_items.py
# MODIFIED: All mouse event logic has been removed and moved to the DesignCanvas.

from typing import Optional
from PyQt6.QtWidgets import QGraphicsObject, QGraphicsItem
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QFont,
    QFontMetrics,
    QPixmap,
    QIcon,
    QPainterPath,
    QPolygonF,
    QLinearGradient,
)
from PyQt6.QtCore import QRectF, Qt, QPointF, QLineF
from PyQt6.QtSvg import QSvgRenderer
import os
import math
import copy
import logging

from services.screen_data_service import screen_service
from utils.icon_manager import IconManager


def _pct_of(value, base):
    """Return ``value`` percent of ``base``.

    Only ``TypeError`` and ``ValueError`` are handled; other exceptions will
    propagate to the caller. If an error occurs the exception is logged and
    re-raised so that callers can decide how to recover.
    """
    try:
        return float(value) * base / 100.0
    except (TypeError, ValueError) as exc:
        logging.getLogger(__name__).warning(
            "Failed to compute percentage: value=%r base=%r", value, base, exc_info=exc
        )
        raise


def _apply_pen_style_from_name(pen: QPen, style_name: str):
    """Apply a named pen style to a QPen.

    Supports extended dash patterns approximating styles from the manual.
    """
    if not style_name:
        return
    name = str(style_name).lower()
    if name in ("solid",):
        pen.setStyle(Qt.PenStyle.SolidLine)
        return
    if name in ("dash", "dashed", "dashline"):
        pen.setStyle(Qt.PenStyle.DashLine)
        return
    if name in ("dot", "dotted", "dotline"):
        pen.setStyle(Qt.PenStyle.DotLine)
        return

    # Custom patterns
    patterns = {
        # Fine broken line: short dashes
        "fine_broken": [4, 4],
        # Coarse broken line: longer dashes
        "coarse_broken": [10, 6],
        # Speck chain line: dash-dot pattern
        "speck_chain": [12, 3, 3, 3],
        # Two-dot long and two short dashes line
        "two_dot_long_two_short": [14, 4, 2, 4, 2, 6],
    }
    pattern = patterns.get(name)
    if pattern:
        pen.setStyle(Qt.PenStyle.CustomDashLine)
        pen.setDashPattern(pattern)
    else:
        # Fallback
        pen.setStyle(Qt.PenStyle.SolidLine)

class BaseGraphicsItem(QGraphicsObject):
    """
    A base class for all custom graphics items on the canvas. It is now a simple
    visual representation, with all interaction logic handled by the DesignCanvas.
    """
    def __init__(self, instance_data, parent=None):
        super().__init__(parent)
        self.instance_data = instance_data
        self.is_resizable = False

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setAcceptHoverEvents(True)

    def get_instance_id(self):
        return self.instance_data.get('instance_id')

    def update_data(self, new_instance_data):
        self.prepareGeometryChange()
        self.instance_data = new_instance_data
        self.update()

class EmbeddedScreenItem(BaseGraphicsItem):
    def __init__(self, instance_data, parent=None):
        super().__init__(instance_data, parent)
        self.is_resizable = True
        self.setAcceptHoverEvents(True)
        self._hovered = False
        # Cache complex embedded rendering when static
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)

    def boundingRect(self) -> QRectF:
        # Use instance size if provided, otherwise use base screen size
        instance_size = self.instance_data.get('size', {})
        if instance_size:
            w = instance_size.get('width', 200)
            h = instance_size.get('height', 150)
        else:
            base_screen_data = screen_service.get_screen(self.instance_data.get('screen_id'))
            if not base_screen_data:
                return QRectF(0, 0, 200, 150)
                
            size = base_screen_data.get('size', {})
            w = size.get('width', 200)
            h = size.get('height', 150)
        
        return QRectF(0, 0, w, h)

    def paint(self, painter: QPainter, option, widget=None):
        base_screen_data = screen_service.get_screen(self.instance_data.get('screen_id'))
        
        if not base_screen_data:
            painter.save()
            painter.setPen(QPen(Qt.GlobalColor.red, 2))
            painter.setBrush(Qt.GlobalColor.lightGray)
            painter.drawRect(self.boundingRect())
            painter.drawText(self.boundingRect(), Qt.AlignmentFlag.AlignCenter, "Invalid Screen ID")
            painter.restore()
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        base_style = copy.deepcopy(base_screen_data.get('style', {}))
        instance_style = self.instance_data.get('style', {})
        final_style = {**base_style, **instance_style}

        # Background
        bg_color = QColor(final_style.get('color1', '#555b66'))
        bg_color.setAlphaF(final_style.get('opacity', 1.0))
        painter.setBrush(bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.boundingRect())
        
        painter.restore()

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()
        super().hoverLeaveEvent(event)

class ButtonItem(BaseGraphicsItem):
    def __init__(self, instance_data, parent=None):
        super().__init__(instance_data, parent)
        self.is_resizable = True
        self._conditional_style_manager = None
        # Design-time only: do not bind to live tag updates in the designer
        # Runtime tag-driven behavior lives in runtime_simulator widgets
        self._current_tag_values = {}
        self._state = 'normal'
        self._tooltip = ''
        # Initialize tooltip based on current style (with empty tag values)
        self._get_active_style_properties(self._state)
        # Base size used for percentage-based properties
        self._base_width = 100
        self._base_height = 40

    def boundingRect(self) -> QRectF:
        props = self.instance_data.get('properties', {})
        size = props.get('size', {})
        w = size.get('width', 100)
        h = size.get('height', 40)
        self._base_width = w
        self._base_height = h
        return QRectF(0, 0, w, h)

    def update_data(self, new_instance_data):
        super().update_data(new_instance_data)
        # Reset conditional style manager when data changes
        self._conditional_style_manager = None

    def _get_conditional_style_manager(self):
        """Lazy load conditional style manager"""
        if self._conditional_style_manager is None:
            from tools.button.conditional_style import ConditionalStyleManager, ConditionalStyle
            self._conditional_style_manager = ConditionalStyleManager()
            
            # Load conditional styles from properties
            conditional_styles = self.instance_data.get('properties', {}).get('conditional_styles', [])
            if conditional_styles:
                self._conditional_style_manager.conditional_styles = [
                    ConditionalStyle.from_dict(style_data)
                    for style_data in conditional_styles
                ]
            
            # Set default style
            props = self.instance_data.get('properties', {})
            # Align default style keys with Conditional Style window (StyleProperties)
            default_style = {
                # Core component styling
                'component_type': props.get('component_type', 'Standard Button'),
                'shape_style': props.get('shape_style', 'Flat'),
                'background_type': props.get('background_type', 'Solid'),
                'background_color': props.get('background_color', '#5a6270'),
                # Extras supported by the editor (stored via StyleProperties.extra)
                'background_color2': props.get('background_color2', '#5a6270'),
                'gradient_x1': props.get('gradient_x1', 0),
                'gradient_y1': props.get('gradient_y1', 0),
                'gradient_x2': props.get('gradient_x2', 0),
                'gradient_y2': props.get('gradient_y2', 1),
                # Text
                'text_type': props.get('text_type', 'Text'),
                'text_value': props.get('text_value', props.get('label', 'Button')),
                'text_color': props.get('text_color', '#ffffff'),
                'font_family': props.get('font_family', ''),
                'font_size': props.get('font_size', 18),
                'bold': props.get('bold', False),
                'italic': props.get('italic', False),
                'underline': props.get('underline', False),
                'h_align': props.get('h_align', props.get('horizontal_align', 'center')),
                'v_align': props.get('v_align', props.get('vertical_align', 'middle')),
                'offset': props.get('offset', props.get('offset_to_frame', 0)),
                'comment_ref': props.get('comment_ref', {}),
                # Border
                'border_radius': props.get('border_radius', 5),
                'border_radius_tl': props.get('border_radius_tl') or props.get('border_radius', 5),
                'border_radius_tr': props.get('border_radius_tr') or props.get('border_radius', 5),
                'border_radius_br': props.get('border_radius_br') or props.get('border_radius', 5),
                'border_radius_bl': props.get('border_radius_bl') or props.get('border_radius', 5),
                'border_width': props.get('border_width', 0),
                'border_style': props.get('border_style', 'solid'),
                'border_color': props.get('border_color', '#000000'),
                # Icon
                'icon': props.get('icon', ''),
                'icon_size': props.get('icon_size', 50),
                'icon_align': props.get('icon_align', 'center'),
                'icon_color': props.get('icon_color', ''),
            }
            self._conditional_style_manager.default_style = default_style
        
        return self._conditional_style_manager

    def _get_current_tag_values(self):
        """Get current tag values for conditional style evaluation"""
        return self._current_tag_values

    def _get_active_style_properties(self, state: str = 'normal'):
        """Get the active style properties based on conditional styles.

        Parameters
        ----------
        state: str
            One of ``'normal'`` or ``'hover'``.
        """
        manager = self._get_conditional_style_manager()
        tag_values = self._get_current_tag_values()

        default_props = dict(self.instance_data.get('properties', {}))
        hover_default = default_props.pop('hover_properties', {})

        if state == 'hover':
            default_props.update(hover_default)

        active_props = manager.get_active_style(tag_values, state if state == 'hover' else None)

        # Map text_value to label for compatibility with paint method
        if 'text_value' in active_props:
            active_props['label'] = active_props['text_value']

        final_props = {**default_props, **active_props}

        tooltip = final_props.get('tooltip', '')
        if tooltip != self._tooltip:
            self._tooltip = tooltip
            self.setToolTip(tooltip)

        return final_props

    def paint(self, painter: QPainter, option, widget=None):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get active style properties
        props = self._get_active_style_properties(self._state)
        rect = self.boundingRect()
        w = rect.width()
        h = rect.height()
        min_dim = min(w, h)

        component_type = props.get('component_type', 'Standard Button')
        shape_style = props.get('shape_style', 'Flat')
        background_type = props.get('background_type', 'Solid')

        # Apply style properties converting percentages to absolute values
        bg_color = QColor(props.get('background_color') or '#5a6270')
        text_color = QColor(props.get('text_color') or '#ffffff')
        # Prefer Conditional Style "text_value"; fallback to legacy "label"
        label = props.get('text_value', props.get('label', 'Button'))
        try:
            border_radius = _pct_of(props.get('border_radius', 0), min_dim)
        except (TypeError, ValueError):
            border_radius = 0.0
        try:
            border_width = _pct_of(props.get('border_width', 0), min_dim)
        except (TypeError, ValueError):
            border_width = 0.0
        border_color = QColor(props.get('border_color') or '#000000')
        try:
            font_size = _pct_of(props.get('font_size', 0), h)
        except (TypeError, ValueError):
            font_size = 0.0
        # Text formatting from Conditional Style
        font_family = props.get('font_family', 'Arial') or 'Arial'
        font_bold = bool(props.get('bold', False))
        font_italic = bool(props.get('italic', False))
        font_underline = bool(props.get('underline', False))

        try:
            br_tl = _pct_of(props.get('border_radius_tl') or props.get('border_radius', 0), min_dim)
        except (TypeError, ValueError):
            br_tl = 0.0
        try:
            br_tr = _pct_of(props.get('border_radius_tr') or props.get('border_radius', 0), min_dim)
        except (TypeError, ValueError):
            br_tr = 0.0
        try:
            br_br = _pct_of(props.get('border_radius_br') or props.get('border_radius', 0), min_dim)
        except (TypeError, ValueError):
            br_br = 0.0
        try:
            br_bl = _pct_of(props.get('border_radius_bl') or props.get('border_radius', 0), min_dim)
        except (TypeError, ValueError):
            br_bl = 0.0
        custom_radii = any(
            props.get(k, 0) for k in ('border_radius_tl','border_radius_tr','border_radius_br','border_radius_bl')
        )

        # Component type adjustments
        if component_type == 'Circle Button':
            size = min_dim
            rect = QRectF((w - size) / 2, (h - size) / 2, size, size)
            w = h = min_dim = size
            border_radius = size / 2
            br_tl = br_tr = br_br = br_bl = border_radius
            custom_radii = False
        elif component_type == 'Toggle Switch':
            border_radius = h / 2
            br_tl = br_tr = br_br = br_bl = border_radius
            custom_radii = False
        # Removed special handling for 'Selector Switch (12)' and 'Tab Button'
        # so they are treated like standard buttons if encountered.

        # Secondary background colour (for gradients)
        bg_color2 = QColor(props.get('background_color2', bg_color.name()))

        # Transparency handling (0-100 => 0-255 alpha)
        try:
            alpha_pct = int(props.get('background_opacity', 100) or 100)
        except Exception:
            alpha_pct = 100
        alpha_pct = max(0, min(100, alpha_pct))
        _alpha255 = int(round(alpha_pct * 255 / 100))

        # Determine brush
        brush = None
        if shape_style == 'Outline':
            brush = Qt.BrushStyle.NoBrush
        elif background_type != 'Solid':
            x1 = float(props.get('gradient_x1', 0)) * w
            y1 = float(props.get('gradient_y1', 0)) * h
            x2 = float(props.get('gradient_x2', 0)) * w
            y2 = float(props.get('gradient_y2', 1)) * h
            grad = QLinearGradient(x1, y1, x2, y2)
            c1 = QColor(bg_color)
            c2 = QColor(bg_color2)
            c1.setAlpha(_alpha255)
            c2.setAlpha(_alpha255)
            grad.setColorAt(0, c1)
            grad.setColorAt(1, c2)
            brush = grad
        elif shape_style == 'Glass':
            light = QColor(bg_color).lighter(150)
            base = QColor(bg_color)
            light.setAlpha(_alpha255)
            base.setAlpha(_alpha255)
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0, light)
            grad.setColorAt(1, base)
            brush = grad
        else:
            base = QColor(bg_color)
            base.setAlpha(_alpha255)
            brush = base

        # Pen/brush setup
        if shape_style == 'Outline':
            painter.setPen(QPen(bg_color, max(1, border_width)))
            painter.setBrush(Qt.BrushStyle.NoBrush)
        else:
            if border_width > 0:
                pen = QPen(border_color, border_width)
                _apply_pen_style_from_name(pen, props.get('border_style', 'solid'))
                painter.setPen(pen)
            else:
                painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(brush)

        shape_path = None
        if custom_radii:
            shape_path = QPainterPath()
            shape_path.moveTo(br_tl, 0)
            shape_path.lineTo(w - br_tr, 0)
            shape_path.quadTo(w, 0, w, br_tr)
            shape_path.lineTo(w, h - br_br)
            shape_path.quadTo(w, h, w - br_br, h)
            shape_path.lineTo(br_bl, h)
            shape_path.quadTo(0, h, 0, h - br_bl)
            shape_path.lineTo(0, br_tl)
            shape_path.quadTo(0, 0, br_tl, 0)
            painter.drawPath(shape_path)
        else:
            if component_type == 'Circle Button':
                painter.drawEllipse(rect)
            else:
                painter.drawRoundedRect(rect, border_radius, border_radius)

        if component_type == 'Toggle Switch':
            # Mirror preview geometry: 10% margins and 80% diameter knob
            margin = int(h * 0.1)
            knob_d = int(h * 0.8)
            # Direction: if 'on' state is on the left, the initial (off) is right
            toggle_dir = str(props.get('toggle_direction', 'ltr') or 'ltr').lower()
            on_is_left = bool(props.get('toggle_on_is_left', False)) or toggle_dir in ('rtl', 'right_to_left', 'r2l')
            off_x = margin if not on_is_left else (w - margin - knob_d)
            knob_rect = QRectF(off_x, (h - knob_d) / 2, knob_d, knob_d)
            painter.setBrush(text_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(knob_rect)
        # Removed 'Selector Switch (12)' pointer rendering

        # Draw icon if available
        icon_src = props.get('icon', '')
        if icon_src:
            try:
                size = int(_pct_of(props.get('icon_size', 0), min_dim))
            except (TypeError, ValueError):
                size = 0
            color = props.get('icon_color')
            align = props.get('icon_align', 'center')
            icon: Optional[QIcon] = None
            pix = QPixmap()
            logger = logging.getLogger(__name__)
            if str(icon_src).startswith('qta:'):
                name = icon_src.split(':', 1)[1]
                icon = IconManager.create_icon(name, color=color)
                if icon.isNull():
                    logger.warning("Failed to load icon '%s'", icon_src)
            else:
                ext = os.path.splitext(icon_src)[1].lower()
                if ext == '.svg':
                    if os.path.exists(icon_src):
                        renderer = QSvgRenderer(icon_src)
                        if renderer.isValid():
                            pix = QPixmap(size, size)
                            pix.fill(Qt.GlobalColor.transparent)
                            p = QPainter(pix)
                            renderer.render(p)
                            p.end()
                            if pix.isNull():
                                logger.warning("Failed to render SVG icon '%s'", icon_src)
                        else:
                            logger.warning("Invalid SVG icon '%s'", icon_src)
                    else:
                        logger.warning("Icon file not found: %s", icon_src)
                else:
                    if os.path.exists(icon_src):
                        pix = QPixmap(icon_src)
                        if pix.isNull():
                            logger.warning("Failed to load icon '%s'", icon_src)
                        else:
                            pix = pix.scaled(
                                size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                            )
                    else:
                        logger.warning("Icon file not found: %s", icon_src)
            br = rect
            if icon is not None and not icon.isNull():
                x = br.left() + (br.width() - size) / 2
                y = br.top() + (br.height() - size) / 2
                if 'left' in align:
                    x = br.left()
                elif 'right' in align:
                    x = br.right() - size
                if 'top' in align:
                    y = br.top()
                elif 'bottom' in align:
                    y = br.bottom() - size
                target = QRectF(int(x), int(y), size, size)
                icon.paint(painter, target.toRect())
            elif not pix.isNull():
                x = br.left() + (br.width() - pix.width()) / 2
                y = br.top() + (br.height() - pix.height()) / 2
                if 'left' in align:
                    x = br.left()
                elif 'right' in align:
                    x = br.right() - pix.width()
                if 'top' in align:
                    y = br.top()
                elif 'bottom' in align:
                    y = br.bottom() - pix.height()
                painter.drawPixmap(int(x), int(y), pix)
            else:
                x = br.left() + (br.width() - size) / 2
                y = br.top() + (br.height() - size) / 2
                if 'left' in align:
                    x = br.left()
                elif 'right' in align:
                    x = br.right() - size
                if 'top' in align:
                    y = br.top()
                elif 'bottom' in align:
                    y = br.bottom() - size
                placeholder = QRectF(int(x), int(y), size, size)
                painter.setBrush(QColor("#cccccc"))
                painter.setPen(QPen(Qt.GlobalColor.darkGray, 1, Qt.PenStyle.SolidLine))
                painter.drawRect(placeholder)
                painter.drawLine(placeholder.topLeft(), placeholder.bottomRight())
                painter.drawLine(placeholder.topRight(), placeholder.bottomLeft())

        # Draw text
        painter.setPen(text_color)
        font = QFont(font_family, max(1, int(font_size)))
        font.setBold(font_bold)
        font.setItalic(font_italic)
        font.setUnderline(font_underline)
        painter.setFont(font)

        # Alignment and offset
        h_align = props.get('h_align', props.get('horizontal_align', 'center'))
        v_align = props.get('v_align', props.get('vertical_align', 'middle'))
        alignment = Qt.AlignmentFlag.AlignAbsolute
        if h_align == 'left':
            alignment |= Qt.AlignmentFlag.AlignLeft
        elif h_align == 'center':
            alignment |= Qt.AlignmentFlag.AlignHCenter
        elif h_align == 'right':
            alignment |= Qt.AlignmentFlag.AlignRight
        if v_align == 'top':
            alignment |= Qt.AlignmentFlag.AlignTop
        elif v_align == 'middle':
            alignment |= Qt.AlignmentFlag.AlignVCenter
        elif v_align == 'bottom':
            alignment |= Qt.AlignmentFlag.AlignBottom
        offset_px = int(props.get('offset', props.get('offset_to_frame', 0)) or 0)
        text_rect = self.boundingRect().adjusted(offset_px, offset_px, -offset_px, -offset_px)
        painter.drawText(text_rect, alignment, label)
        
        # Handle animations (simplified for now)
        animation = props.get('animation', {})
        if animation.get('enabled', False):
            # Basic animation support - could be enhanced with QPropertyAnimation
            anim_type = animation.get('type', 'pulse')
            intensity = animation.get('intensity', 1.0)
            
            if anim_type == 'pulse':
                # Simple pulse effect by adjusting opacity
                pulse_factor = 0.8 + 0.2 * intensity
                base_alpha = _alpha255 / 255.0
                bg_color.setAlphaF(min(1.0, base_alpha * pulse_factor))
                painter.setBrush(bg_color)
                if shape_path:
                    painter.drawPath(shape_path)
                else:
                    painter.drawRoundedRect(rect, border_radius, border_radius)
        
        painter.restore()
    
    def update_tag_values(self, tag_values):
        """Update tag-driven properties and schedule a repaint.

        Parameters
        ----------
        tag_values: dict
            Mapping of tag names to their current values.

        Notes
        -----
        This method is shared by both the designer preview and the runtime
        simulator.  When tag values change we store the new mapping, refresh
        the active style (which may alter colours, text, tooltips, etc.) and
        trigger a repaint so the visual representation stays in sync.
        """

        # Persist the latest tag values for style evaluation
        self._current_tag_values = dict(tag_values or {})

        # Recalculate any conditional style properties that depend on tags
        self._get_active_style_properties(self._state)

        # Schedule a repaint to reflect the updated style
        self.update()


class TextItem(BaseGraphicsItem):
    """Simple text drawing item."""

    def __init__(self, instance_data, parent=None):
        super().__init__(instance_data, parent)
        self.is_resizable = True

    def _get_font(self) -> QFont:
        props = self.instance_data.get("properties", {})
        font_info = props.get("font", {})
        font = QFont(font_info.get("family", "Arial"), font_info.get("size", 12))
        font.setBold(font_info.get("bold", False))
        font.setItalic(font_info.get("italic", False))
        return font

    def boundingRect(self) -> QRectF:
        props = self.instance_data.get("properties", {})
        size = props.get("size")
        if size:
            w = size.get("width", 0)
            h = size.get("height", 0)
        else:
            text = props.get("content", "")
            metrics = QFontMetrics(self._get_font())
            w = metrics.horizontalAdvance(text)
            h = metrics.height()
        return QRectF(0, 0, w, h)

    def paint(self, painter: QPainter, option, widget=None):
        props = self.instance_data.get("properties", {})
        text = props.get("content", "")
        color = QColor(props.get("color", "#000000"))
        painter.save()
        painter.setPen(color)
        painter.setFont(self._get_font())
        painter.drawText(self.boundingRect(), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
        painter.restore()


class LineItem(BaseGraphicsItem):
    """Represents a simple line between two points."""

    def __init__(self, instance_data, parent=None):
        super().__init__(instance_data, parent)
        self.is_resizable = True
        self._offset = QPointF(0, 0)

    def _points(self):
        props = self.instance_data.get("properties", {})
        s = props.get("start", {"x": 0, "y": 0})
        e = props.get("end", {"x": 100, "y": 0})
        return QPointF(s.get("x", 0), s.get("y", 0)), QPointF(e.get("x", 0), e.get("y", 0))

    def boundingRect(self) -> QRectF:
        p1, p2 = self._points()
        min_x = min(p1.x(), p2.x())
        min_y = min(p1.y(), p2.y())
        max_x = max(p1.x(), p2.x())
        max_y = max(p1.y(), p2.y())
        self._offset = QPointF(min_x, min_y)
        width = max_x - min_x
        height = max_y - min_y
        pen_w = self.instance_data.get("properties", {}).get("width", 1)
        pad = pen_w / 2 + 1
        return QRectF(0, 0, width, height).adjusted(-pad, -pad, pad, pad)

    def paint(self, painter: QPainter, option, widget=None):
        props = self.instance_data.get("properties", {})
        p1, p2 = self._points()
        p1 -= self._offset
        p2 -= self._offset
        color = QColor(props.get("color", "#000000"))
        width = props.get("width", 1)
        style = props.get("style", "solid")
        pen = QPen(color, width)
        _apply_pen_style_from_name(pen, style)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(pen)
        painter.drawLine(p1, p2)
        painter.restore()


class FreeformItem(BaseGraphicsItem):
    """Draws a path from a list of points."""

    def __init__(self, instance_data, parent=None):
        super().__init__(instance_data, parent)
        self.is_resizable = True
        self._offset = QPointF(0, 0)
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)

    def _points(self):
        props = self.instance_data.get("properties", {})
        pts = props.get("points", [])
        if not pts:
            pts = [{"x": 0, "y": 0}]
        return [QPointF(p.get("x", 0), p.get("y", 0)) for p in pts]

    def boundingRect(self) -> QRectF:
        pts = self._points()
        xs = [p.x() for p in pts]
        ys = [p.y() for p in pts]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        self._offset = QPointF(min_x, min_y)
        pen_w = self.instance_data.get("properties", {}).get("stroke_width", 1)
        pad = pen_w / 2 + 1
        return QRectF(0, 0, max_x - min_x, max_y - min_y).adjusted(-pad, -pad, pad, pad)

    def paint(self, painter: QPainter, option, widget=None):
        props = self.instance_data.get("properties", {})
        pts = [p - self._offset for p in self._points()]
        path = QPainterPath()
        if pts:
            path.moveTo(pts[0])
            for pt in pts[1:]:
                path.lineTo(pt)
        stroke_color = QColor(props.get("stroke_color", "#000000"))
        pen = QPen(stroke_color, props.get("stroke_width", 1))
        style = props.get("stroke_style", "solid")
        _apply_pen_style_from_name(pen, style)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(pen)
        fill = props.get("fill_color")
        if fill:
            painter.setBrush(QColor(fill))
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        painter.restore()


class RectItem(BaseGraphicsItem):
    """Simple rectangle item."""

    def __init__(self, instance_data, parent=None):
        super().__init__(instance_data, parent)
        self.is_resizable = True
        # Rect is simple; skip cache to avoid unnecessary memory

    def boundingRect(self) -> QRectF:
        props = self.instance_data.get("properties", {})
        size = props.get("size", {})
        w = size.get("width", 100)
        h = size.get("height", 100)
        return QRectF(0, 0, w, h)

    def paint(self, painter: QPainter, option, widget=None):
        props = self.instance_data.get("properties", {})
        size = props.get("size", {})
        w = int(size.get("width", 100))
        h = int(size.get("height", 100))
        pen = QPen(QColor(props.get("stroke_color", "#000000")), props.get("stroke_width", 1))
        style = props.get("stroke_style", "solid")
        _apply_pen_style_from_name(pen, style)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(pen)
        painter.setBrush(QColor(props.get("fill_color", "#ffffff")))
        painter.drawRect(0, 0, w, h)
        painter.restore()


class PolygonItem(BaseGraphicsItem):
    """Polygon item defined by a list of points."""

    def __init__(self, instance_data, parent=None):
        super().__init__(instance_data, parent)
        self.is_resizable = True
        self._offset = QPointF(0, 0)
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)

    def _points(self):
        props = self.instance_data.get("properties", {})
        pts = props.get("points", [])
        if not pts:
            pts = [{"x": 0, "y": 0}]
        return [QPointF(p.get("x", 0), p.get("y", 0)) for p in pts]

    def boundingRect(self) -> QRectF:
        pts = self._points()
        xs = [p.x() for p in pts]
        ys = [p.y() for p in pts]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        self._offset = QPointF(min_x, min_y)
        pen_w = self.instance_data.get("properties", {}).get("stroke_width", 1)
        pad = pen_w / 2 + 1
        return QRectF(0, 0, max_x - min_x, max_y - min_y).adjusted(-pad, -pad, pad, pad)

    def paint(self, painter: QPainter, option, widget=None):
        props = self.instance_data.get("properties", {})
        pts = [p - self._offset for p in self._points()]
        polygon = QPolygonF(pts)
        pen = QPen(QColor(props.get("stroke_color", "#000000")), props.get("stroke_width", 1))
        style = props.get("stroke_style", "solid")
        _apply_pen_style_from_name(pen, style)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(pen)
        painter.setBrush(QColor(props.get("fill_color", "#ffffff")))
        painter.drawPolygon(polygon)
        painter.restore()


class CircleItem(BaseGraphicsItem):
    """Ellipse or circle item."""

    def __init__(self, instance_data, parent=None):
        super().__init__(instance_data, parent)
        self.is_resizable = True
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)

    def boundingRect(self) -> QRectF:
        props = self.instance_data.get("properties", {})
        if "radius" in props:
            r = props.get("radius", 50)
            w = h = r * 2
        else:
            size = props.get("size", {})
            w = size.get("width", 100)
            h = size.get("height", 100)
        return QRectF(0, 0, w, h)

    def paint(self, painter: QPainter, option, widget=None):
        props = self.instance_data.get("properties", {})
        rect = self.boundingRect()
        pen = QPen(QColor(props.get("stroke_color", "#000000")), props.get("stroke_width", 1))
        style = props.get("stroke_style", "solid")
        if style == "dash":
            pen.setStyle(Qt.PenStyle.DashLine)
        elif style == "dot":
            pen.setStyle(Qt.PenStyle.DotLine)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(pen)
        painter.setBrush(QColor(props.get("fill_color", "#ffffff")))
        painter.drawEllipse(rect)
        painter.restore()


class ArcItem(BaseGraphicsItem):
    """Represents a simple arc."""

    def __init__(self, instance_data, parent=None):
        super().__init__(instance_data, parent)
        self.is_resizable = True
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)

    def boundingRect(self) -> QRectF:
        props = self.instance_data.get("properties", {})
        radius = props.get("radius")
        if radius is not None:
            w = h = radius * 2
        else:
            size = props.get("size", {})
            w = size.get("width", 100)
            h = size.get("height", 100)
        return QRectF(0, 0, w, h)

    def paint(self, painter: QPainter, option, widget=None):
        props = self.instance_data.get("properties", {})
        start = props.get("start_angle", 0)
        span = props.get("span_angle", 90)
        rect = self.boundingRect()
        pen = QPen(QColor(props.get("color", "#000000")), props.get("width", 1))
        style = props.get("style", "solid")
        _apply_pen_style_from_name(pen, style)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(rect, int(start * 16), int(span * 16))
        painter.restore()


class SectorItem(BaseGraphicsItem):
    """A filled sector (pie slice)."""

    def __init__(self, instance_data, parent=None):
        super().__init__(instance_data, parent)
        self.is_resizable = True
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)

    def boundingRect(self) -> QRectF:
        props = self.instance_data.get("properties", {})
        radius = props.get("radius")
        if radius is not None:
            w = h = radius * 2
        else:
            size = props.get("size", {})
            w = size.get("width", 100)
            h = size.get("height", 100)
        return QRectF(0, 0, w, h)

    def paint(self, painter: QPainter, option, widget=None):
        props = self.instance_data.get("properties", {})
        start = props.get("start_angle", 0)
        span = props.get("span_angle", 90)
        rect = self.boundingRect()
        path = QPainterPath()
        center = rect.center()
        path.moveTo(center)
        path.arcTo(rect, start, span)
        path.closeSubpath()
        pen = QPen(QColor(props.get("stroke_color", "#000000")), props.get("stroke_width", 1))
        style = props.get("stroke_style", "solid")
        _apply_pen_style_from_name(pen, style)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(pen)
        painter.setBrush(QColor(props.get("fill_color", "#ffffff")))
        painter.drawPath(path)
        painter.restore()


class TableItem(BaseGraphicsItem):
    """Simple table/grid representation."""

    def __init__(self, instance_data, parent=None):
        super().__init__(instance_data, parent)
        self.is_resizable = True
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)

    def boundingRect(self) -> QRectF:
        props = self.instance_data.get("properties", {})
        rows = props.get("rows", 2)
        cols = props.get("columns", 2)
        cell = props.get("cell_size", {"width": 50, "height": 20})
        w = cols * cell.get("width", 50)
        h = rows * cell.get("height", 20)
        return QRectF(0, 0, w, h)

    def paint(self, painter: QPainter, option, widget=None):
        props = self.instance_data.get("properties", {})
        rows = props.get("rows", 2)
        cols = props.get("columns", 2)
        cell = props.get("cell_size", {"width": 50, "height": 20})
        w = cols * cell.get("width", 50)
        h = rows * cell.get("height", 20)
        pen = QPen(QColor(props.get("stroke_color", "#000000")), props.get("stroke_width", 1))
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(pen)
        painter.setBrush(QColor(props.get("fill_color", "#ffffff")))
        painter.drawRect(QRectF(0, 0, w, h))
        for r in range(1, rows):
            y = r * cell.get("height", 20)
            painter.drawLine(QLineF(0, y, w, y))
        for c in range(1, cols):
            x = c * cell.get("width", 50)
            painter.drawLine(QLineF(x, 0, x, h))
        painter.restore()


class ScaleItem(BaseGraphicsItem):
    """Basic ruler-like scale with measurement labels."""

    def __init__(self, instance_data, parent=None):
        super().__init__(instance_data, parent)
        self.is_resizable = True
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)

    def boundingRect(self) -> QRectF:
        props = self.instance_data.get("properties", {})
        orient = props.get("orientation", "horizontal")
        length = props.get("length", 100)
        thickness = props.get("thickness", 20)
        major = max(1, props.get("major_ticks", 10))
        tick_spacing = props.get("tick_spacing", 1)
        units = props.get("units", "")

        font = QFont("Arial", 8)
        metrics = QFontMetrics(font)
        max_label = f"{major * tick_spacing}{units}"
        label_w = metrics.horizontalAdvance(max_label) + 4
        label_h = metrics.height() + 2

        if orient == "vertical":
            return QRectF(0, 0, thickness + label_w, length)
        return QRectF(0, 0, length, thickness + label_h)

    def paint(self, painter: QPainter, option, widget=None):
        props = self.instance_data.get("properties", {})
        orient = props.get("orientation", "horizontal")
        length = props.get("length", 100)
        thickness = props.get("thickness", 20)
        major = max(1, props.get("major_ticks", 10))
        minor = props.get("minor_ticks", 5)
        tick_spacing = props.get("tick_spacing", 1)
        units = props.get("units", "")
        color = QColor(props.get("color", "#000000"))

        pen = QPen(color, 1)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(pen)

        font = QFont("Arial", 8)
        painter.setFont(font)
        metrics = QFontMetrics(font)
        self._draw_ticks(
            painter,
            orient,
            length,
            thickness,
            major,
            minor,
            tick_spacing,
            units,
            metrics,
        )
        painter.restore()

    @staticmethod
    def _draw_axis_line(painter: QPainter, orient: str, length: float, thickness: float):
        if orient == "vertical":
            painter.drawLine(QPointF(thickness / 2, 0), QPointF(thickness / 2, length))
        else:
            painter.drawLine(QPointF(0, thickness / 2), QPointF(length, thickness / 2))

    @staticmethod
    def _draw_major_tick(painter: QPainter, orient: str, pos: float, thickness: float):
        if orient == "vertical":
            painter.drawLine(QPointF(0, pos), QPointF(thickness, pos))
        else:
            painter.drawLine(QPointF(pos, 0), QPointF(pos, thickness))

    @staticmethod
    def _draw_minor_tick(painter: QPainter, orient: str, pos: float, thickness: float):
        if orient == "vertical":
            painter.drawLine(QPointF(thickness / 4, pos), QPointF(3 * thickness / 4, pos))
        else:
            painter.drawLine(QPointF(pos, thickness / 4), QPointF(pos, 3 * thickness / 4))

    @staticmethod
    def _draw_label(
        painter: QPainter,
        orient: str,
        pos: float,
        thickness: float,
        label: str,
        metrics: QFontMetrics,
    ):
        if orient == "vertical":
            text_rect = QRectF(
                thickness,
                pos - metrics.height() / 2,
                metrics.horizontalAdvance(label) + 4,
                metrics.height(),
            )
            alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        else:
            text_rect = QRectF(
                pos - metrics.horizontalAdvance(label) / 2,
                thickness,
                metrics.horizontalAdvance(label) + 4,
                metrics.height(),
            )
            alignment = Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop
        painter.drawText(text_rect, alignment, label)

    def _draw_ticks(
        self,
        painter: QPainter,
        orient: str,
        length: float,
        thickness: float,
        major: int,
        minor: int,
        tick_spacing: float,
        units: str,
        metrics: QFontMetrics,
    ):
        self._draw_axis_line(painter, orient, length, thickness)
        for i in range(major + 1):
            pos = i * (length / major)
            self._draw_major_tick(painter, orient, pos, thickness)

            label = f"{i * tick_spacing:g}{units}"
            self._draw_label(painter, orient, pos, thickness, label, metrics)

            if minor > 1 and i < major:
                step = length / major / minor
                for j in range(1, minor):
                    pos_minor = pos + j * step
                    self._draw_minor_tick(painter, orient, pos_minor, thickness)


class ImageItem(BaseGraphicsItem):
    """Displays an image from a file path."""

    def __init__(self, instance_data, parent=None):
        super().__init__(instance_data, parent)
        self.is_resizable = True
        self._pixmap = None
        self._load_pixmap()
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)

    def _load_pixmap(self):
        props = self.instance_data.get("properties", {})
        path = props.get("path")
        self._pixmap = QPixmap()
        if path:
            if os.path.exists(path):
                pixmap = QPixmap(path)
                if pixmap.isNull():
                    logging.getLogger(__name__).warning("Failed to load image '%s'", path)
                else:
                    self._pixmap = pixmap
            else:
                logging.getLogger(__name__).warning("Image file not found: %s", path)

    def update_data(self, new_instance_data):
        super().update_data(new_instance_data)
        self._load_pixmap()

    def boundingRect(self) -> QRectF:
        props = self.instance_data.get("properties", {})
        size = props.get("size", {})
        if size:
            w = size.get("width", 100)
            h = size.get("height", 100)
        elif self._pixmap and not self._pixmap.isNull():
            w = self._pixmap.width()
            h = self._pixmap.height()
        else:
            w = h = 100
        return QRectF(0, 0, w, h)

    def paint(self, painter: QPainter, option, widget=None):
        rect = self.boundingRect()
        painter.save()
        if self._pixmap and not self._pixmap.isNull():
            painter.drawPixmap(rect, self._pixmap, QRectF(self._pixmap.rect()))
        else:
            painter.setBrush(QColor("#cccccc"))
            painter.setPen(QPen(Qt.GlobalColor.darkGray, 1, Qt.PenStyle.DashLine))
            painter.drawRect(rect)
            painter.drawLine(rect.topLeft(), rect.bottomRight())
            painter.drawLine(rect.topRight(), rect.bottomLeft())
        painter.restore()


class DxfItem(BaseGraphicsItem):
    """Placeholder item for DXF drawings."""

    def __init__(self, instance_data, parent=None):
        super().__init__(instance_data, parent)
        self.is_resizable = True
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)

    def boundingRect(self) -> QRectF:
        props = self.instance_data.get("properties", {})
        size = props.get("size", {})
        w = size.get("width", 100)
        h = size.get("height", 100)
        return QRectF(0, 0, w, h)

    def paint(self, painter: QPainter, option, widget=None):
        rect = self.boundingRect()
        painter.save()
        painter.setPen(QPen(QColor("#888888"), 1, Qt.PenStyle.DashLine))
        painter.setBrush(QColor(200, 200, 200, 50))
        painter.drawRect(rect)
        painter.setPen(QPen(Qt.GlobalColor.black))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "DXF")
        painter.restore()
