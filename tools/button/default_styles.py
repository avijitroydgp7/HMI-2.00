"""Default button style catalog and grouping.

This module centralizes built-in button styles so they can be consumed by
the conditional style editor without bloating its code. It provides:

- `STYLE_GROUPS`: grouped styles by variant type
- `get_style_groups()`: access grouped styles
- `get_all_styles()`: flattened list of all styles
- `get_style_by_id(style_id)`: lookup helper

Each style entry is a dictionary compatible with the structure that
`tools.button.conditional_style` expects:

{
    "id": str,
    "name": str,
    "icon": str | None,
    "hover_icon": str | None,
    "properties": {
        "shape_style": str,                 # Flat | 3D | Glass | Neumorphic | Outline
        "background_type": str,             # Solid | Linear Gradient | Radial Gradient
        "background_color": str,            # #RRGGBB
        "background_color2": str | None,    # for gradients
        "gradient_type": str | None,
        "text_color": str,
        "border_radius": int,
        "border_width": int | None,
        "border_style": str | None,
        "border_color": str | None,
        "icon_size": int | None,
    },
    "hover_properties": {...},
}
"""

from typing import Dict, List, Tuple, OrderedDict as _OrderedDictType
from collections import OrderedDict


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

def _clamp(n: int) -> int:
    return 0 if n < 0 else (255 if n > 255 else n)


def _hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    s = hex_str.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    r = int(s[0:2], 16)
    g = int(s[2:4], 16)
    b = int(s[4:6], 16)
    return r, g, b


def _rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def _mix(rgb: Tuple[int, int, int], factor: float, white: bool = False) -> Tuple[int, int, int]:
    # factor in [0, 1]: 0 -> original, 1 -> target (white or black)
    tr, tg, tb = (255, 255, 255) if white else (0, 0, 0)
    r = _clamp(int(rgb[0] + (tr - rgb[0]) * factor))
    g = _clamp(int(rgb[1] + (tg - rgb[1]) * factor))
    b = _clamp(int(rgb[2] + (tb - rgb[2]) * factor))
    return r, g, b


def lighten(hex_str: str, factor: float) -> str:
    return _rgb_to_hex(_mix(_hex_to_rgb(hex_str), factor, white=True))


def darken(hex_str: str, factor: float) -> str:
    return _rgb_to_hex(_mix(_hex_to_rgb(hex_str), factor, white=False))


def contrast_text(hex_str: str) -> str:
    # WCAG-like perceived luminance to pick black/white text
    r, g, b = _hex_to_rgb(hex_str)
    luminance = 0.2126 * (r / 255) + 0.7152 * (g / 255) + 0.0722 * (b / 255)
    return "#000000" if luminance > 0.6 else "#ffffff"


# ---------------------------------------------------------------------------
# Base palettes (Material-ish)
# ---------------------------------------------------------------------------

PALETTES: List[Tuple[str, str]] = [
    ("blue", "#2196f3"),
    ("indigo", "#3f51b5"),
    ("purple", "#9c27b0"),
    ("pink", "#e91e63"),
    ("red", "#f44336"),
    ("orange", "#ff9800"),
    ("amber", "#ffc107"),
    ("yellow", "#ffeb3b"),
    ("lime", "#cddc39"),
    ("green", "#4caf50"),
    ("teal", "#009688"),
    ("cyan", "#00bcd4"),
    ("lightblue", "#03a9f4"),
    ("deeporange", "#ff5722"),
    ("brown", "#795548"),
    ("gray", "#9e9e9e"),
    ("bluegray", "#607d8b"),
    ("navy", "#001f3f"),
]


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _base_entry(_id: str, name: str, props: Dict, hover: Dict, *, icon: str = "", hover_icon: str = "") -> Dict:
    entry = {
        "id": _id,
        "name": name,
        "properties": props,
        "hover_properties": hover,
    }
    if icon:
        entry["icon"] = icon
    if hover_icon:
        entry["hover_icon"] = hover_icon
    return entry


def build_solid_variants() -> List[Dict]:
    styles: List[Dict] = []
    for key, base in PALETTES:
        text = contrast_text(base)
        hover = darken(base, 0.1)
        for shape, radius in (("Rounded", 10), ("Pill", 22)):
            props = {
                "shape_style": "Flat",
                "background_type": "Solid",
                "background_color": base,
                "text_color": text,
                "border_radius": radius,
            }
            hover_props = {"background_color": hover, "text_color": text}
            styles.append(
                _base_entry(
                    f"{key}_solid_{shape.lower()}",
                    f"{key.title()} Solid {shape}",
                    props,
                    hover_props,
                )
            )
    return styles


