# components/screen/graphics_items.py
# MODIFIED: All mouse event logic has been removed and moved to the DesignCanvas.

from PyQt6.QtWidgets import QGraphicsObject, QGraphicsItem
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QFont,
    QFontMetrics,
    QPixmap,
    QPainterPath,
    QPolygonF,
)
from PyQt6.QtCore import QRectF, Qt, QPointF, QLineF
import copy

from services.screen_data_service import screen_service

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
        self._current_tag_values = {}

    def boundingRect(self) -> QRectF:
        props = self.instance_data.get('properties', {})
        size = props.get('size', {})
        w = size.get('width', 100)
        h = size.get('height', 40)
        return QRectF(0, 0, w, h)

    def update_data(self, new_instance_data):
        super().update_data(new_instance_data)
        # Reset conditional style manager when data changes
        self._conditional_style_manager = None

    def _get_conditional_style_manager(self):
        """Lazy load conditional style manager"""
        if self._conditional_style_manager is None:
            from components.button.conditional_style import ConditionalStyleManager, ConditionalStyle
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
            self._conditional_style_manager.default_style = {
                'background_color': props.get('background_color', '#5a6270'),
                'text_color': props.get('text_color', '#ffffff'),
                'label': props.get('label', 'Button'),
                'border_radius': props.get('border_radius', 5),
                'border_width': props.get('border_width', 0),
                'border_color': props.get('border_color', '#000000'),
                'font_size': props.get('font_size', 10),
                'font_weight': props.get('font_weight', 'normal'),
                'opacity': props.get('opacity', 1.0)
            }
        
        return self._conditional_style_manager

    def _get_current_tag_values(self):
        """Get current tag values for conditional style evaluation"""
        # This would typically come from tag data service
        # For now, return empty dict - will be populated by tag service
        return self._current_tag_values

    def _get_active_style_properties(self):
        """Get the active style properties based on conditional styles"""
        manager = self._get_conditional_style_manager()
        tag_values = self._get_current_tag_values()
        
        # Get active style properties
        active_props = manager.get_active_style(tag_values)
        
        # Merge with default properties
        default_props = self.instance_data.get('properties', {})
        final_props = {**default_props, **active_props}
        
        return final_props

    def paint(self, painter: QPainter, option, widget=None):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get active style properties
        props = self._get_active_style_properties()
        
        # Apply style properties
        bg_color = QColor(props.get('background_color', '#5a6270'))
        text_color = QColor(props.get('text_color', '#ffffff'))
        label = props.get('label', 'Button')
        border_radius = props.get('border_radius', 5)
        border_width = props.get('border_width', 0)
        border_color = QColor(props.get('border_color', '#000000'))
        font_size = props.get('font_size', 10)
        font_weight = props.get('font_weight', 'normal')
        opacity = props.get('opacity', 1.0)
        
        # Apply opacity
        bg_color.setAlphaF(opacity)
        text_color.setAlphaF(opacity)
        
        # Draw background
        if border_width > 0:
            painter.setPen(QPen(border_color, border_width))
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            
        painter.setBrush(bg_color)
        painter.drawRoundedRect(self.boundingRect(), border_radius, border_radius)
        
        # Draw text
        painter.setPen(text_color)
        font = QFont("Arial", font_size)
        if font_weight == 'bold':
            font.setBold(True)
        elif font_weight == 'light':
            font.setWeight(QFont.Weight.Light)
        painter.setFont(font)
        painter.drawText(self.boundingRect(), Qt.AlignmentFlag.AlignCenter, label)
        
        # Handle animations (simplified for now)
        animation = props.get('animation', {})
        if animation.get('enabled', False):
            # Basic animation support - could be enhanced with QPropertyAnimation
            anim_type = animation.get('type', 'pulse')
            intensity = animation.get('intensity', 1.0)
            
            if anim_type == 'pulse':
                # Simple pulse effect by adjusting opacity
                pulse_factor = 0.8 + 0.2 * intensity
                bg_color.setAlphaF(opacity * pulse_factor)
                painter.setBrush(bg_color)
                painter.drawRoundedRect(self.boundingRect(), border_radius, border_radius)
        
        painter.restore()
    
    def update_tag_values(self, tag_values):
        """Update tag values and re-evaluate conditional styles"""
        self._current_tag_values = tag_values
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
        if style == "dash":
            pen.setStyle(Qt.PenStyle.DashLine)
        elif style == "dot":
            pen.setStyle(Qt.PenStyle.DotLine)
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
        if style == "dash":
            pen.setStyle(Qt.PenStyle.DashLine)
        elif style == "dot":
            pen.setStyle(Qt.PenStyle.DotLine)
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

    def boundingRect(self) -> QRectF:
        props = self.instance_data.get("properties", {})
        size = props.get("size", {})
        w = size.get("width", 100)
        h = size.get("height", 100)
        return QRectF(0, 0, w, h)

    def paint(self, painter: QPainter, option, widget=None):
        props = self.instance_data.get("properties", {})
        size = props.get("size", {})
        w = size.get("width", 100)
        h = size.get("height", 100)
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
        painter.drawRect(0, 0, w, h)
        painter.restore()


