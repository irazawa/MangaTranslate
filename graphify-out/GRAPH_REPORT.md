# Graph Report - MangaTranslate  (2026-07-07)

## Corpus Check
- 34 files · ~182,983 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1522 nodes · 3744 edges · 72 communities (52 shown, 20 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 310 edges (avg confidence: 0.6)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6aa1454f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]

## God Nodes (most connected - your core abstractions)
1. `MangaOCRApp` - 476 edges
2. `TypesetArea` - 73 edges
3. `VideoPlayerWidget` - 60 edges
4. `AdvancedTextEditDialog` - 55 edges
5. `SettingsCenterDialog` - 54 edges
6. `SelectableImageLabel` - 47 edges
7. `SettingsWorkspace` - 36 edges
8. `notify_toast()` - 34 edges
9. `CurvesGraphWidget` - 33 edges
10. `FontDelegate` - 32 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `MangaOCRApp`  [EXTRACTED]
  main.py → src/ui/main_window.py
- `_run_first_run_setup()` --calls--> `run_bootstrap_setup()`  [EXTRACTED]
  launcher_app.py → src/ui/bootstrap_setup.py
- `main()` --calls--> `StartupSplash`  [EXTRACTED]
  main.py → src/ui/startup_splash.py
- `main()` --calls--> `apply_appearance_from_settings_file()`  [EXTRACTED]
  main.py → src/ui/theme.py
- `FileDownloadWorker` --uses--> `EnhancedResult`  [INFERRED]
  src/ui/main_window.py → src/core/models.py

## Import Cycles
- None detected.

## Communities (72 total, 20 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (22): ResultCache, FontManager, get_font_manager(), Utility class for loading and tracking custom font files., set_global_font_manager(), EnhancedResult, AutoDetectorSignals, AutoDetectorWorker (+14 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (18): date, QWidget, _format_duration(), _format_money(), _format_number(), Embedded Settings workspace for the main window., Compact GitHub-style activity grid for token usage., Main-window settings surface with profile, usage, help, and settings. (+10 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (13): QColor, QFont, QIcon, QImage, QPainter, QPointF, Choose outline color based on the text color using luminance rules.          - I, Render text directly on the image without drawing any background boxes or fills. (+5 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (34): configure_windows_app_id(), main(), show_main_window(), Animated startup splash screen for MangaTranslate., Small indeterminate spinner used by the startup splash., Loading window shown while the main application initializes., SpinnerWidget, StartupSplash (+26 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (9): Mengirimkan desktop notification menggunakan QSystemTrayIcon secara lazy., Mengonversi path ke path absolut Windows Long Path (\\\\?\\prefix) jika berjalan, Export semua halaman yang sudah di-typeset ke format CBZ (Comic Book Zip)., Salin area typeset yang dipilih ke clipboard., Batch send all PF entries (original text only) to AI for contextual translation., Returns (provider, model_name) from current global SETTINGS., Batch send all QC entries (translated text) to AI for style/tone validation., Try to parse AI response as JSON array first. If that fails, fall back to line-s (+1 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (10): TypesetArea, coerce_float(), coerce_int(), dict_to_rect(), list_to_polygon(), polygon_to_list(), Serialize a polygon to a list.      When *compact* is True (default, schema v4+), Deserialize a polygon from a list.      Supports both the compact ``[[x, y], ... (+2 more)

### Community 6 - "Community 6"
Cohesion: 0.07
Nodes (12): Navigasi mundur satu langkah di undo history timeline., Navigasi maju satu langkah di undo history timeline., Update enabled state tombol Undo dan Redo berdasarkan snapshot history., Ambil snapshot deep-copy dari typeset_areas sebelum perubahan.         Push ke _, Restore typeset_areas dari snapshot ke-idx di _undo_history., Perbarui QListWidget timeline dengan seluruh undo history., Handler saat user klik item di undo timeline — jump ke snapshot tersebut., Bersihkan seluruh undo history timeline. (+4 more)

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (3): Legacy placeholder retained for backward compatibility., Memuat default presets dari settings.json dan menerapkan ke UI., Populate the typeset font dropdown. Optionally filter by a font group name.

### Community 8 - "Community 8"
Cohesion: 0.09
Nodes (3): Menetapkan item yang terdeteksi untuk konfirmasi pengguna., Membatalkan item yang menunggu konfirmasi., SelectableImageLabel

### Community 9 - "Community 9"
Cohesion: 0.09
Nodes (3): QTextCursor, AdvancedTextEditDialog, Populate the dialog font combo, optionally filtering by a group name provided by

