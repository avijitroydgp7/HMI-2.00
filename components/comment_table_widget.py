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
    QToolBar,
    QColorDialog,
    QInputDialog,
)
from PyQt6.QtGui import QKeySequence, QAction
from PyQt6.QtCore import Qt
from services.comment_data_service import comment_data_service
from services.command_history_service import command_history_service
from services.commands import (
    InsertCommentRowCommand,
    RemoveCommentRowsCommand,
    InsertCommentColumnCommand,
    RemoveCommentColumnCommand,
    BulkUpdateCellsCommand,
)
import re
from datetime import datetime, timedelta, date
from .comment_table_model import CommentTableModel
from .comment_filter_model import CommentFilterProxyModel


class CommentItemDelegate(QStyledItemDelegate):
    """Delegate providing auto-completion support."""

    _FUNCTIONS = ["SUM", "AVERAGE", "MIN", "MAX"]

    def createEditor(self, parent, option, index):  # noqa: N802 - Qt naming convention
        editor = QLineEdit(parent)
        model = index.model()
        if hasattr(model, "sourceModel"):
            model = model.sourceModel()
        refs = []
        for r in range(model.rowCount()):
            for c in range(1, model.columnCount()):
                refs.append(model._cell_name(r, c))
        refs.extend(f"{fn}(" for fn in self._FUNCTIONS)
        completer = QCompleter(refs, editor)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        editor.setCompleter(completer)
        editor.setToolTip("Functions: " + ", ".join(self._FUNCTIONS))

        def _show_menu(pos):
            menu = editor.createStandardContextMenu()
            func_menu = menu.addMenu("Functions")
            for fn in self._FUNCTIONS:
                action = func_menu.addAction(fn)
                action.triggered.connect(lambda _=False, f=fn: editor.insert(f + "("))
            menu.exec(editor.mapToGlobal(pos))

        editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        editor.customContextMenuRequested.connect(_show_menu)
        return editor


