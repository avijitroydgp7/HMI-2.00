"""Utilities for building QPushButton style sheets.

This module centralizes generation of QSS for button widgets so that
both the design-time canvas, runtime controller and editors share the same
implementation.  Only a very small subset of CSS is required by the
application and the helper focusses on that subset.

Supported properties
--------------------
- ``background_type``: ``"Solid"`` or ``"Linear Gradient"``
- ``background_color`` / ``background_color2``
- ``gradient_type``: one of "Top to Bottom", "Bottom to Top",
  "Left to Right", "Right to Left", "Diagonal TL-BR", "Diagonal BL-TR"
- ``text_color``
- ``border_radius`` (int or dict with tl/tr/br/bl keys)
- ``border_width`` / ``border_style`` / ``border_color``
- ``font_family`` / ``font_size`` / ``font_weight`` / ``font_style`` /
  ``text_decoration``
- ``h_align`` / ``v_align``: ``left|center|right`` and ``top|middle|bottom``

The function :func:`build_button_qss` returns a single string containing the
base rules and optional ``:hover`` rules.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

_GRADIENT_STYLES = {
    "Top to Bottom": (0, 0, 0, 1),
    "Bottom to Top": (0, 1, 0, 0),
    "Left to Right": (0, 0, 1, 0),
    "Right to Left": (1, 0, 0, 0),
    "Diagonal TL-BR": (0, 0, 1, 1),
    "Diagonal BL-TR": (0, 1, 1, 0),
}


def _alignment_rule(h_align: str | None, v_align: str | None) -> Iterable[str]:
    h_map = {
        "left": "AlignLeft",
        "center": "AlignHCenter",
        "right": "AlignRight",
    }
    v_map = {
        "top": "AlignTop",
        "middle": "AlignVCenter",
        "bottom": "AlignBottom",
    }
    flags: List[str] = []
    if h_align and h_align in h_map:
        flags.append(h_map[h_align])
    if v_align and v_align in v_map:
        flags.append(v_map[v_align])
    if flags:
        yield f"qproperty-alignment: {'|'.join(flags)};"
        if h_align in ("left", "center", "right"):
            yield f"text-align: {h_align};"


def _rules(props: Dict[str, any]) -> List[str]:
    rules: List[str] = []

    bg_type = props.get("background_type", "Solid")
    bg1 = props.get("background_color")
    bg2 = props.get("background_color2")
    if bg_type == "Linear Gradient" and bg1 and bg2:
        orient = _GRADIENT_STYLES.get(props.get("gradient_type", "Top to Bottom"), (0, 0, 0, 1))
        x1, y1, x2, y2 = orient
        rules.append(
            "background-color: qlineargradient(x1:%s, y1:%s, x2:%s, y2:%s, stop:0 %s, stop:1 %s);"
            % (x1, y1, x2, y2, bg1, bg2)
        )
    elif bg1:
        rules.append(f"background-color: {bg1};")

    if props.get("text_color"):
        rules.append(f"color: {props['text_color']};")

    if props.get("font_family"):
        rules.append(f"font-family: '{props['font_family']}';")
    if props.get("font_size"):
        rules.append(f"font-size: {props['font_size']}pt;")
    if props.get("font_weight"):
        rules.append(f"font-weight: {props['font_weight']};")
    if props.get("font_style"):
        rules.append(f"font-style: {props['font_style']};")
    if props.get("text_decoration"):
        rules.append(f"text-decoration: {props['text_decoration']};")

    if props.get("padding") is not None:
        rules.append(f"padding: {int(props['padding'])}px;")

    br = props.get("border_radius")
    if isinstance(br, dict):
        rules.append(f"border-top-left-radius: {int(br.get('tl', 0))}px;")
        rules.append(f"border-top-right-radius: {int(br.get('tr', 0))}px;")
        rules.append(f"border-bottom-right-radius: {int(br.get('br', 0))}px;")
        rules.append(f"border-bottom-left-radius: {int(br.get('bl', 0))}px;")
    elif br is not None:
        rules.append(f"border-radius: {int(br)}px;")

    bw = props.get("border_width")
    if bw is not None or props.get("border_color") or props.get("border_style"):
        bw = int(bw or 0)
        bs = props.get("border_style", "solid")
        bc = props.get("border_color", "#000000")
        rules.append(f"border:{bw}px {bs} {bc};")

    rules.extend(_alignment_rule(props.get("h_align"), props.get("v_align")))

    return rules


def build_button_qss(base_props: Dict[str, any], hover_props: Optional[Dict[str, any]] = None) -> str:
    """Return a QPushButton style sheet for the provided properties.

    Parameters
    ----------
    base_props:
        Properties for the default state.
    hover_props:
        Optional properties applied when the button is hovered. Missing keys
        fall back to the values from ``base_props``.
    """

    main_rules = _rules(base_props)
    qss = "QPushButton{\n    " + "\n    ".join(main_rules) + "\n}"

    if hover_props:
        merged = dict(base_props)
        merged.update(hover_props)
        hover_rules = _rules(merged)
        qss += "\nQPushButton:hover{\n    " + "\n    ".join(hover_rules) + "\n}"
    return qss
