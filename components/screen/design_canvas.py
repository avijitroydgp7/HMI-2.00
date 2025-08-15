# components/screen/design_canvas.py
# MODIFIED: Overhauled mouse event logic to correctly handle multi-selection.

from PyQt6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QMenu,
    QGraphicsRectItem,
    QGraphicsDropShadowEffect,
    QGraphicsLineItem,
    QGraphicsEllipseItem,
    QGraphicsPathItem,
)
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QMouseEvent,
    QKeyEvent,
    QDragEnterEvent,
    QDropEvent,
    QPen,
    QPainterPath,
    QCursor,
    QBrush,
)
from PyQt6.QtCore import Qt, QPoint, QPointF, pyqtSignal, QRectF, QRect, QEvent, QLineF, QTimer
import copy
import uuid

from utils.icon_manager import IconManager
from services.screen_data_service import screen_service
from services.clipboard_service import clipboard_service
from services.command_history_service import command_history_service
from services.commands import MoveChildCommand, RemoveChildCommand, AddChildCommand, UpdateChildPropertiesCommand, BulkUpdateChildPropertiesCommand, BulkMoveChildCommand
from tools import (
    button as button_tool,
    line as line_tool,
    polygon as polygon_tool,
    text as text_tool,
    image as image_tool,
    dxf as dxf_tool,
    scale as scale_tool,
)

