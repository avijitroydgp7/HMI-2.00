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
    icon: str = ""
    hover_icon: str = ""
    tooltip: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuntimeConditionalStyle":
        """Build a RuntimeConditionalStyle from a persisted dictionary."""

        return cls(
            style_id=data.get("style_id", ""),
            condition=data.get("condition"),
            condition_data=data.get(
                "condition_data", {"mode": TriggerMode.ORDINARY.value}
            ),
            properties=data.get("properties", {}),
            hover_properties=data.get("hover_properties", {}),
            icon=data.get("icon", ""),
            hover_icon=data.get("hover_icon", ""),
            tooltip=data.get("tooltip", ""),
        )
