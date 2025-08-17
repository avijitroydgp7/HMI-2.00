from __future__ import annotations

from typing import Any, List

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt

try:
    from asteval import Interpreter
except Exception:  # pragma: no cover - runtime import
    Interpreter = None


class CommentTableModel(QAbstractTableModel):
    """Table model that stores raw cell input and evaluated values."""

    def __init__(self, columns: List[str], parent=None):
        super().__init__(parent)
        self.columns = columns
        self._data: List[List[dict[str, Any]]] = []
        self._headers = ["Serial No."] + columns
        self._asteval = Interpreter() if Interpreter else None

    # Basic model API -------------------------------------------------
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: D401
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: D401
        return len(self._headers)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._headers[section]
        return super().headerData(section, orientation, role)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):  # noqa: D401
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            cell = self._data[row][col]
            if role == Qt.ItemDataRole.DisplayRole:
                return cell.get("value", "")
            return cell.get("raw", "")
        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole):  # noqa: D401
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False
        row, col = index.row(), index.column()
        self._data[row][col]["raw"] = value
        self._evaluate_all()
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])
        return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:  # noqa: D401
        if not index.isValid():
            return Qt.ItemFlag.ItemIsEnabled
        if index.column() == 0:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        return super().flags(index) | Qt.ItemFlag.ItemIsEditable

    # Row/Column management -------------------------------------------
    def insertRow(self, row: int, parent: QModelIndex = QModelIndex()):  # noqa: D401
        self.beginInsertRows(parent, row, row)
        cols = self.columnCount()
        new_row = [dict(raw="", value="") for _ in range(cols)]
        self._data.insert(row, new_row)
        self.endInsertRows()
        self._reindex_serials()
        return True

    def removeRow(self, row: int, parent: QModelIndex = QModelIndex()):  # noqa: D401
        if row < 0 or row >= self.rowCount():
            return False
        self.beginRemoveRows(parent, row, row)
        self._data.pop(row)
        self.endRemoveRows()
        self._reindex_serials()
        return True

    def insertColumn(self, column: int, parent: QModelIndex = QModelIndex()):  # noqa: D401
        self.beginInsertColumns(parent, column, column)
        self._headers.insert(column, f"Column {column}")
        for row in self._data:
            row.insert(column, dict(raw="", value=""))
        self.endInsertColumns()
        return True

    def removeColumn(self, column: int, parent: QModelIndex = QModelIndex()):  # noqa: D401
        if column <= 0 or column >= self.columnCount():
            return False
        self.beginRemoveColumns(parent, column, column)
        self._headers.pop(column)
        for row in self._data:
            row.pop(column)
        self.endRemoveColumns()
        return True

    # Utility ---------------------------------------------------------
    def get_raw(self, row: int, col: int) -> Any:
        return self._data[row][col].get("raw", "")

    def set_row_values(self, values):
        row = self.rowCount()
        self.insertRow(row)
        for col, text in enumerate(values, start=1):
            idx = self.index(row, col)
            self.setData(idx, text)

    def _reindex_serials(self):
        for i, row in enumerate(self._data, start=1):
            row[0]["raw"] = str(i)
            row[0]["value"] = str(i)
        self._evaluate_all()

    def _evaluate_all(self):
        if not self._asteval:
            # if asteval not available simply mirror raw values
            for row in self._data:
                for cell in row:
                    cell["value"] = cell.get("raw", "")
            return
        env = {}
        changed = True
        iterations = 0
        max_iter = self.rowCount() * self.columnCount() + 1
        while changed and iterations < max_iter:
            changed = False
            iterations += 1
            for r, row in enumerate(self._data):
                for c, cell in enumerate(row):
                    raw = cell.get("raw", "")
                    if isinstance(raw, str) and raw.startswith("=") and c != 0:
                        expr = raw[1:]
                        self._asteval.symtable.update(env)
                        try:
                            val = self._asteval(expr)
                        except Exception:
                            val = "ERR"
                    else:
                        val = raw
                    if cell.get("value") != val:
                        cell["value"] = val
                        env[self._cell_name(r, c)] = val
                        changed = True
        # final population for non-formula cells
        for r, row in enumerate(self._data):
            for c, cell in enumerate(row):
                env[self._cell_name(r, c)] = cell.get("value")

    @staticmethod
    def _cell_name(row: int, col: int) -> str:
        """Return Excel-like cell name (A1, B2, ...)."""
        letters = ""
        col -= 1  # skip serial number column
        while col >= 0:
            letters = chr(ord('A') + col % 26) + letters
            col = col // 26 - 1
        return f"{letters}{row + 1}"