"""Shared UI theme constants and QSS helpers for MangaTranslate."""

import copy
import json
import os
import re


BASE_DARK_COLORS = {
    "bg": "#090a0f",
    "panel": "#0e111a",
    "card": "#111827",
    "card_alt": "#0f172a",
    "border": "#1e293b",
    "accent": "#38bdf8",
    "accent_hover": "#7dd3fc",
    "text": "#cbd5e1",
    "muted": "#64748b",
    "success": "#4ade80",
    "warning": "#facc15",
    "danger": "#f87171",
}

BASE_LIGHT_COLORS = {
    "bg": "#f7f8fb",
    "panel": "#ffffff",
    "card": "#ffffff",
    "card_alt": "#eef2f7",
    "border": "#d8dee8",
    "accent": "#2563eb",
    "accent_hover": "#1d4ed8",
    "text": "#172033",
    "muted": "#667085",
    "success": "#16a34a",
    "warning": "#ca8a04",
    "danger": "#dc2626",
}


def _palette(base: dict, **overrides) -> dict:
    colors = dict(base)
    colors.update(overrides)
    return colors


DARK_THEME_CHOICES = [
    ("absolutely", "Absolutely"),
    ("ayu", "Ayu"),
    ("catppuccin", "Catppuccin"),
    ("codex", "Codex"),
    ("dracula", "Dracula"),
    ("everforest", "Everforest"),
    ("github", "GitHub"),
    ("gruvbox", "Gruvbox"),
    ("linear", "Linear"),
    ("lobster", "Lobster"),
    ("material", "Material"),
    ("matrix", "Matrix"),
    ("monokai", "Monokai"),
    ("night_owl", "Night Owl"),
    ("nord", "Nord"),
    ("notion", "Notion"),
    ("one", "One"),
    ("oscurange", "Oscurange"),
    ("raycast", "Raycast"),
    ("rose_pine", "Rose Pine"),
    ("sentry", "Sentry"),
    ("solarized", "Solarized"),
    ("temple", "Temple"),
    ("tokyo_night", "Tokyo Night"),
    ("vercel", "Vercel"),
    ("vs_code_plus", "VS Code Plus"),
    ("xcode", "Xcode"),
]

DARK_THEME_PRESETS = {
    "absolutely": _palette(BASE_DARK_COLORS, bg="#16110f", panel="#201a17", card="#2b211c", card_alt="#1b1512", border="#3f3028", accent="#f28c52", accent_hover="#ffb077", text="#f4eee9", muted="#9d8d82"),
    "ayu": _palette(BASE_DARK_COLORS, bg="#0b0e14", panel="#11151c", card="#171b24", card_alt="#0f141b", border="#2d3640", accent="#ffcc66", accent_hover="#ffd580", text="#e6e1cf", muted="#8a9199"),
    "catppuccin": _palette(BASE_DARK_COLORS, bg="#11111b", panel="#181825", card="#1e1e2e", card_alt="#181825", border="#313244", accent="#89b4fa", accent_hover="#b4befe", text="#cdd6f4", muted="#9399b2"),
    "codex": dict(BASE_DARK_COLORS),
    "dracula": _palette(BASE_DARK_COLORS, bg="#171923", panel="#1f2233", card="#282a36", card_alt="#21222c", border="#44475a", accent="#bd93f9", accent_hover="#d6acff", text="#f8f8f2", muted="#9aa0b4"),
    "everforest": _palette(BASE_DARK_COLORS, bg="#1e2326", panel="#272e33", card="#2e383c", card_alt="#232a2e", border="#3c4841", accent="#a7c080", accent_hover="#dbbc7f", text="#d3c6aa", muted="#859289"),
    "github": _palette(BASE_DARK_COLORS, bg="#0d1117", panel="#161b22", card="#21262d", card_alt="#161b22", border="#30363d", accent="#2f81f7", accent_hover="#58a6ff", text="#e6edf3", muted="#7d8590"),
    "gruvbox": _palette(BASE_DARK_COLORS, bg="#1d2021", panel="#282828", card="#32302f", card_alt="#232323", border="#504945", accent="#fabd2f", accent_hover="#fe8019", text="#ebdbb2", muted="#928374"),
    "linear": _palette(BASE_DARK_COLORS, bg="#08090a", panel="#101113", card="#17191c", card_alt="#111317", border="#2a2c31", accent="#5e6ad2", accent_hover="#8b92f8", text="#f7f8f8", muted="#8a8f98"),
    "lobster": _palette(BASE_DARK_COLORS, bg="#140c12", panel="#21141d", card="#2c1a28", card_alt="#1b1118", border="#482536", accent="#ff5c7a", accent_hover="#ff8aa0", text="#ffeef3", muted="#ad8090"),
    "material": _palette(BASE_DARK_COLORS, bg="#0f111a", panel="#151824", card="#1f2233", card_alt="#121521", border="#30364a", accent="#80cbc4", accent_hover="#89ddff", text="#eeffff", muted="#717cb4"),
    "matrix": _palette(BASE_DARK_COLORS, bg="#020805", panel="#07110b", card="#0b1a10", card_alt="#06100a", border="#12331d", accent="#00ff66", accent_hover="#6dff9e", text="#d8ffe4", muted="#6bb884"),
    "monokai": _palette(BASE_DARK_COLORS, bg="#191814", panel="#272822", card="#30312a", card_alt="#20211c", border="#49483e", accent="#a6e22e", accent_hover="#e6db74", text="#f8f8f2", muted="#a59f85"),
    "night_owl": _palette(BASE_DARK_COLORS, bg="#011627", panel="#071d33", card="#0b2942", card_alt="#061a2d", border="#1d3b53", accent="#82aaff", accent_hover="#c792ea", text="#d6deeb", muted="#637777"),
    "nord": _palette(BASE_DARK_COLORS, bg="#242933", panel="#2e3440", card="#3b4252", card_alt="#252b36", border="#4c566a", accent="#88c0d0", accent_hover="#8fbcbb", text="#eceff4", muted="#a3b0c0"),
    "notion": _palette(BASE_DARK_COLORS, bg="#191919", panel="#202020", card="#2a2a2a", card_alt="#232323", border="#3b3b3b", accent="#3f7cff", accent_hover="#6aa0ff", text="#f1f1ef", muted="#9b9a97"),
    "one": _palette(BASE_DARK_COLORS, bg="#1e2127", panel="#282c34", card="#30343d", card_alt="#22252c", border="#3e4451", accent="#61afef", accent_hover="#98c379", text="#abb2bf", muted="#7f848e"),
    "oscurange": _palette(BASE_DARK_COLORS, bg="#130f0b", panel="#1d1711", card="#271d14", card_alt="#18120d", border="#463321", accent="#ff9f43", accent_hover="#ffbe76", text="#f7ead9", muted="#a78b70"),
    "raycast": _palette(BASE_DARK_COLORS, bg="#121113", panel="#1d1c20", card="#27252b", card_alt="#17161a", border="#3d3944", accent="#ff6363", accent_hover="#ff8585", text="#f4f2f7", muted="#9993a4"),
    "rose_pine": _palette(BASE_DARK_COLORS, bg="#191724", panel="#1f1d2e", card="#26233a", card_alt="#1b1928", border="#403d52", accent="#c4a7e7", accent_hover="#ebbcba", text="#e0def4", muted="#908caa"),
    "sentry": _palette(BASE_DARK_COLORS, bg="#181225", panel="#211832", card="#2a2040", card_alt="#1b1429", border="#493465", accent="#8b5cf6", accent_hover="#a78bfa", text="#f5f1ff", muted="#a59ab8"),
    "solarized": _palette(BASE_DARK_COLORS, bg="#002b36", panel="#073642", card="#0b3f4c", card_alt="#06313b", border="#27515c", accent="#2aa198", accent_hover="#268bd2", text="#eee8d5", muted="#839496"),
    "temple": _palette(BASE_DARK_COLORS, bg="#111509", panel="#1b2110", card="#242c15", card_alt="#151a0d", border="#3c4b21", accent="#b5e853", accent_hover="#d6ff7a", text="#eef7d6", muted="#9eae83"),
    "tokyo_night": _palette(BASE_DARK_COLORS, bg="#1a1b26", panel="#202331", card="#292e42", card_alt="#1f2335", border="#3b4261", accent="#7aa2f7", accent_hover="#bb9af7", text="#c0caf5", muted="#787c99"),
    "vercel": _palette(BASE_DARK_COLORS, bg="#000000", panel="#111111", card="#1a1a1a", card_alt="#0f0f0f", border="#333333", accent="#0070f3", accent_hover="#3291ff", text="#fafafa", muted="#888888"),
    "vs_code_plus": _palette(BASE_DARK_COLORS, bg="#1e1e1e", panel="#252526", card="#2d2d30", card_alt="#202020", border="#3c3c3c", accent="#3794ff", accent_hover="#4fc1ff", text="#d4d4d4", muted="#858585"),
    "xcode": _palette(BASE_DARK_COLORS, bg="#1f2430", panel="#292e3a", card="#333a49", card_alt="#242936", border="#465064", accent="#0a84ff", accent_hover="#5eb1ff", text="#f2f5fb", muted="#9aa6b8"),
}

