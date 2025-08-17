from PyQt6.QtWidgets import QTableView
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt, QModelIndex
from services.comment_data_service import comment_data_service


class CommentTableWidget(QTableView):
    """Table for managing comments within a comment group."""

    def __init__(self, group_id: str, parent=None):
        super().__init__(parent)
        self.group_id = group_id
        group = comment_data_service.get_group(group_id) or {}
        self.group_label = f"[{group.get('number', '')}] - {group.get('name', '')}".strip()
        self.setObjectName("CommentTableWidget")

        self._model = QStandardItemModel(0, 2, self)
        self._model.setHorizontalHeaderLabels(["Serial No.", "Comment"])
        self.setModel(self._model)

        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)

        # Load existing comments
        for comment in group.get("comments", []):
            self.add_comment(comment)

        self._model.dataChanged.connect(lambda *_: self._sync_to_service())
        self._model.rowsInserted.connect(self._on_rows_changed)
        self._model.rowsRemoved.connect(self._on_rows_changed)

    def add_comment(self, text: str = "") -> None:
        """Append a new comment row."""
        row = self._model.rowCount()
        self._model.insertRow(row)
        self._model.setItem(row, 1, QStandardItem(text))

    def _on_rows_changed(self, parent: QModelIndex, first: int, last: int) -> None:
        self._reindex_rows()
        self._sync_to_service()

    def _reindex_rows(self) -> None:
        for row in range(self._model.rowCount()):
            item = self._model.item(row, 0)
            if item is None:
                item = QStandardItem()
                self._model.setItem(row, 0, item)
            item.setEditable(False)
            item.setText(str(row + 1))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    def _sync_to_service(self) -> None:
        comments = []
        for row in range(self._model.rowCount()):
            item = self._model.item(row, 1)
            comments.append(item.text() if item else "")
        comment_data_service.update_comments(self.group_id, comments)