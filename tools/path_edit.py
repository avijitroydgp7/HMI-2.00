from __future__ import annotations

# tools/path_edit.py
# Provides editing utilities for polygon and freeform paths.

from typing import List, Optional

import copy

from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem
from PyQt6.QtGui import QPen, QBrush, QColor
from PyQt6.QtCore import QPointF, QLineF

from services.command_history_service import command_history_service
from services.commands import AddAnchorCommand, RemoveAnchorCommand, MoveAnchorCommand


class AnchorHandle(QGraphicsEllipseItem):
    """Visual handle for a single path anchor."""

    def __init__(self, index: int, pos: QPointF, tool: "PathEditTool"):
        super().__init__(-4, -4, 8, 8)
        self.index = index
        self.tool = tool
        self.setZValue(1000)  # Ensure handles are drawn on top
        self.setPen(QPen(QColor("#00ffff")))
        self.setBrush(QBrush(QColor("#00ffff")))
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsScenePositionChanges
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
        )
        self.setPos(pos)

    # Update preview while dragging
    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            self.tool._preview_move(self.index, value)
        return super().itemChange(change, value)

    # Commit move on release
    def mouseReleaseEvent(self, event):
        self.tool._commit_move(self.index, self.pos())
        super().mouseReleaseEvent(event)


class PathEditTool:
    """Interactive editor for path-based items."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.item = None
        self.handles: List[AnchorHandle] = []

    # Activation -----------------------------------------------------------
    def activate(self, item: Optional[QGraphicsItem]):
        """Begin editing ``item`` by showing its anchors."""
        self.deactivate()
        self.item = item
        if not item:
            return
        props = item.instance_data.get("properties", {})
        pts = props.get("points", [])
        base_pos = item.pos()
        for idx, pt in enumerate(pts):
            scene_pt = base_pos + QPointF(pt.get("x", 0), pt.get("y", 0))
            handle = AnchorHandle(idx, scene_pt, self)
            self.canvas.scene.addItem(handle)
            self.handles.append(handle)

    def deactivate(self):
        for h in self.handles:
            self.canvas.scene.removeItem(h)
        self.handles.clear()
        self.item = None

    def refresh(self):
        """Rebuild handles from current item data."""
        if self.item:
            self.activate(self.item)

    # Anchor manipulation --------------------------------------------------
    def _preview_move(self, index: int, new_scene_pos: QPointF):
        if not self.item:
            return
        base_pos = self.item.pos()
        rel = new_scene_pos - base_pos
        props = self.item.instance_data.get("properties", {})
        pts = props.get("points", [])
        if 0 <= index < len(pts):
            pts[index] = {"x": int(rel.x()), "y": int(rel.y())}
        self.item.update()

    def _commit_move(self, index: int, scene_pos: QPointF):
        if not self.item:
            return
        base_pos = self.item.pos()
        rel = scene_pos - base_pos
        props = self.item.instance_data.get("properties", {})
        old_props = copy.deepcopy(props)
        pts = props.get("points", [])
        if 0 <= index < len(pts):
            pts[index] = {"x": int(rel.x()), "y": int(rel.y())}
        cmd = MoveAnchorCommand(
            self.canvas.screen_id, self.item.get_instance_id(), index, pts[index], old_props
        )
        command_history_service.add_command(cmd)
        self.refresh()

    def add_anchor(self, scene_pos: QPointF):
        if not self.item:
            return
        base_pos = self.item.pos()
        insert_idx = self._find_insert_index(scene_pos)
        rel = scene_pos - base_pos
        new_point = {"x": int(rel.x()), "y": int(rel.y())}
        props = self.item.instance_data.get("properties", {})
        old_props = copy.deepcopy(props)
        pts = props.get("points", [])
        pts.insert(insert_idx, new_point)
        cmd = AddAnchorCommand(
            self.canvas.screen_id, self.item.get_instance_id(), insert_idx, new_point, old_props
        )
        command_history_service.add_command(cmd)
        self.refresh()

    def delete_selected_anchor(self) -> bool:
        if not self.item:
            return False
        for h in self.handles:
            if h.isSelected():
                props = self.item.instance_data.get("properties", {})
                old_props = copy.deepcopy(props)
                cmd = RemoveAnchorCommand(
                    self.canvas.screen_id, self.item.get_instance_id(), h.index, old_props
                )
                command_history_service.add_command(cmd)
                self.refresh()
                return True
        return False

    # Utilities ------------------------------------------------------------
    def _find_insert_index(self, scene_pos: QPointF) -> int:
        if not self.item:
            return 0
        props = self.item.instance_data.get("properties", {})
        pts = props.get("points", [])
        if len(pts) < 2:
            return len(pts)
        base_pos = self.item.pos()
        min_dist = float("inf")
        insert_idx = len(pts)
        for i in range(len(pts) - 1):
            a = base_pos + QPointF(pts[i]["x"], pts[i]["y"])
            b = base_pos + QPointF(pts[i + 1]["x"], pts[i + 1]["y"])
            idx = self._distance_to_segment(scene_pos, a, b)
            if idx < min_dist:
                min_dist = idx
                insert_idx = i + 1
        return insert_idx

    @staticmethod
    def _distance_to_segment(p: QPointF, a: QPointF, b: QPointF) -> float:
        line = QLineF(a, b)
        if line.length() == 0:
            return (p - a).manhattanLength()
        t = ((p.x() - a.x()) * (b.x() - a.x()) + (p.y() - a.y()) * (b.y() - a.y())) / line.length() ** 2
        t = max(0.0, min(1.0, t))
        proj = QPointF(a.x() + t * (b.x() - a.x()), a.y() + t * (b.y() - a.y()))
        return (p - proj).manhattanLength()