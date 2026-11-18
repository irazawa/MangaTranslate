# Manga OCR & Typeset Tool v14.9.9.3
# ==============================
# ?? Import modul bawaan Python
# ==============================
import os
import traceback
import copy

# ==============================
# ?? Library pihak ketiga
# ==============================
# (tidak ada impor pihak ketiga yang dibutuhkan)

# ==============================
# PyQt5 (dibagi per kategori)
# ==============================
from PyQt5.QtWidgets import (
    QApplication, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget,
    QTextEdit, QScrollArea, QComboBox, QMessageBox, QListWidget, QListWidgetItem,
    QColorDialog, QLineEdit, QDialog, QDialogButtonBox, QCheckBox, QSpinBox,
    QTabWidget, QGroupBox, QGridLayout, QFrame, QSplitter, QToolButton, QFormLayout, QFontComboBox,
    QDoubleSpinBox, QSlider,
    QMenu, QTableWidget, QTableWidgetItem, QHeaderView, QStackedWidget, QProgressDialog,
    QAbstractItemView, QProgressBar
)
from PyQt5.QtGui import (
    QColor, QFont, QTextCharFormat, QTextCursor, QBrush, QTextBlockFormat, QPixmap, QImage,
    QIcon, QPainter, QPen
)
from PyQt5.QtCore import (
    Qt, pyqtSignal, QTimer, QSignalBlocker, QSize, QThread, QPoint
)

import sys
import subprocess
import shutil
import importlib
import requests

from src.core.config import *
from src.ui.widgets import *
from src.ui.panels import *
from src.ui.notifications import notify_banner, notify_toast
from src.ui.icons import app_icon, icon_label, status_dot_icon, status_dot_pixmap
from src.ui.texts import AppearanceText, SettingsText, FullPageBatchText, InpaintText
from src.core.workers import InpaintModelDownloadWorker
from src.core.inpaint import (
    engine_display_label,
    format_inpaint_engine_option,
    get_inpaint_manager,
    get_inpaint_spec,
    is_engine_ready,
    list_inpaint_engines,
    normalize_inpaint_engine_id,
    resolve_inpaint_engine_id,
)
from src.ui.theme import (
    APPEARANCE_DEFAULTS,
    DARK_THEME_CHOICES,
    DARK_THEME_PRESETS,
    COLORS,
    normalize_appearance_settings,
    resolve_appearance,
    settings_center_stylesheet,
    advanced_text_editor_stylesheet,
    combo_popup_qss,
    table_header_qss,
    table_qss,
)
from src.utils.helpers import *
from src.core.fonts import *

class APIManagerDialog(QDialog):
    """Modal wrapper that reuses APIManagerPanel and persists changes."""

    TRANSLATION_PROVIDERS = APIManagerPanel.TRANSLATION_PROVIDERS
    OCR_PROVIDERS = APIManagerPanel.OCR_PROVIDERS

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('API Manager')
        self.setModal(True)
        self.resize(860, 520)

        layout = QVBoxLayout(self)
        self.panel = APIManagerPanel(SETTINGS, self)
        layout.addWidget(self.panel)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, self)
        save_btn = buttons.button(QDialogButtonBox.Save)
        save_btn.setText("Save")
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_save(self):
        exported = self.panel.export_settings()
        if exported is None:
            warnings = "\n".join(self.panel.validation_messages())
            details = f"\n\n{warnings}" if warnings else ""
            notify_banner(self, "api-manager-validation", "Validation", f"Please fix the highlighted issues before saving.{details}", kind="warning")
            return

        SETTINGS.setdefault('apis', {})
        SETTINGS.setdefault('ocr', {})
        SETTINGS.setdefault('tesseract', {})
        SETTINGS['apis'] = copy.deepcopy(exported.get('apis', {}))
        SETTINGS['ocr'] = copy.deepcopy(exported.get('ocr', {}))
        SETTINGS['tesseract'] = copy.deepcopy(exported.get('tesseract', {}))
        save_settings(SETTINGS)

        try:
            refresh_api_clients()
        except Exception:
            pass

        parent = self.parent()
        if parent and hasattr(parent, 'populate_ocr_languages'):
            try:
                parent.populate_ocr_languages()
            except Exception:
                pass

        notify_toast(self, "Success", "API settings updated successfully.", kind="success")
        self.accept()

class SettingsDialog(QDialog):
    def __init__(self, parent=None, autosave_enabled: bool = True, autosave_interval_ms: int = 300000):
        super().__init__(parent)
        self.setWindowTitle('Preferences')
        self.setModal(True)
        self.resize(360, 140)

        layout = QVBoxLayout(self)

        # Autosave enable
        self.autosave_checkbox = QCheckBox('Enable autosave', self)
        self.autosave_checkbox.setChecked(bool(autosave_enabled))
        layout.addWidget(self.autosave_checkbox)

        # Interval (seconds)
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel('Autosave interval (seconds):'))
        self.interval_spin = QSpinBox(self)
        self.interval_spin.setRange(5, 3600)  # 5s..1h
        # store/display in seconds for user convenience
        self.interval_spin.setValue(max(5, int(autosave_interval_ms / 1000)))
        interval_layout.addWidget(self.interval_spin)
        layout.addLayout(interval_layout)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self):
        return {
            'enabled': bool(self.autosave_checkbox.isChecked()),
            'interval_ms': int(self.interval_spin.value() * 1000)
        }


