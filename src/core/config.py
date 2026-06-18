# Manga OCR & Typeset Tool v14.8.7
# ==============================
# ?? Import modul bawaan Python
# ==============================
import os
import sys
import json
import shutil
import copy

# ==============================
# ?? Library pihak ketiga (hanya yang dibutuhkan config)
# ==============================
import warnings
warnings.filterwarnings("ignore")

import pytesseract
import google.generativeai as genai

from PyQt5.QtCore import Qt

from src.utils.helpers import check_dependency, ensure_dependencies
from src.utils.crypto import encrypt_settings_keys, decrypt_settings_keys
from src.core.app_info import APP_VERSION

def get_effective_orientation(settings: dict, ocr_lang: str = ''):
    # SETTINGS may contain a 'lang_orientation' mapping like {'en': 'Horizontal', 'ja': 'Auto-Detect'}
    lang_map = SETTINGS.get('lang_orientation', {})
    # normalize short code
    code = (ocr_lang or '').lower()
    if code.startswith('en') and 'en' in lang_map:
        return lang_map.get('en')
    if code.startswith('ja') and 'ja' in lang_map:
        return lang_map.get('ja')
    # Fallback to per-job or global orientation
    return settings.get('orientation', SETTINGS.get('orientation', 'Auto-Detect'))

torch = check_dependency("torch")
is_gpu_available = torch.cuda.is_available() if torch else False

# --- Model Deteksi ---
onnxruntime = check_dependency("onnxruntime", "onnxruntime atau onnxruntime-gpu")
YOLO = None
try:
    from ultralytics import YOLO as YOLO_cls
    YOLO = YOLO_cls
except Exception as exc:
    pass

# --- Engine OCR ---
paddleocr = check_dependency("paddleocr", "paddleocr paddlepaddle")
doctr = check_dependency("doctr", "python-doctr[torch]")
RapidOCR = None
try:
    from rapidocr_onnxruntime import RapidOCR as RapidOCR_cls
    RapidOCR = RapidOCR_cls
except Exception as exc:
    pass

# --- [BARU] Engine Inpainting ---
lama_cleaner = check_dependency("lama_cleaner", "lama-cleaner")

# --- [BARU] API Provider ---
openai = check_dependency("openai", "openai")



# --- JSON-based settings (settings.json) ---
# Menentukan ROOT direktori aplikasi agar settings.json diakses secara seragam
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SETTINGS_PATH = os.path.join(ROOT_DIR, 'settings.json')


def default_settings() -> dict:
    if sys.platform.startswith('win'):
        default_tess = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    elif sys.platform.startswith('darwin'):
        default_tess = "/usr/local/bin/tesseract"
    else:
        default_tess = "/usr/bin/tesseract"
    return {
        "general": {
            "save_format": "PNG",  # PNG, WEBP, JPG
            "save_quality": 95
        },
        "apis": {
            "gemini": {"keys": []},
            "openai": {"keys": []},
            "deepl": {"keys": []},
            "google": {"keys": []},
            "openrouter": {"keys": []}
        },
        "tesseract": {
            "path": default_tess,
            "auto_detected": False
        }
        ,
        "cleanup": {
            "use_background_box": True,
            "use_inpaint": True,
            "apply_mode": "selected",
            "text_color_threshold": 128,
            "auto_text_color": True,   # <— BARU: bisa dimatikan dari Settings
            # When true, debug/temp files created by AI OCR and MOFRL (under ./temp/) will be removed after a run
            "constrain_text": True,
            "remove_ai_temp_files": False,
        },
        "typeset": {
            "outline_enabled": True,
            "outline_thickness": 2,  # legacy key, kept for backward compatibility
            "outline_width": 2.0,
            "outline_color": "#000000",
            "outline_style": "stroke",
        },
        "ocr": {
            "openrouter": {
                "url": "https://openrouter.ai/api/v1/chat/completions",
                "api_key": "",
                "models": []
            },
            "other": {
                "url": "",
                "api_key": "",
                "models": []
            }
        },
        "ocr_plugins": {
            "EasyOCR": True,
            "PaddleOCR": True,
            "DocTR": False,
            "RapidOCR": False
        },
        "translate": {
            "openrouter": {
                "url": "https://openrouter.ai/api/v1/chat/completions",
                "api_key": "",
                "models": []
            },
            "other": {
                "url": "",
                "api_key": "",
                "models": []
            }
        },
        "autosave": {
            "enabled": False,
            "interval_ms": 300000
        },
        "emergency_close": {
            "action_type": "url",
            "target": "https://youtube.com"
        }
    }


