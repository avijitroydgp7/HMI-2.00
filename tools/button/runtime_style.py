from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from tools.button.actions.constants import TriggerMode


@dataclass(slots=True)
class RuntimeConditionalStyle:
    """Minimal subset of ConditionalStyle used during runtime."""

    style_id: str = ""
    condition: Optional[str] = None
    condition_data: Dict[str, Any] = field(
        default_factory=lambda: {"mode": TriggerMode.ORDINARY.value}
    )
    properties: Dict[str, Any] = field(default_factory=dict)
    hover_properties: Dict[str, Any] = field(default_factory=dict)
    tooltip: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuntimeConditionalStyle":
        """Build a RuntimeConditionalStyle from a persisted dictionary."""

        props = data.get("properties", {}) or {}
        hover = data.get("hover_properties", {}) or {}
        if "icon" in data and "icon" not in props:
            props = dict(props)
            props["icon"] = data.get("icon")
        if "hover_icon" in data and "icon" not in hover:
            hover = dict(hover)
            hover["icon"] = data.get("hover_icon")
        return cls(
            style_id=data.get("style_id", ""),
            condition=data.get("condition"),
            condition_data=data.get(
                "condition_data", {"mode": TriggerMode.ORDINARY.value}
            ),
            properties=props,
            hover_properties=hover,
            tooltip=data.get("tooltip", ""),
        )
