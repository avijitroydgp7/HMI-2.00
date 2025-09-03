from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, Callable, Set
from dataclasses import dataclass

import os

from PyQt6.QtCore import QObject, QSize, Qt
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtGui import QColor, QIcon, QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer

from runtime_simulator.data_manager import DataManager

# Reuse the designer's conditional style logic for evaluation
from tools.button.conditional_style import ConditionalStyleManager
from tools.button.runtime_style import RuntimeConditionalStyle
from tools.button.actions.constants import TriggerMode, ActionType
from utils.icon_manager import IconManager
from utils.percentage import percent_to_value


@dataclass(slots=True)
class ButtonRuntimeConfig:
    """Subset of button configuration used at runtime."""
    properties: Dict[str, Any]


class ButtonRuntimeController(QObject):
    """
    Attach runtime behavior to a QPushButton based on saved button properties.

    - Observes DataManager for tag changes to re-evaluate conditional styles.
    - Handles click/press depending on configured actions.
    - Evaluates triggers (Ordinary/On/Off/Range) before executing actions.
    """

    def __init__(self, data_mgr: DataManager, button_config: Dict[str, Any]):
        super().__init__()
        self.data_mgr = data_mgr
        self.cfg = ButtonRuntimeConfig(properties=button_config.get("properties", {}))
        self._manager = self._build_style_manager(self.cfg.properties)
        self._tag_values: Dict[str, Any] = {}
        self._tags_of_interest: Set[str] = self._collect_referenced_tags(self.cfg.properties)
        self._button: Optional[QPushButton] = None

        # Prime local cache
        for t in self._tags_of_interest:
            self._tag_values[t] = self.data_mgr.get(t)

        # Observe tag changes
        self.data_mgr.tag_changed.connect(self._on_tag_changed)

    # --- Public API -----------------------------------------------------
    def bind(self, button: QPushButton):
        """Bind the controller to a QPushButton instance."""
        self._button = button
        self._apply_style(state=None)
        # Hook runtime actions
        actions = self.cfg.properties.get("actions", [])
        if not actions:
            # Still provide visual pressed/hover state via simple styling
            button.pressed.connect(lambda: self._apply_style(state="click"))
            button.released.connect(lambda: self._apply_style(state=None))
            return

        # For now, apply first action as the primary.
        # Future: support multiple actions or composite execution.
        action = actions[0]
        a_type = action.get("action_type")
        if a_type == ActionType.BIT.value:
            mode = action.get("mode", "Momentary")
            if mode == "Momentary":
                button.pressed.connect(lambda: self._execute_bit_action(action, pressed=True))
                button.released.connect(lambda: self._execute_bit_action(action, pressed=False))
            else:
                button.clicked.connect(lambda: self._execute_bit_action(action, pressed=True))
        elif a_type == ActionType.WORD.value:
            button.clicked.connect(lambda: self._execute_word_action(action))

    # --- Tag + style handling ------------------------------------------
    def _on_tag_changed(self, name: str, value: Any):
        if name in self._tags_of_interest:
            self._tag_values[name] = value
            self._apply_style(state=None)

    def _build_style_manager(self, props: Dict[str, Any]) -> ConditionalStyleManager:
        m = ConditionalStyleManager()
        # Default/base style: copy all known style keys while excluding runtime-only fields
        base = {
            k: v
            for k, v in props.items()
            if k not in ("actions", "conditional_styles", "default_style")
        }
        m.default_style = base
        # Conditional styles
        for s in props.get("conditional_styles", []) or []:
            try:
                m.add_style(RuntimeConditionalStyle.from_dict(s))
            except Exception:
                # Skip malformed style entries in runtime
                pass
        return m

    def _apply_style(self, state: Optional[str]):
        if not self._button:
            return
        props = self._manager.get_active_style(self._tag_values, state)

        # Button geometry for proportional scaling
        h = max(self._button.height(), 1)
        w = max(self._button.width(), 1)
        min_dim = min(w, h)

        # Visual properties
        bg = props.get("background_color", "#5a6270")
        fg = props.get("text_color", "#ffffff")
        bw = percent_to_value(props.get("border_width", 0) or 0, min_dim)
        bc = props.get("border_color", "#000000")

        # Border radius (supports per-corner values)
        if any(k in props for k in ("border_radius_tl", "border_radius_tr", "border_radius_br", "border_radius_bl")):
            br_tl = percent_to_value(props.get("border_radius_tl", 0) or 0, min_dim)
            br_tr = percent_to_value(props.get("border_radius_tr", 0) or 0, min_dim)
            br_br = percent_to_value(props.get("border_radius_br", 0) or 0, min_dim)
            br_bl = percent_to_value(props.get("border_radius_bl", 0) or 0, min_dim)
            radius_css = (
                f"border-top-left-radius:{br_tl}px;"
                f"border-top-right-radius:{br_tr}px;"
                f"border-bottom-right-radius:{br_br}px;"
                f"border-bottom-left-radius:{br_bl}px;"
            )
        else:
            br = percent_to_value(props.get("border_radius", 0) or 0, min_dim)
            radius_css = f"border-radius:{br}px;"

        # Font handling
        text = str(props.get("text_value", props.get("label", "Button")))
        self._button.setText(text)
        font_size = percent_to_value(props.get("font_size", 0) or 0, h)
        font_family = props.get("font_family")
        bold = props.get("bold")
        italic = props.get("italic")
        underline = props.get("underline")
        font_css = f"font-size:{font_size}px;"
        if font_family:
            font_css += f"font-family:'{font_family}';"
        if bold:
            font_css += "font-weight:bold;"
        if italic:
            font_css += "font-style:italic;"
        if underline:
            font_css += "text-decoration:underline;"

        css = (
            "QPushButton{"
            f"background-color:{bg};color:{fg};"
            f"border:{bw}px solid {bc};"
            f"{radius_css}{font_css}"
            "}"
        )
        self._button.setStyleSheet(css)
        # ToolTip
        self._button.setToolTip(str(props.get("tooltip", "") or ""))

        # Icon handling
        icon_src = props.get("icon", "")
        if icon_src:
            size = percent_to_value(props.get("icon_size", 0) or 0, h)
            color = props.get("icon_color")
            icon = QIcon()
            if str(icon_src).startswith("qta:"):
                name = icon_src.split(":", 1)[1]
                icon = IconManager.create_icon(name, size=size, color=color)
            else:
                ext = os.path.splitext(icon_src)[1].lower()
                if ext == ".svg":
                    renderer = QSvgRenderer(icon_src)
                    if renderer.isValid():
                        pix = QPixmap(size, size)
                        pix.fill(Qt.GlobalColor.transparent)
                        p = QPainter(pix)
                        renderer.render(p)
                        p.end()
                        icon = QIcon(pix)
                else:
                    pix = QPixmap(icon_src)
                    if not pix.isNull():
                        icon = QIcon(pix)
            self._button.setIcon(icon)
            self._button.setIconSize(QSize(size, size))

    # --- Action execution -----------------------------------------------
    def _execute_bit_action(self, action: Dict[str, Any], pressed: bool):
        if not self._button:
            return
        if not self._passes_trigger(action.get("trigger")):
            return
        tgt = self._extract_tag_name(action.get("target_tag"))
        if not tgt:
            return

        mode = action.get("mode", "Momentary")
        current = bool(self.data_mgr.get(tgt))
        if mode == "Momentary":
            self.data_mgr.set(tgt, True if pressed else False)
        elif mode == "Alternate":
            self.data_mgr.set(tgt, not current)
        elif mode == "Set":
            self.data_mgr.set(tgt, True)
        elif mode == "Reset":
            self.data_mgr.set(tgt, False)

    def _execute_word_action(self, action: Dict[str, Any]):
        if not self._button:
            return
        if not self._passes_trigger(action.get("trigger")):
            return
        tgt = self._extract_tag_name(action.get("target_tag"))
        if not tgt:
            return
        mode = action.get("action_mode", "Set Value")
        lhs = self._coerce_number(self.data_mgr.get(tgt))
        rhs = self._extract_operand_value(action.get("value"))
        if rhs is None:
            return
        rhs = self._coerce_number(rhs)
        if lhs is None or rhs is None:
            return
        if mode == "Set Value":
            self.data_mgr.set(tgt, rhs)
        elif mode == "Addition":
            self.data_mgr.set(tgt, lhs + rhs)
        elif mode == "Subtraction":
            self.data_mgr.set(tgt, lhs - rhs)
        elif mode == "Multiplication":
            self.data_mgr.set(tgt, lhs * rhs)
        elif mode == "Division":
            try:
                self.data_mgr.set(tgt, lhs / rhs)
            except Exception:
                pass

    # --- Triggers --------------------------------------------------------
    def _passes_trigger(self, trigger: Optional[Dict[str, Any]]) -> bool:
        if not trigger:
            return True
        mode = trigger.get("mode", TriggerMode.ORDINARY.value)
        if mode == TriggerMode.ORDINARY.value:
            return True
        if mode in (TriggerMode.ON.value, TriggerMode.OFF.value):
            tag = self._extract_tag_name(trigger.get("tag"))
            val = bool(self.data_mgr.get(tag)) if tag else False
            return val if mode == TriggerMode.ON.value else (not val)
        if mode == TriggerMode.RANGE.value:
            op = trigger.get("operator", "==")
            op1 = self._extract_operand_value(trigger.get("operand1"))
            if op in ("between", "outside"):
                lo = self._extract_operand_value(trigger.get("lower_bound"))
                hi = self._extract_operand_value(trigger.get("upper_bound"))
                try:
                    if op == "between":
                        return lo <= op1 <= hi
                    return op1 < lo or op1 > hi
                except Exception:
                    return False
            else:
                op2 = self._extract_operand_value(trigger.get("operand2"))
                try:
                    if op == "==":
                        return op1 == op2
                    if op == "!=":
                        return op1 != op2
                    if op == ">":
                        return op1 > op2
                    if op == ">=":
                        return op1 >= op2
                    if op == "<":
                        return op1 < op2
                    if op == "<=":
                        return op1 <= op2
                except Exception:
                    return False
        return True

    # --- Helpers ---------------------------------------------------------
    def _extract_tag_name(self, data: Optional[Dict[str, Any]]) -> Optional[str]:
        if not data:
            return None
        mt = data.get("main_tag", data)
        if not isinstance(mt, dict):
            return None
        if mt.get("source") == "tag":
            val = mt.get("value") or {}
            # Prefer canonical path "[DB]::Tag" when possible for uniqueness
            db = val.get("db_name")
            tn = val.get("tag_name")
            if db and tn:
                return f"[{db}]::" + tn
            # Fallback to plain name (legacy)
            return tn
        return None

    def _extract_operand_value(self, data: Optional[Dict[str, Any]]):
        if not data:
            return None
        mt = data.get("main_tag", data)
        if not isinstance(mt, dict):
            return None
        src = mt.get("source")
        val = mt.get("value")
        if src == "constant":
            return val
        if src == "tag":
            tag = self._extract_tag_name(data)
            return self.data_mgr.get(tag) if tag else None
        return None

    def _coerce_number(self, v: Any) -> Optional[float]:
        try:
            return float(v)
        except Exception:
            return None

    def _collect_referenced_tags(self, props: Dict[str, Any]) -> Set[str]:
        tags: Set[str] = set()

        def add_from_operand(data: Optional[Dict[str, Any]]):
            tag = self._extract_tag_name(data)
            if tag:
                tags.add(tag)

        # Conditional styles
        for s in props.get('conditional_styles', []) or []:
            # condition_data can contain operands
            cd = s.get('condition_data') or {}
            add_from_operand(cd.get('tag'))
            add_from_operand(cd.get('operand1'))
            add_from_operand(cd.get('operand2'))
            add_from_operand(cd.get('lower_bound'))
            add_from_operand(cd.get('upper_bound'))

        # Actions
        for a in props.get('actions', []) or []:
            add_from_operand(a.get('target_tag'))
            add_from_operand(a.get('value'))
            tr = a.get('trigger') or {}
            add_from_operand(tr.get('tag'))
            add_from_operand(tr.get('operand1'))
            add_from_operand(tr.get('operand2'))
            add_from_operand(tr.get('lower_bound'))
            add_from_operand(tr.get('upper_bound'))

        return tags