class PolygonItem(BaseGraphicsItem):
    """Polygon item defined by a list of points."""

    def __init__(self, instance_data, parent=None):
        super().__init__(instance_data, parent)
        self.is_resizable = True
        self._offset = QPointF(0, 0)

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
        if style == "dash":
            pen.setStyle(Qt.PenStyle.DashLine)
        elif style == "dot":
            pen.setStyle(Qt.PenStyle.DotLine)
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
        if style == "dash":
            pen.setStyle(Qt.PenStyle.DashLine)
        elif style == "dot":
            pen.setStyle(Qt.PenStyle.DotLine)
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
        if style == "dash":
            pen.setStyle(Qt.PenStyle.DashLine)
        elif style == "dot":
            pen.setStyle(Qt.PenStyle.DotLine)
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

        if orient == "vertical":
            painter.drawLine(QPointF(thickness / 2, 0), QPointF(thickness / 2, length))
            for i in range(major + 1):
                y = i * (length / major)
                painter.drawLine(QPointF(0, y), QPointF(thickness, y))

                label = f"{i * tick_spacing:g}{units}"
                text_rect = QRectF(
                    thickness,
                    y - metrics.height() / 2,
                    metrics.horizontalAdvance(label) + 4,
                    metrics.height(),
                )
                painter.drawText(
                    text_rect,
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    label,
                )

                if minor > 1 and i < major:
                    step = length / major / minor
                    for j in range(1, minor):
                        yy = y + j * step
                        painter.drawLine(
                            QPointF(thickness / 4, yy),
                            QPointF(3 * thickness / 4, yy),
                        )
        else:
            painter.drawLine(QPointF(0, thickness / 2), QPointF(length, thickness / 2))
            for i in range(major + 1):
                x = i * (length / major)
                painter.drawLine(QPointF(x, 0), QPointF(x, thickness))

                label = f"{i * tick_spacing:g}{units}"
                text_rect = QRectF(
                    x - metrics.horizontalAdvance(label) / 2,
                    thickness,
                    metrics.horizontalAdvance(label) + 4,
                    metrics.height(),
                )
                painter.drawText(
                    text_rect,
                    Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop,
                    label,
                )

                if minor > 1 and i < major:
                    step = length / major / minor
                    for j in range(1, minor):
                        xx = x + j * step
                        painter.drawLine(
                            QPointF(xx, thickness / 4),
                            QPointF(xx, 3 * thickness / 4),
                        )
        painter.restore()


class ImageItem(BaseGraphicsItem):
    """Displays an image from a file path."""

    def __init__(self, instance_data, parent=None):
        super().__init__(instance_data, parent)
        self.is_resizable = True
        self._pixmap = None
        self._load_pixmap()

    def _load_pixmap(self):
        props = self.instance_data.get("properties", {})
        path = props.get("path")
        if path:
            self._pixmap = QPixmap(path)

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
