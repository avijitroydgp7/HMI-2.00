from __future__ import annotations

from typing import Optional
import os

from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, pyqtProperty, Qt, QSize, QPoint
from PyQt6.QtWidgets import QPushButton, QLabel
from PyQt6.QtGui import QColor, QPixmap, QIcon, QPainter, QBrush
from PyQt6.QtSvg import QSvgRenderer

from utils.icon_manager import IconManager
from utils.dpi import dpi_scale


class SwitchButton(QPushButton):
    """A custom toggle switch used for previewing switch styles."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 100)

        self._handle_x_pos = 0
        self._handle_radius = 0
        self._margin = 0
        self._on_pos = 0
        self._off_pos = 0

        self.animation = QPropertyAnimation(self, b"handle_x_pos", self)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.setDuration(200)

        self._handle_color = QColor("white")
        self._on_is_left = False  # Default: 'on' state is on the right

        # Set initial state based on default alignment without animation
        self.set_alignment(False)

    @pyqtProperty(int)
    def handle_x_pos(self):
        return self._handle_x_pos

    @handle_x_pos.setter
    def handle_x_pos(self, pos):
        self._handle_x_pos = pos
        self.update()

    def _update_geometry(self):
        """Recalculate handle size and positions based on current widget size."""
        prev_on = getattr(self, "_on_pos", None)
        prev_off = getattr(self, "_off_pos", None)
        progress = 0.0
        if prev_on is not None and prev_off is not None and prev_on != prev_off:
            progress = (self._handle_x_pos - prev_off) / (prev_on - prev_off)
        # scale handle size based on height (with 10% margins)
        self._handle_radius = int(self.height() * 0.4)
        self._margin = int(self.height() * 0.1)
        left = self._margin + self._handle_radius
        right = self.width() - self._margin - self._handle_radius
        if self._on_is_left:
            self._on_pos, self._off_pos = left, right
        else:
            self._on_pos, self._off_pos = right, left
        # keep previous relative position if possible
        self.handle_x_pos = int(self._off_pos + progress * (self._on_pos - self._off_pos))

    def set_alignment(self, on_is_left):
        """Sets the toggle direction and initial state."""
        self._on_is_left = on_is_left
        self._update_geometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_geometry()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        brush = QBrush(self._handle_color)
        painter.setBrush(brush)
        painter.setPen(Qt.PenStyle.NoPen)

        handle_y = self.height() / 2
        handle_center = QPoint(self.handle_x_pos, int(handle_y))
        painter.drawEllipse(handle_center, self._handle_radius, self._handle_radius)

    def mousePressEvent(self, e):
        self.animation.setEndValue(self._on_pos)
        self.animation.start()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self.animation.setEndValue(self._off_pos)
        self.animation.start()
        super().mouseReleaseEvent(e)


class IconButton(QPushButton):
    """Button capable of displaying SVG or QtAwesome icons for previewing styles."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._icon_label = QLabel(self)
        self._icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._icon_label.setStyleSheet("background: transparent;")
        self._base_pixmap = QPixmap()
        self._hover_pixmap = QPixmap()
        self._current_source = ""
        self._hover_source = ""
        self._icon_color: Optional[str] = None
        self._icon_alignment = "center"
        self.icon_size = QSize(dpi_scale(50), dpi_scale(50))

    def set_icon(self, source: str, color: Optional[str] = None):
        self._current_source = source or ""
        self._icon_color = color
        self._base_pixmap = self._create_pixmap_from_source(source, color)
        self._icon_label.setPixmap(self._base_pixmap)
        self._update_icon_geometry()

    def set_hover_icon(self, source: str, color: Optional[str] = None):
        self._hover_source = source or ""
        col = color if color is not None else self._icon_color
        self._hover_pixmap = self._create_pixmap_from_source(source, col)

    def set_icon_size(self, size: int):
        self.icon_size = QSize(size, size)
        if self._current_source:
            self._base_pixmap = self._create_pixmap_from_source(
                self._current_source, self._icon_color
            )
            self._icon_label.setPixmap(self._base_pixmap)
        if self._hover_source:
            self._hover_pixmap = self._create_pixmap_from_source(
                self._hover_source, self._icon_color
            )
        self._update_icon_geometry()

    def set_icon_alignment(self, alignment: str):
        self._icon_alignment = alignment or "center"
        self._update_icon_geometry()

    def _create_pixmap_from_source(
        self, source: Optional[str], color: Optional[str] = None
    ) -> QPixmap:
        if not source:
            return QPixmap()
        src = str(source)
        if src.startswith("qta:"):
            name = src.split(":", 1)[1]
            return IconManager.create_pixmap(name, self.icon_size.width(), color=color)
        ext = os.path.splitext(src)[1].lower()
        if ext == ".svg":
            renderer = QSvgRenderer(src)
            if renderer.isValid():
                pixmap = QPixmap(self.icon_size)
                pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(pixmap)
                renderer.render(painter)
                painter.end()
                return pixmap
            return QPixmap()
        pix = QPixmap(src)
        if pix and not pix.isNull():
            return pix.scaled(
                self.icon_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
        return QPixmap()

    def _update_icon_geometry(self):
        pix = self._icon_label.pixmap()
        if pix is None or pix.isNull():
            self._icon_label.setGeometry(0, 0, 0, 0)
            return
        w = pix.width()
        h = pix.height()
        x = (self.width() - w) // 2
        y = (self.height() - h) // 2
        align = self._icon_alignment
        if "left" in align:
            x = 0
        elif "right" in align:
            x = self.width() - w
        if "top" in align:
            y = 0
        elif "bottom" in align:
            y = self.height() - h
        self._icon_label.setGeometry(x, y, w, h)
        self._icon_label.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_icon_geometry()

    def enterEvent(self, e):
        if not self._hover_pixmap.isNull():
            self._icon_label.setPixmap(self._hover_pixmap)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._icon_label.setPixmap(self._base_pixmap)
        super().leaveEvent(e)


class PreviewButton(IconButton):
    """Preview button that relies on style sheets for rendering."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        # QLabel to handle text so we can control alignment
        self._text_label = QLabel(self)
        self._text_label.setStyleSheet("background: transparent;")
        self._text_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text_label.raise_()
        self._base_text_color = ""
        self._hover_text_color = ""
        self._offset = 0
        self.setText(text)

    def resizeEvent(self, event):  # pragma: no cover - GUI behaviour
        super().resizeEvent(event)
        self._update_label_geometry()

    # Reimplemented to route through the internal label
    def setText(self, text: str):  # pragma: no cover - GUI behaviour
        self._text_label.setText(text)

    def text(self) -> str:  # pragma: no cover - GUI behaviour
        return self._text_label.text()

    def setAlignment(self, alignment):  # pragma: no cover - GUI behaviour
        """Allow external callers to align the preview text."""
        self._text_label.setAlignment(alignment)

    # ------------------------------------------------------------------
    # Text font/offset handling
    # ------------------------------------------------------------------
    def set_text_font(
        self,
        family: str,
        size: int,
        bold: bool,
        italic: bool,
        underline: bool,
    ) -> None:
        """Apply font properties to the internal label."""
        font = self._text_label.font()
        if family:
            font.setFamily(family)
        if size > 0:
            font.setPointSize(size)
        font.setBold(bold)
        font.setItalic(italic)
        font.setUnderline(underline)
        self._text_label.setFont(font)

    def set_text_offset(self, offset: int) -> None:
        """Offset the text label from the button frame."""
        self._offset = offset
        self._update_label_geometry()

    def _update_label_geometry(self) -> None:
        rect = self.rect().adjusted(
            self._offset,
            self._offset,
            -self._offset,
            -self._offset,
        )
        self._text_label.setGeometry(rect)

    # ------------------------------------------------------------------
    # Text colour handling
    # ------------------------------------------------------------------
    def set_text_colors(self, base: str, hover: str) -> None:
        """Set the base and hover text colours for the preview label."""
        self._base_text_color = base or ""
        self._hover_text_color = hover or base or ""
        self._apply_text_color(self._base_text_color)

    def _apply_text_color(self, color: str) -> None:
        self._text_label.setStyleSheet(
            f"background: transparent; color: {color};"
        )

    def enterEvent(self, event):  # pragma: no cover - GUI behaviour
        if self._hover_text_color:
            self._apply_text_color(self._hover_text_color)
        super().enterEvent(event)

    def leaveEvent(self, event):  # pragma: no cover - GUI behaviour
        if self._base_text_color:
            self._apply_text_color(self._base_text_color)
        super().leaveEvent(event)
