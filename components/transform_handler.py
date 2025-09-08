from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPen, QBrush, QCursor, QPainter
from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsItem


class HandleItem(QGraphicsRectItem):
    """Small square handle used for resizing/rotating."""

    cursor_map = {
        "top_left": Qt.CursorShape.SizeFDiagCursor,
        "top_right": Qt.CursorShape.SizeBDiagCursor,
        "bottom_left": Qt.CursorShape.SizeBDiagCursor,
        "bottom_right": Qt.CursorShape.SizeFDiagCursor,
        "top": Qt.CursorShape.SizeVerCursor,
        "bottom": Qt.CursorShape.SizeVerCursor,
        "left": Qt.CursorShape.SizeHorCursor,
        "right": Qt.CursorShape.SizeHorCursor,
    }

    def __init__(self, role: str, size: float, parent: QGraphicsItem):
        super().__init__(-size / 2, -size / 2, size, size, parent)
        self.role = role
        pen = QPen(QColor("#2c313c"), 1)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setBrush(QBrush(QColor("#ffffff")))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        self.setAcceptHoverEvents(True)
        cursor = self.cursor_map.get(role, Qt.CursorShape.ArrowCursor)
        self.setCursor(QCursor(cursor))


class TransformHandler(QGraphicsRectItem):
    """Dynamic selection box with resize handles."""

    def __init__(self, parent: QGraphicsItem | None = None):
        super().__init__(parent)
        pen = QPen(QColor("#528bff"), 2)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.setZValue(1000)
        self.handle_size = 8
        self._targets: list[QGraphicsItem] = []
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self._create_handles()
        self.hide()

    # ------------------------------------------------------------------
    def _create_handles(self):
        roles = [
            "top_left",
            "top_right",
            "bottom_left",
            "bottom_right",
            "top",
            "bottom",
            "left",
            "right",
        ]
        self.handles: dict[str, HandleItem] = {}
        for role in roles:
            self.handles[role] = HandleItem(role, self.handle_size, self)

    # ------------------------------------------------------------------
    def set_targets(self, items: list[QGraphicsItem]):
        # Disconnect previous signals
        for t in self._targets:
            for sig in ("xChanged", "yChanged", "rotationChanged", "scaleChanged"):
                try:
                    getattr(t, sig).disconnect(self.update_geometry)
                except Exception:
                    pass
        self._targets = [i for i in items if i is not None]
        if not self._targets:
            self.hide()
            return
        for t in self._targets:
            for sig in ("xChanged", "yChanged", "rotationChanged", "scaleChanged"):
                try:
                    getattr(t, sig).connect(self.update_geometry)
                except Exception:
                    pass
        self.update_geometry()
        self.show()

    # ------------------------------------------------------------------
    def update_geometry(self):
        if not self._targets:
            self.hide()
            return
        rect = None
        for item in self._targets:
            r = item.sceneBoundingRect()
            rect = r if rect is None else rect.united(r)
        if rect is None:
            self.hide()
            return
        w, h = rect.width(), rect.height()
        pad = self.handle_size
        self.prepareGeometryChange()
        # Expand the handler's own rect to include the resize handles so they
        # are visible immediately when the handler first appears.
        self.setPos(rect.topLeft())
        self.setRect(-pad / 2, -pad / 2, w + pad, h + pad)
        self._position_handles(w, h)
        for handle in self.handles.values():
            handle.show()
        self.show()

    # ------------------------------------------------------------------
    def _position_handles(self, w: float, h: float):
        self.handles["top_left"].setPos(0, 0)
        self.handles["top_right"].setPos(w, 0)
        self.handles["bottom_left"].setPos(0, h)
        self.handles["bottom_right"].setPos(w, h)
        self.handles["top"].setPos(w / 2, 0)
        self.handles["bottom"].setPos(w / 2, h)
        self.handles["left"].setPos(0, h / 2)
        self.handles["right"].setPos(w, h / 2)

    # ------------------------------------------------------------------
    def paint(self, painter: QPainter, option, widget=None):
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        pad = self.handle_size / 2
        # Draw the visual rectangle inside the expanded bounding rect so the
        # outline hugs the targets while still keeping the handles within the
        # item's bounding region.
        inner = self.rect().adjusted(pad, pad, -pad, -pad)
        painter.drawRect(inner)
