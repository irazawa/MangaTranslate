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


class StartupText:
    VERSION_LABEL = f"v{APP_VERSION}"
    SUBTITLE = "Menyiapkan OCR, translator, dan workspace typeset."
    HINT = "Aplikasi sedang dibuka. Tidak perlu menjalankan EXE lagi."
    STATUS_STARTING = "Memulai aplikasi..."
    STATUS_IMPORTING_APP = "Memuat modul aplikasi..."
    STATUS_CHECKING_DEPENDENCIES = "Memeriksa dependency..."
    STATUS_PREPARING_SESSION = "Menyiapkan data sesi..."
    STATUS_BUILDING_UI = "Membangun interface..."
    STATUS_APPLYING_THEME = "Menerapkan dark theme..."
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
