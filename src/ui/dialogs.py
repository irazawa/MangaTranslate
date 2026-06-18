# Manga OCR & Typeset Tool v14.8.8
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
# 🌟 PyQt5 (dibagi per kategori)
# ==============================
from PyQt5.QtWidgets import (
    QApplication, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget,
    QTextEdit, QScrollArea, QComboBox, QMessageBox, QListWidget, QListWidgetItem,
    QColorDialog, QLineEdit, QDialog, QDialogButtonBox, QCheckBox, QSpinBox,
    QTabWidget, QGroupBox, QGridLayout, QFrame, QSplitter, QToolButton, QFormLayout, QFontComboBox,
    QDoubleSpinBox,
    QMenu, QTableWidget, QTableWidgetItem, QHeaderView, QStackedWidget, QProgressDialog,
    QAbstractItemView
)
from PyQt5.QtGui import (
    QColor, QFont, QTextCharFormat, QTextCursor, QBrush, QTextBlockFormat, QPixmap, QImage
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
from src.ui.texts import SettingsText
from src.ui.theme import settings_center_stylesheet
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
        self.setWindowTitle("OpenRouter Translate Settings")
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

    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
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
        self._initial_translate = copy.deepcopy(SETTINGS.get('translate', {}).get('openrouter', {}))
        self._initial_shortcuts = copy.deepcopy(SETTINGS.get('shortcuts', {}))
        self.shortcut_editors = {}

        self._build_ui()

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

        self.general_tab = self._create_general_tab()
        self.cleanup_tab = self._create_cleanup_tab()
        self.translation_tab = self._create_translation_tab()
        self.shortcuts_tab = self._create_shortcuts_tab()
        self.api_tab = self._create_api_tab()
        self.ocr_plugins_tab = self._create_ocr_plugins_tab()
        self.media_tools_tab = self._create_media_tools_tab()
        self.glossary_tab = self._create_glossary_tab()

        for page in (self.general_tab, self.cleanup_tab,
                     self.translation_tab, self.shortcuts_tab, self.api_tab, self.ocr_plugins_tab,
                     self.media_tools_tab, self.glossary_tab):
            self._pages.addWidget(page)

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

        # Wire nav selection → page switch
        self._nav_list.currentRowChanged.connect(self._on_nav_changed)
        self._nav_list.setCurrentRow(0)

        self._apply_settings_styles()

    def _on_nav_changed(self, index):
        """Switch stacked page when user clicks nav item."""
        if 0 <= index < self._pages.count():
            self._pages.setCurrentIndex(index)

    def _nav_index_for_key(self, key: str):
        normalized = str(key or "").strip().lower()
        aliases = {
            "apis": "api",
            "keys": "api",
            "shortcut": "shortcuts",
            "ocr": "ocr_plugins",
            "plugins": "ocr_plugins",
            "media": "media_tools",
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
        text_col.addWidget(lbl)
        if desc:
            dlbl = QLabel(desc)
            dlbl.setObjectName("settings-option-desc")
            dlbl.setWordWrap(True)
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
        as_card = QGroupBox("💾  Autosave")
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
        out_card = QGroupBox("🖼  Output")
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
        def_card = QGroupBox("📋  Default Presets")
        def_card.setObjectName("settings-card")
        def_vbox = QVBoxLayout(def_card)
        def_vbox.setSpacing(4)
        def_vbox.setContentsMargins(0, 8, 0, 8)

        # Default OCR Language
        self.default_ocr_combo = QComboBox()
        self.default_ocr_combo.setFixedWidth(180)
        if hasattr(self.main_window, 'ocr_lang_combo'):
            for i in range(self.main_window.ocr_lang_combo.count()):
                self.default_ocr_combo.addItem(self.main_window.ocr_lang_combo.itemText(i))
        current_ocr = SETTINGS.get('general', {}).get('default_ocr_lang', 'Japanese (Manga-OCR)')
        self.default_ocr_combo.setCurrentText(current_ocr)
        def_vbox.addWidget(self._make_option_row(
            "Default OCR Language", "Select the default language used for OCR.",
            self.default_ocr_combo))

        # Default AI-Only Translate
        self.default_ai_only_checkbox = QCheckBox()
        current_ai_only = bool(SETTINGS.get('general', {}).get('default_ai_only_translate', False))
        self.default_ai_only_checkbox.setChecked(current_ai_only)
        def_vbox.addWidget(self._make_option_row(
            "Default AI-Only Translate", "Whether to enable AI-Only Translation mode by default.",
            self.default_ai_only_checkbox))

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
        ec_card = QGroupBox("🚨  Emergency Close")
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
            meta.get("title", "Cleanup"),
            meta.get("subtitle", ""),
        ))

        card = QGroupBox("🧹  Text Defaults")
        card.setObjectName("settings-card")
        card_vbox = QVBoxLayout(card)
        card_vbox.setSpacing(4)
        card_vbox.setContentsMargins(0, 8, 0, 8)

        cleanup_cfg = SETTINGS.get('cleanup', {})

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
        self.remove_ai_temp_checkbox.setToolTip("Delete temp/ debug files after each successful AI OCR/MOFRL run.")
        self.remove_ai_temp_checkbox.setChecked(bool(cleanup_cfg.get('remove_ai_temp_files', False)))
        card_vbox.addWidget(self._make_option_row(
            "Remove AI temp files",
            "Delete temporary debug files after AI OCR & MOFRL runs.",
            self.remove_ai_temp_checkbox))

        layout.addWidget(card)
        layout.addStretch(1)
        return page

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
                clear_btn.setText("✕")
                clear_btn.setToolTip("Clear shortcut")
                clear_btn.clicked.connect(editor.clear_sequence)
                row_layout.addWidget(clear_btn)

                default_btn = QToolButton()
                default_btn.setText("↺")
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

    def _apply_settings_styles(self):
        self.setStyleSheet(settings_center_stylesheet())

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
    def _create_media_tools_tab(self):
        meta = self._page_meta("media_tools")
        page, layout = self._make_page_scroll()
        layout.addWidget(self._make_page_header(
            meta.get("title", "Media Tools"),
            meta.get("subtitle", ""),
        ))

        card = QGroupBox("YouTube & FFmpeg Dependencies")
        card.setObjectName("settings-card")
        card_vbox = QVBoxLayout(card)
        card_vbox.setSpacing(10)
        card_vbox.setContentsMargins(16, 12, 16, 12)

        note = QLabel(
            "These dependencies are no longer checked or installed during app startup. "
            "Use this installer when you want YouTube media loading, playlist extraction, "
            "or FFmpeg-based video tools."
        )
        note.setWordWrap(True)
        note.setObjectName("settings-option-desc")
        card_vbox.addWidget(note)

        self.media_dependency_labels = {}
        for key, label in (
            ("yt_dlp", "yt-dlp"),
            ("yt_dlp_ejs", "yt-dlp-ejs"),
            ("ffmpeg", "FFmpeg"),
            ("deno", "Deno"),
        ):
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            status_label = QLabel()
            status_label.setObjectName("settings-option-desc")
            row.addStretch(1)
            row.addWidget(status_label)
            self.media_dependency_labels[key] = status_label
            card_vbox.addLayout(row)

        button_row = QHBoxLayout()
        self.refresh_media_deps_btn = QPushButton("Refresh Status")
        self.refresh_media_deps_btn.clicked.connect(self._refresh_media_dependency_status)
        self.install_media_deps_btn = QPushButton("Install Media Tools")
        self.install_media_deps_btn.setObjectName("settings-action-btn")
        self.install_media_deps_btn.clicked.connect(self._run_media_dependencies_installer)
        button_row.addWidget(self.refresh_media_deps_btn)
        button_row.addWidget(self.install_media_deps_btn)
        button_row.addStretch(1)
        card_vbox.addLayout(button_row)

        layout.addWidget(card)
        layout.addStretch(1)
        self._refresh_media_dependency_status()
        return page

    def _refresh_media_dependency_status(self):
        status = get_media_dependency_status()
        labels = getattr(self, 'media_dependency_labels', {})
        for key, ready in status.items():
            label = labels.get(key)
            if label is None:
                continue
            if ready:
                label.setText("Installed")
                label.setStyleSheet("color: #4ade80; font-weight: bold;")
            else:
                label.setText("Not installed")
                label.setStyleSheet("color: #facc15; font-weight: bold;")

    def _run_media_dependencies_installer(self):
        ret = QMessageBox.question(
            self,
            "Install Media Tools",
            "Install optional YouTube/Media dependencies now?\n\n"
            "This may download yt-dlp, yt-dlp-ejs, FFmpeg, and Deno, so it can take a while.",
            QMessageBox.Yes | QMessageBox.No
        )
        if ret != QMessageBox.Yes:
            return

        self.install_media_deps_btn.setEnabled(False)
        self.refresh_media_deps_btn.setEnabled(False)

        progress_dlg = QProgressDialog("Installing optional media tools...", None, 0, 0, self)
        progress_dlg.setWindowModality(Qt.WindowModal)
        progress_dlg.setWindowTitle("Installing Media Tools")
        progress_dlg.show()

        worker = MediaDependenciesInstallWorker()

        def on_progress(status):
            progress_dlg.setLabelText(status)

        def on_finished(success, message):
            progress_dlg.close()
            self.install_media_deps_btn.setEnabled(True)
            self.refresh_media_deps_btn.setEnabled(True)
            self._refresh_media_dependency_status()
            if success:
                notify_toast(self, "Media tools ready", message, kind="success", timeout_ms=5000)
            else:
                notify_banner(self, "media-tools-install-failed", "Media tools install failed", message, kind="error")

        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.finished.connect(worker.deleteLater)
        worker.start()
        self._media_dependencies_worker = worker

    def _create_glossary_tab(self):
        meta = self._page_meta("glossary")
        page, layout = self._make_page_scroll()
        layout.addWidget(self._make_page_header(
            meta.get("title", "Glossary"),
            meta.get("subtitle", "")
        ))

        card = QGroupBox("📖  Term Pairs (Source → Target)")
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
        remove_btn = QPushButton("− Remove Selected")
        remove_btn.clicked.connect(self._on_glossary_remove)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch(1)
        card_vbox.addLayout(btn_row)

        layout.addWidget(card)

        # Info box
        info_card = QGroupBox("ℹ  How it works")
        info_card.setObjectName("settings-card")
        info_vbox = QVBoxLayout(info_card)
        info_label = QLabel(
            "Setiap pasangan term yang kamu tambahkan akan diinjeksikan ke dalam prompt AI "
            "saat menerjemahkan. AI akan selalu menggunakan 'Target Term' untuk setiap "
            "kemunculan 'Source Term' dalam teks.\n\n"
            "Contoh:\n"
            "  Source: 煉獄杏寿郎  →  Target: Rengoku Kyojuro\n"
            "  Source: 無惨  →  Target: Muzan\n"
            "  Source: 全集中  →  Target: Total Concentration"
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
        # Save OCR plugins config
        ocr_plugins_cfg = SETTINGS.setdefault('ocr_plugins', {})
        for name, checkbox in self.plugin_checkboxes.items():
            ocr_plugins_cfg[name] = bool(checkbox.isChecked())

        api_export = self.api_panel.export_settings()
        if api_export is None:
            warnings = "\n".join(self.api_panel.validation_messages())
            details = f"\n\n{warnings}" if warnings else ""
            notify_banner(self, "settings-api-validation", "API settings", f"Please fix the highlighted API settings issues before saving.{details}", kind="warning")
            self.set_active_tab("api")
            return False

        openrouter_settings = self.openrouter_panel.export_settings()

        autosave_enabled = bool(self.autosave_checkbox.isChecked())
        autosave_interval_ms = int(self.autosave_interval_spin.value() * 1000)
        self._apply_autosave_settings(autosave_enabled, autosave_interval_ms)

        gen_cfg = SETTINGS.setdefault('general', {})
        gen_cfg['save_format'] = self.save_format_combo.currentText()
        gen_cfg['save_quality'] = self.save_quality_spin.value()
        gen_cfg['default_ocr_lang'] = self.default_ocr_combo.currentText()
        gen_cfg['default_ai_only_translate'] = bool(self.default_ai_only_checkbox.isChecked())
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
        # Persist new AI temp cleanup option
        try:
            cleanup_cfg['remove_ai_temp_files'] = bool(self.remove_ai_temp_checkbox.isChecked())
        except Exception:
            cleanup_cfg['remove_ai_temp_files'] = bool(cleanup_cfg.get('remove_ai_temp_files', False))

        shortcut_settings = {}
        for key, editor in self.shortcut_editors.items():
            sequence = (editor.sequence() or '').strip()
            default_seq = DEFAULT_SHORTCUTS.get(key, '')
            if not sequence:
                # Only persist blanks when overriding a default binding
                if default_seq:
                    shortcut_settings[key] = ''
            elif sequence != default_seq:
                shortcut_settings[key] = sequence

        shortcuts_changed = shortcut_settings != self._initial_shortcuts

        SETTINGS.setdefault('translate', {})
        SETTINGS['translate']['openrouter'] = copy.deepcopy(openrouter_settings)
        SETTINGS['apis'] = copy.deepcopy(api_export.get('apis', {}))
        SETTINGS['ocr'] = copy.deepcopy(api_export.get('ocr', {}))
        SETTINGS['tesseract'] = copy.deepcopy(api_export.get('tesseract', {}))
        SETTINGS['shortcuts'] = shortcut_settings

        # Simpan Glossary
        if hasattr(self, '_glossary_table'):
            SETTINGS['glossary'] = self._get_glossary_from_table()

        save_settings(SETTINGS)

        # Hot-apply custom default values to main window
        if hasattr(self.main_window, 'apply_defaults_from_settings'):
            try:
                self.main_window.apply_defaults_from_settings()
            except Exception as e:
                print(f"Error applying default presets: {e}")

        try:
            refresh_api_clients()
        except Exception:
            pass

        # Refresh OpenAI availability flag after API clients are recreated
        try:
            self.main_window.is_openai_available = (openai is not None and openai_client is not None)
        except Exception:
            pass

        if hasattr(self.main_window, 'reload_shortcuts'):
            try:
                self.main_window.reload_shortcuts()
            except Exception:
                pass

        if hasattr(self.main_window, 'populate_ocr_languages'):
            try:
                self.main_window.populate_ocr_languages()
            except Exception:
                pass

        if hasattr(self.main_window, 'populate_ai_models'):
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
        ):
            status_parts.append("Cleanup defaults updated")
        if openrouter_settings != self._initial_translate:
            status_parts.append("Translation settings updated")
        if any(api_export.get(key, {}) != self._initial_api.get(key, {}) for key in ('apis', 'ocr', 'tesseract')):
            status_parts.append("API settings updated")
        if (autosave_enabled != self._initial_autosave_enabled) or (abs(autosave_interval_ms - self._initial_autosave_interval) > 1):
            status_parts.append("Autosave preferences updated")
        if shortcuts_changed:
            status_parts.append("Shortcuts updated")

        if status_parts and hasattr(self.main_window, 'statusBar'):
            try:
                self.main_window.statusBar().showMessage(" | ".join(status_parts), 4000)
            except Exception:
                pass

        self._initial_autosave_enabled = autosave_enabled
        self._initial_autosave_interval = autosave_interval_ms
        self._initial_cleanup = copy.deepcopy(cleanup_cfg)
        self._initial_api = {
            'apis': copy.deepcopy(SETTINGS.get('apis', {})),
            'ocr': copy.deepcopy(SETTINGS.get('ocr', {})),
            'tesseract': copy.deepcopy(SETTINGS.get('tesseract', {})),
        }
        self._initial_translate = copy.deepcopy(SETTINGS.get('translate', {}).get('openrouter', {}))
        self._initial_shortcuts = copy.deepcopy(shortcut_settings)

        if close_dialog:
            self.accept()
        else:
            notify_toast(self, "Settings applied", "Changes saved without closing Settings.", kind="success")
        return True

    def _create_ocr_plugins_tab(self):
        meta = self._page_meta("ocr_plugins")
        page, layout = self._make_page_scroll()
        layout.addWidget(self._make_page_header(
            meta.get("title", "OCR Plugins Manager"),
            meta.get("subtitle", ""),
        ))

        # ── 1. Modular OCR Plugins ────────────────────────────────────────
        card = QGroupBox("🔌  OCR Engines")
        card.setObjectName("settings-card")
        card_vbox = QVBoxLayout(card)
        card_vbox.setSpacing(4)
        card_vbox.setContentsMargins(0, 8, 0, 8)

        plugins_cfg = SETTINGS.get('ocr_plugins', {})
        self.plugin_checkboxes = {}
        
        # EasyOCR
        self.easyocr_checkbox = QCheckBox()
        self.easyocr_checkbox.setChecked(bool(plugins_cfg.get('EasyOCR', True)))
        self.plugin_checkboxes['EasyOCR'] = self.easyocr_checkbox
        card_vbox.addWidget(self._make_option_row(
            "EasyOCR",
            "Local deep learning OCR. Supports multiple languages offline.",
            self.easyocr_checkbox))

        # PaddleOCR
        self.paddle_checkbox = QCheckBox()
        self.paddle_checkbox.setChecked(bool(plugins_cfg.get('PaddleOCR', True)))
        self.plugin_checkboxes['PaddleOCR'] = self.paddle_checkbox
        card_vbox.addWidget(self._make_option_row(
            "PaddleOCR",
            "Ultra-accurate local Chinese/Japanese/English OCR.",
            self.paddle_checkbox))

        # DocTR
        self.doctr_checkbox = QCheckBox()
        self.doctr_checkbox.setChecked(bool(plugins_cfg.get('DocTR', False)))
        self.plugin_checkboxes['DocTR'] = self.doctr_checkbox
        card_vbox.addWidget(self._make_option_row(
            "DocTR",
            "Document Text Recognition engine. Heavy, recommended for advanced users.",
            self.doctr_checkbox))

        # RapidOCR
        self.rapid_checkbox = QCheckBox()
        self.rapid_checkbox.setChecked(bool(plugins_cfg.get('RapidOCR', False)))
        self.plugin_checkboxes['RapidOCR'] = self.rapid_checkbox
        card_vbox.addWidget(self._make_option_row(
            "RapidOCR",
            "Fast, lightweight local OCR engine.",
            self.rapid_checkbox))

        layout.addWidget(card)

        # ── 2. Tesseract Auto-Installer ────────────────────────────────────
        tess_card = QGroupBox("📦  Tesseract Auto-Installer")
        tess_card.setObjectName("settings-card")
        tess_vbox = QVBoxLayout(tess_card)
        tess_vbox.setSpacing(10)
        tess_vbox.setContentsMargins(16, 12, 16, 12)

        # Status row
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("Current Status:"))
        
        from src.core.config import IS_TESSERACT_AVAILABLE, TESSERACT_PATH
        self.tess_status_label = QLabel()
        if IS_TESSERACT_AVAILABLE:
            self.tess_status_label.setText("🟢 Installed & Ready")
            self.tess_status_label.setStyleSheet("color: #4ade80; font-weight: bold;")
        else:
            self.tess_status_label.setText("🔴 Not Found")
            self.tess_status_label.setStyleSheet("color: #f87171; font-weight: bold;")
        status_layout.addWidget(self.tess_status_label)
        status_layout.addStretch()
        tess_vbox.addLayout(status_layout)

        # Path display
        self.tess_path_label = QLabel(f"Path: {TESSERACT_PATH if TESSERACT_PATH else 'None'}")
        self.tess_path_label.setStyleSheet("color: #94a3b8; font-size: 9pt;")
        self.tess_path_label.setWordWrap(True)
        tess_vbox.addWidget(self.tess_path_label)

        # Installer button
        self.install_tess_btn = QPushButton("🚀 Auto-Install Tesseract")
        self.install_tess_btn.setObjectName("settings-action-btn")
        self.install_tess_btn.clicked.connect(self._run_tesseract_installer)
        tess_vbox.addWidget(self.install_tess_btn)

        layout.addWidget(tess_card)

        # ── 3. Tesseract Language Models ──────────────────────────────────
        lang_card = QGroupBox("🌐  Tesseract Language Models")
        lang_card.setObjectName("settings-card")
        lang_vbox = QVBoxLayout(lang_card)
        lang_vbox.setSpacing(8)
        lang_vbox.setContentsMargins(16, 12, 16, 12)

        # Help tip
        tip_lbl = QLabel("Manage language models for local Tesseract OCR offline processing.")
        tip_lbl.setStyleSheet("color: #94a3b8; font-size: 9.5pt;")
        lang_vbox.addWidget(tip_lbl)

        # Table of models
        self.lang_table = QTableWidget()
        self.lang_table.setColumnCount(3)
        self.lang_table.setHorizontalHeaderLabels(["Language", "Code", "Actions"])
        self.lang_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.lang_table.setFixedHeight(220)
        self.lang_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.lang_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        # Style header explicitly to ensure high-contrast Obsidian dark theme style
        self.lang_table.horizontalHeader().setStyleSheet("QHeaderView::section { background-color: #0f131c; color: #cbd5e1; padding: 4px; border: 1px solid #1f2b36; }")
        self.lang_table.setStyleSheet("QTableWidget { background-color: #0c121d; border: 1px solid #1f2b36; border-radius: 8px; } QTableWidget::item { color: #cbd5e1; }")
        
        self._languages_list = [
            ("Japanese (Horizontal)", "jpn"),
            ("Japanese (Vertical)", "jpn_vert"),
            ("English", "eng"),
            ("Chinese Simplified", "chi_sim"),
            ("Chinese Traditional", "chi_tra"),
            ("Korean", "kor"),
            ("Korean (Vertical)", "kor_vert"),
            ("French", "fra"),
            ("German", "deu"),
            ("Spanish", "spa"),
            ("Indonesian", "ind")
        ]
        
        self._refresh_tesseract_languages_table()
        lang_vbox.addWidget(self.lang_table)

        layout.addWidget(lang_card)
        layout.addStretch(1)
        return page

    def _refresh_tesseract_languages_table(self):
        self.lang_table.setRowCount(0)
        self.lang_table.setRowCount(len(self._languages_list))
        
        writable_path = get_writable_tessdata_path()
        system_path = get_tessdata_path()
        
        for idx, (lang_name, lang_code) in enumerate(self._languages_list):
            self.lang_table.setItem(idx, 0, QTableWidgetItem(lang_name))
            self.lang_table.setItem(idx, 1, QTableWidgetItem(lang_code))
            
            # Check if file exists in system or writable path
            file_exists = False
            if writable_path:
                file_exists = os.path.exists(os.path.join(writable_path, f"{lang_code}.traineddata"))
            if not file_exists and system_path:
                file_exists = os.path.exists(os.path.join(system_path, f"{lang_code}.traineddata"))
            
            if file_exists:
                uninstall_btn = QPushButton("🗑 Uninstall")
                uninstall_btn.setStyleSheet("background: #dc2626; color: white; border: none; border-radius: 4px; padding: 4px 8px; font-weight: normal;")
                uninstall_btn.clicked.connect(lambda checked=False, c=lang_code: self._uninstall_lang_model(c))
                self.lang_table.setCellWidget(idx, 2, uninstall_btn)
            else:
                download_btn = QPushButton("📥 Download")
                download_btn.setStyleSheet("background: #1f6fb5; color: white; border: none; border-radius: 4px; padding: 4px 8px; font-weight: normal;")
                download_btn.clicked.connect(lambda checked=False, c=lang_code: self._download_lang_model(c))
                self.lang_table.setCellWidget(idx, 2, download_btn)

    def _uninstall_lang_model(self, lang_code):
        ret = QMessageBox.question(
            self, "Uninstall Language Model",
            f"Are you sure you want to delete the '{lang_code}' language model file to free up disk space?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ret == QMessageBox.Yes:
            success, msg = uninstall_tessdata_lang(lang_code)
            if success:
                notify_toast(self, "Success", msg, kind="success")
                self._refresh_tesseract_languages_table()
                if hasattr(self.main_window, 'populate_ocr_languages'):
                    self.main_window.populate_ocr_languages()
            else:
                notify_banner(self, "tessdata-uninstall-failed", "Error", msg, kind="error")

    def _download_lang_model(self, lang_code):
        writable_path = get_writable_tessdata_path()
        if not writable_path:
            notify_banner(self, "tessdata-path-missing", "Error", "Could not locate a writable tessdata directory.", kind="error")
            return
            
        progress_dlg = QProgressDialog("Downloading language model from GitHub...", "Cancel", 0, 100, self)
        progress_dlg.setWindowModality(Qt.WindowModal)
        progress_dlg.setWindowTitle("Downloading...")
        progress_dlg.setAutoClose(True)
        progress_dlg.show()
        
        worker = TessdataDownloadWorker(lang_code, writable_path)
        
        def on_progress(downloaded, total):
            if total > 0:
                pct = int(downloaded * 100 / total)
                progress_dlg.setValue(pct)
                progress_dlg.setLabelText(f"Downloading '{lang_code}': {pct}% ({downloaded // 1024} KB / {total // 1024} KB)")
            
        def on_finished(success, message):
            progress_dlg.close()
            if success:
                notify_toast(self, "Download complete", f"Successfully downloaded '{lang_code}' language model.", kind="success")
                self._refresh_tesseract_languages_table()
                if hasattr(self.main_window, 'populate_ocr_languages'):
                    self.main_window.populate_ocr_languages()
            else:
                notify_banner(self, "tessdata-download-failed", "Download failed", f"Failed to download language model: {message}", kind="error")
                
        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        progress_dlg.canceled.connect(worker.terminate)
        
        worker.start()
        self._active_download_worker = worker

    def _run_tesseract_installer(self):
        self.install_tess_btn.setEnabled(False)
        self.install_tess_btn.setText("Installing Tesseract...")
        
        progress_dlg = QProgressDialog("Running Tesseract Auto-Installer...", None, 0, 0, self)
        progress_dlg.setWindowModality(Qt.WindowModal)
        progress_dlg.setWindowTitle("Installing...")
        progress_dlg.show()
        
        worker = TesseractInstallWorker()
        
        def on_progress(status):
            progress_dlg.setLabelText(status)
            
        def on_finished(success, path_or_err):
            progress_dlg.close()
            self.install_tess_btn.setEnabled(True)
            self.install_tess_btn.setText("🚀 Auto-Install Tesseract")
            if success:
                notify_toast(self, "Success", f"Tesseract successfully installed. Path: {path_or_err}", kind="success", timeout_ms=5000)
                self.tess_status_label.setText("🟢 Installed & Ready")
                self.tess_status_label.setStyleSheet("color: #4ade80; font-weight: bold;")
                self.tess_path_label.setText(f"Path: {path_or_err}")
                
                from src.core.config import SETTINGS, save_settings, reload_tesseract_availability
                SETTINGS.setdefault('tesseract', {})['path'] = path_or_err
                SETTINGS.setdefault('tesseract', {})['auto_detected'] = True
                save_settings(SETTINGS)
                reload_tesseract_availability()
                
                sync_tessdata_files()
                self._refresh_tesseract_languages_table()
                
                if hasattr(self.main_window, 'populate_ocr_languages'):
                    self.main_window.populate_ocr_languages()
            else:
                notify_banner(self, "tesseract-install-failed", "Error", f"Failed to install Tesseract: {path_or_err}", kind="error")
                
        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.start()
        self._active_install_worker = worker

        self.accept()

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


class AdvancedTextEditDialog(QDialog):
    EFFECT_OPTIONS = [
        ("None", "none"),
        ("Curved", "curved"),
        ("Wavy", "wavy"),
        ("Jagged Shout", "jagged"),
        ("Arc (Bended)", "arc"),
        ("Arch (Gate)", "arch"),
        ("Flag (Wave)", "flag"),
    ]
    ALIGN_OPTIONS = [
        ("Center", Qt.AlignHCenter),
        ("Left", Qt.AlignLeft),
        ("Right", Qt.AlignRight),
        ("Justify", Qt.AlignJustify),
    ]
    EMOJI_PRESETS = [
        ("Heart", "❤"),
        ("Heart1", "♥︎"),
        ("Heart2", "♡"),
        ("Heart3", "❤"),
        ("Heart3", "ㅤ♡ㅤ"),
        ("Sparkle", "✨"),
        ("Star", "★"),
        ("Music", "♪"),
        ("Shock", "⁉"),
        ("Sweat", "💦"),
        ("Smile", "😊"),
        ("Angry", "😠"),
        ("Glow", "glow"),
    ]

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

    def __init__(self, parent=None, area=None, font_manager=None):
        super().__init__(parent)
        self.area = area
        self.font_manager = font_manager
        self.result = None
        self._manual_text_color_changed = False
        self.setWindowTitle("Advanced Text Editor")
        self.setModal(True)
        # Restore previous size if available, else use default responsive size
        saved_size = SETTINGS.get('ui', {}).get('advanced_editor_size')
        if saved_size and len(saved_size) == 2 and saved_size[0] > 900:
            try:
                self.resize(int(saved_size[0]), int(saved_size[1]))
            except Exception:
                self._apply_default_size()
        else:
            self._apply_default_size()


        self.setObjectName("AdvancedTextEditDialog")
        self.setStyleSheet("""
            QDialog#AdvancedTextEditDialog {
                background: #0f1624;
                color: #e8eef7;
                font-size: 10.5pt;
            }
            QGroupBox {
                background: rgba(255,255,255,0.03);
                border: 1px solid #1f2b36;
                border-radius: 12px;
                margin-top: 12px;
                padding-top: 14px;
            }
            QGroupBox::title {
                color: #9fc3f5;
                padding: 0 8px;
                font-weight: 600;
            }
            QLabel { color: #e8eef7; }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
                background: #0c121d;
                border: 1px solid #1f2b36;
                border-radius: 8px;
                padding: 6px 8px;
            }
            QPushButton, QToolButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1f6fb5, stop:1 #2c8ae6);
                color: #e8eef7;
                border: 1px solid #2b6aa1;
                border-radius: 8px;
                padding: 7px 12px;
                font-weight: 600;
            }
            QPushButton:hover, QToolButton:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #2a7fcb, stop:1 #3b9af3); }
            QPushButton:disabled, QToolButton:disabled {
                background: #182131;
                color: #7f8a96;
                border-color: #1f2b36;
            }
            QTextEdit {
                border-radius: 12px;
                padding: 10px;
                line-height: 1.4;
            }
            #ate-hero {
                border: 1px solid #1f2b36;
                border-radius: 14px;
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #132036, stop:1 #0c1729);
                padding: 10px;
            }
            #ate-title { font-size: 16px; font-weight: 700; color: #eaf3ff; }
            #ate-subtitle { color: #8fa6c5; }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(10)

        hero = QFrame()
        hero.setObjectName("ate-hero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(14, 12, 14, 12)
        hero_layout.setSpacing(4)
        title = QLabel("Advanced Text Editor")
        title.setObjectName("ate-title")
        subtitle = QLabel("Fine-tune text formatting. Select a range to style only that portion or press Ctrl+A to target the whole bubble.")
        subtitle.setObjectName("ate-subtitle")
        subtitle.setWordWrap(True)
        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        main_layout.addWidget(hero)

        toolbar_layout = QHBoxLayout()
        # Font group selector for the advanced editor (if the main application provided groups)
        self.font_group_combo = QComboBox()
        self.font_group_combo.setMinimumWidth(160)
        self.font_group_combo.addItem("All")
        toolbar_layout.addWidget(self.font_group_combo)
        self.font_combo = QComboBox()
        self.font_combo.setMinimumWidth(220)
        from src.ui.widgets import FontDelegate
        self.font_combo.setItemDelegate(FontDelegate(self.font_manager, self.font_combo))
        toolbar_layout.addWidget(self.font_combo)

        self.font_preview = QLabel("AaBb123")
        self.font_preview.setFixedWidth(140)
        self.font_preview.setAlignment(Qt.AlignCenter)
        self.font_preview.setStyleSheet("border: 1px solid #1f2b3b; border-radius: 6px; padding: 4px;")
        toolbar_layout.addWidget(self.font_preview)

        self.font_size_spin = QDoubleSpinBox(); self.font_size_spin.setRange(4.0, 220.0); self.font_size_spin.setDecimals(1); self.font_size_spin.setSingleStep(1.0); self.font_size_spin.setSuffix(" pt")
        toolbar_layout.addWidget(self.font_size_spin)

        self.bold_button = QToolButton(); self.bold_button.setText("B"); self.bold_button.setCheckable(True); self.bold_button.setToolTip("Toggle bold")
        toolbar_layout.addWidget(self.bold_button)

        self.italic_button = QToolButton(); self.italic_button.setText("I"); self.italic_button.setCheckable(True); self.italic_button.setToolTip("Toggle italic")
        toolbar_layout.addWidget(self.italic_button)

        self.underline_button = QToolButton(); self.underline_button.setText("U"); self.underline_button.setCheckable(True); self.underline_button.setToolTip("Toggle underline")
        toolbar_layout.addWidget(self.underline_button)

        self.color_button = QToolButton(); self.color_button.setText("Color"); self.color_button.setToolTip("Change text color")
        toolbar_layout.addWidget(self.color_button)

        toolbar_layout.addSpacing(10)
        self.ai_translate_btn = QPushButton("AI Translate")
        self.ai_translate_btn.setToolTip("Translate currently selected text (or all text) using active AI model")
        self.ai_translate_btn.clicked.connect(self._on_ai_translate_clicked)
        toolbar_layout.addWidget(self.ai_translate_btn)

        self.recent_translations_btn = QPushButton("📋 Recent")
        self.recent_translations_btn.setToolTip("Apply a recently generated translation to this text area")
        self.recent_translations_btn.clicked.connect(self._show_recent_menu)
        toolbar_layout.addWidget(self.recent_translations_btn)

        # After creating widgets, populate group combo if possible and hook handlers
        try:
            main_win = self.parent()
            if getattr(main_win, 'font_groups', None):
                # Clear default 'All' then add groups
                self.font_group_combo.clear(); self.font_group_combo.addItem('All')
                for g in main_win.font_groups.keys():
                    self.font_group_combo.addItem(g)
            # connect group changes to a local handler
            self.font_group_combo.currentTextChanged.connect(self._on_dialog_font_group_changed)
        except Exception:
            pass

        # Populate the font combo initially (respecting any selected group)
        try:
            sel = self.font_group_combo.currentText()
            if sel == 'All':
                self._populate_dialog_fonts(None)
            else:
                self._populate_dialog_fonts(sel)
        except Exception:
            pass

        self.emoji_button = QToolButton(); self.emoji_button.setText("Emotes"); self.emoji_button.setToolTip("Insert emoticons or symbols")
        self.emoji_menu = QMenu(self)
        for label, symbol in self.EMOJI_PRESETS:
            action = self.emoji_menu.addAction(f"{label} {symbol}")
            action.triggered.connect(lambda checked=False, s=symbol: self._insert_emoji(s))
        self.emoji_button.setMenu(self.emoji_menu); self.emoji_button.setPopupMode(QToolButton.InstantPopup)
        toolbar_layout.addWidget(self.emoji_button)

        toolbar_layout.addStretch()

        # Scrollable container so the bottom buttons stay reachable on smaller screens
        content_scroll = QScrollArea()
        content_scroll.setWidgetResizable(True)
        content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        content_layout.addLayout(toolbar_layout)

        self.text_edit = QTextEdit(); self.text_edit.setAcceptRichText(True); self.text_edit.setMinimumHeight(240)
        content_layout.addWidget(self.text_edit, 1)
        self._outline_color = self.area.get_text_outline_color() if hasattr(self.area, 'get_text_outline_color') else QColor('#000000')
        self._last_text_cursor = QTextCursor(self.text_edit.document())
        self.text_edit.cursorPositionChanged.connect(self._remember_cursor_state)
        self.text_edit.cursorPositionChanged.connect(self._sync_toolbar_from_cursor)

        layout_group = QGroupBox("Layout & Effects")
        layout_grid = QGridLayout(layout_group)

        self.orientation_combo = QComboBox(); self.orientation_combo.addItems(["Horizontal", "Vertical"])
        layout_grid.addWidget(QLabel("Orientation:"), 0, 0); layout_grid.addWidget(self.orientation_combo, 0, 1)

        self.effect_combo = QComboBox()
        for label, value in self.EFFECT_OPTIONS:
            self.effect_combo.addItem(label, value)
        layout_grid.addWidget(QLabel("Effect:"), 0, 2); layout_grid.addWidget(self.effect_combo, 0, 3)

        self.effect_intensity_spin = QDoubleSpinBox(); self.effect_intensity_spin.setRange(0.0, 300.0); self.effect_intensity_spin.setDecimals(1); self.effect_intensity_spin.setSingleStep(5.0)
        layout_grid.addWidget(QLabel("Effect Strength:"), 1, 0); layout_grid.addWidget(self.effect_intensity_spin, 1, 1)

        self.alignment_combo = QComboBox()
        for label, _ in self.ALIGN_OPTIONS:
            self.alignment_combo.addItem(label)
        layout_grid.addWidget(QLabel("Alignment:"), 1, 2); layout_grid.addWidget(self.alignment_combo, 1, 3)

        self.line_spacing_spin = QDoubleSpinBox(); self.line_spacing_spin.setRange(0.6, 3.0); self.line_spacing_spin.setSingleStep(0.1); self.line_spacing_spin.setValue(1.0)
        layout_grid.addWidget(QLabel("Line Spacing:"), 2, 0); layout_grid.addWidget(self.line_spacing_spin, 2, 1)

        self.char_spacing_spin = QDoubleSpinBox(); self.char_spacing_spin.setRange(50.0, 400.0); self.char_spacing_spin.setSingleStep(5.0); self.char_spacing_spin.setSuffix(" %")
        layout_grid.addWidget(QLabel("Character Spacing:"), 2, 2); layout_grid.addWidget(self.char_spacing_spin, 2, 3)

        self.smart_fit_checkbox = QCheckBox("Smart Auto-Fit Text to Bubble / Bounding Area")
        layout_grid.addWidget(self.smart_fit_checkbox, 3, 0, 1, 4)
        
        self.bubble_checkbox = QCheckBox("Render bubble (white fill, black outline)")
        layout_grid.addWidget(self.bubble_checkbox, 4, 0, 1, 4)

        content_layout.addWidget(layout_group)

        outline_group = QGroupBox("Text Outline & Glow")
        outline_layout = QGridLayout(outline_group)
        self.text_outline_checkbox = QCheckBox("Enable outline / glow")
        outline_layout.addWidget(self.text_outline_checkbox, 0, 0, 1, 4)

        self.outline_style_combo = QComboBox()
        self.outline_style_combo.addItems(["Stroke", "Glow"])
        outline_layout.addWidget(QLabel("Style:"), 1, 0)
        outline_layout.addWidget(self.outline_style_combo, 1, 1)

        self.outline_width_spin = QDoubleSpinBox()
        self.outline_width_spin.setRange(0.0, 30.0)
        self.outline_width_spin.setSingleStep(0.5)
        self.outline_width_spin.setDecimals(1)
        outline_layout.addWidget(QLabel("Width / Glow Radius:"), 1, 2)
        outline_layout.addWidget(self.outline_width_spin, 1, 3)

        self.outline_color_button = QPushButton("Outline Color")
        outline_layout.addWidget(QLabel("Color:"), 2, 0)
        outline_layout.addWidget(self.outline_color_button, 2, 1, 1, 3)

        glow_hint = QLabel("Tip: choose Glow for soft halos, Stroke for crisp comic outlines.")
        glow_hint.setStyleSheet("color: #9bb3cf; font-size: 10.2pt;")
        glow_hint.setWordWrap(True)
        outline_layout.addWidget(glow_hint, 3, 0, 1, 4)

        outline_layout.addWidget(QLabel("Concentric Outline Layers (Stacking):"), 4, 0, 1, 4)
        self.layers_list = QListWidget()
        self.layers_list.setFixedHeight(80)
        outline_layout.addWidget(self.layers_list, 5, 0, 1, 4)
        
        layer_controls = QHBoxLayout()
        self.add_layer_btn = QPushButton("Add Layer")
        self.remove_layer_btn = QPushButton("Remove Layer")
        self.layer_width_spin = QDoubleSpinBox()
        self.layer_width_spin.setRange(0.5, 30.0)
        self.layer_width_spin.setSingleStep(0.5)
        self.layer_color_btn = QPushButton("Layer Color")
        
        layer_controls.addWidget(self.add_layer_btn)
        layer_controls.addWidget(self.remove_layer_btn)
        layer_controls.addWidget(QLabel("Width:"))
        layer_controls.addWidget(self.layer_width_spin)
        layer_controls.addWidget(self.layer_color_btn)
        outline_layout.addLayout(layer_controls, 6, 0, 1, 4)

        content_layout.addWidget(outline_group)

        # Gradient Group
        gradient_group = QGroupBox("Gradient Fill")
        gradient_layout = QGridLayout(gradient_group)
        self.gradient_enabled_checkbox = QCheckBox("Enable Gradient")
        gradient_layout.addWidget(self.gradient_enabled_checkbox, 0, 0, 1, 4)

        self.gradient_color1_btn = QPushButton("Start Color")
        self.gradient_color2_btn = QPushButton("End Color")
        gradient_layout.addWidget(QLabel("Colors:"), 1, 0)
        gradient_layout.addWidget(self.gradient_color1_btn, 1, 1)
        gradient_layout.addWidget(self.gradient_color2_btn, 1, 2)

        self.gradient_angle_spin = QDoubleSpinBox()
        self.gradient_angle_spin.setRange(0.0, 360.0)
        self.gradient_angle_spin.setSingleStep(15.0)
        self.gradient_angle_spin.setSuffix(" °")
        self.gradient_angle_spin.setSuffix(" °")
        
        self.gradient_direction_combo = QComboBox()
        for label, _ in self.GRADIENT_DIRECTIONS:
            self.gradient_direction_combo.addItem(label)
            
        gradient_layout.addWidget(QLabel("Angle:"), 1, 3)
        gradient_layout.addWidget(self.gradient_angle_spin, 1, 4)
        gradient_layout.addWidget(QLabel("Direction:"), 1, 5)
        gradient_layout.addWidget(self.gradient_direction_combo, 1, 6)
        
        content_layout.addWidget(gradient_group)

        # Drop Shadow Group
        shadow_group = QGroupBox("Drop Shadow")
        shadow_group.setCheckable(True)
        shadow_layout = QGridLayout(shadow_group)
        self.shadow_enabled_checkbox = shadow_group
        
        self.shadow_color_btn = QPushButton("Shadow Color")
        self.shadow_blur_spin = QDoubleSpinBox()
        self.shadow_blur_spin.setRange(0.0, 50.0)
        self.shadow_blur_spin.setSingleStep(1.0)
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
        
        shadow_layout.addWidget(QLabel("Color:"), 0, 0)
        shadow_layout.addWidget(self.shadow_color_btn, 0, 1)
        shadow_layout.addWidget(QLabel("Blur Radius:"), 0, 2)
        shadow_layout.addWidget(self.shadow_blur_spin, 0, 3)
        
        shadow_layout.addWidget(QLabel("Offset X:"), 1, 0)
        shadow_layout.addWidget(self.shadow_offset_x_spin, 1, 1)
        shadow_layout.addWidget(QLabel("Offset Y:"), 1, 2)
        shadow_layout.addWidget(self.shadow_offset_y_spin, 1, 3)
        
        shadow_layout.addWidget(QLabel("Opacity:"), 2, 0)
        shadow_layout.addWidget(self.shadow_opacity_spin, 2, 1)
        
        content_layout.addWidget(shadow_group)

        # Screentone Pattern Group
        pattern_group = QGroupBox("Manga Screentone Fill")
        pattern_group.setCheckable(True)
        pattern_layout = QGridLayout(pattern_group)
        self.pattern_enabled_checkbox = pattern_group
        
        self.pattern_type_combo = QComboBox()
        self.pattern_type_combo.addItem("Screentone Dots", "dot")
        self.pattern_type_combo.addItem("Screentone Lines", "line")
        self.pattern_type_combo.addItem("Crosshatch Pattern", "hatch")
        self.pattern_type_combo.addItem("Manga Wave", "wave")
        
        self.pattern_scale_spin = QDoubleSpinBox()
        self.pattern_scale_spin.setRange(0.1, 10.0)
        self.pattern_scale_spin.setSingleStep(0.1)
        self.pattern_scale_spin.setValue(1.0)
        
        pattern_layout.addWidget(QLabel("Pattern Type:"), 0, 0)
        pattern_layout.addWidget(self.pattern_type_combo, 0, 1)
        pattern_layout.addWidget(QLabel("Pattern Scale:"), 0, 2)
        pattern_layout.addWidget(self.pattern_scale_spin, 0, 3)
        
        content_layout.addWidget(pattern_group)

        margin_group = QGroupBox("Inner Margins (px)")
        margin_grid = QGridLayout(margin_group)
        self.margin_top_spin = QSpinBox(); self.margin_top_spin.setRange(0, 400)
        self.margin_right_spin = QSpinBox(); self.margin_right_spin.setRange(0, 400)
        self.margin_bottom_spin = QSpinBox(); self.margin_bottom_spin.setRange(0, 400)
        self.margin_left_spin = QSpinBox(); self.margin_left_spin.setRange(0, 400)
        margin_grid.addWidget(QLabel("Top:"), 0, 0); margin_grid.addWidget(self.margin_top_spin, 0, 1)
        margin_grid.addWidget(QLabel("Right:"), 0, 2); margin_grid.addWidget(self.margin_right_spin, 0, 3)
        margin_grid.addWidget(QLabel("Bottom:"), 1, 0); margin_grid.addWidget(self.margin_bottom_spin, 1, 1)
        margin_grid.addWidget(QLabel("Left:"), 1, 2); margin_grid.addWidget(self.margin_left_spin, 1, 3)
        content_layout.addWidget(margin_group)

        bezier_group = QGroupBox("Bezier Control Points (0.0 - 1.0)")
        bezier_layout = QGridLayout(bezier_group)
        self.cp1x_spin = self._create_bezier_spin(); self.cp1y_spin = self._create_bezier_spin()
        self.cp2x_spin = self._create_bezier_spin(); self.cp2y_spin = self._create_bezier_spin()
        bezier_layout.addWidget(QLabel("Control 1 X:"), 0, 0); bezier_layout.addWidget(self.cp1x_spin, 0, 1)
        bezier_layout.addWidget(QLabel("Control 1 Y:"), 0, 2); bezier_layout.addWidget(self.cp1y_spin, 0, 3)
        bezier_layout.addWidget(QLabel("Control 2 X:"), 1, 0); bezier_layout.addWidget(self.cp2x_spin, 1, 1)
        bezier_layout.addWidget(QLabel("Control 2 Y:"), 1, 2); bezier_layout.addWidget(self.cp2y_spin, 1, 3)
        content_layout.addWidget(bezier_group)
        content_layout.addStretch(1)

        content_scroll.setWidget(content_widget)
        main_layout.addWidget(content_scroll, 1)

        button_box = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        button_box.button(QDialogButtonBox.Save).setText("Apply")
        button_box.accepted.connect(self._handle_accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

        # Revert to global defaults button
        self.revert_button = QPushButton("Revert to Global Defaults")
        self.revert_button.setToolTip("Clear per-area overrides and use global defaults for this area.")
        def _on_revert_clicked():
            notes = self.area.review_notes if isinstance(getattr(self.area, 'review_notes', {}), dict) else {}
            for legacy in ('manual_inpaint', 'manual'):
                if legacy in notes:
                    notes.pop(legacy, None)
            self.area.review_notes = notes
            if hasattr(self.area, 'clear_override'):
                self.area.clear_override('use_inpaint')
                self.area.clear_override('use_background_box')
                self.area.clear_override('constrain_text')
                self.area.clear_override('use_auto_text_color')
            parent = self.parent()
            if parent and hasattr(parent, 'redraw_all_typeset_areas'):
                try:
                    parent.redraw_all_typeset_areas()
                except Exception:
                    pass
            if parent and getattr(parent, 'selected_typeset_area', None) is self.area:
                try:
                    parent._sync_cleanup_controls_from_selection()
                except Exception:
                    pass
            notify_toast(self, "Reverted", "This area's overrides have been cleared and global defaults will be used.", kind="success")
        self.revert_button.clicked.connect(_on_revert_clicked)
        main_layout.addWidget(self.revert_button)

        self.gradient_enabled_checkbox.toggled.connect(self._update_gradient_ui_state)
        self.gradient_color1_btn.clicked.connect(lambda: self._choose_gradient_color(0))
        self.gradient_color2_btn.clicked.connect(lambda: self._choose_gradient_color(1))
        self.gradient_direction_combo.currentIndexChanged.connect(self._on_gradient_direction_changed)
        self.gradient_angle_spin.valueChanged.connect(self._on_gradient_angle_changed)
        
        self.gradient_colors_store = ["#FF0000", "#0000FF"]

        self.font_combo.currentTextChanged.connect(self._change_font_family)
        self.font_size_spin.valueChanged.connect(self._change_font_size)
        self.bold_button.toggled.connect(self._toggle_bold)
        self.italic_button.toggled.connect(self._toggle_italic)
        self.underline_button.toggled.connect(self._toggle_underline)
        self.color_button.clicked.connect(self._choose_color)
        self.text_edit.cursorPositionChanged.connect(self._sync_toolbar_from_cursor)
        self.alignment_combo.currentIndexChanged.connect(self._apply_alignment)
        self.line_spacing_spin.valueChanged.connect(self._apply_line_spacing)
        self.char_spacing_spin.valueChanged.connect(self._apply_char_spacing)
        self.text_outline_checkbox.toggled.connect(self._update_outline_controls_enabled)
        self.outline_style_combo.currentIndexChanged.connect(self._update_outline_controls_enabled)
        self.outline_width_spin.valueChanged.connect(self._update_outline_controls_enabled)
        self.outline_width_spin.valueChanged.connect(self._update_outline_controls_enabled)
        self.outline_color_button.clicked.connect(self._choose_outline_color)

        # Outline layers signals
        self.add_layer_btn.clicked.connect(self._add_layer)
        self.remove_layer_btn.clicked.connect(self._remove_layer)
        self.layers_list.currentRowChanged.connect(self._on_layer_selected_changed)
        self.layer_width_spin.valueChanged.connect(self._on_layer_width_changed)
        self.layer_color_btn.clicked.connect(self._choose_layer_color)
        
        # Shadow signals
        self.shadow_color_btn.clicked.connect(self._choose_shadow_color)
        
        self.outline_layers_store = []
        self._shadow_color = QColor('#000000')

        self._populate_font_combo()
        self._load_area_into_editor()
        self._sync_toolbar_from_cursor()

    def _update_gradient_ui_state(self):
        enabled = self.gradient_enabled_checkbox.isChecked()
        self.gradient_color1_btn.setEnabled(enabled)
        self.gradient_color2_btn.setEnabled(enabled)
        self.gradient_angle_spin.setEnabled(enabled)
        self.gradient_direction_combo.setEnabled(enabled)

    def _on_gradient_direction_changed(self):
        idx = self.gradient_direction_combo.currentIndex()
        if idx < 0: return
        label, angle = self.GRADIENT_DIRECTIONS[idx]
        if angle != -1:
            with QSignalBlocker(self.gradient_angle_spin):
                self.gradient_angle_spin.setValue(angle)

    def _on_gradient_angle_changed(self):
        val = self.gradient_angle_spin.value()
        # Find close match
        best_idx = 0 # Custom
        for i, (label, angle) in enumerate(self.GRADIENT_DIRECTIONS):
            if angle != -1 and abs(angle - val) < 1.0:
                best_idx = i
                break
            # Check for 360/0 equivalence
            if angle == 0.0 and abs(360.0 - val) < 1.0:
                best_idx = i
                break
        
        with QSignalBlocker(self.gradient_direction_combo):
            self.gradient_direction_combo.setCurrentIndex(best_idx)

    def _choose_gradient_color(self, index):
        current_hex = self.gradient_colors_store[index] if 0 <= index < len(self.gradient_colors_store) else "#000000"
        color = QColorDialog.getColor(QColor(current_hex), self, "Select Gradient Color")
        if color.isValid():
            if index < len(self.gradient_colors_store):
                self.gradient_colors_store[index] = color.name()
            else:
                self.gradient_colors_store.append(color.name())
            self._update_gradient_buttons_style()

    def _update_gradient_buttons_style(self):
        c1 = self.gradient_colors_store[0]
        c2 = self.gradient_colors_store[1] if len(self.gradient_colors_store) > 1 else c1
        self.gradient_color1_btn.setStyleSheet(f"background-color: {c1}; color: {'#000000' if QColor(c1).lightness() > 128 else '#ffffff'}; border: 1px solid #555;")
        self.gradient_color2_btn.setStyleSheet(f"background-color: {c2}; color: {'#000000' if QColor(c2).lightness() > 128 else '#ffffff'}; border: 1px solid #555;")

    def _apply_default_size(self):
        try:
            screen = QApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                # Lebarkan hingga 85% layar
                self.resize(int(geo.width() * 0.85), int(geo.height() * 0.85))
            else:
                self.resize(1200, 800)
        except Exception:
            self.resize(1200, 800)

    def closeEvent(self, event):
        try:
            s = self.size()
            SETTINGS.setdefault('ui', {})['advanced_editor_size'] = (s.width(), s.height())
        except Exception:
            pass
        super().closeEvent(event)

    def _create_bezier_spin(self):
        spin = QDoubleSpinBox()
        spin.setRange(-1.0, 2.0)
        spin.setDecimals(3)
        spin.setSingleStep(0.05)
        return spin

    def _remember_cursor_state(self):
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
            pos = cursor.position()
            anchor = cursor.anchor()
            length = doc.characterCount()
            if pos < 0 or anchor < 0 or pos > length or anchor > length:
                return False
            return True
        except Exception:
            return False

    def _is_light(self, color_str):
        c = QColor(color_str)
        return c.lightness() > 128

    def _update_shadow_color_button_ui(self, color):
        name = color.name()
        self.shadow_color_btn.setStyleSheet(f"background-color: {name}; color: {'#000000' if self._is_light(name) else '#ffffff'}; border: 1px solid #555;")

    def _choose_shadow_color(self):
        c = QColorDialog.getColor(self._shadow_color, self, "Pick Shadow Color")
        if c.isValid():
            self._shadow_color = c
            self._update_shadow_color_button_ui(c)

    def _refresh_layers_list(self):
        self.layers_list.clear()
        for idx, layer in enumerate(self.outline_layers_store):
            w = layer.get('width', 2.0)
            c = layer.get('color', '#000000')
            item = QListWidgetItem(f"Layer {idx + 1}: Width {w}px — Color {c}")
            item.setBackground(QColor(c))
            item.setForeground(QColor('#000000' if self._is_light(c) else '#ffffff'))
            self.layers_list.addItem(item)
            
    def _add_layer(self):
        c = QColorDialog.getColor(Qt.black, self, "Select Outline Layer Color")
        if c.isValid():
            self.outline_layers_store.append({'width': 2.0, 'color': c.name()})
            self._refresh_layers_list()
            self.layers_list.setCurrentRow(len(self.outline_layers_store) - 1)
            
    def _remove_layer(self):
        row = self.layers_list.currentRow()
        if row >= 0:
            self.outline_layers_store.pop(row)
            self._refresh_layers_list()
            
    def _on_layer_selected_changed(self):
        row = self.layers_list.currentRow()
        if row >= 0 and row < len(self.outline_layers_store):
            layer = self.outline_layers_store[row]
            with QSignalBlocker(self.layer_width_spin):
                self.layer_width_spin.setValue(float(layer.get('width', 2.0)))
                
    def _on_layer_width_changed(self):
        row = self.layers_list.currentRow()
        if row >= 0 and row < len(self.outline_layers_store):
            self.outline_layers_store[row]['width'] = self.layer_width_spin.value()
            self._refresh_layers_list()
            
    def _choose_layer_color(self):
        row = self.layers_list.currentRow()
        if row >= 0 and row < len(self.outline_layers_store):
            layer = self.outline_layers_store[row]
            current_c = QColor(layer.get('color', '#000000'))
            c = QColorDialog.getColor(current_c, self, "Edit Outline Layer Color")
            if c.isValid():
                self.outline_layers_store[row]['color'] = c.name()
                self._refresh_layers_list()

    def _populate_font_combo(self):
        if not self.font_manager:
            return
        fonts = self.font_manager.list_fonts()
        with QSignalBlocker(self.font_combo):
            self.font_combo.clear()
            for name in fonts:
                self.font_combo.addItem(name)
                preview_font = self.font_manager.create_qfont(name)
                preview_font.setPointSize(16)
                idx = self.font_combo.count() - 1
                self.font_combo.setItemData(idx, preview_font, Qt.FontRole)

    def _update_font_preview(self, display_name):
        if not self.font_manager or not display_name:
            return
        base_font = self.text_edit.currentCharFormat().font()
        if not base_font.family():
            base_font = self.area.get_font()
        preview_font = self.font_manager.create_qfont(display_name, base_font=base_font)
        preview_font.setPointSizeF(self.font_size_spin.value())
        preview_font.setWeight(base_font.weight())
        preview_font.setItalic(base_font.italic())
        self.font_preview.setFont(preview_font)
        self.font_preview.setToolTip(display_name)

    def _load_area_into_editor(self):
        self.text_edit.clear()
        cursor = QTextCursor(self.text_edit.document())
        cursor.movePosition(QTextCursor.Start)

        segments = self.area.get_segments()
        if not segments:
            segments = [{'text': self.area.text or '', 'font': self.area.font_to_dict(self.area.get_font()), 'color': self.area.get_color().name(), 'underline': False}]

        for segment in segments:
            text_value = segment.get('text', '')
            if not text_value:
                continue
            fmt = QTextCharFormat()
            seg_font = self.area.segment_to_qfont(segment)
            fmt.setFont(seg_font)
            fmt.setForeground(QBrush(self.area.segment_to_color(segment)))
            if segment.get('underline', seg_font.underline()):
                fmt.setFontUnderline(True)

            parts = text_value.split('\n')
            for idx, part in enumerate(parts):
                cursor.insertText(part, fmt)
                if idx < len(parts) - 1:
                    cursor.insertBlock()

        orientation = self.area.get_orientation()
        with QSignalBlocker(self.orientation_combo):
            self.orientation_combo.setCurrentIndex(1 if orientation == 'vertical' else 0)

        current_effect = self.area.get_effect()
        effect_idx = next((i for i, (_, val) in enumerate(self.EFFECT_OPTIONS) if val == current_effect), 0)
        with QSignalBlocker(self.effect_combo):
            self.effect_combo.setCurrentIndex(effect_idx)

        # [FIX] Load Margins
        margins = self.area.get_margins()
        if margins:
            self.margin_top_spin.setValue(int(margins.get('top', 0)))
            self.margin_right_spin.setValue(int(margins.get('right', 0)))
            self.margin_bottom_spin.setValue(int(margins.get('bottom', 0)))
            self.margin_left_spin.setValue(int(margins.get('left', 0)))

        # [FIX] Load Alignment
        align_val = self.area.get_alignment()
        if align_val:
            # Match "left", "center", "right"
            idx_align = next((i for i, (lbl, _) in enumerate(self.ALIGN_OPTIONS) if lbl.lower().startswith(align_val.lower())), 1)
            with QSignalBlocker(self.alignment_combo):
                self.alignment_combo.setCurrentIndex(idx_align)
        
        # [FIX] Load Spacing
        self.line_spacing_spin.setValue(float(self.area.get_line_spacing()))
        self.char_spacing_spin.setValue(float(self.area.get_char_spacing()))

        # [FIX] Load Text Outline
        has_outline = bool(self.area.has_text_outline() if hasattr(self.area, 'has_text_outline') else False)
        self.text_outline_checkbox.setChecked(has_outline)
        
        outline_width = float(self.area.get_text_outline_width() if hasattr(self.area, 'get_text_outline_width') else 2.0)
        self.outline_width_spin.setValue(outline_width)
        
        outline_style = self.area.get_text_outline_style() if hasattr(self.area, 'get_text_outline_style') else 'stroke'
        style_idx = 1 if outline_style == 'glow' else 0
        with QSignalBlocker(self.outline_style_combo):
            self.outline_style_combo.setCurrentIndex(style_idx)
            
        outline_color_val = self.area.get_text_outline_color() if hasattr(self.area, 'get_text_outline_color') else '#000000'
        self._outline_color = QColor(outline_color_val) if isinstance(outline_color_val, (str, QColor)) else QColor('#000000')
        self._update_outline_color_button_ui(self._outline_color)
        self._update_outline_controls_enabled()

        self.effect_intensity_spin.setValue(self.area.get_effect_intensity())
        self.bubble_checkbox.setChecked(bool(getattr(self.area, 'bubble_enabled', False)))

        bezier = self.area.get_bezier_points()
        if len(bezier) >= 2:
            self.cp1x_spin.setValue(bezier[0].get('x', 0.25)); self.cp1y_spin.setValue(bezier[0].get('y', 0.2))
            self.cp2x_spin.setValue(bezier[1].get('x', 0.75)); self.cp2y_spin.setValue(bezier[1].get('y', 0.2))

        self.smart_fit_checkbox.setChecked(bool(getattr(self.area, 'smart_fit_enabled', False)))
        
        # Load Shadow
        self.shadow_enabled_checkbox.setChecked(bool(getattr(self.area, 'shadow_enabled', False)))
        self._shadow_color = QColor(getattr(self.area, 'shadow_color', '#000000'))
        self._update_shadow_color_button_ui(self._shadow_color)
        self.shadow_blur_spin.setValue(float(getattr(self.area, 'shadow_blur', 4.0)))
        self.shadow_offset_x_spin.setValue(float(getattr(self.area, 'shadow_offset_x', 3.0)))
        self.shadow_offset_y_spin.setValue(float(getattr(self.area, 'shadow_offset_y', 3.0)))
        self.shadow_opacity_spin.setValue(float(getattr(self.area, 'shadow_opacity', 0.7)))
        
        # Load Pattern
        self.pattern_enabled_checkbox.setChecked(bool(getattr(self.area, 'pattern_fill_enabled', False)))
        p_type = getattr(self.area, 'pattern_type', 'dot')
        p_idx = self.pattern_type_combo.findData(p_type)
        if p_idx >= 0:
            self.pattern_type_combo.setCurrentIndex(p_idx)
        self.pattern_scale_spin.setValue(float(getattr(self.area, 'pattern_scale', 1.0)))
        
        # Load Outline Layers
        self.outline_layers_store = copy.deepcopy(getattr(self.area, 'outline_layers', []))
        self._refresh_layers_list()

        # [NEW] Load Gradient State
        self.gradient_enabled_checkbox.setChecked(bool(self.area.get_extra('gradient_enabled')))
        
        grad_colors = self.area.get_extra('gradient_colors')
        if isinstance(grad_colors, list) and len(grad_colors) >= 2:
            self.gradient_colors_store = list(grad_colors)
        else:
            self.gradient_colors_store = ["#FF0000", "#0000FF"]
        self._update_gradient_buttons_style()
        
        self.gradient_angle_spin.setValue(float(self.area.get_extra('gradient_angle') or 0.0))
        
        direction_str = self.area.get_extra('gradient_direction')
        if direction_str:
            self.gradient_direction_combo.setCurrentText(direction_str)


    def _show_recent_menu(self):
        parent = self.parent()
        if not parent or not hasattr(parent, 'history_entries'):
            return
            
        from PyQt5.QtWidgets import QMenu, QAction
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #172330; border: 1px solid #2d3f58; } QMenu::item:selected { background-color: #1e3050; }")
        
        recent_texts = []
        for entry in reversed(parent.history_entries):
            text = entry.get('translated_text', '').strip()
            if text and text not in recent_texts:
                recent_texts.append(text)
                if len(recent_texts) >= 20:
                    break
                    
        if not recent_texts:
            action = QAction("No recent translations", self)
            action.setEnabled(False)
            menu.addAction(action)
        else:
            for text in recent_texts:
                display_text = text if len(text) <= 40 else text[:37] + '...'
                action = QAction(display_text, self)
                action.setData(text)
                menu.addAction(action)
                
        # Connect menu triggered
        def on_action(action):
            if action.data():
                # Replace selection or all text
                cursor = self.text_edit.textCursor()
                if cursor.hasSelection():
                    cursor.insertText(action.data())
                else:
                    self.text_edit.setPlainText(action.data())
                    
        menu.triggered.connect(on_action)
        
        # Show menu under button
        menu.exec_(self.recent_translations_btn.mapToGlobal(QPoint(0, self.recent_translations_btn.height())))


    def _on_ai_translate_clicked(self):
        parent = self.parent()
        if not parent: return

        # Get text to translate: selection or all text
        cursor = self.text_edit.textCursor()
        selected_text = cursor.selectedText()
        if not selected_text:
            text_to_translate = self.text_edit.toPlainText()
            is_selection = False
        else:
            text_to_translate = selected_text
            is_selection = True
        
        if not text_to_translate.strip():
            return

        provider, model_name = parent.get_selected_model_name()
        if not model_name:
            notify_banner(self, "advanced-edit-no-model", "No model", "Please select an AI model in the main window first.", kind="warning")
            return

        self.ai_translate_btn.setEnabled(False)
        self.ai_translate_btn.setText("Translating...")
        QApplication.processEvents()

        try:
            # We don't have style context easily available, so pass empty style
            # Unless we want to try to infer it from the area, but let's keep it simple
            translated = parent.translate_with_ai(text_to_translate, {}, provider, model_name, {})
            
            # Replace text
            if is_selection:
                cursor.insertText(str(translated))
            else:
                self.text_edit.setPlainText(str(translated))
        except Exception as e:
            notify_banner(self, "advanced-edit-translation-failed", "Error", f"Translation failed: {str(e)}", kind="error")
        finally:
            self.ai_translate_btn.setEnabled(True)
            self.ai_translate_btn.setText("AI Translate")

        margins = self.area.get_margins()
        self.margin_top_spin.setValue(int(margins.get('top', 0)))
        self.margin_right_spin.setValue(int(margins.get('right', 0)))
        self.margin_bottom_spin.setValue(int(margins.get('bottom', 0)))
        self.margin_left_spin.setValue(int(margins.get('left', 0)))

        align_value = self.area.get_alignment()
        align_idx = next((i for i, (label, _) in enumerate(self.ALIGN_OPTIONS) if label.lower().startswith(align_value)), 0)
        with QSignalBlocker(self.alignment_combo):
            self.alignment_combo.setCurrentIndex(align_idx)
        self._apply_alignment()

        self.line_spacing_spin.setValue(self.area.get_line_spacing())
        self.char_spacing_spin.setValue(self.area.get_char_spacing())
        self._apply_line_spacing()
        self._apply_char_spacing()
        self.text_outline_checkbox.setChecked(bool(self.area.has_text_outline() if hasattr(self.area, 'has_text_outline') else False))
        style_value = 'stroke'
        try:
            style_value = self.area.get_text_outline_style()
        except Exception:
            style_value = 'stroke'
        style_idx = 0 if style_value == 'stroke' else 1
        with QSignalBlocker(self.outline_style_combo):
            self.outline_style_combo.setCurrentIndex(style_idx)
        with QSignalBlocker(self.outline_width_spin):
            self.outline_width_spin.setValue(float(self.area.get_text_outline_width() if hasattr(self.area, 'get_text_outline_width') else 2.0))
        self._outline_color = self.area.get_text_outline_color() if hasattr(self.area, 'get_text_outline_color') else QColor('#000000')
        self._update_outline_color_button_ui(self._outline_color)
        self._update_outline_color_button_ui(self._outline_color)
        self._update_outline_controls_enabled()
        
        # Load Gradient
        g_enabled = getattr(self.area, 'gradient_enabled', False)
        g_colors = getattr(self.area, 'gradient_colors', None) or ["#ff0000", "#0000ff"]
        g_angle = getattr(self.area, 'gradient_angle', 0.0)
        
        with QSignalBlocker(self.gradient_enabled_checkbox):
            self.gradient_enabled_checkbox.setChecked(bool(g_enabled))
        self.gradient_colors_store = list(g_colors)
        if len(self.gradient_colors_store) < 2: self.gradient_colors_store = ["#ff0000", "#0000ff"]
        with QSignalBlocker(self.gradient_angle_spin):
            self.gradient_angle_spin.setValue(float(g_angle))
            
        # Sync combo
        self._on_gradient_angle_changed()
            
        self._update_gradient_buttons_style()
        self._update_gradient_ui_state()

        base_font = self.area.get_font()
        display_name = None
        if self.font_manager:
            display_name = self.font_manager.display_name_for_font(base_font)
        if not display_name:
            display_name = base_font.family()
        with QSignalBlocker(self.font_combo):
            if display_name:
                self.font_combo.setCurrentText(display_name)
        with QSignalBlocker(self.font_size_spin):
            self.font_size_spin.setValue(base_font.pointSizeF() or base_font.pointSize())
        self._update_font_preview(display_name)
        self._last_text_cursor = QTextCursor(self.text_edit.document())

    def _insert_emoji(self, text):
        try:
            if not text:
                return
            cursor = self.text_edit.textCursor()
            if not self._is_cursor_valid(cursor):
                cursor = QTextCursor(self.text_edit.document())
                cursor.movePosition(QTextCursor.End)
            cursor.insertText(text)
            self.text_edit.setTextCursor(cursor)
            self._last_text_cursor = QTextCursor(cursor)
        except Exception:
            traceback.print_exc()

    def _populate_dialog_fonts(self, group: str | None = None):
        """Populate the dialog font combo, optionally filtering by a group name provided by the main window."""
        try:
            fonts = self.font_manager.list_fonts() if self.font_manager else []
            if group and getattr(self.parent(), 'font_groups', None):
                allowed = set(self.parent().font_groups.get(group, []))
                fonts = [f for f in fonts if f in allowed]
            with QSignalBlocker(self.font_combo):
                self.font_combo.clear()
                for name in fonts:
                    self.font_combo.addItem(name)
                    preview_font = self.font_manager.create_qfont(name) if self.font_manager else QFont(name)
                    preview_font.setPointSize(14)
                    idx = self.font_combo.count() - 1
                    self.font_combo.setItemData(idx, preview_font, Qt.FontRole)
        except Exception:
            traceback.print_exc()

    def _on_dialog_font_group_changed(self, group_name: str):
        if group_name == 'All':
            self._populate_dialog_fonts(None)
        else:
            self._populate_dialog_fonts(group=group_name)

    def _merge_char_format(self, fmt):
        if fmt is None:
            return
        try:
            cursor = self.text_edit.textCursor()
            if cursor is None or cursor.isNull():
                return
            if not cursor.hasSelection():
                stored = getattr(self, '_last_text_cursor', None)
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
        except Exception:
            traceback.print_exc()

    def _change_font_family(self, display_name):
        try:
            if not display_name:
                return
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
            self._last_text_cursor = QTextCursor(self.text_edit.textCursor())
        except Exception:
            traceback.print_exc()

    def _change_font_size(self, value):
        try:
            fmt = QTextCharFormat()
            fmt.setFontPointSize(float(value))
            self._merge_char_format(fmt)
            current = self.font_combo.currentText()
            if current:
                self._update_font_preview(current)
            self._last_text_cursor = QTextCursor(self.text_edit.textCursor())
        except Exception:
            traceback.print_exc()

    def _toggle_bold(self, checked):
        try:
            fmt = QTextCharFormat()
            fmt.setFontWeight(QFont.Bold if checked else QFont.Normal)
            self._merge_char_format(fmt)
            self._last_text_cursor = QTextCursor(self.text_edit.textCursor())
        except Exception:
            traceback.print_exc()

    def _toggle_italic(self, checked):
        try:
            fmt = QTextCharFormat()
            fmt.setFontItalic(checked)
            self._merge_char_format(fmt)
            self._last_text_cursor = QTextCursor(self.text_edit.textCursor())
        except Exception:
            traceback.print_exc()

    def _toggle_underline(self, checked):
        try:
            fmt = QTextCharFormat()
            fmt.setFontUnderline(checked)
            self._merge_char_format(fmt)
            self._last_text_cursor = QTextCursor(self.text_edit.textCursor())
        except Exception:
            traceback.print_exc()

    def _choose_color(self):
        try:
            # User Feedback: ensure gradient logic is handled. 
            # If gradient is enabled, we use the first gradient color as initial, or cursor color
            initial = self._current_color_from_cursor()
            if self.gradient_enabled_checkbox.isChecked() and self.gradient_colors_store:
                 initial = QColor(self.gradient_colors_store[0])
            
            color = QColorDialog.getColor(initial, self, "Select Text Color")
            if color.isValid():
                # If user picks a solid color, disable gradient to avoid confusion/overrides
                if self.gradient_enabled_checkbox.isChecked():
                    self.gradient_enabled_checkbox.setChecked(False)
                    
                fmt = QTextCharFormat()
                fmt.setForeground(QBrush(color))
                self._merge_char_format(fmt)
                self._update_color_button(color)
                self._manual_text_color_changed = True
                self._last_text_cursor = QTextCursor(self.text_edit.textCursor())
        except Exception:
            traceback.print_exc()

    def _current_color_from_cursor(self):
        fmt = self.text_edit.currentCharFormat()
        brush = fmt.foreground()
        return brush.color() if brush.style() != Qt.NoBrush else self.area.get_color()

    def _update_color_button(self, color):
        try:
            if color.isValid():
                self.color_button.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #222; color: white;")
            else:
                self.color_button.setStyleSheet("")
        except Exception:
            traceback.print_exc()

    def _update_outline_color_button_ui(self, color: QColor | None = None):
        if not getattr(self, 'outline_color_button', None):
            return
        if color is None:
            color = self._outline_color if isinstance(getattr(self, '_outline_color', None), QColor) else QColor('#000000')
        if not color.isValid():
            color = QColor('#000000')
        self._outline_color = color
        try:
            luminance = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
            text_color = '#000000' if luminance > 160 else '#f3f6fb'
            self.outline_color_button.setStyleSheet(
                f"QPushButton {{ background-color: {color.name()}; color: {text_color}; border: 1px solid #1f2b36; border-radius: 8px; padding: 6px 10px; }}"
                " QPushButton:hover { border-color: #3a9bff; }"
            )
        except Exception:
            traceback.print_exc()

    def _choose_outline_color(self):
        try:
            color = QColorDialog.getColor(self._outline_color, self, "Select Outline/Glow Color")
            if color.isValid():
                self._outline_color = color
                self._update_outline_color_button_ui(color)
        except Exception:
            traceback.print_exc()

    def _update_outline_controls_enabled(self):
        enabled = self.text_outline_checkbox.isChecked()
        self.outline_style_combo.setEnabled(enabled)
        self.outline_width_spin.setEnabled(enabled)
        self.outline_color_button.setEnabled(enabled)
        # Give quick visual cue when glow is selected by dimming the button text slightly
        if enabled and self.outline_style_combo.currentText().lower().startswith('glow'):
            self.outline_color_button.setText("Glow Color")
        else:
            self.outline_color_button.setText("Outline Color")

    def _apply_alignment(self):
        try:
            doc = self.text_edit.document()
            original = self.text_edit.textCursor()
            cursor = QTextCursor(doc)
            cursor.select(QTextCursor.Document)
            block_format = QTextBlockFormat()
            align_label, align_flag = self.ALIGN_OPTIONS[self.alignment_combo.currentIndex()]
            block_format.setAlignment(align_flag)
            block_format.setLineHeight(int(self.line_spacing_spin.value() * 100), QTextBlockFormat.ProportionalHeight)
            cursor.setBlockFormat(block_format)
            self.text_edit.setTextCursor(original)
        except Exception:
            traceback.print_exc()

    def _apply_line_spacing(self):
        try:
            doc = self.text_edit.document()
            original = self.text_edit.textCursor()
            cursor = QTextCursor(doc)
            cursor.select(QTextCursor.Document)
            block_format = QTextBlockFormat()
            block_format.setLineHeight(int(self.line_spacing_spin.value() * 100), QTextBlockFormat.ProportionalHeight)
            _, align_flag = self.ALIGN_OPTIONS[self.alignment_combo.currentIndex()]
            block_format.setAlignment(align_flag)
            cursor.setBlockFormat(block_format)
            self.text_edit.setTextCursor(original)
        except Exception:
            traceback.print_exc()

    def _apply_char_spacing(self):
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
        except Exception:
            traceback.print_exc()

    def _sync_toolbar_from_cursor(self):
        fmt = self.text_edit.currentCharFormat()
        current_font = fmt.font()
        if not current_font.family():
            current_font = self.area.get_font()
        display = None
        if self.font_manager:
            display = self.font_manager.display_name_for_font(current_font)
        if not display:
            display = current_font.family()
        if display:
            with QSignalBlocker(self.font_combo):
                self.font_combo.setCurrentText(display)
        point = fmt.fontPointSize() or current_font.pointSizeF() or current_font.pointSize()
        with QSignalBlocker(self.font_size_spin): self.font_size_spin.setValue(point)
        with QSignalBlocker(self.bold_button): self.bold_button.setChecked(fmt.fontWeight() >= QFont.Bold)
        with QSignalBlocker(self.italic_button): self.italic_button.setChecked(fmt.fontItalic())
        with QSignalBlocker(self.underline_button): self.underline_button.setChecked(fmt.fontUnderline())
        self._update_color_button(self._current_color_from_cursor())
        self._update_color_button(self._current_color_from_cursor())
        if display:
            self._update_font_preview(display)
        
        # Adaptive background
        text_col = self._current_color_from_cursor()
        bg_col = "#0c121d" # dark default
        text_col_q = QColor(text_col) if isinstance(text_col, str) or isinstance(text_col, QColor) else None
        if text_col_q and text_col_q.isValid() and text_col_q.lightness() < 128:
            bg_col = "#f0f0f0" # light background for dark text
        
        col_str = text_col if text_col else '#e8eef7'
        if isinstance(col_str, QColor):
            col_str = col_str.name()
            
        self.text_edit.setStyleSheet(f"QTextEdit {{ background: {bg_col}; border-radius: 12px; padding: 10px; color: {col_str}; }}")

    def _extract_segments(self):
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
                            segments.append({
                                'text': text,
                                'font': TypesetArea.font_to_dict(font),
                                'color': fmt.foreground().color().name() if fmt.foreground().color().isValid() else self.area.get_color().name(),
                                'underline': fmt.fontUnderline(),
                            })
                    it += 1
                block = block.next()
                if block != doc.end():
                    segments.append({'text': '\n', 'font': TypesetArea.font_to_dict(self.area.get_font()), 'color': self.area.get_color().name(), 'underline': False})
        except Exception:
            traceback.print_exc()
        return segments

    def _handle_accept(self):
        try:
            segments = self._extract_segments()
            plain_text = ''.join(seg.get('text', '') for seg in segments)
            orientation = 'vertical' if self.orientation_combo.currentIndex() == 1 else 'horizontal'
            effect = self.effect_combo.currentData()
            bezier_data = [
                {'x': self.cp1x_spin.value(), 'y': self.cp1y_spin.value()},
                {'x': self.cp2x_spin.value(), 'y': self.cp2y_spin.value()},
            ]
            margins = {
                'top': self.margin_top_spin.value(),
                'right': self.margin_right_spin.value(),
                'bottom': self.margin_bottom_spin.value(),
                'left': self.margin_left_spin.value(),
            }
            align_label, _ = self.ALIGN_OPTIONS[self.alignment_combo.currentIndex()]
            self.result = {
                'segments': segments,
                'plain_text': plain_text,
                'orientation': orientation,
                'effect': effect,
                'effect_intensity': self.effect_intensity_spin.value(),
                'bezier_points': bezier_data,
                'bubble_enabled': self.bubble_checkbox.isChecked(),
                'alignment': align_label.lower(),
                'line_spacing': self.line_spacing_spin.value(),
                'char_spacing': self.char_spacing_spin.value(),
                'margins': margins,
                'text_outline': self.text_outline_checkbox.isChecked(),
                'text_outline_width': self.outline_width_spin.value(),
                'text_outline_color': self._outline_color.name() if isinstance(self._outline_color, QColor) else str(self._outline_color),
                'text_outline_style': self.outline_style_combo.currentText().lower(),
                'gradient_enabled': self.gradient_enabled_checkbox.isChecked(),
                'gradient_colors': self.gradient_colors_store,
                'gradient_angle': self.gradient_angle_spin.value(),
                'gradient_direction': self.gradient_direction_combo.currentText(),
                'shadow_enabled': self.shadow_enabled_checkbox.isChecked(),
                'shadow_color': self._shadow_color.name(),
                'shadow_blur': self.shadow_blur_spin.value(),
                'shadow_offset_x': self.shadow_offset_x_spin.value(),
                'shadow_offset_y': self.shadow_offset_y_spin.value(),
                'shadow_opacity': self.shadow_opacity_spin.value(),
                'outline_layers': self.outline_layers_store,
                'pattern_fill_enabled': self.pattern_enabled_checkbox.isChecked(),
                'pattern_type': self.pattern_type_combo.currentData(),
                'pattern_scale': self.pattern_scale_spin.value(),
                'smart_fit_enabled': self.smart_fit_checkbox.isChecked(),
                'manual_text_color_changed': bool(self._manual_text_color_changed),
            }
            self.accept()
            self.accept()
            self._last_text_cursor = QTextCursor(self.text_edit.document())
        except Exception as e:
            traceback.print_exc()
            notify_banner(self, "advanced-edit-apply-failed", "Apply failed", f"Failed to apply text changes: {str(e)}", kind="error")

    def get_result(self):
        return self.result



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
        g_font = QGroupBox("Font & Color")
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
# 📦 Tesseract & Manga-OCR Background System Integration Helpers & Workers
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

def _python_module_available(module_name):
    try:
        importlib.import_module(module_name)
        return True
    except Exception:
        return False

def _find_media_executable(name):
    path = shutil.which(name)
    if path:
        return path
    exe_name = f"{name}.exe" if sys.platform.startswith('win') and not name.endswith('.exe') else name
    try:
        local_path = os.path.join(ROOT_DIR, "bin", exe_name)
        if os.path.exists(local_path):
            return local_path
    except Exception:
        pass
    return ""

def get_media_dependency_status():
    return {
        "yt_dlp": _python_module_available("yt_dlp"),
        "yt_dlp_ejs": _python_module_available("yt_dlp_ejs"),
        "ffmpeg": bool(_find_media_executable("ffmpeg")),
        "deno": bool(_find_media_executable("deno")),
    }

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

class MediaDependenciesInstallWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def run(self):
        try:
            self.progress.emit("Installing YouTube Python packages...")
            pip_cmd = [sys.executable, "-m", "pip", "install", "yt-dlp", "yt-dlp-ejs"]
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            pip_proc = subprocess.Popen(
                pip_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creationflags,
            )
            _, pip_stderr = pip_proc.communicate()
            if pip_proc.returncode != 0:
                self.finished.emit(False, f"Pip install failed:\n{pip_stderr.decode(errors='ignore')}")
                return

            importlib.invalidate_caches()

            if sys.platform.startswith('win'):
                script_path = os.path.join(ROOT_DIR, "bin", "install_ffmpeg.ps1")
                if os.path.exists(script_path):
                    self.progress.emit("Installing FFmpeg and Deno...")
                    ps_cmd = [
                        "powershell",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        script_path,
                    ]
                    ps_proc = subprocess.Popen(
                        ps_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=creationflags,
                    )
                    _, ps_stderr = ps_proc.communicate()
                    if ps_proc.returncode != 0:
                        self.finished.emit(False, f"FFmpeg/Deno installer failed:\n{ps_stderr.decode(errors='ignore')}")
                        return
                else:
                    self.finished.emit(False, f"Installer script not found:\n{script_path}")
                    return
            else:
                self.progress.emit("Skipping FFmpeg/Deno auto installer on this platform.")

            status = get_media_dependency_status()
            missing = [name for name, ready in status.items() if not ready]
            if missing:
                self.finished.emit(False, "Still missing: " + ", ".join(missing))
            else:
                self.finished.emit(True, "YouTube/Media dependencies are ready.")
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

        self.setWindowTitle("📈 Session Analytics & Export")
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

        title_lbl = QLabel("📈  Session Analytics")
        title_lbl.setStyleSheet("font-size: 14pt; font-weight: bold; color: #38bdf8;")
        hdr_layout.addWidget(title_lbl)
        hdr_layout.addStretch(1)

        # Tombol export & reset di header
        export_btn = QPushButton("⬇  Export CSV")
        export_btn.setObjectName("export_btn")
        export_btn.setFixedHeight(32)
        export_btn.clicked.connect(self._export_csv)
        hdr_layout.addWidget(export_btn)

        reset_btn = QPushButton("🗑  Reset")
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
        self._section_label("💰 Cost Summary")
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
        self._section_label("📊 API Usage per Model")

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
                f"<b style='color:{color}; font-size:10pt;'>▶ {provider}</b>"
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
        self._section_label("⏱ Rate Limit Status (saat ini)")

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

                status_icon = "🟢"
                rpm_pct = int(min(rpm / rpm_limit * 100, 100)) if rpm_limit > 0 else 0
                if rpm_pct >= 100:
                    status_icon = "🔴"
                elif rpm_pct >= 60:
                    status_icon = "🟡"

                row_w = QWidget()
                rl = QHBoxLayout(row_w)
                rl.setContentsMargins(8, 2, 8, 2)
                rl.setSpacing(10)

                icon_lbl = QLabel(status_icon)
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
