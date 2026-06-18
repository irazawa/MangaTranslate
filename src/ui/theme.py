"""Shared UI theme constants and QSS helpers for MangaTranslate."""

COLORS = {
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

FONT_FAMILY = "'Outfit', 'Inter', 'Segoe UI', sans-serif"


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
        font-size: 10pt;
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
    QPushButton:hover:!disabled {{
        background-color: {COLORS["accent"]};
        color: {COLORS["bg"]};
        border-color: {COLORS["accent"]};
    }}
    QPushButton:pressed:!disabled {{
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
        color: #f8fafc;
    }}
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
        color: #f8fafc;
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

    {selector}:hover:!disabled {{
        background-color: #334155;
        border-color: {COLORS["accent"]};
        color: #f8fafc;
    }}

    {selector}:pressed:!disabled {{
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
        color: #94a3b8;
        font-weight: 600;
    }}
    {selector}:hover:!disabled {{
        background-color: {COLORS["border"]};
        border-color: {COLORS["accent"]};
        color: #f8fafc;
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
    {selector}:hover:!disabled {{
        background-color: #0369a1;
        border-color: {COLORS["accent"]};
        color: #f0f9ff;
    }}
    {selector}:pressed:!disabled {{
        background-color: #075985;
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
    return f"""
    QDialog#SettingsCenterDialog {{
        background: {COLORS["bg"]};
        color: {COLORS["text"]};
        font-family: {FONT_FAMILY};
        font-size: 10pt;
    }}

    #settings-nav-panel {{
        background: {COLORS["panel"]};
        border-right: 1px solid {COLORS["border"]};
    }}
    #settings-nav-brand {{
        background: {COLORS["panel"]};
        border-bottom: 1px solid {COLORS["border"]};
    }}
    #settings-brand-title {{
        color: #f8fafc;
        font-size: 17pt;
        font-weight: 800;
    }}
    #settings-brand-subtitle {{
        color: {COLORS["muted"]};
        font-size: 9pt;
        line-height: 130%;
    }}
    #settings-nav-list {{
        background: {COLORS["panel"]};
        border: none;
        outline: none;
        color: {COLORS["text"]};
        padding: 10px 8px;
    }}
    #settings-nav-list::item {{
        border-radius: {RADIUS["md"]}px;
        margin: 3px 0;
        padding: 9px 12px;
        color: #94a3b8;
    }}
    #settings-nav-list::item:selected {{
        background: {COLORS["border"]};
        color: {COLORS["accent"]};
        font-weight: 700;
        border-left: 3px solid {COLORS["accent"]};
    }}
    #settings-nav-list::item:hover:!selected {{
        background: {COLORS["card_alt"]};
        color: #f8fafc;
    }}
    #settings-nav-footer {{
        background: {COLORS["panel"]};
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
        color: #f8fafc;
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
        selection-background-color: {COLORS["border"]};
        selection-color: {COLORS["accent"]};
    }}
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
    QPushButton:hover:!disabled,
    QToolButton:hover:!disabled {{
        background: {COLORS["accent"]};
        border-color: {COLORS["accent"]};
        color: {COLORS["bg"]};
    }}
    QPushButton:pressed:!disabled,
    QToolButton:pressed:!disabled {{
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
        color: #f8fafc;
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