LIGHT_THEME_CHOICES = [
    ("daylight", "Daylight"),
]

LIGHT_THEME_PRESETS = {
    "daylight": dict(BASE_LIGHT_COLORS),
}

DEFAULT_UI_FONT = "'Outfit', 'Inter', 'Segoe UI', sans-serif"
DEFAULT_CODE_FONT = "ui-monospace, 'SFMono-Regular', Menlo, Consolas, monospace"

APPEARANCE_DEFAULTS = {
    "mode": "dark",
    "dark_theme": "codex",
    "light_theme": "daylight",
    "accent": "",
    "background": "",
    "foreground": "",
    "ui_font": DEFAULT_UI_FONT,
    "code_font": DEFAULT_CODE_FONT,
    "use_pointer_cursors": True,
    "reduce_motion": "system",
    "ui_font_size": 14,
    "code_font_size": 12,
    "contrast": 60,
    "translucent_sidebar": False,
}

_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

COLORS = dict(BASE_DARK_COLORS)
FONT_FAMILY = DEFAULT_UI_FONT
CODE_FONT_FAMILY = DEFAULT_CODE_FONT
UI_FONT_SIZE = 14
CODE_FONT_SIZE = 12
ACTIVE_APPEARANCE = dict(APPEARANCE_DEFAULTS)

SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 24,
}

RADIUS = {
    "sm": 6,
    "md": 10,
    "lg": 14,
}


def appearance_defaults() -> dict:
    return copy.deepcopy(APPEARANCE_DEFAULTS)


def is_hex_color(value) -> bool:
    return isinstance(value, str) and bool(_HEX_COLOR_RE.match(value.strip()))


def _normalize_choice(value: str, allowed: set, fallback: str) -> str:
    value = str(value or "").strip().lower()
    return value if value in allowed else fallback


def normalize_appearance_settings(raw: dict | None) -> dict:
    settings = appearance_defaults()
    if isinstance(raw, dict):
        settings.update(raw)

    settings["mode"] = _normalize_choice(settings.get("mode"), {"dark", "light", "system"}, "dark")
    settings["dark_theme"] = _normalize_choice(settings.get("dark_theme"), set(DARK_THEME_PRESETS), "codex")
    settings["light_theme"] = _normalize_choice(settings.get("light_theme"), set(LIGHT_THEME_PRESETS), "daylight")
    settings["reduce_motion"] = _normalize_choice(settings.get("reduce_motion"), {"system", "reduce", "full"}, "system")

    for key in ("accent", "background", "foreground"):
        value = str(settings.get(key, "") or "").strip()
        settings[key] = value if is_hex_color(value) else ""

    for key in ("ui_font", "code_font"):
        value = str(settings.get(key, "") or "").strip()
        settings[key] = value or APPEARANCE_DEFAULTS[key]

    for key, minimum, maximum in (("ui_font_size", 10, 20), ("code_font_size", 10, 18), ("contrast", 30, 100)):
        try:
            value = int(settings.get(key, APPEARANCE_DEFAULTS[key]))
        except Exception:
            value = APPEARANCE_DEFAULTS[key]
        settings[key] = max(minimum, min(maximum, value))

    settings["use_pointer_cursors"] = bool(settings.get("use_pointer_cursors", True))
    settings["translucent_sidebar"] = bool(settings.get("translucent_sidebar", False))
    return settings


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, int(v))) for v in rgb))


