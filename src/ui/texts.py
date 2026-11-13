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
    COMPARE_MODE = "Compare"


class ActionText:
    HELP_USAGE_MENU = "Help & Usage..."
    FULL_PAGE_TRANSLATE = "Terjemahkan Halaman Ini"
    NEW_PROJECT_AUTOSAVED = "New project created and auto-saved."


class DialogText:
    ABOUT_TITLE = "About & API Usage"
    HELP_USAGE_TITLE = "Help & Usage"
    HELP_USAGE_HEADER = "Help & Usage"


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
            "label": "Cleanup & Inpaint",
            "description": "IOPaint server & cleanup",
            "title": "Cleanup & Inpainting",
            "subtitle": "Configure IOPaint server URL, inpainting backend, padding, and text box defaults.",
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
            "description": "Local and cloud models",
            "title": "Translation",
            "subtitle": "Configure OpenRouter, 9Router, Ollama, and other OpenAI-compatible translation models.",
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
            "key": "glossary",
            "label": "Glossary",
            "description": "Term consistency",
            "title": "Glossary",
            "subtitle": "Keep names, places, and special manga terms translated consistently.",
        },
    ]


class SettingsWorkspaceText:
    TITLE = "Settings"
    SUBTITLE = "App settings, IOPaint configuration, workers monitor, and insights in one clean workspace."
    BACK_TO_APP = "Back to app"
    SEARCH_PLACEHOLDER = "Search settings..."
    PROFILE_NAME_FALLBACK = "MangaTranslate User"
    PROFILE_HANDLE = "@mangatranslate"
    PROFILE_BADGE = "Local profile"
    PROFILE_TITLE = "Profile"
    PROFILE_ACTIVITY = "Token activity"
    PROFILE_INSIGHTS = "Activity insights"
    PROFILE_MODE_DAILY = "Daily"
    PROFILE_MODE_WEEKLY = "Weekly"
    PROFILE_MODE_CUMULATIVE = "Cumulative"
    REFRESH = "Refresh"
    LOADING_SETTINGS = "Loading settings…"

    NAV_SECTIONS = [
        (
            "App Settings",
            [
                ("general", "General", "Export, autosave, presets", "settings"),
                ("cleanup", "Cleanup & Inpaint", "IOPaint server & cleanup", "paintbrush"),
                ("appearance", "Appearance", "Theme, fonts, motion", "palette"),
                ("translation", "Translation", "Local/cloud models", "languages"),
                ("api", "API Keys", "Providers and tokens", "key"),
                ("shortcuts", "Shortcuts", "Keyboard and mouse", "keyboard"),
                ("glossary", "Glossary", "Term consistency", "book"),
                ("workers", "Workers Monitor", "Active jobs & threads", "activity"),
            ],
        ),
        (
            "Personal & Help",
            [
                ("profile", "Profile", "Usage identity and streaks", "user"),
                ("usage", "Usage & Billing", "Costs, analytics, pricing", "dollar"),
                ("help_overview", "Help & About", "About app and project stats", "help"),
            ],
        ),
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


class WorkersText:
    TAB_TOOLTIP = "Monitor worker aktif, antrian, batch, dan hentikan worker yang macet"
    WORKERS_SECTION = "Worker Aktif"
    QUEUE_SECTION = "Antrian"
    BATCH_SECTION = "Batch Translate"
    EMPTY_WORKERS = "Tidak ada worker aktif. Worker muncul otomatis saat ada antrian terjemahan."
    HINT = "Worker macet (>2 menit tanpa progres) ditandai merah. 'Batalkan' berhenti setelah tugas berjalan; 'Paksa' menghentikan segera."
    COL_WORKER = "Worker"
    COL_TASK = "Tugas"
    COL_STAGE = "Tahap"
    COL_MODEL = "Model"
    COL_DURATION = "Durasi"
    COL_STATUS = "Status"
    COL_ACTION = "Aksi"
    COL_INDEX = "#"
    COL_ITEM = "Item"
    STATUS_RUNNING = "Berjalan"
    STATUS_API_WAIT = "Menunggu slot API"
    STATUS_STUCK = "Macet"
    FULLPAGE_TASK = "Full-page translate"
    STAGE_LABELS = {
        'job': "Menyiapkan",
        'ocr': "OCR",
        'translate': "Translate",
        'api_wait': "Tunggu API",
    }
    BTN_CANCEL = "Batalkan"
    BTN_FORCE = "Paksa"
    BTN_CANCEL_BATCH = "Batalkan Batch"
    BTN_FORCE_BATCH = "Paksa Hentikan Batch"
    BATCH_IDLE = "Tidak ada batch berjalan. Aktifkan mode batch, pilih area, lalu tekan 'Process Batch Now'."
    BATCH_DONE_FMT = "Selesai {done}/{total}"
    BATCH_CURRENT_FMT = "Halaman: {current}"
    BATCH_ETA_FMT = "Perkiraan selesai: {eta}"
    BATCH_ELAPSED_FMT = "Berjalan: {elapsed}"
    SUMMARY_ETA_FMT = "±{eta}"
    AVG_FMT = "Rata-rata {avg}/job"


class FullPageBatchText:
    """Teks fitur batch Full-Page Translation (tab Full)."""

    SCOPE_CURRENT = "Halaman saat ini"
    SCOPE_SELECTED = "Halaman terpilih"
    SCOPE_PROJECT = "Seluruh proyek"
    SCOPE_CURRENT_TIP = "Proses hanya halaman yang sedang tampil di canvas."
    SCOPE_SELECTED_TIP = "Proses halaman yang dipilih lewat pemilih halaman."
    SCOPE_PROJECT_TIP = "Proses semua halaman di proyek ini. Halaman yang sudah di-typeset atau sudah memiliki file _typeset dilewati otomatis."

    PICK_PAGES_BTN = "Pilih halaman… ({count})"
    PICK_TITLE = "Pilih Halaman"
    PICK_HINT = "Centang halaman yang ingin diproses. File _typeset beserta halaman aslinya (serta halaman yang sudah di-typeset) akan dilewati otomatis."
    PICK_CHECK_ALL = "Centang semua"
    PICK_UNCHECK_ALL = "Hapus centang"

    DIALOG_TITLE = "Full-Page Translation — Batch"
    DIALOG_PAGE_FMT = "Halaman {current}/{total} — {name}"
    DIALOG_STATS_FMT = "Selesai {done} • Dilewati {skipped} • Gagal {failed}"
    DIALOG_CANCELLING = "Membatalkan… (menunggu langkah saat ini selesai)"
    DIALOG_CANCEL_BTN = "Batalkan"
    DIALOG_STEP_WAIT = "Menunggu…"

    SINGLE_DIALOG_TITLE = "Full-Page Translation"
    SINGLE_PAGE_FMT = "Halaman: {name}"
    SINGLE_LOCK_HINT = "Navigasi dan canvas dikunci sementara hingga proses selesai atau dibatalkan."
    SINGLE_STEP_INIT = "Memulai proses halaman..."

    START_NO_TARGETS = "Tidak ada halaman untuk diproses. Semua halaman sudah di-typeset (atau sudah punya file _typeset) atau pilihan kosong."
    START_NEED_PICK = "Pilih dulu halaman yang ingin diproses."
    BATCH_BUSY = "Batch full-page masih berjalan. Tunggu hingga selesai."
    TOAST_DONE_FMT = "Batch selesai: {done} halaman diproses, {skipped} dilewati, {failed} gagal."

    RESTORE_AREA_INPAINT_BTN = "Pulihkan Inpaint Area"
    RESTORE_AREA_INPAINT_TIP = "Kembalikan gambar asli (sebelum inpaint) hanya pada area teks/SFX yang sedang dipilih."
    CANCEL_PAGE_INPAINT_BTN = "Batalkan Inpaint Halaman"
    CANCEL_PAGE_INPAINT_TIP = "Kembalikan seluruh gambar asli halaman ini seperti sebelum inpainting."
    LAYER_RESTORE_INPAINT_ACTION = "Pulihkan Inpaint Area Ini"


class TypesetText:
    """Teks kontrol typesetting & auto font size (tab Typeset)."""

    TIP_ORIENTATION_HORIZONTAL = "Teks mendatar normal (kiri ke kanan)."
    TIP_ORIENTATION_VERTICAL = "Teks vertikal diputar 90° ke samping."
    TIP_ORIENTATION_UPRIGHT = "Teks tersusun vertikal ke bawah dengan huruf tetap tegak horizontal."

    AUTO_FONT_SIZE_LABEL = "Auto Font Size (Fit Box)"
    AUTO_FONT_SIZE_TIP = "Otomatis menyesuaikan ukuran font dengan besar bubble/area teks hasil deteksi."
    FIT_FONT_SIZE_BTN = "Fit Box"
    FIT_FONT_SIZE_TIP = "Sesuaikan ukuran font area terpilih agar pas mengisi kotak bubble."
    FIT_FONT_SIZE_NO_SELECTION = "Pilih area teks terlebih dahulu untuk menyesuaikan ukuran font."
    FIT_FONT_SIZE_APPLIED_FMT = "Ukuran font disesuaikan ke {size:.1f} pt."


class AdvancedEditorText:
    """Teks UI untuk dialog Advanced Text Editor."""

    WINDOW_TITLE = "Advanced Text Editor"
    HERO_TITLE = "Advanced Text Editor"
    HERO_SUBTITLE = (
        "Atur format teks, warna gradasi, pola screentone, outline, bayangan, "
        "dan bentuk lengkungan dengan pratinjau langsung."
    )
    HERO_BADGE_AREA = "Rich Text & Effects"

    EDITOR_TITLE = "Editor Teks"
    EDITOR_HINT = "Blok sebagian teks untuk styling parsial, atau Ctrl+A untuk mengubah seluruh bubble."
    PREVIEW_TITLE = "Live Preview Bubble"
    PREVIEW_HINT = "Pratinjau render mendekati tampilan di kanvas."

    PREVIEW_BG_PAPER = "Putih"
    PREVIEW_BG_DARK = "Gelap"
    PREVIEW_BG_CHECKER = "Transparan"

    BTN_AI_TRANSLATE = "AI Translate"
    BTN_TRANSLATING = "Menerjemahkan..."
    TIP_AI_TRANSLATE = "Terjemahkan teks terseleksi (atau seluruh isi editor) menggunakan model AI aktif."
    BTN_RECENT = "Riwayat"
    TIP_RECENT = "Tempel salah satu hasil terjemahan terbaru ke editor ini."
    BTN_SYMBOLS = "Simbol"
    TIP_SYMBOLS = "Sisipkan simbol cinta (love), bintang, musik, atau ekspresi manga terkelompok ke posisi kursor."
    SYM_SECTION_QUICK_LOVE = "Akses Cepat: Love"
    SYM_SECTION_CATEGORIES = "Kategori Simbol"
    SYM_CAT_LOVE_CLASSIC = "Love & Hati: Klasik Manga"
    SYM_CAT_LOVE_VARIATIONS = "Love & Hati: Variasi Warna & Efek"
    SYM_CAT_LOVE_KAOMOJI = "Love & Hati: Kaomoji Romantis"
    SYM_CAT_SPARKLES_STARS = "Kilau, Bintang & Bunga"
    SYM_CAT_MUSIC = "Musik & Nada"
    SYM_CAT_MANGA_FX = "Ekspresi & Reaksi Manga"
    SYM_CAT_PUNCTUATION = "Tanda Baca & Kurung Manga"

    CONTRAST_LIGHT_PILL = "Kontras Editor: Kertas Terang (teks gelap)"
    CONTRAST_DARK_PILL = "Kontras Editor: Gelap (teks terang)"

    TAB_LAYOUT = "Layout"
    ORIENTATION_HORIZONTAL = "Horizontal"
    ORIENTATION_VERTICAL = "Vertical (Putar 90°)"
    ORIENTATION_UPRIGHT = "Vertical (Huruf Tegak)"
    TAB_FILL = "Fill && Color"
    TAB_OUTLINE = "Outline && FX"
    TAB_WARP = "Warp && Curve"

    CARD_LAYOUT_TITLE = "Orientasi, Perataan & Jarak"
    CARD_LAYOUT_DESC = "Tentukan arah baca horizontal/vertikal, perataan teks, spasi baris, dan jarak antar huruf."
    CARD_FIT_BUBBLE_TITLE = "Smart Auto-Fit & Bubble"
    CARD_FIT_BUBBLE_DESC = "Sesuaikan ukuran font otomatis agar pas di kotak area atau aktifkan kotak bubble latar putih."
    CARD_MARGINS_TITLE = "Batas Dalam / Inner Margins (px)"
    CARD_MARGINS_DESC = (
        "Memberi jarak padding di sisi dalam kotak teks (Atas, Kanan, Bawah, Kiri) "
        "supaya huruf tidak terlalu mepet atau menyentuh garis tepi bubble."
    )

    CARD_GRADIENT_TITLE = "Gradient Fill (Gradasi Warna)"
    CARD_GRADIENT_DESC = (
        "Mewarnai isi huruf dengan perpaduan dua warna atau lebih. "
        "Saat aktif, gradient menggantikan warna solid pada seluruh teks."
    )
    BTN_SWAP_COLORS = "Tukar"
    BTN_ADD_STOP = "+ Warna"
    BTN_REMOVE_STOP = "- Hapus"

    CARD_SCREENTONE_TITLE = "Manga Screentone Fill (Arsir Komik)"
    CARD_SCREENTONE_DESC = (
        "Mengisi bagian dalam teks dengan pola tekstur ala komik/manga (titik, garis, silang, atau gelombang). "
        "Paling jelas terlihat pada font berukuran besar dan tebal (SFX / judul)."
    )

    CARD_OUTLINE_TITLE = "Text Outline & Glow"
    CARD_OUTLINE_DESC = (
        "Stroke memberi garis tepi tajam agar teks terbaca di atas latar ramai; "
        "Glow memberi pendar cahaya lembut di sekeliling huruf."
    )
    CARD_LAYERS_TITLE = "Concentric Outline Layers (Lapisan Bertumpuk)"
    CARD_LAYERS_DESC = (
        "Menumpuk beberapa lapis outline sekaligus dari dalam ke luar "
        "(misalnya layer putih + layer hitam luar untuk efek teks komik berlapis)."
    )
    CARD_SHADOW_TITLE = "Drop Shadow (Bayangan Jatuh)"
    CARD_SHADOW_DESC = (
        "Menambahkan bayangan ber-blur di belakang huruf dengan arah offset X/Y dan tingkat transparansi (opacity)."
    )

    CARD_WARP_TITLE = "Warp Effect (Efek Bentuk Teks)"
    CARD_WARP_DESC = (
        "Melengkungkan atau mendistorsi jalur teks (Curved, Wavy, Jagged Shout, Arc, Arch, Flag). "
        "Atur kekuatan efek untuk mengontrol seberapa ekstrem bentuknya."
    )
    CARD_BEZIER_TITLE = "Bezier Control Points (0.0 - 1.0)"
    CARD_BEZIER_DESC = (
        "Khusus saat Effect = Curved: geser dua titik kontrol biru pada grafik untuk membentuk kurva lengkung kustom. "
        "Angka X/Y (0.0 sampai 1.0) adalah koordinat ternormalisasi titik kontrol."
    )
    BEZIER_USE_CURVED_BTN = "Aktifkan Mode Curved"
    BEZIER_RESET_BTN = "Reset Kurva"

    BTN_REVERT = "Revert to Global Defaults"
    TIP_REVERT = "Hapus override khusus area ini agar kembali mengikuti pengaturan global."
    BTN_CANCEL = "Batal"
    BTN_APPLY = "Terapkan"
    TIP_APPLY = "Simpan semua perubahan dan render ulang teks di kanvas."


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
