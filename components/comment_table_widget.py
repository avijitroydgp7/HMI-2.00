from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableView,
    QPushButton,
    QApplication,
    QMenu,
    QLineEdit,
    QStyledItemDelegate,
    QCompleter,
)
from PyQt6.QtGui import QKeySequence, QAction
from PyQt6.QtCore import Qt
from services.comment_data_service import comment_data_service
from .comment_table_model import CommentTableModel


class FormulaDelegate(QStyledItemDelegate):
    """Delegate providing cell reference auto-completion for formulas."""

    def createEditor(self, parent, option, index):  # noqa: N802 - Qt naming convention
        editor = QLineEdit(parent)
        model = index.model()
        refs = []
        for r in range(model.rowCount()):
            for c in range(1, model.columnCount()):
                refs.append(model._cell_name(r, c))
        completer = QCompleter(refs, editor)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        editor.setCompleter(completer)
        return editor


class CommentTableView(QTableView):
    """Table view with basic clipboard support for comment cells."""

    def keyPressEvent(self, event):  # noqa: N802 - Qt naming convention
        clipboard = QApplication.clipboard()
        model = self.model()
        selection_model = self.selectionModel()
        indexes = sorted(selection_model.selectedIndexes(), key=lambda i: (i.row(), i.column()))

        if event.matches(QKeySequence.StandardKey.Copy):
            if indexes:
                rows = {}
                for idx in indexes:
                    rows.setdefault(idx.row(), {})[idx.column()] = idx.data() or ""
                lines = []
                for row in sorted(rows.keys()):
                    cols = rows[row]
                    line = "\t".join(cols[col] for col in sorted(cols.keys()))
                    lines.append(line)
                clipboard.setText("\n".join(lines))
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.Cut):
            if indexes:
                rows = {}
                for idx in indexes:
                    rows.setdefault(idx.row(), {})[idx.column()] = idx.data() or ""
                lines = []
                for row in sorted(rows.keys()):
                    cols = rows[row]
                    line = "\t".join(cols[col] for col in sorted(cols.keys()))
                    lines.append(line)
                clipboard.setText("\n".join(lines))
                for idx in indexes:
                    model.setData(idx, "")
                parent = self.parent()
                if parent and hasattr(parent, "_sync_to_service"):
                    parent._sync_to_service()
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.Paste):
            text = clipboard.text()
            if text and indexes:
                start_row = indexes[0].row()
                start_col = indexes[0].column()
                lines = text.splitlines()
                for r, line in enumerate(lines):
                    for c, cell in enumerate(line.split("\t")):
                        row = start_row + r
                        col = start_col + c
                        if row < model.rowCount() and col < model.columnCount():
                            model.setData(model.index(row, col), cell)
                parent = self.parent()
                if parent and hasattr(parent, "_sync_to_service"):
                    parent._sync_to_service()
            event.accept()
            return
        if event.key() == Qt.Key.Key_F2:
            self.edit(self.currentIndex())
            event.accept()
            return
        if event.text() == "=" and not self.state() == QTableView.State.EditingState:
            index = self.currentIndex()
            self.edit(index)
            editor = self.focusWidget()
            if isinstance(editor, QLineEdit):
                editor.setText("=")
            event.accept()
            return
        super().keyPressEvent(event)

    # Context menu ---------------------------------------------------
    def contextMenuEvent(self, event):  # noqa: N802 - Qt naming convention
        menu = QMenu(self)
        insert_row = QAction("Insert Row", self)
        delete_row = QAction("Delete Row", self)
        insert_col = QAction("Insert Column", self)
        delete_col = QAction("Delete Column", self)
        merge_cells = QAction("Merge Cells", self)
        unmerge_cells = QAction("Unmerge Cells", self)
        freeze = QAction("Freeze Panes", self)
        menu.addActions([insert_row, delete_row, insert_col, delete_col, merge_cells, unmerge_cells, freeze])

        action = menu.exec(event.globalPos())
        parent = self.parent()
        if not parent:
            return
        if action == insert_row:
            parent.add_comment()
        elif action == delete_row:
            parent.remove_selected_rows()
        elif action == insert_col:
            parent.add_column()
        elif action == delete_col:
            parent.remove_column()
        elif action == merge_cells:
            self._merge_selected()
        elif action == unmerge_cells:
            self._unmerge_selected()
        elif action == freeze:
            setattr(parent, "_frozen", True)

    def _merge_selected(self):
        indexes = self.selectionModel().selectedIndexes()
        if not indexes:
            return
        rows = [i.row() for i in indexes]
        cols = [i.column() for i in indexes]
        top, left = min(rows), min(cols)
        bottom, right = max(rows), max(cols)
        self.setSpan(top, left, bottom - top + 1, right - left + 1)

    def _unmerge_selected(self):
        indexes = self.selectionModel().selectedIndexes()
        for index in indexes:
            self.setSpan(index.row(), index.column(), 1, 1)


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

        self.table = CommentTableView(self)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectItems)
        self.table.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        main_layout.addWidget(self.table)
        self.table.setItemDelegate(FormulaDelegate(self.table))

        self._model = CommentTableModel(self.columns, self)
        self.table.setModel(self._model)
        self.table.setSortingEnabled(True)

        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)

        for row_data in group.get("comments", []):
            self.add_comment(row_data)

        self._model.dataChanged.connect(lambda *_: self._sync_to_service())
        self._model.rowsInserted.connect(lambda *_: self._sync_to_service())
        self._model.rowsRemoved.connect(lambda *_: self._sync_to_service())
        self._model.columnsInserted.connect(lambda *_: self._sync_to_service())
        self._model.columnsRemoved.connect(lambda *_: self._sync_to_service())

        self.add_row_btn.clicked.connect(lambda: self.add_comment())
        self.remove_row_btn.clicked.connect(self.remove_selected_rows)
        self.add_col_btn.clicked.connect(self.add_column)
        self.remove_col_btn.clicked.connect(self.remove_column)

    def setFocus(self):  # noqa: N802 - Qt naming convention
        self.table.setFocus()

    def add_comment(self, values=None) -> None:
        """Append a new comment row."""
        if values is None:
            values = [""] * len(self.columns)
        self._model.set_row_values(values)

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
        self._sync_to_service()

    def _sync_to_service(self) -> None:
        model = self.table.model()
        comments = []
        for row in range(model.rowCount()):
            row_data = []
            for col in range(1, model.columnCount()):
                row_data.append(model.get_raw(row, col) or "")
            comments.append(row_data)
        comment_data_service.update_comments(self.group_id, comments, self.columns)