def _mix_hex(first: str, second: str, weight: float) -> str:
    r1, g1, b1 = _hex_to_rgb(first)
    r2, g2, b2 = _hex_to_rgb(second)
    weight = max(0.0, min(1.0, weight))
    return _rgb_to_hex((
        r1 + (r2 - r1) * weight,
        g1 + (g2 - g1) * weight,
        b1 + (b2 - b1) * weight,
    ))


def _qss_rgba(value: str, alpha: int = 224) -> str:
    r, g, b = _hex_to_rgb(value)
    return f"rgba({r}, {g}, {b}, {max(0, min(255, int(alpha)))})"


def _color_lightness(value: str) -> float:
    r, g, b = _hex_to_rgb(value)
    return (0.299 * r) + (0.587 * g) + (0.114 * b)


def _hover_color(accent: str, bg: str) -> str:
    return _mix_hex(accent, "#ffffff" if _color_lightness(bg) < 128 else "#000000", 0.22)


def _apply_contrast(colors: dict, contrast: int) -> dict:
    if contrast == APPEARANCE_DEFAULTS["contrast"]:
        return colors
    adjusted = dict(colors)
    dark_background = _color_lightness(adjusted["bg"]) < 128
    target = "#ffffff" if dark_background else "#000000"
    border_weight = 0.12 + (contrast / 100.0) * 0.18
    muted_weight = 0.35 + (contrast / 100.0) * 0.22
    adjusted["border"] = _mix_hex(adjusted["bg"], target, border_weight)
    adjusted["muted"] = _mix_hex(adjusted["bg"], target, muted_weight)
    return adjusted


def resolve_appearance(raw: dict | None = None, system_dark: bool = True) -> dict:
    settings = normalize_appearance_settings(raw)
    mode = settings["mode"]
    effective_mode = "dark" if mode == "dark" or (mode == "system" and system_dark) else "light"
    if effective_mode == "dark":
        colors = dict(DARK_THEME_PRESETS[settings["dark_theme"]])
        preset_name = dict(DARK_THEME_CHOICES).get(settings["dark_theme"], "Codex")
    else:
        colors = dict(LIGHT_THEME_PRESETS[settings["light_theme"]])
        preset_name = dict(LIGHT_THEME_CHOICES).get(settings["light_theme"], "Daylight")

    if settings["background"]:
        colors["bg"] = settings["background"]
    if settings["foreground"]:
        colors["text"] = settings["foreground"]
    if settings["accent"]:
        colors["accent"] = settings["accent"]
        colors["accent_hover"] = _hover_color(settings["accent"], colors["bg"])

    colors = _apply_contrast(colors, settings["contrast"])
    return {
        "settings": settings,
        "colors": colors,
        "effective_mode": effective_mode,
        "preset_name": preset_name,
    }


def set_active_appearance(raw: dict | None = None, system_dark: bool = True) -> dict:
    """Resolve and store the active palette for QSS helpers."""
    global FONT_FAMILY, CODE_FONT_FAMILY, UI_FONT_SIZE, CODE_FONT_SIZE
    resolved = resolve_appearance(raw, system_dark=system_dark)
    COLORS.clear()
    COLORS.update(resolved["colors"])
    cfg = resolved["settings"]
    ACTIVE_APPEARANCE.clear()
    ACTIVE_APPEARANCE.update(cfg)
    FONT_FAMILY = cfg["ui_font"]
    CODE_FONT_FAMILY = cfg["code_font"]
    UI_FONT_SIZE = cfg["ui_font_size"]
    CODE_FONT_SIZE = cfg["code_font_size"]
    return resolved


def apply_appearance_from_settings_file(root_dir: str | None = None, settings_path: str | None = None, system_dark: bool = True) -> dict:
    """Load only the non-secret appearance block from settings.json and activate it."""
    if settings_path is None:
        if root_dir is None:
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        settings_path = os.path.join(root_dir, "settings.json")
    appearance = {}
    try:
        with open(settings_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict) and isinstance(data.get("appearance"), dict):
            appearance = data.get("appearance", {})
    except Exception:
        appearance = {}
    return set_active_appearance(appearance, system_dark=system_dark)


def table_qss(selector: str = "QTableWidget") -> str:
    return f"""
    {selector} {{
        background-color: {COLORS["panel"]};
        alternate-background-color: {COLORS["card_alt"]};
        border: 1px solid {COLORS["border"]};
        gridline-color: {COLORS["border"]};
        color: {COLORS["text"]};
        border-radius: {RADIUS["sm"]}px;
        selection-background-color: {COLORS["border"]};
        selection-color: {COLORS["accent"]};
    }}
    {selector}::item {{
        background-color: transparent;
        color: {COLORS["text"]};
        border: none;
        padding: 6px;
    }}
    {selector}::item:selected {{
        background-color: {COLORS["border"]};
        color: {COLORS["accent"]};
    }}
    {selector}::item:hover {{
        background-color: {COLORS["card_alt"]};
        color: {COLORS["text"]};
    }}
    """


def table_header_qss(selector: str = "QHeaderView::section") -> str:
    return f"""
    {selector} {{
        background-color: {COLORS["card_alt"]};
        color: {COLORS["text"]};
        border: none;
        border-bottom: 1px solid {COLORS["border"]};
        padding: 6px;
        font-weight: 600;
    }}
    """


