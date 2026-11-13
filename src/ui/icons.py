"""Centralized crisp vector SVG icons (theme-aware, zero emoticons)."""

from __future__ import annotations

from functools import lru_cache

from PyQt5.QtCore import QByteArray, Qt
from PyQt5.QtGui import QIcon, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QLabel

from src.ui import theme

_SVG_HEADER = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
    'fill="none" stroke="{color}" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
)
_SVG_FOOTER = "</svg>"

_PATHS: dict[str, str] = {
    "activity": '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
    "alert": (
        '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>'
        '<line x1="12" y1="9" x2="12" y2="13"/>'
        '<circle cx="12" cy="17" r="0.8" fill="{color}"/>'
    ),
    "arrow-right": '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
    "bar-chart": (
        '<line x1="18" y1="20" x2="18" y2="10"/>'
        '<line x1="12" y1="20" x2="12" y2="4"/>'
        '<line x1="6" y1="20" x2="6" y2="14"/>'
    ),
    "book": (
        '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>'
        '<path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>'
    ),
    "check": '<polyline points="20 6 9 17 4 12"/>',
    "chevron-down": '<polyline points="6 9 12 15 18 9"/>',
    "chevron-up": '<polyline points="18 15 12 9 6 15"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15.5 14"/>',
    "copy": (
        '<rect x="9" y="9" width="11" height="11" rx="2" ry="2"/>'
        '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>'
    ),
    "cpu": (
        '<rect x="5" y="5" width="14" height="14" rx="2"/>'
        '<rect x="9" y="9" width="6" height="6"/>'
        '<line x1="9" y1="1" x2="9" y2="5"/><line x1="15" y1="1" x2="15" y2="5"/>'
        '<line x1="9" y1="19" x2="9" y2="23"/><line x1="15" y1="19" x2="15" y2="23"/>'
        '<line x1="1" y1="9" x2="5" y2="9"/><line x1="1" y1="15" x2="5" y2="15"/>'
        '<line x1="19" y1="9" x2="23" y2="9"/><line x1="19" y1="15" x2="23" y2="15"/>'
    ),
    "dollar": (
        '<line x1="12" y1="2" x2="12" y2="22"/>'
        '<path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>'
    ),
    "dot": '<circle cx="12" cy="12" r="6" fill="{color}" stroke="none"/>',
    "download": (
        '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
        '<polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>'
    ),
    "eraser": (
        '<path d="M20 20H7L3 16a2 2 0 0 1 0-2.83l9.9-9.9a2 2 0 0 1 2.83 0l5 5a2 2 0 0 1 0 2.83L12 20"/>'
        '<line x1="7" y1="11" x2="13" y2="17"/>'
    ),
    "eye": (
        '<path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/>'
        '<circle cx="12" cy="12" r="3"/>'
    ),
    "folder": (
        '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>'
    ),
    "heart": (
        '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>'
    ),
    "help": (
        '<circle cx="12" cy="12" r="9"/>'
        '<path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>'
        '<circle cx="12" cy="17" r="0.8" fill="{color}"/>'
    ),
    "history": (
        '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/>'
        '<polyline points="3 3 3 8 8 8"/>'
        '<polyline points="12 7 12 12 15 14"/>'
    ),
    "image": (
        '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>'
        '<circle cx="8.5" cy="8.5" r="1.5"/>'
        '<polyline points="21 15 16 10 5 21"/>'
    ),
    "info": (
        '<circle cx="12" cy="12" r="9"/>'
        '<line x1="12" y1="16" x2="12" y2="12"/>'
        '<circle cx="12" cy="8" r="0.8" fill="{color}"/>'
    ),
    "key": (
        '<circle cx="7.5" cy="15.5" r="4.5"/>'
        '<line x1="10.85" y1="12.15" x2="21" y2="2"/>'
        '<line x1="18" y1="5" x2="21" y2="8"/>'
        '<line x1="15" y1="8" x2="17" y2="10"/>'
    ),
    "keyboard": (
        '<rect x="2" y="5" width="20" height="14" rx="2"/>'
        '<line x1="6" y1="9" x2="6.01" y2="9"/><line x1="10" y1="9" x2="10.01" y2="9"/>'
        '<line x1="14" y1="9" x2="14.01" y2="9"/><line x1="18" y1="9" x2="18.01" y2="9"/>'
        '<line x1="7" y1="15" x2="17" y2="15"/>'
    ),
    "languages": (
        '<path d="M5 8l6 6"/><path d="M4 14l6-6 2-3"/>'
        '<path d="M2 5h12"/><path d="M7 2h1"/>'
        '<path d="M22 22l-5-10-5 10"/><path d="M14 18h6"/>'
    ),
    "layers": (
        '<polygon points="12 2 2 7 12 12 22 7 12 2"/>'
        '<polyline points="2 12 12 17 22 12"/>'
        '<polyline points="2 17 12 22 22 17"/>'
    ),
    "list": (
        '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/>'
        '<line x1="8" y1="18" x2="21" y2="18"/>'
        '<line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/>'
        '<line x1="3" y1="18" x2="3.01" y2="18"/>'
    ),
    "message": (
        '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>'
    ),
    "minus": '<line x1="5" y1="12" x2="19" y2="12"/>',
    "music": (
        '<path d="M9 18V5l12-2v13"/>'
        '<circle cx="6" cy="18" r="3"/>'
        '<circle cx="18" cy="16" r="3"/>'
    ),
    "paintbrush": (
        '<path d="M18.37 2.63L14 7l-1.59-1.59a2 2 0 0 0-2.82 0L8 7l9 9 1.59-1.59a2 2 0 0 0 0-2.82L17 10l4.37-4.37a2.12 2.12 0 1 0-3-3z"/>'
        '<path d="M9 8c-2 3-4 3.5-7 4l8 10c2-1 6-5 6-7"/>'
    ),
    "palette": (
        '<circle cx="12" cy="12" r="9"/>'
        '<path d="M12 3a9 9 0 0 0 0 18z" fill="{color}" stroke="none"/>'
    ),
    "play": '<polygon points="6 4 20 12 6 20 6 4" fill="{color}"/>',
    "plus": '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    "redo": (
        '<polyline points="15 14 20 9 15 4"/>'
        '<path d="M4 20v-7a4 4 0 0 1 4-4h12"/>'
    ),
    "refresh": (
        '<polyline points="23 4 23 10 17 10"/>'
        '<polyline points="1 20 1 14 7 14"/>'
        '<path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>'
    ),
    "rocket": (
        '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/>'
        '<path d="M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/>'
        '<path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/>'
        '<path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>'
    ),
    "save": (
        '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>'
        '<polyline points="17 21 17 13 7 13 7 21"/>'
        '<polyline points="7 3 7 8 15 8"/>'
    ),
    "scan": (
        '<path d="M3 7V5a2 2 0 0 1 2-2h2"/>'
        '<path d="M17 3h2a2 2 0 0 1 2 2v2"/>'
        '<path d="M21 17v2a2 2 0 0 1-2 2h-2"/>'
        '<path d="M7 21H5a2 2 0 0 1-2-2v-2"/>'
        '<circle cx="11" cy="11" r="4"/>'
        '<line x1="16" y1="16" x2="14" y2="14"/>'
    ),
    "search": (
        '<circle cx="11" cy="11" r="7"/>'
        '<line x1="21" y1="21" x2="16.65" y2="16.65"/>'
    ),
    "send": '<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>',
    "settings": (
        '<circle cx="12" cy="12" r="3"/>'
        '<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>'
    ),
    "shield-alert": (
        '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
        '<line x1="12" y1="8" x2="12" y2="12"/>'
        '<circle cx="12" cy="16" r="0.8" fill="{color}"/>'
    ),
    "sparkles": (
        '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/>'
        '<line x1="19" y1="3" x2="19" y2="7"/><line x1="17" y1="5" x2="21" y2="5"/>'
    ),
    "star": (
        '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>'
    ),
    "stop": '<rect x="6" y="6" width="12" height="12" rx="2" fill="{color}"/>',
    "trash": (
        '<polyline points="3 6 5 6 21 6"/>'
        '<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'
        '<line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/>'
    ),
    "trending": (
        '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>'
        '<polyline points="17 6 23 6 23 12"/>'
    ),
    "type": (
        '<polyline points="4 7 4 4 20 4 20 7"/>'
        '<line x1="9" y1="20" x2="15" y2="20"/>'
        '<line x1="12" y1="4" x2="12" y2="20"/>'
    ),
    "undo": (
        '<polyline points="9 14 4 9 9 4"/>'
        '<path d="M20 20v-7a4 4 0 0 0-4-4H4"/>'
    ),
    "user": (
        '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>'
        '<circle cx="12" cy="7" r="4"/>'
    ),
    "x": '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    "zap": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
}