class ModelEditDialog(QDialog):
    def __init__(self, parent=None, name: str = "", model_id: str = "", description: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Model Settings")
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("Display name")
        self.id_edit = QLineEdit(model_id)
        self.id_edit.setPlaceholderText("provider/model-id")
        self.description_edit = QLineEdit(description)
        self.description_edit.setPlaceholderText("Optional description")
        form.addRow("Model Name", self.name_edit)
        form.addRow("Model ID", self.id_edit)
        form.addRow("Description", self.description_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self):
        return {
            "name": self.name_edit.text().strip(),
            "id": self.id_edit.text().strip(),
            "description": self.description_edit.text().strip()
        }

class OpenRouterSettingsDialog(QDialog):
    """Backward-compatible dialog wrapper around OpenRouterSettingsPanel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Translation Provider Settings")
        self.setModal(True)
        self.resize(640, 480)

        layout = QVBoxLayout(self)
        self.panel = OpenRouterSettingsPanel(SETTINGS, self)
        layout.addWidget(self.panel)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        self.panel.export_settings()
        self.accept()

    def get_settings(self):
        return self.panel.get_settings()

class SettingsCenterDialog(QDialog):
    """Unified settings dialog — modern sidebar navigation layout."""

    _NAV_ITEMS = SettingsText.NAV_ITEMS

    def __init__(self, main_window, initial_tab="general"):
        super().__init__(main_window)
        self.main_window = main_window
        self._initial_tab_key = initial_tab or "general"
        self.setWindowTitle(SettingsText.TITLE)
        self.setModal(True)
        self.setObjectName("SettingsCenterDialog")
        self.setMinimumSize(900, 620)
        # Fit dialog to the available screen — cap at 85 % height, 75 % width
        try:
            screen = QApplication.primaryScreen().availableGeometry()
            max_h = int(screen.height() * 0.88)
            max_w = int(screen.width() * 0.82)
            dlg_w = min(1120, max_w)
            dlg_h = min(740, max_h)
            self.resize(dlg_w, dlg_h)
            self.setMaximumHeight(max_h)
        except Exception:
            self.resize(1040, 700)
            self.setMaximumHeight(760)

        self._initial_autosave_enabled, self._initial_autosave_interval = self._current_autosave_state()
        self._initial_cleanup = copy.deepcopy(SETTINGS.get('cleanup', {}))
        self._initial_api = {
            'apis': copy.deepcopy(SETTINGS.get('apis', {})),
            'ocr': copy.deepcopy(SETTINGS.get('ocr', {})),
            'tesseract': copy.deepcopy(SETTINGS.get('tesseract', {})),
        }
        self._initial_translate = self._translation_settings_snapshot()
        self._initial_shortcuts = copy.deepcopy(SETTINGS.get('shortcuts', {}))
        self._initial_appearance = normalize_appearance_settings(SETTINGS.get('appearance', {}))
        self.shortcut_editors = {}
        self.appearance_color_edits = {}
        self.appearance_color_buttons = {}

        self._build_ui()

    def _translation_settings_snapshot(self):
        translate = SETTINGS.get('translate', {})
        return {
            key: copy.deepcopy(translate.get(key, {}))
            for key in LOCAL_TRANSLATE_PROVIDERS
        }

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Splitter: left sidebar nav + right content ─────────────────
        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setObjectName("settings-splitter")
        splitter.setHandleWidth(1)

        # Left nav panel
        nav_panel = QWidget()
        nav_panel.setObjectName("settings-nav-panel")
        nav_panel.setFixedWidth(248)
        nav_vbox = QVBoxLayout(nav_panel)
        nav_vbox.setContentsMargins(0, 0, 0, 0)
        nav_vbox.setSpacing(0)

        brand = QWidget()
        brand.setObjectName("settings-nav-brand")
        brand_layout = QVBoxLayout(brand)
        brand_layout.setContentsMargins(20, 18, 18, 16)
        brand_layout.setSpacing(4)
        brand_title = QLabel(SettingsText.HEADER_TITLE)
        brand_title.setObjectName("settings-brand-title")
        brand_subtitle = QLabel(SettingsText.HEADER_SUBTITLE)
        brand_subtitle.setObjectName("settings-brand-subtitle")
        brand_subtitle.setWordWrap(True)
        brand_layout.addWidget(brand_title)
        brand_layout.addWidget(brand_subtitle)
        nav_vbox.insertWidget(0, brand)

        self._nav_list = QListWidget()
        self._nav_list.setObjectName("settings-nav-list")
        self._nav_list.setFocusPolicy(Qt.NoFocus)
        self._nav_list.setSpacing(2)
        self._nav_list.setWordWrap(True)
        self._nav_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._nav_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        for index, meta in enumerate(self._NAV_ITEMS):
            label = meta.get("label", "")
            desc = meta.get("description", "")
            item = QListWidgetItem(f"{index + 1:02d}  {label}\n     {desc}")
            item.setData(Qt.UserRole, meta.get("key", label.lower()))
            item.setToolTip(f"{label} - {desc}")
            item.setSizeHint(QSize(220, 58))
            self._nav_list.addItem(item)
        nav_vbox.addWidget(self._nav_list, 1)

        footer_lbl = QLabel(SettingsText.FOOTER_HINT)
        footer_lbl.setObjectName("settings-nav-footer")
        footer_lbl.setFixedHeight(44)
        footer_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        nav_vbox.addWidget(footer_lbl)

        splitter.addWidget(nav_panel)

        # Right: stacked content + button bar
        right_panel = QWidget()
        right_panel.setObjectName("settings-right-panel")
        right_vbox = QVBoxLayout(right_panel)
        right_vbox.setContentsMargins(0, 0, 0, 0)
        right_vbox.setSpacing(0)

        self._pages = QStackedWidget()
        self._pages.setObjectName("settings-pages")

        self._tab_factories = {
            "general": self._create_general_tab,
            "cleanup": self._create_cleanup_tab,
            "appearance": self._create_appearance_tab,
            "translation": self._create_translation_tab,
            "api": self._create_api_tab,
            "shortcuts": self._create_shortcuts_tab,
            "glossary": self._create_glossary_tab,
        }
        self._page_keys = [meta.get("key") for meta in self._NAV_ITEMS if meta.get("key") in self._tab_factories]
        self._built_tabs = {}
        self._tab_placeholders = {}
        for key in self._page_keys:
            placeholder = QWidget()
            self._tab_placeholders[key] = placeholder
            self._pages.addWidget(placeholder)

        right_vbox.addWidget(self._pages, 1)

        # Button bar
        btn_bar = QWidget()
        btn_bar.setObjectName("settings-btn-bar")
        btn_bar_hbox = QHBoxLayout(btn_bar)
        btn_bar_hbox.setContentsMargins(24, 10, 24, 14)
        btn_bar_hbox.setSpacing(10)
        btn_bar_hbox.addStretch(1)

        self._cancel_btn = QPushButton(SettingsText.BUTTON_CANCEL)
        self._cancel_btn.setObjectName("settings-cancel-btn")
        self._cancel_btn.setFixedWidth(100)
        self._cancel_btn.clicked.connect(self.reject)

        self._apply_btn = QPushButton(SettingsText.BUTTON_APPLY)
        self._apply_btn.setObjectName("settings-apply-btn")
        self._apply_btn.setFixedWidth(100)
        self._apply_btn.clicked.connect(self._on_apply)

        self._save_btn = QPushButton(SettingsText.BUTTON_SAVE)
        self._save_btn.setObjectName("settings-save-btn")
        self._save_btn.setFixedWidth(130)
        self._save_btn.clicked.connect(self._on_save)

        btn_bar_hbox.addWidget(self._cancel_btn)
        btn_bar_hbox.addWidget(self._apply_btn)
        btn_bar_hbox.addWidget(self._save_btn)
        right_vbox.addWidget(btn_bar)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter, 1)

        # Wire nav selection → lazy page switch
        self._nav_list.currentRowChanged.connect(self._on_nav_changed)
        initial_idx = self._nav_index_for_key(getattr(self, "_initial_tab_key", "general"))
        if initial_idx is None:
            initial_idx = 0
        self._nav_list.setCurrentRow(initial_idx)
        self._on_nav_changed(initial_idx)

        self._apply_settings_styles(root_widget=self._built_tabs.get(self._page_keys[initial_idx] if self._page_keys else None))

    def _ensure_tab(self, key: str):
        """Lazily build and insert a settings tab page the first time it is visited."""
        if key in self._built_tabs:
            return self._built_tabs[key]
        factory = self._tab_factories.get(key)
        if factory is None:
            return None
        page = factory()
        self._built_tabs[key] = page
        setattr(self, f"{key}_tab", page)
        placeholder = self._tab_placeholders.get(key)
        if placeholder is not None:
            idx = self._pages.indexOf(placeholder)
            if idx >= 0:
                self._pages.insertWidget(idx, page)
                self._pages.removeWidget(placeholder)
            placeholder.deleteLater()
            self._tab_placeholders.pop(key, None)
        else:
            self._pages.addWidget(page)
        self._style_settings_subtree(page)
        return page

    def _on_nav_changed(self, index):
        """Switch stacked page when user clicks nav item, materializing lazily."""
        if 0 <= index < len(self._page_keys):
            key = self._page_keys[index]
            page = self._ensure_tab(key)
            if page is not None:
                if key == "cleanup":
                    self.sync_cleanup_controls_from_settings()
                self._pages.setCurrentWidget(page)
                return
        if 0 <= index < self._pages.count():
            self._pages.setCurrentIndex(index)

    def _nav_index_for_key(self, key: str):
        normalized = str(key or "").strip().lower()
        aliases = {
            "apis": "api",
            "keys": "api",
            "shortcut": "shortcuts",
            "ocr": "api",
            "plugins": "api",
            "ocr_plugins": "api",
            "theme": "appearance",
            "style": "appearance",
            "inpaint": "cleanup",
            "iopaint": "cleanup",
        }
        normalized = aliases.get(normalized, normalized)
        for index, meta in enumerate(self._NAV_ITEMS):
            if meta.get("key") == normalized:
                return index
        return None

    def _page_meta(self, key: str):
        index = self._nav_index_for_key(key)
        if index is None:
            return {}
        return self._NAV_ITEMS[index]

    def _make_page_scroll(self):
        """Helper: returns (scroll_area, inner_layout) for a settings page."""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        inner.setObjectName("settings-page-inner")
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(32, 26, 32, 28)
        inner_layout.setSpacing(22)
        scroll.setWidget(inner)
        page_layout.addWidget(scroll)
        return page, inner_layout

    def _make_page_header(self, title: str, subtitle: str = ""):
        """Returns a styled header widget for a page."""
        w = QWidget()
        w.setObjectName("settings-page-header")
        vl = QVBoxLayout(w)
        vl.setContentsMargins(0, 0, 0, 12)
        vl.setSpacing(5)
        t = QLabel(title)
        t.setObjectName("settings-page-title")
        vl.addWidget(t)
        if subtitle:
            s = QLabel(subtitle)
            s.setObjectName("settings-page-subtitle")
            s.setWordWrap(True)
            vl.addWidget(s)
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("settings-sep")
        vl.addWidget(sep)
        return w

    def _make_option_row(self, label: str, desc: str, widget):
        """Returns a horizontal row: label+desc on left, widget on right."""
        row = QWidget()
        row.setObjectName("settings-option-row")
        hl = QHBoxLayout(row)
        row.setMinimumHeight(62)
        hl.setContentsMargins(16, 12, 16, 12)
        hl.setSpacing(16)
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        lbl = QLabel(label)
        lbl.setObjectName("settings-option-label")
        lbl.setWordWrap(True)
        lbl.setMinimumWidth(0)
        text_col.addWidget(lbl)
        if desc:
            dlbl = QLabel(desc)
            dlbl.setObjectName("settings-option-desc")
            dlbl.setWordWrap(True)
            dlbl.setMinimumWidth(0)
            text_col.addWidget(dlbl)
        hl.addLayout(text_col, 1)
        hl.addWidget(widget)
        return row

    def _make_panel_page(self, key: str, panel):
        meta = self._page_meta(key)
        page, layout = self._make_page_scroll()
        layout.addWidget(self._make_page_header(
            meta.get("title", key.title()),
            meta.get("subtitle", ""),
        ))
        host = QFrame()
        host.setObjectName("settings-panel-host")
        host_layout = QVBoxLayout(host)
        host_layout.setContentsMargins(0, 0, 0, 0)
        host_layout.setSpacing(0)
        host_layout.addWidget(panel)
        layout.addWidget(host)
        layout.addStretch(1)
        return page

    def _create_general_tab(self):
        meta = self._page_meta("general")
        page, layout = self._make_page_scroll()
        layout.addWidget(self._make_page_header(
            meta.get("title", "General"),
            meta.get("subtitle", ""),
        ))

        # ── Autosave card ────────────────────────────────────────────────
        as_card = QGroupBox("Autosave")
        as_card.setObjectName("settings-card")
        as_vbox = QVBoxLayout(as_card)
        as_vbox.setSpacing(4)
        as_vbox.setContentsMargins(0, 8, 0, 8)

        self.autosave_checkbox = QCheckBox("Enable autosave")
        as_vbox.addWidget(self._make_option_row(
            "Autosave",
            "Periodically save a backup of your current project.",
            self.autosave_checkbox))

        self.autosave_interval_spin = QSpinBox()
        self.autosave_interval_spin.setRange(5, 3600)
        self.autosave_interval_spin.setSingleStep(5)
        self.autosave_interval_spin.setSuffix(" s")
        self.autosave_interval_spin.setFixedWidth(90)
        as_vbox.addWidget(self._make_option_row(
            "Interval",
            "How often to auto-save (seconds).",
            self.autosave_interval_spin))

        layout.addWidget(as_card)

        # ── Output card ──────────────────────────────────────────────────
        out_card = QGroupBox("Output")
        out_card.setObjectName("settings-card")
        out_vbox = QVBoxLayout(out_card)
        out_vbox.setSpacing(4)
        out_vbox.setContentsMargins(0, 8, 0, 8)

        self.save_format_combo = QComboBox()
        self.save_format_combo.addItems(["PNG", "WEBP", "JPG"])
        self.save_format_combo.setFixedWidth(110)
        current_fmt = SETTINGS.get('general', {}).get('save_format', 'PNG').upper()
        if current_fmt not in ["PNG", "WEBP", "JPG"]: current_fmt = "PNG"
        self.save_format_combo.setCurrentText(current_fmt)
        out_vbox.addWidget(self._make_option_row(
            "Image Format", "File format for exported/saved pages.",
            self.save_format_combo))

        self.save_quality_spin = QSpinBox()
        self.save_quality_spin.setRange(10, 100)
        self.save_quality_spin.setSuffix("%")
        self.save_quality_spin.setFixedWidth(90)
        self.save_quality_spin.setValue(int(SETTINGS.get('general', {}).get('save_quality', 95)))
        out_vbox.addWidget(self._make_option_row(
            "Quality", "Compression quality for WEBP/JPG exports.",
            self.save_quality_spin))

        layout.addWidget(out_card)

        # ── Defaults & Preset card ──────────────────────────────────────────
        def_card = QGroupBox("Default Presets")
        def_card.setObjectName("settings-card")
        def_vbox = QVBoxLayout(def_card)
        def_vbox.setSpacing(4)
        def_vbox.setContentsMargins(0, 8, 0, 8)

        # Default AI Model
        self.default_ai_model_combo = QComboBox()
        self.default_ai_model_combo.setFixedWidth(180)
        if hasattr(self.main_window, 'ai_model_combo'):
            for i in range(self.main_window.ai_model_combo.count()):
                self.default_ai_model_combo.addItem(self.main_window.ai_model_combo.itemText(i))
        current_ai_model = SETTINGS.get('general', {}).get('default_ai_model', '')
        self.default_ai_model_combo.setCurrentText(current_ai_model)
        def_vbox.addWidget(self._make_option_row(
            "Default AI Model", "Default model used in AI Hardware config.",
            self.default_ai_model_combo))

        # Default Translation Style
        self.default_style_combo = QComboBox()
        self.default_style_combo.setFixedWidth(180)
        if hasattr(self.main_window, 'translation_styles'):
            self.default_style_combo.addItems(self.main_window.translation_styles)
        current_style = SETTINGS.get('general', {}).get('default_translation_style', 'Santai (Default)')
        self.default_style_combo.setCurrentText(current_style)
        def_vbox.addWidget(self._make_option_row(
            "Default Translation Style", "Default style used for AI-based translations.",
            self.default_style_combo))

        # Default Font Family
        self.default_font_combo = QComboBox()
        self.default_font_combo.setFixedWidth(180)
        if hasattr(self.main_window, 'font_dropdown'):
            for i in range(self.main_window.font_dropdown.count()):
                self.default_font_combo.addItem(self.main_window.font_dropdown.itemText(i))
        current_font = SETTINGS.get('general', {}).get('default_font_family', '')
        self.default_font_combo.setCurrentText(current_font)
        def_vbox.addWidget(self._make_option_row(
            "Default Typeset Font", "Standard font family for manual typeset additions.",
            self.default_font_combo))

        # Default Font Size
        self.default_font_size_spin = QSpinBox()
        self.default_font_size_spin.setRange(4, 200)
        self.default_font_size_spin.setSuffix(" pt")
        self.default_font_size_spin.setFixedWidth(90)
        current_size = int(SETTINGS.get('general', {}).get('default_font_size', 14))
        self.default_font_size_spin.setValue(current_size)
        def_vbox.addWidget(self._make_option_row(
            "Default Font Size", "Standard font size for newly created layers.",
            self.default_font_size_spin))

        # Default Bold State
        self.default_font_bold_checkbox = QCheckBox()
        current_bold = bool(SETTINGS.get('general', {}).get('default_font_bold', False))
        self.default_font_bold_checkbox.setChecked(current_bold)
        def_vbox.addWidget(self._make_option_row(
            "Default Bold", "Newly created text layers start with bold font enabled.",
            self.default_font_bold_checkbox))

        # Default Text Outline State
        self.default_outline_checkbox = QCheckBox()
        current_outline = bool(SETTINGS.get('typeset', {}).get('outline_enabled', True))
        self.default_outline_checkbox.setChecked(current_outline)
        def_vbox.addWidget(self._make_option_row(
            "Default Text Outline", "Newly created text layers start with outline enabled.",
            self.default_outline_checkbox))

        # Default Outline Color
        self.default_outline_color_button = QPushButton("Pick Color")
        self.default_outline_color_button.setFixedWidth(110)
        self.default_outline_color = QColor(SETTINGS.get('typeset', {}).get('outline_color', '#ff00ff'))
        if not self.default_outline_color.isValid():
            self.default_outline_color = QColor('#ff00ff')
        
        def _update_default_outline_color_button_ui():
            color = self.default_outline_color
            luminance = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
            text_color = '#000000' if luminance > 160 else '#f3f6fb'
            self.default_outline_color_button.setStyleSheet(
                f"QPushButton {{ background-color: {color.name()}; color: {text_color}; border: 1px solid #1f2b36; border-radius: 8px; padding: 6px 10px; }}"
                " QPushButton:hover { border-color: #3a9bff; }"
            )
            
        def _choose_default_outline_color():
            color = QColorDialog.getColor(self.default_outline_color, self, "Select Default Outline Color")
            if color.isValid():
                self.default_outline_color = color
                _update_default_outline_color_button_ui()
                
        self.default_outline_color_button.clicked.connect(_choose_default_outline_color)
        _update_default_outline_color_button_ui()
        def_vbox.addWidget(self._make_option_row(
            "Default Outline Color", "Standard color for text outlines.",
            self.default_outline_color_button))

        layout.addWidget(def_card)

        # ── Emergency Close card ──────────────────────────────────────────
        ec_card = QGroupBox("Emergency Close")
        ec_card.setObjectName("settings-card")
        ec_vbox = QVBoxLayout(ec_card)
        ec_vbox.setSpacing(4)
        ec_vbox.setContentsMargins(0, 8, 0, 8)

        self.ec_action_combo = QComboBox()
        self.ec_action_combo.addItems(["Open URL", "Launch Application", "Focus Existing Window"])
        self.ec_action_combo.setFixedWidth(180)
        
        ec_cfg = SETTINGS.get('emergency_close', {})
        current_type = ec_cfg.get('action_type', 'url')
        type_map = {'url': "Open URL", 'app': "Launch Application", 'focus': "Focus Existing Window"}
        self.ec_action_combo.setCurrentText(type_map.get(current_type, "Open URL"))

        self.ec_target_edit = QLineEdit()
        self.ec_target_edit.setPlaceholderText("e.g., https://youtube.com or notepad.exe")
        self.ec_target_edit.setText(ec_cfg.get('target', 'https://youtube.com'))

        # Browse button for application path
        self.ec_browse_btn = QPushButton("Browse...")
        self.ec_browse_btn.setFixedWidth(80)
        
        def _on_browse_app():
            from PyQt5.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Application", "", 
                "Executable Files (*.exe);;All Files (*)"
            )
            if file_path:
                self.ec_target_edit.setText(os.path.abspath(file_path))

        self.ec_browse_btn.clicked.connect(_on_browse_app)

        # Container for edit and browse button
        target_widget = QWidget()
        target_layout = QHBoxLayout(target_widget)
        target_layout.setContentsMargins(0, 0, 0, 0)
        target_layout.setSpacing(6)
        target_layout.addWidget(self.ec_target_edit, 1)
        target_layout.addWidget(self.ec_browse_btn)

        # Connect combobox index change to adjust placeholder text and browse visibility
        def _on_ec_type_changed(text):
            if text == "Open URL":
                self.ec_target_edit.setPlaceholderText("e.g., https://youtube.com")
                self.ec_browse_btn.setVisible(False)
            elif text == "Launch Application":
                self.ec_target_edit.setPlaceholderText("e.g., C:\\Windows\\notepad.exe")
                self.ec_browse_btn.setVisible(True)
            else:
                self.ec_target_edit.setPlaceholderText("e.g., Brave, Discord, Chrome, Spotify")
                self.ec_browse_btn.setVisible(False)

        self.ec_action_combo.currentTextChanged.connect(_on_ec_type_changed)
        _on_ec_type_changed(self.ec_action_combo.currentText())

        ec_vbox.addWidget(self._make_option_row(
            "Action Type", "Choose what to do when emergency close is triggered.",
            self.ec_action_combo))

        ec_vbox.addWidget(self._make_option_row(
            "Target Destination", "Specify the URL, app path, or window title.",
            target_widget))

        layout.addWidget(ec_card)
        layout.addStretch(1)

        self.autosave_checkbox.setChecked(self._initial_autosave_enabled)
        self.autosave_interval_spin.setValue(max(5, int(self._initial_autosave_interval / 1000)))

        return page

    def _create_cleanup_tab(self):
        meta = self._page_meta("cleanup")
        page, layout = self._make_page_scroll()
        layout.addWidget(self._make_page_header(
            meta.get("title", "Cleanup & Inpainting"),
            meta.get("subtitle", ""),
        ))

        cleanup_cfg = SETTINGS.get('cleanup', {}) if isinstance(SETTINGS.get('cleanup'), dict) else {}
        unified_eid = resolve_inpaint_engine_id(cleanup_cfg)

        # ── Card 1: Integrated Inpainting Engine ──────────────────────────────
        inpaint_card = QGroupBox(InpaintText.CARD_ENGINES_TITLE)
        inpaint_card.setObjectName("settings-card")
        inpaint_vbox = QVBoxLayout(inpaint_card)
        inpaint_vbox.setSpacing(6)
        inpaint_vbox.setContentsMargins(0, 8, 0, 8)

        self.cleanup_use_inpaint_checkbox = QCheckBox()
        self.cleanup_use_inpaint_checkbox.setChecked(bool(cleanup_cfg.get('use_inpaint', True)))
        inpaint_vbox.addWidget(self._make_option_row(
            "Enable inpainting by default",
            "Hapus teks asli secara otomatis di balik balon atau kotak terjemahan.",
            self.cleanup_use_inpaint_checkbox))

        def _prep_combo(cb, width=210):
            cb.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            cb.setMinimumContentsLength(12)
            cb.setFixedWidth(width)

        self.cleanup_inpaint_engine_combo = QComboBox()
        _prep_combo(self.cleanup_inpaint_engine_combo, 210)
        for spec in list_inpaint_engines("full"):
            self.cleanup_inpaint_engine_combo.addItem(spec.short_label, spec.id)
        e_idx = self.cleanup_inpaint_engine_combo.findData(unified_eid)
        if e_idx != -1:
            self.cleanup_inpaint_engine_combo.setCurrentIndex(e_idx)
        inpaint_vbox.addWidget(self._make_option_row(
            InpaintText.LABEL_UNIFIED_ENGINE,
            "Dipakai bersama untuk Full-Page Auto Translate dan Inpainting Brush (default: Big-LaMa bawaan).",
            self.cleanup_inpaint_engine_combo))

        self.cleanup_inpaint_device_combo = QComboBox()
        _prep_combo(self.cleanup_inpaint_device_combo, 210)
        self.cleanup_inpaint_device_combo.addItem("Otomatis (CUDA jika ada)", "auto")
        self.cleanup_inpaint_device_combo.addItem("GPU NVIDIA CUDA", "cuda")
        self.cleanup_inpaint_device_combo.addItem("CPU Saja", "cpu")
        saved_dev = str(cleanup_cfg.get('inpaint_device', 'auto') or 'auto').lower()
        dev_idx = self.cleanup_inpaint_device_combo.findData(saved_dev)
        self.cleanup_inpaint_device_combo.setCurrentIndex(dev_idx if dev_idx != -1 else 0)
        inpaint_vbox.addWidget(self._make_option_row(
            InpaintText.LABEL_DEVICE,
            "Big-LaMa, Manga Inpaintor, dan MI-GAN berjalan cepat di CPU maupun GPU CUDA.",
            self.cleanup_inpaint_device_combo))

        hw_text = InpaintText.HARDWARE_CPU_ONLY
        hw_color = theme.COLORS['muted']
        try:
            import torch
            if torch.cuda.is_available():
                hw_text = InpaintText.HARDWARE_CUDA_FMT.format(name=torch.cuda.get_device_name(0))
                hw_color = theme.COLORS['success']
        except Exception:
            pass
        self.cleanup_hw_info_label = QLabel(hw_text)
        self.cleanup_hw_info_label.setWordWrap(True)
        self.cleanup_hw_info_label.setStyleSheet(
            f"color: {hw_color}; font-size: 8.5pt; padding: 4px 12px 6px 12px;"
        )
        inpaint_vbox.addWidget(self.cleanup_hw_info_label)

        self.cleanup_inpaint_padding_spin = QSpinBox()
        self.cleanup_inpaint_padding_spin.setRange(1, 25)
        self.cleanup_inpaint_padding_spin.setFixedWidth(90)
        self.cleanup_inpaint_padding_spin.setSuffix(" px")
        self.cleanup_inpaint_padding_spin.setValue(int(cleanup_cfg.get('inpaint_padding', 5) or 5))
        inpaint_vbox.addWidget(self._make_option_row(
            "Mask padding",
            "Ekstra piksel di sekeliling mask teks sebelum inpainting.",
            self.cleanup_inpaint_padding_spin))

        unload_btn = QPushButton(InpaintText.BTN_UNLOAD)
        unload_btn.setObjectName("settings-action-btn")
        unload_btn.clicked.connect(self._on_unload_inpaint_memory)
        inpaint_vbox.addWidget(self._make_option_row(
            "Manajemen RAM / VRAM",
            "Kosongkan model AI yang tersimpan di cache memori saat ini.",
            unload_btn))

        layout.addWidget(inpaint_card)

        # ── Card 2: Model Status & One-Click Downloads ────────────────────────
        models_card = QGroupBox(InpaintText.CARD_MODELS_TITLE)
        models_card.setObjectName("settings-card")
        models_vbox = QVBoxLayout(models_card)
        models_vbox.setSpacing(6)
        models_vbox.setContentsMargins(0, 8, 0, 8)

        models_desc = QLabel(InpaintText.CARD_MODELS_DESC)
        models_desc.setWordWrap(True)
        models_desc.setStyleSheet(f"color: {theme.COLORS['muted']}; font-size: 8.5pt; padding: 2px 12px 4px 12px;")
        models_vbox.addWidget(models_desc)

        self._inpaint_model_status_labels = {}
        self._inpaint_model_dl_buttons = {}
        self._inpaint_dl_worker = None

        for eid in ("big_lama", "manga_inpaintor", "migan"):
            spec = get_inpaint_spec(eid)
            ctrl_w = QWidget()
            ctrl_h = QHBoxLayout(ctrl_w)
            ctrl_h.setContentsMargins(0, 0, 0, 0)
            ctrl_h.setSpacing(8)
            status_lbl = QLabel("")
            status_lbl.setStyleSheet(f"color: {theme.COLORS['muted']}; font-size: 8.5pt;")
            dl_btn = QPushButton(InpaintText.BTN_DOWNLOAD)
            dl_btn.setObjectName("settings-action-btn")
            dl_btn.setIcon(app_icon("download", theme.COLORS["accent"], 13))
            dl_btn.setIconSize(QSize(13, 13))
            dl_btn.clicked.connect(lambda _checked=False, target_id=eid: self._on_download_inpaint_model(target_id))
            ctrl_h.addWidget(status_lbl)
            ctrl_h.addWidget(dl_btn)
            self._inpaint_model_status_labels[eid] = status_lbl
            self._inpaint_model_dl_buttons[eid] = dl_btn
            models_vbox.addWidget(self._make_option_row(
                f"{spec.short_label} ({spec.size_hint})",
                spec.description,
                ctrl_w))

        self.inpaint_dl_progress = QProgressBar()
        self.inpaint_dl_progress.setRange(0, 100)
        self.inpaint_dl_progress.setVisible(False)
        self.inpaint_dl_progress.setFixedHeight(8)
        self.inpaint_dl_status_label = QLabel("")
        self.inpaint_dl_status_label.setWordWrap(True)
        self.inpaint_dl_status_label.setVisible(False)
        self.inpaint_dl_status_label.setStyleSheet(
            f"color: {theme.COLORS['accent_hover']}; font-size: 8.5pt; padding: 2px 12px 4px 12px;"
        )
        models_vbox.addWidget(self.inpaint_dl_progress)
        models_vbox.addWidget(self.inpaint_dl_status_label)
        self._refresh_inpaint_model_statuses()

        layout.addWidget(models_card)

        # ── Card 3: External IOPaint Server (Optional) ────────────────────────
        ext_card = QGroupBox(InpaintText.CARD_EXTERNAL_TITLE)
        ext_card.setObjectName("settings-card")
        ext_vbox = QVBoxLayout(ext_card)
        ext_vbox.setSpacing(4)
        ext_vbox.setContentsMargins(0, 8, 0, 8)

        ext_desc = QLabel(InpaintText.CARD_EXTERNAL_DESC)
        ext_desc.setWordWrap(True)
        ext_desc.setStyleSheet(f"color: {theme.COLORS['muted']}; font-size: 8.5pt; padding: 2px 12px 4px 12px;")
        ext_vbox.addWidget(ext_desc)

        self.cleanup_iopaint_url_edit = QLineEdit()
        self.cleanup_iopaint_url_edit.setFixedWidth(240)
        self.cleanup_iopaint_url_edit.setPlaceholderText(DEFAULT_INPAINT_SERVER_URL)
        self.cleanup_iopaint_url_edit.setText(str(cleanup_cfg.get('inpaint_server_url', DEFAULT_INPAINT_SERVER_URL) or DEFAULT_INPAINT_SERVER_URL))
        ext_vbox.addWidget(self._make_option_row(
            "IOPaint server URL",
            "URL server IOPaint eksternal (default http://127.0.0.1:8080).",
            self.cleanup_iopaint_url_edit))

        self.cleanup_iopaint_timeout_spin = QSpinBox()
        self.cleanup_iopaint_timeout_spin.setRange(5, 600)
        self.cleanup_iopaint_timeout_spin.setFixedWidth(90)
        self.cleanup_iopaint_timeout_spin.setSuffix(" s")
        self.cleanup_iopaint_timeout_spin.setValue(int(cleanup_cfg.get('inpaint_server_timeout', DEFAULT_INPAINT_SERVER_TIMEOUT) or DEFAULT_INPAINT_SERVER_TIMEOUT))
        ext_vbox.addWidget(self._make_option_row(
            "Request timeout",
            "Batas waktu tunggu HTTP per request ke server IOPaint.",
            self.cleanup_iopaint_timeout_spin))

        test_holder = QWidget()
        test_h = QHBoxLayout(test_holder)
        test_h.setContentsMargins(0, 0, 0, 0)
        test_h.setSpacing(8)
        self.iopaint_status_label = QLabel("Not checked")
        self.iopaint_status_label.setStyleSheet(f"color: {theme.COLORS['muted']}; font-size: 8.5pt;")
        self.iopaint_test_btn = QPushButton("Test Connection")
        self.iopaint_test_btn.setObjectName("settings-action-btn")
        self.iopaint_test_btn.clicked.connect(self._on_test_iopaint_server)
        test_h.addWidget(self.iopaint_status_label)
        test_h.addWidget(self.iopaint_test_btn)
        ext_vbox.addWidget(self._make_option_row(
            "Server connectivity",
            "Periksa apakah server IOPaint eksternal sedang berjalan.",
            test_holder))

        layout.addWidget(ext_card)

        # ── Card 2: Text Defaults ───────────────────────────────────────────
        card = QGroupBox("Text Box && Color Defaults")
        card.setObjectName("settings-card")
        card_vbox = QVBoxLayout(card)
        card_vbox.setSpacing(4)
        card_vbox.setContentsMargins(0, 8, 0, 8)

        self.auto_text_color_checkbox = QCheckBox()
        self.auto_text_color_checkbox.setChecked(bool(cleanup_cfg.get('auto_text_color', True)))
        card_vbox.addWidget(self._make_option_row(
            "Auto text color",
            "Automatically pick a contrasting text color for each bubble.",
            self.auto_text_color_checkbox))

        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(0, 255)
        self.threshold_spin.setFixedWidth(90)
        self.threshold_spin.setToolTip("Higher values prefer brighter text.")
        self.threshold_spin.setValue(int(cleanup_cfg.get('text_color_threshold', 128)))
        card_vbox.addWidget(self._make_option_row(
            "Color threshold",
            "Luminance threshold for auto text color inversion (0–255).",
            self.threshold_spin))

        self.use_background_box_checkbox = QCheckBox()
        self.use_background_box_checkbox.setChecked(bool(cleanup_cfg.get('use_background_box', True)))
        card_vbox.addWidget(self._make_option_row(
            "Background box",
            "Draw a filled background box behind new translated text by default.",
            self.use_background_box_checkbox))

        self.constrain_text_checkbox = QCheckBox()
        self.constrain_text_checkbox.setToolTip("Text will wrap to box width even when the background is hidden.")
        self.constrain_text_checkbox.setChecked(bool(cleanup_cfg.get('constrain_text', True)))
        card_vbox.addWidget(self._make_option_row(
            "Constrain text",
            "Wrap text to box width even when the background box is off.",
            self.constrain_text_checkbox))

        self.remove_ai_temp_checkbox = QCheckBox()
        self.remove_ai_temp_checkbox.setToolTip("Delete temporary AI OCR/MOFRL debug files automatically after each run.")
        self.remove_ai_temp_checkbox.setChecked(bool(cleanup_cfg.get('remove_ai_temp_files', True)))
        card_vbox.addWidget(self._make_option_row(
            "Remove AI temp files",
            "Delete temporary debug files after AI OCR & MOFRL runs.",
            self.remove_ai_temp_checkbox))

        layout.addWidget(card)
        layout.addStretch(1)
        return page

    def _refresh_cleanup_engine_combo_items(self):
        combo = getattr(self, 'cleanup_inpaint_engine_combo', None)
        if combo is None:
            return
        current_eid = combo.currentData()
        with QSignalBlocker(combo):
            combo.clear()
            for spec in list_inpaint_engines("full"):
                text, badge, ready = format_inpaint_engine_option(spec)
                dot_color = (
                    theme.COLORS['muted']
                    if spec.id == "iopaint_server"
                    else (theme.COLORS['success'] if ready else theme.COLORS['warning'])
                )
                combo.addItem(status_dot_icon(dot_color, 8), text, spec.id)
                idx = combo.count() - 1
                combo.setItemData(
                    idx,
                    f"{spec.label}\nStatus: {badge}\n{spec.description}",
                    Qt.ToolTipRole,
                )
            if current_eid:
                idx = combo.findData(current_eid)
                if idx != -1:
                    combo.setCurrentIndex(idx)

    def _refresh_inpaint_model_statuses(self):
        labels = getattr(self, '_inpaint_model_status_labels', None) or {}
        buttons = getattr(self, '_inpaint_model_dl_buttons', None) or {}
        worker_active = getattr(self, '_inpaint_dl_worker', None) is not None
        for eid, lbl in labels.items():
            ready = is_engine_ready(eid)
            try:
                if ready:
                    lbl.setText(InpaintText.STATUS_READY)
                    lbl.setStyleSheet(f"color: {theme.COLORS['success']}; font-size: 8.5pt; font-weight: 700;")
                else:
                    lbl.setText(InpaintText.STATUS_MISSING)
                    lbl.setStyleSheet(f"color: {theme.COLORS['warning']}; font-size: 8.5pt; font-weight: 700;")
                btn = buttons.get(eid)
                if btn is not None:
                    btn.setEnabled((not ready) and (not worker_active))
                    btn.setText(InpaintText.STATUS_READY if ready else InpaintText.BTN_DOWNLOAD)
            except RuntimeError:
                pass
        self._refresh_cleanup_engine_combo_items()

    def _on_unload_inpaint_memory(self):
        try:
            get_inpaint_manager().unload_loaded_model()
            notify_toast(self, "Memori Dibersihkan", InpaintText.UNLOAD_DONE, kind="info")
        except Exception as exc:
            notify_toast(self, "Inpaint", str(exc), kind="warning")

    def _on_download_inpaint_model(self, engine_id: str):
        if getattr(self, '_inpaint_dl_worker', None) is not None:
            return
        for btn in (getattr(self, '_inpaint_model_dl_buttons', None) or {}).values():
            try:
                btn.setEnabled(False)
            except RuntimeError:
                pass
        try:
            self.inpaint_dl_progress.setValue(0)
            self.inpaint_dl_progress.setVisible(True)
            self.inpaint_dl_status_label.setText(
                InpaintText.DOWNLOAD_STARTED_FMT.format(name=engine_display_label(engine_id, short=True))
            )
            self.inpaint_dl_status_label.setVisible(True)
        except RuntimeError:
            pass

        worker = InpaintModelDownloadWorker(engine_id)
        worker.progress.connect(self._on_inpaint_dl_progress)
        worker.finished_ok.connect(self._on_inpaint_dl_finished)
        worker.finished.connect(self._on_inpaint_dl_thread_done)
        self._inpaint_dl_worker = worker
        worker.start()

    def _on_inpaint_dl_progress(self, pct: int, msg: str):
        try:
            if getattr(self, 'inpaint_dl_progress', None) is not None:
                self.inpaint_dl_progress.setValue(max(0, min(100, int(pct))))
            if getattr(self, 'inpaint_dl_status_label', None) is not None:
                self.inpaint_dl_status_label.setText(msg)
        except RuntimeError:
            pass

    def _on_inpaint_dl_finished(self, engine_id: str, success: bool, detail: str):
        try:
            if getattr(self, 'inpaint_dl_progress', None) is not None:
                self.inpaint_dl_progress.setValue(100 if success else 0)
            if getattr(self, 'inpaint_dl_status_label', None) is not None:
                color = theme.COLORS['success'] if success else theme.COLORS['danger']
                self.inpaint_dl_status_label.setStyleSheet(
                    f"color: {color}; font-size: 8.5pt; padding: 2px 12px 4px 12px;"
                )
                self.inpaint_dl_status_label.setText(detail)
            notify_toast(
                self,
                "Model Inpaint" if success else "Unduhan Gagal",
                detail,
                kind="success" if success else "warning",
            )
        except RuntimeError:
            pass

    def _on_inpaint_dl_thread_done(self):
        self._inpaint_dl_worker = None
        self._refresh_inpaint_model_statuses()
        if getattr(self, 'main_window', None) is not None and hasattr(self.main_window, '_refresh_inpaint_summary_badges'):
            try:
                self.main_window._refresh_inpaint_summary_badges()
            except Exception:
                pass

    def _on_test_iopaint_server(self):
        import threading
        import urllib.request
        url = (self.cleanup_iopaint_url_edit.text() or DEFAULT_INPAINT_SERVER_URL).strip().rstrip("/")
        if not url:
            url = DEFAULT_INPAINT_SERVER_URL
        self.iopaint_test_btn.setEnabled(False)
        self.iopaint_status_label.setText("Checking…")
        self.iopaint_status_label.setStyleSheet(f"color: {theme.COLORS['muted']}; font-size: 8.5pt;")

        def _finish(ok: bool, detail: str):
            try:
                if getattr(self, 'iopaint_test_btn', None) is not None:
                    self.iopaint_test_btn.setEnabled(True)
                lbl = getattr(self, 'iopaint_status_label', None)
                if lbl is not None:
                    color = theme.COLORS['success'] if ok else theme.COLORS['danger']
                    lbl.setText(detail)
                    lbl.setStyleSheet(f"color: {color}; font-size: 8.5pt; font-weight: 700;")
            except RuntimeError:
                pass

        def _probe():
            ok = False
            detail = "Offline"
            for suffix in ("/api/v1/model", "/"):
                try:
                    req = urllib.request.Request(f"{url}{suffix}", method="GET")
                    with urllib.request.urlopen(req, timeout=3) as resp:
                        if 200 <= getattr(resp, "status", 200) < 400:
                            ok = True
                            detail = f"Connected (HTTP {getattr(resp, 'status', 200)})"
                            break
                except Exception as exc:
                    detail = f"Offline: {str(exc)[:42]}"
            QTimer.singleShot(0, self, lambda o=ok, d=detail: _finish(o, d))

        threading.Thread(target=_probe, daemon=True).start()

    def _theme_swatch_icon(self, colors: dict):
        pixmap = QPixmap(30, 22)
        pixmap.fill(QColor(colors.get("bg", "#090a0f")))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(QPen(QColor(colors.get("border", "#1e293b")), 1))
        painter.setBrush(QColor(colors.get("panel", "#0e111a")))
        painter.drawRoundedRect(1, 1, 28, 20, 5, 5)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(colors.get("accent", "#38bdf8")))
        painter.drawRoundedRect(5, 5, 8, 12, 3, 3)
        painter.setBrush(QColor(colors.get("text", "#cbd5e1")))
        painter.drawRoundedRect(16, 6, 8, 2, 1, 1)
        painter.setBrush(QColor(colors.get("muted", "#64748b")))
        painter.drawRoundedRect(16, 11, 6, 2, 1, 1)
        painter.end()
        return QIcon(pixmap)

    def _combo_set_data(self, combo, value):
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _color_button_qss(self, color_name: str):
        color = QColor(color_name)
        if not color.isValid():
            color = QColor("#38bdf8")
        luminance = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
        text_color = "#020617" if luminance > 150 else "#f8fafc"
        return (
            f"QPushButton {{ background: {color.name()}; color: {text_color}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 6px 10px; }}"
            f"\nQPushButton:hover {{ border-color: {COLORS['accent']}; }}"
        )

    def _appearance_preview_settings(self):
        cfg = normalize_appearance_settings(SETTINGS.get('appearance', {}))
        if hasattr(self, 'appearance_mode_combo'):
            cfg['mode'] = self.appearance_mode_combo.currentData() or cfg['mode']
        if hasattr(self, 'dark_theme_combo'):
            cfg['dark_theme'] = self.dark_theme_combo.currentData() or cfg['dark_theme']
        for key, edit in getattr(self, 'appearance_color_edits', {}).items():
            cfg[key] = edit.text().strip()
        if hasattr(self, 'contrast_slider'):
            cfg['contrast'] = int(self.contrast_slider.value())
        return normalize_appearance_settings(cfg)

    def _refresh_appearance_color_editors(self):
        resolved = resolve_appearance(self._appearance_preview_settings(), system_dark=True)
        colors = resolved.get("colors", {})
        key_map = {
            "accent": colors.get("accent", "#38bdf8"),
            "background": colors.get("bg", "#090a0f"),
            "foreground": colors.get("text", "#cbd5e1"),
        }
        for key, edit in self.appearance_color_edits.items():
            fallback = key_map.get(key, APPEARANCE_DEFAULTS.get(key, ""))
            edit.setPlaceholderText(fallback.upper())
            btn = self.appearance_color_buttons.get(key)
            if btn is not None:
                btn.setStyleSheet(self._color_button_qss(edit.text().strip() or fallback))

    def _make_color_editor(self, key: str, value: str):
        holder = QWidget()
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        edit = QLineEdit()
        edit.setFixedWidth(120)
        edit.setPlaceholderText("#38BDF8")
        edit.setText(value or "")
        edit.setMaxLength(7)

        pick_btn = QPushButton(AppearanceText.PICK_COLOR)
        pick_btn.setFixedWidth(64)

        reset_btn = QToolButton()
        reset_btn.setText(AppearanceText.RESET_COLOR)
        reset_btn.setToolTip("Use the selected theme preset color")

        def _pick_color():
            fallback = edit.text().strip() or edit.placeholderText() or "#38bdf8"
            color = QColor(fallback)
            if not color.isValid():
                color = QColor("#38bdf8")
            chosen = QColorDialog.getColor(color, self, f"Select {key.title()} Color")
            if chosen.isValid():
                edit.setText(chosen.name().upper())

        pick_btn.clicked.connect(_pick_color)
        reset_btn.clicked.connect(lambda: edit.setText(""))
        edit.textChanged.connect(lambda _text: self._refresh_appearance_color_editors())

        row.addWidget(edit)
        row.addWidget(pick_btn)
        row.addWidget(reset_btn)
        self.appearance_color_edits[key] = edit
        self.appearance_color_buttons[key] = pick_btn
        return holder

    def _create_appearance_tab(self):
        meta = self._page_meta("appearance")
        page, layout = self._make_page_scroll()
        layout.addWidget(self._make_page_header(
            meta.get("title", "Appearance"),
            meta.get("subtitle", ""),
        ))

        cfg = normalize_appearance_settings(SETTINGS.get('appearance', {}))

        theme_card = QGroupBox(AppearanceText.CARD_THEME)
        theme_card.setObjectName("settings-card")
        theme_vbox = QVBoxLayout(theme_card)
        theme_vbox.setSpacing(4)
        theme_vbox.setContentsMargins(0, 8, 0, 8)

        self.appearance_mode_combo = QComboBox()
        self.appearance_mode_combo.setFixedWidth(180)
        for value, label in AppearanceText.MODES:
            self.appearance_mode_combo.addItem(label, value)
        self._combo_set_data(self.appearance_mode_combo, cfg["mode"])
        theme_vbox.addWidget(self._make_option_row(
            AppearanceText.MODE_LABEL,
            AppearanceText.MODE_DESC,
            self.appearance_mode_combo,
        ))

        self.dark_theme_combo = QComboBox()
        self.dark_theme_combo.setFixedWidth(220)
        for key, label in DARK_THEME_CHOICES:
            self.dark_theme_combo.addItem(self._theme_swatch_icon(DARK_THEME_PRESETS[key]), label, key)
        self._combo_set_data(self.dark_theme_combo, cfg["dark_theme"])
        theme_vbox.addWidget(self._make_option_row(
            AppearanceText.DARK_THEME_LABEL,
            AppearanceText.DARK_THEME_DESC,
            self.dark_theme_combo,
        ))

        layout.addWidget(theme_card)

        color_card = QGroupBox(AppearanceText.CARD_COLORS)
        color_card.setObjectName("settings-card")
        color_vbox = QVBoxLayout(color_card)
        color_vbox.setSpacing(4)
        color_vbox.setContentsMargins(0, 8, 0, 8)
        color_vbox.addWidget(self._make_option_row(
            AppearanceText.ACCENT_LABEL,
            AppearanceText.ACCENT_DESC,
            self._make_color_editor("accent", cfg.get("accent", "")),
        ))
        color_vbox.addWidget(self._make_option_row(
            AppearanceText.BACKGROUND_LABEL,
            AppearanceText.BACKGROUND_DESC,
            self._make_color_editor("background", cfg.get("background", "")),
        ))
        color_vbox.addWidget(self._make_option_row(
            AppearanceText.FOREGROUND_LABEL,
            AppearanceText.FOREGROUND_DESC,
            self._make_color_editor("foreground", cfg.get("foreground", "")),
        ))
        layout.addWidget(color_card)

        interface_card = QGroupBox(AppearanceText.CARD_INTERFACE)
        interface_card.setObjectName("settings-card")
        interface_vbox = QVBoxLayout(interface_card)
        interface_vbox.setSpacing(4)
        interface_vbox.setContentsMargins(0, 8, 0, 8)

        self.ui_font_edit = QLineEdit()
        self.ui_font_edit.setMinimumWidth(320)
        self.ui_font_edit.setText(cfg["ui_font"])
        interface_vbox.addWidget(self._make_option_row(
            AppearanceText.UI_FONT_LABEL,
            AppearanceText.UI_FONT_DESC,
            self.ui_font_edit,
        ))

        self.code_font_edit = QLineEdit()
        self.code_font_edit.setMinimumWidth(320)
        self.code_font_edit.setText(cfg["code_font"])
        interface_vbox.addWidget(self._make_option_row(
            AppearanceText.CODE_FONT_LABEL,
            AppearanceText.CODE_FONT_DESC,
            self.code_font_edit,
        ))

        self.translucent_sidebar_checkbox = QCheckBox()
        self.translucent_sidebar_checkbox.setChecked(bool(cfg["translucent_sidebar"]))
        interface_vbox.addWidget(self._make_option_row(
            AppearanceText.TRANSLUCENT_SIDEBAR_LABEL,
            AppearanceText.TRANSLUCENT_SIDEBAR_DESC,
            self.translucent_sidebar_checkbox,
        ))

        contrast_holder = QWidget()
        contrast_layout = QHBoxLayout(contrast_holder)
        contrast_layout.setContentsMargins(0, 0, 0, 0)
        contrast_layout.setSpacing(8)
        self.contrast_slider = QSlider(Qt.Horizontal)
        self.contrast_slider.setRange(30, 100)
        self.contrast_slider.setValue(int(cfg["contrast"]))
        self.contrast_slider.setFixedWidth(180)
        self.contrast_value_label = QLabel(str(cfg["contrast"]))
        self.contrast_value_label.setFixedWidth(34)
        self.contrast_slider.valueChanged.connect(lambda value: self.contrast_value_label.setText(str(value)))
        self.contrast_slider.valueChanged.connect(lambda _value: self._refresh_appearance_color_editors())
        contrast_layout.addWidget(self.contrast_slider)
        contrast_layout.addWidget(self.contrast_value_label)
        interface_vbox.addWidget(self._make_option_row(
            AppearanceText.CONTRAST_LABEL,
            AppearanceText.CONTRAST_DESC,
            contrast_holder,
        ))

        self.pointer_cursor_checkbox = QCheckBox()
        self.pointer_cursor_checkbox.setChecked(bool(cfg["use_pointer_cursors"]))
        interface_vbox.addWidget(self._make_option_row(
            AppearanceText.POINTER_LABEL,
            AppearanceText.POINTER_DESC,
            self.pointer_cursor_checkbox,
        ))

        self.reduce_motion_combo = QComboBox()
        self.reduce_motion_combo.setFixedWidth(180)
        for value, label in AppearanceText.MOTION_OPTIONS:
            self.reduce_motion_combo.addItem(label, value)
        self._combo_set_data(self.reduce_motion_combo, cfg["reduce_motion"])
        interface_vbox.addWidget(self._make_option_row(
            AppearanceText.REDUCE_MOTION_LABEL,
            AppearanceText.REDUCE_MOTION_DESC,
            self.reduce_motion_combo,
        ))

        self.ui_font_size_spin = QSpinBox()
        self.ui_font_size_spin.setRange(10, 20)
        self.ui_font_size_spin.setSuffix(" px")
        self.ui_font_size_spin.setFixedWidth(90)
        self.ui_font_size_spin.setValue(int(cfg["ui_font_size"]))
        interface_vbox.addWidget(self._make_option_row(
            AppearanceText.UI_FONT_SIZE_LABEL,
            AppearanceText.UI_FONT_SIZE_DESC,
            self.ui_font_size_spin,
        ))

        self.code_font_size_spin = QSpinBox()
        self.code_font_size_spin.setRange(10, 18)
        self.code_font_size_spin.setSuffix(" px")
        self.code_font_size_spin.setFixedWidth(90)
        self.code_font_size_spin.setValue(int(cfg["code_font_size"]))
        interface_vbox.addWidget(self._make_option_row(
            AppearanceText.CODE_FONT_SIZE_LABEL,
            AppearanceText.CODE_FONT_SIZE_DESC,
            self.code_font_size_spin,
        ))

        layout.addWidget(interface_card)
        layout.addStretch(1)

        self.dark_theme_combo.currentIndexChanged.connect(lambda _index: self._refresh_appearance_color_editors())
        self.appearance_mode_combo.currentIndexChanged.connect(lambda _index: self._refresh_appearance_color_editors())
        self._refresh_appearance_color_editors()
        return page

    def _collect_appearance_settings(self):
        cfg = normalize_appearance_settings(SETTINGS.get('appearance', {}))
        cfg['mode'] = self.appearance_mode_combo.currentData() or cfg['mode']
        cfg['dark_theme'] = self.dark_theme_combo.currentData() or cfg['dark_theme']
        for key, edit in self.appearance_color_edits.items():
            cfg[key] = edit.text().strip()
        cfg['ui_font'] = self.ui_font_edit.text().strip() or APPEARANCE_DEFAULTS['ui_font']
        cfg['code_font'] = self.code_font_edit.text().strip() or APPEARANCE_DEFAULTS['code_font']
        cfg['translucent_sidebar'] = bool(self.translucent_sidebar_checkbox.isChecked())
        cfg['contrast'] = int(self.contrast_slider.value())
        cfg['use_pointer_cursors'] = bool(self.pointer_cursor_checkbox.isChecked())
        cfg['reduce_motion'] = self.reduce_motion_combo.currentData() or cfg['reduce_motion']
        cfg['ui_font_size'] = int(self.ui_font_size_spin.value())
        cfg['code_font_size'] = int(self.code_font_size_spin.value())
        return normalize_appearance_settings(cfg)

    def _create_translation_tab(self):
        self.openrouter_panel = OpenRouterSettingsPanel(SETTINGS, self)
        return self._make_panel_page("translation", self.openrouter_panel)

    def _create_shortcuts_tab(self):
        meta = self._page_meta("shortcuts")
        page, container_layout = self._make_page_scroll()
        container_layout.addWidget(self._make_page_header(
            meta.get("title", "Shortcuts"),
            meta.get("subtitle", ""),
        ))

        category_order = []
        grouped = {}
        for key, label, category in SHORTCUT_DEFINITIONS:
            grouped.setdefault(category, []).append((key, label))
            if category not in category_order:
                category_order.append(category)

        user_shortcuts = SETTINGS.get('shortcuts', {}) or {}
        for category in category_order:
            entries = grouped.get(category, [])
            if not entries:
                continue
            group_box = QGroupBox(category)
            group_box.setObjectName("settings-card")
            form = QFormLayout(group_box)
            form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            form.setHorizontalSpacing(18)
            form.setVerticalSpacing(10)

            for key, label in entries:
                editor = ShortcutCaptureEdit()
                seq = user_shortcuts.get(key)
                if seq is None:
                    seq = DEFAULT_SHORTCUTS.get(key, '')
                if seq:
                    editor.set_sequence(seq)
                else:
                    editor.clear_sequence()

                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(6)
                row_layout.addWidget(editor, 1)

                clear_btn = QToolButton()
                clear_btn.setIcon(app_icon("x", size=12))
                clear_btn.setIconSize(QSize(12, 12))
                clear_btn.setToolTip("Clear shortcut")
                clear_btn.clicked.connect(editor.clear_sequence)
                row_layout.addWidget(clear_btn)

                default_btn = QToolButton()
                default_btn.setIcon(app_icon("refresh", size=12))
                default_btn.setIconSize(QSize(12, 12))
                default_btn.setToolTip("Restore default")

                def _reset_editor(checked=False, target_editor=editor, target_key=key):
                    default_seq = DEFAULT_SHORTCUTS.get(target_key, '')
                    target_editor.set_sequence(default_seq)

                default_btn.clicked.connect(_reset_editor)
                row_layout.addWidget(default_btn)

                form.addRow(label, row_widget)
                self.shortcut_editors[key] = editor

            container_layout.addWidget(group_box)

        container_layout.addStretch(1)
        return page

    def _create_api_tab(self):
        self.api_panel = APIManagerPanel(SETTINGS, self)
        return self._make_panel_page("api", self.api_panel)

    def _style_settings_subtree(self, root):
        if root is None:
            return
        for table in root.findChildren(QTableWidget):
            try:
                table.setStyleSheet(table_qss())
                table.horizontalHeader().setStyleSheet(table_header_qss())
            except Exception:
                pass
        for combo in root.findChildren(QComboBox):
            try:
                combo.view().setStyleSheet(combo_popup_qss())
            except Exception:
                pass
        appearance_cfg = SETTINGS.get('appearance', {})
        if not isinstance(appearance_cfg, dict):
            appearance_cfg = {}
        cursor_shape = Qt.PointingHandCursor if appearance_cfg.get('use_pointer_cursors', True) else Qt.ArrowCursor
        for widget in root.findChildren(QWidget):
            if isinstance(widget, (QPushButton, QToolButton, QComboBox, QCheckBox, QSlider, QListWidget)):
                widget.setCursor(cursor_shape)

    def _apply_settings_styles(self, root_widget=None):
        self.setStyleSheet(settings_center_stylesheet())
        if root_widget is not None:
            self._style_settings_subtree(root_widget)
            return
        for page in self._built_tabs.values() if hasattr(self, '_built_tabs') else (self,):
            self._style_settings_subtree(page)
        self._style_settings_subtree(self._nav_list)
        if getattr(self, '_cancel_btn', None) is not None:
            appearance_cfg = SETTINGS.get('appearance', {}) or {}
            cursor_shape = Qt.PointingHandCursor if appearance_cfg.get('use_pointer_cursors', True) else Qt.ArrowCursor
            for btn in (self._cancel_btn, self._apply_btn, self._save_btn):
                btn.setCursor(cursor_shape)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def set_active_tab(self, key: str):
        if not key:
            return
        idx = self._nav_index_for_key(key)
        if idx is not None:
            self._nav_list.setCurrentRow(idx)

    def _current_autosave_state(self):
        enabled = False
        interval_ms = 300000
        try:
            timer = getattr(self.main_window, 'autosave_timer', None)
            if timer is not None:
                interval_ms = timer.interval()
                enabled = timer.isActive()
        except Exception:
            pass
        if hasattr(self.main_window, 'autosave_enabled'):
            enabled = bool(getattr(self.main_window, 'autosave_enabled'))
        return enabled, max(5000, int(interval_ms))

    def _apply_autosave_settings(self, enabled, interval_ms):
        try:
            timer = getattr(self.main_window, 'autosave_timer', None)
            if timer is None:
                timer = QTimer(self.main_window)
                timer.timeout.connect(self.main_window.auto_save_project)
                self.main_window.autosave_timer = timer
            try:
                interval_ms = int(interval_ms)
            except Exception:
                interval_ms = 300000
            interval_ms = max(5000, interval_ms)
            timer.setInterval(interval_ms)
            self.main_window.autosave_enabled = bool(enabled)
            if enabled:
                timer.start()
            else:
                timer.stop()
            autosave_cfg = SETTINGS.setdefault('autosave', {})
            autosave_cfg['enabled'] = bool(enabled)
            autosave_cfg['interval_ms'] = interval_ms
            save_settings(SETTINGS)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Save handler
    # ------------------------------------------------------------------
    def _create_glossary_tab(self):
        meta = self._page_meta("glossary")
        page, layout = self._make_page_scroll()
        layout.addWidget(self._make_page_header(
            meta.get("title", "Glossary"),
            meta.get("subtitle", "")
        ))

        card = QGroupBox("Term Pairs (Source -> Target)")
        card.setObjectName("settings-card")
        card_vbox = QVBoxLayout(card)
        card_vbox.setSpacing(8)
        card_vbox.setContentsMargins(12, 16, 12, 12)

        # Tabel glossary
        self._glossary_table = QTableWidget(0, 2)
        self._glossary_table.setHorizontalHeaderLabels(["Source Term (Original)", "Target Term (Terjemahan)"])
        self._glossary_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._glossary_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._glossary_table.setAlternatingRowColors(True)
        self._glossary_table.setMinimumHeight(280)
        card_vbox.addWidget(self._glossary_table)

        # Muat data glossary dari SETTINGS
        glossary = SETTINGS.get('glossary', {})
        for source, target in glossary.items():
            self._add_glossary_row(source, target)

        # Tombol aksi
        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Add Term")
        add_btn.clicked.connect(self._on_glossary_add)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.setIcon(app_icon("minus", COLORS['danger'], size=12))
        remove_btn.setIconSize(QSize(12, 12))
        remove_btn.clicked.connect(self._on_glossary_remove)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch(1)
        card_vbox.addLayout(btn_row)

        layout.addWidget(card)

        # Info box
        info_card = QGroupBox("How it works")
        info_card.setObjectName("settings-card")
        info_vbox = QVBoxLayout(info_card)
        info_label = QLabel(
            "Setiap pasangan term yang kamu tambahkan akan diinjeksikan ke dalam prompt AI "
            "saat menerjemahkan. AI akan selalu menggunakan 'Target Term' untuk setiap "
            "kemunculan 'Source Term' dalam teks.\n\n"
            "Contoh:\n"
            "  Source: 煉獄杏寿郎  ->  Target: Rengoku Kyojuro\n"
            "  Source: 無惨  ->  Target: Muzan\n"
            "  Source: 全集中  ->  Target: Total Concentration"
        )
        info_label.setWordWrap(True)
        info_label.setObjectName("settings-option-desc")
        info_vbox.addWidget(info_label)
        layout.addWidget(info_card)
        layout.addStretch(1)
        return page

    def _add_glossary_row(self, source: str = "", target: str = ""):
        """Tambahkan baris baru ke tabel glossary."""
        row = self._glossary_table.rowCount()
        self._glossary_table.insertRow(row)
        self._glossary_table.setItem(row, 0, QTableWidgetItem(source))
        self._glossary_table.setItem(row, 1, QTableWidgetItem(target))

    def _on_glossary_add(self):
        """Tambahkan baris kosong ke tabel glossary."""
        self._add_glossary_row()
        # Scroll ke baris baru dan mulai edit
        last_row = self._glossary_table.rowCount() - 1
        self._glossary_table.scrollToBottom()
        self._glossary_table.setCurrentCell(last_row, 0)
        self._glossary_table.editItem(self._glossary_table.item(last_row, 0))

    def _on_glossary_remove(self):
        """Hapus baris yang dipilih dari tabel glossary."""
        selected_rows = sorted(
            set(idx.row() for idx in self._glossary_table.selectedIndexes()),
            reverse=True
        )
        for row in selected_rows:
            self._glossary_table.removeRow(row)

    def _get_glossary_from_table(self) -> dict:
        """Kumpulkan semua pasangan term dari tabel menjadi dict."""
        result = {}
        for row in range(self._glossary_table.rowCount()):
            source_item = self._glossary_table.item(row, 0)
            target_item = self._glossary_table.item(row, 1)
            source = source_item.text().strip() if source_item else ''
            target = target_item.text().strip() if target_item else ''
            if source:
                result[source] = target
        return result

    def _on_apply(self):
        self._commit_settings(close_dialog=False)

    def _on_save(self):
        self._commit_settings(close_dialog=True)

    def _commit_settings(self, close_dialog=True):
        built = getattr(self, '_built_tabs', {})

        api_export = None
        if "api" in built and getattr(self, 'api_panel', None) is not None:
            api_export = self.api_panel.export_settings()
            if api_export is None:
                warnings = "\n".join(self.api_panel.validation_messages())
                details = f"\n\n{warnings}" if warnings else ""
                notify_banner(self, "settings-api-validation", "API settings", f"Please fix the highlighted API settings issues before saving.{details}", kind="warning")
                self.set_active_tab("api")
                return False

        translation_settings = None
        if "translation" in built and getattr(self, 'openrouter_panel', None) is not None:
            translation_settings = self.openrouter_panel.export_settings()

        appearance_cfg = None
        appearance_changed = False
        if "appearance" in built:
            appearance_cfg = self._collect_appearance_settings()
            appearance_changed = appearance_cfg != self._initial_appearance

        autosave_enabled = self._initial_autosave_enabled
        autosave_interval_ms = self._initial_autosave_interval
        if "general" in built:
            autosave_enabled = bool(self.autosave_checkbox.isChecked())
            autosave_interval_ms = int(self.autosave_interval_spin.value() * 1000)
            self._apply_autosave_settings(autosave_enabled, autosave_interval_ms)

            gen_cfg = SETTINGS.setdefault('general', {})
            gen_cfg['save_format'] = self.save_format_combo.currentText()
            gen_cfg['save_quality'] = self.save_quality_spin.value()
            gen_cfg['default_ai_model'] = self.default_ai_model_combo.currentText()
            gen_cfg['default_translation_style'] = self.default_style_combo.currentText()
            gen_cfg['default_font_family'] = self.default_font_combo.currentText()
            gen_cfg['default_font_size'] = self.default_font_size_spin.value()
            gen_cfg['default_font_bold'] = bool(self.default_font_bold_checkbox.isChecked())

            typeset_cfg = SETTINGS.setdefault('typeset', {})
            typeset_cfg['outline_enabled'] = bool(self.default_outline_checkbox.isChecked())
            typeset_cfg['outline_color'] = self.default_outline_color.name()

            ec_cfg = SETTINGS.setdefault('emergency_close', {})
            action_map_reverse = {"Open URL": "url", "Launch Application": "app", "Focus Existing Window": "focus"}
            ec_cfg['action_type'] = action_map_reverse.get(self.ec_action_combo.currentText(), 'url')
            ec_cfg['target'] = self.ec_target_edit.text().strip()

        cleanup_cfg = SETTINGS.setdefault('cleanup', {})
        prev_auto_color = bool(cleanup_cfg.get('auto_text_color', True))
        prev_threshold = int(cleanup_cfg.get('text_color_threshold', 128))
        prev_use_box = bool(cleanup_cfg.get('use_background_box', True))
        prev_constrain_text = bool(cleanup_cfg.get('constrain_text', True))
        prev_inpaint_model = cleanup_cfg.get('inpaint_model_name', 'Built-in Big-LaMa')
        prev_unified_engine = resolve_inpaint_engine_id(cleanup_cfg)
        prev_inpaint_url = cleanup_cfg.get('inpaint_server_url', DEFAULT_INPAINT_SERVER_URL)

        if "cleanup" in built:
            if getattr(self, 'cleanup_use_inpaint_checkbox', None) is not None:
                use_inpaint_val = bool(self.cleanup_use_inpaint_checkbox.isChecked())
                if hasattr(self.main_window, '_set_global_cleanup_default'):
                    try:
                        self.main_window._set_global_cleanup_default('use_inpaint', use_inpaint_val, persist=False)
                    except Exception:
                        cleanup_cfg['use_inpaint'] = use_inpaint_val
                cleanup_cfg['use_inpaint'] = use_inpaint_val
            if getattr(self, 'cleanup_inpaint_engine_combo', None) is not None:
                unified_eid = normalize_inpaint_engine_id(self.cleanup_inpaint_engine_combo.currentData())
                cleanup_cfg['inpaint_engine'] = unified_eid
                cleanup_cfg['full_inpaint_engine'] = unified_eid
                cleanup_cfg['brush_inpaint_engine'] = unified_eid
                cleanup_cfg['inpaint_model_name'] = engine_display_label(unified_eid)
            if getattr(self, 'cleanup_inpaint_device_combo', None) is not None:
                cleanup_cfg['inpaint_device'] = str(self.cleanup_inpaint_device_combo.currentData() or 'auto')
            if getattr(self, 'cleanup_inpaint_padding_spin', None) is not None:
                cleanup_cfg['inpaint_padding'] = int(self.cleanup_inpaint_padding_spin.value())
            if getattr(self, 'cleanup_iopaint_url_edit', None) is not None:
                url_val = self.cleanup_iopaint_url_edit.text().strip() or DEFAULT_INPAINT_SERVER_URL
                cleanup_cfg['inpaint_server_url'] = url_val
            if getattr(self, 'cleanup_iopaint_timeout_spin', None) is not None:
                cleanup_cfg['inpaint_server_timeout'] = int(self.cleanup_iopaint_timeout_spin.value())

            cleanup_cfg['auto_text_color'] = bool(self.auto_text_color_checkbox.isChecked())
            cleanup_cfg['text_color_threshold'] = int(self.threshold_spin.value())
            use_box_value = bool(self.use_background_box_checkbox.isChecked())
            if hasattr(self.main_window, '_set_global_cleanup_default'):
                try:
                    self.main_window._set_global_cleanup_default('use_background_box', use_box_value, persist=False)
                except Exception:
                    cleanup_cfg['use_background_box'] = use_box_value
            cleanup_cfg['use_background_box'] = use_box_value
            constrain_text_value = bool(self.constrain_text_checkbox.isChecked())
            if hasattr(self.main_window, '_set_global_cleanup_default'):
                try:
                    self.main_window._set_global_cleanup_default('constrain_text', constrain_text_value, persist=False)
                except Exception:
                    cleanup_cfg['constrain_text'] = constrain_text_value
            cleanup_cfg['constrain_text'] = constrain_text_value
            try:
                cleanup_cfg['remove_ai_temp_files'] = bool(self.remove_ai_temp_checkbox.isChecked())
            except Exception:
                cleanup_cfg['remove_ai_temp_files'] = bool(cleanup_cfg.get('remove_ai_temp_files', True))

        shortcut_settings = None
        shortcuts_changed = False
        if "shortcuts" in built and getattr(self, 'shortcut_editors', None) is not None:
            shortcut_settings = {}
            for key, editor in self.shortcut_editors.items():
                sequence = (editor.sequence() or '').strip()
                default_seq = DEFAULT_SHORTCUTS.get(key, '')
                if not sequence:
                    if default_seq:
                        shortcut_settings[key] = ''
                elif sequence != default_seq:
                    shortcut_settings[key] = sequence
            shortcuts_changed = shortcut_settings != self._initial_shortcuts
            SETTINGS['shortcuts'] = shortcut_settings

        if translation_settings is not None:
            SETTINGS.setdefault('translate', {})
            SETTINGS['translate'].update(copy.deepcopy(translation_settings))
        if api_export is not None:
            SETTINGS['apis'] = copy.deepcopy(api_export.get('apis', {}))
            SETTINGS['ocr'] = copy.deepcopy(api_export.get('ocr', {}))
            SETTINGS['tesseract'] = copy.deepcopy(api_export.get('tesseract', {}))
        if appearance_cfg is not None:
            SETTINGS['appearance'] = copy.deepcopy(appearance_cfg)

        if "glossary" in built and hasattr(self, '_glossary_table'):
            SETTINGS['glossary'] = self._get_glossary_from_table()

        save_settings(SETTINGS)

        # Hot-apply custom default values & cleanup badges to main window
        if hasattr(self.main_window, 'apply_defaults_from_settings'):
            try:
                self.main_window.apply_defaults_from_settings(apply_runtime_controls=("cleanup" in built or "general" in built))
            except Exception as e:
                print(f"Error applying default presets: {e}")
        if "cleanup" in built and hasattr(self.main_window, '_refresh_inpaint_summary_badges'):
            try:
                self.main_window._refresh_inpaint_summary_badges()
            except Exception:
                pass

        if api_export is not None:
            try:
                refresh_api_clients()
            except Exception:
                pass

        if appearance_changed and hasattr(self.main_window, 'apply_appearance_from_settings'):
            try:
                self.main_window.apply_appearance_from_settings()
                self._apply_settings_styles()
            except Exception as e:
                print(f"Error applying appearance settings: {e}")

        if api_export is not None:
            try:
                self.main_window.is_openai_available = (openai is not None and openai_client is not None)
            except Exception:
                pass

        if shortcuts_changed and hasattr(self.main_window, 'reload_shortcuts'):
            try:
                self.main_window.reload_shortcuts()
            except Exception:
                pass

        if api_export is not None and hasattr(self.main_window, 'populate_ocr_languages'):
            try:
                self.main_window.populate_ocr_languages()
            except Exception:
                pass

        if (api_export is not None or translation_settings is not None) and hasattr(self.main_window, 'populate_ai_models'):
            try:
                self.main_window.populate_ai_models()
            except Exception:
                pass

        if (
            (cleanup_cfg.get('auto_text_color') != prev_auto_color)
            or (cleanup_cfg.get('text_color_threshold') != prev_threshold)
            or (cleanup_cfg.get('constrain_text') != prev_constrain_text)
        ):
            try:
                self.main_window.redraw_all_typeset_areas()
            except Exception:
                pass

        status_parts = []
        if (
            (cleanup_cfg.get('auto_text_color') != prev_auto_color)
            or (cleanup_cfg.get('text_color_threshold') != prev_threshold)
            or (cleanup_cfg.get('use_background_box') != prev_use_box)
            or (cleanup_cfg.get('constrain_text') != prev_constrain_text)
            or (cleanup_cfg.get('inpaint_model_name') != prev_inpaint_model)
            or (resolve_inpaint_engine_id(cleanup_cfg) != prev_unified_engine)
            or (cleanup_cfg.get('inpaint_server_url') != prev_inpaint_url)
        ):
            status_parts.append("Cleanup & Inpaint settings updated")
        if translation_settings is not None and translation_settings != self._initial_translate:
            status_parts.append("Translation settings updated")
        if api_export is not None and any(api_export.get(key, {}) != self._initial_api.get(key, {}) for key in ('apis', 'ocr', 'tesseract')):
            status_parts.append("API settings updated")
        if (autosave_enabled != self._initial_autosave_enabled) or (abs(autosave_interval_ms - self._initial_autosave_interval) > 1):
            status_parts.append("Autosave preferences updated")
        if shortcuts_changed:
            status_parts.append("Shortcuts updated")
        if appearance_changed:
            status_parts.append("Appearance updated")

        if status_parts and hasattr(self.main_window, 'statusBar'):
            try:
                self.main_window.statusBar().showMessage(" | ".join(status_parts), 4000)
            except Exception:
                pass

        self._initial_autosave_enabled = autosave_enabled
        self._initial_autosave_interval = autosave_interval_ms
        self._initial_cleanup = copy.deepcopy(cleanup_cfg)
        if api_export is not None:
            self._initial_api = {
                'apis': copy.deepcopy(SETTINGS.get('apis', {})),
                'ocr': copy.deepcopy(SETTINGS.get('ocr', {})),
                'tesseract': copy.deepcopy(SETTINGS.get('tesseract', {})),
            }
        if translation_settings is not None:
            self._initial_translate = self._translation_settings_snapshot()
        if shortcut_settings is not None:
            self._initial_shortcuts = copy.deepcopy(shortcut_settings)
        if appearance_cfg is not None:
            self._initial_appearance = copy.deepcopy(appearance_cfg)

        if close_dialog:
            self.accept()
        else:
            notify_toast(self, "Settings applied", "Changes saved without closing Settings.", kind="success")
        return True

    def sync_cleanup_controls_from_settings(self):
        cleanup_cfg = SETTINGS.get('cleanup', {}) if isinstance(SETTINGS.get('cleanup'), dict) else {}
        unified_eid = resolve_inpaint_engine_id(cleanup_cfg)
        combo = getattr(self, 'cleanup_inpaint_engine_combo', None)
        if combo is not None:
            with QSignalBlocker(combo):
                idx = combo.findData(unified_eid)
                if idx != -1:
                    combo.setCurrentIndex(idx)
        self._refresh_inpaint_model_statuses()

    def closeEvent(self, event):
        worker = getattr(self, '_inpaint_dl_worker', None)
        if worker is not None:
            try:
                worker.cancel()
                worker.wait(500)
            except Exception:
                pass
        super().closeEvent(event)

class ReviewDialog(QDialog):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Review OCR Text")
        self.setGeometry(200, 200, 400, 300)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Please review and edit the OCR text before translating:"))
        self.text_edit = QTextEdit()
        self.text_edit.setText(text)
        layout.addWidget(self.text_edit)
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("Continue")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        layout.addLayout(button_layout)

    def get_text(self):
        return self.text_edit.toPlainText()


from src.ui.advanced_text_editor_dialog import AdvancedTextEditDialog  # noqa: E402


class SceneReviewDialog(QDialog):
    def __init__(self, parent, original_items, ai_proposals):
        super().__init__(parent)
        self.setWindowTitle("Review AI Changes")
        self.resize(900, 600)
        self.accepted_indices = []
        
        layout = QVBoxLayout(self)
        
        # Info
        layout.addWidget(QLabel("Review the proposed changes below. Uncheck items you want to skip."))
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["#", "Original / Current", "AI Proposal", "Apply"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        # Populate
        # original_items is [Text 1 (Old), Text 2, ..., Text N (New)]
        # ai_proposals is matching list
        row_count = min(len(original_items), len(ai_proposals))
        self.table.setRowCount(row_count)
        
        for i in range(row_count):
            orig = original_items[i]
            prop = ai_proposals[i]
            
            # Col 0: Index
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            
            # Col 1: Original
            orig_item = QTableWidgetItem(orig)
            orig_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(i, 1, orig_item)
            
            # Col 2: Proposal
            prop_item = QTableWidgetItem(prop)
            prop_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
            self.table.setItem(i, 2, prop_item)
            
            # Col 3: Checkbox
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.setContentsMargins(0,0,0,0)
            chk_layout.setAlignment(Qt.AlignCenter)
            chk = QCheckBox()
            chk.setChecked(True)
            chk_layout.addWidget(chk)
            self.table.setCellWidget(i, 3, chk_widget)
            
        layout.addWidget(self.table)
        
        # Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.button(QDialogButtonBox.Ok).setText("Apply Selected")
        btn_box.accepted.connect(self.accept_changes)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        
    def accept_changes(self):
        self.accepted_indices = []
        for i in range(self.table.rowCount()):
            widget = self.table.cellWidget(i, 3)
            if widget:
                chk = widget.findChild(QCheckBox)
                if chk and chk.isChecked():
                    # Get potentially edited text
                    new_text = self.table.item(i, 2).text()
                    self.accepted_indices.append((i, new_text))
        self.accept()

class HistoryEditDialog(QDialog):
    def __init__(self, entry, styles, allow_original=True, allow_style=True, parent=None):
        super().__init__(parent)
        self.entry = entry  # Dictionary copy of the history/area data
        self.result = None
        self.setWindowTitle("Advanced Text Edit")
        self.setModal(True)
        self.resize(700, 600)

        main_layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # ----------------------------------------------------------------
        # Tab 1: Text & Translation
        # ----------------------------------------------------------------
        self.text_tab = QWidget()
        text_layout = QVBoxLayout(self.text_tab)
        
        info_label = QLabel("Adjust the text below.")
        text_layout.addWidget(info_label)

        original_label = QLabel("Original OCR")
        text_layout.addWidget(original_label)
        self.original_edit = QTextEdit()
        self.original_edit.setPlainText(entry.get('original_text', ''))
        self.original_edit.setMinimumHeight(100)
        if not allow_original:
            self.original_edit.setReadOnly(True)
            self.original_edit.setStyleSheet("background-color: #111824; color: #7f8ba7;")
        text_layout.addWidget(self.original_edit)

        translated_label = QLabel("Translated Text")
        text_layout.addWidget(translated_label)
        self.translated_edit = QTextEdit()
        self.translated_edit.setPlainText(entry.get('translated_text', ''))
        self.translated_edit.setMinimumHeight(120)
        text_layout.addWidget(self.translated_edit)

        translate_btn_layout = QHBoxLayout()
        translate_btn_layout.addStretch()
        self.translate_button = QPushButton("Translate")
        self.translate_button.setToolTip("Translate the OCR text using the active translation provider")
        translate_btn_layout.addWidget(self.translate_button)
        text_layout.addLayout(translate_btn_layout)
        self.translate_button.clicked.connect(self._on_translate_clicked)

        # AI Model Selector
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("AI Model:"))
        self.ai_model_combo = QComboBox()
        # Populate
        parent = self.parent()
        if parent:
             current_provider, current_model = parent.get_selected_model_name()
             if current_model:
                 self.ai_model_combo.addItem(f"{current_provider}: {current_model}")
             
             known_models = ["Gemini: gemini-1.5-flash", "Gemini: gemini-1.5-pro", "OpenAI: gpt-4o", "OpenAI: gpt-4o-mini"]
             for m in known_models:
                 if self.ai_model_combo.findText(m) == -1:
                     self.ai_model_combo.addItem(m)
        else:
             self.ai_model_combo.addItem("Gemini: gemini-1.5-flash")
        
        model_layout.addWidget(self.ai_model_combo)
        text_layout.addLayout(model_layout)

        if allow_style:
            style_layout = QHBoxLayout()
            style_label = QLabel("Translation Style")
            style_layout.addWidget(style_label)
            self.style_combo = QComboBox()
            self.style_combo.addItems(styles or [])
            current_style = entry.get('translation_style', '')
            if current_style and current_style in (styles or []):
                self.style_combo.setCurrentText(current_style)
            elif styles:
                self.style_combo.setCurrentIndex(0)
            style_layout.addWidget(self.style_combo)
            style_layout.addStretch()
            text_layout.addLayout(style_layout)
        else:
            self.style_combo = None

        self.tab_widget.addTab(self.text_tab, "Text")
        
        # Typography tab removed as requested


        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        button_box.button(QDialogButtonBox.Ok).setText("Apply")
        button_box.accepted.connect(self.handle_accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def _build_typography_tab(self):
        # We need access to FontManager. Currently GLOBAL_FONT_MANAGER or self.parent().font_manager
        parent = self.parent()
        self.font_manager = getattr(parent, 'font_manager', None)

        layout = QScrollArea()
        layout.setWidgetResizable(True)
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setSpacing(15)
        layout.setWidget(container)

        self.overrides = self.entry.get('overrides', {}).copy()
        # Helper to get value falling back to app defaults if not in overrides
        # But here we are editing specific area, so we should show what's currently active on the area
        # The 'entry' passed in is just a dict derived from history.
        # Ideally we want the actual TypesetArea object or enough data to reconstruct state.
        # Assuming 'entry' has keys like 'font_family', 'font_size', etc. 
        # If the entry comes from 'history', it might be sparse.
        # The caller 'open_result_editor' passes a dict from history. History doesn't store full rich typography usually.
        # Wait, if `HistoryEditDialog` is "Advanced Text Edit", we typically want to edit the active TypesetArea.
        # If this dialog is invoked from the ResultTable (history), it might not have the TypesetArea reference.
        # However, the user request implies changing these settings for the text on screen. 
        # Let's assume we can init fields from the `entry` if keys exist, or defaults.
        
        # --- Appearance: Font & Color ---
        g_font = QGroupBox("Font && Color")
        g_font_layout = QGridLayout(g_font)
        
        g_font_layout.addWidget(QLabel("Family:"), 0, 0)
        self.font_combo = QComboBox() 
        from src.ui.widgets import FontDelegate
        self.font_combo.setItemDelegate(FontDelegate(self.font_manager, self.font_combo))
        # Ideally use custom font manager population if possible, matching main app
        if self.font_manager:
            self.font_combo.clear()
            for f in self.font_manager.list_fonts():
                self.font_combo.addItem(f)
        current_font = self.entry.get('font_family') or "Arial"
        self.font_combo.setCurrentText(current_font)
        g_font_layout.addWidget(self.font_combo, 0, 1)

        g_font_layout.addWidget(QLabel("Size:"), 0, 2)
        self.size_spin = QDoubleSpinBox()
        self.size_spin.setRange(4, 300); self.size_spin.setValue(float(self.entry.get('font_size', 14)))
        g_font_layout.addWidget(self.size_spin, 0, 3)

        g_font_layout.addWidget(QLabel("Color:"), 1, 0)
        self.color_btn = QPushButton("Pick Color")
        self.color_val = self.entry.get('text_color', '#000000')
        self.color_btn.setStyleSheet(f"background-color: {self.color_val}; color: {'#000' if self._is_light(self.color_val) else '#fff'}")
        self.color_btn.clicked.connect(self._pick_color)
        g_font_layout.addWidget(self.color_btn, 1, 1)

        vbox.addWidget(g_font)

        # --- Gradient ---
        g_grad = QGroupBox("Gradient Coloring")
        g_grad.setCheckable(True)
        self.grad_enabled = bool(self.entry.get('gradient_enabled', False))
        g_grad.setChecked(self.grad_enabled)
        g_grad_layout = QVBoxLayout(g_grad)

        # Angle
        angle_row = QHBoxLayout()
        angle_row.addWidget(QLabel("Angle (deg):"))
        self.grad_angle_spin = QDoubleSpinBox()
        self.grad_angle_spin.setRange(0, 360)
        self.grad_angle_spin.setSingleStep(15)
        self.grad_angle_spin.setValue(float(self.entry.get('gradient_angle', 0.0)))
        angle_row.addWidget(self.grad_angle_spin)
        g_grad_layout.addLayout(angle_row)

        # Colors List
        self.grad_colors = list(self.entry.get('gradient_colors', ["#FF0000", "#0000FF"]))
        if not isinstance(self.grad_colors, list) or len(self.grad_colors) < 2:
            self.grad_colors = ["#FF0000", "#0000FF"]
        
        self.grad_list = QListWidget()
        self.grad_list.setFixedHeight(100)
        self._refresh_grad_list()
        g_grad_layout.addWidget(self.grad_list)

        grad_btns = QHBoxLayout()
        add_c_btn = QPushButton("Add Color")
        add_c_btn.clicked.connect(self._add_grad_color)
        rem_c_btn = QPushButton("Remove Color")
        rem_c_btn.clicked.connect(self._remove_grad_color)
        grad_btns.addWidget(add_c_btn)
        grad_btns.addWidget(rem_c_btn)
        g_grad_layout.addLayout(grad_btns)
        
        vbox.addWidget(g_grad)
        self.grad_group = g_grad

        # --- Layout ---
        g_layout = QGroupBox("Layout")
        l_layout = QFormLayout(g_layout)
        self.align_combo = QComboBox()
        self.align_combo.addItems(["left", "center", "right", "justify"])
        self.align_combo.setCurrentText(self.entry.get('alignment', 'center'))
        l_layout.addRow("Alignment:", self.align_combo)
        
        self.line_spacing_spin = QDoubleSpinBox(); self.line_spacing_spin.setRange(0.5, 5.0); self.line_spacing_spin.setSingleStep(0.1)
        self.line_spacing_spin.setValue(float(self.entry.get('line_spacing', 1.0)))
        l_layout.addRow("Line Spacing:", self.line_spacing_spin)

        vbox.addWidget(g_layout)

        # Add scroll area to tab
        layout_in_tab = QVBoxLayout(self.min_typography_tab)
        layout_in_tab.addWidget(layout)

    def _is_light(self, color_str):
        c = QColor(color_str)
        return c.lightness() > 128

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self.color_val), self, "Pick Text Color")
        if c.isValid():
            self.color_val = c.name()
            self.color_btn.setStyleSheet(f"background-color: {self.color_val}; color: {'#000' if self._is_light(self.color_val) else '#fff'}")

    def _refresh_grad_list(self):
        self.grad_list.clear()
        for c in self.grad_colors:
            item = QListWidgetItem(c)
            item.setBackground(QColor(c))
            item.setForeground(QColor('#000' if self._is_light(c) else '#fff'))
            self.grad_list.addItem(item)

    def _add_grad_color(self):
        c = QColorDialog.getColor(Qt.white, self, "Add Gradient Color")
        if c.isValid():
            self.grad_colors.append(c.name())
            self._refresh_grad_list()

    def _remove_grad_color(self):
        row = self.grad_list.currentRow()
        if row >= 0 and len(self.grad_colors) > 2:
            self.grad_colors.pop(row)
            self._refresh_grad_list()
        elif len(self.grad_colors) <= 2:
            notify_toast(self, "Limit", "Gradient must have at least 2 colors.", kind="warning")

    def handle_accept(self):
        self.result = {
            'original_text': self.original_edit.toPlainText(),
            'translated_text': self.translated_edit.toPlainText(),
            'translation_style': self.style_combo.currentText() if self.style_combo else (self.entry.get('translation_style') or ''),
        }
        self.accept()

    def _on_translate_clicked(self):
        parent = self.parent()
        if not parent:
            return

        ocr_text = self.original_edit.toPlainText() or ''
        if not ocr_text.strip():
            return

        # Determine provider/model from local combo
        combo_text = self.ai_model_combo.currentText()
        if ":" in combo_text:
            provider, model_name = [x.strip() for x in combo_text.split(":", 1)]
        else:
             # Fallback
             provider, model_name = parent.get_selected_model_name()

        if not model_name:
            notify_banner(self, "history-edit-no-model", "No model", "Please select an AI model.", kind="warning")
            return

        self.translate_button.setEnabled(False)
        self.translate_button.setText("Translating...")
        QApplication.processEvents()

        try:
            # Need to get styles if any
            local_settings = SETTINGS.copy()
            if self.style_combo:
                style_name = self.style_combo.currentText()
                if style_name:
                    local_settings['translation_style'] = style_name
            
            # Call parent method with SETTINGS dict
            translated = parent.translate_with_ai(ocr_text, {}, provider, model_name, local_settings)
            self.translated_edit.setPlainText(str(translated))
        except Exception as e:
            traceback.print_exc()
            notify_banner(self, "history-edit-translation-failed", "Error", f"Translation failed: {str(e)}", kind="error")
        finally:
            self.translate_button.setEnabled(True)
            self.translate_button.setText("Translate")

    def get_result(self):
        return self.result



class ManualTextDialog(QDialog):
    def __init__(self, default_inpaint=True, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manual Text Input")
        self.setModal(True)
        self.resize(420, 340)

        main_layout = QVBoxLayout(self)

        instructions = QLabel("Type the text you want to place inside the selected area.")
        instructions.setWordWrap(True)
        main_layout.addWidget(instructions)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Enter manual text here...")
        self.text_edit.setMinimumHeight(160)
        main_layout.addWidget(self.text_edit)

        self.inpaint_checkbox = QCheckBox("Apply inpainting before adding text")
        self.inpaint_checkbox.setChecked(default_inpaint)
        main_layout.addWidget(self.inpaint_checkbox)

        button_box = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        button_box.button(QDialogButtonBox.Ok).setText("Apply")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def get_text(self):
        return self.text_edit.toPlainText()

    def use_inpainting(self):
        return self.inpaint_checkbox.isChecked()

class BatchSaveDialog(QDialog):
    save_requested = pyqtSignal(list)

    def __init__(self, all_files, parent=None):
        super().__init__(parent)
        self.main_app = parent
        self.all_files = all_files
        self.setWindowTitle("Batch Save Images")
        self.setMinimumSize(600, 700)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        selection_layout = QGridLayout()
        presets = [5, 10, 15, 20, 25]
        for i, num in enumerate(presets):
            btn = QPushButton(f"Select Next {num} Unsaved")
            btn.clicked.connect(lambda _, n=num: self.select_next_unsaved(n))
            selection_layout.addWidget(btn, 0, i)

        select_all_btn = QPushButton("Select All Unsaved")
        select_all_btn.clicked.connect(self.select_all_unsaved)
        selection_layout.addWidget(select_all_btn, 1, 0, 1, 2)

        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self.deselect_all)
        selection_layout.addWidget(deselect_all_btn, 1, 2, 1, 3)
        layout.addLayout(selection_layout)

        self.list_widget = QListWidget()
        self.populate_list()
        layout.addWidget(self.list_widget)

        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save Selected")
        self.save_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        layout.addLayout(button_layout)

    def populate_list(self):
        self.list_widget.clear()
        for file_path in self.all_files:
            if "_typeset" in file_path.lower():
                continue
            item = QListWidgetItem(os.path.basename(file_path))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)

            is_saved = self.main_app.check_if_saved(file_path)
            if is_saved:
                item.setCheckState(Qt.Unchecked)
                item.setForeground(QColor("gray"))
                item.setText(f"{os.path.basename(file_path)} [SAVED]")
            else:
                item.setCheckState(Qt.Unchecked)

            item.setData(Qt.UserRole, file_path)
            self.list_widget.addItem(item)

    def select_next_unsaved(self, count):
        self.deselect_all()
        selected_count = 0
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            file_path = item.data(Qt.UserRole)
            if not self.main_app.check_if_saved(file_path):
                item.setCheckState(Qt.Checked)
                selected_count += 1
                if selected_count >= count:
                    break

    def select_all_unsaved(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not self.main_app.check_if_saved(item.data(Qt.UserRole)):
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)

    def deselect_all(self):
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.Unchecked)

    def get_selected_files(self):
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.data(Qt.UserRole))
        return selected

# ──────────────────────────────────────────────────────────────────
# Tesseract & Manga-OCR Background System Integration Helpers & Workers
# ──────────────────────────────────────────────────────────────────

def get_tessdata_path():
    tess_path = SETTINGS.get('tesseract', {}).get('path', '')
    if tess_path and os.path.exists(tess_path):
        dir_path = os.path.dirname(tess_path)
        tessdata = os.path.join(dir_path, 'tessdata')
        if os.path.exists(tessdata):
            return tessdata
        parent_tessdata = os.path.join(os.path.dirname(dir_path), 'share', 'tessdata')
        if os.path.exists(parent_tessdata):
            return parent_tessdata
    standard_paths = [
        r"C:\Program Files\Tesseract-OCR\tessdata",
        r"C:\Program Files (x86)\Tesseract-OCR\tessdata",
        "/usr/local/share/tessdata",
        "/opt/homebrew/share/tessdata",
        "/usr/share/tesseract-ocr/tessdata",
        "/usr/share/tessdata",
    ]
    for p in standard_paths:
        if os.path.exists(p):
            return p
    return None

def get_writable_tessdata_path():
    system_tessdata = get_tessdata_path()
    if system_tessdata and os.path.exists(system_tessdata):
        test_file = os.path.join(system_tessdata, ".write_test")
        try:
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            return system_tessdata
        except Exception:
            pass
    app_data_tessdata = os.path.join(ROOT_DIR, "tessdata")
    if not os.path.exists(app_data_tessdata):
        try:
            os.makedirs(app_data_tessdata)
        except Exception:
            pass
    return app_data_tessdata

def sync_tessdata_files():
    system_tessdata = get_tessdata_path()
    writable_tessdata = get_writable_tessdata_path()
    if system_tessdata and writable_tessdata and system_tessdata != writable_tessdata:
        try:
            for f in os.listdir(system_tessdata):
                if f.endswith(".traineddata"):
                    src = os.path.join(system_tessdata, f)
                    dst = os.path.join(writable_tessdata, f)
                    if not os.path.exists(dst):
                        shutil.copy2(src, dst)
        except Exception as e:
            print(f"Error syncing tessdata files: {e}")

def uninstall_tessdata_lang(lang):
    writable = get_writable_tessdata_path()
    file_path = os.path.join(writable, f"{lang}.traineddata")
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return True, f"Successfully uninstalled {lang} language model."
        except Exception as e:
            return False, f"Failed to delete file: {e}"
    return False, "Language model file not found or is in a system read-only folder."


class TessdataDownloadWorker(QThread):
    progress = pyqtSignal(int, int) # downloaded, total
    finished = pyqtSignal(bool, str) # success, message
    
    def __init__(self, lang, dest_dir):
        super().__init__()
        self.lang = lang
        self.dest_dir = dest_dir
        
    def run(self):
        url = f"https://github.com/tesseract-ocr/tessdata_fast/raw/main/{self.lang}.traineddata"
        dest_file = os.path.join(self.dest_dir, f"{self.lang}.traineddata")
        try:
            response = requests.get(url, stream=True, timeout=30)
            if response.status_code != 200:
                url = f"https://github.com/tesseract-ocr/tessdata/raw/main/{self.lang}.traineddata"
                response = requests.get(url, stream=True, timeout=30)
                if response.status_code != 200:
                    self.finished.emit(False, f"Download failed (HTTP {response.status_code})")
                    return
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            with open(dest_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        self.progress.emit(downloaded, total_size)
            self.finished.emit(True, dest_file)
        except Exception as e:
            self.finished.emit(False, str(e))

class TesseractInstallWorker(QThread):
    progress = pyqtSignal(str) # Status message
    finished = pyqtSignal(bool, str) # Success flag, message
    
    def run(self):
        try:
            if sys.platform.startswith('win'):
                self.progress.emit("Running winget install UB-Mannheim.TesseractOCR...")
                cmd = ["winget", "install", "UB-Mannheim.TesseractOCR", "--accept-source-agreements", "--accept-package-agreements", "--silent"]
                proc = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = proc.communicate()
                
                default_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
                if os.path.exists(default_path):
                    self.finished.emit(True, default_path)
                else:
                    self.finished.emit(False, f"Installation completed but tesseract.exe not found at default path.")
            
            elif sys.platform.startswith('darwin'):
                self.progress.emit("Running brew install tesseract...")
                proc = subprocess.Popen(["brew", "install", "tesseract"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = proc.communicate()
                
                which_proc = subprocess.Popen(["which", "tesseract"], stdout=subprocess.PIPE)
                path = which_proc.communicate()[0].decode().strip()
                if path and os.path.exists(path):
                    self.finished.emit(True, path)
                else:
                    self.finished.emit(False, f"Brew installed but tesseract not found in PATH.")
                    
            else:
                self.progress.emit("Running apt-get install tesseract-ocr...")
                proc = subprocess.Popen(["sudo", "apt-get", "update", "-y"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                proc.communicate()
                proc2 = subprocess.Popen(["sudo", "apt-get", "install", "-y", "tesseract-ocr"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                proc2.communicate()
                
                which_proc = subprocess.Popen(["which", "tesseract"], stdout=subprocess.PIPE)
                path = which_proc.communicate()[0].decode().strip()
                if path and os.path.exists(path):
                    self.finished.emit(True, path)
                else:
                    self.finished.emit(False, "Apt-get installed but tesseract not found in PATH.")
        except Exception as e:
            self.finished.emit(False, str(e))


class PipInstallWorker(QThread):
    progress = pyqtSignal(str)        # streamed pip output lines
    finished = pyqtSignal(bool, str)  # (success, message)

    def __init__(self, commands):
        """commands: list of pip-install arg-lists run sequentially.
        Each inner list is appended to [sys.executable, -m, pip, install].
        A bare list-of-strings is treated as a single command (legacy).
        """
        super().__init__()
        if commands and isinstance(commands[0], str):
            commands = [commands]
        self.commands = commands

    def run(self):
        try:
            for args in self.commands:
                label = " ".join(a for a in args if not a.startswith("-"))[:60]
                self.progress.emit(f"[pip] Installing: {label}...")
                cmd = [sys.executable, "-m", "pip", "install"] + args
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                )
                last_line = ""
                for line in proc.stdout:
                    line = line.rstrip()
                    if line:
                        self.progress.emit(line)
                        last_line = line
                proc.wait()
                if proc.returncode != 0:
                    self.finished.emit(
                        False,
                        f"pip failed for [{label}] (exit {proc.returncode}).\n"
                        f"Last output: {last_line}",
                    )
                    return
            importlib.invalidate_caches()
            # NOTE: Do NOT import torch-based packages here.
            # PyTorch DLL (c10.dll) must be initialised on the main thread.
            self.finished.emit(True, "All packages installed successfully.")
        except Exception as e:
            self.finished.emit(False, str(e))


class ImageCurvesDialog(QDialog):
    """Photoshop-style dialog for adjusting image contrast/brightness via natural spline curves."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Curves Adjustment")
        self.setModal(True)
        self.resize(740, 380)

        # Apply dark styling matching the main window
        self.setStyleSheet("""
            QDialog {
                background-color: #090a0f;
            }
            QLabel {
                color: #cbd5e1;
                font-family: 'Outfit', 'Inter', sans-serif;
            }
            QPushButton {
                background-color: #1e293b;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #38bdf8;
                color: #090a0f;
                border-color: #38bdf8;
            }
        """)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # Left layout: curves editor
        left_layout = QVBoxLayout()
        left_layout.setSpacing(8)
        
        title_label = QLabel("Spline Curves Editor")
        title_label.setStyleSheet("font-size: 11pt; font-weight: bold; color: #38bdf8;")
        left_layout.addWidget(title_label)

        # Import widget
        from src.ui.widgets import CurvesGraphWidget
        self.curves_widget = CurvesGraphWidget(self)
        left_layout.addWidget(self.curves_widget)

        instructions = QLabel("• Drag points to adjust\n• Click curve to add points\n• Right-click to remove points")
        instructions.setStyleSheet("color: #64748b; font-size: 8.5pt;")
        left_layout.addWidget(instructions)
        content_layout.addLayout(left_layout)

        # Right layout: live preview
        right_layout = QVBoxLayout()
        right_layout.setSpacing(8)

        preview_title = QLabel("Live Image Preview")
        preview_title.setStyleSheet("font-size: 11pt; font-weight: bold; color: #38bdf8;")
        right_layout.addWidget(preview_title)

        self.preview_label = QLabel()
        self.preview_label.setFixedSize(400, 260)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("background-color: #0f131c; border: 1.5px solid #1e293b; border-radius: 8px;")
        right_layout.addWidget(self.preview_label)
        
        right_layout.addStretch(1)
        content_layout.addLayout(right_layout)

        main_layout.addLayout(content_layout)

        # Bottom row
        bottom_layout = QHBoxLayout()
        
        reset_btn = QPushButton("Reset Curve")
        reset_btn.clicked.connect(self.reset_curve)
        bottom_layout.addWidget(reset_btn)
        
        bottom_layout.addStretch(1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(cancel_btn)

        apply_btn = QPushButton("Apply Curve")
        apply_btn.clicked.connect(self.apply_curve)
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #0369a1;
                color: #ffffff;
                border-color: #0284c7;
            }
            QPushButton:hover {
                background-color: #38bdf8;
                color: #090a0f;
                border-color: #38bdf8;
            }
        """)
        bottom_layout.addWidget(apply_btn)

        main_layout.addLayout(bottom_layout)

        # Load image for preview downscaled
        self.cv_preview = None
        self.unmodified_pil = None
        if parent and hasattr(parent, 'unmodified_image_pil') and parent.unmodified_image_pil is not None:
            self.unmodified_pil = parent.unmodified_image_pil
        elif parent and hasattr(parent, 'current_image_pil') and parent.current_image_pil is not None:
            self.unmodified_pil = parent.current_image_pil

        if self.unmodified_pil is not None:
            import cv2
            import numpy as np
            # Downscale copy to speed up live updates
            preview_copy = self.unmodified_pil.copy()
            preview_copy.thumbnail((400, 260))
            self.cv_preview = cv2.cvtColor(np.array(preview_copy), cv2.COLOR_RGB2BGR)

            # Compute histogram
            gray = cv2.cvtColor(self.cv_preview, cv2.COLOR_BGR2GRAY)
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
            self.curves_widget.set_histogram_data(hist)

        # Connect curves widget signal
        self.curves_widget.curveUpdated.connect(self.update_preview)

        # Restore existing active curves points if parent has them
        if parent and hasattr(parent, 'active_curves_points') and parent.active_curves_points is not None:
            self.curves_widget.set_curves_points(parent.active_curves_points)
        else:
            self.curves_widget.recompute_spline()

    def update_preview(self, lut):
        if self.cv_preview is None:
            self.preview_label.setText("No active image loaded")
            return
            
        import cv2
        # Apply LUT
        applied = cv2.LUT(self.cv_preview, lut)
        
        # Convert BGR to RGB
        rgb = cv2.cvtColor(applied, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.preview_label.setPixmap(QPixmap.fromImage(q_img))

    def reset_curve(self):
        self.curves_widget.set_curves_points([(0, 0), (255, 255)])

    def apply_curve(self):
        # Trigger parent applying curves to full size image
        if self.parent:
            self.parent.apply_curves_lut(self.curves_widget.lut, self.curves_widget.get_curves_points())
        self.accept()


# ============================================================
# Feature #16 — Session Analytics & Export Dialog
# ============================================================
class SessionAnalyticsDialog(QDialog):
    """
    Dialog analitik sesi: menampilkan API usage per provider/model
    sebagai grafik bar sederhana, estimasi biaya akumulasi,
    rate limit status (progress bar), dan fitur export ke CSV.
    """

    # Warna per provider (konsisten dengan dark theme app)
    PROVIDER_COLORS = {
        'Gemini':     '#4ade80',   # hijau
        'OpenAI':     '#60a5fa',   # biru
        'OpenRouter': '#f472b6',   # merah muda
    }
    PROVIDER_DEFAULT_COLOR = '#94a3b8'

    def __init__(self, parent=None, usage_data=None, ai_providers=None,
                 total_cost=0.0, usd_to_idr_rate=16200.0, total_input_tokens=0,
                 total_output_tokens=0):
        super().__init__(parent)
        self.usage_data      = usage_data      or {}
        self.ai_providers    = ai_providers    or {}
        self.total_cost      = total_cost
        self.usd_to_idr_rate = usd_to_idr_rate
        self.total_input_tokens  = total_input_tokens
        self.total_output_tokens = total_output_tokens

        self.setWindowTitle("Session Analytics & Export")
        self.setWindowIcon(app_icon("trending", COLORS['accent'], size=16))
        self.setModal(True)
        self.resize(700, 580)
        self._apply_style()
        self._build_ui()

    # ------------------------------------------------------------------
    # Stylesheet
    # ------------------------------------------------------------------
    def _apply_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #090a0f;
                color: #cbd5e1;
                font-family: 'Outfit', 'Inter', 'Segoe UI', sans-serif;
            }
            QLabel { color: #cbd5e1; }
            QScrollArea { border: none; background: transparent; }
            QWidget#inner_widget { background: transparent; }
            QFrame#separator {
                background-color: #1e293b;
                max-height: 1px;
                border: none;
            }
            QFrame#card {
                background-color: #0e111a;
                border: 1px solid #1e293b;
                border-radius: 8px;
            }
            QProgressBar {
                background-color: #1e293b;
                border: none;
                border-radius: 4px;
                height: 10px;
                text-align: right;
            }
            QProgressBar::chunk { border-radius: 4px; }
            QPushButton {
                background-color: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #f1f5f9;
                border-color: #38bdf8;
            }
            QPushButton#export_btn {
                background-color: #0ea5e9;
                color: #f8fafc;
                border: none;
                font-weight: bold;
            }
            QPushButton#export_btn:hover { background-color: #38bdf8; color: #0f172a; }
            QPushButton#reset_btn {
                background-color: #7f1d1d;
                color: #fca5a5;
                border: 1px solid #b91c1c;
            }
            QPushButton#reset_btn:hover { background-color: #b91c1c; color: #fff; }
        """)

    # ------------------------------------------------------------------
    # UI Builder
    # ------------------------------------------------------------------
    def _build_ui(self):
        from PyQt5.QtWidgets import QProgressBar as _QProgressBar, QScrollArea, QSizePolicy
        from PyQt5.QtCore import Qt

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────────
        header = QWidget()
        header.setStyleSheet("background-color: #0e111a; border-bottom: 1px solid #1e293b;")
        hdr_layout = QHBoxLayout(header)
        hdr_layout.setContentsMargins(20, 14, 20, 14)

        title_lbl = QLabel("Session Analytics")
        title_lbl.setStyleSheet("font-size: 14pt; font-weight: bold; color: #38bdf8;")
        hdr_layout.addWidget(title_lbl)
        hdr_layout.addStretch(1)

        # Tombol export & reset di header
        export_btn = QPushButton("Export CSV")
        export_btn.setIcon(app_icon("download", size=13))
        export_btn.setIconSize(QSize(13, 13))
        export_btn.setObjectName("export_btn")
        export_btn.setFixedHeight(32)
        export_btn.clicked.connect(self._export_csv)
        hdr_layout.addWidget(export_btn)

        reset_btn = QPushButton("Reset")
        reset_btn.setIcon(app_icon("trash", COLORS['danger'], size=13))
        reset_btn.setIconSize(QSize(13, 13))
        reset_btn.setObjectName("reset_btn")
        reset_btn.setFixedHeight(32)
        reset_btn.clicked.connect(self._reset_usage)
        hdr_layout.addWidget(reset_btn)

        outer.addWidget(header)

        # ── Scroll area ─────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        inner.setObjectName("inner_widget")
        self._vbox = QVBoxLayout(inner)
        self._vbox.setContentsMargins(20, 16, 20, 20)
        self._vbox.setSpacing(16)

        self._populate_content()

        self._vbox.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)

        # ── Footer ──────────────────────────────────────────────────────
        footer = QWidget()
        footer.setStyleSheet("background-color: #0e111a; border-top: 1px solid #1e293b;")
        ftr_layout = QHBoxLayout(footer)
        ftr_layout.setContentsMargins(20, 10, 20, 10)
        ftr_layout.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(90)
        close_btn.clicked.connect(self.accept)
        ftr_layout.addWidget(close_btn)
        outer.addWidget(footer)

    # ------------------------------------------------------------------
    # Content population
    # ------------------------------------------------------------------
    def _section_label(self, text):
        """Buat label section header dengan separator."""
        lbl = QLabel(f"<b style='color:#38bdf8; font-size:10pt;'>{text}</b>")
        lbl.setTextFormat(Qt.RichText)
        self._vbox.addWidget(lbl)
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #1e293b;")
        self._vbox.addWidget(sep)

    def _make_card(self):
        """Buat QFrame 'card' dengan shadow styling."""
        card = QFrame()
        card.setObjectName("card")
        return card

    def _populate_content(self):
        from PyQt5.QtWidgets import QProgressBar as _QProgressBar

        provider_usage = self.usage_data.get('provider_usage', {})

        # ── 1. Ringkasan biaya ──────────────────────────────────────────
        self._section_label("Cost Summary")
        cost_card = self._make_card()
        cc_layout = QGridLayout(cost_card)
        cc_layout.setContentsMargins(16, 12, 16, 12)
        cc_layout.setVerticalSpacing(6)

        cost_idr = self.total_cost * self.usd_to_idr_rate

        def _stat(row, label, value, color="#f1f5f9"):
            lbl_w = QLabel(f"<span style='color:#64748b;'>{label}</span>")
            lbl_w.setTextFormat(Qt.RichText)
            val_w = QLabel(f"<b style='color:{color};'>{value}</b>")
            val_w.setTextFormat(Qt.RichText)
            cc_layout.addWidget(lbl_w, row, 0)
            cc_layout.addWidget(val_w, row, 1, Qt.AlignRight)

        _stat(0, "Total Session Cost (USD)", f"${self.total_cost:.6f}", "#4ade80")
        _stat(1, "Estimasi IDR", f"Rp {cost_idr:,.0f}", "#fbbf24")
        _stat(2, "Total Input Tokens", f"{self.total_input_tokens:,}", "#94a3b8")
        _stat(3, "Total Output Tokens", f"{self.total_output_tokens:,}", "#94a3b8")
        _stat(4, "Data tanggal", self.usage_data.get('date', '-'), "#64748b")

        self._vbox.addWidget(cost_card)

        # ── 2. Usage per provider & model ────────────────────────────────
        self._section_label("API Usage per Model")

        # Kumpulkan total daily_count global untuk menentukan skala bar
        all_counts = []
        for _p, models in provider_usage.items():
            for _m, mdata in models.items():
                all_counts.append(mdata.get('daily_count', 0))
        global_max = max(all_counts) if all_counts else 1

        for provider in sorted(provider_usage.keys()):
            models = provider_usage[provider]
            if not models:
                continue

            color = self.PROVIDER_COLORS.get(provider, self.PROVIDER_DEFAULT_COLOR)

            # Header provider
            prov_lbl = QLabel(
                f"<b style='color:{color}; font-size:10pt;'>{provider}</b>"
            )
            prov_lbl.setTextFormat(Qt.RichText)
            self._vbox.addWidget(prov_lbl)

            for model_name in sorted(models.keys()):
                mdata    = models[model_name]
                daily    = mdata.get('daily_count', 0)
                rpm      = mdata.get('minute_count', 0)

                # Cari limits di AI_PROVIDERS
                model_info  = self.ai_providers.get(provider, {}).get(model_name, {})
                limits      = model_info.get('limits', {'rpm': 300, 'rpd': 1000})
                rpd_limit   = limits.get('rpd', 1000)
                rpm_limit   = limits.get('rpm', 60)

                # Display name
                display = (model_info.get('display') or model_name)
                if len(display) > 45:
                    display = display[:42] + "…"

                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(8, 4, 8, 4)
                row_layout.setSpacing(10)

                name_lbl = QLabel(f"<span style='color:#cbd5e1;'>{display}</span>")
                name_lbl.setTextFormat(Qt.RichText)
                name_lbl.setMinimumWidth(230)
                name_lbl.setMaximumWidth(280)
                row_layout.addWidget(name_lbl)

                # Bar RPD
                rpd_pct = int(min(daily / rpd_limit * 100, 100)) if rpd_limit > 0 else 0
                rpd_bar = _QProgressBar()
                rpd_bar.setRange(0, 100)
                rpd_bar.setValue(rpd_pct)
                rpd_bar.setFixedHeight(10)
                rpd_bar.setTextVisible(False)
                chunk_color = "#ef4444" if rpd_pct >= 90 else ("#f59e0b" if rpd_pct >= 60 else color)
                rpd_bar.setStyleSheet(
                    f"QProgressBar {{ background: #1e293b; border: none; border-radius: 4px; }}"
                    f"QProgressBar::chunk {{ background: {chunk_color}; border-radius: 4px; }}"
                )
                row_layout.addWidget(rpd_bar, 1)

                count_lbl = QLabel(
                    f"<span style='color:#94a3b8; font-size:8pt;'>{daily}/{rpd_limit} (daily)</span>"
                )
                count_lbl.setTextFormat(Qt.RichText)
                count_lbl.setMinimumWidth(110)
                row_layout.addWidget(count_lbl)

                self._vbox.addWidget(row_widget)

        # ── 3. Rate Limit Status ─────────────────────────────────────────
        self._section_label("Rate Limit Status (saat ini)")

        has_any = False
        for provider in sorted(provider_usage.keys()):
            models = provider_usage[provider]
            color  = self.PROVIDER_COLORS.get(provider, self.PROVIDER_DEFAULT_COLOR)
            for model_name in sorted(models.keys()):
                mdata  = models[model_name]
                rpm    = mdata.get('minute_count', 0)
                model_info = self.ai_providers.get(provider, {}).get(model_name, {})
                limits     = model_info.get('limits', {'rpm': 300, 'rpd': 1000})
                rpm_limit  = limits.get('rpm', 60)
                daily      = mdata.get('daily_count', 0)
                rpd_limit  = limits.get('rpd', 1000)

                if rpm == 0 and daily == 0:
                    continue   # sembunyikan model yang tidak pernah dipakai

                has_any = True
                display = model_info.get('display') or model_name
                if len(display) > 45:
                    display = display[:42] + "…"

                dot_color = "#22c55e"
                rpm_pct = int(min(rpm / rpm_limit * 100, 100)) if rpm_limit > 0 else 0
                if rpm_pct >= 100:
                    dot_color = "#ef4444"
                elif rpm_pct >= 60:
                    dot_color = "#f59e0b"

                row_w = QWidget()
                rl = QHBoxLayout(row_w)
                rl.setContentsMargins(8, 2, 8, 2)
                rl.setSpacing(10)

                icon_lbl = QLabel()
                icon_lbl.setPixmap(status_dot_pixmap(dot_color, size=10))
                icon_lbl.setAlignment(Qt.AlignCenter)
                icon_lbl.setFixedWidth(20)
                rl.addWidget(icon_lbl)

                nm_lbl = QLabel(f"<span style='color:#cbd5e1;'>{display}</span>")
                nm_lbl.setTextFormat(Qt.RichText)
                nm_lbl.setMinimumWidth(230)
                nm_lbl.setMaximumWidth(280)
                rl.addWidget(nm_lbl)

                rpm_bar = _QProgressBar()
                rpm_bar.setRange(0, 100)
                rpm_bar.setValue(rpm_pct)
                rpm_bar.setFixedHeight(8)
                rpm_bar.setTextVisible(False)
                chunk_c = "#ef4444" if rpm_pct >= 90 else ("#f59e0b" if rpm_pct >= 60 else color)
                rpm_bar.setStyleSheet(
                    f"QProgressBar {{ background: #1e293b; border: none; border-radius: 3px; }}"
                    f"QProgressBar::chunk {{ background: {chunk_c}; border-radius: 3px; }}"
                )
                rl.addWidget(rpm_bar, 1)

                rpm_lbl = QLabel(
                    f"<span style='color:#94a3b8; font-size:8pt;'>{rpm}/{rpm_limit} rpm</span>"
                )
                rpm_lbl.setTextFormat(Qt.RichText)
                rpm_lbl.setMinimumWidth(90)
                rl.addWidget(rpm_lbl)

                self._vbox.addWidget(row_w)

        if not has_any:
            no_lbl = QLabel("<i style='color:#475569;'>Belum ada model yang digunakan sesi ini.</i>")
            no_lbl.setTextFormat(Qt.RichText)
            self._vbox.addWidget(no_lbl)

    # ------------------------------------------------------------------
    # Export CSV
    # ------------------------------------------------------------------
    def _export_csv(self):
        import csv
        import os
        from PyQt5.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Analytics CSV", "session_analytics.csv",
            "CSV Files (*.csv)"
        )
        if not path:
            return

        provider_usage = self.usage_data.get('provider_usage', {})
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Header
                writer.writerow([
                    "Date", "Provider", "Model",
                    "Daily Count", "RPD Limit", "RPD %",
                    "Minute Count (last)", "RPM Limit"
                ])
                date_str = self.usage_data.get('date', '-')
                for provider in sorted(provider_usage.keys()):
                    for model_name in sorted(provider_usage[provider].keys()):
                        mdata = provider_usage[provider][model_name]
                        model_info = self.ai_providers.get(provider, {}).get(model_name, {})
                        limits = model_info.get('limits', {'rpm': 300, 'rpd': 1000})
                        daily = mdata.get('daily_count', 0)
                        rpm   = mdata.get('minute_count', 0)
                        rpd_limit = limits.get('rpd', 1000)
                        rpm_limit = limits.get('rpm', 60)
                        rpd_pct = round(daily / rpd_limit * 100, 2) if rpd_limit > 0 else 0
                        writer.writerow([
                            date_str, provider, model_name,
                            daily, rpd_limit, f"{rpd_pct}%",
                            rpm, rpm_limit
                        ])

                # Summary row
                writer.writerow([])
                writer.writerow(["Total Cost (USD)", f"${self.total_cost:.6f}"])
                writer.writerow(["Estimasi IDR", f"Rp {self.total_cost * self.usd_to_idr_rate:,.0f}"])
                writer.writerow(["Total Input Tokens", self.total_input_tokens])
                writer.writerow(["Total Output Tokens", self.total_output_tokens])

            notify_toast(self, "Export berhasil", f"Analytics berhasil disimpan ke: {path}", kind="success", timeout_ms=5000)
        except Exception as e:
            notify_banner(self, "analytics-export-failed", "Export gagal", f"Gagal menyimpan CSV: {e}", kind="error")

    # ------------------------------------------------------------------
    # Reset usage
    # ------------------------------------------------------------------
    def _reset_usage(self):
        reply = QMessageBox.question(
            self, "Reset Usage Data",
            "Reset semua data usage (daily count, minute count) ke nol?\n"
            "Total cost tidak akan direset.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        provider_usage = self.usage_data.get('provider_usage', {})
        for provider in provider_usage:
            for model_name in provider_usage[provider]:
                provider_usage[provider][model_name]['daily_count'] = 0
                provider_usage[provider][model_name]['minute_count'] = 0

        # Beritahu parent untuk simpan
        if self.parent() and hasattr(self.parent(), 'save_usage_data'):
            self.parent().save_usage_data()

        notify_toast(self, "Reset selesai", "Usage data berhasil direset.", kind="success")
        self.accept()


class FullPageProgressDialog(QDialog):
    """Modal progres Full-Page Translation untuk satu halaman aktif.

    Selama proses berjalan, dialog bersifat modal terhadap window utama sehingga
    navigasi halaman, kanvas, dan daftar file terkunci aman dari race condition.
    """

    cancel_requested = pyqtSignal()

    def __init__(self, parent, page_name):
        super().__init__(parent)
        self.setWindowTitle(FullPageBatchText.SINGLE_DIALOG_TITLE)
        self.setWindowIcon(app_icon("rocket", COLORS['accent'], size=16))
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowSystemMenuHint)
        self.setFixedWidth(480)
        self._finished = False

        self.setStyleSheet(
            f"QDialog {{ background: {COLORS['panel']}; color: {COLORS['text']}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 18)
        layout.setSpacing(10)

        hdr_row = QHBoxLayout()
        hdr_row.setContentsMargins(0, 0, 0, 0)
        hdr_row.setSpacing(8)
        hdr_row.addWidget(icon_label("rocket", COLORS['accent'], size=18))
        title = QLabel(FullPageBatchText.SINGLE_DIALOG_TITLE)
        title.setStyleSheet(f"color: {COLORS['text']}; font-size: 12pt; font-weight: 700; border: none; background: transparent;")
        hdr_row.addWidget(title)
        hdr_row.addStretch(1)
        layout.addLayout(hdr_row)

        self.page_label = QLabel(
            FullPageBatchText.SINGLE_PAGE_FMT.format(name=page_name or "—")
        )
        self.page_label.setStyleSheet(f"color: {COLORS['accent']}; font-size: 10.5pt; font-weight: 600; border: none; background: transparent;")
        self.page_label.setWordWrap(True)
        layout.addWidget(self.page_label)

        hint_lbl = QLabel(FullPageBatchText.SINGLE_LOCK_HINT)
        hint_lbl.setWordWrap(True)
        hint_lbl.setStyleSheet(f"color: {COLORS['muted']}; font-size: 8.5pt; border: none; background: transparent;")
        layout.addWidget(hint_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setStyleSheet(
            f"QProgressBar {{ background: {COLORS['bg']}; border: 1px solid {COLORS['border']}; border-radius: 7px;"
            f" text-align: center; color: {COLORS['text']}; font-size: 8.5pt; }}"
            f"QProgressBar::chunk {{ background: {COLORS['accent']}; border-radius: 6px; }}"
        )
        layout.addWidget(self.progress_bar)

        self.step_label = QLabel(FullPageBatchText.SINGLE_STEP_INIT)
        self.step_label.setWordWrap(True)
        self.step_label.setStyleSheet(f"color: {COLORS['muted']}; font-size: 9pt; font-style: italic; border: none; background: transparent;")
        layout.addWidget(self.step_label)

        self.cancel_btn = QPushButton(FullPageBatchText.DIALOG_CANCEL_BTN)
        self.cancel_btn.setIcon(app_icon("x", COLORS['danger'], size=13))
        self.cancel_btn.setIconSize(QSize(13, 13))
        self.cancel_btn.clicked.connect(self._on_cancel)
        layout.addWidget(self.cancel_btn, 0, Qt.AlignRight)

    def set_progress(self, pct, msg=""):
        try:
            self.progress_bar.setValue(max(0, min(100, int(pct))))
        except (TypeError, ValueError):
            pass
        if msg is not None:
            self.step_label.setText(str(msg))

    def mark_finished(self):
        self._finished = True
        self.cancel_btn.setVisible(False)

    def _on_cancel(self):
        if self._finished:
            return
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText(FullPageBatchText.DIALOG_CANCELLING)
        self.cancel_requested.emit()

    def reject(self):
        # Esc / tombol tutup dialog = minta batal & tunggu worker berhenti aman
        self._on_cancel()


class FullPageBatchProgressDialog(QDialog):
    """Dialog progres batch Full-Page Translation.

    Modal: selama tampil, input ke window utama (canvas, navigasi halaman)
    terblokir sehingga state tidak bisa berubah di tengah pemrosesan batch.
    """

    cancel_requested = pyqtSignal()

    def __init__(self, parent, total_pages):
        super().__init__(parent)
        self.setWindowTitle(FullPageBatchText.DIALOG_TITLE)
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowSystemMenuHint)
        self.setFixedWidth(500)
        self._finished = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 18)
        layout.setSpacing(10)

        title = QLabel(FullPageBatchText.DIALOG_TITLE)
        title.setStyleSheet("color:#e2e8f0; font-size:12pt; font-weight:600; border:none;")
        layout.addWidget(title)

        self.page_label = QLabel(
            FullPageBatchText.DIALOG_PAGE_FMT.format(current=0, total=total_pages, name="—")
        )
        self.page_label.setStyleSheet("color:#38bdf8; font-size:10.5pt; font-weight:600; border:none;")
        self.page_label.setWordWrap(True)
        layout.addWidget(self.page_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, max(1, total_pages))
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setStyleSheet(
            "QProgressBar { background:#0e111a; border:1px solid #1e293b; border-radius:7px;"
            " text-align:center; color:#cbd5e1; font-size:8.5pt; }"
            "QProgressBar::chunk { background:#38bdf8; border-radius:6px; }"
        )
        layout.addWidget(self.progress_bar)

        self.step_label = QLabel(FullPageBatchText.DIALOG_STEP_WAIT)
        self.step_label.setWordWrap(True)
        self.step_label.setStyleSheet("color:#4a5c78; font-size:9pt; font-style:italic; border:none;")
        layout.addWidget(self.step_label)

        self.stats_label = QLabel(
            FullPageBatchText.DIALOG_STATS_FMT.format(done=0, skipped=0, failed=0)
        )
        self.stats_label.setStyleSheet("color:#cbd5e1; font-size:9.5pt; border:none;")
        layout.addWidget(self.stats_label)

        self.cancel_btn = QPushButton(FullPageBatchText.DIALOG_CANCEL_BTN)
        self.cancel_btn.clicked.connect(self._on_cancel)
        layout.addWidget(self.cancel_btn, 0, Qt.AlignRight)

    def set_page(self, current, total, name):
        self.page_label.setText(
            FullPageBatchText.DIALOG_PAGE_FMT.format(current=current, total=total, name=name)
        )

    def set_step(self, msg):
        self.step_label.setText(msg or "")

    def set_done_pages(self, count):
        self.progress_bar.setValue(count)

    def set_stats(self, done, skipped, failed):
        self.stats_label.setText(
            FullPageBatchText.DIALOG_STATS_FMT.format(done=done, skipped=skipped, failed=failed)
        )

    def mark_finished(self):
        self._finished = True
        self.cancel_btn.setVisible(False)

    def _on_cancel(self):
        if self._finished:
            return
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText(FullPageBatchText.DIALOG_CANCELLING)
        self.cancel_requested.emit()

    def reject(self):
        # Esc / close = permintaan batal (worker berhenti di batas halaman),
        # bukan menutup dialog di tengah batch.
        self._on_cancel()