def list_widget_qss(selector: str = "QListWidget", compact: bool = False) -> str:
    padding = "4px 6px" if compact else "7px 8px"
    margin = "1px 0px" if compact else "2px 0px"
    return f"""
    {selector} {{
        background-color: {COLORS["panel"]};
        border: 1px solid {COLORS["border"]};
        border-radius: {RADIUS["sm"]}px;
        color: {COLORS["text"]};
        outline: none;
    }}
    {selector}::item {{
        background-color: transparent;
        color: {COLORS["text"]};
        padding: {padding};
        margin: {margin};
        border-radius: {RADIUS["sm"]}px;
    }}
    {selector}::item:selected {{
        background-color: {COLORS["border"]};
        color: {COLORS["accent"]};
    }}
    {selector}::item:hover:!selected {{
        background-color: {COLORS["card_alt"]};
        color: {COLORS["text"]};
    }}
    """


def combo_popup_qss() -> str:
    return f"""
    QComboBox QAbstractItemView,
    QComboBox QListView,
    QAbstractItemView {{
        background-color: {COLORS["panel"]};
        border: 1px solid {COLORS["border"]};
        color: {COLORS["text"]};
        selection-background-color: {COLORS["accent"]};
        selection-color: {COLORS["bg"]};
        outline: none;
    }}
    QComboBox QAbstractItemView::item,
    QComboBox QListView::item,
    QAbstractItemView::item {{
        padding: 6px 8px;
        min-height: 22px;
        color: {COLORS["text"]};
    }}
    QComboBox QAbstractItemView::item:hover,
    QComboBox QListView::item:hover,
    QAbstractItemView::item:hover {{
        background-color: {COLORS["card_alt"]};
        color: {COLORS["text"]};
    }}
    QComboBox QAbstractItemView::item:selected,
    QComboBox QListView::item:selected,
    QAbstractItemView::item:selected {{
        background-color: {COLORS["accent"]};
        color: {COLORS["bg"]};
    }}
    """


def progress_bar_qss(chunk_color: str | None = None, radius: int = 4, height: int | None = None) -> str:
    height_line = f"height: {height}px;" if height is not None else ""
    return f"""
    QProgressBar {{
        background: {COLORS["border"]};
        border: none;
        border-radius: {radius}px;
        {height_line}
    }}
    QProgressBar::chunk {{
        background: {chunk_color or COLORS["accent"]};
        border-radius: {radius}px;
    }}
    """


def embedded_tool_stylesheet(root_selector: str = "QWidget") -> str:
    return f"""
    {root_selector} {{
        background-color: {COLORS["bg"]};
        color: {COLORS["text"]};
        font-family: {FONT_FAMILY};
        font-size: {UI_FONT_SIZE}px;
    }}
    {root_selector} QFrame {{
        background-color: {COLORS["panel"]};
        border: 1px solid {COLORS["border"]};
        border-radius: {RADIUS["md"]}px;
    }}
    {root_selector} QLabel {{
        color: {COLORS["text"]};
        background: transparent;
        border: none;
    }}
    {root_selector} QTextEdit,
    {root_selector} QLineEdit,
    {root_selector} QComboBox,
    {root_selector} QListWidget {{
        background-color: {COLORS["card_alt"]};
        border: 1px solid {COLORS["border"]};
        border-radius: {RADIUS["sm"]}px;
        color: {COLORS["text"]};
        selection-background-color: {COLORS["accent"]};
        selection-color: {COLORS["bg"]};
    }}
    {root_selector} QTextEdit:focus,
    {root_selector} QLineEdit:focus,
    {root_selector} QComboBox:focus {{
        border-color: {COLORS["accent"]};
    }}
    {root_selector} QComboBox::drop-down {{
        border-left: 1px solid {COLORS["border"]};
        width: 22px;
    }}
    {root_selector} QPushButton,
    {root_selector} QToolButton {{
        background-color: {COLORS["card_alt"]};
        color: {COLORS["text"]};
        border: 1px solid {COLORS["border"]};
        border-radius: {RADIUS["sm"]}px;
        padding: 6px 10px;
        font-weight: 700;
    }}
    {root_selector} QPushButton:enabled:hover,
    {root_selector} QToolButton:enabled:hover {{
        background-color: {COLORS["border"]};
        border-color: {COLORS["accent"]};
        color: {COLORS["accent"]};
    }}
    {root_selector} QPushButton:disabled,
    {root_selector} QToolButton:disabled {{
        background-color: {COLORS["panel"]};
        color: {COLORS["muted"]};
        border-color: {COLORS["border"]};
    }}
    {root_selector} QTabWidget::pane {{
        background-color: {COLORS["panel"]};
        border: 1px solid {COLORS["border"]};
        border-radius: {RADIUS["sm"]}px;
    }}
    {root_selector} QTabBar::tab {{
        background: transparent;
        color: {COLORS["muted"]};
        padding: 6px 10px;
        border-bottom: 2px solid transparent;
    }}
    {root_selector} QTabBar::tab:selected {{
        color: {COLORS["accent"]};
        border-bottom-color: {COLORS["accent"]};
    }}
    {root_selector} QSlider::groove:horizontal {{
        border: none;
        height: 4px;
        background: {COLORS["border"]};
        border-radius: 2px;
    }}
    {root_selector} QSlider::sub-page:horizontal {{
        background: {COLORS["accent"]};
        border-radius: 2px;
    }}
    {root_selector} QSlider::handle:horizontal {{
        background: {COLORS["accent"]};
        width: 12px;
        height: 12px;
        margin: -4px 0;
        border-radius: 6px;
    }}
    {root_selector} QProgressBar {{
        background: {COLORS["card_alt"]};
        border: none;
        border-radius: 3px;
    }}
    {root_selector} QProgressBar::chunk {{
        background: {COLORS["accent"]};
        border-radius: 3px;
    }}
    {combo_popup_qss()}
    {list_widget_qss(f"{root_selector} QListWidget", compact=True)}
    """