def save_settings(settings: dict, path: str = SETTINGS_PATH):
    """Save settings to disk using an atomic write via a temp file in the
    system temp directory.  Writing the temp file outside the project folder
    avoids the Windows ACL-inheritance problem where newly-created files
    inside the project directory don't receive the owner's FullControl ACE.
    """
    import time
    import tempfile
    tmp_fd = None
    tmp_path = None
    try:
        # Encrypt API keys before writing to disk
        encrypted = encrypt_settings_keys(settings)

        # Write to a temp file in the system temp directory first
        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.tmp', prefix='manga_settings_')
        with os.fdopen(tmp_fd, 'w', encoding='utf-8') as fh:
            tmp_fd = None  # fdopen takes ownership
            json.dump(encrypted, fh, ensure_ascii=False, indent=2)
            fh.flush()
            os.fsync(fh.fileno())

        # shutil.move works across drives and handles the rename
        max_retries = 10
        for i in range(max_retries):
            try:
                shutil.move(tmp_path, path)
                tmp_path = None  # successfully moved
                break
            except Exception as e:
                if i == max_retries - 1:
                    raise e
                time.sleep(0.1)
    except Exception as e:
        try:
            if tmp_fd is not None:
                os.close(tmp_fd)
        except Exception:
            pass
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        print(f"Failed to save settings.json: {e}", file=sys.stderr)


def _migrate_openrouter_key(settings: dict) -> None:
    """Migrate duplicate OpenRouter API keys to centralized apis.openrouter.keys.

    If ocr.openrouter.api_key or translate.openrouter.api_key contain a key but
    apis.openrouter.keys is empty, move the key to the centralized location and
    clear the per-section fields.
    """
    apis = settings.setdefault('apis', {})
    openrouter_apis = apis.setdefault('openrouter', {'keys': []})
    existing_keys = openrouter_apis.get('keys', [])

    # Only migrate if centralized store is empty
    if existing_keys:
        return

    # Collect candidate keys from ocr and translate sections
    candidate_key = ''
    for section in ('ocr', 'translate'):
        section_cfg = settings.get(section, {})
        or_cfg = section_cfg.get('openrouter', {})
        key = or_cfg.get('api_key', '').strip()
        if key and not candidate_key:
            candidate_key = key

    if candidate_key:
        openrouter_apis['keys'] = [{'name': 'Utama', 'value': candidate_key, 'active': True}]
        print("Info: OpenRouter API key berhasil dimigrasikan ke apis.openrouter.keys", file=sys.stderr)


