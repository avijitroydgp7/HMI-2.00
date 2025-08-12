# components/screen/graphics_items.py
# MODIFIED: All mouse event logic has been removed and moved to the DesignCanvas.

from PyQt6.QtWidgets import QGraphicsObject, QGraphicsItem
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from PyQt6.QtCore import QRectF, Qt
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