def advanced_text_editor_stylesheet() -> str:
    return f"""
    QDialog#AdvancedTextEditDialog {{
        background: {COLORS["bg"]};
        color: {COLORS["text"]};
        font-family: {FONT_FAMILY};
        font-size: {UI_FONT_SIZE}px;
    }}
    QFrame#ate-hero {{
        border: 1px solid {COLORS["border"]};
        border-radius: {RADIUS["md"]}px;
        background: {COLORS["panel"]};
        padding: 10px;
    }}
    #ate-title {{
        font-size: 16px;
        font-weight: 700;
        color: {COLORS["text"]};
    }}
    #ate-subtitle {{
        color: {COLORS["muted"]};
    }}
    QGroupBox {{
        background: {COLORS["panel"]};
        border: 1px solid {COLORS["border"]};
        border-radius: {RADIUS["md"]}px;
        margin-top: 12px;
        padding-top: 14px;
    }}
    QGroupBox::title {{
        color: {COLORS["accent"]};
        padding: 0 8px;
        font-weight: 600;
    }}
    QLabel {{
        color: {COLORS["text"]};
        background: transparent;
    }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QListWidget {{
        background: {COLORS["card_alt"]};
        border: 1px solid {COLORS["border"]};
        border-radius: {RADIUS["sm"]}px;
        padding: 6px 8px;
        color: {COLORS["text"]};
        selection-background-color: {COLORS["accent"]};
        selection-color: {COLORS["bg"]};
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {{
        border-color: {COLORS["accent"]};
    }}
    QTextEdit {{
        border-radius: {RADIUS["md"]}px;
        padding: 10px;
        line-height: 1.4;
    }}
    QPushButton, QToolButton {{
        background: {COLORS["card_alt"]};
        color: {COLORS["text"]};
        border: 1px solid {COLORS["border"]};
        border-radius: {RADIUS["sm"]}px;
        padding: 7px 12px;
        font-weight: 600;
    }}
    QPushButton:enabled:hover, QToolButton:enabled:hover {{
        background: {COLORS["border"]};
        border-color: {COLORS["accent"]};
        color: {COLORS["accent"]};
    }}
    QPushButton:disabled, QToolButton:disabled {{
        background: {COLORS["panel"]};
        color: {COLORS["muted"]};
        border-color: {COLORS["border"]};
    }}
    {combo_popup_qss()}
    {list_widget_qss("QListWidget", compact=True)}
    """


def progress_dialog_qss() -> str:
    return f"""
    QProgressDialog {{
        background-color: {COLORS["bg"]};
        color: {COLORS["text"]};
        font-family: {FONT_FAMILY};
    }}
    QLabel {{
        color: {COLORS["text"]};
        background: transparent;
    }}
    QPushButton {{
        background-color: {COLORS["border"]};
        color: {COLORS["text"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 4px;
        padding: 4px 8px;
    }}
    QPushButton:enabled:hover {{
        background-color: {COLORS["card_alt"]};
        border-color: {COLORS["accent"]};
    }}
    """


def notification_frame_qss(accent: str, radius: int = 8) -> str:
    return f"""
    QFrame#appNotification {{
        background-color: {COLORS["panel"]};
        border: 1px solid {COLORS["border"]};
        border-left: 4px solid {accent};
        border-radius: {radius}px;
    }}
    QLabel#notificationTitle {{
        color: {COLORS["text"]};
        font-family: {FONT_FAMILY};
        font-size: {UI_FONT_SIZE}px;
        font-weight: 700;
        background: transparent;
    }}
    QLabel#notificationMessage {{
        color: {COLORS["muted"]};
        font-family: {FONT_FAMILY};
        font-size: {max(10, UI_FONT_SIZE - 2)}px;
        background: transparent;
    }}
    QPushButton#notificationClose {{
        color: {COLORS["muted"]};
        background: transparent;
        border: 1px solid transparent;
        border-radius: 5px;
        font-weight: 700;
        min-width: 22px;
        min-height: 22px;
        padding: 0;
    }}
    QPushButton#notificationClose:hover {{
        color: {COLORS["text"]};
        background: {COLORS["card_alt"]};
        border-color: {COLORS["border"]};
    }}
    QPushButton#notificationAction {{
        color: {COLORS["bg"]};
        background: {accent};
        border: 0;
        border-radius: 5px;
        font-weight: 700;
        padding: 5px 10px;
    }}
    QPushButton#notificationAction:hover {{
        background: {COLORS["accent_hover"]};
    }}
    """


