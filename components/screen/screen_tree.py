# components/screen/screen_tree.py
# Contains the custom QTreeWidget and QTreeWidgetItem for the screen manager.

from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QAbstractItemView
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QByteArray
from PyQt6.QtGui import QDrag, QKeyEvent
from components.custom_tree_widget import CustomTreeWidget
from utils import constants


class ScreenTreeItem(QTreeWidgetItem):
    """A custom tree widget item to allow for proper sorting by screen number."""
    def __lt__(self, other):
        tree = self.treeWidget()
        if not tree:
            return super().__lt__(other)
        
        column = tree.sortColumn()
        my_data = self.data(column, Qt.ItemDataRole.UserRole + 1)
        other_data = other.data(column, Qt.ItemDataRole.UserRole + 1)
        
        if isinstance(my_data, int) and isinstance(other_data, int):
            return my_data < other_data
        
        return self.text(column) < other.text(column)

class ScreenTreeWidget(CustomTreeWidget):

    """A custom tree widget that handles drag-and-drop and delete key presses."""
    delete_key_pressed = pyqtSignal()
    rename_key_pressed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(False)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.setHeaderHidden(True)
        self.setIndentation(20)  # Increased to 20px for consistent expand/collapse area
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.setRootIsDecorated(True)

    def keyPressEvent(self, event: QKeyEvent):
        """Emit a signal when the delete key is pressed."""
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_key_pressed.emit()
            event.accept()
        elif event.key() == Qt.Key.Key_F2:
            self.rename_key_pressed.emit()
            event.accept()
        else:
            super().keyPressEvent(event)

    def startDrag(self, supportedActions):
        """Initiates a drag operation for a screen item."""
        item = self.currentItem()
        if not item or not isinstance(item, ScreenTreeItem):
            return

        screen_id = item.data(0, Qt.ItemDataRole.UserRole)
        is_primary_screen = item.data(0, Qt.ItemDataRole.UserRole + 1) is not None

        if screen_id and is_primary_screen:
            mime_data = QMimeData()
            mime_data.setData(constants.MIME_TYPE_SCREEN_ID, QByteArray(screen_id.encode('utf-8')))
            
            drag = QDrag(self)
            drag.setMimeData(mime_data)
            
            if self.viewport():
                pixmap = self.viewport().grab(self.visualItemRect(item))
                drag.setPixmap(pixmap)
                drag.setHotSpot(pixmap.rect().center())
                
            drag.exec(Qt.DropAction.CopyAction)
