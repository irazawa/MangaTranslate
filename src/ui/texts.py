"""Centralized UI copy for labels, titles, and repeated messages."""

from html import escape

from src.core.app_info import APP_COPYRIGHT, APP_NAME, APP_VERSION


class NavText:
    HIDE_FOLDER = "Hide Folder"
    SHOW_FOLDER = "Show Folder"
    HIDE_TOOLS = "Hide Tools"
    SHOW_TOOLS = "Show Tools"
    FOCUS_MODE = "Focus Mode"
    FOCUS_MODE_ACTION = "Toggle Focus Mode (Canvas Only)"
    FOCUS_MODE_SHORTCUT = "Focus Mode (Canvas Only)"
    FOCUS_MODE_STATUS = "Focus Mode: Canvas Only (Press F2 to restore)"
    COMPARE_MODE = "👁 Compare"


class ActionText:
    HELP_USAGE_MENU = "📖 Help & Usage..."
    FULL_PAGE_TRANSLATE = "🚀 Terjemahkan Halaman Ini"
    NEW_PROJECT_AUTOSAVED = "New project created and auto-saved."


class DialogText:
    ABOUT_TITLE = "About & API Usage"
    HELP_USAGE_TITLE = "📖 Help & Usage"
    HELP_USAGE_HEADER = "📖  Help & Usage"


class SettingsText:
    TITLE = "Settings"
    HEADER_TITLE = "Settings"
    HEADER_SUBTITLE = "Workspace, OCR, API, export, and tool preferences."
    FOOTER_HINT = f"MangaTranslate v{APP_VERSION}"
    BUTTON_CANCEL = "Cancel"
    BUTTON_APPLY = "Apply"
    BUTTON_SAVE = "Save Changes"

    NAV_ITEMS = [
        {
            "key": "general",
            "label": "General",
            "description": "Export, autosave, presets",
            "title": "General",
            "subtitle": "Set project safety, output defaults, and the presets used by new work.",
        },
        {
            "key": "cleanup",
            "label": "Cleanup",
            "description": "Text cleanup defaults",
            "title": "Cleanup",
            "subtitle": "Choose how new text areas behave when the app cleans and redraws bubbles.",
        },
        {
            "key": "appearance",
            "label": "Appearance",
            "description": "Theme and UI style",
            "title": "Appearance",
            "subtitle": "Use light, dark, or system theme mode and tune the app colors, fonts, and motion preferences.",
        },
        {
            "key": "translation",
            "label": "Translation",
            "description": "OpenRouter models",
            "title": "Translation",
            "subtitle": "Configure OpenRouter translation endpoints and model lists.",
        },
        {
            "key": "shortcuts",
            "label": "Shortcuts",
            "description": "Keyboard and mouse",
            "title": "Shortcuts",
            "subtitle": "Assign keyboard or mouse shortcuts. Leave a field blank to disable an action.",
        },
        {
            "key": "api",
            "label": "API Keys",
            "description": "Providers and tokens",
            "title": "API Keys",
            "subtitle": "Manage translation and OCR provider keys, active keys, and the Tesseract path.",
        },
        {
            "key": "ocr_plugins",
            "label": "OCR Plugins",
            "description": "Engines and languages",
            "title": "OCR Plugins Manager",
            "subtitle": "Enable OCR engines, install Tesseract, and manage local language models.",
        },
        {
            "key": "media_tools",
            "label": "Media Tools",
            "description": "Optional installs",
            "title": "Media Tools",
            "subtitle": "Install optional YouTube, FFmpeg, and Deno tooling only when you need it.",
        },
        {
            "key": "glossary",
            "label": "Glossary",
            "description": "Term consistency",
            "title": "Glossary",
            "subtitle": "Keep names, places, and special manga terms translated consistently.",
        },
    ]


