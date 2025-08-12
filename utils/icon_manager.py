from PyQt6.QtGui import QIcon, QPixmap
import qtawesome as qta
from services.settings_service import settings_service
from .theme_manager import get_theme_colors

class IconManager:
    """
    Centralized manager for creating and converting icons in the application.
    Handles compatibility between PySide6 and PyQt6 icon types and theme-aware colors.
    """

    @staticmethod
    def get_current_theme_colors():
        """Gets the colors for the currently active theme."""
        current_theme = settings_service.get_value("appearance/theme", "dark_theme")
        return get_theme_colors(current_theme)

    @staticmethod
    def create_icon(icon_name: str, color: str = None, active_color: str = None, size: int = None) -> QIcon:
        """
        Create a PyQt6 QIcon from a qtawesome icon name with theme-aware colors.
        
        Args:
            icon_name (str): The qtawesome icon name (e.g., 'fa5s.file').
            color (str, optional): The color of the icon. Defaults to the theme's icon color.
            active_color (str, optional): The color of the icon when active. Defaults to theme's active color.
            size (int, optional): The size of the icon in pixels. If None, returns a scalable icon.
            
        Returns:
            QIcon: A PyQt6-compatible QIcon.
        """
        try:
            theme_colors = IconManager.get_current_theme_colors()
            base_color = color if color is not None else theme_colors.get('icon_color', '#dbe0e8')
            
            # For now, we use the same color for all states, but this can be expanded.
            qta_icon = qta.icon(icon_name, color=base_color)
            
            if size is None:
                return qta_icon
                
            pixmap = qta_icon.pixmap(size, size)
            return QIcon(pixmap)
            
        except Exception as e:
            print(f"Error creating icon {icon_name}: {str(e)}")
            return QIcon()

    @staticmethod
    def create_pixmap(icon_name: str, size: int, color: str = None) -> QPixmap:
        """
        Create a PyQt6 QPixmap from a qtawesome icon name with a theme-aware color.
        
        Args:
            icon_name (str): The qtawesome icon name.
            size (int): The size of the pixmap in pixels.
            color (str, optional): The color of the icon. Defaults to the theme's icon color.
            
        Returns:
            QPixmap: A PyQt6-compatible QPixmap.
        """
        try:
            theme_colors = IconManager.get_current_theme_colors()
            base_color = color if color is not None else theme_colors.get('icon_color', '#dbe0e8')
            
            qta_icon = qta.icon(icon_name, color=base_color)
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