from .graphics_items import (
    ButtonItem,
    EmbeddedScreenItem,
    BaseGraphicsItem,
    TextItem,
    LineItem,
    FreeformItem,
    RectItem,
    PolygonItem,
    CircleItem,
    ArcItem,
    SectorItem,
    TableItem,
    ScaleItem,
    ImageItem,
    DxfItem,
)
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

        # State used while creating new items with drawing tools
        self._drawing = False
        self._start_pos = None
        self._draw_points = []
        self._preview_item = None

        self.scene = QGraphicsScene(self)
        self.scene.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.BspTreeIndex)
        self.setScene(self.scene)
        self.page_item = QGraphicsRectItem()

        # Track items currently visible/hidden on the scene
        self._visible_items = set()
        self._hidden_items = set()

        # Throttle expensive visibility updates
        self._visible_update_timer = QTimer(self)
        self._visible_update_timer.setSingleShot(True)
        self._visible_update_timer.timeout.connect(self.update_visible_items)

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
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.viewport().installEventFilter(self)

        self.scene.selectionChanged.connect(self._on_selection_changed)

        self.update_screen_data()


    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.HoverMove:
            self._last_mouse_scene_pos = self.mapToScene(event.position().toPoint())
        elif event.type() == QEvent.Type.MouseMove and event.buttons() == Qt.MouseButton.NoButton:
            self._last_mouse_scene_pos = self.mapToScene(event.pos())
        return False

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

        # Items intersecting the current viewport
        visible_now = set(self.scene.items(scene_rect))

        # On first run, assume everything starts visible so off-screen items get hidden
        if not self._visible_items and not self._hidden_items:
            self._visible_items = set(self.scene.items())

        # Show items that were hidden but now intersect the viewport
        for item in visible_now & self._hidden_items:
            item.setVisible(True)
            item.setEnabled(True)
            self._hidden_items.remove(item)

        # Hide items that no longer intersect the viewport
        for item in self._visible_items - visible_now:
            item.setVisible(False)
            item.setEnabled(False)
            self._hidden_items.add(item)

        # Update the set of currently visible items
        self._visible_items = visible_now

    def _schedule_visible_items_update(self):
        """Schedule a deferred call to update_visible_items."""
        # Restarting the timer coalesces multiple rapid requests
        self._visible_update_timer.start(16)

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
        if not group_rect:
            return None

        current_scale = self.transform().m11()
        handle_size = self.selection_overlay.handle_size / current_scale
        half_handle = handle_size / 2.0
        
        handle_positions = {
            'top_left': QRectF(group_rect.left() - half_handle, group_rect.top() - half_handle, handle_size, handle_size),
            'top_right': QRectF(group_rect.right() - half_handle, group_rect.top() - half_handle, handle_size, handle_size),
            'bottom_left': QRectF(group_rect.left() - half_handle, group_rect.bottom() - half_handle, handle_size, handle_size),
            'bottom_right': QRectF(group_rect.right() - half_handle, group_rect.bottom() - half_handle, handle_size, handle_size),
            'top': QRectF(group_rect.center().x() - half_handle, group_rect.top() - half_handle, handle_size, handle_size),
            'bottom': QRectF(group_rect.center().x() - half_handle, group_rect.bottom() - half_handle, handle_size, handle_size),
            'left': QRectF(group_rect.left() - half_handle, group_rect.center().y() - half_handle, handle_size, handle_size),
            'right': QRectF(group_rect.right() - half_handle, group_rect.center().y() - half_handle, handle_size, handle_size),
        }

        scene_pos = self.mapToScene(pos)
        for handle, rect in handle_positions.items():
            if rect.contains(scene_pos):
                return handle
        return None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._schedule_visible_items_update()

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        self._schedule_visible_items_update()

    def mousePressEvent(self, event: QMouseEvent):
        if self.active_tool != constants.TOOL_SELECT:
            if event.button() == Qt.MouseButton.LeftButton:
                scene_pos = self.mapToScene(event.pos())

                if not self._drawing and self._preview_item:
                    self.scene.removeItem(self._preview_item)
                    self._preview_item = None

                if self.active_tool == constants.TOOL_BUTTON:
                    default_props = button_tool.get_default_properties()
                    pos_x = int(scene_pos.x() - default_props['size']['width'] / 2)
                    pos_y = int(scene_pos.y() - default_props['size']['height'] / 2)
                    default_props["position"] = {"x": pos_x, "y": pos_y}
                    self._add_tool_item(constants.TOOL_BUTTON, default_props)
                elif self.active_tool == constants.TOOL_TEXT:
                    default_props = text_tool.get_default_properties()
                    default_props["position"] = {
                        "x": int(scene_pos.x()),
                        "y": int(scene_pos.y()),
                    }
                    self._add_tool_item(constants.TOOL_TEXT, default_props)
                elif self.active_tool == constants.TOOL_IMAGE:
                    props = image_tool.prompt_for_image(self)
                    if props:
                        props["position"] = {
                            "x": int(scene_pos.x()),
                            "y": int(scene_pos.y()),
                        }
                        self._add_tool_item(constants.TOOL_IMAGE, props)
                elif self.active_tool == constants.TOOL_POLYGON:
                    if not self._drawing:
                        self._drawing = True
                        self._draw_points = [scene_pos]
                        pen = QPen(QColor(200, 200, 255), 1, Qt.PenStyle.DashLine)
                        self._preview_item = QGraphicsPathItem()
                        self._preview_item.setPen(pen)
                        self.scene.addItem(self._preview_item)
                    else:
                        self._draw_points.append(scene_pos)
                elif self.active_tool == constants.TOOL_FREEFORM:
                    self._drawing = True
                    self._draw_points = [scene_pos]
                    pen = QPen(QColor(200, 200, 255), 1, Qt.PenStyle.DashLine)
                    self._preview_item = QGraphicsPathItem()
                    self._preview_item.setPen(pen)
                    self.scene.addItem(self._preview_item)
                else:
                    self._drawing = True
                    self._start_pos = scene_pos
                    pen = QPen(QColor(200, 200, 255), 1, Qt.PenStyle.DashLine)
                    if self.active_tool == constants.TOOL_LINE:
                        self._preview_item = QGraphicsLineItem()
                    elif self.active_tool in (
                        constants.TOOL_RECT,
                        constants.TOOL_TABLE,
                        constants.TOOL_SCALE,
                        constants.TOOL_DXF,
                    ):
                        self._preview_item = QGraphicsRectItem()
                    elif self.active_tool in (
                        constants.TOOL_CIRCLE,
                        constants.TOOL_ARC,
                        constants.TOOL_SECTOR,
                    ):
                        self._preview_item = QGraphicsEllipseItem()
                    else:
                        self._preview_item = QGraphicsRectItem()
                    self._preview_item.setPen(pen)
                    # Only set brush for items that support it
                    if isinstance(self._preview_item, (QGraphicsRectItem, QGraphicsEllipseItem)):
                        self._preview_item.setBrush(QBrush(Qt.BrushStyle.NoBrush))
                    self.scene.addItem(self._preview_item)
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
                        self._start_selection_states[item.get_instance_id()] = {
                            'rect': item.sceneBoundingRect(),
                            'properties': copy.deepcopy(item.instance_data.get('properties', {}))
                        }
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

        if self.active_tool != constants.TOOL_SELECT:
            if self._drawing and self._preview_item:
                if self.active_tool == constants.TOOL_FREEFORM:
                    self._draw_points.append(current_scene_pos)
                    path = QPainterPath(self._draw_points[0])
                    for p in self._draw_points[1:]:
                        path.lineTo(p)
                    self._preview_item.setPath(path)
                elif self.active_tool == constants.TOOL_POLYGON:
                    if self._draw_points:
                        path = QPainterPath(self._draw_points[0])
                        for p in self._draw_points[1:]:
                            path.lineTo(p)
                        path.lineTo(current_scene_pos)
                        self._preview_item.setPath(path)
                elif self.active_tool == constants.TOOL_LINE:
                    self._preview_item.setLine(QLineF(self._start_pos, current_scene_pos))
                elif self.active_tool in (
                    constants.TOOL_RECT,
                    constants.TOOL_TABLE,
                    constants.TOOL_SCALE,
                    constants.TOOL_DXF,
                ):
                    rect = QRectF(self._start_pos, current_scene_pos).normalized()
                    self._preview_item.setRect(rect)
                elif self.active_tool in (
                    constants.TOOL_CIRCLE,
                    constants.TOOL_ARC,
                    constants.TOOL_SECTOR,
                ):
                    rect = QRectF(self._start_pos, current_scene_pos).normalized()
                    self._preview_item.setRect(rect)
            return

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
                    if handle in ['top_left', 'bottom_right']:
                        self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
                    elif handle in ['top_right', 'bottom_left']:
                        self.setCursor(QCursor(Qt.CursorShape.SizeBDiagCursor))
                    elif handle in ['top', 'bottom']:
                        self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
                    elif handle in ['left', 'right']:
                        self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
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
        self.viewport().update()
        
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
        if 'left' in self._resize_handle:
            new_left = new_group_rect.left() + delta.x()
            max_left = new_group_rect.right() - 1
            new_group_rect.setLeft(new_left if new_left <= max_left else max_left)
        if 'right' in self._resize_handle:
            new_right = new_group_rect.right() + delta.x()
            min_right = new_group_rect.left() + 1
            new_group_rect.setRight(new_right if new_right >= min_right else min_right)
        if 'top' in self._resize_handle:
            new_top = new_group_rect.top() + delta.y()
            max_top = new_group_rect.bottom() - 1
            new_group_rect.setTop(new_top if new_top <= max_top else max_top)
        if 'bottom' in self._resize_handle:
            new_bottom = new_group_rect.bottom() + delta.y()
            min_bottom = new_group_rect.top() + 1
            new_group_rect.setBottom(new_bottom if new_bottom >= min_bottom else min_bottom)

        if new_group_rect.width() < 1:
            new_group_rect.setWidth(1)
        if new_group_rect.height() < 1:
            new_group_rect.setHeight(1)

        # Calculate scale factors after clamping
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
            if not isinstance(item, BaseGraphicsItem) or not hasattr(item, 'is_resizable') or not item.is_resizable:
                continue

            start_item_rect = item.sceneBoundingRect()
            
            relative_x = (start_item_rect.left() - current_group_rect.left()) * scale_x
            relative_y = (start_item_rect.top() - current_group_rect.top()) * scale_y
            
            new_width = start_item_rect.width() * scale_x
            new_height = start_item_rect.height() * scale_y

            props = item.instance_data.setdefault('properties', {})

            if isinstance(item, LineItem):
                start = props.get('start', {'x': 0, 'y': 0})
                end = props.get('end', {'x': new_width, 'y': new_height})
                start = {'x': start.get('x', 0) * scale_x, 'y': start.get('y', 0) * scale_y}
                end = {'x': end.get('x', 0) * scale_x, 'y': end.get('y', 0) * scale_y}
                min_x = min(start['x'], end['x'])
                min_y = min(start['y'], end['y'])
                start['x'] -= min_x
                start['y'] -= min_y
                end['x'] -= min_x
                end['y'] -= min_y
                relative_x += min_x
                relative_y += min_y
                props.update({'start': start, 'end': end, 'size': {'width': new_width, 'height': new_height}})
            elif isinstance(item, (PolygonItem, FreeformItem)):
                pts = props.get('points', [])
                scaled_pts = [
                    {
                        'x': p.get('x', 0) * scale_x,
                        'y': p.get('y', 0) * scale_y,
                    }
                    for p in pts
                ]
                if scaled_pts:
                    min_x = min(p['x'] for p in scaled_pts)
                    min_y = min(p['y'] for p in scaled_pts)
                else:
                    min_x = min_y = 0
                scaled_pts = [
                    {'x': p['x'] - min_x, 'y': p['y'] - min_y}
                    for p in scaled_pts
                ]
                relative_x += min_x
                relative_y += min_y
                props.update({'points': scaled_pts, 'size': {'width': new_width, 'height': new_height}})
            elif isinstance(item, TextItem):
                props['size'] = {'width': new_width, 'height': new_height}
                font_info = props.get('font', {})
                original_size = font_info.get('size', 12)
                scale = min(scale_x, scale_y)
                font_info['size'] = max(1, int(original_size * scale))
                props['font'] = font_info
            elif isinstance(item, TableItem):
                rows = props.get('rows', 1) or 1
                cols = props.get('columns', 1) or 1
                cell_width = new_width / cols
                cell_height = new_height / rows
                props.update(
                    {
                        'size': {'width': new_width, 'height': new_height},
                        'cell_size': {'width': cell_width, 'height': cell_height},
                    }
                )
            elif isinstance(item, ScaleItem):
                orient = props.get('orientation', 'horizontal')
                if orient == 'horizontal':
                    length = int(new_width)
                    thickness = int(new_height)
                else:
                    length = int(new_height)
                    thickness = int(new_width)
                props.update({'length': length, 'thickness': thickness})
            else:
                props['size'] = {'width': new_width, 'height': new_height}

            item.update_data(item.instance_data)

            offset_rect = item.boundingRect()
            item.setPos(
                new_group_rect.left() + relative_x - offset_rect.left(),
                new_group_rect.top() + relative_y - offset_rect.top(),
            )

        self.viewport().update()
        
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
        if self.active_tool != constants.TOOL_SELECT:
            if event.button() == Qt.MouseButton.LeftButton and self._drawing:
                scene_pos = self.mapToScene(event.pos())
                if self.active_tool == constants.TOOL_LINE:
                    pts = [self._start_pos, scene_pos]
                    min_x = min(p.x() for p in pts)
                    min_y = min(p.y() for p in pts)
                    start = {"x": int(self._start_pos.x() - min_x), "y": int(self._start_pos.y() - min_y)}
                    end = {"x": int(scene_pos.x() - min_x), "y": int(scene_pos.y() - min_y)}
                    props = line_tool.get_default_properties()
                    props.update({"start": start, "end": end, "position": {"x": int(min_x), "y": int(min_y)}})
                    self._add_tool_item(constants.TOOL_LINE, props)
                elif self.active_tool == constants.TOOL_FREEFORM:
                    self._draw_points.append(scene_pos)
                    min_x = min(p.x() for p in self._draw_points)
                    min_y = min(p.y() for p in self._draw_points)
                    rel = [{"x": int(p.x() - min_x), "y": int(p.y() - min_y)} for p in self._draw_points]
                    props = polygon_tool.get_default_properties()
                    props.update({"points": rel, "position": {"x": int(min_x), "y": int(min_y)}})
                    self._add_tool_item(constants.TOOL_FREEFORM, props)
                elif self.active_tool == constants.TOOL_RECT:
                    x = int(min(self._start_pos.x(), scene_pos.x()))
                    y = int(min(self._start_pos.y(), scene_pos.y()))
                    w = int(abs(scene_pos.x() - self._start_pos.x()))
                    h = int(abs(scene_pos.y() - self._start_pos.y()))
                    props = {
                        "position": {"x": x, "y": y},
                        "size": {"width": w, "height": h},
                        "fill_color": "#ffffff",
                        "stroke_color": "#000000",
                        "stroke_width": 1,
                        "stroke_style": "solid",
                    }
                    self._add_tool_item(constants.TOOL_RECT, props)
                elif self.active_tool == constants.TOOL_CIRCLE:
                    x = int(min(self._start_pos.x(), scene_pos.x()))
                    y = int(min(self._start_pos.y(), scene_pos.y()))
                    w = int(abs(scene_pos.x() - self._start_pos.x()))
                    h = int(abs(scene_pos.y() - self._start_pos.y()))
                    props = {
                        "position": {"x": x, "y": y},
                        "size": {"width": w, "height": h},
                        "fill_color": "#ffffff",
                        "stroke_color": "#000000",
                        "stroke_width": 1,
                        "stroke_style": "solid",
                    }
                    self._add_tool_item(constants.TOOL_CIRCLE, props)
                elif self.active_tool == constants.TOOL_ARC:
                    x = int(min(self._start_pos.x(), scene_pos.x()))
                    y = int(min(self._start_pos.y(), scene_pos.y()))
                    w = int(abs(scene_pos.x() - self._start_pos.x()))
                    h = int(abs(scene_pos.y() - self._start_pos.y()))
                    props = {
                        "position": {"x": x, "y": y},
                        "size": {"width": w, "height": h},
                        "start_angle": 0,
                        "span_angle": 90,
                        "color": "#000000",
                        "width": 1,
                        "style": "solid",
                    }
                    self._add_tool_item(constants.TOOL_ARC, props)
                elif self.active_tool == constants.TOOL_SECTOR:
                    x = int(min(self._start_pos.x(), scene_pos.x()))
                    y = int(min(self._start_pos.y(), scene_pos.y()))
                    w = int(abs(scene_pos.x() - self._start_pos.x()))
                    h = int(abs(scene_pos.y() - self._start_pos.y()))
                    props = {
                        "position": {"x": x, "y": y},
                        "size": {"width": w, "height": h},
                        "start_angle": 0,
                        "span_angle": 90,
                        "stroke_color": "#000000",
                        "stroke_width": 1,
                        "stroke_style": "solid",
                        "fill_color": "#ffffff",
                    }
                    self._add_tool_item(constants.TOOL_SECTOR, props)
                elif self.active_tool == constants.TOOL_TABLE:
                    x = int(min(self._start_pos.x(), scene_pos.x()))
                    y = int(min(self._start_pos.y(), scene_pos.y()))
                    w = int(abs(scene_pos.x() - self._start_pos.x()))
                    h = int(abs(scene_pos.y() - self._start_pos.y()))
                    props = {
                        "position": {"x": x, "y": y},
                        "rows": 2,
                        "columns": 2,
                        "cell_size": {"width": max(int(w / 2), 1), "height": max(int(h / 2), 1)},
                        "stroke_color": "#000000",
                        "stroke_width": 1,
                        "fill_color": "#ffffff",
                    }
                    self._add_tool_item(constants.TOOL_TABLE, props)
                elif self.active_tool == constants.TOOL_SCALE:
                    x = int(min(self._start_pos.x(), scene_pos.x()))
                    y = int(min(self._start_pos.y(), scene_pos.y()))
                    w = int(abs(scene_pos.x() - self._start_pos.x()))
                    h = int(abs(scene_pos.y() - self._start_pos.y()))
                    orient = "horizontal" if w >= h else "vertical"
                    length = w if orient == "horizontal" else h
                    thickness = h if orient == "horizontal" else w
                    props = scale_tool.get_default_properties()
                    props.update({
                        "position": {"x": x, "y": y},
                        "orientation": orient,
                        "length": int(length),
                        "thickness": int(thickness),
                        "major_ticks": 10,
                        "minor_ticks": 5,
                        "color": "#000000",
                    })
                    self._add_tool_item(constants.TOOL_SCALE, props)

                elif self.active_tool == constants.TOOL_DXF:
                    shapes = dxf_tool.prompt_for_dxf(self)
                    if shapes:
                        x = int(min(self._start_pos.x(), scene_pos.x()))
                        y = int(min(self._start_pos.y(), scene_pos.y()))
                        for shape in shapes:
                            t = shape.get("tool_type")
                            props = shape.get("properties", {})
                            if t == constants.TOOL_LINE:
                                props["start"]["x"] += x
                                props["start"]["y"] += y
                                props["end"]["x"] += x
                                props["end"]["y"] += y
                            elif t == constants.TOOL_ARC:
                                props["position"]["x"] += x
                                props["position"]["y"] += y
                            elif t == constants.TOOL_POLYGON:
                                for pt in props.get("points", []):
                                    pt["x"] += x
                                    pt["y"] += y
                            self._add_tool_item(t, props)
                if self.active_tool != constants.TOOL_POLYGON:
                    self._drawing = False
                    self._start_pos = None
                    self._draw_points = []
                    if self._preview_item:
                        self.scene.removeItem(self._preview_item)
                        self._preview_item = None
            return
        if event.button() == Qt.MouseButton.LeftButton:
            if self._drag_mode == 'resize':
                update_list = []
                for item in self.scene.selectedItems():
                    if not isinstance(item, BaseGraphicsItem) or not hasattr(item, 'is_resizable') or not item.is_resizable: continue
                    
                    start_state = self._start_selection_states[item.get_instance_id()]
                    start_rect = start_state['rect'] if isinstance(start_state, dict) else start_state

                    base_props = start_state.get('properties', {}) if isinstance(start_state, dict) else {}
                    old_props = copy.deepcopy(base_props)
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
            if self._drag_mode in ('move', 'resize'):
                self.viewport().update()
                
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
            self._last_mouse_scene_pos = self.mapToScene(event.position().toPoint())
            self.view_zoomed.emit(f"{int(self.current_zoom * 100)}%")
            self._update_shadow_for_zoom()
            self._schedule_visible_items_update()
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
                item.update_data(copy.deepcopy(child_data))
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
        data_copy = copy.deepcopy(child_data)
        item = None
        if 'tool_type' in data_copy:
            t = data_copy['tool_type']
            if t == constants.TOOL_BUTTON:
                item = ButtonItem(data_copy)
            elif t == constants.TOOL_TEXT:
                item = TextItem(data_copy)
            elif t == constants.TOOL_LINE:
                item = LineItem(data_copy)
            elif t == constants.TOOL_FREEFORM:
                item = FreeformItem(data_copy)
            elif t == constants.TOOL_RECT:
                item = RectItem(data_copy)
            elif t == constants.TOOL_POLYGON:
                item = PolygonItem(data_copy)
            elif t == constants.TOOL_CIRCLE:
                item = CircleItem(data_copy)
            elif t == constants.TOOL_ARC:
                item = ArcItem(data_copy)
            elif t == constants.TOOL_SECTOR:
                item = SectorItem(data_copy)
            elif t == constants.TOOL_TABLE:
                item = TableItem(data_copy)
            elif t == constants.TOOL_SCALE:
                item = ScaleItem(data_copy)
            elif t == constants.TOOL_IMAGE:
                item = ImageItem(data_copy)
            elif t == constants.TOOL_DXF:
                item = DxfItem(data_copy)
        elif 'screen_id' in data_copy:
            item = EmbeddedScreenItem(data_copy)
        if item:
            pos_data = data_copy.get('position') or data_copy.get('properties', {}).get('position', {})
            item.setPos(QPointF(pos_data.get('x', 0), pos_data.get('y', 0)))
            self.scene.addItem(item)
            self._item_map[instance_id] = item
        return item

    def _add_tool_item(self, tool_type, properties):
        child_data = {
            "instance_id": str(uuid.uuid4()),
            "tool_type": tool_type,
            "properties": properties,
        }
        command = AddChildCommand(self.screen_id, child_data)
        command_history_service.add_command(command)
        main_window = self.window()
        if hasattr(main_window, "revert_to_select_tool"):
            main_window.revert_to_select_tool()

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
        if self.active_tool == constants.TOOL_POLYGON and self._drawing:
            scene_pos = self.mapToScene(event.pos())
            self._draw_points.append(scene_pos)
            min_x = min(p.x() for p in self._draw_points)
            min_y = min(p.y() for p in self._draw_points)
            rel = [{"x": int(p.x() - min_x), "y": int(p.y() - min_y)} for p in self._draw_points]
            props = polygon_tool.get_default_properties()
            props.update({"points": rel, "position": {"x": int(min_x), "y": int(min_y)}})
            self._add_tool_item(constants.TOOL_POLYGON, props)
            self._drawing = False
            self._draw_points = []
            if self._preview_item:
                self.scene.removeItem(self._preview_item)
                self._preview_item = None
            return
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
        if not selected_items:
            return

        instance_data_list = [
            item.instance_data
            for item in selected_items
            if isinstance(item, BaseGraphicsItem)
        ]

        if not instance_data_list:
            return

        self.clear_selection()

        for instance_data in instance_data_list:
            command = RemoveChildCommand(self.screen_id, instance_data)
            command_history_service.add_command(command)

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