def load_or_create_settings(path: str = SETTINGS_PATH) -> dict:
    import time
    try:
        if not os.path.exists(path):
            s = default_settings()
            save_settings(s, path)
            return s
            
        data = None
        max_retries = 10
        for i in range(max_retries):
            try:
                with open(path, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
                break
            except PermissionError as e:
                if i == max_retries - 1:
                    raise e
                time.sleep(0.1)
            except Exception:
                if i == max_retries - 1:
                    # Let other exceptions (like json parse errors) fall through
                    with open(path, 'r', encoding='utf-8') as fh:
                        data = json.load(fh)
                else:
                    time.sleep(0.1)

        # Decrypt API keys after reading from disk
        if isinstance(data, dict):
            decrypt_settings_keys(data)

        base = default_settings()
        # Shallow merge for top-level keys
        merged = base
        if isinstance(data, dict):
            merged.update(data)
        # Ensure providers exist
        merged.setdefault('apis', base['apis'])
        for p in base['apis'].keys():
            merged['apis'].setdefault(p, {'keys': []})
        merged.setdefault('tesseract', base['tesseract'])
        cleanup_defaults = base.get('cleanup', {})
        cleanup_settings = merged.setdefault('cleanup', {})
        for key, value in cleanup_defaults.items():
            cleanup_settings.setdefault(key, value)
        ocr_defaults = base.get('ocr', {})
        ocr_settings = merged.setdefault('ocr', {})
        for provider, defaults in ocr_defaults.items():
            provider_cfg = ocr_settings.setdefault(provider, {})
            provider_cfg.setdefault('url', defaults.get('url', ''))
            provider_cfg.setdefault('api_key', defaults.get('api_key', ''))
            models = provider_cfg.get('models')
            if not isinstance(models, list):
                provider_cfg['models'] = []
                models = provider_cfg['models']
            for model in models:
                if not isinstance(model, dict):
                    continue
                model.setdefault('name', '')
                model.setdefault('id', '')
                model['active'] = bool(model.get('active', False))
        translate_defaults = base.get('translate', {})
        translate_settings = merged.setdefault('translate', {})
        for provider, defaults in translate_defaults.items():
            provider_cfg = translate_settings.setdefault(provider, {})
            provider_cfg.setdefault('url', defaults.get('url', ''))
            provider_cfg.setdefault('api_key', defaults.get('api_key', ''))
            models = provider_cfg.get('models')
            if not isinstance(models, list):
                provider_cfg['models'] = []
                models = provider_cfg['models']
            for model in models:
                if not isinstance(model, dict):
                    continue
                model.setdefault('name', '')
                model.setdefault('id', '')
                model.setdefault('description', '')
                model['active'] = bool(model.get('active', True))
        autosave_defaults = base.get('autosave', {})
        autosave_settings = merged.setdefault('autosave', {})
        autosave_settings['enabled'] = bool(autosave_settings.get('enabled', autosave_defaults.get('enabled', False)))
        try:
            interval = int(autosave_settings.get('interval_ms', autosave_defaults.get('interval_ms', 300000)))
        except Exception:
            interval = autosave_defaults.get('interval_ms', 300000)
        autosave_settings['interval_ms'] = max(5000, interval)
        
        emergency_defaults = base.get('emergency_close', {})
        emergency_settings = merged.setdefault('emergency_close', {})
        for key, value in emergency_defaults.items():
            emergency_settings.setdefault(key, value)

        # Migrate duplicate OpenRouter keys to centralized location
        _migrate_openrouter_key(merged)

        return merged
    except Exception as e:
        print(f"Failed to load settings.json: {e}", file=sys.stderr)
        return default_settings()


# Load settings and expose simple getters for compatibility
SETTINGS = load_or_create_settings()


def get_active_key(provider_name: str) -> str:
    try:
        prov = SETTINGS.get('apis', {}).get(provider_name.lower(), {})
        for k in prov.get('keys', []) or []:
            if k.get('active'):
                return k.get('value') or ''
    except Exception:
        pass
    return ''


DEEPL_API_KEY = get_active_key('deepl')
GEMINI_API_KEY = get_active_key('gemini')
OPENAI_API_KEY = get_active_key('openai')
TESSERACT_PATH = SETTINGS.get('tesseract', {}).get('path', '')


def get_openrouter_api_key() -> str:
    """Return the active OpenRouter API key from the centralized apis.openrouter location.

    Falls back to ocr.openrouter.api_key or translate.openrouter.api_key for
    backward compatibility with settings files that haven't been migrated yet.
    """
    # 1. Try centralized location
    key = get_active_key('openrouter')
    if key:
        return key

    # 2. Fallback to per-section keys
    for section in ('translate', 'ocr'):
        section_cfg = SETTINGS.get(section, {})
        or_cfg = section_cfg.get('openrouter', {})
        k = or_cfg.get('api_key', '').strip()
        if k:
            return k
    return ''


def get_translate_provider_settings(provider_name: str) -> dict:
    """Return provider settings from the translate section.

    For OpenRouter, also injects the centralized API key if the per-section
    key is empty (backward compatibility during migration).
    """
    try:
        translate_cfg = SETTINGS.get('translate', {})
        cfg = translate_cfg.get(provider_name.lower(), {}) or {}
        # Inject centralized key for openrouter if not set locally
        if provider_name.lower() == 'openrouter' and not cfg.get('api_key', '').strip():
            cfg = dict(cfg)  # shallow copy to avoid mutation
            cfg['api_key'] = get_openrouter_api_key()
        return cfg
    except Exception:
        return {}

def refresh_api_clients():
    """Refresh global API key variables and reconfigure provider clients.

    Call this after modifying `SETTINGS` so the running application picks up
    newly added or activated API keys without needing to restart.
    """
    global DEEPL_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY, openai_client
    DEEPL_API_KEY = get_active_key('deepl')
    GEMINI_API_KEY = get_active_key('gemini')
    OPENAI_API_KEY = get_active_key('openai')

    # Reconfigure Gemini (google.generativeai)
    try:
        if GEMINI_API_KEY:
            try:
                genai.configure(api_key=GEMINI_API_KEY)
            except Exception as e:
                print(f"Gagal mengkonfigurasi Gemini API: {e}", file=sys.stderr)
    except Exception:
        pass

    # Recreate OpenAI client if available
    openai_client = None
    try:
        if openai and OPENAI_API_KEY:
            try:
                openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
            except Exception as e:
                print(f"Gagal mengkonfigurasi OpenAI API: {e}", file=sys.stderr)
    except Exception:
        pass

def detect_tesseract_and_update_settings():
    found = None
    if sys.platform.startswith('win'):
        cand = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.exists(cand):
            found = cand
    if not found and sys.platform.startswith('darwin'):
        cand = '/usr/local/bin/tesseract'
        if os.path.exists(cand):
            found = cand
    if not found:
        cand = '/usr/bin/tesseract'
        if os.path.exists(cand):
            found = cand
    if not found:
        try:
            which_out = shutil.which('tesseract')
            if which_out and os.path.exists(which_out):
                found = which_out
        except Exception:
            pass
    if found:
        SETTINGS.setdefault('tesseract', {})['path'] = found
        SETTINGS.setdefault('tesseract', {})['auto_detected'] = True
        save_settings(SETTINGS)
        return found
    SETTINGS.setdefault('tesseract', {})['auto_detected'] = False
    save_settings(SETTINGS)
    return ''


# If no valid tess path, attempt autodetect
if not TESSERACT_PATH or not os.path.exists(TESSERACT_PATH):
    detected = detect_tesseract_and_update_settings()
    if detected:
        TESSERACT_PATH = detected


# Configure APIs with active keys (best-effort) using centralized helper
openai_client = None

try:
    refresh_api_clients()
except Exception:
    pass


SELECTION_MODE_LABELS = [
    "Bubble Finder (Rect)",
    "Bubble Finder (Oval)",
    "Direct OCR (Rect)",
    "Direct OCR (Oval)",
    "Manual Text (Rect)",
    "Manual Text (Pen)",
    "Pen Tool",
    "Transform (Hand)",
    "Click-to-Translate"
]

SELECTION_MODE_SHORTCUT_KEYS = ["7", "8", "3", "4", "5", "6", "2", "1", "9"]

DEFAULT_SHORTCUTS = {
    'save_project': 'Ctrl+S',
    'load_project': 'Ctrl+O',
    'save_image': 'Ctrl+Shift+S',
    'undo': 'Ctrl+Z',
    'redo': 'Ctrl+Y',
    'emergency_close': 'MOUSE:double:Right',
}

for idx, default_key in enumerate(SELECTION_MODE_SHORTCUT_KEYS):
    DEFAULT_SHORTCUTS[f'selection_mode_{idx}'] = default_key

SHORTCUT_DEFINITIONS = [
    ('save_project', "Save Project", "File"),
    ('save_image', "Save Typeset Image", "File"),
    ('load_project', "Load Project", "File"),
    ('undo', "Undo Last Action", "Editing"),
    ('redo', "Redo Last Action", "Editing"),
    ('confirm_pen', "Confirm Pen Selection", "Selection Actions"),
    ('next', "Next Image/Page", "Navigation"),
    ('prev', "Previous Image/Page", "Navigation"),
    ('emergency_close', "Emergency Close & Exit", "General"),
]

for idx, label in enumerate(SELECTION_MODE_LABELS):
    SHORTCUT_DEFINITIONS.append(
        (f'selection_mode_{idx}', f"Switch to {label}", "Selection Modes")
    )

MOUSE_BUTTON_NAME_MAP = {
    Qt.LeftButton: 'Left',
    Qt.RightButton: 'Right',
    Qt.MiddleButton: 'Middle',
    Qt.BackButton: 'Back',
    Qt.ForwardButton: 'Forward',
    Qt.TaskButton: 'Task',
}

# --- Konfigurasi Manga-OCR ---
_MANGA_OCR_IMPORT_ERROR = None
_MANGA_OCR_IMPORT_CHECKED = False
try:
    from manga_ocr import MangaOcr
    _MANGA_OCR_IMPORT_CHECKED = True
except Exception as exc:
    MangaOcr = None
    _MANGA_OCR_IMPORT_ERROR = str(exc)
    _MANGA_OCR_IMPORT_CHECKED = True

def check_manga_ocr(force=False):
    global MangaOcr, _MANGA_OCR_IMPORT_ERROR, _MANGA_OCR_IMPORT_CHECKED
    if MangaOcr is not None:
        return True
    if _MANGA_OCR_IMPORT_CHECKED and not force:
        return False
    try:
        from manga_ocr import MangaOcr as MO
        MangaOcr = MO
        _MANGA_OCR_IMPORT_ERROR = None
        _MANGA_OCR_IMPORT_CHECKED = True
        return True
    except Exception as exc:
        _MANGA_OCR_IMPORT_ERROR = str(exc)
        _MANGA_OCR_IMPORT_CHECKED = True
        return False

def get_manga_ocr_import_error():
    return _MANGA_OCR_IMPORT_ERROR

def is_manga_ocr_installed():
    """Return True if the manga_ocr package is present on disk (without importing it).

    Uses importlib.util.find_spec so it never triggers DLL initialisation.
    Useful to distinguish "not installed" from "installed but DLL failed to load".
    """
    import importlib.util
    return importlib.util.find_spec("manga_ocr") is not None

# --- Konfigurasi Tesseract ---
IS_TESSERACT_AVAILABLE = False
try:
    if TESSERACT_PATH and os.path.exists(TESSERACT_PATH):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
        IS_TESSERACT_AVAILABLE = True
except Exception:
    pass

def reload_tesseract_availability():
    global TESSERACT_PATH, IS_TESSERACT_AVAILABLE
    TESSERACT_PATH = SETTINGS.get('tesseract', {}).get('path', '')
    IS_TESSERACT_AVAILABLE = False
    try:
        if TESSERACT_PATH and os.path.exists(TESSERACT_PATH):
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
            IS_TESSERACT_AVAILABLE = True
            return True
    except Exception:
        pass
    return False
