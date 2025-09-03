from __future__ import annotations

import copy
from typing import Dict

from PyQt6.QtWidgets import QWidget

from services.command_history_service import command_history_service
from services.commands import UpdateChildPropertiesCommand

from tools import button as button_tool
from tools.button.button_properties_dialog import (
    ButtonPropertiesWidget,
    value_to_percent,
)


def _ensure_percentage_props(props: Dict) -> Dict:
    """Ensure numeric style properties are stored as percentages."""
    p = copy.deepcopy(props)
    size = p.get("size", {})
    w = size.get("width", 100)
    h = size.get("height", 40)
    min_dim = min(w, h)

    def conv(key, base):
        val = p.get(key)
        if val is None:
            return
        # Values greater than 100 are assumed to be absolute pixels
        if isinstance(val, (int, float)) and val > 100:
            p[key] = value_to_percent(val, base)

    conv("font_size", h)
    conv("border_radius", min_dim)
    conv("border_width", min_dim)
    conv("icon_size", min_dim)
    for k in ("border_radius_tl", "border_radius_tr", "border_radius_br", "border_radius_bl"):
        conv(k, min_dim)
    return p


def build(host) -> QWidget:
    """Build the button property editor using :class:`ButtonPropertiesWidget`."""

    widget = ButtonPropertiesWidget(_ensure_percentage_props(host.current_properties))

    def _on_props_changed(new_props: Dict) -> None:
        guard = host._begin_edit()
        try:
            processed = _ensure_percentage_props(new_props)
            if processed != host.current_properties:
                if host.current_object_id:
                    command = UpdateChildPropertiesCommand(
                        host.current_parent_id,
                        host.current_object_id,
                        processed,
                        host.current_properties,
                    )
                    command_history_service.add_command(command)
                    guard.mark_changed()
                else:
                    button_tool.set_default_properties(processed)
                host.current_properties = copy.deepcopy(processed)
        finally:
            guard.end()

    widget.properties_changed.connect(_on_props_changed)
    return widget


def update_fields(editor: ButtonPropertiesWidget, props: dict) -> None:
    """Refresh the editor from ``props``."""

    editor.set_properties(props)

