"""Comment table model with spreadsheet-like formula support.

The model evaluates cell formulas using :mod:`asteval` and exposes a small
set of common spreadsheet functions such as :func:`SUM`, :func:`AVERAGE`,
:func:`MIN` and :func:`MAX`. Functions accept either individual values or
Excel-style ranges, e.g. ``=SUM(A1:A5)``.
"""
from __future__ import annotations

from typing import Any, List
import re
from datetime import datetime, date

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt6.QtGui import QFont, QColor
from services.command_history_service import command_history_service
from services.commands import (
    UpdateCommentCellCommand,
    UpdateCommentFormatCommand,
)

try:
    from asteval import Interpreter
except Exception:  # pragma: no cover - runtime import
    Interpreter = None


class CommentTableModel(QAbstractTableModel):
    """Table model that stores raw cell input and evaluated values."""

    def __init__(self, columns: List[str], parent=None):
        super().__init__(parent)
        self.columns = columns
        # each cell stores {'raw': Any, 'value': Any, 'format': {}, 'type': str}
        self._data: List[List[dict[str, Any]]] = []
        self._headers = ["Serial No."] + columns
        self._asteval = Interpreter() if Interpreter else None
        self._suspend_history = False
        self.history_sync_cb = lambda: None

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
        cell = self._data[row][col]
        fmt = cell.get("format", {})
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if role == Qt.ItemDataRole.DisplayRole:
                return cell.get("value", "")
            return cell.get("raw", "")
        if role == Qt.ItemDataRole.FontRole:
            font = QFont()
            font.setBold(fmt.get("bold", False))
            font.setItalic(fmt.get("italic", False))
            font.setUnderline(fmt.get("underline", False))
            return font
        if role == Qt.ItemDataRole.BackgroundRole:
            color = fmt.get("bg_color")
            if color:
                return QColor(color)
        if role == Qt.ItemDataRole.UserRole:
            return fmt
        return None

    @staticmethod
    def _infer_type(value: Any) -> str:
        if isinstance(value, (int, float)):
            return "number"
        if isinstance(value, (datetime, date)):
            return "date"
        return "str"

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole):  # noqa: D401
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False
        row, col = index.row(), index.column()
        if self._suspend_history:
            self._data[row][col]["raw"] = value
            self._data[row][col]["type"] = self._infer_type(value)
            self._evaluate_all()
            self.dataChanged.emit(
                index,
                index,
                [
                    Qt.ItemDataRole.DisplayRole,
                    Qt.ItemDataRole.EditRole,
                    Qt.ItemDataRole.FontRole,
                    Qt.ItemDataRole.BackgroundRole,
                ],
            )
            return True
        old = self._data[row][col].get("raw", "")
        if old == value:
            return True
        cmd = UpdateCommentCellCommand(self, row, col, value, old, self.history_sync_cb)
        command_history_service.add_command(cmd)
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
        new_row = [dict(raw="", value="", format={}, type="str") for _ in range(cols)]
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
            row.insert(column, dict(raw="", value="", format={}, type="str"))
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

    def rename_header(self, column: int, name: str) -> None:
        """Rename a column header and notify views."""
        if 0 <= column < len(self._headers):
            self._headers[column] = name
            self.headerDataChanged.emit(Qt.Orientation.Horizontal, column, column)

    # Utility ---------------------------------------------------------
    def get_raw(self, row: int, col: int) -> Any:
        return self._data[row][col].get("raw", "")

    def get_format(self, row: int, col: int) -> dict[str, Any]:
        return self._data[row][col].get("format", {}).copy()

    def get_type(self, row: int, col: int) -> str:
        return self._data[row][col].get("type", "str")

    def set_cell_format(self, row: int, col: int, fmt: dict[str, Any]):
        if not self._suspend_history:
            old_fmt = self.get_format(row, col)
            cmd = UpdateCommentFormatCommand(self, row, col, fmt, old_fmt, self.history_sync_cb)
            command_history_service.add_command(cmd)
            return
        cell = self._data[row][col]
        current = cell.setdefault("format", {})
        current.update(fmt)
        idx = self.index(row, col)
        self.dataChanged.emit(
            idx,
            idx,
            [
                Qt.ItemDataRole.FontRole,
                Qt.ItemDataRole.BackgroundRole,
                Qt.ItemDataRole.DisplayRole,
            ],
        )

    def set_row_values(self, values):
        row = self.rowCount()
        self.insertRow(row)
        for col, cell in enumerate(values, start=1):
            idx = self.index(row, col)
            if isinstance(cell, dict):
                self.setData(idx, cell.get("raw", ""))
                self._data[row][col]["type"] = cell.get("type", self._infer_type(cell.get("raw", "")))
                fmt = cell.get("format")
                if fmt:
                    self.set_cell_format(row, col, fmt)
            else:
                self.setData(idx, cell)

    def _reindex_serials(self):
        for i, row in enumerate(self._data, start=1):
            row[0]["raw"] = str(i)
            row[0]["value"] = str(i)
            row[0]["type"] = "str"
        self._evaluate_all()

    def _evaluate_all(self):
        if not self._asteval:
            # if asteval not available simply mirror raw values
            for row in self._data:
                for cell in row:
                    cell["value"] = cell.get("raw", "")
            return
        env: dict[str, Any] = {}
        for r, row in enumerate(self._data):
            for c, cell in enumerate(row):
                env[self._cell_name(r, c)] = cell.get("value")

        def parse_cell(name: str) -> tuple[int, int]:
            match = re.fullmatch(r"([A-Z]+)([0-9]+)", name)
            if not match:
                raise ValueError(f"Invalid cell name: {name}")
            letters, number = match.groups()
            col = 0
            for ch in letters:
                col = col * 26 + (ord(ch) - ord('A') + 1)
            return int(number) - 1, col

        def cell_range(start: str, end: str):
            sr, sc = parse_cell(start)
            er, ec = parse_cell(end)
            values: list[Any] = []
            for r in range(min(sr, er), max(sr, er) + 1):
                for c in range(min(sc, ec), max(sc, ec) + 1):
                    values.append(env.get(self._cell_name(r, c)))
            return values

        def _flatten(items):
            out: list[Any] = []
            for it in items:
                if isinstance(it, (list, tuple)):
                    out.extend(_flatten(it))
                else:
                    out.append(it)
            return out

        def _coerce_number(value: Any) -> Any:
            if isinstance(value, (int, float)):
                return value
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        def SUM(*args):
            vals = [_coerce_number(v) for v in _flatten(args)]
            return sum(v for v in vals if v is not None)

        def AVERAGE(*args):
            vals = [v for v in (_coerce_number(v) for v in _flatten(args)) if v is not None]
            return sum(vals) / len(vals) if vals else 0

        def MIN(*args):
            vals = [v for v in (_coerce_number(v) for v in _flatten(args)) if v is not None]
            return min(vals) if vals else 0

        def MAX(*args):
            vals = [v for v in (_coerce_number(v) for v in _flatten(args)) if v is not None]
            return max(vals) if vals else 0

        env.update({
            'SUM': SUM,
            'AVERAGE': AVERAGE,
            'MIN': MIN,
            'MAX': MAX,
            'cell_range': cell_range,
        })

        range_re = re.compile(r"([A-Z]+[0-9]+):([A-Z]+[0-9]+)")

        changed = True
        iterations = 0
        max_iter = self.rowCount() * self.columnCount() + 1
        while changed and iterations < max_iter:
            changed = False
            iterations += 1
            for r, row in enumerate(self._data):
                for c, cell in enumerate(row):
                    raw = cell.get('raw', '')
                    if isinstance(raw, str) and raw.startswith('=') and c != 0:
                        expr = raw[1:]
                        expr = range_re.sub(lambda m: f"cell_range('{m.group(1)}','{m.group(2)}')", expr)
                        self._asteval.symtable.update(env)
                        try:
                            val = self._asteval(expr)
                        except Exception:
                            val = 'ERR'
                    else:
                        val = raw
                    if cell.get('value') != val:
                        cell['value'] = val
                        env[self._cell_name(r, c)] = val
                        changed = True
        # final population for non-formula cells
        for r, row in enumerate(self._data):
            for c, cell in enumerate(row):
                env[self._cell_name(r, c)] = cell.get('value')

    @staticmethod
    def _cell_name(row: int, col: int) -> str:
        """Return Excel-like cell name (A1, B2, ...)."""
        letters = ""
        col -= 1  # skip serial number column
        while col >= 0:
            letters = chr(ord('A') + col % 26) + letters
            col = col // 26 - 1
        return f"{letters}{row + 1}"
