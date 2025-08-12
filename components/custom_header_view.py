# components/custom_header_view.py
# A custom header view that draws its own sort indicators for reliability.

from PyQt6.QtWidgets import QHeaderView
from PyQt6.QtGui import QPainter
from PyQt6.QtCore import Qt
from utils.icon_manager import IconManager

class CustomHeaderView(QHeaderView):
    """
    A QHeaderView subclass that manually paints a sort indicator icon
    to ensure it is always visible, regardless of stylesheet complexities.
    """
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setSectionsClickable(True)

    def paintSection(self, painter: QPainter, rect, logicalIndex):
        """
        Overrides the default paintSection to draw a custom sort indicator.
        """
        painter.save()
        super().paintSection(painter, rect, logicalIndex)
        painter.restore()

        # Check if this section is the one being sorted
        if self.isSortIndicatorShown() and self.sortIndicatorSection() == logicalIndex:
            order = self.sortIndicatorOrder()
            
            # Choose the correct icon based on the sort order
            if order == Qt.SortOrder.AscendingOrder:
                icon = IconManager.create_icon('fa5s.sort-up', color='#dbe0e8')
            else:
                icon = IconManager.create_icon('fa5s.sort-down', color='#dbe0e8')

            # Calculate the position for the icon on the right side of the header
            icon_size = 12
            y = (rect.height() - icon_size) // 2
            x = rect.x() + rect.width() - icon_size - 8 # 8px padding from the right edge
            
            # Draw the icon
            icon.paint(painter, x, y, icon_size, icon_size)

