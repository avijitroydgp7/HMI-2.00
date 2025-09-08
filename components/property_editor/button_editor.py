from __future__ import annotations

import copy
from typing import Dict, Any

from PyQt6.QtWidgets import QWidget

from services.command_history_service import command_history_service
from services.commands import (
    UpdateChildPropertiesCommand,
    BulkUpdateChildPropertiesCommand,
)
from services.screen_data_service import screen_service

from tools import button as button_tool
from tools.button.button_properties_dialog import ButtonPropertiesWidget


def _merge_into(base: Dict[str, Any], inc: Dict[str, Any]) -> Dict[str, Any]:
    """Overlay ``inc`` onto ``base`` ignoring ``None`` values (recursive)."""
    for k, v in inc.items():
        if v is None:
            continue
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge_into(base[k], v)
        else:
            base[k] = copy.deepcopy(v)
    return base


def _expand_style_props(props: Dict[str, Any]) -> Dict[str, Any]:
    """Expose style properties at the root level for widget consumption."""
    p = copy.deepcopy(props)
    style = p.get("default_style", {})
    if isinstance(style, dict):
        style_props = style.get("properties", style)
        for key in ("background_color", "text_color"):
            if key not in p and key in style_props:
                p[key] = style_props[key]
        for key in ("hover_properties", "pressed_properties", "disabled_properties"):
            if key not in p and key in style:
                p[key] = style[key]
        p.update(style_props)
    return p


def build(host) -> QWidget:
    """Build the full-featured button property editor."""

    widget = ButtonPropertiesWidget(_expand_style_props(host.current_properties))

    def _on_props_changed(new_props: Dict[str, Any]) -> None:
        guard = host._begin_edit()
        try:
            # Drop top-level duplicates emitted for compatibility
            new_props.pop("background_color", None)
            new_props.pop("text_color", None)
            processed = new_props
            if processed != host.current_properties:
                if host.current_object_id:
                    if isinstance(host.current_object_id, list):
                        update_list = []
                        for inst_id in host.current_object_id:
                            instance = screen_service.get_child_instance(
                                host.current_parent_id, inst_id
                            )
                            if instance is None:
                                continue
                            base_props = copy.deepcopy(instance.get("properties", {}))
                            old_props = copy.deepcopy(base_props)
                            _merge_into(base_props, processed)
                            if base_props != old_props:
                                update_list.append((inst_id, base_props, old_props))
                        if update_list:
                            command = BulkUpdateChildPropertiesCommand(
                                host.current_parent_id, update_list
                            )
                            command_history_service.add_command(command)
                            guard.mark_changed()
                            _merge_into(host.current_properties, processed)
                    else:
                        base_props = copy.deepcopy(host.current_properties)
                        old_props = copy.deepcopy(base_props)
                        _merge_into(base_props, processed)
                        if base_props != old_props:
                            command = UpdateChildPropertiesCommand(
                                host.current_parent_id,
                                host.current_object_id,
                                base_props,
                                old_props,
                            )
                            command_history_service.add_command(command)
                            guard.mark_changed()
                        host.current_properties = copy.deepcopy(base_props)
                else:
                    base_props = copy.deepcopy(host.current_properties)
                    _merge_into(base_props, processed)
                    button_tool.set_default_properties(base_props)
                    host.current_properties = copy.deepcopy(base_props)
        finally:
            guard.end()

    widget.properties_changed.connect(_on_props_changed)
    return widget


def update_fields(editor: ButtonPropertiesWidget, props: dict) -> None:
    """Refresh the editor from ``props``. Fields with ``None`` are cleared."""

    editor.set_properties(_expand_style_props(props))
