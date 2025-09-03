from typing import List, Optional, Any, Dict, Tuple
from PyQt6.QtCore import QObject
from PyQt6.QtGui import QIcon, QPixmap, QMovie
import qtawesome as qta


_ICON_CACHE: Dict[Tuple[str, Optional[str], Optional[str]], QIcon] = {}
"""Cache for generated :class:`QIcon` objects.

The cache is unbounded and will grow until cleared via
``IconManager.clear_cache``.
"""

_PIXMAP_CACHE: Dict[Tuple[str, int, Optional[str], Optional[str]], QPixmap] = {}
"""Cache for generated :class:`QPixmap` objects.

This cache has no eviction policy.
"""


class IconManager:
    """Centralized manager for creating and converting icons.

    Icons are cached by ``(icon_name, color, active_color)`` and pixmaps by
    ``(icon_name, size, color, active_color)``. Call :meth:`clear_cache` to
    release memory.
    """

    @staticmethod
    def create_icon(
        icon_name: str,
        color: Optional[str] = None,
        active_color: Optional[str] = None,
        size: Optional[int] = None,
    ):
        """Create a PyQt6 ``QIcon`` from a qtawesome icon name.

        Results are cached by ``(icon_name, color, active_color)``. The
        ``size`` argument is retained for backward compatibility but is not
        used; Qt will render scalable icons at the requested dimensions via
        ``QWidget.setIconSize``.

        Args:
            icon_name (str): The qtawesome icon name (e.g., 'fa5s.file').
            color (str, optional): The color of the icon. Defaults to the standard icon color.
            active_color (str, optional): The color of the icon when active. Defaults to the standard active color.
            size (int, optional): Deprecated. Provided for compatibility but
                ignored; the returned icon is scalable.

        Returns:
            QIcon: A PyQt6-compatible ``QIcon``.
        """
        key = (icon_name, color, active_color)
        if key in _ICON_CACHE:
            return _ICON_CACHE[key]

        try:
            base_color = color if color is not None else "#DADADA"
            selected_color = active_color if active_color is not None else "#DADADA"

            # Use different colors for normal and selected states
            qta_icon = qta.icon(
                icon_name,
                color=base_color,
                color_active=selected_color,
                color_selected=selected_color,
            )

            if qta_icon is None:
                result = QIcon()
            else:
                # Wrap the qtawesome icon to ensure a distinct QIcon instance
                # while preserving the scalable rendering capabilities.
                result = QIcon(qta_icon)

        except Exception as e:
            print(f"Error creating icon {icon_name}: {str(e)}")
            result = QIcon()

        _ICON_CACHE[key] = result
        return result

    @staticmethod
    def create_pixmap(
        icon_name: str,
        size: int,
        color: Optional[str] = None,
        active_color: Optional[str] = None,
    ):
        """Create a PyQt6 ``QPixmap`` from a qtawesome icon name.

        Results are cached by ``(icon_name, size, color, active_color)``.

        Args:
            icon_name (str): The qtawesome icon name.
            size (int): The size of the pixmap in pixels.
            color (str, optional): The color of the icon. Defaults to the standard icon color.
            active_color (str, optional): Active color for completeness; unused for static pixmaps.

        Returns:
            QPixmap: A PyQt6-compatible ``QPixmap``.
        """
        key = (icon_name, size, color, active_color)
        if key in _PIXMAP_CACHE:
            return _PIXMAP_CACHE[key]

        try:
            base_color = color if color is not None else "#FFFFFF"
            selected_color = active_color if active_color is not None else base_color

            qta_icon = qta.icon(
                icon_name,
                color=base_color,
                color_active=selected_color,
                color_selected=selected_color,
            )

            if qta_icon is None:
                result = QPixmap()
            else:
                result = qta_icon.pixmap(size, size)

        except Exception as e:
            print(f"Error creating pixmap {icon_name}: {str(e)}")
            result = QPixmap()

        _PIXMAP_CACHE[key] = result
        return result

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
    def clear_cache():
        """Clear cached icons and pixmaps.

        The caches are unbounded and may consume memory over time. Call
        this method to release stored ``QIcon`` and ``QPixmap`` instances.
        """
        _ICON_CACHE.clear()
        _PIXMAP_CACHE.clear()

    @staticmethod
    def create_animated_icon(
        source: str,
        color: Optional[str] = None,
        active_color: Optional[str] = None,
        size: Optional[int] = None,
    ):
        """Create an animated icon or gracefully fall back to a static one.

        ``source`` can either be a path to a GIF/APNG file or a qtawesome
        icon name. If the movie cannot be created the method returns a
        :class:`AnimatedIcon` wrapping a static icon created via
        :func:`create_icon`.

        Args:
            source (str): Path to an animated image or a qtawesome icon name.
            color (str, optional): Color for qtawesome icons.
            active_color (str, optional): Active color for qtawesome icons.
            size (int, optional): Desired size of the icon.

        Returns:
            AnimatedIcon: Helper object that keeps animations running and
            updates any registered targets.

        Example:
            >>> spinner = IconManager.create_animated_icon("spinner.gif")
            >>> spinner.add_target(my_button)
        """

        movie = QMovie(source)
        if movie.isValid():
            movie.jumpToFrame(0)
            return AnimatedIcon(movie, QIcon(movie.currentPixmap()))

        # Fallback: treat ``source`` as a qtawesome icon name
        static_icon = IconManager.create_icon(
            source, color=color, active_color=active_color, size=size
        )
        return AnimatedIcon(None, static_icon)


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