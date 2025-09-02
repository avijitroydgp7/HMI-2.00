from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any
import os
import json

from PyQt6.QtCore import Qt, QSize, QEvent, QObject
from PyQt6.QtGui import QIcon, QPixmap, QColor
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
    QSpinBox,
    QComboBox,
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

    The selected data is returned as a dictionary containing ``source``,
    ``size``, ``color`` and ``align``.
    """

    _BASE_COLORS: Dict[str, QColor] = {
        "Blue": QColor("#3498db"),
        "Red": QColor("#e74c3c"),
        "Green": QColor("#2ecc71"),
        "Orange": QColor("#e67e22"),
        "Cyan": QColor("#1abc9c"),
        "Purple": QColor("#9b59b6"),
        "Pink": QColor("#fd79a8"),
        "Teal": QColor("#008080"),
        "Indigo": QColor("#3F51B5"),
        "Crimson": QColor("#DC143C"),
        "Gray": QColor("#95a5a6"),
        "Black": QColor("#34495e"),
        "White": QColor("#ecf0f1"),
    }

    def __init__(
        self,
        icons_root: str,
        parent: Optional[QWidget] = None,
        initial: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        preview_style: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Select Icon")
        self._icons_root = icons_root
        self._selected: Optional[Tuple[str, str]] = None  # (kind, value)
        self._initial = initial or {}
        self._initial_source = source or ""
        self._preview_style = preview_style or {}

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
        # Preview button
        from tools.button.conditional_style.widgets import PreviewButton

        text = self._preview_style.get("text", "")
        self.preview_btn = PreviewButton(text)
        self.preview_btn.setFixedSize(80, 80)
        if self._preview_style.get("style_sheet"):
            self.preview_btn.setStyleSheet(self._preview_style["style_sheet"])
        base_col = self._preview_style.get("text_color")
        if base_col:
            hover_col = self._preview_style.get(
                "hover_text_color", base_col
            )
            self.preview_btn.set_text_colors(base_col, hover_col)
        font = self._preview_style.get("font")
        if font:
            self.preview_btn.set_text_font(
                font.get("family", ""),
                font.get("size", 0),
                font.get("bold", False),
                font.get("italic", False),
                font.get("underline", False),
            )
        if "offset" in self._preview_style:
            self.preview_btn.set_text_offset(self._preview_style.get("offset", 0))
        root.addWidget(self.preview_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # --- Parameter controls -------------------------------------
        params = QHBoxLayout()
        params.setContentsMargins(0, 0, 0, 0)
        params.setSpacing(12)

        # Alignment grid (3x3)
        align_box = QVBoxLayout()
        align_box.setContentsMargins(0, 0, 0, 0)
        align_box.addWidget(QLabel("Alignment:"))
        self.align_group = QButtonGroup(self)
        align_widget = QWidget()
        align_layout = QGridLayout(align_widget)
        align_layout.setContentsMargins(0, 0, 0, 0)
        align_layout.setSpacing(1)
        positions = [
            ("top_left", 0, 0),
            ("top", 0, 1),
            ("top_right", 0, 2),
            ("left", 1, 0),
            ("center", 1, 1),
            ("right", 1, 2),
            ("bottom_left", 2, 0),
            ("bottom", 2, 1),
            ("bottom_right", 2, 2),
        ]
        self._align_buttons: Dict[str, QToolButton] = {}
        for name, r, c in positions:
            btn = QToolButton()
            btn.setCheckable(True)
            btn.setFixedSize(24, 24)
            btn.setProperty("align", name)
            align_layout.addWidget(btn, r, c)
            self.align_group.addButton(btn)
            self._align_buttons[name] = btn
        align_box.addWidget(align_widget)
        params.addLayout(align_box)

        # Size selector
        size_box = QVBoxLayout()
        size_box.setContentsMargins(0, 0, 0, 0)
        size_box.addWidget(QLabel("Size:"))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 512)
        self.size_spin.setValue(48)
        size_box.addWidget(self.size_spin)
        params.addLayout(size_box)

        # Color selector (Qt icons only)
        color_box = QVBoxLayout()
        color_box.setContentsMargins(0, 0, 0, 0)
        color_box.addWidget(QLabel("Color:"))
        color_layout = QHBoxLayout()
        color_layout.setContentsMargins(0, 0, 0, 0)
        self.color_base_combo = QComboBox()
        for name, col in self._BASE_COLORS.items():
            pixmap = QPixmap(16, 16)
            pixmap.fill(col)
            self.color_base_combo.addItem(QIcon(pixmap), name)
        self.color_shade_combo = QComboBox()
        color_layout.addWidget(self.color_base_combo)
        color_layout.addWidget(self.color_shade_combo)
        color_widget = QWidget(); color_widget.setLayout(color_layout)
        color_box.addWidget(color_widget)
        params.addLayout(color_box)

        root.addLayout(params)

        # Hooks for controls
        self.size_spin.valueChanged.connect(lambda _: self._update_preview())
        self.color_base_combo.currentTextChanged.connect(self._update_shades)
        self.color_shade_combo.currentIndexChanged.connect(lambda _: self._update_preview())
        self.align_group.buttonClicked.connect(lambda _: self._update_preview())

        def _update_color_enabled():
            en = self.qt_radio.isChecked()
            self.color_base_combo.setEnabled(en)
            self.color_shade_combo.setEnabled(en)
            self._update_preview()
        self.qt_radio.toggled.connect(lambda _: _update_color_enabled())

        # Apply initial selections
        if self._initial_source.startswith("qta:"):
            self.qt_radio.setChecked(True)
        elif self._initial_source:
            self.svg_radio.setChecked(True)
        self.size_spin.setValue(int(self._initial.get("size", 48)))

        initial_color = str(self._initial.get("color", ""))
        if initial_color:
            for name in self._BASE_COLORS:
                shades = self._get_shades(name)
                for i, shade in enumerate(shades):
                    if shade.name().lower() == initial_color.lower():
                        self.color_base_combo.setCurrentText(name)
                        self._update_shades(name, i, emit=False)
                        break
                else:
                    continue
                break
        else:
            self._update_shades(self.color_base_combo.currentText(), emit=False)

        align_btn = self._align_buttons.get(self._initial.get("align", "center"))
        if align_btn:
            align_btn.setChecked(True)
        else:
            self._align_buttons.get("center").setChecked(True)

        self.qt_radio.toggled.connect(lambda s: self.stack.setCurrentIndex(0 if s else 1))

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        root.addWidget(self.button_box)

        _update_color_enabled()
        if self._initial_source:
            if self._initial_source.startswith("qta:"):
                target = self._initial_source.split(":", 1)[1]
                for btn, (_grp, full) in self._qt_meta.items():
                    if full == target:
                        self._on_select("qta", full, btn)
                        break
            else:
                target = os.path.abspath(self._initial_source)
                for btn, (_grp, path) in self._svg_meta.items():
                    if os.path.abspath(path) == target:
                        self._on_select("svg", path, btn)
                        break
        self._update_preview()

    # ---------------------- Public API ----------------------
    def selected_value(self) -> Optional[Dict[str, Any]]:
        if not self._selected:
            return None
        kind, value = self._selected
        source = f"qta:{value}" if kind == "qta" else value
        align_btn = self.align_group.checkedButton()
        align = align_btn.property("align") if align_btn else "center"
        color = ""
        if kind == "qta":
            col = self.color_shade_combo.currentData()
            if isinstance(col, QColor):
                color = col.name()
        size = int(self.size_spin.value())
        return {"source": source, "align": align, "color": color, "size": size}

    def _get_shades(self, color_name: str) -> List[QColor]:
        base = self._BASE_COLORS.get(color_name, QColor("#000000"))
        shades: List[QColor] = []
        for i in range(16):
            factor = 1.2 - (i / 15.0) * 0.6
            shades.append(
                base.lighter(int(100 * factor))
                if factor > 1.0
                else base.darker(int(100 / factor))
            )
        return shades

    def _update_shades(
        self, color_name: str, select_index: Optional[int] = None, emit: bool = True
    ):
        self.color_shade_combo.blockSignals(True)
        self.color_shade_combo.clear()
        shades = self._get_shades(color_name)
        for i, shade in enumerate(shades):
            pixmap = QPixmap(16, 16)
            pixmap.fill(shade)
            self.color_shade_combo.addItem(QIcon(pixmap), f"Shade {i+1}")
            self.color_shade_combo.setItemData(i, shade)
        self.color_shade_combo.setCurrentIndex(
            select_index if select_index is not None else 7
        )
        self.color_shade_combo.blockSignals(False)
        if emit:
            self._update_preview()

    def _update_preview(self):
        if not self._selected:
            self.preview_btn.set_icon("", None)
            return
        kind, value = self._selected
        align_btn = self.align_group.checkedButton()
        align = align_btn.property("align") if align_btn else "center"
        size = int(self.size_spin.value())
        color = ""
        if kind == "qta":
            col = self.color_shade_combo.currentData()
            if isinstance(col, QColor):
                color = col.name()
        source = f"qta:{value}" if kind == "qta" else value
        self.preview_btn.set_icon(source, color if color else None)
        self.preview_btn.set_icon_size(size)
        self.preview_btn.set_icon_alignment(align)

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
        self.qt_grid_container.installEventFilter(self)
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
        cols = self._compute_grid_cols(grid)
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
        self.svg_grid_container.installEventFilter(self)
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
        cols = self._compute_grid_cols(self.svg_grid)
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
        cols = self._compute_grid_cols(grid)
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

    def _compute_grid_cols(self, grid: QGridLayout) -> int:
        """Determine number of columns based on available width."""
        container = grid.parentWidget()
        if not container:
            return 6
        spacing = grid.horizontalSpacing() or 0
        cell = 96 + spacing  # button width + spacing
        return max(1, container.width() // cell)

    def eventFilter(self, obj: QObject, event: QEvent):
        if event.type() == QEvent.Type.Resize:
            if obj is self.qt_grid_container:
                self._reflow_grid(self.qt_grid, self._qt_items)
            elif obj is self.svg_grid_container:
                self._reflow_grid(self.svg_grid, self._svg_items)
        return super().eventFilter(obj, event)

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
        self._update_preview()