def app_stylesheet() -> str:
    """Global dark theme used by the main application window."""
    return f"""
    QMainWindow, QDialog {{
        background-color: {COLORS["bg"]};
        color: {COLORS["text"]};
    }}
    QWidget {{
        background-color: {COLORS["panel"]};
        color: {COLORS["text"]};
        font-size: {UI_FONT_SIZE}px;
        font-family: {FONT_FAMILY};
    }}
    QLabel {{
        padding: 2px;
        background-color: transparent;
        color: {COLORS["text"]};
    }}
    QLabel#h3 {{
        color: {COLORS["accent"]};
        font-size: 12pt;
        font-weight: 700;
        margin-top: 10px;
        border-bottom: 2px solid {COLORS["border"]};
        padding-bottom: 6px;
        text-transform: uppercase;
    }}
    QMenuBar {{
        background-color: {COLORS["bg"]};
        color: {COLORS["text"]};
        border: none;
        border-bottom: 1px solid {COLORS["border"]};
    }}
    QMenuBar::item {{
        padding: 6px 12px;
        margin: 2px;
        border-radius: {RADIUS["sm"]}px;
        background-color: transparent;
    }}
    QMenuBar::item:selected {{
        background-color: {COLORS["border"]};
        color: {COLORS["accent"]};
    }}
    QMenu {{
        background-color: {COLORS["panel"]};
        color: {COLORS["text"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 8px;
        padding: 6px;
    }}
    QMenu::item {{
        border-radius: {RADIUS["sm"]}px;
        padding: 6px 12px;
        margin: 2px 0px;
    }}
    QMenu::item:selected {{
        background-color: {COLORS["border"]};
        color: {COLORS["accent"]};
    }}
    QPushButton {{
        background-color: {COLORS["border"]};
        color: {COLORS["text"]};
        padding: 8px 14px;
        border-radius: 8px;
        border: 1px solid #334155;
        margin: 2px;
        font-weight: 600;
    }}
    QPushButton:enabled:hover {{
        background-color: {COLORS["accent"]};
        color: {COLORS["bg"]};
        border-color: {COLORS["accent"]};
    }}
    QPushButton:enabled:pressed {{
        background-color: #0284c7;
        color: #ffffff;
    }}
    QPushButton:disabled {{
        background-color: #0f131a;
        color: {COLORS["muted"]};
        border-color: {COLORS["border"]};
    }}
    QTextEdit, QPlainTextEdit, QComboBox, QListWidget, QLineEdit,
    QSpinBox, QDoubleSpinBox, QCheckBox, QRadioButton, QTableWidget {{
        background-color: {COLORS["card_alt"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 8px;
        padding: 6px 8px;
        color: {COLORS["text"]};
        selection-background-color: {COLORS["accent"]};
        selection-color: {COLORS["bg"]};
    }}
    QTextEdit:focus, QPlainTextEdit:focus, QLineEdit:focus,
    QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
        border: 1px solid {COLORS["accent"]};
    }}
    QPlainTextEdit {{
        font-family: {CODE_FONT_FAMILY};
        font-size: {CODE_FONT_SIZE}px;
    }}
    QComboBox::drop-down {{
        border: none;
        width: 26px;
    }}
    QListWidget::item {{
        padding: 8px;
        border-radius: {RADIUS["sm"]}px;
        margin: 2px 0px;
    }}
    QListWidget::item:selected {{
        background-color: {COLORS["border"]};
        color: {COLORS["accent"]};
        font-weight: 600;
    }}
    QListWidget::item:hover:!selected {{
        background-color: {COLORS["card_alt"]};
        color: {COLORS["text"]};
    }}
    {combo_popup_qss()}
    QScrollArea, QScrollArea QWidget {{
        background: transparent;
        border: none;
    }}
    QGroupBox {{
        background-color: {COLORS["panel"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 10px;
        margin-top: 14px;
        padding: 14px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 14px;
        padding: 0 8px;
        color: {COLORS["accent"]};
        font-weight: 700;
    }}
    QTabWidget::pane {{
        border: 1px solid {COLORS["border"]};
        border-radius: 10px;
        background-color: {COLORS["panel"]};
        margin-top: 8px;
    }}
    QTabBar::tab {{
        background: {COLORS["bg"]};
        color: {COLORS["muted"]};
        padding: 9px 18px;
        border: 1px solid transparent;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        margin-right: 4px;
    }}
    QTabBar::tab:selected {{
        background: {COLORS["border"]};
        color: {COLORS["accent"]};
        border-top: 2px solid {COLORS["accent"]};
    }}
    QTabBar::tab:hover:!selected {{
        background: {COLORS["card_alt"]};
        color: {COLORS["text"]};
    }}
    QProgressBar {{
        background-color: {COLORS["card_alt"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 8px;
        height: 18px;
        text-align: center;
        font-weight: 600;
    }}
    QProgressBar::chunk {{
        background-color: {COLORS["accent"]};
        border-radius: 8px;
    }}
    QStatusBar {{
        background-color: {COLORS["bg"]};
        color: {COLORS["muted"]};
        border-top: 1px solid {COLORS["border"]};
    }}
    QSplitter::handle {{
        background-color: {COLORS["border"]};
        margin: 0 6px;
    }}
    QFrame[frameShape="5"] {{
        color: {COLORS["border"]};
    }}
    QToolTip {{
        background-color: {COLORS["panel"]};
        color: {COLORS["text"]};
        border: 1px solid {COLORS["accent"]};
        border-radius: {RADIUS["sm"]}px;
        padding: 6px 8px;
    }}
    QScrollBar:vertical {{
        border: none;
        background: {COLORS["bg"]};
        width: 10px;
        margin: 0px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical {{
        background: {COLORS["border"]};
        min-height: 20px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {COLORS["accent"]};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        border: none;
        background: none;
        height: 0px;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
    }}
    QScrollBar:horizontal {{
        border: none;
        background: {COLORS["bg"]};
        height: 10px;
        margin: 0px;
        border-radius: 5px;
    }}
    QScrollBar::handle:horizontal {{
        background: {COLORS["border"]};
        min-width: 20px;
        border-radius: 5px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {COLORS["accent"]};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        border: none;
        background: none;
        width: 0px;
    }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: none;
    }}
    """


def card_qss(selector: str = "QFrame") -> str:
    return f"""
    {selector} {{
        background-color: {COLORS["card"]};
        border: 1px solid {COLORS["border"]};
        border-radius: {RADIUS["md"]}px;
        color: {COLORS["text"]};
    }}
    """


def secondary_button_qss(selector: str = "QPushButton") -> str:
    return f"""
    {selector} {{
        background-color: {COLORS["border"]};
        color: {COLORS["text"]};
        border: 1px solid #334155;
        border-radius: {RADIUS["sm"]}px;
        padding: 8px 14px;
        font-weight: 600;
    }}

    {selector}:enabled:hover {{
        background-color: #334155;
        border-color: {COLORS["accent"]};
        color: {COLORS["text"]};
    }}

    {selector}:enabled:pressed {{
        background-color: #0f172a;
    }}

    {selector}:disabled {{
        background-color: #0f131a;
        color: {COLORS["muted"]};
        border-color: {COLORS["border"]};
    }}
    """


def toggle_button_qss(selector: str = "QPushButton") -> str:
    return f"""
    {selector} {{
        background-color: {COLORS["card_alt"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 8px;
        padding: 6px 12px;
        color: {COLORS["muted"]};
        font-weight: 600;
    }}
    {selector}:enabled:hover {{
        background-color: {COLORS["border"]};
        border-color: {COLORS["accent"]};
        color: {COLORS["text"]};
    }}
    {selector}:checked {{
        background-color: {COLORS["border"]};
        border-color: {COLORS["accent"]};
        color: {COLORS["accent"]};
    }}
    """


