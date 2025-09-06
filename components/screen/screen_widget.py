# components/screen/screen_widget.py
# MODIFIED: Removed zoom-related signals and helpers.

from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import pyqtSignal, pyqtSlot, QPointF
from services.screen_data_service import screen_service
from services.data_context import data_context
from .design_canvas import DesignCanvas

class ScreenWidget(QWidget):
    """
    Container widget for a DesignCanvas.
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.design_canvas = DesignCanvas(screen_id, self)
        layout.addWidget(self.design_canvas)
        
        # Forward canvas signals explicitly via this widget's signals
        self.design_canvas.selection_changed.connect(self.selection_changed.emit)
        self.design_canvas.open_screen_requested.connect(self.open_screen_requested.emit)
        self.design_canvas.mouse_moved_on_scene.connect(self.mouse_moved_on_scene.emit)
        self.design_canvas.mouse_left_scene.connect(self.mouse_left_scene.emit)
        self.design_canvas.selection_dragged.connect(self.selection_dragged.emit)
        self.design_canvas.zoom_changed.connect(self.zoom_changed.emit)

        data_context.screens_changed.connect(
            lambda evt: self.on_screen_modified(evt.get("screen_id", ""))
            if evt.get("action") == "screen_modified"
            else None
        )

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

    # Zoom helpers removed per request

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

    # Zoom controls removed per request
