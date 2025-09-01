from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, Callable, Set
from dataclasses import dataclass

from PyQt6.QtCore import QObject, QSize, Qt
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtGui import QColor, QIcon

from runtime_simulator.data_manager import DataManager

# Reuse the designer's conditional style logic for evaluation
from tools.button.conditional_style import ConditionalStyleManager
from tools.button.style_builder import build_button_qss
from tools.button.runtime_style import RuntimeConditionalStyle
from tools.button.actions.constants import TriggerMode, ActionType
from utils.icon_manager import IconManager


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
        # Default/base
        m.default_style = {
            'background_color': props.get('background_color', '#5a6270'),
            'text_color': props.get('text_color', '#ffffff'),
            'label': props.get('label', 'Button'),
            'border_radius': props.get('border_radius', 5),
            'border_width': props.get('border_width', 0),
            'border_color': props.get('border_color', '#000000'),
            'font_size': props.get('font_size', 10),
            'font_weight': props.get('font_weight', 'normal'),
            'opacity': props.get('opacity', 1.0),
        }
        # Conditional styles
        for s in props.get('conditional_styles', []) or []:
            try:
                m.add_style(RuntimeConditionalStyle.from_dict(s))
            except Exception:
                # Skip malformed style entries in runtime
                pass
        return m

    def _apply_style(self, state: Optional[str]):
        if not self._button:
            return
        base = self._manager.get_active_style(self._tag_values, state)
        hover = self._manager.get_active_style(self._tag_values, "hover")
        qss = build_button_qss(base, hover)
        self._button.setStyleSheet(qss)
        self._button.setText(str(base.get('label', 'Button')))
        # Alignment via property to support qproperty-alignment
        h_map = {
            'left': Qt.AlignmentFlag.AlignLeft,
            'center': Qt.AlignmentFlag.AlignHCenter,
            'right': Qt.AlignmentFlag.AlignRight,
        }
        v_map = {
            'top': Qt.AlignmentFlag.AlignTop,
            'middle': Qt.AlignmentFlag.AlignVCenter,
            'bottom': Qt.AlignmentFlag.AlignBottom,
        }
        h_align = h_map.get(base.get('h_align', 'center'), Qt.AlignmentFlag.AlignHCenter)
        v_align = v_map.get(base.get('v_align', 'middle'), Qt.AlignmentFlag.AlignVCenter)
        self._button.setProperty('alignment', h_align | v_align)

        # Icons
        icon_path = base.get('icon', '')
        hover_icon = hover.get('icon', icon_path)
        icon_size = base.get('icon_size')
        if hasattr(self._button, 'set_icon'):
            self._button.set_icon(icon_path)
            self._button.set_hover_icon(hover_icon)
            if icon_size and hasattr(self._button, 'set_icon_size'):
                self._button.set_icon_size(int(icon_size))
        else:
            if icon_path:
                if icon_path.startswith('qta:'):
                    icon = IconManager.create_icon(icon_path.split(':', 1)[1])
                else:
                    icon = QIcon(icon_path)
                if icon_size:
                    self._button.setIconSize(QSize(int(icon_size), int(icon_size)))
                self._button.setIcon(icon)

        # ToolTip
        self._button.setToolTip(str(base.get('tooltip', '') or ''))

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