### Community 10 - "Community 10"
Cohesion: 0.07
Nodes (6): Membuka dialog Find and Replace teks terjemahan global., Memproses item yang telah dikonfirmasi oleh pengguna., Memproses klik pengguna pada kanvas untuk mendeteksi balon teks secara asinkron, Called when user clicks Next; navigate to the next image without forcing an auto, Try to open an image robustly:          1) normal Image.open().convert('RGB'), Memproses poligon yang koordinatnya sudah dalam sistem gambar penuh (unzoomed).

### Community 11 - "Community 11"
Cohesion: 0.06
Nodes (7): Detect text regions and return recognized text polygons., Group nearby text boxes into cohesive reading blocks., [DIUBAH] Menjalankan OCR pada gambar yang diberikan berdasarkan pengaturan., MOFRL-GPT: OCR berbasis GPT multimodal (OpenAI/Gemini/OpenRouter)         Ambil, Membangun string tambahan untuk prompt AI berdasarkan pengaturan., Terjemahkan teks manga via OpenAI Chat Completions.         - Gunakan caching un, robust_post()

### Community 12 - "Community 12"
Cohesion: 0.05
Nodes (38): 1. AI Chatbot Assistant (🤖 AI Chatbot), 1. Bootloader & Zero-Configuration Environment (`launcher.bat`), 1. Persistent Local Cache (`ocr_translation_cache.json`), 1. Photoshop & Canva-Style Layers Panel, 1. Pipeline Standar (Standard Pipeline), 1. Skema Proyek Portabel (Schema Version 4), 1. Tab Proofreader (Batch PF), 2. Enkripsi API Key Kredensial (+30 more)

### Community 13 - "Community 13"
Cohesion: 0.07
Nodes (10): app_title(), Application identity and version metadata., Isi ulang grid kartu recent projects dari SETTINGS., Buat satu kartu recent project., Refresh kartu recent projects di welcome screen tanpa rebuild seluruh widget., Hapus satu entri dari recent projects list., Membangun ulang submenu Recent Projects dari settings., Tambahkan path project ke recent projects (max 10 entri). (+2 more)

### Community 14 - "Community 14"
Cohesion: 0.12
Nodes (16): _base_dir(), _creation_flags(), main(), _message_box(), _needs_first_run_setup(), _prepare_path(), _run_first_run_setup(), _run_main_app() (+8 more)