def build_outline_variants() -> List[Dict]:
    styles: List[Dict] = []
    for key, base in PALETTES:
        text = base
        bg_hover = lighten(base, 0.85)  # very light tint
        for shape, radius in (("Rounded", 10), ("Pill", 22)):
            props = {
                "shape_style": "Outline",
                "background_type": "Solid",
                "background_color": "transparent",
                "text_color": text,
                "border_radius": radius,
                "border_width": 2,
                "border_style": "solid",
                "border_color": base,
            }
            hover_props = {"background_color": bg_hover, "text_color": contrast_text(bg_hover)}
            styles.append(
                _base_entry(
                    f"{key}_outline_{shape.lower()}",
                    f"{key.title()} Outline {shape}",
                    props,
                    hover_props,
                )
            )
    return styles


def build_gradient_variants() -> List[Dict]:
    styles: List[Dict] = []
    for key, base in PALETTES:
        c2 = lighten(base, 0.25)
        text = contrast_text(base)
        hover = lighten(base, 0.08)
        props = {
            "shape_style": "Flat",
            "background_type": "Linear Gradient",
            "background_color": base,
            "background_color2": c2,
            "gradient_type": "Top to Bottom",
            "text_color": text,
            "border_radius": 10,
            "border_width": 2,
            "border_style": "solid",
            "border_color": base,
        }
        hover_props = {"background_color": hover, "text_color": text}
        styles.append(
            _base_entry(
                f"{key}_gradient_rounded",
                f"{key.title()} Gradient Rounded",
                props,
                hover_props,
            )
        )
    return styles


def build_glass_variants() -> List[Dict]:
    # A smaller curated set to avoid exploding counts
    glass_keys = ["blue", "indigo", "purple", "teal", "gray", "navy"]
    styles: List[Dict] = []
    for key, base in PALETTES:
        if key not in glass_keys:
            continue
        text = contrast_text(base)
        props = {
            "shape_style": "Glass",
            "background_type": "Linear Gradient",
            "background_color": lighten(base, 0.35),
            "background_color2": darken(base, 0.15),
            "gradient_type": "Top to Bottom",
            "text_color": text,
            "border_radius": 14,
            "border_width": 1,
            "border_style": "solid",
            "border_color": lighten(base, 0.4),
        }
        hover_props = {"background_color": lighten(base, 0.45)}
        styles.append(
            _base_entry(
                f"{key}_glass_rounded",
                f"{key.title()} Glass Rounded",
                props,
                hover_props,
            )
        )
    return styles


def build_neumorphic_variants() -> List[Dict]:
    styles: List[Dict] = []
    # Neumorphic looks best on light greys
    bases = [
        ("softgray", "#e0e0e0"),
        ("paper", "#f3f3f3"),
        ("ash", "#d9d9d9"),
    ]
    for key, base in bases:
        text = "#333333"
        hover = lighten(base, 0.04)
        props = {
            "shape_style": "Neumorphic",
            "background_type": "Solid",
            "background_color": base,
            "text_color": text,
            "border_radius": 16,
        }
        styles.append(
            _base_entry(
                f"{key}_neumorphic_soft",
                f"{key.title()} Neumorphic Soft",
                props,
                {"background_color": hover, "text_color": text},
            )
        )
    return styles


def build_icon_variants() -> List[Dict]:
    # A few icon-centric circle buttons using available assets
    icons = [
        ("play", "play-circle-svgrepo-com.svg"),
        ("pause", "pause-circle-svgrepo-com.svg"),
        ("stop", "stop-circle-svgrepo-com.svg"),
        ("settings", "settings-svgrepo-com.svg"),
        ("user", "user-circle-svgrepo-com.svg"),
        ("bell", "bell-svgrepo-com.svg"),
        ("camera", "camera-square-svgrepo-com.svg"),
        ("download", "arrow-to-line-down-svgrepo-com.svg"),
    ]
    base = "#ffffff"
    text = "#333333"
    hover = "#f0f0f0"
    styles: List[Dict] = []
    for key, filename in icons:
        path = f"lib/icon/{filename}"
        props = {
            "shape_style": "Flat",
            "background_type": "Solid",
            "background_color": base,
            "text_color": text,
            "border_radius": 50,
            "border_width": 1,
            "border_style": "solid",
            "border_color": "#cccccc",
            "icon_size": 28,
        }
        styles.append(
            _base_entry(
                f"icon_{key}",
                f"Icon {key.title()}",
                props,
                {"background_color": hover},
                icon=path,
                hover_icon=path,
            )
        )
    return styles


