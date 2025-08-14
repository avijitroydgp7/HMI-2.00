# tools/dxf.py
# Utilities for importing DXF files as canvas items.

from __future__ import annotations

from typing import List, Dict, Optional

import ezdxf
from utils import constants


def _collect_entities(msp) -> List[Dict]:
    """Collect supported entities from a DXF modelspace.

    Parameters
    ----------
    msp: ezdxf.layouts.Modelspace
        The modelspace from a loaded DXF document.

    Returns
    -------
    List[Dict]
        A list of dictionaries containing ``tool_type`` and ``properties``
        for each supported entity.
    """
    items: List[Dict] = []
    min_x = float("inf")
    min_y = float("inf")

    for entity in msp:
        dxftype = entity.dxftype()
        if dxftype == "LINE":
            start = entity.dxf.start
            end = entity.dxf.end
            props = {
                "start": {"x": start[0], "y": start[1]},
                "end": {"x": end[0], "y": end[1]},
                "color": "#000000",
                "width": 1,
                "style": "solid",
            }
            items.append({"tool_type": constants.TOOL_LINE, "properties": props})
            min_x = min(min_x, start[0], end[0])
            min_y = min(min_y, start[1], end[1])
        elif dxftype == "ARC":
            center = entity.dxf.center
            radius = entity.dxf.radius
            start_angle = entity.dxf.start_angle
            end_angle = entity.dxf.end_angle
            span = end_angle - start_angle
            if span < 0:
                span += 360
            props = {
                "position": {"x": center[0] - radius, "y": center[1] - radius},
                "size": {"width": radius * 2, "height": radius * 2},
                "start_angle": start_angle,
                "span_angle": span,
                "color": "#000000",
                "width": 1,
                "style": "solid",
            }
            items.append({"tool_type": constants.TOOL_ARC, "properties": props})
            min_x = min(min_x, center[0] - radius)
            min_y = min(min_y, center[1] - radius)
        elif dxftype in ("LWPOLYLINE", "POLYLINE"):
            points = []
            if dxftype == "LWPOLYLINE":
                for x, y, *_ in entity.get_points():
                    points.append({"x": x, "y": y})
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
            else:  # POLYLINE
                for v in entity.vertices():
                    x, y, _ = v.dxf.location
                    points.append({"x": x, "y": y})
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
            props = {
                "points": points,
                "fill_color": "#00000000",
                "stroke_color": "#000000",
                "stroke_width": 1,
                "stroke_style": "solid",
            }
            items.append({"tool_type": constants.TOOL_POLYGON, "properties": props})

    if min_x == float("inf"):
        min_x = 0
        min_y = 0

    for item in items:
        t = item["tool_type"]
        props = item["properties"]
        if t == constants.TOOL_LINE:
            props["start"]["x"] -= min_x
            props["start"]["y"] -= min_y
            props["end"]["x"] -= min_x
            props["end"]["y"] -= min_y
        elif t == constants.TOOL_ARC:
            props["position"]["x"] -= min_x
            props["position"]["y"] -= min_y
        elif t == constants.TOOL_POLYGON:
            for pt in props["points"]:
                pt["x"] -= min_x
                pt["y"] -= min_y
    return items


def load_dxf(path: str) -> List[Dict]:
    """Load entities from the DXF file at ``path``."""
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    return _collect_entities(msp)


def prompt_for_dxf(parent=None) -> Optional[List[Dict]]:
    """Prompt the user to choose a DXF file and parse its entities."""
    from PyQt6.QtWidgets import QFileDialog

    file_path, _ = QFileDialog.getOpenFileName(
        parent,
        "Select DXF",
        "",
        "DXF Files (*.dxf)",
    )
    if not file_path:
        return None
    return load_dxf(file_path)