def compact_primary_button_qss(selector: str = "QPushButton") -> str:
    return f"""
    {selector} {{
        background-color: #0c4a6e;
        color: #e0f2fe;
        border: 1px solid #0284c7;
        border-radius: 8px;
        padding: 8px 12px;
        font-weight: 700;
    }}
    {selector}:enabled:hover {{
        background-color: #0369a1;
        border-color: {COLORS["accent"]};
        color: #f0f9ff;
    }}
    {selector}:enabled:pressed {{
        background-color: #075985;
    }}
    """


def danger_button_qss(selector: str = "QPushButton") -> str:
    return f"""
    {selector} {{
        background-color: {COLORS["danger"]};
        color: {COLORS["bg"]};
        border: 1px solid {COLORS["danger"]};
        border-radius: {RADIUS["sm"]}px;
        padding: 8px 14px;
        font-weight: 700;
    }}
    {selector}:enabled:hover {{
        background-color: {COLORS["bg"]};
        border-color: {COLORS["danger"]};
        color: {COLORS["danger"]};
    }}
    {selector}:disabled {{
        background-color: {COLORS["panel"]};
        color: {COLORS["muted"]};
        border-color: {COLORS["border"]};
    }}
    """


def primary_button_qss(selector: str = "QPushButton") -> str:
    return f"""
    {selector} {{
        background-color: {COLORS["accent"]};
        color: #020617;
        border: none;
        border-radius: {RADIUS["sm"]}px;
        padding: 8px 14px;
        font-weight: 600;
    }}

    {selector}:hover {{
        background-color: {COLORS["accent_hover"]};
    }}

    {selector}:disabled {{
        background-color: {COLORS["border"]};
        color: {COLORS["muted"]};
    }}
    """