class _FillHandle(QWidget):
    """Small square shown at selection corner to start fill operations."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedSize(6, 6)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setStyleSheet("background-color: black")
        self.hide()

    def mousePressEvent(self, event):  # noqa: N802
        self.parent()._start_fill_drag()

    def mouseReleaseEvent(self, event):  # noqa: N802
        self.parent()._end_fill_drag(self.mapToParent(event.pos()))

    def mouseDoubleClickEvent(self, event):  # noqa: N802
        self.parent()._auto_fill_down()


class CommentTableView(QTableView):
    """Table view with basic clipboard support for comment cells."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fill_handle = _FillHandle(self)
        self._dragging_fill = False

    def selectionChanged(self, selected, deselected):  # noqa: N802
        super().selectionChanged(selected, deselected)
        self._update_fill_handle()

    def _update_fill_handle(self):
        indexes = self.selectionModel().selectedIndexes()
        if not indexes:
            self._fill_handle.hide()
            return
        rows = [i.row() for i in indexes]
        cols = [i.column() for i in indexes]
        bottom, right = max(rows), max(cols)
        rect = self.visualRect(self.model().index(bottom, right))
        size = self._fill_handle.size()
        self._fill_handle.move(rect.right() - size.width(), rect.bottom() - size.height())
        self._fill_handle.show()

    def _start_fill_drag(self):
        self._dragging_fill = True

    def _end_fill_drag(self, pos):
        if not self._dragging_fill:
            return
        self._dragging_fill = False
        idx = self.indexAt(pos)
        if idx.isValid():
            self._apply_fill(idx)
        self._update_fill_handle()

    def _auto_fill_down(self):
        model = self.model()
        source_model = model.sourceModel() if hasattr(model, "sourceModel") else model
        sel_indexes = self.selectionModel().selectedIndexes()
        if not sel_indexes:
            return
        mapped_sel = [model.mapToSource(i) if hasattr(model, "mapToSource") else i for i in sel_indexes]
        rows = [i.row() for i in mapped_sel]
        cols = [i.column() for i in mapped_sel]
        bottom, right = max(rows), max(cols)
        last_row = source_model.rowCount() - 1
        if bottom >= last_row:
            return
        target_source = source_model.index(last_row, right)
        target = model.mapFromSource(target_source) if hasattr(model, "mapFromSource") else target_source
        self._apply_fill(target)
        self._update_fill_handle()

    def _apply_fill(self, target_index):
        model = self.model()
        source_model = model.sourceModel() if hasattr(model, "sourceModel") else model
        sel_indexes = self.selectionModel().selectedIndexes()
        if not sel_indexes:
            return
        mapped_sel = [model.mapToSource(i) if hasattr(model, "mapToSource") else i for i in sel_indexes]
        rows = [i.row() for i in mapped_sel]
        cols = [i.column() for i in mapped_sel]
        top, left, bottom, right = min(rows), min(cols), max(rows), max(cols)

        target = model.mapToSource(target_index) if hasattr(model, "mapToSource") else target_index
        tr, tc = target.row(), target.column()
        if top <= tr <= bottom and left <= tc <= right:
            return
        tr = min(max(tr, 0), source_model.rowCount() - 1)
        tc = min(max(tc, 0), source_model.columnCount() - 1)
        up_rows = max(0, top - tr)
        down_rows = max(0, tr - bottom)
        left_cols = max(0, left - tc)
        right_cols = max(0, tc - right)
        if up_rows == down_rows == left_cols == right_cols == 0:
            return
        start_row = top - up_rows
        end_row = bottom + down_rows
        start_col = left - left_cols
        end_col = right + right_cols
        updates = []
        for r in range(start_row, end_row + 1):
            if r < 0 or r >= source_model.rowCount():
                continue
            for c in range(start_col, end_col + 1):
                if c < 0 or c >= source_model.columnCount():
                    continue
                if top <= r <= bottom and left <= c <= right:
                    continue
                src_r = top + ((r - top) % (bottom - top + 1))
                src_c = left + ((c - left) % (right - left + 1))
                base = source_model.get_raw(src_r, src_c)
                dr = r - src_r
                dc = c - src_c
                if isinstance(base, str) and base.startswith("="):
                    new_val = self._shift_formula(base, dr, dc, source_model._cell_name)
                else:
                    if left_cols == right_cols == 0 and left <= c <= right:
                        seq = [source_model.get_raw(row, c) for row in range(top, bottom + 1)]
                        step = r - bottom if r > bottom else r - top
                        new_val = self._sequence_value(seq, step)
                    elif up_rows == down_rows == 0 and top <= r <= bottom:
                        seq = [source_model.get_raw(r, col) for col in range(left, right + 1)]
                        step = c - right if c > right else c - left
                        new_val = self._sequence_value(seq, step)
                    else:
                        new_val = base
                old_val = source_model.get_raw(r, c)
                updates.append((r, c, new_val, old_val))
        if updates:
            cmd = BulkUpdateCellsCommand(source_model, updates, getattr(source_model, "history_sync_cb", None))
            command_history_service.add_command(cmd)

    @staticmethod
    def _parse_date(value):
        if isinstance(value, (datetime, date)):
            return value
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(value, fmt)
            except Exception:
                continue
        return None

    def _sequence_value(self, values, step):
        if len(values) == 1:
            return values[0]
        nums = []
        all_nums = True
        for v in values:
            try:
                nums.append(float(v))
            except Exception:
                all_nums = False
                break
        if all_nums:
            delta = nums[1] - nums[0] if len(nums) >= 2 else 1
            start = nums[-1] if step >= 0 else nums[0]
            return str(start + delta * step)
        dates = []
        all_dates = True
        for v in values:
            d = self._parse_date(v)
            if d is None:
                all_dates = False
                break
            dates.append(d)
        if all_dates:
            delta = dates[1] - dates[0] if len(dates) >= 2 else timedelta(days=1)
            start = dates[-1] if step >= 0 else dates[0]
            return (start + delta * step).strftime("%Y-%m-%d")
        return values[step % len(values)]

    def _shift_formula(self, formula, dr, dc, cell_name_func):
        ref_re = re.compile(r"([A-Z]+)([0-9]+)")

        def col_to_num(col):
            n = 0
            for ch in col:
                n = n * 26 + (ord(ch) - ord('A') + 1)
            return n

        def repl(match):
            letters, row_str = match.groups()
            col = col_to_num(letters) + dc
            row = int(row_str) + dr
            return cell_name_func(row - 1, col)

        return "=" + ref_re.sub(repl, formula[1:])

    def keyPressEvent(self, event):  # noqa: N802 - Qt naming convention
        clipboard = QApplication.clipboard()
        model = self.model()
        selection_model = self.selectionModel()
        indexes = sorted(selection_model.selectedIndexes(), key=lambda i: (i.row(), i.column()))

        if event.matches(QKeySequence.StandardKey.Undo):
            command_history_service.undo()
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.Redo):
            command_history_service.redo()
            event.accept()
            return
        if (
            event.modifiers() == Qt.KeyboardModifier.ControlModifier
            and event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right)
        ):
            self._ctrl_arrow(event.key())
            event.accept()
            return
        if (
            event.modifiers()
            == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
            and event.key() == Qt.Key.Key_L
        ):
            self._toggle_filter()
            event.accept()
            return

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

    def _ctrl_arrow(self, key):
        model = self.model()
        idx = self.currentIndex()
        row, col = idx.row(), idx.column()
        if key == Qt.Key.Key_Up:
            row = 0
        elif key == Qt.Key.Key_Down:
            row = model.rowCount() - 1
        elif key == Qt.Key.Key_Left:
            col = 0
        elif key == Qt.Key.Key_Right:
            col = model.columnCount() - 1
        self.setCurrentIndex(model.index(row, col))

    def _toggle_filter(self):
        self.setSortingEnabled(not self.isSortingEnabled())

    # Context menu ---------------------------------------------------
    def contextMenuEvent(self, event):  # noqa: N802 - Qt naming convention
        menu = QMenu(self)
        
        # Standard operations
        cut_action = QAction("Cut", self)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        
        copy_action = QAction("Copy", self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        
        paste_action = QAction("Paste", self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        
        delete_action = QAction("Delete", self)
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        
        rename_action = QAction("Rename", self)
        rename_action.setShortcut(Qt.Key.Key_F2)
        
        # Table operations
        insert_row = QAction("Insert Row", self)
        insert_row.setShortcut(QKeySequence("Ctrl+I"))
        
        delete_row = QAction("Delete Row", self)
        delete_row.setShortcut(QKeySequence("Ctrl+Shift+I"))
        
        insert_col = QAction("Insert Column", self)
        insert_col.setShortcut(QKeySequence("Ctrl+L"))
        
        delete_col = QAction("Delete Column", self)
        delete_col.setShortcut(QKeySequence("Ctrl+Shift+L"))
        
        # Add actions to menu
        menu.addActions([cut_action, copy_action, paste_action, delete_action, rename_action])
        menu.addSeparator()
        menu.addActions([insert_row, delete_row, insert_col, delete_col])

        action = menu.exec(event.globalPos())
        parent = self.parent()
        if not parent:
            return
            
        if action == cut_action:
            self._cut_selected()
        elif action == copy_action:
            self._copy_selected()
        elif action == paste_action:
            self._paste_selected()
        elif action == delete_action:
            self._delete_selected()
        elif action == rename_action:
            self._rename_selected()
        elif action == insert_row:
            parent.add_comment()
        elif action == delete_row:
            parent.remove_selected_rows()
        elif action == insert_col:
            parent.add_column()
        elif action == delete_col:
            parent.remove_column()

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

    def _cut_selected(self):
        """Cut selected cells to clipboard."""
        clipboard = QApplication.clipboard()
        model = self.model()
        selection_model = self.selectionModel()
        indexes = sorted(selection_model.selectedIndexes(), key=lambda i: (i.row(), i.column()))
        
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

    def _copy_selected(self):
        """Copy selected cells to clipboard."""
        clipboard = QApplication.clipboard()
        model = self.model()
        selection_model = self.selectionModel()
        indexes = sorted(selection_model.selectedIndexes(), key=lambda i: (i.row(), i.column()))
        
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

    def _paste_selected(self):
        """Paste clipboard content to selected cells."""
        clipboard = QApplication.clipboard()
        model = self.model()
        selection_model = self.selectionModel()
        indexes = selection_model.selectedIndexes()
        
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

    def _delete_selected(self):
        """Delete content of selected cells."""
        model = self.model()
        selection_model = self.selectionModel()
        indexes = selection_model.selectedIndexes()
        
        for idx in indexes:
            model.setData(idx, "")

    def _rename_selected(self):
        """Rename selected cell (start editing)."""
        index = self.currentIndex()
        if index.isValid():
            self.edit(index)


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

        # Formatting toolbar -------------------------------------------------
        self.format_toolbar = QToolBar()
        main_layout.addWidget(self.format_toolbar)

        self.bold_action = QAction("B", self)
        self.bold_action.setCheckable(True)
        self.bold_action.triggered.connect(
            lambda: self._apply_format_to_selection(bold=self.bold_action.isChecked())
        )
        self.format_toolbar.addAction(self.bold_action)

        self.italic_action = QAction("I", self)
        self.italic_action.setCheckable(True)
        self.italic_action.triggered.connect(
            lambda: self._apply_format_to_selection(italic=self.italic_action.isChecked())
        )
        self.format_toolbar.addAction(self.italic_action)

        self.underline_action = QAction("U", self)
        self.underline_action.setCheckable(True)
        self.underline_action.triggered.connect(
            lambda: self._apply_format_to_selection(underline=self.underline_action.isChecked())
        )
        self.format_toolbar.addAction(self.underline_action)

        self.fill_action = QAction("Fill", self)
        self.fill_action.triggered.connect(self._choose_fill_color)
        self.format_toolbar.addAction(self.fill_action)

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter...")
        main_layout.addWidget(self.filter_input)

        self.table = CommentTableView(self)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectItems)
        self.table.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        main_layout.addWidget(self.table)
        self.table.setItemDelegate(CommentItemDelegate(self.table))

        self._model = CommentTableModel(self.columns, self)
        self._model.history_sync_cb = self._sync_to_service
        self.proxy_model = CommentFilterProxyModel(self)
        self.proxy_model.setSourceModel(self._model)
        self.table.setModel(self.proxy_model)
        self.table.setSortingEnabled(True)
        self.filter_input.textChanged.connect(self.proxy_model.set_filter_text)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.sectionDoubleClicked.connect(self._handle_header_double_click)
        self.table.verticalHeader().setVisible(False)

        for row_data in group.get("comments", []):
            self.add_comment(row_data, record_history=False)

        self.add_row_btn.clicked.connect(lambda: self.add_comment())
        self.remove_row_btn.clicked.connect(self.remove_selected_rows)
        self.add_col_btn.clicked.connect(self.add_column)
        self.remove_col_btn.clicked.connect(self.remove_column)

    def setFocus(self):  # noqa: N802 - Qt naming convention
        self.table.setFocus()

    def add_comment(self, values=None, record_history=True) -> None:
        """Append a new comment row."""
        if values is None:
            values = [dict(raw="", format={}, type="str") for _ in self.columns]
        if record_history:
            row = self._model.rowCount()
            cmd = InsertCommentRowCommand(self._model, row, values, self._sync_to_service)
            command_history_service.add_command(cmd)
        else:
            self._model._suspend_history = True
            self._model.set_row_values(values)
            self._model._suspend_history = False
            self._sync_to_service()

    def remove_selected_rows(self) -> None:
        """Remove all currently selected rows."""
        selection = self.table.selectionModel().selectedRows()
        rows = sorted({self.proxy_model.mapToSource(index).row() for index in selection})
        if not rows:
            return
        rows_data = []
        for r in rows:
            data = []
            for c in range(1, self._model.columnCount()):
                data.append({
                    "raw": self._model.get_raw(r, c),
                    "format": self._model.get_format(r, c),
                    "type": self._model.get_type(r, c),
                })
            rows_data.append(data)
        cmd = RemoveCommentRowsCommand(self._model, rows, rows_data, self._sync_to_service)
        command_history_service.add_command(cmd)

    def add_column(self) -> None:
        """Append a new editable column to the table."""
        col_index = self._model.columnCount()
        column_name = f"Column {col_index}"
        cmd = InsertCommentColumnCommand(self._model, col_index, column_name, self.columns, self._sync_to_service)
        command_history_service.add_command(cmd)

    def remove_column(self) -> None:
        """Remove the last column if more than one data column exists."""
        if self._model.columnCount() <= 2:
            return  # Keep at least one data column besides the serial number
        col_index = self._model.columnCount() - 1
        header = self.columns[col_index - 1]
        column_data = [
            {
                "raw": self._model.get_raw(r, col_index),
                "format": self._model.get_format(r, col_index),
                "type": self._model.get_type(r, col_index),
            }
            for r in range(self._model.rowCount())
        ]
        cmd = RemoveCommentColumnCommand(self._model, col_index, header, column_data, self.columns, self._sync_to_service)
        command_history_service.add_command(cmd)

    def _handle_header_double_click(self, section: int) -> None:
        """Prompt for a new column name when header is double-clicked."""
        if section == 0:
            return
        old_name = self.columns[section - 1]
        new_name, ok = QInputDialog.getText(self, "Rename Column", "Column name:", text=old_name)
        new_name = new_name.strip()
        if ok and new_name and new_name != old_name:
            self.columns[section - 1] = new_name
            self._model.rename_header(section, new_name)
            self._sync_to_service()

    def _sync_to_service(self) -> None:
        model = self._model
        comments = []
        for row in range(model.rowCount()):
            row_data = []
            for col in range(1, model.columnCount()):
                cell = {
                    "raw": model.get_raw(row, col),
                    "format": model.get_format(row, col),
                    "type": model.get_type(row, col),
                }
                row_data.append(cell)
            comments.append(row_data)
        comment_data_service.update_comments(self.group_id, comments, self.columns)

    # Formatting helpers ---------------------------------------------
    def _choose_fill_color(self):
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            self._apply_format_to_selection(bg_color=color.name())

    def _apply_format_to_selection(self, **fmt):
        indexes = self.table.selectionModel().selectedIndexes()
        for idx in indexes:
            source_idx = self.proxy_model.mapToSource(idx)
            if source_idx.column() == 0:
                continue
            self._model.set_cell_format(source_idx.row(), source_idx.column(), fmt)
