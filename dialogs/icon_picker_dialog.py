from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import os
import json

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QGridLayout,
    QWidget,
    QScrollArea,
    QToolButton,
    QDialogButtonBox,
    QStackedWidget,
    QRadioButton,
    QButtonGroup,
)

from utils.icon_manager import IconManager


class _ThumbButton(QToolButton):
    """Small checkable button showing an icon preview and name."""

    def __init__(self, text: str, icon: QIcon, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.setIcon(icon)
        self.setText(text)
        self.setIconSize(QSize(32, 32))
        self.setCheckable(True)
        # Improve density
        self.setFixedWidth(96)


class IconPickerDialog(QDialog):
    """Icon browser to select QtAwesome or SVG icons from ``lib/icon``.

    Result is available via :meth:`selected_value` as either ``"qta:<name>"``
    (e.g. ``qta:mdi.home``) or an absolute file path to an SVG under
    ``lib/icon``.
    """

    def __init__(self, icons_root: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Select Icon")
        self._icons_root = icons_root
        self._selected: Optional[Tuple[str, str]] = None  # (kind, value)

        root = QVBoxLayout(self)

        # Source toggles
        toggles = QHBoxLayout()
        self.qt_radio = QRadioButton("Qt Icon")
        self.svg_radio = QRadioButton("SVG Icon")
        self.qt_radio.setChecked(True)
        self._radio_group = QButtonGroup(self)
        self._radio_group.addButton(self.qt_radio)
        self._radio_group.addButton(self.svg_radio)
        toggles.addWidget(self.qt_radio)
        toggles.addWidget(self.svg_radio)
        toggles.addStretch()
        root.addLayout(toggles)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_qtawesome_page())
        self.stack.addWidget(self._build_svg_page())
        root.addWidget(self.stack)

        self.qt_radio.toggled.connect(lambda s: self.stack.setCurrentIndex(0 if s else 1))

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        root.addWidget(self.button_box)

    # ---------------------- Public API ----------------------
    def selected_value(self) -> Optional[str]:
        if not self._selected:
            return None
        kind, value = self._selected
        return f"qta:{value}" if kind == "qta" else value

    # ------------------- QtAwesome page ---------------------
    def _build_qtawesome_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        # Search
        search = QLineEdit(); search.setPlaceholderText("Search Qt icons (e.g. mdi.home)")
        layout.addWidget(search)

        content = QHBoxLayout()
        layout.addLayout(content)

        # Groups (categories like arrow, media ...)
        self.qt_groups = QListWidget(); self.qt_groups.setMaximumWidth(160)
        content.addWidget(self.qt_groups)

        # Grid area inside scroll area
        self.qt_grid_container = QWidget()
        self.qt_grid = QGridLayout(self.qt_grid_container)
        self.qt_grid.setSpacing(6)
        self.qt_grid.setContentsMargins(6, 6, 6, 6)

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(self.qt_grid_container)
        content.addWidget(scroll, 1)

        # Load icons from curated JSON list
        self._qt_items: List[_ThumbButton] = []
        self._qt_meta: Dict[_ThumbButton, Tuple[str, str]] = {}
        groups, names = self._get_qtawesome_icons()

        # populate groups
        self.qt_groups.addItem("All")
        for grp in groups:
            self.qt_groups.addItem(grp)

        # populate grid
        self._populate_grid(self.qt_grid, names, kind="qta")

        # hooks
        self.qt_groups.currentTextChanged.connect(lambda _: self._apply_qt_filters(search.text()))
        search.textChanged.connect(self._apply_qt_filters)

        return page

    def _get_qtawesome_icons(self) -> Tuple[List[str], List[Tuple[str, str]]]:
        """Return curated QtAwesome icons grouped by category.

        The icons are listed in ``qtawesome_icons.json`` to avoid importing
        Qt modules or scanning the full QtAwesome charmap at runtime. If that
        file is unavailable we fall back to enumerating the bundled font
        charmaps without importing ``qtawesome`` or any Qt modules."""

        groups: List[str] = []
        names: List[Tuple[str, str]] = []  # (group, full-name)
        json_path = os.path.join(os.path.dirname(__file__), "qtawesome_icons.json")
        try:
            with open(json_path, "r", encoding="utf-8") as fh:
                data: Dict[str, List[str]] = json.load(fh)
            for group, icons in data.items():
                groups.append(group)
                for full in icons:
                    names.append((group, full))
            return groups, names
        except Exception:
            # fall back to dynamic discovery of QtAwesome fonts. This avoids
            # importing Qt modules at startup which can slow down the dialog.
            pass

        try:
            import ast
            import importlib.util

            spec = importlib.util.find_spec("qtawesome")
            if not spec or not spec.submodule_search_locations:
                return groups, names

            base = spec.submodule_search_locations[0]
            init_path = os.path.join(base, "__init__.py")
            fonts_dir = os.path.join(base, "fonts")

            bundled: List[Tuple[str, str, str]] = []
            with open(init_path, "r", encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "_BUNDLED_FONTS":
                            bundled = list(ast.literal_eval(node.value))
                            break

            families: List[str] = []
            for prefix, _ttf, charmap_file in bundled:
                families.append(prefix)
                charmap_path = os.path.join(fonts_dir, charmap_file)
                try:
                    with open(charmap_path, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    for name in data:
                        names.append((prefix, f"{prefix}.{name}"))
                except Exception:
                    continue
            return families, names
        except Exception:
            # Leave groups and names empty if font resources cannot be read.
            return groups, names

    def _populate_grid(self, grid: QGridLayout, items: List[Tuple[str, str]], kind: str):
        # Clear
        while grid.count():
            item = grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # Create buttons
        self._qt_items.clear()
        self._qt_meta.clear()
        cols = 6
        r = c = 0
        for grp, full in items:
            try:
                icon = IconManager.create_icon(full)
            except Exception:
                icon = QIcon()
            btn = _ThumbButton(full.split(".", 1)[1], icon)
            btn.clicked.connect(lambda _=False, b=btn, v=full: self._on_select("qta", v, b))
            self._qt_items.append(btn)
            self._qt_meta[btn] = (grp, full)
            grid.addWidget(
                btn,
                r,
                c,
                alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            )
            c += 1
            if c >= cols:
                c = 0
                r += 1

    def _apply_qt_filters(self, text: str):
        group = self.qt_groups.currentItem().text() if self.qt_groups.currentItem() else "All"
        text = (text or "").strip().lower()
        for btn in self._qt_items:
            grp, full = self._qt_meta.get(btn, ("", ""))
            visible = (group == "All" or grp == group)
            if text:
                visible = visible and (text in full.lower())
            btn.setVisible(visible)
        self._reflow_grid(self.qt_grid, self._qt_items)

    # --------------------- SVG page -------------------------
    def _build_svg_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        # Search
        search = QLineEdit(); search.setPlaceholderText("Search SVG icons (lib/icon)")
        layout.addWidget(search)

        content = QHBoxLayout(); layout.addLayout(content)

        self.svg_groups = QListWidget(); self.svg_groups.setMaximumWidth(200)
        content.addWidget(self.svg_groups)

        self.svg_grid_container = QWidget()
        self.svg_grid = QGridLayout(self.svg_grid_container)
        self.svg_grid.setSpacing(6)
        self.svg_grid.setContentsMargins(6, 6, 6, 6)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(self.svg_grid_container)
        content.addWidget(scroll, 1)

        # Load SVG files from root
        files = self._collect_svg_files(self._icons_root)
        groups = self._group_svg(files)
        self.svg_groups.addItem("All")
        for g in groups.keys():
            self.svg_groups.addItem(g)

        self._svg_items: List[_ThumbButton] = []
        self._svg_meta: Dict[_ThumbButton, Tuple[str, str]] = {}
        self._populate_svg_grid(files)

        self.svg_groups.currentTextChanged.connect(lambda _: self._apply_svg_filters(search.text()))
        search.textChanged.connect(self._apply_svg_filters)
        return page

    def _collect_svg_files(self, root: str) -> List[str]:
        out: List[str] = []
        try:
            for name in os.listdir(root):
                if name.lower().endswith(".svg"):
                    out.append(os.path.join(root, name))
        except Exception:
            pass
        return sorted(out, key=lambda p: os.path.basename(p).lower())

    def _group_svg(self, files: List[str]) -> Dict[str, List[str]]:
        groups: Dict[str, List[str]] = {}
        for p in files:
            base = os.path.basename(p)
            key = base.split("-", 1)[0] if "-" in base else base[:1].upper()
            groups.setdefault(key, []).append(p)
        return groups

    def _populate_svg_grid(self, files: List[str]):
        while self.svg_grid.count():
            item = self.svg_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._svg_items.clear()
        self._svg_meta.clear()
        cols = 6
        r = c = 0
        for p in files:
            icon = QIcon(p)
            text = os.path.splitext(os.path.basename(p))[0]
            btn = _ThumbButton(text, icon)
            btn.clicked.connect(lambda _=False, b=btn, v=p: self._on_select("svg", v, b))
            self._svg_items.append(btn)
            grp = text.split("-", 1)[0] if "-" in text else text[:1].upper()
            self._svg_meta[btn] = (grp, p)
            self.svg_grid.addWidget(
                btn,
                r,
                c,
                alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            )
            c += 1
            if c >= cols:
                c = 0
                r += 1

    def _apply_svg_filters(self, text: str):
        group = self.svg_groups.currentItem().text() if self.svg_groups.currentItem() else "All"
        text = (text or "").strip().lower()
        for btn in self._svg_items:
            grp, path = self._svg_meta.get(btn, ("", ""))
            base = os.path.basename(path).lower()
            visible = (group == "All" or grp == group)
            if text:
                visible = visible and (text in base)
            btn.setVisible(visible)
        self._reflow_grid(self.svg_grid, self._svg_items)

    def _reflow_grid(self, grid: QGridLayout, items: List[_ThumbButton]):
        cols = 6
        r = c = 0
        for btn in items:
            grid.removeWidget(btn)
        for btn in items:
            if not btn.isVisible():
                continue
            grid.addWidget(
                btn,
                r,
                c,
                alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            )
            c += 1
            if c >= cols:
                c = 0
                r += 1

    # ------------------- Selection handling ----------------
    def _on_select(self, kind: str, value: str, btn: _ThumbButton):
        # Uncheck others in the current page
        if self.stack.currentIndex() == 0:
            items = self._qt_items
        else:
            items = self._svg_items
        for it in items:
            if it is not btn:
                it.setChecked(False)
        btn.setChecked(True)
        self._selected = (kind, value)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