def settings_center_stylesheet() -> str:
    """Dialog-local stylesheet for the unified Settings center."""
    sidebar_bg = (
        _qss_rgba(COLORS["panel"], 226)
        if ACTIVE_APPEARANCE.get("translucent_sidebar")
        else COLORS["panel"]
    )
    return f"""
    QDialog#SettingsCenterDialog {{
        background: {COLORS["bg"]};
        color: {COLORS["text"]};
        font-family: {FONT_FAMILY};
        font-size: {UI_FONT_SIZE}px;
    }}

    #settings-nav-panel {{
        background: {sidebar_bg};
        border-right: 1px solid {COLORS["border"]};
    }}
    #settings-nav-brand {{
        background: {sidebar_bg};
        border-bottom: 1px solid {COLORS["border"]};
    }}
    #settings-brand-title {{
        color: {COLORS["text"]};
        font-size: 17pt;
        font-weight: 800;
    }}
    #settings-brand-subtitle {{
        color: {COLORS["muted"]};
        font-size: 9pt;
        line-height: 130%;
    }}
    #settings-nav-list {{
        background: {sidebar_bg};
        border: none;
        outline: none;
        color: {COLORS["text"]};
        padding: 10px 8px;
    }}
    #settings-nav-list::item {{
        border-radius: {RADIUS["md"]}px;
        margin: 3px 0;
        padding: 9px 12px;
        color: {COLORS["muted"]};
    }}
    #settings-nav-list::item:selected {{
        background: {COLORS["border"]};
        color: {COLORS["accent"]};
        font-weight: 700;
        border-left: 3px solid {COLORS["accent"]};
    }}
    #settings-nav-list::item:hover:!selected {{
        background: {COLORS["card_alt"]};
        color: {COLORS["text"]};
    }}
    #settings-nav-footer {{
        background: {sidebar_bg};
        color: {COLORS["muted"]};
        border-top: 1px solid {COLORS["border"]};
        padding: 10px 18px;
        font-size: 8.5pt;
    }}

    #settings-right-panel,
    #settings-pages,
    #settings-page-inner {{
        background: {COLORS["bg"]};
    }}
    #settings-page-header {{
        background: transparent;
        border-bottom: 1px solid {COLORS["border"]};
        padding-bottom: 14px;
    }}
    #settings-page-title {{
        color: {COLORS["text"]};
        font-size: 18pt;
        font-weight: 800;
    }}
    #settings-page-subtitle {{
        color: {COLORS["muted"]};
        font-size: 9.5pt;
    }}
    #settings-page-header-bar {{
        background: {COLORS["bg"]};
    }}
    #settings-sep {{
        color: {COLORS["border"]};
        background: {COLORS["border"]};
        max-height: 1px;
        border: none;
        margin-top: 8px;
    }}

    QGroupBox#settings-card,
    QGroupBox {{
        background: {COLORS["panel"]};
        border: 1px solid {COLORS["border"]};
        border-radius: {RADIUS["md"]}px;
        margin-top: 16px;
        padding-top: 16px;
        color: {COLORS["text"]};
    }}
    QGroupBox#settings-card::title,
    QGroupBox::title {{
        color: {COLORS["accent"]};
        font-weight: 800;
        font-size: 10pt;
        padding: 0 10px;
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 14px;
    }}
    #settings-panel-host {{
        background: transparent;
        border: none;
    }}
    #settings-option-row {{
        background: transparent;
        border: 1px solid transparent;
        border-radius: {RADIUS["sm"]}px;
    }}
    #settings-option-row:hover {{
        background: {COLORS["card_alt"]};
        border-color: {COLORS["border"]};
    }}
    #settings-option-label {{
        color: {COLORS["text"]};
        font-size: 10pt;
        font-weight: 700;
    }}
    #settings-option-desc {{
        color: {COLORS["muted"]};
        font-size: 8.8pt;
    }}

    QComboBox,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QTextEdit,
    QPlainTextEdit {{
        background: {COLORS["card_alt"]};
        border: 1px solid {COLORS["border"]};
        border-radius: {RADIUS["sm"]}px;
        padding: 7px 10px;
        color: {COLORS["text"]};
        selection-background-color: {COLORS["accent"]};
        selection-color: {COLORS["bg"]};
    }}
    QComboBox:focus,
    QLineEdit:focus,
    QSpinBox:focus,
    QDoubleSpinBox:focus,
    QTextEdit:focus,
    QPlainTextEdit:focus {{
        border-color: {COLORS["accent"]};
    }}
    QComboBox::drop-down {{
        width: 24px;
        border-left: 1px solid {COLORS["border"]};
    }}
    QComboBox QAbstractItemView {{
        background: {COLORS["card_alt"]};
        border: 1px solid {COLORS["border"]};
        color: {COLORS["text"]};
        selection-background-color: {COLORS["accent"]};
        selection-color: {COLORS["bg"]};
    }}
    {combo_popup_qss()}
    QCheckBox,
    QRadioButton {{
        color: {COLORS["text"]};
        spacing: 8px;
    }}
    QCheckBox::indicator,
    QRadioButton::indicator {{
        width: 18px;
        height: 18px;
        border: 2px solid {COLORS["border"]};
        background: {COLORS["card_alt"]};
    }}
    QCheckBox::indicator {{
        border-radius: 5px;
    }}
    QRadioButton::indicator {{
        border-radius: 9px;
    }}
    QCheckBox::indicator:checked,
    QRadioButton::indicator:checked {{
        background: {COLORS["accent"]};
        border-color: {COLORS["accent"]};
    }}
    QCheckBox::indicator:hover,
    QRadioButton::indicator:hover {{
        border-color: {COLORS["accent"]};
    }}

    QPushButton,
    QToolButton {{
        background: {COLORS["border"]};
        color: {COLORS["text"]};
        border: 1px solid #334155;
        border-radius: {RADIUS["sm"]}px;
        padding: 7px 14px;
        font-weight: 700;
    }}
    QPushButton:enabled:hover,
    QToolButton:enabled:hover {{
        background: {COLORS["accent"]};
        border-color: {COLORS["accent"]};
        color: {COLORS["bg"]};
    }}
    QPushButton:enabled:pressed,
    QToolButton:enabled:pressed {{
        background: #0284c7;
        color: #ffffff;
    }}
    QPushButton:disabled,
    QToolButton:disabled {{
        background: {COLORS["panel"]};
        color: {COLORS["muted"]};
        border-color: {COLORS["border"]};
    }}
    #settings-save-btn {{
        background: {COLORS["accent"]};
        color: #020617;
        border-color: {COLORS["accent"]};
        font-weight: 800;
    }}
    #settings-save-btn:hover {{
        background: {COLORS["accent_hover"]};
        border-color: {COLORS["accent_hover"]};
    }}
    #settings-apply-btn {{
        background: #0c4a6e;
        color: #e0f2fe;
        border-color: #0284c7;
    }}
    #settings-apply-btn:hover {{
        background: #0369a1;
        border-color: {COLORS["accent"]};
        color: #f0f9ff;
    }}
    #settings-action-btn {{
        background: #0c4a6e;
        color: #e0f2fe;
        border-color: #0284c7;
    }}
    #settings-action-btn:hover {{
        background: #0369a1;
        border-color: {COLORS["accent"]};
        color: #f0f9ff;
    }}
    #settings-cancel-btn {{
        background: transparent;
        color: {COLORS["muted"]};
        border-color: {COLORS["border"]};
    }}
    #settings-cancel-btn:hover {{
        background: {COLORS["border"]};
        color: {COLORS["text"]};
    }}
    #settings-btn-bar {{
        background: {COLORS["panel"]};
        border-top: 1px solid {COLORS["border"]};
    }}
    #settings-footer-hint {{
        color: {COLORS["muted"]};
        font-size: 8.8pt;
    }}

    QTabWidget::pane {{
        border: 1px solid {COLORS["border"]};
        background: {COLORS["panel"]};
        border-radius: {RADIUS["md"]}px;
        margin-top: 8px;
    }}
    QTabBar::tab {{
        background: {COLORS["bg"]};
        color: {COLORS["muted"]};
        border: 1px solid {COLORS["border"]};
        border-radius: {RADIUS["sm"]}px;
        padding: 7px 14px;
        margin: 2px;
    }}
    QTabBar::tab:selected {{
        background: {COLORS["border"]};
        color: {COLORS["accent"]};
        font-weight: 800;
        border-color: {COLORS["accent"]};
    }}
    QTabBar::tab:hover:!selected {{
        background: {COLORS["card_alt"]};
        color: {COLORS["text"]};
    }}

    QTableWidget {{
        background-color: {COLORS["panel"]};
        alternate-background-color: {COLORS["card_alt"]};
        border: 1px solid {COLORS["border"]};
        gridline-color: {COLORS["border"]};
        color: {COLORS["text"]};
        border-radius: {RADIUS["sm"]}px;
    }}
    QTableWidget::item {{
        background-color: transparent;
        color: {COLORS["text"]};
        border: none;
        padding: 6px;
    }}
    QTableWidget::item:selected {{
        background-color: {COLORS["border"]};
        color: {COLORS["accent"]};
    }}
    QHeaderView::section {{
        background: {COLORS["card_alt"]};
        color: {COLORS["muted"]};
        border: none;
        border-bottom: 1px solid {COLORS["border"]};
        padding: 7px;
        font-weight: 700;
    }}
    QListWidget {{
        background: {COLORS["panel"]};
        border: 1px solid {COLORS["border"]};
        color: {COLORS["text"]};
        border-radius: {RADIUS["sm"]}px;
    }}
    QListWidget::item {{
        background-color: transparent;
        color: {COLORS["text"]};
        padding: 7px;
        border-radius: {RADIUS["sm"]}px;
    }}
    QListWidget::item:selected {{
        background: {COLORS["border"]};
        color: {COLORS["accent"]};
    }}
    QListWidget::item:hover:!selected {{
        background: {COLORS["card_alt"]};
        color: {COLORS["text"]};
    }}

    QScrollArea,
    QScrollArea > QWidget > QWidget {{
        background: transparent;
        border: none;
    }}
    QScrollBar:vertical {{
        border: none;
        background: {COLORS["bg"]};
        width: 10px;
        margin: 0px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical {{
        background: {COLORS["border"]};
        min-height: 24px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {COLORS["accent"]};
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QSplitter::handle {{
        background: {COLORS["border"]};
    }}
    QLabel {{
        color: {COLORS["text"]};
        background: transparent;
    }}
    """
