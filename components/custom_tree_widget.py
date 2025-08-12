from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PyQt6.QtGui import QPainter, QMouseEvent
from PyQt6.QtCore import QModelIndex, QRect
from utils.icon_manager import IconManager
from .array_tree_handler import ArrayTreeHandler

class CustomTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Disable the default behavior of expanding/collapsing on double-click.
        # This ensures that only a single click on the branch indicator (+)
        # will trigger the action.
        self.setExpandsOnDoubleClick(False)
        # Standardize indentation for consistent alignment
        self.setIndentation(20)
        self.setRootIsDecorated(True)

    def mousePressEvent(self, event: QMouseEvent):
        """
        Overrides the default mouse press event to provide reliable single-click
        expansion/collapse behavior on the branch indicator (+/- icon).
        Handles 3D array expansion with single click for all dimensions.
        """
        index = self.indexAt(event.pos())
        if not index.isValid():
            super().mousePressEvent(event)
            return

        # Get the branch rectangle - this is where the branch indicator is drawn
        branch_rect = self.visualRect(index)
        
        # The branch indicator is always in the indentation area
        indent = self.indentation()
        icon_size = 16
        
        # Calculate the level to determine the correct indentation position
        level = 0
        parent = index.parent()
        while parent.isValid():
            level += 1
            parent = parent.parent()
        
        # Calculate the exact position for the branch indicator
        # This matches the drawBranches method positioning exactly
        indicator_x = branch_rect.left() + (level * indent) + (indent - icon_size) // 2
        indicator_y = branch_rect.top() + (branch_rect.height() - icon_size) // 2
        
        # Create precise indicator rectangle
        indicator_rect = QRect(indicator_x, indicator_y, icon_size, icon_size)
        
        # Check if click is on the branch indicator
        if indicator_rect.contains(event.pos()):
            item = self.itemFromIndex(index)
            if item:
                has_children = item.childCount() > 0
                show_indicator_policy = (item.childIndicatorPolicy() == QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
                
                if has_children or show_indicator_policy:
                    is_expanded = self.isExpanded(index)
                    
                    # Toggle expansion state
                    self.setExpanded(index, not is_expanded)
                    
                    # Handle 3D array expansion
                    if ArrayTreeHandler.should_expand_all(item):
                        if not is_expanded:
                            ArrayTreeHandler.expand_all_dimensions(item)
                        else:
                            ArrayTreeHandler.collapse_all_dimensions(item)
                    else:
                        # Normal expansion for non-array items
                        if not is_expanded:
                            self._expand_all_children(item)
                        else:
                            self._collapse_all_children(item)
                    
                    # The event is handled, so we don't pass it to the base class.
                    return

        # If the click was not on the indicator, fall back to default behavior.
        super().mousePressEvent(event)

    def _expand_all_children(self, item):
        """Recursively expand all children of an item"""
        if not item:
            return
        item.setExpanded(True)
        for i in range(item.childCount()):
            child = item.child(i)
            self._expand_all_children(child)

    def _collapse_all_children(self, item):
        """Recursively collapse all children of an item"""
        if not item:
            return
        item.setExpanded(False)
        for i in range(item.childCount()):
            child = item.child(i)
            self._collapse_all_children(child)

    def drawBranches(self, painter: QPainter, rect: QRect, index: QModelIndex):
        # First, let the base class draw the tracking lines and default indicator.
        super().drawBranches(painter, rect, index)

        # Now, we will draw our custom icon over the default indicator.
        item = self.itemFromIndex(index)
        if not item:
            return

        # An indicator should be drawn if the item has children, or if its policy
        # is to show an indicator even when childless (i.e., it's a "folder").
        has_children = item.childCount() > 0
        show_indicator_policy = (item.childIndicatorPolicy() == QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)

        if not (has_children or show_indicator_policy):
            return

        # Determine the state (open or closed) using the widget's isExpanded() method.
        is_expanded = self.isExpanded(index)

        icon_name = 'fa5s.minus-square' if is_expanded else 'fa5s.plus-square'
        icon = IconManager.create_icon(icon_name)
        icon_size = 16

        # Calculate the exact position for the icon based on tree level
        # This ensures all expand/collapse buttons align vertically regardless of depth
        level = 0
        parent = index.parent()
        while parent.isValid():
            level += 1
            parent = parent.parent()
        
        # Position the icon consistently based on tree level
        # This creates consistent alignment across all tree levels
        indent = self.indentation()
        icon_x = rect.left() + (level * indent) + (indent - icon_size) // 2
        icon_y = rect.top() + (rect.height() - icon_size) // 2
        
        # Paint our custom icon at the calculated position
        icon.paint(painter, icon_x, icon_y, icon_size, icon_size)
