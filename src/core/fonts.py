# Manga OCR & Typeset Tool v14.9.0
# ==============================
# ?? Import modul bawaan Python
# ==============================
import os
import shutil

# ==============================
# ?? Library pihak ketiga
# ==============================
# (tidak ada impor pihak ketiga yang dibutuhkan)

# ==============================
# ?? PyQt5 (dibagi per kategori)
# ==============================
from PyQt5.QtGui import (
    QFont, QFontDatabase
)


class FontManager:
    """Utility class for loading and tracking custom font files."""

    SUPPORTED_EXTENSIONS = {".ttf", ".otf", ".ttc", ".otc"}

    def __init__(self, font_dir: str):
        self.font_dir = os.path.abspath(font_dir)
        self._fonts = {}
        self._family_lookup = {}
        self._default_display = "System Default"
        self.ensure_font_dir()
        self.reload_fonts()

    def ensure_font_dir(self):
        try:
            os.makedirs(self.font_dir, exist_ok=True)
        except OSError:
            pass

    def reload_fonts(self):
        self._fonts.clear()
        self._family_lookup.clear()
        self.ensure_font_dir()

        default_font = QFont()
        default_family = default_font.family()
        self._fonts[self._default_display] = {
            'display': self._default_display,
            'path': None,
            'families': [default_family] if default_family else [],
            'font_id': None,
            'is_system': True,
        }
        if default_family:
            self._family_lookup[default_family] = self._default_display

        for entry in sorted(os.listdir(self.font_dir)):
            path = os.path.join(self.font_dir, entry)
            if not os.path.isfile(path):
                continue
            ext = os.path.splitext(entry)[1].lower()
            if ext not in self.SUPPORTED_EXTENSIONS:
                continue
            display_name = os.path.splitext(entry)[0]
            font_id = QFontDatabase.addApplicationFont(path)
            if font_id == -1:
                continue
            families = QFontDatabase.applicationFontFamilies(font_id)
            if not families:
                QFontDatabase.removeApplicationFont(font_id)
                continue
            self._fonts[display_name] = {
                'display': display_name,
                'path': path,
                'families': families,
                'font_id': font_id,
                'is_system': False,
            }
            for fam in families:
                self._family_lookup[fam] = display_name

    def list_fonts(self):
        names = sorted(name for name, meta in self._fonts.items() if not meta.get('is_system'))
        return [self._default_display] + names

    def has_font(self, display_name: str) -> bool:
        return display_name in self._fonts

    @property
    def default_display(self) -> str:
        return self._default_display

    def create_qfont(self, display_name: str, base_font: QFont | None = None) -> QFont:
        font = QFont(base_font) if isinstance(base_font, QFont) else QFont()
        meta = self._fonts.get(display_name)
        if not meta:
            return font
        families = meta.get('families') or []
        if families:
            font.setFamily(families[0])
        return font

    def display_name_for_font(self, font: QFont | None, fallback: str | None = None) -> str:
        if not isinstance(font, QFont):
            return fallback or self._default_display
        family = font.family()
        if family and family in self._family_lookup:
            return self._family_lookup[family]
        return fallback or self._default_display

    def import_font(self, source_path: str) -> str:
        if not source_path:
            raise ValueError("Missing font path")

        ext = os.path.splitext(source_path)[1].lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported font format: {ext}")

        display_name = os.path.splitext(os.path.basename(source_path))[0]
        dest_path = os.path.join(self.font_dir, os.path.basename(source_path))

        if os.path.exists(dest_path) or self.has_font(display_name):
            raise FileExistsError(f"Font '{display_name}' already exists")

        shutil.copy2(source_path, dest_path)
        registered = self._register_font_file(dest_path)
        if not registered:
            try:
                os.remove(dest_path)
            except OSError:
                pass
            raise RuntimeError(f"Failed to load font '{display_name}'")
        return registered

    def _register_font_file(self, path: str) -> str | None:
        font_id = QFontDatabase.addApplicationFont(path)
        if font_id == -1:
            return None
        families = QFontDatabase.applicationFontFamilies(font_id)
        if not families:
            QFontDatabase.removeApplicationFont(font_id)
            return None
        display_name = os.path.splitext(os.path.basename(path))[0]
        self._fonts[display_name] = {
            'display': display_name,
            'path': path,
            'families': families,
            'font_id': font_id,
            'is_system': False,
        }
        for fam in families:
            self._family_lookup[fam] = display_name
        return display_name


GLOBAL_FONT_MANAGER: FontManager | None = None


def build_font(
    font_manager: FontManager | None,
    display: str | None = None,
    fallback_font: QFont | None = None,
    size: float | None = None,
    bold: bool | None = None,
    italic: bool | None = None,
    underline: bool | None = None,
    char_spacing: float | None = None,
) -> QFont:
    """Rakit QFont dari pilihan pengguna, tanpa menyentuh widget apa pun.

    Sumber font dipilih berurutan: font_manager+display, lalu fallback_font,
    lalu Arial 14.

    bold/italic/underline bernilai None berarti "jangan diutak-atik" -- gaya
    bawaan font dipertahankan. Ini menjaga perilaku asli, yang hanya memanggil
    setBold() bila widget toggle-nya memang ada.
    """
    if font_manager and display:
        font = font_manager.create_qfont(display)
    elif isinstance(fallback_font, QFont):
        font = QFont(fallback_font)
    else:
        font = QFont('Arial', 14)

    size_value = float(size) if size is not None else 24.0
    if size_value <= 0:
        size_value = 12.0
    font.setPointSizeF(size_value)

    if bold is not None:
        font.setBold(bold)
    if italic is not None:
        font.setItalic(italic)
    if underline is not None:
        font.setUnderline(underline)

    font.setLetterSpacing(QFont.PercentageSpacing, char_spacing or 100.0)
    return font


def fonts_in_group(fonts, group_members) -> list:
    """Saring daftar font ke anggota satu grup, mempertahankan urutan asli.

    Nama yang terdaftar di grup tapi fontnya tidak terpasang akan hilang dengan
    sendirinya -- itu memang perilaku yang diharapkan.
    """
    allowed = set(group_members or [])
    return [f for f in fonts if f in allowed]


def set_global_font_manager(manager: FontManager):
    global GLOBAL_FONT_MANAGER
    GLOBAL_FONT_MANAGER = manager


def get_font_manager() -> FontManager | None:
    return GLOBAL_FONT_MANAGER