def available_icons() -> tuple[str, ...]:
    """Return sorted tuple of registered SVG icon names."""
    return tuple(sorted(_PATHS.keys()))


@lru_cache(maxsize=512)
def _render_pixmap_cached(name: str, color_hex: str, size: int) -> QPixmap:
    body = _PATHS.get(name, _PATHS["dot"]).format(color=color_hex)
    svg = f"{_SVG_HEADER.format(color=color_hex)}{body}{_SVG_FOOTER}".encode("utf-8")
    scale = 2
    px_size = max(8, int(size)) * scale
    pixmap = QPixmap(px_size, px_size)
    pixmap.fill(Qt.transparent)
    renderer = QSvgRenderer(QByteArray(svg))
    if renderer.isValid():
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        renderer.render(painter)
        painter.end()
    pixmap.setDevicePixelRatio(scale)
    return pixmap


def app_pixmap(name: str, color: str | None = None, size: int = 16) -> QPixmap:
    """Return a crisp high-DPI QPixmap for an SVG icon name."""
    resolved_color = color or theme.COLORS.get("text", "#cbd5e1")
    return _render_pixmap_cached(name, resolved_color, int(size))


def app_icon(
    name: str,
    color: str | None = None,
    size: int = 16,
    active_color: str | None = None,
) -> QIcon:
    """Build a theme-aware vector QIcon, optionally tinted when checked/selected."""
    base_color = color or theme.COLORS.get("text", "#cbd5e1")
    icon = QIcon()
    normal_pm = app_pixmap(name, base_color, size)
    icon.addPixmap(normal_pm, QIcon.Normal, QIcon.Off)
    if active_color:
        active_pm = app_pixmap(name, active_color, size)
        icon.addPixmap(active_pm, QIcon.Normal, QIcon.On)
        icon.addPixmap(active_pm, QIcon.Selected, QIcon.Off)
        icon.addPixmap(active_pm, QIcon.Selected, QIcon.On)
    else:
        icon.addPixmap(normal_pm, QIcon.Normal, QIcon.On)
    return icon


def status_dot_pixmap(color: str, size: int = 10) -> QPixmap:
    """Return a clean filled circular status indicator pixmap."""
    return app_pixmap("dot", color=color, size=size)


def status_dot_icon(color: str, size: int = 10) -> QIcon:
    """Return a clean filled circular status indicator QIcon."""
    return app_icon("dot", color=color, size=size)


def icon_label(name: str, color: str | None = None, size: int = 16) -> QLabel:
    """Create a transparent QLabel carrying a crisp vector icon pixmap."""
    lbl = QLabel()
    lbl.setPixmap(app_pixmap(name, color=color, size=size))
    lbl.setFixedSize(size + 2, size + 2)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setStyleSheet("background: transparent; border: none;")
    return lbl


def clear_icon_cache() -> None:
    """Clear rendered pixmap cache when theme presets change."""
    _render_pixmap_cached.cache_clear()
