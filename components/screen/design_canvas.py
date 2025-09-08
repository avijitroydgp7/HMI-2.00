# components/screen/design_canvas.py
# MODIFIED: Overhauled mouse event logic to correctly handle multi-selection.

from PyQt6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QMenu,
    QGraphicsRectItem,
    QGraphicsItem,
    QApplication,
)
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QMouseEvent,
    QKeyEvent,
    QWheelEvent,
    QDragEnterEvent,
    QDropEvent,
    QPen,
    QPainterPath,
    QCursor,
    QBrush,
)
from PyQt6.QtCore import Qt, QPoint, QPointF, pyqtSignal, QRectF, QRect, QEvent, QLineF, QTimer, QElapsedTimer
import copy
import uuid

from utils.icon_manager import IconManager
from services.screen_data_service import screen_service
from services.clipboard_service import clipboard_service
from services.command_history_service import command_history_service
from services.commands import MoveChildCommand, RemoveChildCommand, AddChildCommand, UpdateChildPropertiesCommand, BulkUpdateChildPropertiesCommand, BulkMoveChildCommand
from services.settings_service import settings_service
from services.style_data_service import style_data_service
from tools import (
    button as button_tool,
)

from .graphics_items import (
    ButtonItem,
    EmbeddedScreenItem,
    BaseGraphicsItem,
)
from ..selection_overlay import SelectionOverlay
from utils import constants

