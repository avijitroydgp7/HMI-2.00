from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableView,
    QPushButton,
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt, QModelIndex
from services.comment_data_service import comment_data_service


class CommentTableWidget(QWidget):
    """Table for managing comments within a comment group."""

    def __init__(self, group_id: str, parent=None):
        super().__init__(parent)
        self.group_id = group_id
        group = comment_data_service.get_group(group_id) or {}
        self.group_label = f"[{group.get('number', '')}] - {group.get('name', '')}".strip()
        self.setObjectName("CommentTableWidget")

        self.columns = list(group.get("columns", ["Comment"]))

        main_layout = QVBoxLayout(self)
        button_layout = QHBoxLayout()
        self.add_row_btn = QPushButton("Add Row")
        self.remove_row_btn = QPushButton("Remove Row")
        self.add_col_btn = QPushButton("Add Column")
        self.remove_col_btn = QPushButton("Remove Column")
        button_layout.addWidget(self.add_row_btn)
        button_layout.addWidget(self.remove_row_btn)
        button_layout.addWidget(self.add_col_btn)
        button_layout.addWidget(self.remove_col_btn)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        self.table = QTableView(self)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectItems)
        self.table.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        main_layout.addWidget(self.table)

        self._model = QStandardItemModel(0, len(self.columns) + 1, self)
        headers = ["Serial No."] + self.columns
        self._model.setHorizontalHeaderLabels(headers)
        self.table.setModel(self._model)

        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)

        for row_data in group.get("comments", []):
            self.add_comment(row_data)

        self._model.dataChanged.connect(lambda *_: self._sync_to_service())
        self._model.rowsInserted.connect(self._on_structure_changed)
        self._model.rowsRemoved.connect(self._on_structure_changed)
        self._model.columnsInserted.connect(self._on_structure_changed)
        self._model.columnsRemoved.connect(self._on_structure_changed)

        self.add_row_btn.clicked.connect(lambda: self.add_comment())
        self.remove_row_btn.clicked.connect(self.remove_selected_rows)
        self.add_col_btn.clicked.connect(self.add_column)
        self.remove_col_btn.clicked.connect(self.remove_column)

        self._reindex_rows()

    def setFocus(self):  # noqa: N802 - Qt naming convention
        self.table.setFocus()

    def add_comment(self, values=None) -> None:
        """Append a new comment row."""
        if values is None:
            values = [""] * len(self.columns)
        row = self._model.rowCount()
        self._model.insertRow(row)
        for col, text in enumerate(values, start=1):
            self._model.setItem(row, col, QStandardItem(text))

    def remove_selected_rows(self) -> None:
        """Remove all currently selected rows."""
        selection = self.table.selectionModel().selectedRows()
        for index in sorted(selection, key=lambda i: i.row(), reverse=True):
            self._model.removeRow(index.row())

    def add_column(self) -> None:
        """Append a new editable column to the table."""
        col_index = self._model.columnCount()
        column_name = f"Column {col_index}"
        self._model.insertColumn(col_index)
        self._model.setHeaderData(col_index, Qt.Orientation.Horizontal, column_name)
        for row in range(self._model.rowCount()):
            self._model.setItem(row, col_index, QStandardItem(""))
        self.columns.append(column_name)
        self._sync_to_service()

    def remove_column(self) -> None:
        """Remove the last column if more than one data column exists."""
        if self._model.columnCount() <= 2:
            return  # Keep at least one data column besides the serial number
        col_index = self._model.columnCount() - 1
        self._model.removeColumn(col_index)
        if self.columns:
            self.columns.pop()

    def _on_structure_changed(self, parent: QModelIndex, first: int, last: int) -> None:
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
            row_data = []
            for col in range(1, self._model.columnCount()):
                item = self._model.item(row, col)
                row_data.append(item.text() if item else "")
            comments.append(row_data)
        comment_data_service.update_comments(self.group_id, comments, self.columns)