# ---------------------------------------------------------------------------
# Legacy curated styles (carryover to preserve IDs like "default_rounded")
# ---------------------------------------------------------------------------

LEGACY_STYLES: List[Dict] = [
    {
        "id": "default_rounded",
        "name": "Default Rounded",
        "properties": {
            "background_color": "#5a6270",
            "text_color": "#ffffff",
            "border_radius": 20,
        },
        "hover_properties": {
            "background_color": "#6b7383",
            "text_color": "#ffffff",
        },
    },
    {
        "id": "warning_pill",
        "name": "Warning Pill",
        "properties": {
            "background_color": "#ff9800",
            "text_color": "#000000",
            "border_radius": 20,
        },
        "hover_properties": {
            "background_color": "#ffb74d",
            "text_color": "#000000",
        },
    },
    {
        "id": "danger_flat",
        "name": "Danger Flat",
        "properties": {
            "background_color": "#f44336",
            "text_color": "#ffffff",
            "border_radius": 0,
        },
        "hover_properties": {
            "background_color": "#e53935",
            "text_color": "#ffffff",
        },
    },
    {
        "id": "gradient_blue",
        "name": "Gradient Blue",
        "properties": {
            "background_type": "Linear Gradient",
            "background_color": "#4facfe",
            "background_color2": "#00f2fe",
            "gradient_type": "Top to Bottom",
            "text_color": "#ffffff",
            "border_radius": 10,
            "border_width": 2,
            "border_style": "solid",
            "border_color": "#4facfe",
        },
        "hover_properties": {
            "background_color": "#00f2fe",
            "text_color": "#ffffff",
        },
    },
    {
        "id": "outline_primary",
        "name": "Outline Primary",
        "properties": {
            "background_color": "transparent",
            "text_color": "#1976d2",
            "border_radius": 5,
            "border_width": 2,
            "border_style": "solid",
            "border_color": "#1976d2",
        },
        "hover_properties": {
            "background_color": "#1976d2",
            "text_color": "#ffffff",
        },
    },
    {
        "id": "neumorphic_soft",
        "name": "Neumorphic Soft",
        "properties": {
            "background_color": "#e0e0e0",
            "text_color": "#333333",
            "border_radius": 15,
            "shape_style": "Neumorphic",
        },
        "hover_properties": {
            "background_color": "#e8e8e8",
            "text_color": "#333333",
        },
    },
    {
        "id": "icon_play",
        "name": "Icon Play",
        "icon": "lib/icon/bolt-circle-svgrepo-com.svg",
        "properties": {
            "background_color": "#ffffff",
            "text_color": "#333333",
            "border_radius": 50,
            "border_width": 1,
            "border_style": "solid",
            "border_color": "#cccccc",
            "icon_size": 32,
        },
        "hover_properties": {
            "background_color": "#f0f0f0",
        },
    },
]


# ---------------------------------------------------------------------------
# Public catalog
# ---------------------------------------------------------------------------

STYLE_GROUPS: "_OrderedDictType[str, List[Dict]]" = OrderedDict()

# Group: Solid
STYLE_GROUPS["Solid"] = LEGACY_STYLES[:1] + build_solid_variants()

# Group: Outline
STYLE_GROUPS["Outline"] = [s for s in LEGACY_STYLES if s["id"] == "outline_primary"] + build_outline_variants()

# Group: Gradient
STYLE_GROUPS["Gradient"] = [s for s in LEGACY_STYLES if s["id"] == "gradient_blue"] + build_gradient_variants()

# Group: Glass
STYLE_GROUPS["Glass"] = build_glass_variants()

# Group: Neumorphic
STYLE_GROUPS["Neumorphic"] = [s for s in LEGACY_STYLES if s["id"] == "neumorphic_soft"] + build_neumorphic_variants()

# Group: Icons
STYLE_GROUPS["Icon"] = [s for s in LEGACY_STYLES if s["id"] == "icon_play"] + build_icon_variants()


def get_style_groups() -> "_OrderedDictType[str, List[Dict]]":
    """Return grouped default styles by variant type."""
    return STYLE_GROUPS


def get_all_styles() -> List[Dict]:
    """Return a flattened list of all default styles (50+)."""
    out: List[Dict] = []
    seen = set()
    for group in STYLE_GROUPS.values():
        for s in group:
            if s["id"] in seen:
                continue
            seen.add(s["id"])
            out.append(s)
    return out


def get_style_by_id(style_id: str) -> Dict:
    """Find a style entry by ID. Falls back to the first available style."""
    for s in get_all_styles():
        if s.get("id") == style_id:
            return s
    # default
    return get_all_styles()[0]