# View scaling via zoom is not supported in this application

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
    zoom_changed = pyqtSignal(float)
    
    def __init__(self, screen_id, parent=None):
        super().__init__(parent)
        self.screen_id = screen_id
        self.screen_data = None
        self.active_tool = constants.ToolType.SELECT
        self._item_map = {}
        self.selection_overlay = SelectionOverlay()

        # Zoom is disabled; keep view scale fixed at 1.0
        self._rubber_band_origin = None
        self._rubber_band_rect = QRect()

        self._drag_mode = None
        self._resize_handle = None
        self._start_selection_states = {}
        # Track both snapped and raw cursor positions separately.  The raw
        # position is used for drag deltas so that snapping does not shift the
        # cursor-to-item offset during a move/resize.
        self._last_mouse_scene_pos = QPointF()
        self._raw_last_scene_pos = QPointF()
        self._shift_pressed = False
        self._update_cursor()

        # Use the default QWidget-based viewport for rasterized rendering
        self.scene = QGraphicsScene(self)
        self.scene.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.BspTreeIndex)
        self.setScene(self.scene)
        self.page_item = QGraphicsRectItem()
        self._initial_centered = False

        # Track items currently visible/hidden on the scene
        self._visible_items = set()
        self._hidden_items = set()

        # Throttle expensive visibility updates
        self._visible_update_timer = QTimer(self)
        self._visible_update_timer.setSingleShot(True)
        self._visible_update_timer.timeout.connect(self.update_visible_items)

        # Visual drop effect removed per request

        self.page_item.setZValue(-1)
        self.scene.addItem(self.page_item)

        # Object snapping configuration
        self.snap_to_objects = settings_service.get_value("snap_to_objects", True)
        self.snap_lines_visible = settings_service.get_value("snap_lines_visible", True)
        self._snap_lines = []

        # Preview styling for snap lines and selection rubber band
        self._update_preview_style()

        # Disable global antialiasing; enable per-item where needed
        self.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        # Use no automatic anchor; we'll manually keep the cursor's scene
        # point fixed during zoom for precise Photoshop-like behavior.
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setObjectName("DesignCanvas")
        self.setBackgroundBrush(QColor("#1f1f1f"))
        # Prefer minimal viewport updates for dynamic scenes
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)
        # Center the canvas within the viewport when it is smaller than
        # the view, like Photoshop's pasteboard behavior.
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.viewport().installEventFilter(self)

        self.scene.selectionChanged.connect(self._on_selection_changed)

        self.update_screen_data()

        style_data_service.styles_changed.connect(self._on_styles_changed)

        # Frame throttling (~60 fps)
        self._frame_timer = QElapsedTimer()
        self._frame_timer.start()
        
    def drawBackground(self, painter: QPainter, rect: QRectF):
        """Draw the scene background without grid lines."""
        super().drawBackground(painter, rect)

    # --- Utilities ---------------------------------------------------------
    def _remove_item_safely(self, item: QGraphicsItem | None):
        """Remove a QGraphicsItem from whichever scene owns it, if any.

        This prevents Qt warnings when attempting to remove an item from a
        different scene, or when the item has already been detached (scene is
        None).
        """
        if not item:
            return
        try:
            s = item.scene()
        except Exception:
            s = None
        if s is not None:
            try:
                s.removeItem(item)
            except Exception:
                # Swallow removal errors; item may be mid-destruction
                pass


    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.HoverMove:
            # Throttle hover computations
            if self._frame_timer.isValid() and self._frame_timer.elapsed() < 16:
                return False
            self._frame_timer.restart()
            pos = event.position().toPoint()
            self._last_mouse_scene_pos = self._snap_position(self.mapToScene(pos))
            if self.scene.selectedItems():
                handle = self.get_handle_at(pos)
                if handle:
                    self._set_cursor_for_handle(handle)
                else:
                    self.viewport().setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        elif event.type() == QEvent.Type.MouseMove and event.buttons() == Qt.MouseButton.NoButton:
            if self._frame_timer.isValid() and self._frame_timer.elapsed() < 16:
                return False
            self._frame_timer.restart()
            pos = event.pos()
            self._last_mouse_scene_pos = self._snap_position(self.mapToScene(pos))
            if self.scene.selectedItems():
                handle = self.get_handle_at(pos)
                if handle:
                    self._set_cursor_for_handle(handle)
                else:
                    self.viewport().setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        return False


    def _update_preview_style(self):
        """Set preview pen and color used for snap lines and rubber-band."""
        self._preview_color = QColor("#ff00a7")
        self._preview_pen = QPen(self._preview_color, 0, Qt.PenStyle.DashLine)


    def _update_cursor(self):
        if self.active_tool == constants.ToolType.SELECT:
            self.viewport().setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        else:
            self.viewport().setCursor(QCursor(Qt.CursorShape.CrossCursor))

    def _snap_position(self, pos: QPointF) -> QPointF:
        self._snap_lines.clear()
        snapped = QPointF(pos.x(), pos.y())
        if self.snap_to_objects:
            snapped = self._snap_to_objects(snapped)
        if self.snap_lines_visible:
            self.viewport().update()
        return snapped

    def _snap_to_objects(self, pos: QPointF) -> QPointF:
        threshold = 5 / self.transform().m11()
        page_rect = self.page_item.rect()
        snap_x = pos.x()
        snap_y = pos.y()
        best_dx = threshold
        best_dy = threshold
        snap_line_x = None
        snap_line_y = None

        for item in self.scene.items():
            if item is self.page_item or item in self.scene.selectedItems():
                continue
            rect = item.sceneBoundingRect()
            for x_val in (rect.left(), rect.center().x(), rect.right()):
                dx = abs(pos.x() - x_val)
                if dx < best_dx:
                    best_dx = dx
                    snap_x = x_val
                    snap_line_x = QLineF(x_val, page_rect.top(), x_val, page_rect.bottom())
            for y_val in (rect.top(), rect.center().y(), rect.bottom()):
                dy = abs(pos.y() - y_val)
                if dy < best_dy:
                    best_dy = dy
                    snap_y = y_val
                    snap_line_y = QLineF(page_rect.left(), y_val, page_rect.right(), y_val)

        if self.snap_lines_visible:
            self._snap_lines.clear()
            if snap_line_x:
                self._snap_lines.append(snap_line_x)
            if snap_line_y:
                self._snap_lines.append(snap_line_y)
        return QPointF(snap_x, snap_y)

    def set_snap_to_objects(self, enabled: bool):
        self.snap_to_objects = enabled

    def set_snap_lines_visible(self, visible: bool):
        self.snap_lines_visible = visible
        if not visible:
            self._snap_lines.clear()
            self.viewport().update()

    def update_visible_items(self):
        """Show or hide items based on their intersection with the viewport."""
        scene_rect = self.mapToScene(self.viewport().rect()).boundingRect()

        # Items intersecting the current viewport.  Use all scene items so
        # previously hidden ones can be restored when they re-enter.
        visible_now = {
            item
            for item in self.scene.items()
            if item.sceneBoundingRect().intersects(scene_rect)
        }

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
        # Start the timer only if not already active so updates fire regularly
        # even during continuous scrolling or zooming, preventing items from
        # remaining hidden until movement stops.
        if not self._visible_update_timer.isActive():
            self._visible_update_timer.start(16)

    def drawForeground(self, painter: QPainter, rect):
        super().drawForeground(painter, rect)
        if self.snap_lines_visible and self._snap_lines:
            painter.save()
            painter.setPen(self._preview_pen)
            painter.drawLines(self._snap_lines)
            painter.restore()

        if self._drag_mode == 'rubberband':
            painter.save()
            painter.resetTransform()
            painter.setPen(self._preview_pen)
            painter.setBrush(QColor(self._preview_color.red(), self._preview_color.green(), self._preview_color.blue(), 30))
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

    def _set_cursor_for_handle(self, handle: str):
        """Set the appropriate cursor based on the resize handle."""
        if handle in {"top_left", "bottom_right"}:
            self.viewport().setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
        elif handle in {"top_right", "bottom_left"}:
            self.viewport().setCursor(QCursor(Qt.CursorShape.SizeBDiagCursor))
        elif handle in {"top", "bottom"}:
            self.viewport().setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
        elif handle in {"left", "right"}:
            self.viewport().setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
        else:
            self.viewport().setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._schedule_visible_items_update()

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        self._schedule_visible_items_update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.active_tool != constants.ToolType.SELECT:
            scene_pos = self._snap_position(self.mapToScene(event.pos()))
            if self.active_tool == constants.ToolType.BUTTON:
                default_props = button_tool.get_default_properties()
                pos_x = int(scene_pos.x() - default_props['size']['width'] / 2)
                pos_y = int(scene_pos.y() - default_props['size']['height'] / 2)
                default_props["position"] = {"x": pos_x, "y": pos_y}
                self._add_tool_item(constants.ToolType.BUTTON, default_props)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            # Cache both raw and snapped cursor positions at the start of a drag
            self._raw_last_scene_pos = self.mapToScene(event.pos())
            self._last_mouse_scene_pos = self._snap_position(self._raw_last_scene_pos)
            
            # Priority 1: Check for resize handle click
            self._resize_handle = self.get_handle_at(event.pos())
            if self._resize_handle:
                self._drag_mode = 'resize'
                self._set_cursor_for_handle(self._resize_handle)
                self._start_selection_states.clear()
                for item in self.scene.selectedItems():
                    if isinstance(item, BaseGraphicsItem):
                        self._start_selection_states[item.get_instance_id()] = {
                            'rect': item.sceneBoundingRect(),
                            'properties': copy.deepcopy(item.instance_data.get('properties', {}))
                        }
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
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        raw_scene_pos = self.mapToScene(event.pos())
        snapped_scene_pos = self._snap_position(raw_scene_pos)

        if self._frame_timer.isValid() and self._frame_timer.elapsed() < 16:
            self.mouse_moved_on_scene.emit(snapped_scene_pos)
            return

        self._frame_timer.restart()
        self.mouse_moved_on_scene.emit(snapped_scene_pos)

        delta = raw_scene_pos - self._raw_last_scene_pos

        if self._drag_mode == 'resize':
            self._perform_group_resize(delta)
            self._set_cursor_for_handle(self._resize_handle)
        elif self._drag_mode == 'move':
            self._perform_group_move(delta)
        elif self._drag_mode == 'rubberband':
            self._rubber_band_rect.setBottomRight(event.pos())
            self.viewport().update()
        else:
            if self.scene.selectedItems():
                handle = self.get_handle_at(event.pos())
                if handle:
                    self._set_cursor_for_handle(handle)
                else:
                    self.viewport().setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            else:
                self.viewport().setCursor(QCursor(Qt.CursorShape.ArrowCursor))

        self._raw_last_scene_pos = raw_scene_pos
        self._last_mouse_scene_pos = snapped_scene_pos


    def _perform_group_move(self, delta: QPointF):
        """Applies a move delta to all selected items and snaps the result."""
        for item in self.scene.selectedItems():
            if isinstance(item, BaseGraphicsItem):
                item.moveBy(delta.x(), delta.y())

        # Snap the whole group based on its bounding rect
        group_rect = self.get_group_bounding_rect()
        if group_rect:
            snapped_top_left = self._snap_position(group_rect.topLeft())
            offset = snapped_top_left - group_rect.topLeft()
            if offset.x() or offset.y():
                for item in self.scene.selectedItems():
                    if isinstance(item, BaseGraphicsItem):
                        item.moveBy(offset.x(), offset.y())

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
            props['size'] = {'width': new_width, 'height': new_height}
            item.update_data(item.instance_data)
            offset_rect = item.boundingRect()
            item.setPos(
                new_group_rect.left() + relative_x - offset_rect.left(),
                new_group_rect.top() + relative_y - offset_rect.top(),
            )

        # After resizing, snap the group's top-left corner
        group_rect = self.get_group_bounding_rect()
        if group_rect:
            snapped_top_left = self._snap_position(group_rect.topLeft())
            offset = snapped_top_left - group_rect.topLeft()
            if offset.x() or offset.y():
                for item in self.scene.selectedItems():
                    if isinstance(item, BaseGraphicsItem):
                        item.moveBy(offset.x(), offset.y())

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
                selection_data = [dict(first_item.instance_data)]
                self.selection_changed.emit(self.screen_id, selection_data)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._drag_mode == 'resize':
                update_list = []
                for item in self.scene.selectedItems():
                    if not isinstance(item, BaseGraphicsItem) or not getattr(item, "is_resizable", False):
                        continue
                    start_state = self._start_selection_states[item.get_instance_id()]
                    start_rect = start_state['rect'] if isinstance(start_state, dict) else start_state
                    base_props = start_state.get('properties', {}) if isinstance(start_state, dict) else {}
                    old_props = dict(base_props)
                    old_props['position'] = {'x': start_rect.x(), 'y': start_rect.y()}
                    old_props['size'] = {'width': start_rect.width(), 'height': start_rect.height()}
                    new_props = dict(item.instance_data['properties'])
                    new_props['position'] = {'x': item.pos().x(), 'y': item.pos().y()}
                    if old_props != new_props:
                        update_list.append((item.get_instance_id(), new_props, old_props))
                if update_list:
                    from services.commands import BulkUpdateChildPropertiesCommand
                    command = BulkUpdateChildPropertiesCommand(self.screen_id, update_list)
                    from services.command_history_service import command_history_service
                    command_history_service.add_command(command)
            elif self._drag_mode == 'move':
                move_list = []
                for item in self.scene.selectedItems():
                    if isinstance(item, BaseGraphicsItem):
                        start_pos = self._start_selection_states.get(item.get_instance_id())
                        if start_pos and start_pos != item.pos():
                            move_list.append((item.get_instance_id(), {'x': item.pos().x(), 'y': item.pos().y()}, {'x': start_pos.x(), 'y': start_pos.y()}))
                if move_list:
                    from services.commands import BulkMoveChildCommand
                    command = BulkMoveChildCommand(self.screen_id, move_list)
                    from services.command_history_service import command_history_service
                    command_history_service.add_command(command)
            elif self._drag_mode == 'rubberband':
                self.viewport().update()
                selection_path = QPainterPath()
                view_rect = self._rubber_band_rect.normalized()
                scene_path = self.mapToScene(view_rect)
                selection_path.addPolygon(scene_path)
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
            self._snap_lines.clear()
            self.viewport().update()
            self.viewport().setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        from PyQt6.QtWidgets import QApplication
        modifiers = QApplication.keyboardModifiers()

        # If Ctrl/Cmd is pressed, perform zoom; otherwise let it scroll.
        if modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier):
            # Determine scroll delta; prefer angleDelta for classic wheels,
            # fall back to pixelDelta for high-resolution touchpads.
            delta = event.angleDelta().y()
            if delta == 0:
                delta = event.pixelDelta().y()

            if delta == 0:
                super().wheelEvent(event)
                return

            # Photoshop-like: zoom towards the cursor, keeping the cursor's
            # scene position fixed in the viewport.
            # Use the actual cursor position mapped to the viewport to avoid any
            # discrepancies in event coordinates across platforms.
            mouse_view_pos = self.viewport().mapFromGlobal(QCursor.pos())
            scene_pos_before = self.mapToScene(mouse_view_pos)

            # Smooth exponential zoom factor; 120 units ~= one notch.
            zoom_factor = pow(1.0015, delta)

            # Clamp overall view scale to reasonable bounds
            current_scale = self.transform().m11()
            min_scale, max_scale = 0.1, 10.0
            target_scale = current_scale * zoom_factor
            if target_scale < min_scale:
                zoom_factor = min_scale / current_scale
            elif target_scale > max_scale:
                zoom_factor = max_scale / current_scale

            # Apply zoom uniformly
            self.scale(zoom_factor, zoom_factor)

            # Re-center so the scene point under the cursor stays under the cursor
            # Compute where the viewport center is in scene coords after scaling
            view_center_scene = self.mapToScene(self.viewport().rect().center())
            # Compute the offset required to move the center so that the mouse
            # position maps back to the original scene_pos_before
            delta_scene = scene_pos_before - self.mapToScene(mouse_view_pos)
            self.centerOn(view_center_scene + delta_scene)

            self._schedule_visible_items_update()
            # Notify listeners of the new zoom level
            self.zoom_changed.emit(self.transform().m11())
            event.accept()
        else:
            # Default scroll behavior for two-finger trackpad and mouse wheel
            super().wheelEvent(event)
        

    def update_screen_data(self):
        selected_ids = [
            item.instance_data.get('instance_id')
            for item in self.scene.selectedItems()
            if isinstance(item, BaseGraphicsItem)
        ]
        old_selection_ids = set(selected_ids)

        self.screen_data = screen_service.get_screen(self.screen_id)
        if not self.screen_data:
            self.scene.clear()
            self._item_map.clear()
            return

        size = self.screen_data.get('size', {'width': 1920, 'height': 1080})
        w = int(size.get('width', 1920))
        h = int(size.get('height', 1080))
        # Expand scene rect to include margins so outside area is visible
        # and pannable around the page (Photoshop-like pasteboard).
        pad = 1000
        self.scene.setSceneRect(-pad, -pad, w + 2 * pad, h + 2 * pad)

        style = self.screen_data.get('style', {})
        # The page fills only the actual page size at (0,0,w,h)
        self.page_item.setRect(QRectF(0, 0, w, h))
        self.page_item.setPen(QPen(Qt.PenStyle.NoPen))

        if style.get('transparent', False):
            self.page_item.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        else:
            color = style.get('color1', "#FFFFFF")
            self.page_item.setBrush(QBrush(QColor(color)))

        self.scene.blockSignals(True)
        self._sync_scene_items()
        for inst_id in selected_ids:
            item = self._item_map.get(inst_id)
            if item:
                item.setSelected(True)
        # Determine if the selection actually changed as a result of sync
        new_selection_ids = {
            it.instance_data.get('instance_id')
            for it in self.scene.selectedItems()
            if isinstance(it, BaseGraphicsItem)
        }
        self.scene.blockSignals(False)
        if new_selection_ids != old_selection_ids:
            self._on_selection_changed()
        # Center the view on the page center once on first load so the
        # page appears centered within the padded scene.
        if not self._initial_centered:
            self.centerOn(QPointF(w / 2, h / 2))
            self._initial_centered = True
        self.update()
        self.update_visible_items()

    def _on_styles_changed(self, style_id: str):
        if not self.screen_data:
            return
        from tools.button import conditional_style as button_styles
        changed = False
        for child in self.screen_data.get('children', []):
            if child.get('tool_type') != constants.ToolType.BUTTON:
                continue
            props = child.get('properties', {})
            sid = props.get('style_id')
            if style_id and sid != style_id:
                continue
            style_def = button_styles.get_style_by_id(sid)
            if not style_def:
                continue
            props.update(copy.deepcopy(style_def.get('properties', {})))
            if 'hover_properties' in style_def:
                props['hover_properties'] = copy.deepcopy(style_def['hover_properties'])
            else:
                props.pop('hover_properties', None)
            if style_def.get('icon'):
                props['icon'] = style_def['icon']
            else:
                props.pop('icon', None)
            if style_def.get('hover_icon'):
                props['hover_icon'] = style_def['hover_icon']
            else:
                props.pop('hover_icon', None)
            item = self._item_map.get(child.get('instance_id'))
            if item:
                item.update_data(copy.deepcopy(child))
            changed = True
        if changed:
            self.update()

    def apply_default_colors(self):
        """Apply a fixed palette to the canvas."""
        self.setBackgroundBrush(QColor("#1e1e1e"))
        if not self.screen_data.get('style', {}).get('transparent', False):
            self.page_item.setBrush(QColor("#252526"))
        self._update_preview_style()
        self.update()

    def _sync_scene_items(self):
        children_list = self.screen_data.get('children', [])
        current_instance_ids = {item_data['instance_id'] for item_data in children_list}
        for instance_id, item in list(self._item_map.items()):
            if instance_id not in current_instance_ids:
                self._remove_item_safely(item)
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
            if t == constants.ToolType.BUTTON:
                item = ButtonItem(data_copy)
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
                instance_id = item.get_instance_id()
                if instance_id is None:
                    continue
                data = dict(item.instance_data)
                selection_data.append(data)

    def set_active_tool(self, tool_name):
        self.active_tool = constants.tool_type_from_str(tool_name) or tool_name
        if self.active_tool != constants.ToolType.SELECT:
            self.clear_selection()
        self._update_cursor()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        item = self.itemAt(event.pos())
        if isinstance(item, ButtonItem):
            self._open_button_properties(item.instance_data)
        else:
            super().mouseDoubleClickEvent(event)
    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        if not isinstance(item, BaseGraphicsItem):
            menu = QMenu(self)
            paste_anim = IconManager.create_animated_icon('fa5s.paste')
            paste_action = menu.addAction(paste_anim.icon, "Paste")
            paste_anim.add_target(paste_action)
            paste_action._animated_icon = paste_anim
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
        cut_anim = IconManager.create_animated_icon('fa5s.cut')
        cut_action = menu.addAction(cut_anim.icon, "Cut")
        cut_anim.add_target(cut_action)
        cut_action._animated_icon = cut_anim
        copy_anim = IconManager.create_animated_icon('fa5s.copy')
        copy_action = menu.addAction(copy_anim.icon, "Copy")
        copy_anim.add_target(copy_action)
        copy_action._animated_icon = copy_anim
        duplicate_action = menu.addAction("Duplicate")
        delete_anim = IconManager.create_animated_icon('fa5s.trash-alt')
        delete_action = menu.addAction(delete_anim.icon, "Delete")
        delete_anim.add_target(delete_action)
        delete_action._animated_icon = delete_anim
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
                open_anim = IconManager.create_animated_icon('fa5s.external-link-alt')
                open_action = menu.addAction(open_anim.icon, "Open Base Screen")
                open_anim.add_target(open_action)
                open_action._animated_icon = open_anim
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
        from tools.button.button_properties_dialog import ButtonPropertiesDialog
        
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
                button_instance_data['properties'] = new_properties
                if item:
                    item.update_data({
                        'instance_id': button_instance_data['instance_id'],
                        'properties': new_properties,
                    })
                    item.update()
                self.scene.update()
                self.viewport().update()
        
        # Ensure item position is restored and scene is updated
        if item and original_pos:
            item.setPos(original_pos)
            self.scene.update()
            self.viewport().update()
