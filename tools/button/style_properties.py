from __future__ import annotations

from dataclasses import MISSING, dataclass, field, fields
from typing import Any, Dict, Iterable
import copy


@dataclass(slots=True)
class StyleProperties:
    """Encapsulates the visual properties for a button state."""

    component_type: str = "Standard Button"
    shape_style: str = "Flat"
    background_type: str = "Solid"
    background_color: str = ""
    text_color: str = ""
    border_radius: int = 0
    border_width: int = 0
    border_style: str = "solid"
    border_color: str = ""
    font_family: str = ""
    font_size: int = 0
    bold: bool = False
    italic: bool = False
    underline: bool = False
    text_type: str = "Text"
    text_value: str = ""
    comment_ref: Dict[str, Any] = field(default_factory=dict)
    h_align: str = "center"
    v_align: str = "middle"
    offset: int = 0
    icon: str = ""
    icon_size: int = 0
    icon_align: str = "center"
    icon_color: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    # --- dict-like helpers ---------------------------------------------------
    def _field_names(self) -> Iterable[str]:
        return [f.name for f in fields(self) if f.name != "extra"]

    def _as_dict(self) -> Dict[str, Any]:
        data = {name: getattr(self, name) for name in self._field_names()}
        data.update(self.extra)
        return data

    def to_dict(self) -> Dict[str, Any]:
        return copy.deepcopy(self._as_dict())

    # Mapping protocol --------------------------------------------------------
    def __getitem__(self, key):
        if key in self._field_names():
            return getattr(self, key)
        return self.extra[key]

    def __setitem__(self, key, value):
        if key in self._field_names():
            setattr(self, key, value)
        else:
            self.extra[key] = value

    def get(self, key, default=None):
        if key in self._field_names():
            return getattr(self, key)
        return self.extra.get(key, default)

    def update(self, other: Dict[str, Any]):
        for k, v in other.items():
            self[k] = v

    def __contains__(self, key):
        return key in self._field_names() or key in self.extra

    def __iter__(self):
        return iter(self.to_dict())

    def items(self):
        return self.to_dict().items()

    def keys(self):
        return self.to_dict().keys()

    def values(self):
        return self.to_dict().values()

    # Factory -----------------------------------------------------------------
    @staticmethod
    def _normalize(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize legacy keys into the new structure."""
        if "text" in data:
            if "text_value" not in data:
                data["text_value"] = data["text"]
            data.pop("text", None)
        if data.get("text_type") == "Comment" and "comment_ref" not in data:
            data["comment_ref"] = {
                "number": data.pop("comment_number", 0),
                "column": data.pop("comment_column", 0),
                "row": data.pop("comment_row", 0),
            }
        else:
            data.pop("comment_number", None)
            data.pop("comment_column", None)
            data.pop("comment_row", None)
        if "horizontal_align" in data:
            if "h_align" not in data:
                data["h_align"] = data["horizontal_align"]
            data.pop("horizontal_align", None)
        if "vertical_align" in data:
            if "v_align" not in data:
                data["v_align"] = data["vertical_align"]
            data.pop("vertical_align", None)
        if "offset_to_frame" in data:
            if "offset" not in data:
                data["offset"] = data["offset_to_frame"]
            data.pop("offset_to_frame", None)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StyleProperties":
        if not data:
            return cls()
        data = cls._normalize(dict(data))
        known = {}
        for field in fields(cls):
            if field.name == "extra":
                continue
            default_value = (
                field.default
                if field.default is not MISSING
                else field.default_factory()
                if field.default_factory is not MISSING
                else None
            )
            known[field.name] = data.pop(field.name, default_value)
        inst = cls(**known)
        inst.extra = data
        return inst