### Community 15 - "Community 15"
Cohesion: 0.09
Nodes (10): MouseButton, QAction, QWheelEvent, Dispatch a mouse shortcut if configured. event_type in {'press','release','doubl, Menangani event scroll mouse untuk mengganti item., Shortcut field that can capture keyboard or mouse buttons (incl. extra/back/pen, ScrollableComboBox, ShortcutCaptureEdit (+2 more)

### Community 16 - "Community 16"
Cohesion: 0.12
Nodes (18): QDialog, QStyledItemDelegate, APIManagerDialog, _find_media_executable(), get_media_dependency_status(), ManualTextDialog, MediaDependenciesInstallWorker, _python_module_available() (+10 more)

### Community 17 - "Community 17"
Cohesion: 0.12
Nodes (3): State, A highly polished premium Video Player widget with local Media Library and YouTu, VideoPlayerWidget

### Community 18 - "Community 18"
Cohesion: 0.15
Nodes (20): QThread, AIChatWidget, A wrapper widget that hosts both the AI Chatbot and a Video Player,     allowing, PipInstallWorker, FileDownloadWorker, FindReplaceWorker, FullPageTranslateWorker, # NOTE: Do NOT call _sync_typeset_controls_from_selection() here. (+12 more)

### Community 20 - "Community 20"
Cohesion: 0.07
Nodes (28): ask_user_input_v0, bash_tool, Content safety, conversation_search, create_file, Critical NEVER search for images in following categories (blocked):, Examples of when **NOT** to use image search:, fetch_sports_data (+20 more)

### Community 22 - "Community 22"
Cohesion: 0.13
Nodes (5): Hapus baris yang dipilih dari tabel glossary., Kumpulkan semua pasangan term dari tabel menjadi dict., Unified settings dialog — modern sidebar navigation layout., Switch stacked page when user clicks nav item., SettingsCenterDialog

### Community 23 - "Community 23"
Cohesion: 0.19
Nodes (4): AIChatWidgetContent, Returns (provider, model_id) for the currently selected combo item., Insert before the trailing stretch (which keeps bubbles top-aligned)., Full-featured AI chatbot widget to be embedded as a tab inside     the Tools & W

### Community 25 - "Community 25"
Cohesion: 0.16
Nodes (10): get_active_key(), get_openrouter_api_key(), get_translate_provider_settings(), Return the active OpenRouter API key from the centralized apis.openrouter locati, Return provider settings from the translate section.      For OpenRouter, also i, Refresh global API key variables and reconfigure provider clients.      Call thi, refresh_api_clients(), ChatStreamWorker (+2 more)

### Community 26 - "Community 26"
Cohesion: 0.21
Nodes (4): Tambahkan baris baru ke tabel glossary., Helper: returns (scroll_area, inner_layout) for a settings page., Returns a styled header widget for a page., Returns a horizontal row: label+desc on left, widget on right.

### Community 27 - "Community 27"
Cohesion: 0.18
Nodes (6): Alignment, _kind_color(), NotificationCenter, _NotificationFrame, Overlay manager for toast and banner notifications., notification_frame_qss()

### Community 28 - "Community 28"
Cohesion: 0.11
Nodes (18): After search, Connector directory first, Data Scope, Design guidance, Error Handling, Explicit triggers, Key Design Pattern, Limitations (+10 more)

### Community 29 - "Community 29"
Cohesion: 0.17
Nodes (6): QFrame, QLabel, QToolButton, Forward refresh_models call to the active chatbot widget., Animated three-dot typing indicator shown while AI is responding., TypingIndicator

### Community 30 - "Community 30"
Cohesion: 0.13
Nodes (6): QScrollArea, Bangun widget welcome screen yang indah dengan quick actions dan recent projects, Tampilkan dialog statistik project saat ini., Modern icon-sidebar + stacked-widget layout untuk Tools & Workspace panel., Switch stacked widget page and update sidebar button states., Apply modern dark sidebar skin to the Tools & Workspace column.

### Community 31 - "Community 31"
Cohesion: 0.20
Nodes (4): ModelEditDialog, OpenRouterSettingsPanel, table_header_qss(), table_qss()

### Community 32 - "Community 32"
Cohesion: 0.19
Nodes (8): dismiss_banner(), _notification_center_for(), notify_banner(), notify_toast(), Non-blocking in-app notifications for the main PyQt UI., _status_fallback(), Ambil ulang harga dari OpenRouter API dan refresh tabel., Scans src/data/video/ and src/data/music/ for media files.

### Community 35 - "Community 35"
Cohesion: 0.14
Nodes (6): FFmpegWorker, Runs an FFmpeg process in a background thread and monitors it., A dummy logger to silence yt-dlp console output warnings., Fetches direct video/audio stream URLs or playlist entries from a YouTube link., YouTubeUrlExtractor, YtdlDummyLogger

### Community 36 - "Community 36"
Cohesion: 0.15
Nodes (10): check_manga_ocr(), get_manga_ocr_import_error(), is_manga_ocr_installed(), Return True if the manga_ocr package is present on disk (without importing it)., easyocr_error_message(), get_easyocr_module(), Import EasyOCR lazily so Torch DLL failures do not block app startup., Mengisi daftar bahasa dari semua engine yang tersedia. (+2 more)

### Community 37 - "Community 37"
Cohesion: 0.14
Nodes (5): Save settings to disk using an atomic write via a temp file in the     system te, save_settings(), Callback dari UnifiedHelpDialog saat user menyimpan perubahan harga.         Upd, Instance handler to persist per-language orientation overrides into SETTINGS., compact_primary_button_qss()

### Community 38 - "Community 38"
Cohesion: 0.18
Nodes (5): ChatHistoryManager, HistoryDialog, Auto-generate a session title from the first user message., Handles loading, saving, listing and deleting chat sessions from disk., Dialog to browse and select from past chat sessions.

### Community 39 - "Community 39"
Cohesion: 0.18
Nodes (5): commands: list of pip-install arg-lists run sequentially.         Each inner lis, Dialog analitik sesi: menampilkan API usage per provider/model     sebagai grafi, Buat label section header dengan separator., Buat QFrame 'card' dengan shadow styling., SessionAnalyticsDialog

### Community 40 - "Community 40"
Cohesion: 0.20
Nodes (5): ChatBubble, A styled bubble displaying one chat message (user or assistant).     Fills the f, Split text into a list of (type, content, lang) tuples.         type is "text" o, Convert inline markdown (bold, italic, inline-code) and newlines to HTML., Copy the entire raw message text to clipboard.

### Community 41 - "Community 41"
Cohesion: 0.21
Nodes (9): default_settings(), detect_tesseract_and_update_settings(), get_effective_orientation(), load_or_create_settings(), _migrate_openrouter_key(), Migrate duplicate OpenRouter API keys to centralized apis.openrouter.keys., reload_tesseract_availability(), check_dependency() (+1 more)

### Community 42 - "Community 42"
Cohesion: 0.20
Nodes (3): Initializes engines that don't depend on user input, like Manga-OCR and language, Mengisi daftar model AI yang tersedia dari semua provider., Mengambil data harga model OpenRouter secara dinamis dari API models resmi OpenR

### Community 43 - "Community 43"
Cohesion: 0.23
Nodes (3): CurvesGraphWidget, Photoshop-style curves adjustment graph (0-255 input vs 0-255 output) with splin, Allows drawing a gray-shaded histogram behind the curves line.

### Community 50 - "Community 50"
Cohesion: 0.39
Nodes (8): _decrypt_in_place(), decrypt_settings_keys(), _encrypt_dict(), encrypt_settings_keys(), _get_fernet(), _is_secret_key(), Encrypt settings keys on save., Decrypt settings keys on load. Keys are mutated in-place.

### Community 51 - "Community 51"
Cohesion: 0.25
Nodes (7): CLAUDE.md - MangaTranslate Project Standard, 🛑 Completion Gate & Handoff, 🧠 Core Principles (Adapted from claude-fable-5.md), 🕸️ Graphify (Mandatory Architecture Check), 📚 Skills & MCP Integration, 🚀 Startup & Operating Loop, 👥 Subagents & Team Workflow ("The Chef Team")

### Community 53 - "Community 53"
Cohesion: 0.25
Nodes (3): ImageCurvesDialog, Photoshop-style dialog for adjusting image contrast/brightness via natural splin, Launches the Photoshop-style Curves adjustment dialog.

### Community 54 - "Community 54"
Cohesion: 0.48
Nodes (4): get_tessdata_path(), get_writable_tessdata_path(), sync_tessdata_files(), uninstall_tessdata_lang()

### Community 57 - "Community 57"
Cohesion: 0.40
Nodes (5): CRITICAL BROWSER STORAGE RESTRICTION, Step 0 — Does the request need a visual at all?, Step 1 — Is a connected MCP tool a fit?, Step 2 — Did the person ask for a file?, Step 3 — Visualizer (default inline visual)

### Community 61 - "Community 61"
Cohesion: 0.50
Nodes (4): Do NOT use artifacts for, HTML, Markdown, React

## Knowledge Gaps
- **85 isolated node(s):** `🚀 Startup & Operating Loop`, `🕸️ Graphify (Mandatory Architecture Check)`, `🧠 Core Principles (Adapted from claude-fable-5.md)`, `👥 Subagents & Team Workflow ("The Chef Team")`, `📚 Skills & MCP Integration` (+80 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MangaOCRApp` connect `Community 21` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 10`, `Community 11`, `Community 13`, `Community 15`, `Community 16`, `Community 18`, `Community 19`, `Community 25`, `Community 27`, `Community 30`, `Community 33`, `Community 34`, `Community 36`, `Community 37`, `Community 42`, `Community 45`, `Community 47`, `Community 48`, `Community 49`, `Community 53`, `Community 55`, `Community 60`, `Community 62`, `Community 65`, `Community 66`?**
  _High betweenness centrality (0.462) - this node is a cross-community bridge._
- **Why does `TypesetArea` connect `Community 5` to `Community 6`, `Community 39`, `Community 8`, `Community 9`, `Community 44`, `Community 13`, `Community 16`, `Community 18`, `Community 52`, `Community 53`, `Community 22`, `Community 21`, `Community 59`, `Community 31`?**
  _High betweenness centrality (0.134) - this node is a cross-community bridge._
- **Why does `VideoPlayerWidget` connect `Community 17` to `Community 32`, `Community 1`, `Community 35`, `Community 38`, `Community 40`, `Community 46`, `Community 18`, `Community 23`, `Community 56`, `Community 25`, `Community 58`, `Community 29`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `MangaOCRApp` (e.g. with `EnhancedResult` and `TypesetArea`) actually correct?**
  _`MangaOCRApp` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `TypesetArea` (e.g. with `AdvancedTextEditDialog` and `APIManagerDialog`) actually correct?**
  _`TypesetArea` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `VideoPlayerWidget` (e.g. with `AIChatWidget` and `AIChatWidgetContent`) actually correct?**
  _`VideoPlayerWidget` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `AdvancedTextEditDialog` (e.g. with `TypesetArea` and `AppearanceText`) actually correct?**
  _`AdvancedTextEditDialog` has 6 INFERRED edges - model-reasoned connections that need verification._