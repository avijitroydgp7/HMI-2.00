from PyQt6.QtWidgets import QTreeWidgetItem
from PyQt6.QtCore import Qt


class ArrayTreeHandler:
    """Handler for 3D array expansion/collapse in tag table"""
    
    @staticmethod
    def expand_all_dimensions(item, expand=True):
        """Expand all dimensions of a 3D array with single click"""
        if not item:
            return
            
        # Expand the current item
        item.setExpanded(expand)
        
        # Recursively expand all child dimensions
        for i in range(item.childCount()):
            child = item.child(i)
            ArrayTreeHandler.expand_all_dimensions(child, expand)
    
    @staticmethod
    def collapse_all_dimensions(item):
        """Collapse all dimensions of a 3D array"""
        ArrayTreeHandler.expand_all_dimensions(item, False)
    
    @staticmethod
    def is_3d_array_item(item):
        """Check if this item represents a 3D array element"""
        if not item:
            return False
            
        # Check if this is an array element by looking at indices
        indices = item.data(0, Qt.ItemDataRole.UserRole)
        return isinstance(indices, list) and len(indices) >= 1
    
    @staticmethod
    def get_array_depth(item):
        """Get the depth of array nesting"""
        if not item:
            return 0
            
        indices = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(indices, list):
            return len(indices)
        return 0
    
    @staticmethod
    def should_expand_all(item):
        """Determine if this item should trigger full expansion"""
        if not item:
            return False
            
        # Check if this is a root array item or first dimension
        parent = item.parent()
        if not parent:
            # Root level array
            return True
            
        indices = item.data(0, Qt.ItemDataRole.UserRole)
        parent_indices = parent.data(0, Qt.ItemDataRole.UserRole)
        
        # If this is the first dimension (indices length = 1), expand all
        if isinstance(indices, list) and len(indices) == 1:
            return True
            
        return False