class AppearanceText:
    CARD_THEME = "Theme"
    CARD_COLORS = "Colors"
    CARD_INTERFACE = "Interface"
    MODE_LABEL = "Theme"
    MODE_DESC = "Use light, dark, or match your system."
    DARK_THEME_LABEL = "Dark theme"
    DARK_THEME_DESC = "Choose the dark palette used when dark mode is active."
    ACCENT_LABEL = "Accent"
    ACCENT_DESC = "Primary action and selection color. Leave empty to use the preset."
    BACKGROUND_LABEL = "Background"
    BACKGROUND_DESC = "Main window background override. Leave empty to use the preset."
    FOREGROUND_LABEL = "Foreground"
    FOREGROUND_DESC = "Main text color override. Leave empty to use the preset."
    UI_FONT_LABEL = "UI font"
    UI_FONT_DESC = "Font stack used by the MangaTranslate interface."
    CODE_FONT_LABEL = "Code font"
    CODE_FONT_DESC = "Font stack reserved for monospace/code-like fields."
    TRANSLUCENT_SIDEBAR_LABEL = "Translucent sidebar"
    TRANSLUCENT_SIDEBAR_DESC = "Soften sidebar panels where the theme supports translucency."
    CONTRAST_LABEL = "Contrast"
    CONTRAST_DESC = "Adjust border and muted text contrast."
    POINTER_LABEL = "Use pointer cursors"
    POINTER_DESC = "Change the cursor to a pointer over interactive controls."
    REDUCE_MOTION_LABEL = "Reduce motion"
    REDUCE_MOTION_DESC = "Reduce animations or match your system."
    UI_FONT_SIZE_LABEL = "UI font size"
    UI_FONT_SIZE_DESC = "Adjust the base size used for the MangaTranslate UI."
    CODE_FONT_SIZE_LABEL = "Code font size"
    CODE_FONT_SIZE_DESC = "Adjust the base size used for code-like text."
    PICK_COLOR = "Pick"
    RESET_COLOR = "Reset"
    MODES = [
        ("dark", "Dark"),
        ("light", "Light"),
        ("system", "System"),
    ]
    MOTION_OPTIONS = [
        ("system", "Match system"),
        ("reduce", "Reduce motion"),
        ("full", "Full motion"),
    ]


class StartupText:
    VERSION_LABEL = f"v{APP_VERSION}"
    SUBTITLE = "Menyiapkan OCR, translator, dan workspace typeset."
    HINT = "Aplikasi sedang dibuka. Tidak perlu menjalankan EXE lagi."
    STATUS_STARTING = "Memulai aplikasi..."
    STATUS_IMPORTING_APP = "Memuat modul aplikasi..."
    STATUS_CHECKING_DEPENDENCIES = "Memeriksa dependency..."
    STATUS_PREPARING_SESSION = "Menyiapkan data sesi..."
    STATUS_BUILDING_UI = "Membangun interface..."
    STATUS_APPLYING_THEME = "Menerapkan theme..."
    STATUS_SETTING_SHORTCUTS = "Menyiapkan shortcut..."
    STATUS_INITIALIZING_ENGINES = "Menyiapkan engine OCR..."
    STATUS_SYNCING_TESSDATA = "Menyinkronkan data Tesseract..."
    STATUS_LOADING_MODELS = "Memuat daftar bahasa dan model AI..."
    STATUS_LOADING_MANGA_OCR = "Memuat Manga-OCR lokal. Ini bisa memakan waktu..."
    STATUS_APPLYING_SETTINGS = "Menerapkan setting pengguna..."
    STATUS_LOADING_USAGE = "Memuat data penggunaan API..."
    STATUS_FETCHING_RATES = "Mengambil kurs dan harga model..."
    STATUS_READY = "Hampir siap..."


class BootstrapText:
    TITLE = "MangaTranslate Setup"
    SUBTITLE = "Menyiapkan environment lokal untuk menjalankan aplikasi."
    HINT = "Setup bisa memakan waktu saat pertama kali dibuka. Window ini bisa diminimize."
    STATUS_STARTING = "Memulai setup awal..."
    STATUS_CHECKING = "Memeriksa file aplikasi dan virtual environment..."
    STATUS_CREATING_VENV = "Membuat virtual environment..."
    STATUS_UPGRADING_PIP = "Mengupdate pip..."
    STATUS_INSTALLING_REQUIREMENTS = "Menginstall requirements.txt..."
    STATUS_READY = "Setup selesai. Membuka aplikasi..."
    STATUS_FAILED = "Setup gagal. Periksa log di bawah."
    PYTHON_MISSING = (
        "Python tidak ditemukan di PATH. Install Python 3.10+ terlebih dahulu, "
        "centang Add Python to PATH, lalu jalankan aplikasi lagi."
    )
    MAIN_MISSING = "main.py tidak ditemukan di folder aplikasi."
    REQUIREMENTS_MISSING = "requirements.txt tidak ditemukan di folder aplikasi."


class WorkspaceText:
    RIGHT_PANEL_TITLE = "Tools & Workspace"
    RIGHT_PANEL_TOGGLE_TOOLTIP = "Toggle Tools & Workspace panel (F4)"


def welcome_subtitle_html() -> str:
    return f"{escape(APP_NAME)} &mdash; v{APP_VERSION}"


def about_html() -> str:
    app_name = escape(APP_NAME)
    copyright_text = escape(APP_COPYRIGHT)
    return (
        f"<b>{app_name} v{APP_VERSION}</b><br><br>"
        "This tool was created to streamline the process of translating manga.<br><br>"
        "Powered by Python, PyQt5, and various AI APIs.<br>"
        "Enhanced with new features by Gemini.<br><br>"
        f"{copyright_text}"
    )
