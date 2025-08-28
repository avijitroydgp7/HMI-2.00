# components/screen/screen_widget.py
# MODIFIED: Connected to the new view_zoomed signal.

from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import pyqtSignal, pyqtSlot, QPointF
from PyQt6.QtGui import QCursor
from services.screen_data_service import screen_service
from .design_canvas import DesignCanvas

class ScreenWidget(QWidget):
    """
    Container widget for a DesignCanvas.
    """
    selection_changed = pyqtSignal(str, object)
    open_screen_requested = pyqtSignal(str)
    zoom_changed = pyqtSignal(str)
    
    mouse_moved_on_scene = pyqtSignal(QPointF)
    mouse_left_scene = pyqtSignal()
    selection_dragged = pyqtSignal(dict)

    def __init__(self, screen_id, parent=None):
        super().__init__(parent)
        self.screen_id = screen_id
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.design_canvas = DesignCanvas(screen_id, self)
        layout.addWidget(self.design_canvas)
        
        self.design_canvas.selection_changed.connect(self.selection_changed)
        self.design_canvas.open_screen_requested.connect(self.open_screen_requested)
        self.design_canvas.mouse_moved_on_scene.connect(self.mouse_moved_on_scene)
        self.design_canvas.mouse_left_scene.connect(self.mouse_left_scene)
        self.design_canvas.selection_dragged.connect(self.selection_dragged)
        # MODIFIED: Connect the new signal to the existing one.
        self.design_canvas.view_zoomed.connect(self.zoom_changed)

        screen_service.screen_modified.connect(self.on_screen_modified)

    def set_active_tool(self, tool_name: str):
        self.design_canvas.set_active_tool(tool_name)

    @pyqtSlot(str)
    def on_screen_modified(self, modified_screen_id: str):
        if self.screen_id == modified_screen_id:
            self.update_screen_data()
            return

        if self.design_canvas.screen_data:
            children_ids = {
                child.get('screen_id')
                for child in self.design_canvas.screen_data.get('children', [])
                if 'screen_id' in child
            }
            if modified_screen_id in children_ids:
                self.update_screen_data()

    @pyqtSlot()
    def update_screen_data(self):
        new_data = screen_service.get_screen(self.screen_id)
        if new_data:
            self.design_canvas.update_screen_data()
        else:
            self.layout().removeWidget(self.design_canvas)
            self.design_canvas.deleteLater()
            self.layout().addWidget(QLabel("Screen has been deleted."))

    def get_zoom_percentage(self):
        return f"{int(self.design_canvas.current_zoom * 100)}%"

    def has_selection(self):
        return self.design_canvas.has_selection()

    def copy_selected(self):
        self.design_canvas.copy_selected()

    def cut_selected(self):
        self.design_canvas.cut_selected()

    def paste(self):
        self.design_canvas.paste()

    def refresh_selection_status(self):
        self.design_canvas._on_selection_changed()

    def clear_selection(self):
        self.design_canvas.clear_selection()

    def zoom_in(self):
        new_zoom = min(self.design_canvas.current_zoom * 1.25, self.design_canvas.max_zoom)
        factor = new_zoom / self.design_canvas.current_zoom
        if factor != 1.0:
            mouse_view_pos = self.design_canvas.mapFromGlobal(QCursor.pos())
            if self.design_canvas.viewport().rect().contains(mouse_view_pos):
                scene_pos = self.design_canvas.mapToScene(mouse_view_pos)
            else:
                scene_pos = self.design_canvas._last_mouse_scene_pos
            view_pt = self.design_canvas.mapFromScene(scene_pos)
            if not self.design_canvas.viewport().rect().contains(view_pt):
                scene_pos = self.design_canvas.mapToScene(self.design_canvas.viewport().rect().center())
                view_pt = self.design_canvas.mapFromScene(scene_pos)
            self.design_canvas.scale(factor, factor)
            new_scene_pos = self.design_canvas.mapToScene(view_pt)
            delta = scene_pos - new_scene_pos
            self.design_canvas.translate(delta.x(), delta.y())
        self.design_canvas.current_zoom = new_zoom
        self.design_canvas._update_shadow_for_zoom()
        self.design_canvas.update_visible_items()
        self.zoom_changed.emit(self.get_zoom_percentage())

    def zoom_out(self):
        new_zoom = max(self.design_canvas.current_zoom * 0.8, self.design_canvas.min_zoom)
        factor = new_zoom / self.design_canvas.current_zoom
        if factor != 1.0:
            mouse_view_pos = self.design_canvas.mapFromGlobal(QCursor.pos())
            if self.design_canvas.viewport().rect().contains(mouse_view_pos):
                scene_pos = self.design_canvas.mapToScene(mouse_view_pos)
            else:
                scene_pos = self.design_canvas._last_mouse_scene_pos
            view_pt = self.design_canvas.mapFromScene(scene_pos)
            if not self.design_canvas.viewport().rect().contains(view_pt):
                scene_pos = self.design_canvas.mapToScene(self.design_canvas.viewport().rect().center())
                view_pt = self.design_canvas.mapFromScene(scene_pos)
            self.design_canvas.scale(factor, factor)
            new_scene_pos = self.design_canvas.mapToScene(view_pt)
            delta = scene_pos - new_scene_pos
            self.design_canvas.translate(delta.x(), delta.y())
        self.design_canvas.current_zoom = new_zoom
        self.design_canvas._update_shadow_for_zoom()
        self.design_canvas.update_visible_items()
        self.zoom_changed.emit(self.get_zoom_percentage())
