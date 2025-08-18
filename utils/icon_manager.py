from typing import List, Optional, Any
from PyQt6.QtCore import QObject
from PyQt6.QtGui import QIcon, QPixmap, QMovie
import qtawesome as qta

class IconManager:
    """
    Centralized manager for creating and converting icons in the application.
    Handles compatibility between PySide6 and PyQt6 icon types with a fixed color scheme.
    """

    @staticmethod
    def create_icon(icon_name: str, color: Optional[str] = None, active_color: Optional[str] = None, size: Optional[int] = None):
        """
        Create a PyQt6 QIcon from a qtawesome icon name using a fixed color scheme.

        Args:
            icon_name (str): The qtawesome icon name (e.g., 'fa5s.file').
            color (str, optional): The color of the icon. Defaults to the standard icon color.
            active_color (str, optional): The color of the icon when active. Defaults to the standard active color.
            size (int, optional): The size of the icon in pixels. If None, returns a scalable icon.

        Returns:
            QIcon: A PyQt6-compatible QIcon.
        """
        try:
            base_color = color if color is not None else "#DADADA"
            selected_color = active_color if active_color is not None else "#DADADA"

            
            # Use different colors for normal and selected states
            qta_icon = qta.icon(
                icon_name,
                color=base_color,
                color_active=selected_color,
                color_selected=selected_color
            )
            
            if qta_icon is None:
                return QIcon()

            if size is None:
                return qta_icon
                
            pixmap = qta_icon.pixmap(size, size)
            return QIcon(pixmap)
            
        except Exception as e:
            print(f"Error creating icon {icon_name}: {str(e)}")
            return QIcon()

    @staticmethod
    def create_pixmap(icon_name: str, size: int, color: Optional[str] = None):
        """
        Create a PyQt6 QPixmap from a qtawesome icon name with a fixed color.

        Args:
            icon_name (str): The qtawesome icon name.
            size (int): The size of the pixmap in pixels.
            color (str, optional): The color of the icon. Defaults to the standard icon color.

        Returns:
            QPixmap: A PyQt6-compatible QPixmap.
        """
        try:
            base_color = color if color is not None else "#FFFFFF"

            
            qta_icon = qta.icon(icon_name, color=base_color)

            if qta_icon is None:
                return QPixmap()

            return qta_icon.pixmap(size, size)
            
        except Exception as e:
            print(f"Error creating pixmap {icon_name}: {str(e)}")
            return QPixmap()

    @staticmethod
    def convert_to_pyqt_icon(icon) -> QIcon:
        """
        Convert any icon type to a PyQt6-compatible QIcon.
        """
        try:
            if isinstance(icon, QIcon):
                return icon
            if isinstance(icon, QPixmap):
                return QIcon(icon)
            if hasattr(icon, 'pixmap'):
                pixmap = icon.pixmap(icon.actualSize())
                return QIcon(pixmap)
            return QIcon(icon)
        except Exception as e:
            print(f"Error converting icon: {str(e)}")
            return QIcon()

    @staticmethod
    def create_animated_icon(path: str):
        """Create an animated icon from a GIF or APNG file.

        The returned :class:`AnimatedIcon` manages a :class:`QMovie` and
        automatically updates assigned widgets or actions as the animation
        progresses. If the environment lacks animation support or the file
        cannot be loaded, a static icon is used instead.

        Args:
            path (str): Path to the GIF or APNG file.

        Returns:
            AnimatedIcon: Helper object that keeps the animation running and
            updates any registered targets.

        Example:
            >>> spinner = IconManager.create_animated_icon("spinner.gif")
            >>> spinner.add_target(my_button)

        """
        movie = QMovie(path)
        if not movie.isValid():
            # Fallback to a static icon when animation isn't supported
            return AnimatedIcon(None, QIcon(path))

        movie.jumpToFrame(0)
        return AnimatedIcon(movie, QIcon(movie.currentPixmap()))


class AnimatedIcon(QObject):
    """Helper to apply animated icons to Qt widgets and actions.

    Widgets or actions added via :meth:`add_target` will have their icon
    updated each time the underlying ``QMovie`` advances. When no valid movie
    is supplied the icon remains static, providing a graceful fallback on
    platforms without animation support.
    """

    def __init__(self, movie: Optional[QMovie], icon: QIcon):
        super().__init__()
        self._movie = movie
        self._icon = icon
        self._targets: List[Any] = []

        if self._movie:
            self._movie.frameChanged.connect(self._on_frame_changed)
            self._movie.start()

    def _on_frame_changed(self, _frame: int):
        if not self._movie:
            return
        self._icon = QIcon(self._movie.currentPixmap())
        for target in self._targets:
            if hasattr(target, "setIcon"):
                target.setIcon(self._icon)

    def add_target(self, target: Any):
        """Attach the icon to a widget or action.

        The target must provide a ``setIcon`` method. This works for
        ``QAction``, ``QPushButton`` and any other Qt object exposing the same
        API.
        """
        if hasattr(target, "setIcon"):
            target.setIcon(self._icon)
            self._targets.append(target)

    @property
    def icon(self) -> QIcon:
        """Return the underlying ``QIcon`` instance."""
        return self._icon