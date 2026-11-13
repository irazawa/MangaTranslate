"""Modern tabbed Advanced Text Editor dialog with live bubble preview."""

from __future__ import annotations

import copy
import math
import traceback

from PyQt5.QtCore import QPoint, QPointF, QRect, QSignalBlocker, QSize, Qt, QTimer
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
)
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.core.config import SETTINGS
from src.ui.icons import app_icon
from src.ui.notifications import notify_banner, notify_toast
from src.ui.texts import AdvancedEditorText
from src.ui.theme import COLORS, advanced_text_editor_stylesheet
from src.ui.widgets import FontDelegate, InteractiveCurveEditor


def _is_light_color(color_value) -> bool:
    c = color_value if isinstance(color_value, QColor) else QColor(str(color_value or "#000000"))
    return c.isValid() and c.lightness() > 132


def _swatch_button_qss(color_value) -> str:
    c = color_value if isinstance(color_value, QColor) else QColor(str(color_value or "#000000"))
    hex_name = c.name() if c.isValid() else "#000000"
    fg = "#020617" if _is_light_color(c) else "#f8fafc"
    return (
        f"background-color: {hex_name}; color: {fg}; "
        f"border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 5px 10px; font-weight: 700;"
    )


class _GradientSwatchBar(QWidget):
    """Compact horizontal bar showing the active multi-stop linear gradient."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._colors = ["#FF0000", "#0000FF"]
        self._angle = 0.0
        self._enabled = True
        self.setFixedHeight(26)

    def set_gradient(self, colors: list[str], angle: float, enabled: bool) -> None:
        self._colors = list(colors) if colors else ["#FF0000", "#0000FF"]
        self._angle = float(angle)
        self._enabled = bool(enabled)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect().adjusted(1, 1, -1, -1)
        if not self._enabled or not self._colors:
            painter.setPen(QPen(QColor(COLORS["border"]), 1, Qt.DashLine))
            painter.setBrush(QBrush(QColor(COLORS["card_alt"])))
            painter.drawRoundedRect(rect, 6, 6)
            painter.setPen(QColor(COLORS["muted"]))
            painter.drawText(rect, Qt.AlignCenter, "Gradient nonaktif")
            return

        rad = math.radians(self._angle)
        cx, cy = rect.center().x(), rect.center().y()
        half = max(1.0, rect.width() * 0.5 * abs(math.cos(rad)) + rect.height() * 0.5 * abs(math.sin(rad)))
        dx, dy = math.cos(rad) * half, math.sin(rad) * half
        grad = QLinearGradient(QPointF(cx - dx, cy - dy), QPointF(cx + dx, cy + dy))
        stops = [c for c in self._colors if QColor(c).isValid()] or ["#38bdf8", "#818cf8"]
        if len(stops) == 1:
            grad.setColorAt(0.0, QColor(stops[0]))
            grad.setColorAt(1.0, QColor(stops[0]))
        else:
            last = len(stops) - 1
            for i, col in enumerate(stops):
                grad.setColorAt(i / last, QColor(col))
        painter.setPen(QPen(QColor(COLORS["border"]), 1))
        painter.setBrush(QBrush(grad))
        painter.drawRoundedRect(rect, 6, 6)


class _LiveEffectPreviewWidget(QWidget):
    """Offscreen-rendered live preview of the edited TypesetArea and its effects."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self._bg_mode = "paper"  # 'paper' | 'dark' | 'checker'
        self._area_size = (0, 0)
        self.setMinimumHeight(185)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_bg_mode(self, mode: str) -> None:
        if mode in ("paper", "dark", "checker") and mode != self._bg_mode:
            self._bg_mode = mode
            self.update()

    def render_area(self, host_window, preview_area: TypesetArea) -> None:
        rect = preview_area.get_text_rect() if hasattr(preview_area, "get_text_rect") else preview_area.rect
        w = max(120, int(rect.width()) if rect.width() > 1 else 280)
        h = max(80, int(rect.height()) if rect.height() > 1 else 140)
        self._area_size = (w, h)

        pad = 22
        max_dim = 900
        scale = 1.0
        if max(w, h) > max_dim:
            scale = max_dim / float(max(w, h))

        img_w = max(160, int(round((w + pad * 2) * scale)))
        img_h = max(120, int(round((h + pad * 2) * scale)))
        img = QImage(img_w, img_h, QImage.Format_ARGB32_Premultiplied)
        img.fill(Qt.transparent)

        painter = QPainter(img)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.scale(scale, scale)
        painter.translate(-rect.x() + pad, -rect.y() + pad)

        # Draw subtle bounds guide when no explicit speech bubble is drawn
        if not getattr(preview_area, "bubble_enabled", False):
            guide_pen = QPen(QColor(56, 189, 248, 95), 1.2, Qt.DashLine)
            painter.setPen(guide_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)

            margins = preview_area.get_margins() if hasattr(preview_area, "get_margins") else {}
            if any(int(margins.get(k, 0)) > 0 for k in ("top", "right", "bottom", "left")):
                inner = rect.adjusted(
                    int(margins.get("left", 0)),
                    int(margins.get("top", 0)),
                    -int(margins.get("right", 0)),
                    -int(margins.get("bottom", 0)),
                )
                if inner.width() > 2 and inner.height() > 2:
                    margin_pen = QPen(QColor(251, 191, 36, 120), 1.0, Qt.DotLine)
                    painter.setPen(margin_pen)
                    painter.drawRect(inner)

        try:
            if host_window is not None and hasattr(host_window, "draw_area_text"):
                if getattr(preview_area, "bubble_enabled", False) and hasattr(host_window, "draw_area_bubble"):
                    host_window.draw_area_bubble(painter, preview_area)
                host_window.draw_area_text(painter, preview_area)
            else:
                self._draw_standalone_fallback(painter, preview_area, rect)
        except Exception:
            traceback.print_exc()
        finally:
            painter.end()

        self._pixmap = QPixmap.fromImage(img)
        self.update()

    def _draw_standalone_fallback(self, painter: QPainter, area: TypesetArea, rect: QRect) -> None:
        if getattr(area, "bubble_enabled", False):
            painter.setPen(QPen(QColor(getattr(area, "bubble_outline", "#000000")), 2.5))
            painter.setBrush(QBrush(QColor(getattr(area, "bubble_fill", "#ffffff"))))
            painter.drawRoundedRect(rect, 18, 18)
        painter.setFont(area.get_font())
        painter.setPen(area.get_color())
        margins = area.get_margins()
        target = rect.adjusted(
            int(margins.get("left", 0)),
            int(margins.get("top", 0)),
            -int(margins.get("right", 0)),
            -int(margins.get("bottom", 0)),
        )
        painter.drawText(target, Qt.AlignCenter | Qt.TextWordWrap, area.text or "")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        box = self.rect().adjusted(1, 1, -1, -1)

        if self._bg_mode == "paper":
            painter.fillRect(box, QColor("#f8fafc"))
        elif self._bg_mode == "dark":
            painter.fillRect(box, QColor("#090a0f"))
        else:
            tile = 12
            light = QColor("#1e293b")
            dark = QColor("#0f172a")
            for y in range(box.top(), box.bottom(), tile):
                for x in range(box.left(), box.right(), tile):
                    even = ((x // tile) + (y // tile)) % 2 == 0
                    painter.fillRect(
                        x,
                        y,
                        min(tile, box.right() - x + 1),
                        min(tile, box.bottom() - y + 1),
                        light if even else dark,
                    )

        painter.setPen(QPen(QColor(COLORS["border"]), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(box, 8, 8)

        if not self._pixmap.isNull():
            avail = box.adjusted(8, 8, -8, -24)
            scaled = self._pixmap.scaled(avail.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            px = avail.left() + (avail.width() - scaled.width()) // 2
            py = avail.top() + (avail.height() - scaled.height()) // 2
            painter.drawPixmap(px, py, scaled)

        w, h = self._area_size
        if w > 0 and h > 0:
            painter.setPen(QColor("#64748b" if self._bg_mode == "paper" else COLORS["muted"]))
            badge_rect = box.adjusted(8, box.height() - 22, -10, -5)
            painter.drawText(badge_rect, Qt.AlignRight | Qt.AlignVCenter, f"Area: {w} x {h} px")


class AdvancedTextEditDialog(QDialog):
    """Tabbed rich-text and visual effects editor for a single TypesetArea."""

    EFFECT_OPTIONS = [
        ("None", "none"),
        ("Curved", "curved"),
        ("Wavy", "wavy"),
        ("Jagged Shout", "jagged"),
        ("Arc (Bended)", "arc"),
        ("Arch (Gate)", "arch"),
        ("Flag (Wave)", "flag"),
    ]
    ORIENTATION_OPTIONS = [
        (AdvancedEditorText.ORIENTATION_HORIZONTAL, "horizontal"),
        (AdvancedEditorText.ORIENTATION_VERTICAL, "vertical"),
        (AdvancedEditorText.ORIENTATION_UPRIGHT, "vertical_upright"),
    ]
    ALIGN_OPTIONS = [
        ("Center", Qt.AlignHCenter),
        ("Left", Qt.AlignLeft),
        ("Right", Qt.AlignRight),
        ("Justify", Qt.AlignJustify),
    ]
    QUICK_LOVE_SYMBOLS = [
        ("Hati Solid (Klasik Manga)", "♥"),
        ("Hati Garis (Outline)", "♡"),
        ("Hati Tebal", "❤"),
        ("Dua Hati Berdekatan", "💕"),
    ]
    SYMBOL_CATEGORIES = [
        {
            "key": "love_classic",
            "title": AdvancedEditorText.SYM_CAT_LOVE_CLASSIC,
            "icon": "heart",
            "color": "#f472b6",
            "items": [
                ("Hati Solid (Klasik Manga)", "♥"),
                ("Hati Garis (Outline)", "♡"),
                ("Hati Tebal", "❤"),
                ("Hati Miring Kanan", "❥"),
                ("Tanda Seru Hati", "❣"),
                ("Hati Lengkung Halus", "ღ"),
                ("Hati Kecil Tipis", "დ"),
                ("Hati Ornamen Tetes", "۵"),
                ("Hati Kembar Garis", "ლ"),
                ("Hati Daun Floral", "❦"),
                ("Hati Daun Samping", "❧"),
                ("Hati Berombak Halus", "♡~"),
                ("Hati Solid Berombak", "♥~"),
                ("Hati Bergetar Pembuka", "~♥"),
                ("Hati Ganda Klasik", "♡♡"),
                ("Hati Solid Ganda", "♥♥"),
                ("Hati Terkejut / Seru", "♡!"),
                ("Hati Seru Ganda", "♥!!"),
                ("Hati Malu / Terdiam", "♡..."),
                ("Hati Tersirat / Tanya", "♡?"),
            ],
        },
        {
            "key": "love_variations",
            "title": AdvancedEditorText.SYM_CAT_LOVE_VARIATIONS,
            "icon": "heart",
            "color": "#fb7185",
            "items": [
                ("Hati Merah", "❤️"),
                ("Hati Pink Lembut", "🩷"),
                ("Hati Oranye", "🧡"),
                ("Hati Kuning", "💛"),
                ("Hati Hijau", "💚"),
                ("Hati Biru", "💙"),
                ("Hati Biru Muda", "🩵"),
                ("Hati Ungu", "💜"),
                ("Hati Hitam (Yandere/Gelap)", "🖤"),
                ("Hati Putih", "🤍"),
                ("Hati Cokelat", "🤎"),
                ("Dua Hati Berdekatan", "💕"),
                ("Hati Berputar Jatuh Cinta", "💞"),
                ("Hati Berdetak (Doki-Doki)", "💓"),
                ("Hati Membesar Berdebar", "💗"),
                ("Hati Berkilau Shoujo", "💖"),
                ("Hati Terpanah Asmara", "💘"),
                ("Hati Pita Hadiah", "💝"),
                ("Bingkai Hati", "💟"),
                ("Cinta Membara", "❤️‍🔥"),
                ("Patah Hati", "💔"),
                ("Hati Mulai Sembuh", "❤️‍🩹"),
                ("Tangan Bentuk Hati", "🫶"),
                ("Surat Cinta", "💌"),
                ("Jejak Ciuman", "💋"),
            ],
        },
        {
            "key": "love_kaomoji",
            "title": AdvancedEditorText.SYM_CAT_LOVE_KAOMOJI,
            "icon": "sparkles",
            "color": "#f9a8d4",
            "items": [
                ("Senyum Jatuh Cinta", "(♡˙︶˙♡)"),
                ("Tersipu Malu", "(´｡• ᵕ •｡`) ♡"),
                ("Menggemaskan Penuh Cinta", "♡(´｡•ㅅ•｡`)"),
                ("Cium Manja", "( ˘ ³˘)♥"),
                ("Mata Berbinar Cinta", "(♥ω♥*)"),
                ("Senyum Rahasia", "(♡´艸`)"),
                ("Pesona Shoujo", "✧♡(◕ᴗ◕✿)"),
                ("Kirim Cinta", "(ﾉ´ з `)ノ♥"),
                ("Terpukau Cinta", "(｡♥‿♥｡)"),
                ("Girang Jatuh Cinta", "♡〜٩( ˃́ ˂̀ )۶〜♡"),
                ("Hangat & Lembut", "( ◡‿◡ *)♡"),
                ("Malu-Malu Kucing", "(♡ˊ͈ ꒳ ˋ͈)"),
            ],
        },
        {
            "key": "sparkles_stars",
            "title": AdvancedEditorText.SYM_CAT_SPARKLES_STARS,
            "icon": "star",
            "color": "#fbbf24",
            "items": [
                ("Kilau Trio", "✨"),
                ("Bintang 4 Sisi Hitam", "✦"),
                ("Bintang 4 Sisi Putih", "✧"),
                ("Bintang Penuh", "★"),
                ("Bintang Garis", "☆"),
                ("Bintang Tekan", "✩"),
                ("Bintang Lingkar", "✪"),
                ("Bintang Terbuka", "✫"),
                ("Bintang Tebal", "✭"),
                ("Bintang Kipas", "✯"),
                ("Bintang Bayangan", "✰"),
                ("Kilau 8 Sisi", "✴"),
                ("Kilau Runcing", "✵"),
                ("Kilau 6 Sisi", "✶"),
                ("Kilau Meledak", "✹"),
                ("Pusing / Bintang Jatuh", "💫"),
                ("Bunga Sakura", "🌸"),
                ("Bunga Putih", "❀"),
                ("Bunga Hitam", "✿"),
                ("Bunga Kelopak", "❁"),
            ],
        },
        {
            "key": "music",
            "title": AdvancedEditorText.SYM_CAT_MUSIC,
            "icon": "music",
            "color": "#38bdf8",
            "items": [
                ("Nada Tunggal", "♪"),
                ("Nada Ganda", "♫"),
                ("Nada Irama", "♬"),
                ("Nada Seperempat", "♩"),
                ("Flat (Mol)", "♭"),
                ("Sharp (Kres)", "♯"),
                ("Not Musik", "🎵"),
                ("Melodi Panjang", "🎶"),
                ("Bernyanyi", "🎤"),
            ],
        },
        {
            "key": "manga_reactions",
            "title": AdvancedEditorText.SYM_CAT_MANGA_FX,
            "icon": "zap",
            "color": "#f97316",
            "items": [
                ("Kaget + Tanya", "⁉"),
                ("Seru Ganda", "‼"),
                ("Interrobang", "‽"),
                ("Seru Tebal", "❗"),
                ("Tanya Tebal", "❓"),
                ("Urat Marah", "💢"),
                ("Keringat Panik", "💦"),
                ("Tetes Keringat", "💧"),
                ("Kabur / Mendesah", "💨"),
                ("Tidur / Mengantuk", "💤"),
                ("Ledakan / Benturan", "💥"),
                ("Kejutan Listrik", "⚡"),
                ("Semangat Membara", "🔥"),
                ("Balon Bicara", "💬"),
                ("Balon Pikiran", "💭"),
                ("Tatapan Tajam", "👁"),
                ("Tengkorak / Syok Mati", "💀"),
                ("Aura Hantu / Merinding", "👻"),
            ],
        },
        {
            "key": "punctuation",
            "title": AdvancedEditorText.SYM_CAT_PUNCTUATION,
            "icon": "book",
            "color": "#a78bfa",
            "items": [
                ("Kurung Siku Buka", "「"),
                ("Kurung Siku Tutup", "」"),
                ("Kurung Ganda Buka", "『"),
                ("Kurung Ganda Tutup", "』"),
                ("Kurung Tebal Buka", "【"),
                ("Kurung Tebal Tutup", "】"),
                ("Kurung Judul Buka", "《"),
                ("Kurung Judul Tutup", "》"),
                ("Tilde Panjang", "〜"),
                ("Tilde Tebal", "～"),
                ("Elipsis Tiga Titik", "…"),
                ("Em Dash Panjang", "—"),
                ("Titik Tengah", "・"),
                ("Catatan Teks", "※"),
                ("Simbol Gelap / Salib", "†"),
                ("Salib Ganda", "‡"),
                ("Tak Terbatas", "∞"),
            ],
        },
    ]
    SYMBOL_PRESETS = [item for cat in SYMBOL_CATEGORIES for item in cat["items"]]
    GRADIENT_DIRECTIONS = [
        ("Custom", -1),
        ("Left -> Right", 0.0),
        ("Top -> Bottom", 90.0),
        ("Right -> Left", 180.0),
        ("Bottom -> Top", 270.0),
        ("TL -> BR", 45.0),
        ("TR -> BL", 135.0),
        ("BR -> TL", 315.0),
        ("BL -> TR", 225.0),
    ]
    GRADIENT_PRESETS = [
        ("Fire", ["#fbbf24", "#ef4444"]),
        ("Ice", ["#38bdf8", "#3b82f6"]),
        ("Sakura", ["#f472b6", "#a855f7"]),
        ("Gold", ["#fef08a", "#d97706"]),
        ("Shadow", ["#f8fafc", "#475569"]),
    ]

    def __init__(self, parent=None, area=None, font_manager=None):
        super().__init__(parent)
        if area is None:
            from src.ui.canvas import TypesetArea

            area = TypesetArea(QRect(0, 0, 280, 140), "", QFont("Arial", 16), QColor("#000000"))
        self.area = area
        self.font_manager = font_manager
        self.result = None
        self._manual_text_color_changed = False
        self._loading = True
        self.gradient_colors_store = ["#FF0000", "#0000FF"]
        self.outline_layers_store = []
        self._shadow_color = QColor("#000000")
        self._outline_color = (
            QColor(self.area.get_text_outline_color())
            if hasattr(self.area, "get_text_outline_color")
            else QColor("#000000")
        )

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(25)
        self._preview_timer.timeout.connect(self._refresh_live_preview)

        self.setWindowTitle(AdvancedEditorText.WINDOW_TITLE)
        self.setModal(True)
        self.setObjectName("AdvancedTextEditDialog")
        self.setStyleSheet(advanced_text_editor_stylesheet())
        self._restore_or_apply_size()

        self._build_ui()
        self._connect_signals()
        self._populate_font_groups_and_fonts()
        self._load_area_into_editor()
        self._loading = False
        self._sync_toolbar_from_cursor()
        self._update_bezier_status_ui()
        self._refresh_live_preview()

    # ------------------------------------------------------------------
    # Window sizing & layout builders
    # ------------------------------------------------------------------
    def _restore_or_apply_size(self) -> None:
        saved_size = SETTINGS.get("ui", {}).get("advanced_editor_size")
        if saved_size and len(saved_size) == 2 and saved_size[0] >= 920 and saved_size[1] >= 600:
            try:
                self.resize(int(saved_size[0]), int(saved_size[1]))
                return
            except Exception:
                pass
        self._apply_default_size()

    def _apply_default_size(self) -> None:
        try:
            screen = QApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                self.resize(max(1040, int(geo.width() * 0.84)), max(680, int(geo.height() * 0.84)))
                return
        except Exception:
            pass
        self.resize(1180, 780)

    def closeEvent(self, event):
        try:
            s = self.size()
            SETTINGS.setdefault("ui", {})["advanced_editor_size"] = (s.width(), s.height())
        except Exception:
            pass
        super().closeEvent(event)

    def _make_card(self, title: str, desc: str, header_extra: QWidget | None = None):
        card = QFrame()
        card.setObjectName("ate-card")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(12, 11, 12, 12)
        vbox.setSpacing(8)

        head = QHBoxLayout()
        head.setSpacing(8)
        title_lbl = QLabel(title)
        title_lbl.setObjectName("ate-card-title")
        head.addWidget(title_lbl, 1)
        if header_extra is not None:
            head.addWidget(header_extra, 0)
        vbox.addLayout(head)

        if desc:
            desc_lbl = QLabel(desc)
            desc_lbl.setObjectName("ate-card-desc")
            desc_lbl.setWordWrap(True)
            vbox.addWidget(desc_lbl)
        return card, vbox

    def _wrap_scroll(self, inner: QWidget) -> QScrollArea:
        inner.setObjectName("ate-scroll-body")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(inner)
        return scroll

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(10)

        main_layout.addWidget(self._build_hero_banner())

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_left_pane())
        splitter.addWidget(self._build_right_tabs())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter, 1)

        main_layout.addWidget(self._build_bottom_bar())

    def _build_hero_banner(self) -> QFrame:
        hero = QFrame()
        hero.setObjectName("ate-hero")
        hbox = QHBoxLayout(hero)
        hbox.setContentsMargins(14, 10, 14, 10)
        hbox.setSpacing(10)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        title = QLabel(AdvancedEditorText.HERO_TITLE)
        title.setObjectName("ate-title")
        subtitle = QLabel(AdvancedEditorText.HERO_SUBTITLE)
        subtitle.setObjectName("ate-subtitle")
        subtitle.setWordWrap(True)
        text_col.addWidget(title)
        text_col.addWidget(subtitle)
        hbox.addLayout(text_col, 1)

        badge = QLabel(AdvancedEditorText.HERO_BADGE_AREA)
        badge.setObjectName("ate-badge")
        hbox.addWidget(badge, 0, Qt.AlignTop)
        return hero

    def _build_left_pane(self) -> QWidget:
        pane = QWidget()
        vbox = QVBoxLayout(pane)
        vbox.setContentsMargins(0, 0, 6, 0)
        vbox.setSpacing(10)

        vbox.addWidget(self._build_formatting_bar())

        # Text editor card
        self._contrast_pill = QLabel(AdvancedEditorText.CONTRAST_LIGHT_PILL)
        self._contrast_pill.setObjectName("ate-pill")
        editor_card, editor_box = self._make_card(
            AdvancedEditorText.EDITOR_TITLE,
            AdvancedEditorText.EDITOR_HINT,
            header_extra=self._contrast_pill,
        )
        self.text_edit = QTextEdit()
        self.text_edit.setAcceptRichText(True)
        self.text_edit.setMinimumHeight(175)
        editor_box.addWidget(self.text_edit, 1)
        self._last_text_cursor = QTextCursor(self.text_edit.document())
        vbox.addWidget(editor_card, 3)

        # Live preview card
        bg_bar = QWidget()
        bg_row = QHBoxLayout(bg_bar)
        bg_row.setContentsMargins(0, 0, 0, 0)
        bg_row.setSpacing(4)
        self._preview_bg_buttons: dict[str, QToolButton] = {}
        for mode, label in (
            ("paper", AdvancedEditorText.PREVIEW_BG_PAPER),
            ("dark", AdvancedEditorText.PREVIEW_BG_DARK),
            ("checker", AdvancedEditorText.PREVIEW_BG_CHECKER),
        ):
            btn = QToolButton()
            btn.setText(label)
            btn.setCheckable(True)
            btn.setChecked(mode == "paper")
            btn.clicked.connect(lambda _c=False, m=mode: self._set_preview_bg_mode(m))
            bg_row.addWidget(btn)
            self._preview_bg_buttons[mode] = btn

        preview_card, preview_box = self._make_card(
            AdvancedEditorText.PREVIEW_TITLE,
            AdvancedEditorText.PREVIEW_HINT,
            header_extra=bg_bar,
        )
        self.preview_widget = _LiveEffectPreviewWidget()
        preview_box.addWidget(self.preview_widget, 1)
        vbox.addWidget(preview_card, 3)

        return pane

    def _build_formatting_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("ate-toolbar-bar")
        vbox = QVBoxLayout(bar)
        vbox.setContentsMargins(10, 8, 10, 8)
        vbox.setSpacing(6)

        row1 = QHBoxLayout()
        row1.setSpacing(6)
        self.font_group_combo = QComboBox()
        self.font_group_combo.setMinimumWidth(115)
        self.font_group_combo.addItem("All")
        row1.addWidget(self.font_group_combo)

        self.font_combo = QComboBox()
        self.font_combo.setMinimumWidth(185)
        self.font_combo.setItemDelegate(FontDelegate(self.font_manager, self.font_combo))
        row1.addWidget(self.font_combo, 1)

        self.font_preview = QLabel("AaBb123")
        self.font_preview.setMinimumWidth(95)
        self.font_preview.setMaximumWidth(135)
        self.font_preview.setAlignment(Qt.AlignCenter)
        self.font_preview.setStyleSheet(
            f"border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 3px 6px;"
            f"background: {COLORS['card_alt']}; color: {COLORS['text']};"
        )
        row1.addWidget(self.font_preview)

        self.font_size_spin = QDoubleSpinBox()
        self.font_size_spin.setRange(4.0, 220.0)
        self.font_size_spin.setDecimals(1)
        self.font_size_spin.setSingleStep(1.0)
        self.font_size_spin.setSuffix(" pt")
        self.font_size_spin.setMinimumWidth(84)
        row1.addWidget(self.font_size_spin)

        vbox.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(6)
        self.bold_button = QToolButton()
        self.bold_button.setText("B")
        self.bold_button.setCheckable(True)
        self.bold_button.setToolTip("Toggle bold")
        row2.addWidget(self.bold_button)

        self.italic_button = QToolButton()
        self.italic_button.setText("I")
        self.italic_button.setCheckable(True)
        self.italic_button.setToolTip("Toggle italic")
        row2.addWidget(self.italic_button)

        self.underline_button = QToolButton()
        self.underline_button.setText("U")
        self.underline_button.setCheckable(True)
        self.underline_button.setToolTip("Toggle underline")
        row2.addWidget(self.underline_button)

        self.color_button = QToolButton()
        self.color_button.setText("Color")
        self.color_button.setToolTip("Ubah warna solid teks")
        row2.addWidget(self.color_button)

        row2.addStretch(1)

        self.ai_translate_btn = QPushButton(AdvancedEditorText.BTN_AI_TRANSLATE)
        self.ai_translate_btn.setIcon(app_icon("languages", size=14))
        self.ai_translate_btn.setIconSize(QSize(14, 14))
        self.ai_translate_btn.setToolTip(AdvancedEditorText.TIP_AI_TRANSLATE)
        row2.addWidget(self.ai_translate_btn)

        self.recent_translations_btn = QPushButton(AdvancedEditorText.BTN_RECENT)
        self.recent_translations_btn.setIcon(app_icon("history", size=14))
        self.recent_translations_btn.setIconSize(QSize(14, 14))
        self.recent_translations_btn.setToolTip(AdvancedEditorText.TIP_RECENT)
        row2.addWidget(self.recent_translations_btn)

        self.emoji_button = QToolButton()
        self.emoji_button.setText(AdvancedEditorText.BTN_SYMBOLS)
        self.emoji_button.setIcon(app_icon("heart", size=14))
        self.emoji_button.setIconSize(QSize(14, 14))
        self.emoji_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.emoji_button.setToolTip(AdvancedEditorText.TIP_SYMBOLS)
        self.emoji_menu = self._build_symbols_menu()
        self.emoji_button.setMenu(self.emoji_menu)
        self.emoji_button.setPopupMode(QToolButton.InstantPopup)
        row2.addWidget(self.emoji_button)

        vbox.addLayout(row2)
        return bar

    def _build_right_tabs(self) -> QTabWidget:
        self.tabs = QTabWidget()
        self.tabs.setObjectName("ate-tabs")
        self.tabs.setMinimumWidth(490)
        self.tabs.setUsesScrollButtons(False)

        self.tabs.addTab(self._build_layout_tab(), app_icon("type", size=14), AdvancedEditorText.TAB_LAYOUT)
        self.tabs.addTab(self._build_fill_tab(), app_icon("palette", size=14), AdvancedEditorText.TAB_FILL)
        self.tabs.addTab(self._build_outline_shadow_tab(), app_icon("layers", size=14), AdvancedEditorText.TAB_OUTLINE)
        self.tabs.addTab(self._build_warp_tab(), app_icon("sparkles", size=14), AdvancedEditorText.TAB_WARP)
        return self.tabs

    def _build_layout_tab(self) -> QScrollArea:
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(10, 10, 10, 10)
        vbox.setSpacing(10)

        # Card 1: Orientation, Alignment & Spacing
        c1, b1 = self._make_card(AdvancedEditorText.CARD_LAYOUT_TITLE, AdvancedEditorText.CARD_LAYOUT_DESC)
        g1 = QGridLayout()
        g1.setSpacing(8)
        self.orientation_combo = QComboBox()
        for label, value in self.ORIENTATION_OPTIONS:
            self.orientation_combo.addItem(label, value)
        self.alignment_combo = QComboBox()
        for label, _ in self.ALIGN_OPTIONS:
            self.alignment_combo.addItem(label)

        self.line_spacing_spin = QDoubleSpinBox()
        self.line_spacing_spin.setRange(0.6, 3.0)
        self.line_spacing_spin.setSingleStep(0.1)
        self.line_spacing_spin.setValue(1.1)

        self.char_spacing_spin = QDoubleSpinBox()
        self.char_spacing_spin.setRange(50.0, 400.0)
        self.char_spacing_spin.setSingleStep(5.0)
        self.char_spacing_spin.setSuffix(" %")
        self.char_spacing_spin.setValue(100.0)

        g1.addWidget(QLabel("Orientasi:"), 0, 0)
        g1.addWidget(self.orientation_combo, 0, 1)
        g1.addWidget(QLabel("Perataan:"), 0, 2)
        g1.addWidget(self.alignment_combo, 0, 3)
        g1.addWidget(QLabel("Line Spacing:"), 1, 0)
        g1.addWidget(self.line_spacing_spin, 1, 1)
        g1.addWidget(QLabel("Char Spacing:"), 1, 2)
        g1.addWidget(self.char_spacing_spin, 1, 3)
        b1.addLayout(g1)
        vbox.addWidget(c1)

        # Card 2: Smart Auto-Fit & Bubble
        c2, b2 = self._make_card(AdvancedEditorText.CARD_FIT_BUBBLE_TITLE, AdvancedEditorText.CARD_FIT_BUBBLE_DESC)
        self.smart_fit_checkbox = QCheckBox("Smart Auto-Fit Text to Bubble / Bounding Area")
        self.bubble_checkbox = QCheckBox("Render Bubble (Isi putih, outline hitam)")
        b2.addWidget(self.smart_fit_checkbox)
        b2.addWidget(self.bubble_checkbox)
        vbox.addWidget(c2)

        # Card 3: Inner Margins
        reset_margin_btn = QPushButton("Reset 0")
        reset_margin_btn.setToolTip("Set semua margin menjadi 0 px")
        reset_margin_btn.clicked.connect(self._reset_margins)
        c3, b3 = self._make_card(
            AdvancedEditorText.CARD_MARGINS_TITLE,
            AdvancedEditorText.CARD_MARGINS_DESC,
            header_extra=reset_margin_btn,
        )
        mg = QGridLayout()
        mg.setSpacing(8)
        self.margin_top_spin = QSpinBox()
        self.margin_right_spin = QSpinBox()
        self.margin_bottom_spin = QSpinBox()
        self.margin_left_spin = QSpinBox()
        for sp in (self.margin_top_spin, self.margin_right_spin, self.margin_bottom_spin, self.margin_left_spin):
            sp.setRange(0, 400)
            sp.setSuffix(" px")
        mg.addWidget(QLabel("Atas (Top):"), 0, 0)
        mg.addWidget(self.margin_top_spin, 0, 1)
        mg.addWidget(QLabel("Bawah (Bottom):"), 0, 2)
        mg.addWidget(self.margin_bottom_spin, 0, 3)
        mg.addWidget(QLabel("Kiri (Left):"), 1, 0)
        mg.addWidget(self.margin_left_spin, 1, 1)
        mg.addWidget(QLabel("Kanan (Right):"), 1, 2)
        mg.addWidget(self.margin_right_spin, 1, 3)
        b3.addLayout(mg)
        vbox.addWidget(c3)

        vbox.addStretch(1)
        return self._wrap_scroll(page)

    def _build_fill_tab(self) -> QScrollArea:
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(10, 10, 10, 10)
        vbox.setSpacing(10)

        # Card 1: Gradient Fill
        self.gradient_enabled_checkbox = QCheckBox("Aktif")
        cg, bg = self._make_card(
            AdvancedEditorText.CARD_GRADIENT_TITLE,
            AdvancedEditorText.CARD_GRADIENT_DESC,
            header_extra=self.gradient_enabled_checkbox,
        )

        self.gradient_bar = _GradientSwatchBar()
        bg.addWidget(self.gradient_bar)

        stops_row = QHBoxLayout()
        stops_row.setSpacing(6)
        self.gradient_color1_btn = QPushButton("Start")
        self.gradient_color2_btn = QPushButton("End")
        self._gradient_extra_stops_row = QHBoxLayout()
        self._gradient_extra_stops_row.setSpacing(4)
        stops_row.addWidget(self.gradient_color1_btn)
        stops_row.addLayout(self._gradient_extra_stops_row)
        stops_row.addWidget(self.gradient_color2_btn)
        stops_row.addStretch(1)
        bg.addLayout(stops_row)

        stops_actions_row = QHBoxLayout()
        stops_actions_row.setSpacing(6)
        self.gradient_swap_btn = QPushButton(AdvancedEditorText.BTN_SWAP_COLORS)
        self.gradient_add_stop_btn = QPushButton(AdvancedEditorText.BTN_ADD_STOP)
        self.gradient_remove_stop_btn = QPushButton(AdvancedEditorText.BTN_REMOVE_STOP)
        stops_actions_row.addWidget(self.gradient_swap_btn)
        stops_actions_row.addWidget(self.gradient_add_stop_btn)
        stops_actions_row.addWidget(self.gradient_remove_stop_btn)
        stops_actions_row.addStretch(1)
        bg.addLayout(stops_actions_row)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(4)
        preset_lbl = QLabel("Preset:")
        preset_lbl.setStyleSheet(f"color: {COLORS['muted']};")
        preset_row.addWidget(preset_lbl)
        for name, cols in self.GRADIENT_PRESETS:
            pbtn = QToolButton()
            pbtn.setText(name)
            pbtn.clicked.connect(lambda _c=False, cl=cols: self._apply_gradient_preset(cl))
            preset_row.addWidget(pbtn)
        preset_row.addStretch(1)
        bg.addLayout(preset_row)

        dir_grid = QGridLayout()
        dir_grid.setSpacing(8)
        self.gradient_angle_spin = QDoubleSpinBox()
        self.gradient_angle_spin.setRange(0.0, 360.0)
        self.gradient_angle_spin.setSingleStep(15.0)
        self.gradient_angle_spin.setSuffix(" °")
        self.gradient_direction_combo = QComboBox()
        self.gradient_direction_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.gradient_direction_combo.setMinimumWidth(115)
        for label, _ in self.GRADIENT_DIRECTIONS:
            self.gradient_direction_combo.addItem(label)
        dir_grid.addWidget(QLabel("Arah:"), 0, 0)
        dir_grid.addWidget(self.gradient_direction_combo, 0, 1)
        dir_grid.addWidget(QLabel("Sudut:"), 0, 2)
        dir_grid.addWidget(self.gradient_angle_spin, 0, 3)
        dir_grid.setColumnStretch(1, 1)
        bg.addLayout(dir_grid)
        vbox.addWidget(cg)

        # Card 2: Manga Screentone Fill
        self.pattern_enabled_checkbox = QCheckBox("Aktif")
        cp, bp = self._make_card(
            AdvancedEditorText.CARD_SCREENTONE_TITLE,
            AdvancedEditorText.CARD_SCREENTONE_DESC,
            header_extra=self.pattern_enabled_checkbox,
        )
        pg = QGridLayout()
        pg.setSpacing(8)
        self.pattern_type_combo = QComboBox()
        self.pattern_type_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.pattern_type_combo.setMinimumWidth(145)
        self.pattern_type_combo.addItem("Screentone Dots (Titik)", "dot")
        self.pattern_type_combo.addItem("Screentone Lines (Garis)", "line")
        self.pattern_type_combo.addItem("Crosshatch (Arsir Silang)", "hatch")
        self.pattern_type_combo.addItem("Manga Wave (Gelombang)", "wave")
        self.pattern_scale_spin = QDoubleSpinBox()
        self.pattern_scale_spin.setRange(0.2, 10.0)
        self.pattern_scale_spin.setSingleStep(0.1)
        self.pattern_scale_spin.setValue(1.0)
        pg.addWidget(QLabel("Pola:"), 0, 0)
        pg.addWidget(self.pattern_type_combo, 0, 1)
        pg.addWidget(QLabel("Skala:"), 0, 2)
        pg.addWidget(self.pattern_scale_spin, 0, 3)
        pg.setColumnStretch(1, 1)
        bp.addLayout(pg)
        vbox.addWidget(cp)

        vbox.addStretch(1)
        return self._wrap_scroll(page)

    def _build_outline_shadow_tab(self) -> QScrollArea:
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(10, 8, 10, 8)
        vbox.setSpacing(8)

        # Card 1: Text Outline & Glow
        self.text_outline_checkbox = QCheckBox("Aktif")
        co, bo = self._make_card(
            AdvancedEditorText.CARD_OUTLINE_TITLE,
            AdvancedEditorText.CARD_OUTLINE_DESC,
            header_extra=self.text_outline_checkbox,
        )
        og = QGridLayout()
        og.setSpacing(8)
        self.outline_style_combo = QComboBox()
        self.outline_style_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.outline_style_combo.setMinimumWidth(135)
        self.outline_style_combo.addItem("Stroke (Garis Tegas)", "stroke")
        self.outline_style_combo.addItem("Glow (Pendar Halus)", "glow")
        self.outline_width_spin = QDoubleSpinBox()
        self.outline_width_spin.setRange(0.0, 30.0)
        self.outline_width_spin.setSingleStep(0.5)
        self.outline_width_spin.setDecimals(1)
        self.outline_width_spin.setSuffix(" px")
        self.outline_color_button = QPushButton("Outline Color")

        og.addWidget(QLabel("Gaya:"), 0, 0)
        og.addWidget(self.outline_style_combo, 0, 1)
        og.addWidget(QLabel("Lebar:"), 0, 2)
        og.addWidget(self.outline_width_spin, 0, 3)
        og.addWidget(QLabel("Warna:"), 1, 0)
        og.addWidget(self.outline_color_button, 1, 1, 1, 3)
        og.setColumnStretch(1, 1)
        bo.addLayout(og)
        vbox.addWidget(co)

        # Card 2: Concentric Outline Layers
        cl, bl = self._make_card(AdvancedEditorText.CARD_LAYERS_TITLE, AdvancedEditorText.CARD_LAYERS_DESC)
        self.layers_list = QListWidget()
        self.layers_list.setFixedHeight(64)
        bl.addWidget(self.layers_list)

        lrow1 = QHBoxLayout()
        lrow1.setSpacing(6)
        self.add_layer_btn = QPushButton("Tambah")
        self.add_layer_btn.setIcon(app_icon("plus", size=13))
        self.remove_layer_btn = QPushButton("Hapus")
        self.remove_layer_btn.setIcon(app_icon("minus", size=13))
        lrow1.addWidget(self.add_layer_btn)
        lrow1.addWidget(self.remove_layer_btn)
        lrow1.addStretch(1)
        bl.addLayout(lrow1)

        lrow2 = QHBoxLayout()
        lrow2.setSpacing(6)
        self.layer_width_spin = QDoubleSpinBox()
        self.layer_width_spin.setRange(0.5, 30.0)
        self.layer_width_spin.setSingleStep(0.5)
        self.layer_width_spin.setSuffix(" px")
        self.layer_color_btn = QPushButton("Warna Layer")
        lrow2.addWidget(QLabel("Lebar:"))
        lrow2.addWidget(self.layer_width_spin)
        lrow2.addWidget(self.layer_color_btn)
        lrow2.addStretch(1)
        bl.addLayout(lrow2)
        vbox.addWidget(cl)

        # Card 3: Drop Shadow
        self.shadow_enabled_checkbox = QCheckBox("Aktif")
        cs, bs = self._make_card(
            AdvancedEditorText.CARD_SHADOW_TITLE,
            AdvancedEditorText.CARD_SHADOW_DESC,
            header_extra=self.shadow_enabled_checkbox,
        )
        sg = QGridLayout()
        sg.setSpacing(8)
        self.shadow_color_btn = QPushButton("Shadow Color")
        self.shadow_blur_spin = QDoubleSpinBox()
        self.shadow_blur_spin.setRange(0.0, 50.0)
        self.shadow_blur_spin.setSingleStep(1.0)
        self.shadow_blur_spin.setSuffix(" px")
        self.shadow_blur_spin.setValue(4.0)

        self.shadow_offset_x_spin = QDoubleSpinBox()
        self.shadow_offset_x_spin.setRange(-50.0, 50.0)
        self.shadow_offset_x_spin.setSingleStep(1.0)
        self.shadow_offset_x_spin.setValue(3.0)

        self.shadow_offset_y_spin = QDoubleSpinBox()
        self.shadow_offset_y_spin.setRange(-50.0, 50.0)
        self.shadow_offset_y_spin.setSingleStep(1.0)
        self.shadow_offset_y_spin.setValue(3.0)

        self.shadow_opacity_spin = QDoubleSpinBox()
        self.shadow_opacity_spin.setRange(0.0, 1.0)
        self.shadow_opacity_spin.setSingleStep(0.1)
        self.shadow_opacity_spin.setValue(0.7)

        sg.addWidget(QLabel("Warna:"), 0, 0)
        sg.addWidget(self.shadow_color_btn, 0, 1)
        sg.addWidget(QLabel("Blur:"), 0, 2)
        sg.addWidget(self.shadow_blur_spin, 0, 3)
        sg.addWidget(QLabel("Offset X:"), 1, 0)
        sg.addWidget(self.shadow_offset_x_spin, 1, 1)
        sg.addWidget(QLabel("Offset Y:"), 1, 2)
        sg.addWidget(self.shadow_offset_y_spin, 1, 3)
        sg.addWidget(QLabel("Opacity:"), 2, 0)
        sg.addWidget(self.shadow_opacity_spin, 2, 1)
        bs.addLayout(sg)
        vbox.addWidget(cs)

        vbox.addStretch(1)
        return self._wrap_scroll(page)

    def _build_warp_tab(self) -> QScrollArea:
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(10, 10, 10, 10)
        vbox.setSpacing(10)

        # Card 1: Warp Effect
        cw, bw = self._make_card(AdvancedEditorText.CARD_WARP_TITLE, AdvancedEditorText.CARD_WARP_DESC)
        wg = QGridLayout()
        wg.setSpacing(8)
        self.effect_combo = QComboBox()
        self.effect_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.effect_combo.setMinimumWidth(120)
        for label, value in self.EFFECT_OPTIONS:
            self.effect_combo.addItem(label, value)
        self.effect_intensity_spin = QDoubleSpinBox()
        self.effect_intensity_spin.setRange(0.0, 300.0)
        self.effect_intensity_spin.setDecimals(1)
        self.effect_intensity_spin.setSingleStep(5.0)
        wg.addWidget(QLabel("Efek:"), 0, 0)
        wg.addWidget(self.effect_combo, 0, 1)
        wg.addWidget(QLabel("Strength:"), 0, 2)
        wg.addWidget(self.effect_intensity_spin, 0, 3)
        wg.setColumnStretch(1, 1)
        bw.addLayout(wg)
        vbox.addWidget(cw)

        # Card 2: Interactive Bezier Curve + Numeric Controls
        self._bezier_status_pill = QLabel("")
        self._bezier_status_pill.setObjectName("ate-pill")
        cb, bb = self._make_card(
            AdvancedEditorText.CARD_BEZIER_TITLE,
            AdvancedEditorText.CARD_BEZIER_DESC,
            header_extra=self._bezier_status_pill,
        )

        bezier_body = QHBoxLayout()
        bezier_body.setSpacing(10)

        self.curve_editor = InteractiveCurveEditor()
        self.curve_editor.setFixedSize(128, 128)
        bezier_body.addWidget(self.curve_editor, 0, Qt.AlignTop)

        spins_col = QVBoxLayout()
        spins_col.setSpacing(8)
        sg = QGridLayout()
        sg.setSpacing(6)
        self.cp1x_spin = self._create_bezier_spin()
        self.cp1y_spin = self._create_bezier_spin()
        self.cp2x_spin = self._create_bezier_spin()
        self.cp2y_spin = self._create_bezier_spin()
        sg.addWidget(QLabel("CP1 X:"), 0, 0)
        sg.addWidget(self.cp1x_spin, 0, 1)
        sg.addWidget(QLabel("CP1 Y:"), 0, 2)
        sg.addWidget(self.cp1y_spin, 0, 3)
        sg.addWidget(QLabel("CP2 X:"), 1, 0)
        sg.addWidget(self.cp2x_spin, 1, 1)
        sg.addWidget(QLabel("CP2 Y:"), 1, 2)
        sg.addWidget(self.cp2y_spin, 1, 3)
        spins_col.addLayout(sg)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.use_curved_btn = QPushButton(AdvancedEditorText.BEZIER_USE_CURVED_BTN)
        self.reset_curve_btn = QPushButton(AdvancedEditorText.BEZIER_RESET_BTN)
        btn_row.addWidget(self.use_curved_btn)
        btn_row.addWidget(self.reset_curve_btn)
        btn_row.addStretch(1)
        spins_col.addLayout(btn_row)
        spins_col.addStretch(1)

        bezier_body.addLayout(spins_col, 1)
        bb.addLayout(bezier_body)
        vbox.addWidget(cb)

        vbox.addStretch(1)
        return self._wrap_scroll(page)

    def _build_bottom_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("ate-btn-bar")
        hbox = QHBoxLayout(bar)
        hbox.setContentsMargins(12, 9, 12, 9)
        hbox.setSpacing(8)

        self.revert_button = QPushButton(AdvancedEditorText.BTN_REVERT)
        self.revert_button.setObjectName("ate-revert-btn")
        self.revert_button.setIcon(app_icon("refresh", size=14))
        self.revert_button.setToolTip(AdvancedEditorText.TIP_REVERT)
        hbox.addWidget(self.revert_button)

        hbox.addStretch(1)

        self.cancel_btn = QPushButton(AdvancedEditorText.BTN_CANCEL)
        self.cancel_btn.setObjectName("ate-cancel-btn")
        hbox.addWidget(self.cancel_btn)

        self.apply_btn = QPushButton(AdvancedEditorText.BTN_APPLY)
        self.apply_btn.setObjectName("ate-apply-btn")
        self.apply_btn.setIcon(app_icon("check", color="#020617", size=14))
        self.apply_btn.setToolTip(AdvancedEditorText.TIP_APPLY)
        self.apply_btn.setDefault(True)
        hbox.addWidget(self.apply_btn)
        return bar

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------
    def _connect_signals(self) -> None:
        self.font_combo.currentTextChanged.connect(self._change_font_family)
        self.font_size_spin.valueChanged.connect(self._change_font_size)
        self.bold_button.toggled.connect(self._toggle_bold)
        self.italic_button.toggled.connect(self._toggle_italic)
        self.underline_button.toggled.connect(self._toggle_underline)
        self.color_button.clicked.connect(self._choose_color)

        self.ai_translate_btn.clicked.connect(self._on_ai_translate_clicked)
        self.recent_translations_btn.clicked.connect(self._show_recent_menu)

        self.text_edit.cursorPositionChanged.connect(self._remember_cursor_state)
        self.text_edit.cursorPositionChanged.connect(self._sync_toolbar_from_cursor)
        self.text_edit.textChanged.connect(self._schedule_preview_update)

        # Layout & margins
        self.orientation_combo.currentIndexChanged.connect(self._schedule_preview_update)
        self.alignment_combo.currentIndexChanged.connect(self._apply_alignment)
        self.line_spacing_spin.valueChanged.connect(self._apply_line_spacing)
        self.char_spacing_spin.valueChanged.connect(self._apply_char_spacing)
        self.smart_fit_checkbox.toggled.connect(self._schedule_preview_update)
        self.bubble_checkbox.toggled.connect(self._schedule_preview_update)
        for sp in (self.margin_top_spin, self.margin_right_spin, self.margin_bottom_spin, self.margin_left_spin):
            sp.valueChanged.connect(self._schedule_preview_update)

        # Gradient
        self.gradient_enabled_checkbox.toggled.connect(self._update_gradient_ui_state)
        self.gradient_color1_btn.clicked.connect(lambda: self._choose_gradient_color(0))
        self.gradient_color2_btn.clicked.connect(lambda: self._choose_gradient_color(-1))
        self.gradient_swap_btn.clicked.connect(self._swap_gradient_colors)
        self.gradient_add_stop_btn.clicked.connect(self._add_gradient_stop)
        self.gradient_remove_stop_btn.clicked.connect(self._remove_gradient_stop)
        self.gradient_direction_combo.currentIndexChanged.connect(self._on_gradient_direction_changed)
        self.gradient_angle_spin.valueChanged.connect(self._on_gradient_angle_changed)

        # Screentone pattern
        self.pattern_enabled_checkbox.toggled.connect(self._update_pattern_ui_state)
        self.pattern_type_combo.currentIndexChanged.connect(self._schedule_preview_update)
        self.pattern_scale_spin.valueChanged.connect(self._schedule_preview_update)

        # Outline & glow
        self.text_outline_checkbox.toggled.connect(self._update_outline_controls_enabled)
        self.outline_style_combo.currentIndexChanged.connect(self._update_outline_controls_enabled)
        self.outline_width_spin.valueChanged.connect(self._schedule_preview_update)
        self.outline_color_button.clicked.connect(self._choose_outline_color)

        # Concentric layers
        self.add_layer_btn.clicked.connect(self._add_layer)
        self.remove_layer_btn.clicked.connect(self._remove_layer)
        self.layers_list.currentRowChanged.connect(self._on_layer_selected_changed)
        self.layer_width_spin.valueChanged.connect(self._on_layer_width_changed)
        self.layer_color_btn.clicked.connect(self._choose_layer_color)

        # Shadow
        self.shadow_enabled_checkbox.toggled.connect(self._update_shadow_ui_state)
        self.shadow_color_btn.clicked.connect(self._choose_shadow_color)
        for sp in (self.shadow_blur_spin, self.shadow_offset_x_spin, self.shadow_offset_y_spin, self.shadow_opacity_spin):
            sp.valueChanged.connect(self._schedule_preview_update)

        # Warp & curve
        self.effect_combo.currentIndexChanged.connect(self._on_effect_changed)
        self.effect_intensity_spin.valueChanged.connect(self._schedule_preview_update)
        self.curve_editor.curveChanged.connect(self._on_curve_editor_changed)
        for sp in (self.cp1x_spin, self.cp1y_spin, self.cp2x_spin, self.cp2y_spin):
            sp.valueChanged.connect(self._on_bezier_spin_changed)
        self.use_curved_btn.clicked.connect(self._activate_curved_mode)
        self.reset_curve_btn.clicked.connect(self._reset_bezier_curve)

        # Footer
        self.revert_button.clicked.connect(self._on_revert_clicked)
        self.cancel_btn.clicked.connect(self.reject)
        self.apply_btn.clicked.connect(self._handle_accept)

    # ------------------------------------------------------------------
    # Preview synthesis & background selector
    # ------------------------------------------------------------------
    def _set_preview_bg_mode(self, mode: str) -> None:
        for k, btn in self._preview_bg_buttons.items():
            with QSignalBlocker(btn):
                btn.setChecked(k == mode)
        self.preview_widget.set_bg_mode(mode)

    def _schedule_preview_update(self, *_args) -> None:
        if self._loading:
            return
        self._preview_timer.start()

    def _build_preview_area(self) -> TypesetArea:
        from src.ui.canvas import TypesetArea

        segments = self._extract_segments()
        plain = "".join(seg.get("text", "") for seg in segments)
        first = next((s for s in segments if s.get("text")), None)
        font = TypesetArea.font_from_dict(first["font"]) if first and first.get("font") else self.area.get_font()
        color = QColor(first["color"]) if first and first.get("color") else self.area.get_color()
        align_label, _ = self.ALIGN_OPTIONS[max(0, self.alignment_combo.currentIndex())]

        margins = {
            "top": self.margin_top_spin.value(),
            "right": self.margin_right_spin.value(),
            "bottom": self.margin_bottom_spin.value(),
            "left": self.margin_left_spin.value(),
        }
        bezier = [
            {"x": self.cp1x_spin.value(), "y": self.cp1y_spin.value()},
            {"x": self.cp2x_spin.value(), "y": self.cp2y_spin.value()},
        ]
        outline_style = self.outline_style_combo.currentData() or "stroke"

        preview = TypesetArea(
            rect=QRect(self.area.rect),
            text=plain,
            font=font,
            color=color,
            orientation=self.orientation_combo.currentData() or "horizontal",
            effect=self.effect_combo.currentData() or "none",
            effect_intensity=self.effect_intensity_spin.value(),
            bezier_points=bezier,
            bubble_enabled=self.bubble_checkbox.isChecked(),
            bubble_fill=getattr(self.area, "bubble_fill", "#ffffff"),
            bubble_outline=getattr(self.area, "bubble_outline", "#000000"),
            bubble_outline_width=getattr(self.area, "bubble_outline_width", 3.0),
            text_outline=self.text_outline_checkbox.isChecked(),
            text_outline_width=self.outline_width_spin.value(),
            text_outline_color=self._outline_color.name() if isinstance(self._outline_color, QColor) else str(self._outline_color),
            text_outline_style=outline_style,
            alignment=align_label.lower(),
            line_spacing=self.line_spacing_spin.value(),
            char_spacing=self.char_spacing_spin.value(),
            margins=margins,
            segments=segments,
            overrides=copy.deepcopy(getattr(self.area, "overrides", {})),
            gradient_enabled=self.gradient_enabled_checkbox.isChecked(),
            gradient_colors=list(self.gradient_colors_store),
            gradient_angle=self.gradient_angle_spin.value(),
            gradient_direction=self.gradient_direction_combo.currentText(),
            shadow_enabled=self.shadow_enabled_checkbox.isChecked(),
            shadow_color=self._shadow_color.name(),
            shadow_blur=self.shadow_blur_spin.value(),
            shadow_offset_x=self.shadow_offset_x_spin.value(),
            shadow_offset_y=self.shadow_offset_y_spin.value(),
            shadow_opacity=self.shadow_opacity_spin.value(),
            outline_layers=copy.deepcopy(self.outline_layers_store),
            pattern_fill_enabled=self.pattern_enabled_checkbox.isChecked(),
            pattern_type=self.pattern_type_combo.currentData() or "dot",
            pattern_scale=self.pattern_scale_spin.value(),
            smart_fit_enabled=self.smart_fit_checkbox.isChecked(),
        )
        # Reflect user color selection immediately without letting auto_text_color override it
        if self._manual_text_color_changed:
            preview.set_override("use_auto_text_color", False)
        return preview

    def _refresh_live_preview(self) -> None:
        try:
            preview_area = self._build_preview_area()
            self.preview_widget.render_area(self.parent(), preview_area)
        except Exception:
            traceback.print_exc()

    # ------------------------------------------------------------------
    # Gradient helpers (multi-stop + swap + presets)
    # ------------------------------------------------------------------
    def _update_gradient_ui_state(self) -> None:
        enabled = self.gradient_enabled_checkbox.isChecked()
        for w in (
            self.gradient_color1_btn,
            self.gradient_color2_btn,
            self.gradient_swap_btn,
            self.gradient_add_stop_btn,
            self.gradient_angle_spin,
            self.gradient_direction_combo,
        ):
            w.setEnabled(enabled)
        self.gradient_remove_stop_btn.setEnabled(enabled and len(self.gradient_colors_store) > 2)
        for i in range(self._gradient_extra_stops_row.count()):
            item = self._gradient_extra_stops_row.itemAt(i)
            if item and item.widget():
                item.widget().setEnabled(enabled)
        self.gradient_bar.set_gradient(self.gradient_colors_store, self.gradient_angle_spin.value(), enabled)
        self._schedule_preview_update()

    def _on_gradient_direction_changed(self) -> None:
        idx = self.gradient_direction_combo.currentIndex()
        if idx < 0:
            return
        _, angle = self.GRADIENT_DIRECTIONS[idx]
        if angle != -1:
            with QSignalBlocker(self.gradient_angle_spin):
                self.gradient_angle_spin.setValue(angle)
        self.gradient_bar.set_gradient(
            self.gradient_colors_store,
            self.gradient_angle_spin.value(),
            self.gradient_enabled_checkbox.isChecked(),
        )
        self._schedule_preview_update()

    def _on_gradient_angle_changed(self) -> None:
        val = self.gradient_angle_spin.value()
        best_idx = 0
        for i, (_, angle) in enumerate(self.GRADIENT_DIRECTIONS):
            if angle != -1 and (abs(angle - val) < 1.0 or (angle == 0.0 and abs(360.0 - val) < 1.0)):
                best_idx = i
                break
        with QSignalBlocker(self.gradient_direction_combo):
            self.gradient_direction_combo.setCurrentIndex(best_idx)
        self.gradient_bar.set_gradient(
            self.gradient_colors_store,
            val,
            self.gradient_enabled_checkbox.isChecked(),
        )
        self._schedule_preview_update()

    def _choose_gradient_color(self, index: int) -> None:
        if len(self.gradient_colors_store) < 2:
            self.gradient_colors_store = ["#FF0000", "#0000FF"]
        resolved_idx = (len(self.gradient_colors_store) - 1) if index == -1 else index
        current_hex = (
            self.gradient_colors_store[resolved_idx]
            if 0 <= resolved_idx < len(self.gradient_colors_store)
            else "#000000"
        )
        color = QColorDialog.getColor(QColor(current_hex), self, "Pilih Warna Gradient")
        if color.isValid():
            self.gradient_colors_store[resolved_idx] = color.name()
            self._update_gradient_buttons_style()
            self._schedule_preview_update()

    def _swap_gradient_colors(self) -> None:
        self.gradient_colors_store.reverse()
        self._update_gradient_buttons_style()
        self._schedule_preview_update()

    def _add_gradient_stop(self) -> None:
        c = QColorDialog.getColor(QColor("#ffffff"), self, "Tambah Warna Tengah Gradient")
        if not c.isValid():
            return
        insert_at = max(1, len(self.gradient_colors_store) - 1)
        self.gradient_colors_store.insert(insert_at, c.name())
        self._update_gradient_buttons_style()
        self._update_gradient_ui_state()

    def _remove_gradient_stop(self) -> None:
        if len(self.gradient_colors_store) <= 2:
            return
        self.gradient_colors_store.pop(len(self.gradient_colors_store) - 2)
        self._update_gradient_buttons_style()
        self._update_gradient_ui_state()

    def _apply_gradient_preset(self, colors: list[str]) -> None:
        self.gradient_colors_store = list(colors)
        if not self.gradient_enabled_checkbox.isChecked():
            self.gradient_enabled_checkbox.setChecked(True)
        self._update_gradient_buttons_style()
        self._update_gradient_ui_state()

    def _update_gradient_buttons_style(self) -> None:
        if len(self.gradient_colors_store) < 2:
            self.gradient_colors_store = ["#FF0000", "#0000FF"]
        c1 = self.gradient_colors_store[0]
        c_end = self.gradient_colors_store[-1]
        self.gradient_color1_btn.setStyleSheet(_swatch_button_qss(c1))
        self.gradient_color2_btn.setStyleSheet(_swatch_button_qss(c_end))

        # Rebuild middle stop swatch buttons if there are 3+ colors
        while self._gradient_extra_stops_row.count():
            item = self._gradient_extra_stops_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for mid_idx in range(1, len(self.gradient_colors_store) - 1):
            col_hex = self.gradient_colors_store[mid_idx]
            btn = QPushButton(f"#{mid_idx + 1}")
            btn.setStyleSheet(_swatch_button_qss(col_hex))
            btn.setEnabled(self.gradient_enabled_checkbox.isChecked())
            btn.clicked.connect(lambda _c=False, idx=mid_idx: self._choose_gradient_color(idx))
            self._gradient_extra_stops_row.addWidget(btn)

        self.gradient_remove_stop_btn.setEnabled(
            self.gradient_enabled_checkbox.isChecked() and len(self.gradient_colors_store) > 2
        )
        self.gradient_bar.set_gradient(
            self.gradient_colors_store,
            self.gradient_angle_spin.value(),
            self.gradient_enabled_checkbox.isChecked(),
        )

    # ------------------------------------------------------------------
    # Pattern, Shadow, Outline & Layer controls
    # ------------------------------------------------------------------
    def _update_pattern_ui_state(self) -> None:
        enabled = self.pattern_enabled_checkbox.isChecked()
        self.pattern_type_combo.setEnabled(enabled)
        self.pattern_scale_spin.setEnabled(enabled)
        self._schedule_preview_update()

    def _update_shadow_ui_state(self) -> None:
        enabled = self.shadow_enabled_checkbox.isChecked()
        for w in (
            self.shadow_color_btn,
            self.shadow_blur_spin,
            self.shadow_offset_x_spin,
            self.shadow_offset_y_spin,
            self.shadow_opacity_spin,
        ):
            w.setEnabled(enabled)
        self._schedule_preview_update()

    def _update_shadow_color_button_ui(self, color: QColor) -> None:
        self.shadow_color_btn.setStyleSheet(_swatch_button_qss(color))

    def _choose_shadow_color(self) -> None:
        c = QColorDialog.getColor(self._shadow_color, self, "Pilih Warna Bayangan")
        if c.isValid():
            self._shadow_color = c
            self._update_shadow_color_button_ui(c)
            self._schedule_preview_update()

    def _refresh_layers_list(self) -> None:
        curr = self.layers_list.currentRow()
        self.layers_list.clear()
        for idx, layer in enumerate(self.outline_layers_store):
            w = layer.get("width", 2.0)
            c = layer.get("color", "#000000")
            item = QListWidgetItem(f"Layer {idx + 1}: {w} px — {c}")
            item.setBackground(QColor(c))
            item.setForeground(QColor("#020617" if _is_light_color(c) else "#f8fafc"))
            self.layers_list.addItem(item)
        if 0 <= curr < self.layers_list.count():
            with QSignalBlocker(self.layers_list):
                self.layers_list.setCurrentRow(curr)

    def _add_layer(self) -> None:
        c = QColorDialog.getColor(Qt.black, self, "Pilih Warna Outline Layer")
        if c.isValid():
            self.outline_layers_store.append({"width": 2.0, "color": c.name()})
            self._refresh_layers_list()
            self.layers_list.setCurrentRow(len(self.outline_layers_store) - 1)
            self._schedule_preview_update()

    def _remove_layer(self) -> None:
        row = self.layers_list.currentRow()
        if 0 <= row < len(self.outline_layers_store):
            self.outline_layers_store.pop(row)
            self._refresh_layers_list()
            self._schedule_preview_update()

    def _on_layer_selected_changed(self) -> None:
        row = self.layers_list.currentRow()
        if 0 <= row < len(self.outline_layers_store):
            layer = self.outline_layers_store[row]
            with QSignalBlocker(self.layer_width_spin):
                self.layer_width_spin.setValue(float(layer.get("width", 2.0)))

    def _on_layer_width_changed(self) -> None:
        row = self.layers_list.currentRow()
        if 0 <= row < len(self.outline_layers_store):
            self.outline_layers_store[row]["width"] = self.layer_width_spin.value()
            self._refresh_layers_list()
            self._schedule_preview_update()

    def _choose_layer_color(self) -> None:
        row = self.layers_list.currentRow()
        if 0 <= row < len(self.outline_layers_store):
            current_c = QColor(self.outline_layers_store[row].get("color", "#000000"))
            c = QColorDialog.getColor(current_c, self, "Ubah Warna Outline Layer")
            if c.isValid():
                self.outline_layers_store[row]["color"] = c.name()
                self._refresh_layers_list()
                self._schedule_preview_update()

    def _update_outline_color_button_ui(self, color: QColor | None = None) -> None:
        if color is None:
            color = self._outline_color if isinstance(self._outline_color, QColor) else QColor("#000000")
        if not color.isValid():
            color = QColor("#000000")
        self._outline_color = color
        self.outline_color_button.setStyleSheet(_swatch_button_qss(color))

    def _choose_outline_color(self) -> None:
        color = QColorDialog.getColor(self._outline_color, self, "Pilih Warna Outline / Glow")
        if color.isValid():
            self._outline_color = color
            self._update_outline_color_button_ui(color)
            self._schedule_preview_update()

    def _update_outline_controls_enabled(self) -> None:
        enabled = self.text_outline_checkbox.isChecked()
        self.outline_style_combo.setEnabled(enabled)
        self.outline_width_spin.setEnabled(enabled)
        self.outline_color_button.setEnabled(enabled)
        style_key = self.outline_style_combo.currentData() or "stroke"
        self.outline_color_button.setText("Glow Color" if enabled and style_key == "glow" else "Outline Color")
        self._schedule_preview_update()

    # ------------------------------------------------------------------
    # Margins & Bezier / Warp synchronization
    # ------------------------------------------------------------------
    def _reset_margins(self) -> None:
        for sp in (self.margin_top_spin, self.margin_right_spin, self.margin_bottom_spin, self.margin_left_spin):
            with QSignalBlocker(sp):
                sp.setValue(0)
        self._schedule_preview_update()

    def _create_bezier_spin(self) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(-1.0, 2.0)
        spin.setDecimals(3)
        spin.setSingleStep(0.05)
        return spin

    def _sync_curve_editor_from_spins(self) -> None:
        self.curve_editor.set_control_points(
            self.cp1x_spin.value(),
            self.cp1y_spin.value(),
            self.cp2x_spin.value(),
            self.cp2y_spin.value(),
        )

    def _on_curve_editor_changed(self, cp1x: float, cp1y: float, cp2x: float, cp2y: float) -> None:
        for sp, val in (
            (self.cp1x_spin, cp1x),
            (self.cp1y_spin, cp1y),
            (self.cp2x_spin, cp2x),
            (self.cp2y_spin, cp2y),
        ):
            with QSignalBlocker(sp):
                sp.setValue(val)
        self._schedule_preview_update()

    def _on_bezier_spin_changed(self) -> None:
        self._sync_curve_editor_from_spins()
        self._schedule_preview_update()

    def _on_effect_changed(self) -> None:
        self._update_bezier_status_ui()
        self._schedule_preview_update()

    def _update_bezier_status_ui(self) -> None:
        is_curved = (self.effect_combo.currentData() == "curved")
        if is_curved:
            self._bezier_status_pill.setText("Aktif (Curved)")
            self._bezier_status_pill.setStyleSheet(
                f"background: {COLORS['card_alt']}; color: {COLORS['accent']}; "
                f"border: 1px solid {COLORS['accent']}; border-radius: 9px; padding: 2px 8px; font-size: 10px; font-weight: 700;"
            )
            self.use_curved_btn.setVisible(False)
        else:
            self._bezier_status_pill.setText("Nonaktif — Effect != Curved")
            self._bezier_status_pill.setStyleSheet("")
            self.use_curved_btn.setVisible(True)

    def _activate_curved_mode(self) -> None:
        idx = self.effect_combo.findData("curved")
        if idx >= 0:
            self.effect_combo.setCurrentIndex(idx)
        if self.effect_intensity_spin.value() <= 0.0:
            self.effect_intensity_spin.setValue(35.0)
        self._update_bezier_status_ui()
        self._schedule_preview_update()

    def _reset_bezier_curve(self) -> None:
        defaults = ((self.cp1x_spin, 0.25), (self.cp1y_spin, 0.20), (self.cp2x_spin, 0.75), (self.cp2y_spin, 0.20))
        for sp, val in defaults:
            with QSignalBlocker(sp):
                sp.setValue(val)
        self._sync_curve_editor_from_spins()
        self._schedule_preview_update()

    # ------------------------------------------------------------------
    # Fonts, rich-text formatting & cursor tracking
    # ------------------------------------------------------------------
    def _populate_font_groups_and_fonts(self) -> None:
        try:
            main_win = self.parent()
            if getattr(main_win, "font_groups", None):
                with QSignalBlocker(self.font_group_combo):
                    self.font_group_combo.clear()
                    self.font_group_combo.addItem("All")
                    for group_name in main_win.font_groups.keys():
                        self.font_group_combo.addItem(group_name)
            self.font_group_combo.currentTextChanged.connect(self._on_dialog_font_group_changed)
        except Exception:
            pass
        sel = self.font_group_combo.currentText()
        self._populate_dialog_fonts(None if sel == "All" else sel)

    def _populate_dialog_fonts(self, group: str | None = None) -> None:
        try:
            fonts = self.font_manager.list_fonts() if self.font_manager else []
            if group and getattr(self.parent(), "font_groups", None):
                from src.core.fonts import fonts_in_group

                fonts = fonts_in_group(fonts, self.parent().font_groups.get(group, []), font_manager=self.font_manager)
            with QSignalBlocker(self.font_combo):
                self.font_combo.clear()
                for name in fonts:
                    self.font_combo.addItem(name)
                    preview_font = self.font_manager.create_qfont(name) if self.font_manager else QFont(name)
                    preview_font.setPointSize(14)
                    self.font_combo.setItemData(self.font_combo.count() - 1, preview_font, Qt.FontRole)
        except Exception:
            traceback.print_exc()

    def _on_dialog_font_group_changed(self, group_name: str) -> None:
        self._populate_dialog_fonts(None if group_name == "All" else group_name)

    def _update_font_preview(self, display_name: str) -> None:
        if not self.font_manager or not display_name:
            return
        base_font = self.text_edit.currentCharFormat().font()
        if not base_font.family():
            base_font = self.area.get_font()
        preview_font = self.font_manager.create_qfont(display_name, base_font=base_font)
        preview_font.setPointSizeF(min(18.0, max(9.0, self.font_size_spin.value())))
        preview_font.setWeight(base_font.weight())
        preview_font.setItalic(base_font.italic())
        self.font_preview.setFont(preview_font)
        self.font_preview.setToolTip(display_name)

    def _remember_cursor_state(self) -> None:
        try:
            cursor = self.text_edit.textCursor()
            if self._is_cursor_valid(cursor):
                self._last_text_cursor = QTextCursor(cursor)
            else:
                self._last_text_cursor = QTextCursor(self.text_edit.document())
        except Exception:
            traceback.print_exc()

    def _is_cursor_valid(self, cursor: QTextCursor | None) -> bool:
        try:
            if cursor is None or cursor.isNull():
                return False
            doc = self.text_edit.document()
            if cursor.document() is not doc:
                return False
            length = doc.characterCount()
            return 0 <= cursor.position() <= length and 0 <= cursor.anchor() <= length
        except Exception:
            return False

    def _merge_char_format(self, fmt: QTextCharFormat) -> None:
        if fmt is None:
            return
        try:
            cursor = self.text_edit.textCursor()
            if cursor is None or cursor.isNull():
                return
            if not cursor.hasSelection():
                stored = getattr(self, "_last_text_cursor", None)
                if self._is_cursor_valid(stored) and stored.hasSelection():
                    cursor = QTextCursor(stored)
                    self.text_edit.setTextCursor(cursor)
                else:
                    cursor.select(QTextCursor.WordUnderCursor)
            self.text_edit.setTextCursor(cursor)
            cursor.mergeCharFormat(fmt)
            self.text_edit.mergeCurrentCharFormat(fmt)
            self.text_edit.ensureCursorVisible()
            self._last_text_cursor = QTextCursor(self.text_edit.textCursor())
            self._schedule_preview_update()
        except Exception:
            traceback.print_exc()

    def _change_font_family(self, display_name: str) -> None:
        if not display_name:
            return
        try:
            cursor_font = self.text_edit.currentCharFormat().font()
            if not cursor_font.family():
                cursor_font = self.area.get_font()
            if self.font_manager:
                new_font = self.font_manager.create_qfont(display_name, base_font=cursor_font)
            else:
                new_font = QFont(cursor_font)
                new_font.setFamily(display_name)
            new_font.setPointSizeF(self.font_size_spin.value())
            new_font.setLetterSpacing(cursor_font.letterSpacingType(), cursor_font.letterSpacing())
            new_font.setWeight(cursor_font.weight())
            new_font.setItalic(cursor_font.italic())
            new_font.setUnderline(cursor_font.underline())
            fmt = QTextCharFormat()
            fmt.setFont(new_font)
            self._merge_char_format(fmt)
            self._update_font_preview(display_name)
        except Exception:
            traceback.print_exc()

    def _change_font_size(self, value: float) -> None:
        fmt = QTextCharFormat()
        fmt.setFontPointSize(float(value))
        self._merge_char_format(fmt)
        current = self.font_combo.currentText()
        if current:
            self._update_font_preview(current)

    def _toggle_bold(self, checked: bool) -> None:
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Bold if checked else QFont.Normal)
        self._merge_char_format(fmt)

    def _toggle_italic(self, checked: bool) -> None:
        fmt = QTextCharFormat()
        fmt.setFontItalic(checked)
        self._merge_char_format(fmt)

    def _toggle_underline(self, checked: bool) -> None:
        fmt = QTextCharFormat()
        fmt.setFontUnderline(checked)
        self._merge_char_format(fmt)

    def _choose_color(self) -> None:
        initial = self._current_color_from_cursor()
        if self.gradient_enabled_checkbox.isChecked() and self.gradient_colors_store:
            initial = QColor(self.gradient_colors_store[0])
        color = QColorDialog.getColor(initial, self, "Pilih Warna Teks")
        if color.isValid():
            if self.gradient_enabled_checkbox.isChecked():
                self.gradient_enabled_checkbox.setChecked(False)
            fmt = QTextCharFormat()
            fmt.setForeground(QBrush(color))
            self._merge_char_format(fmt)
            self._update_color_button(color)
            self._apply_editor_contrast(color)
            self._manual_text_color_changed = True

    def _current_color_from_cursor(self) -> QColor:
        fmt = self.text_edit.currentCharFormat()
        brush = fmt.foreground()
        return brush.color() if brush.style() != Qt.NoBrush else self.area.get_color()

    def _update_color_button(self, color: QColor) -> None:
        if color.isValid():
            self.color_button.setStyleSheet(_swatch_button_qss(color))
        else:
            self.color_button.setStyleSheet("")

    def _apply_editor_contrast(self, text_col: QColor | str) -> None:
        qcol = QColor(text_col) if isinstance(text_col, (str, QColor)) else QColor("#f8fafc")
        is_dark_text = qcol.isValid() and qcol.lightness() < 128
        bg_col = "#f1f5f9" if is_dark_text else "#0c121d"
        fg_col = qcol.name() if qcol.isValid() else "#e8eef7"
        self.text_edit.setStyleSheet(
            f"QTextEdit {{ background: {bg_col}; color: {fg_col}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 8px; padding: 10px; }}"
        )
        self._contrast_pill.setText(
            AdvancedEditorText.CONTRAST_LIGHT_PILL if is_dark_text else AdvancedEditorText.CONTRAST_DARK_PILL
        )

    def _apply_alignment(self) -> None:
        try:
            doc = self.text_edit.document()
            original = self.text_edit.textCursor()
            cursor = QTextCursor(doc)
            cursor.select(QTextCursor.Document)
            block_format = QTextBlockFormat()
            _, align_flag = self.ALIGN_OPTIONS[max(0, self.alignment_combo.currentIndex())]
            block_format.setAlignment(align_flag)
            block_format.setLineHeight(int(self.line_spacing_spin.value() * 100), QTextBlockFormat.ProportionalHeight)
            cursor.setBlockFormat(block_format)
            self.text_edit.setTextCursor(original)
            self._schedule_preview_update()
        except Exception:
            traceback.print_exc()

    def _apply_line_spacing(self) -> None:
        self._apply_alignment()

    def _apply_char_spacing(self) -> None:
        try:
            spacing_value = self.char_spacing_spin.value()
            original = self.text_edit.textCursor()
            cursor = QTextCursor(self.text_edit.document())
            cursor.beginEditBlock()
            cursor.select(QTextCursor.Document)
            fmt = QTextCharFormat()
            base_font = self.text_edit.currentCharFormat().font()
            if not base_font.family():
                base_font = self.area.get_font()
            font = QFont(base_font)
            font.setLetterSpacing(QFont.PercentageSpacing, spacing_value)
            fmt.setFont(font)
            cursor.mergeCharFormat(fmt)
            cursor.endEditBlock()
            self.text_edit.setTextCursor(original)
            self._schedule_preview_update()
        except Exception:
            traceback.print_exc()

    def _sync_toolbar_from_cursor(self) -> None:
        fmt = self.text_edit.currentCharFormat()
        current_font = fmt.font()
        if not current_font.family():
            current_font = self.area.get_font()
        display = self.font_manager.display_name_for_font(current_font) if self.font_manager else None
        display = display or current_font.family()
        if display:
            with QSignalBlocker(self.font_combo):
                self.font_combo.setCurrentText(display)
        point = fmt.fontPointSize() or current_font.pointSizeF() or current_font.pointSize()
        with QSignalBlocker(self.font_size_spin):
            self.font_size_spin.setValue(float(point))
        with QSignalBlocker(self.bold_button):
            self.bold_button.setChecked(fmt.fontWeight() >= QFont.Bold)
        with QSignalBlocker(self.italic_button):
            self.italic_button.setChecked(fmt.fontItalic())
        with QSignalBlocker(self.underline_button):
            self.underline_button.setChecked(fmt.fontUnderline())
        col = self._current_color_from_cursor()
        self._update_color_button(col)
        if display:
            self._update_font_preview(display)
        self._apply_editor_contrast(col)

    # ------------------------------------------------------------------
    # Initial load, Actions & Result packaging
    # ------------------------------------------------------------------
    def _load_area_into_editor(self) -> None:
        from src.ui.canvas import TypesetArea

        self.text_edit.clear()
        cursor = QTextCursor(self.text_edit.document())
        cursor.movePosition(QTextCursor.Start)

        segments = self.area.get_segments()
        if not segments:
            segments = [{
                "text": self.area.text or "",
                "font": TypesetArea.font_to_dict(self.area.get_font()),
                "color": self.area.get_color().name(),
                "underline": False,
            }]

        for segment in segments:
            text_value = segment.get("text", "")
            if not text_value:
                continue
            fmt = QTextCharFormat()
            seg_font = self.area.segment_to_qfont(segment)
            fmt.setFont(seg_font)
            fmt.setForeground(QBrush(self.area.segment_to_color(segment)))
            if segment.get("underline", seg_font.underline()):
                fmt.setFontUnderline(True)

            parts = text_value.split("\n")
            for idx, part in enumerate(parts):
                cursor.insertText(part, fmt)
                if idx < len(parts) - 1:
                    cursor.insertBlock()

        ori_idx = self.orientation_combo.findData(str(self.area.get_orientation() or "horizontal").lower())
        with QSignalBlocker(self.orientation_combo):
            self.orientation_combo.setCurrentIndex(ori_idx if ori_idx >= 0 else 0)

        current_effect = self.area.get_effect()
        effect_idx = next((i for i, (_, val) in enumerate(self.EFFECT_OPTIONS) if val == current_effect), 0)
        with QSignalBlocker(self.effect_combo):
            self.effect_combo.setCurrentIndex(effect_idx)

        margins = self.area.get_margins() or {}
        for sp, key in (
            (self.margin_top_spin, "top"),
            (self.margin_right_spin, "right"),
            (self.margin_bottom_spin, "bottom"),
            (self.margin_left_spin, "left"),
        ):
            with QSignalBlocker(sp):
                sp.setValue(int(margins.get(key, 0)))

        align_val = self.area.get_alignment() or "center"
        idx_align = next(
            (i for i, (lbl, _) in enumerate(self.ALIGN_OPTIONS) if lbl.lower().startswith(align_val.lower())),
            0,
        )
        with QSignalBlocker(self.alignment_combo):
            self.alignment_combo.setCurrentIndex(idx_align)

        with QSignalBlocker(self.line_spacing_spin):
            self.line_spacing_spin.setValue(float(self.area.get_line_spacing()))
        with QSignalBlocker(self.char_spacing_spin):
            self.char_spacing_spin.setValue(float(self.area.get_char_spacing()))
        self._apply_alignment()

        has_outline = bool(self.area.has_text_outline()) if hasattr(self.area, "has_text_outline") else False
        with QSignalBlocker(self.text_outline_checkbox):
            self.text_outline_checkbox.setChecked(has_outline)
        outline_width = float(self.area.get_text_outline_width()) if hasattr(self.area, "get_text_outline_width") else 2.0
        with QSignalBlocker(self.outline_width_spin):
            self.outline_width_spin.setValue(outline_width)
        outline_style = (
            str(self.area.get_text_outline_style() or "stroke").strip().lower()
            if hasattr(self.area, "get_text_outline_style")
            else "stroke"
        )
        style_idx = self.outline_style_combo.findData(outline_style)
        with QSignalBlocker(self.outline_style_combo):
            self.outline_style_combo.setCurrentIndex(style_idx if style_idx >= 0 else 0)
        outline_color_val = self.area.get_text_outline_color() if hasattr(self.area, "get_text_outline_color") else "#000000"
        self._outline_color = (
            QColor(outline_color_val) if isinstance(outline_color_val, (str, QColor)) else QColor("#000000")
        )
        self._update_outline_color_button_ui(self._outline_color)
        self._update_outline_controls_enabled()

        with QSignalBlocker(self.effect_intensity_spin):
            self.effect_intensity_spin.setValue(float(self.area.get_effect_intensity()))
        with QSignalBlocker(self.bubble_checkbox):
            self.bubble_checkbox.setChecked(bool(getattr(self.area, "bubble_enabled", False)))

        bezier = self.area.get_bezier_points()
        if len(bezier) >= 2:
            for sp, val in (
                (self.cp1x_spin, bezier[0].get("x", 0.25)),
                (self.cp1y_spin, bezier[0].get("y", 0.2)),
                (self.cp2x_spin, bezier[1].get("x", 0.75)),
                (self.cp2y_spin, bezier[1].get("y", 0.2)),
            ):
                with QSignalBlocker(sp):
                    sp.setValue(float(val))
            self._sync_curve_editor_from_spins()

        with QSignalBlocker(self.smart_fit_checkbox):
            self.smart_fit_checkbox.setChecked(bool(getattr(self.area, "smart_fit_enabled", False)))

        with QSignalBlocker(self.shadow_enabled_checkbox):
            self.shadow_enabled_checkbox.setChecked(bool(getattr(self.area, "shadow_enabled", False)))
        self._shadow_color = QColor(getattr(self.area, "shadow_color", "#000000"))
        self._update_shadow_color_button_ui(self._shadow_color)
        with QSignalBlocker(self.shadow_blur_spin):
            self.shadow_blur_spin.setValue(float(getattr(self.area, "shadow_blur", 4.0)))
        with QSignalBlocker(self.shadow_offset_x_spin):
            self.shadow_offset_x_spin.setValue(float(getattr(self.area, "shadow_offset_x", 3.0)))
        with QSignalBlocker(self.shadow_offset_y_spin):
            self.shadow_offset_y_spin.setValue(float(getattr(self.area, "shadow_offset_y", 3.0)))
        with QSignalBlocker(self.shadow_opacity_spin):
            self.shadow_opacity_spin.setValue(float(getattr(self.area, "shadow_opacity", 0.7)))
        self._update_shadow_ui_state()

        with QSignalBlocker(self.pattern_enabled_checkbox):
            self.pattern_enabled_checkbox.setChecked(bool(getattr(self.area, "pattern_fill_enabled", False)))
        p_idx = self.pattern_type_combo.findData(getattr(self.area, "pattern_type", "dot"))
        with QSignalBlocker(self.pattern_type_combo):
            if p_idx >= 0:
                self.pattern_type_combo.setCurrentIndex(p_idx)
        with QSignalBlocker(self.pattern_scale_spin):
            self.pattern_scale_spin.setValue(float(getattr(self.area, "pattern_scale", 1.0)))
        self._update_pattern_ui_state()

        self.outline_layers_store = copy.deepcopy(getattr(self.area, "outline_layers", []))
        self._refresh_layers_list()

        with QSignalBlocker(self.gradient_enabled_checkbox):
            self.gradient_enabled_checkbox.setChecked(bool(self.area.get_extra("gradient_enabled")))
        grad_colors = self.area.get_extra("gradient_colors")
        if isinstance(grad_colors, list) and len(grad_colors) >= 2:
            self.gradient_colors_store = [str(c) for c in grad_colors]
        else:
            self.gradient_colors_store = ["#FF0000", "#0000FF"]
        with QSignalBlocker(self.gradient_angle_spin):
            self.gradient_angle_spin.setValue(float(self.area.get_extra("gradient_angle") or 0.0))
        direction_str = self.area.get_extra("gradient_direction")
        if direction_str:
            with QSignalBlocker(self.gradient_direction_combo):
                self.gradient_direction_combo.setCurrentText(str(direction_str))
        self._update_gradient_buttons_style()
        self._update_gradient_ui_state()

    @staticmethod
    def _add_menu_header(menu: QMenu, title: str) -> None:
        from PyQt5.QtWidgets import QWidgetAction

        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"color: {COLORS['accent']}; font-size: 10px; font-weight: 700; "
            f"padding: 5px 12px 3px 12px; background: transparent;"
        )
        act = QWidgetAction(menu)
        act.setDefaultWidget(lbl)
        act.setEnabled(False)
        menu.addAction(act)

    def _build_symbols_menu(self) -> QMenu:
        """Build grouped symbols menu with dedicated quick-access & categorized Love submenus."""
        menu = QMenu(self)
        self.symbol_submenus: dict[str, QMenu] = {}

        self._add_menu_header(menu, AdvancedEditorText.SYM_SECTION_QUICK_LOVE)
        for label, symbol in self.QUICK_LOVE_SYMBOLS:
            action = menu.addAction(f"{symbol}   {label}")
            action.setData(symbol)
            action.triggered.connect(lambda checked=False, s=symbol: self._insert_emoji(s))

        menu.addSeparator()
        self._add_menu_header(menu, AdvancedEditorText.SYM_SECTION_CATEGORIES)

        for cat in self.SYMBOL_CATEGORIES:
            submenu = QMenu(str(cat["title"]).replace("&", "&&"), menu)
            submenu.setIcon(app_icon(cat["icon"], color=cat.get("color", COLORS["accent"]), size=14))
            for label, symbol in cat["items"]:
                action = submenu.addAction(f"{symbol}   {label}")
                action.setData(symbol)
                action.triggered.connect(lambda checked=False, s=symbol: self._insert_emoji(s))
            menu.addMenu(submenu)
            self.symbol_submenus[cat["key"]] = submenu

        return menu

    def _insert_emoji(self, text: str) -> None:
        if not text:
            return
        try:
            cursor = self.text_edit.textCursor()
            if not self._is_cursor_valid(cursor):
                cursor = QTextCursor(self.text_edit.document())
                cursor.movePosition(QTextCursor.End)
            cursor.insertText(text)
            self.text_edit.setTextCursor(cursor)
            self._last_text_cursor = QTextCursor(cursor)
        except Exception:
            traceback.print_exc()

    def _show_recent_menu(self) -> None:
        parent = self.parent()
        if not parent or not hasattr(parent, "history_entries"):
            return

        from PyQt5.QtWidgets import QAction

        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{ background-color: {COLORS['panel']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']}; }}"
            f"QMenu::item:selected {{ background-color: {COLORS['card_alt']}; color: {COLORS['accent']}; }}"
        )

        recent_texts = []
        for entry in reversed(parent.history_entries):
            text = entry.get("translated_text", "").strip()
            if text and text not in recent_texts:
                recent_texts.append(text)
                if len(recent_texts) >= 20:
                    break

        if not recent_texts:
            action = QAction("Belum ada riwayat terjemahan", self)
            action.setEnabled(False)
            menu.addAction(action)
        else:
            for text in recent_texts:
                display_text = text if len(text) <= 44 else text[:41] + "..."
                action = QAction(display_text, self)
                action.setData(text)
                menu.addAction(action)

        def on_action(act):
            if act.data():
                cursor = self.text_edit.textCursor()
                if cursor.hasSelection():
                    cursor.insertText(act.data())
                else:
                    self.text_edit.setPlainText(act.data())

        menu.triggered.connect(on_action)
        menu.exec_(self.recent_translations_btn.mapToGlobal(QPoint(0, self.recent_translations_btn.height())))

    def _on_ai_translate_clicked(self) -> None:
        parent = self.parent()
        if not parent or not hasattr(parent, "get_selected_model_name"):
            return

        cursor = self.text_edit.textCursor()
        selected_text = cursor.selectedText()
        if selected_text:
            text_to_translate = selected_text
            is_selection = True
        else:
            text_to_translate = self.text_edit.toPlainText()
            is_selection = False

        if not text_to_translate.strip():
            return

        provider, model_name = parent.get_selected_model_name()
        if not model_name:
            notify_banner(
                self,
                "advanced-edit-no-model",
                "No model",
                "Silakan pilih model AI di jendela utama terlebih dahulu.",
                kind="warning",
            )
            return

        self.ai_translate_btn.setEnabled(False)
        self.ai_translate_btn.setText(AdvancedEditorText.BTN_TRANSLATING)
        QApplication.processEvents()
        try:
            translated = parent.translate_with_ai(text_to_translate, {}, provider, model_name, {})
            if is_selection:
                cursor.insertText(str(translated))
            else:
                self.text_edit.setPlainText(str(translated))
        except Exception as exc:
            notify_banner(self, "advanced-edit-translation-failed", "Error", f"Translation failed: {exc}", kind="error")
        finally:
            self.ai_translate_btn.setEnabled(True)
            self.ai_translate_btn.setText(AdvancedEditorText.BTN_AI_TRANSLATE)

    def _on_revert_clicked(self) -> None:
        notes = self.area.review_notes if isinstance(getattr(self.area, "review_notes", {}), dict) else {}
        for legacy in ("manual_inpaint", "manual"):
            notes.pop(legacy, None)
        self.area.review_notes = notes
        if hasattr(self.area, "clear_override"):
            for key in ("use_inpaint", "use_background_box", "constrain_text", "use_auto_text_color"):
                self.area.clear_override(key)
        self._manual_text_color_changed = False
        parent = self.parent()
        if parent and hasattr(parent, "redraw_all_typeset_areas"):
            try:
                parent.redraw_all_typeset_areas()
            except Exception:
                pass
        if parent and getattr(parent, "selected_typeset_area", None) is self.area:
            try:
                parent._sync_cleanup_controls_from_selection()
            except Exception:
                pass
        self._refresh_live_preview()
        notify_toast(
            self,
            "Reverted",
            "Override area ini dihapus dan akan mengikuti pengaturan global.",
            kind="success",
        )

    def _extract_segments(self) -> list[dict]:
        from src.ui.canvas import TypesetArea

        segments = []
        try:
            doc = self.text_edit.document()
            block = doc.begin()
            while block != doc.end():
                it = block.begin()
                while not it.atEnd():
                    fragment = it.fragment()
                    if fragment.isValid():
                        text = fragment.text()
                        if text:
                            fmt = fragment.charFormat()
                            font = fmt.font()
                            fg_color = fmt.foreground().color()
                            segments.append({
                                "text": text,
                                "font": TypesetArea.font_to_dict(font),
                                "color": fg_color.name() if fg_color.isValid() else self.area.get_color().name(),
                                "underline": fmt.fontUnderline(),
                            })
                    it += 1
                block = block.next()
                if block != doc.end():
                    segments.append({
                        "text": "\n",
                        "font": TypesetArea.font_to_dict(self.area.get_font()),
                        "color": self.area.get_color().name(),
                        "underline": False,
                    })
        except Exception:
            traceback.print_exc()
        return segments

    def _handle_accept(self) -> None:
        try:
            segments = self._extract_segments()
            plain_text = "".join(seg.get("text", "") for seg in segments)
            orientation = self.orientation_combo.currentData() or "horizontal"
            effect = self.effect_combo.currentData()
            bezier_data = [
                {"x": self.cp1x_spin.value(), "y": self.cp1y_spin.value()},
                {"x": self.cp2x_spin.value(), "y": self.cp2y_spin.value()},
            ]
            margins = {
                "top": self.margin_top_spin.value(),
                "right": self.margin_right_spin.value(),
                "bottom": self.margin_bottom_spin.value(),
                "left": self.margin_left_spin.value(),
            }
            align_label, _ = self.ALIGN_OPTIONS[max(0, self.alignment_combo.currentIndex())]
            self.result = {
                "segments": segments,
                "plain_text": plain_text,
                "orientation": orientation,
                "effect": effect,
                "effect_intensity": self.effect_intensity_spin.value(),
                "bezier_points": bezier_data,
                "bubble_enabled": self.bubble_checkbox.isChecked(),
                "alignment": align_label.lower(),
                "line_spacing": self.line_spacing_spin.value(),
                "char_spacing": self.char_spacing_spin.value(),
                "margins": margins,
                "text_outline": self.text_outline_checkbox.isChecked(),
                "text_outline_width": self.outline_width_spin.value(),
                "text_outline_color": (
                    self._outline_color.name() if isinstance(self._outline_color, QColor) else str(self._outline_color)
                ),
                "text_outline_style": self.outline_style_combo.currentData() or "stroke",
                "gradient_enabled": self.gradient_enabled_checkbox.isChecked(),
                "gradient_colors": list(self.gradient_colors_store),
                "gradient_angle": self.gradient_angle_spin.value(),
                "gradient_direction": self.gradient_direction_combo.currentText(),
                "shadow_enabled": self.shadow_enabled_checkbox.isChecked(),
                "shadow_color": self._shadow_color.name(),
                "shadow_blur": self.shadow_blur_spin.value(),
                "shadow_offset_x": self.shadow_offset_x_spin.value(),
                "shadow_offset_y": self.shadow_offset_y_spin.value(),
                "shadow_opacity": self.shadow_opacity_spin.value(),
                "outline_layers": copy.deepcopy(self.outline_layers_store),
                "pattern_fill_enabled": self.pattern_enabled_checkbox.isChecked(),
                "pattern_type": self.pattern_type_combo.currentData(),
                "pattern_scale": self.pattern_scale_spin.value(),
                "smart_fit_enabled": self.smart_fit_checkbox.isChecked(),
                "manual_text_color_changed": bool(self._manual_text_color_changed),
            }
            self._last_text_cursor = QTextCursor(self.text_edit.document())
            self.accept()
        except Exception as exc:
            traceback.print_exc()
            notify_banner(
                self,
                "advanced-edit-apply-failed",
                "Apply failed",
                f"Failed to apply text changes: {exc}",
                kind="error",
            )

    def get_result(self):
        return self.result
