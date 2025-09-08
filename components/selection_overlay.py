# components/selection_overlay.py
# Can draw different styles for group vs. individual selection.

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush

class SelectionOverlay:
    """
    Handles the drawing of a selection box with transform handles.
    This is a drawing utility, not a QWidget itself.
    """
    def __init__(self):
        self.handle_size = 8
        self.handle_color = QColor("#ffffff")
        
        self.border_pen = QPen(QColor("#528bff"), 2, Qt.PenStyle.SolidLine)
        self.border_pen.setCosmetic(True)
        
        self.handle_pen = QPen(QColor("#2c313c"), 1)
        self.handle_pen.setCosmetic(True)

        # Pen for individual item outlines in a group selection.
        self.individual_pen = QPen(QColor(82, 139, 255, 150), 1.5, Qt.PenStyle.DotLine)
        self.individual_pen.setCosmetic(True)

    def paint(self, painter: QPainter, target_rect: QRectF, view_scale: float, draw_handles: bool = True):
        """
        Draws the selection border and handles around the target rectangle.
        """
        if not target_rect:
            return

        # Use the appropriate pen based on whether it's a group or individual box
        if draw_handles:
            painter.setPen(self.border_pen)
        else:
            painter.setPen(self.individual_pen)
        
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(target_rect)

        # Only draw handles for the main group selection box
        if not draw_handles:
            return

        painter.setPen(self.handle_pen)
        painter.setBrush(QBrush(self.handle_color))
        
        handle_draw_size = self.handle_size / view_scale
        half_handle = handle_draw_size / 2

        handles = [
            QRectF(target_rect.left() - half_handle, target_rect.top() - half_handle, handle_draw_size, handle_draw_size),
            QRectF(target_rect.right() - half_handle, target_rect.top() - half_handle, handle_draw_size, handle_draw_size),
            QRectF(target_rect.left() - half_handle, target_rect.bottom() - half_handle, handle_draw_size, handle_draw_size),
            QRectF(target_rect.right() - half_handle, target_rect.bottom() - half_handle, handle_draw_size, handle_draw_size),
            QRectF(target_rect.center().x() - half_handle, target_rect.top() - half_handle, handle_draw_size, handle_draw_size),
            QRectF(target_rect.center().x() - half_handle, target_rect.bottom() - half_handle, handle_draw_size, handle_draw_size),
            QRectF(target_rect.left() - half_handle, target_rect.center().y() - half_handle, handle_draw_size, handle_draw_size),
            QRectF(target_rect.right() - half_handle, target_rect.center().y() - half_handle, handle_draw_size, handle_draw_size),
        ]
        
        for handle in handles:
            painter.drawRect(handle)
