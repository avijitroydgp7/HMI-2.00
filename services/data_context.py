from PyQt6.QtCore import QObject, pyqtSignal

class DataContext(QObject):
    """Application-wide pub/sub bus for data events."""
    tags_changed = pyqtSignal(dict)
    comments_changed = pyqtSignal(dict)
    styles_changed = pyqtSignal(dict)
    screens_changed = pyqtSignal(dict)


data_context = DataContext()
