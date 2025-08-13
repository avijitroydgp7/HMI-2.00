# components/screen/design_canvas.py
# MODIFIED: Overhauled mouse event logic to correctly handle multi-selection.

from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QMenu, QGraphicsRectItem, QGraphicsDropShadowEffect
from PyQt6.QtGui import QPainter, QColor, QMouseEvent, QKeyEvent, QDragEnterEvent, QDropEvent, QPen, QPainterPath, QCursor, QBrush
from PyQt6.QtCore import Qt, QPoint, QPointF, pyqtSignal, QRectF, QRect
import copy
import uuid

from services.screen_data_service import screen_service
from services.clipboard_service import clipboard_service
from services.command_history_service import command_history_service
from services.commands import MoveChildCommand, RemoveChildCommand, AddChildCommand, UpdateChildPropertiesCommand, BulkUpdateChildPropertiesCommand, BulkMoveChildCommand
from utils.icon_manager import IconManager
from tools import button as button_tool
from .graphics_items import ButtonItem, EmbeddedScreenItem, BaseGraphicsItem
from ..selection_overlay import SelectionOverlay
from utils import constants

class DesignCanvas(QGraphicsView):
    """
    The main design surface, implemented using Qt's Graphics View Framework
    for efficient rendering, selection, and interaction.
    """
    selection_changed = pyqtSignal(str, object)
    open_screen_requested = pyqtSignal(str)
    mouse_moved_on_scene = pyqtSignal(QPointF)
    mouse_left_scene = pyqtSignal()
    selection_dragged = pyqtSignal(dict)
    view_zoomed = pyqtSignal(str)
    
    def __init__(self, screen_id, parent=None):
        super().__init__(parent)
        self.screen_id = screen_id
        self.screen_data = None
        self.active_tool = constants.TOOL_SELECT
        self._item_map = {}
        self.selection_overlay = SelectionOverlay()

        self.current_zoom = 1.0
        self.min_zoom = 0.25
        self.max_zoom = 4.0
        self._rubber_band_origin = None
        self._rubber_band_rect = QRect()

        self._drag_mode = None 
        self._resize_handle = None
        self._start_selection_states = {}
        self._last_mouse_scene_pos = QPointF()
        self._shift_pressed = False

        self.scene = QGraphicsScene(self)
        self.scene.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.BspTreeIndex)
        self.setScene(self.scene)

        self.page_item = QGraphicsRectItem()

        # Cache a lighter drop shadow effect for better performance
        self._shadow_effect = QGraphicsDropShadowEffect()
        self._shadow_effect.setBlurRadius(10)
        self._shadow_effect.setColor(QColor(0, 0, 0, 80))
        self._shadow_effect.setOffset(0, 0)

        # Allow turning shadows off and auto-disabling at high zoom levels
        self._shadow_enabled = True
        self._shadow_disable_threshold = 1.25
        if self._shadow_enabled:
            self.page_item.setGraphicsEffect(self._shadow_effect)

        self.page_item.setZValue(-1)
        self.scene.addItem(self.page_item)

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setObjectName("DesignCanvas")
        self.setBackgroundBrush(QColor("#1f1f1f"))

        self.scene.selectionChanged.connect(self._on_selection_changed)

        self.update_screen_data()
        self._update_shadow_for_zoom()
        self.update_visible_items()

    def set_shadow_enabled(self, enabled: bool):
        """Enable or disable page shadows dynamically."""
        self._shadow_enabled = enabled
        self._update_shadow_for_zoom()

    def _update_shadow_for_zoom(self):
        """Toggle shadow based on zoom level, drag state, and preferences."""
        disable_shadow = self._drag_mode in ('move', 'resize')
        use_shadow = (
            self._shadow_enabled
            and self.transform().m11() <= self._shadow_disable_threshold
            and not disable_shadow
        )

        if use_shadow:
            if self.page_item.graphicsEffect() is not self._shadow_effect:
                self.page_item.setGraphicsEffect(self._shadow_effect)
            self._shadow_effect.setEnabled(True)
        else:
            if self.page_item.graphicsEffect() is self._shadow_effect:
                self._shadow_effect.setEnabled(False)

    def update_visible_items(self):
        """Show or hide items based on their intersection with the viewport."""
        scene_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        for item in self.scene.items():
            visible = item.sceneBoundingRect().intersects(scene_rect)
            item.setVisible(visible)
            item.setEnabled(visible)

    def drawForeground(self, painter: QPainter, rect):
        super().drawForeground(painter, rect)
        
        if self._drag_mode == 'rubberband':
            painter.save()
            painter.resetTransform() 
            painter.setPen(QPen(QColor(200, 200, 255), 1, Qt.PenStyle.DashLine))
            painter.setBrush(QColor(82, 139, 255, 30))
            painter.drawRect(self._rubber_band_rect.normalized())
            painter.restore()

        selected_items = self.scene.selectedItems()
        if not selected_items:
            return

        current_scale = self.transform().m11()
        group_rect = self.get_group_bounding_rect()

        if len(selected_items) > 1:
            for item in selected_items:
                self.selection_overlay.paint(painter, item.sceneBoundingRect(), current_scale, draw_handles=False)
        
        if group_rect:
            self.selection_overlay.paint(painter, group_rect, current_scale, draw_handles=True)

    def get_group_bounding_rect(self):
        group_rect = None
        for item in self.scene.selectedItems():
            item_rect = item.sceneBoundingRect()
            if group_rect is None:
                group_rect = item_rect
            else:
                group_rect = group_rect.united(item_rect)
        return group_rect

    def get_handle_at(self, pos: QPoint):
        group_rect = self.get_group_bounding_rect()
        if not group_rect: return None

        view_rect = self.mapFromScene(group_rect).boundingRect()
        s = self.selection_overlay.handle_size
        
        handle_positions = {
            'top_left': QRectF(view_rect.left() - s/2, view_rect.top() - s/2, s, s),
            'top_right': QRectF(view_rect.right() - s/2, view_rect.top() - s/2, s, s),
            'bottom_left': QRectF(view_rect.left() - s/2, view_rect.bottom() - s/2, s, s),
            'bottom_right': QRectF(view_rect.right() - s/2, view_rect.bottom() - s/2, s, s),
            'top': QRectF(view_rect.center().x() - s/2, view_rect.top() - s/2, s, s),
            'bottom': QRectF(view_rect.center().x() - s/2, view_rect.bottom() - s/2, s, s),
            'left': QRectF(view_rect.left() - s/2, view_rect.center().y() - s/2, s, s),
            'right': QRectF(view_rect.right() - s/2, view_rect.center().y() - s/2, s, s),
        }

        for handle, rect in handle_positions.items():
            if rect.contains(QPointF(pos)):
                return handle
        return None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_visible_items()

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        self.update_visible_items()

    def mousePressEvent(self, event: QMouseEvent):
        if self.active_tool != constants.TOOL_SELECT:
            if event.button() == Qt.MouseButton.LeftButton:
                scene_pos = self.mapToScene(event.pos())
                if self.active_tool == constants.TOOL_BUTTON:
                    default_props = button_tool.get_default_properties()
                    pos_x = int(scene_pos.x() - default_props['size']['width'] / 2)
                    pos_y = int(scene_pos.y() - default_props['size']['height'] / 2)
                    child_data = {
                        "instance_id": str(uuid.uuid4()),
                        "tool_type": constants.TOOL_BUTTON,
                        "properties": {**default_props, "position": {"x": pos_x, "y": pos_y}}
                    }
                    command = AddChildCommand(self.screen_id, child_data)
                    command_history_service.add_command(command)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self._last_mouse_scene_pos = self.mapToScene(event.pos())
            
            # Priority 1: Check for resize handle click
            self._resize_handle = self.get_handle_at(event.pos())
            if self._resize_handle:
                self._drag_mode = 'resize'
                self._start_selection_states.clear()
                for item in self.scene.selectedItems():
                    if isinstance(item, BaseGraphicsItem):
                        self._start_selection_states[item.get_instance_id()] = item.sceneBoundingRect()
                self._update_shadow_for_zoom()
                event.accept()
                return

            # Priority 2: Check if clicking on an item for selection/multi-selection
            clicked_item = self.itemAt(event.pos())
            if isinstance(clicked_item, BaseGraphicsItem):
                # Handle multi-selection with modifier keys
                if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                    # Ctrl+Click: Toggle selection of the clicked item
                    clicked_item.setSelected(not clicked_item.isSelected())
                    event.accept()
                    return
                elif event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                    # Shift+Click: Toggle selection (deselect if selected, select if not selected)
                    clicked_item.setSelected(not clicked_item.isSelected())
                    event.accept()
                    return
                else:
                    # Regular click: Clear selection and select only this item (unless already selected)
                    if not clicked_item.isSelected():
                        self.scene.clearSelection()
                        clicked_item.setSelected(True)
                    # Allow dragging of selected items
                    self._drag_mode = 'move'
                    self._start_selection_states.clear()
                    for item in self.scene.selectedItems():
                        if isinstance(item, BaseGraphicsItem):
                            self._start_selection_states[item.get_instance_id()] = item.pos()
                    self._update_shadow_for_zoom()
                    event.accept()
                    return
            else:
                # Clicking on empty space - start rubber band selection
                if event.modifiers() not in (Qt.KeyboardModifier.ControlModifier, Qt.KeyboardModifier.ShiftModifier):
                    # Clear selection only if no modifier keys are pressed
                    self.scene.clearSelection()
                
                self._drag_mode = 'rubberband'
                self._rubber_band_origin = event.pos()
                self._rubber_band_rect = QRect(self._rubber_band_origin, self._rubber_band_origin)
                self.viewport().update()
                self._update_shadow_for_zoom()
                event.accept()
                return
        else:
             super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        current_scene_pos = self.mapToScene(event.pos())
        self.mouse_moved_on_scene.emit(current_scene_pos)
        
        delta = current_scene_pos - self._last_mouse_scene_pos

        if self._drag_mode == 'resize':
            self._perform_group_resize(delta)
        elif self._drag_mode == 'move':
            self._perform_group_move(delta)
        elif self._drag_mode == 'rubberband':
            self._rubber_band_rect.setBottomRight(event.pos())
            self.viewport().update()
        else:
            if self.scene.selectedItems():
                handle = self.get_handle_at(event.pos())
                if handle:
                    if handle in ['top_left', 'bottom_right']: self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
                    elif handle in ['top_right', 'bottom_left']: self.setCursor(QCursor(Qt.CursorShape.SizeBDiagCursor))
                    elif handle in ['top', 'bottom']: self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
                    elif handle in ['left', 'right']: self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
                else:
                    self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            else:
                self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        
        self._last_mouse_scene_pos = current_scene_pos

    def leaveEvent(self, event):
        """Handle mouse leaving the canvas to clear position display."""
        self.mouse_left_scene.emit()
        super().leaveEvent(event)

    def _perform_group_move(self, delta: QPointF):
        """Applies a move delta to all selected items."""
        for item in self.scene.selectedItems():
            if isinstance(item, BaseGraphicsItem):
                item.moveBy(delta.x(), delta.y())
        self.scene.update()
        
        # Emit real-time position updates during drag
        if self.scene.selectedItems():
            first_item = self.scene.selectedItems()[0]
            if isinstance(first_item, BaseGraphicsItem):
                pos_dict = {'x': int(first_item.pos().x()), 'y': int(first_item.pos().y())}
                self.selection_dragged.emit(pos_dict)

    def _perform_group_resize(self, delta: QPointF):
        if not self._start_selection_states: return

        current_group_rect = self.get_group_bounding_rect()
        new_group_rect = QRectF(current_group_rect)

        # Apply delta to the appropriate edges based on the resize handle
        if 'left' in self._resize_handle: new_group_rect.setLeft(new_group_rect.left() + delta.x())
        if 'right' in self._resize_handle: new_group_rect.setRight(new_group_rect.right() + delta.x())
        if 'top' in self._resize_handle: new_group_rect.setTop(new_group_rect.top() + delta.y())
        if 'bottom' in self._resize_handle: new_group_rect.setBottom(new_group_rect.bottom() + delta.y())

        # Calculate scale factors
        scale_x = new_group_rect.width() / current_group_rect.width() if current_group_rect.width() != 0 else 1
        scale_y = new_group_rect.height() / current_group_rect.height() if current_group_rect.height() != 0 else 1

        # Apply proportional scaling when Shift is pressed
        if self._shift_pressed:
            # For proportional scaling, determine which scale factor to use
            # Use the scale factor that has the larger absolute change from 1.0
            scale_x_change = abs(scale_x - 1.0)
            scale_y_change = abs(scale_y - 1.0)
            
            # Choose the scale factor with the larger change
            if scale_x_change >= scale_y_change:
                uniform_scale = scale_x
            else:
                uniform_scale = scale_y
            
            # For corner handles, apply uniform scaling
            if self._resize_handle in ['top_left', 'top_right', 'bottom_left', 'bottom_right']:
                scale_x = scale_y = uniform_scale
                
                # Recalculate the new group rect with uniform scaling
                center = current_group_rect.center()
                new_width = current_group_rect.width() * uniform_scale
                new_height = current_group_rect.height() * uniform_scale
                
                new_group_rect = QRectF(
                    center.x() - new_width / 2,
                    center.y() - new_height / 2,
                    new_width,
                    new_height
                )
                
                # Adjust position based on which corner is being dragged
                if self._resize_handle == 'top_left':
                    new_group_rect.moveBottomRight(current_group_rect.bottomRight())
                elif self._resize_handle == 'top_right':
                    new_group_rect.moveBottomLeft(current_group_rect.bottomLeft())
                elif self._resize_handle == 'bottom_left':
                    new_group_rect.moveTopRight(current_group_rect.topRight())
                elif self._resize_handle == 'bottom_right':
                    new_group_rect.moveTopLeft(current_group_rect.topLeft())
            
            # For edge handles with Shift pressed, also apply proportional scaling
            elif self._resize_handle in ['top', 'bottom', 'left', 'right']:
                scale_x = scale_y = uniform_scale
                
                # Recalculate the new group rect with uniform scaling
                center = current_group_rect.center()
                new_width = current_group_rect.width() * uniform_scale
                new_height = current_group_rect.height() * uniform_scale
                
                new_group_rect = QRectF(
                    center.x() - new_width / 2,
                    center.y() - new_height / 2,
                    new_width,
                    new_height
                )
                
                # Adjust position based on which edge is being dragged
                if self._resize_handle == 'top':
                    new_group_rect.moveBottom(current_group_rect.bottom())
                elif self._resize_handle == 'bottom':
                    new_group_rect.moveTop(current_group_rect.top())
                elif self._resize_handle == 'left':
                    new_group_rect.moveRight(current_group_rect.right())
                elif self._resize_handle == 'right':
                    new_group_rect.moveLeft(current_group_rect.left())

        # Apply the scaling to all selected items
        for item in self.scene.selectedItems():
            if not isinstance(item, BaseGraphicsItem) or not hasattr(item, 'is_resizable') or not item.is_resizable: continue
            
            start_item_rect = item.sceneBoundingRect()
            
            relative_x = (start_item_rect.left() - current_group_rect.left()) * scale_x
            relative_y = (start_item_rect.top() - current_group_rect.top()) * scale_y
            
            new_width = start_item_rect.width() * scale_x
            new_height = start_item_rect.height() * scale_y

            item.setPos(new_group_rect.left() + relative_x, new_group_rect.top() + relative_y)
            item.instance_data.setdefault('properties', {})['size'] = {'width': new_width, 'height': new_height}
            item.update_data(item.instance_data)

        self.scene.update()
        
        # Emit real-time size and position updates during resize
        if self.scene.selectedItems():
            first_item = self.scene.selectedItems()[0]
            if isinstance(first_item, BaseGraphicsItem):
                # Get current size from the updated item data
                size_data = first_item.instance_data.get('properties', {}).get('size', {})
                pos_data = {'x': int(first_item.pos().x()), 'y': int(first_item.pos().y())}
                
                # Create a combined update signal with both position and size
                update_data = {
                    'position': pos_data,
                    'size': {'width': int(size_data.get('width', 0)), 'height': int(size_data.get('height', 0))}
                }
                
                # Emit selection changed to update status bar with new size
                selection_data = [copy.deepcopy(first_item.instance_data)]
                self.selection_changed.emit(self.screen_id, selection_data)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._drag_mode == 'resize':
                update_list = []
                for item in self.scene.selectedItems():
                    if not isinstance(item, BaseGraphicsItem) or not hasattr(item, 'is_resizable') or not item.is_resizable: continue
                    
                    start_rect = self._start_selection_states[item.get_instance_id()]
                    
                    old_props = copy.deepcopy(item.instance_data['properties'])
                    old_props['position'] = {'x': start_rect.x(), 'y': start_rect.y()}
                    old_props['size'] = {'width': start_rect.width(), 'height': start_rect.height()}
                    
                    new_props = copy.deepcopy(item.instance_data['properties'])
                    new_props['position'] = {'x': item.pos().x(), 'y': item.pos().y()}
                    
                    if old_props != new_props:
                        update_list.append((item.get_instance_id(), new_props, old_props))
                
                if update_list:
                    command = BulkUpdateChildPropertiesCommand(self.screen_id, update_list)
                    command_history_service.add_command(command)

            elif self._drag_mode == 'move':
                move_list = []
                for item in self.scene.selectedItems():
                    if isinstance(item, BaseGraphicsItem):
                        start_pos = self._start_selection_states.get(item.get_instance_id())
                        if start_pos and start_pos != item.pos():
                            move_list.append((item.get_instance_id(), {'x': item.pos().x(), 'y': item.pos().y()}, {'x': start_pos.x(), 'y': start_pos.y()}))
                if move_list:
                    command = BulkMoveChildCommand(self.screen_id, move_list)
                    command_history_service.add_command(command)
                
            elif self._drag_mode == 'rubberband':
                self.viewport().update()
                selection_path = QPainterPath()
                view_rect = self._rubber_band_rect.normalized()
                scene_path = self.mapToScene(view_rect)
                selection_path.addPolygon(scene_path)
                
                # --- MODIFIED: Use correct enum syntax ---
                selection_op = Qt.ItemSelectionOperation.ReplaceSelection
                if event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                    selection_op = Qt.ItemSelectionOperation.AddToSelection
                elif event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                    selection_op = Qt.ItemSelectionOperation.ToggleSelection
                
                self.scene.setSelectionArea(selection_path, selection_op, Qt.ItemSelectionMode.ContainsItemBoundingRect)
                
            self._drag_mode = None
            self._resize_handle = None
            self._rubber_band_origin = None
            self._rubber_band_rect = QRect()
            self._update_shadow_for_zoom()
        
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            old_pos = self.mapToScene(event.position().toPoint())
            factor = 1.1 if event.angleDelta().y() > 0 else 1 / 1.1
            new_zoom = max(self.min_zoom, min(self.max_zoom, self.current_zoom * factor))
            scale_factor = new_zoom / self.current_zoom
            if scale_factor != 1.0:
                self.scale(scale_factor, scale_factor)
            self.current_zoom = new_zoom
            new_pos = self.mapToScene(event.position().toPoint())
            delta = old_pos - new_pos
            self.translate(delta.x(), delta.y())
            self.view_zoomed.emit(f"{int(self.current_zoom * 100)}%")
            self._update_shadow_for_zoom()
            self.update_visible_items()
            event.accept()
        else:
            super().wheelEvent(event)

    def update_screen_data(self):
        self.screen_data = screen_service.get_screen(self.screen_id)
        if not self.screen_data:
            self.scene.clear()
            return
            
        size = self.screen_data.get('size', {'width': 1920, 'height': 1080})
        self.scene.setSceneRect(0, 0, size['width'], size['height'])
        
        style = self.screen_data.get('style', {})
        self.page_item.setRect(self.scene.sceneRect())
        self.page_item.setPen(QPen(Qt.PenStyle.NoPen))
        
        if style.get('transparent', False):
            self.page_item.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        else:
            color = style.get('color1', "#FFFFFF")
            self.page_item.setBrush(QBrush(QColor(color)))

        self._sync_scene_items()
        self.update()
        self._update_shadow_for_zoom()
        self.update_visible_items()

    def update_theme_colors(self, theme_name):
        """Update canvas colors based on the current theme."""
        if theme_name == 'dark_theme':
            self.setBackgroundBrush(QColor("#1e1e1e"))
            # Update page item color for dark theme
            if not self.screen_data.get('style', {}).get('transparent', False):
                self.page_item.setBrush(QColor("#252526"))
        elif theme_name == 'light_theme':
            self.setBackgroundBrush(QColor("#ffffff"))
            # Update page item color for light theme
            if not self.screen_data.get('style', {}).get('transparent', False):
                self.page_item.setBrush(QColor("#ffffff"))
        else:  # default theme
            self.setBackgroundBrush(QColor("#f5f5f5"))
            if not self.screen_data.get('style', {}).get('transparent', False):
                self.page_item.setBrush(QColor("#f5f5f5"))
        self.update()

    def _sync_scene_items(self):
        children_list = self.screen_data.get('children', [])
        current_instance_ids = {item_data['instance_id'] for item_data in children_list}
        for instance_id, item in list(self._item_map.items()):
            if instance_id not in current_instance_ids:
                self.scene.removeItem(item)
                del self._item_map[instance_id]
        for child_data in children_list:
            instance_id = child_data['instance_id']
            if instance_id in self._item_map:
                item = self._item_map[instance_id]
                item.update_data(child_data)
                pos_data = child_data.get('position') or child_data.get('properties', {}).get('position', {})
                item.setPos(QPointF(pos_data.get('x', 0), pos_data.get('y', 0)))
            else:
                self._create_item(child_data)
        for i, child_data in enumerate(children_list):
            instance_id = child_data['instance_id']
            if instance_id in self._item_map:
                self._item_map[instance_id].setZValue(i)

    def _create_item(self, child_data):
        instance_id = child_data.get('instance_id')
        if not instance_id: return None
        item = None
        if 'tool_type' in child_data:
            if child_data['tool_type'] == constants.TOOL_BUTTON:
                item = ButtonItem(child_data)
        elif 'screen_id' in child_data:
            item = EmbeddedScreenItem(child_data)
        if item:
            pos_data = child_data.get('position') or child_data.get('properties', {}).get('position', {})
            item.setPos(QPointF(pos_data.get('x', 0), pos_data.get('y', 0)))
            self.scene.addItem(item)
            self._item_map[instance_id] = item
        return item

    def add_embedded_screen(self, screen_id, position):
        """
        Add an embedded screen at the specified position on the canvas.
        """
        import uuid
        child_data = {
            "instance_id": str(uuid.uuid4()),
            "screen_id": screen_id,
            "position": {"x": int(position.x()), "y": int(position.y())},
            "size": {"width": 200, "height": 150}  # Default embedded screen size
        }
        from services.commands import AddChildCommand
        command = AddChildCommand(self.screen_id, child_data)
        from services.command_history_service import command_history_service
        command_history_service.add_command(command)

    def _on_selection_changed(self):
        self.viewport().update()
        selection_data = []
        for item in self.scene.selectedItems():
            if isinstance(item, BaseGraphicsItem):
                selection_data.append(copy.deepcopy(item.instance_data))
        self.selection_changed.emit(self.screen_id, selection_data)

    def set_active_tool(self, tool_name: str):
        self.active_tool = tool_name
        if tool_name == constants.TOOL_SELECT:
            # Use NoDrag mode since we handle selection manually
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
        else:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.clear_selection()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        item = self.itemAt(event.pos())
        if isinstance(item, ButtonItem):
            self._open_button_properties(item.instance_data)
        elif isinstance(item, EmbeddedScreenItem):
            self.open_screen_requested.emit(item.instance_data.get('screen_id'))
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        if not isinstance(item, BaseGraphicsItem):
            menu = QMenu(self)
            paste_action = menu.addAction(IconManager.create_icon('fa5s.paste'), "Paste")
            paste_action.triggered.connect(self.paste)
            content_type, _ = clipboard_service.get_content()
            paste_action.setEnabled(content_type == constants.CLIPBOARD_TYPE_HMI_OBJECTS)
            menu.exec(event.globalPos())
            return
        if not item.isSelected():
            self.scene.clearSelection()
            item.setSelected(True)
        
        selected_items = self.scene.selectedItems()
        selection_count = len(selected_items)
        
        menu = QMenu(self)
        cut_action = menu.addAction(IconManager.create_icon('fa5s.cut'), "Cut")
        copy_action = menu.addAction(IconManager.create_icon('fa5s.copy'), "Copy")
        duplicate_action = menu.addAction("Duplicate")
        delete_action = menu.addAction(IconManager.create_icon('fa5s.trash-alt'), "Delete")
        menu.addSeparator()
        
        stacking_menu = menu.addMenu("Stacking Order")
        to_front_action = stacking_menu.addAction("Move to Front")
        to_back_action = stacking_menu.addAction("Move to Back")
        forward_action = stacking_menu.addAction("Move Forward")
        backward_action = stacking_menu.addAction("Move Backward")
        
        if selection_count == 1:
            to_front_action.setEnabled(True)
            to_back_action.setEnabled(True)
            forward_action.setEnabled(True)
            backward_action.setEnabled(True)
        elif selection_count > 1:
            to_front_action.setEnabled(False)
            to_back_action.setEnabled(False)
            forward_action.setEnabled(True)
            backward_action.setEnabled(True)
        else:
            stacking_menu.setEnabled(False)

        menu.addSeparator()
        
        if selection_count == 1:
            if isinstance(item, EmbeddedScreenItem):
                open_action = menu.addAction(IconManager.create_icon('fa5s.external-link-alt'), "Open Base Screen")
                open_action.triggered.connect(self.open_selected_child)
            elif isinstance(item, ButtonItem):
                props_action = menu.addAction("Properties...")
                props_action.triggered.connect(lambda: self._open_button_properties(item.instance_data))

        cut_action.triggered.connect(self.cut_selected)
        copy_action.triggered.connect(self.copy_selected)
        duplicate_action.triggered.connect(self.duplicate_selected)
        delete_action.triggered.connect(self.delete_selected)
        
        to_front_action.triggered.connect(lambda: self._handle_stacking_order('forward'))
        to_back_action.triggered.connect(lambda: self._handle_stacking_order('backward'))
        forward_action.triggered.connect(lambda: self._handle_stacking_order('front'))
        backward_action.triggered.connect(lambda: self._handle_stacking_order('back'))

        menu.exec(event.globalPos())

    def keyPressEvent(self, event: QKeyEvent):
        # Handle arrow key movement for selected items
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            self._move_selected_items(event.key())
            event.accept()
        elif event.key() == Qt.Key.Key_Shift:
            self._shift_pressed = True
            event.accept()
        elif event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selected()
            event.accept()
        elif event.key() == Qt.Key.Key_Escape:
            self.scene.clearSelection()
            event.accept()
        elif event.key() == Qt.Key.Key_A and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl+A - Select all
            for item in self.scene.items():
                if isinstance(item, BaseGraphicsItem):
                    item.setSelected(True)
            event.accept()
        elif event.key() == Qt.Key.Key_C and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl+C - Copy
            self.copy_selected()
            event.accept()
        elif event.key() == Qt.Key.Key_X and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl+X - Cut
            self.cut_selected()
            event.accept()
        elif event.key() == Qt.Key.Key_V and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl+V - Paste
            self.paste()
            event.accept()
        elif event.key() == Qt.Key.Key_Z and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl+Z - Undo
            command_history_service.undo()
            event.accept()
        elif event.key() == Qt.Key.Key_Y and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl+Y - Redo
            command_history_service.redo()
            event.accept()
        elif event.key() == Qt.Key.Key_D and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl+D - Duplicate
            self.duplicate_selected()
            event.accept()
        elif event.key() == Qt.Key.Key_G and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl+G - Group (future enhancement)
            event.accept()
        elif event.key() == Qt.Key.Key_R and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl+R - Rotate (future enhancement)
            event.accept()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Shift:
            self._shift_pressed = False
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasFormat(constants.MIME_TYPE_SCREEN_ID):
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasFormat(constants.MIME_TYPE_SCREEN_ID):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasFormat(constants.MIME_TYPE_SCREEN_ID):
            dropped_screen_id = event.mimeData().data(constants.MIME_TYPE_SCREEN_ID).data().decode('utf-8')
            if dropped_screen_id == self.screen_id:
                event.ignore()
                return
            drop_pos = self.mapToScene(event.pos())
            position_dict = {'x': int(drop_pos.x()), 'y': int(drop_pos.y())}
            child_data = {
                "instance_id": str(uuid.uuid4()),
                "screen_id": dropped_screen_id,
                "position": position_dict
            }
            command = AddChildCommand(self.screen_id, child_data)
            command_history_service.add_command(command)
            event.acceptProposedAction()

    def duplicate_selected(self):
        if self.has_selection():
            self.copy_selected()
            self.paste()

    def open_selected_child(self):
        selected_items = self.scene.selectedItems()
        if len(selected_items) == 1 and isinstance(selected_items[0], EmbeddedScreenItem):
            child_id = selected_items[0].instance_data.get('screen_id')
            if child_id:
                self.open_screen_requested.emit(child_id)

    def _handle_stacking_order(self, direction: str):
        selected_items = self.scene.selectedItems()
        if not selected_items:
            return
            
        instance_ids = [item.get_instance_id() for item in selected_items if isinstance(item, BaseGraphicsItem)]
        
        if len(instance_ids) == 1:
            screen_service.reorder_child(self.screen_id, instance_ids[0], direction)
        elif len(instance_ids) > 1 and direction in ('front', 'back'):
            screen_service.reorder_children(self.screen_id, instance_ids, direction)

    def has_selection(self):
        return bool(self.scene.selectedItems())

    def clear_selection(self):
        self.scene.clearSelection()

    def copy_selected(self):
        selected_items = [item.instance_data for item in self.scene.selectedItems() if isinstance(item, BaseGraphicsItem)]
        if selected_items:
            clipboard_service.set_content(constants.CLIPBOARD_TYPE_HMI_OBJECTS, selected_items)

    def cut_selected(self):
        self.copy_selected()
        self.delete_selected()

    def paste(self):
        content_type, data = clipboard_service.get_content()
        if content_type != constants.CLIPBOARD_TYPE_HMI_OBJECTS: return
        items_to_paste = data if isinstance(data, list) else [data]
        for item_data in items_to_paste:
            new_item = copy.deepcopy(item_data)
            new_item['instance_id'] = str(uuid.uuid4())
            pos_dict = new_item.get('position') or new_item.get('properties', {}).get('position', {})
            pos_dict['x'] = int(pos_dict.get('x', 0)) + 20
            pos_dict['y'] = int(pos_dict.get('y', 0)) + 20
            command = AddChildCommand(self.screen_id, new_item)
            command_history_service.add_command(command)

    def delete_selected(self):
        selected_items = self.scene.selectedItems()
        if not selected_items: return
        for item in self.scene.selectedItems():
            if isinstance(item, BaseGraphicsItem):
                command = RemoveChildCommand(self.screen_id, item.instance_data)
                command_history_service.add_command(command)
        self.clear_selection()

    def _move_selected_items(self, key):
        """Move selected items using arrow keys."""
        selected_items = self.scene.selectedItems()
        if not selected_items:
            return
            
        # Determine movement amount based on modifier keys
        from PyQt6.QtWidgets import QApplication
        modifiers = QApplication.keyboardModifiers()
        move_amount = 10 if modifiers & Qt.KeyboardModifier.ShiftModifier else 1
        
        move_list = []
        
        for item in selected_items:
            if isinstance(item, BaseGraphicsItem):
                old_pos = item.pos()
                new_pos = QPointF(old_pos.x(), old_pos.y())
                
                if key == Qt.Key.Key_Left:
                    new_pos.setX(old_pos.x() - move_amount)
                elif key == Qt.Key.Key_Right:
                    new_pos.setX(old_pos.x() + move_amount)
                elif key == Qt.Key.Key_Up:
                    new_pos.setY(old_pos.y() - move_amount)
                elif key == Qt.Key.Key_Down:
                    new_pos.setY(old_pos.y() + move_amount)
                
                # Update item position immediately
                item.setPos(new_pos)
                
                # Prepare for undo/redo command
                move_list.append((
                    item.get_instance_id(),
                    {'x': new_pos.x(), 'y': new_pos.y()},
                    {'x': old_pos.x(), 'y': old_pos.y()}
                ))
        
        if move_list:
            command = BulkMoveChildCommand(self.screen_id, move_list)
            command_history_service.add_command(command)
            
        # Update the scene and emit position changes
        self.scene.update()
        if selected_items:
            first_item = selected_items[0]
            if isinstance(first_item, BaseGraphicsItem):
                pos_dict = {'x': int(first_item.pos().x()), 'y': int(first_item.pos().y())}
                self.selection_dragged.emit(pos_dict)

    def _open_button_properties(self, button_instance_data):
        from components.button.button_properties_dialog import ButtonPropertiesDialog
        
        # Store original position before dialog
        original_pos = None
        item = self._item_map.get(button_instance_data['instance_id'])
        if item:
            original_pos = item.pos()
        
        dialog = ButtonPropertiesDialog(button_instance_data['properties'], self)
        if dialog.exec():
            new_properties = dialog.get_data()
            old_properties = button_instance_data['properties']
            if new_properties != old_properties:
                command = UpdateChildPropertiesCommand(
                    self.screen_id, 
                    button_instance_data['instance_id'], 
                    new_properties, 
                    old_properties
                )
                command_history_service.add_command(command)
        
        # Ensure item position is restored and scene is updated
        if item and original_pos:
            item.setPos(original_pos)
            self.scene.update()
            self.viewport().update()
