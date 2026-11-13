# Manga OCR & Typeset Tool v14.9.9.1
# ==============================
# ?? Import modul bawaan Python
# ==============================
import os
import re
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


def _normalize_font_token(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', str(name or '').lower())


_STYLE_SUFFIXES = (
    'bolditalic', 'regular', 'medium', 'semibold', 'italic',
    'roman', 'bold', 'ital', 'bld', 'reg', 'rom', 'bb',
)


def _strip_style_token(token: str) -> str:
    changed = True
    while changed and token:
        changed = False
        for suffix in _STYLE_SUFFIXES:
            if token.endswith(suffix) and len(token) > len(suffix) + 2:
                token = token[:-len(suffix)]
                changed = True
                break
    return token


class FontManager:
    """Utility class for loading and tracking custom font files."""

    SUPPORTED_EXTENSIONS = {".ttf", ".otf", ".ttc", ".otc"}

    def __init__(self, font_dir: str):
        self.font_dir = os.path.abspath(font_dir)
        self._fonts = {}
        self._family_lookup = {}
        self._family_variants = {}
        self._norm_display_lookup = {}
        self._default_display = "System Default"
        self.ensure_font_dir()
        self.reload_fonts()

    def ensure_font_dir(self):
        try:
            os.makedirs(self.font_dir, exist_ok=True)
        except OSError:
            pass

    def _index_font_entry(self, display_name: str, families: list[str]):
        norm_disp = _normalize_font_token(display_name)
        if norm_disp:
            self._norm_display_lookup[norm_disp] = display_name
        for fam in families:
            self._family_lookup[fam] = display_name
            norm_fam = _normalize_font_token(fam)
            if norm_fam:
                variants = self._family_variants.setdefault(norm_fam, [])
                if display_name not in variants:
                    variants.append(display_name)

    def reload_fonts(self):
        self._fonts.clear()
        self._family_lookup.clear()
        self._family_variants.clear()
        self._norm_display_lookup.clear()
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
            self._index_font_entry(self._default_display, [default_family])

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
            self._index_font_entry(display_name, families)

    def list_fonts(self):
        names = sorted(name for name, meta in self._fonts.items() if not meta.get('is_system'))
        return [self._default_display] + names

    def resolve_font_names(self, name: str) -> list[str]:
        """Resolve a display name, TTF/OTF family name, or alias to installed display names."""
        if not name or not isinstance(name, str):
            return []
        if name in self._fonts:
            return [name]

        tok = _normalize_font_token(name)
        if not tok:
            return []
        if tok in self._family_variants:
            return list(self._family_variants[tok])
        if tok in self._norm_display_lookup:
            return [self._norm_display_lookup[tok]]

        # Try matching base token without style/version numbers (e.g. "Anime Ace 3" -> "Anime Ace 2.0 BB",
        # "Komika Axis Bold" -> "Komika Axis", "SF Comic Script Bold" -> "SF Comic Script").
        candidates = []
        base_tok = _strip_style_token(tok)
        no_digit_tok = re.sub(r'[0-9]+', '', base_tok)
        for search_tok in (base_tok, no_digit_tok):
            if len(search_tok) < 4:
                continue
            if search_tok in self._family_variants:
                return list(self._family_variants[search_tok])
            for fam_tok, displays in self._family_variants.items():
                fam_base = re.sub(r'[0-9]+', '', _strip_style_token(fam_tok))
                if fam_tok == search_tok or fam_base == search_tok or (
                    len(search_tok) >= 6 and (fam_tok.startswith(search_tok) or fam_base.startswith(search_tok))
                ):
                    for d in displays:
                        if d not in candidates:
                            candidates.append(d)
            if candidates:
                return candidates
            for disp_tok, disp in self._norm_display_lookup.items():
                if disp_tok.startswith(search_tok) and disp not in candidates:
                    candidates.append(disp)
            if candidates:
                return candidates
        return []

    def resolve_primary_font(self, name: str) -> str | None:
        matches = self.resolve_font_names(name)
        if not matches:
            return None
        for prefer in ('roman', 'regular', 'reg', 'normal'):
            for m in matches:
                if prefer in m.lower():
                    return m
        return matches[0]

    def has_font(self, display_name: str) -> bool:
        return bool(self.resolve_font_names(display_name))

    @property
    def default_display(self) -> str:
        return self._default_display

    def create_qfont(self, display_name: str, base_font: QFont | None = None) -> QFont:
        font = QFont(base_font) if isinstance(base_font, QFont) else QFont()
        meta = self._fonts.get(display_name)
        if not meta:
            resolved = self.resolve_primary_font(display_name)
            meta = self._fonts.get(resolved) if resolved else None
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
        self._index_font_entry(display_name, families)
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


def fonts_in_group(fonts, group_members, font_manager: FontManager | None = None) -> list:
    """Filter font list to members of a group, resolving family names and filename stems."""
    manager = font_manager or GLOBAL_FONT_MANAGER
    allowed = set()
    norm_allowed = set()
    for member in (group_members or []):
        if not isinstance(member, str) or not member.strip():
            continue
        allowed.add(member)
        norm_tok = _normalize_font_token(member)
        if norm_tok:
            norm_allowed.add(norm_tok)
        if manager is not None and callable(getattr(manager, "resolve_font_names", None)):
            allowed.update(manager.resolve_font_names(member))

    result = []
    for f in fonts:
        if f in allowed or _normalize_font_token(f) in norm_allowed:
            result.append(f)
    return result


def resolve_smart_font_for_text(font_groups: dict | None, translated_text: str, font_manager: FontManager | None = None) -> str | None:
    """Pick the best font for translated dialogue tone, resolving installed families before downloading."""
    if not isinstance(font_groups, dict):
        return None
    group_name = "Dialog Normal"
    if translated_text:
        text_upper = translated_text.upper()
        if (translated_text == text_upper and sum(1 for c in translated_text if c.isalpha()) > 3) or "!!!" in translated_text:
            group_name = "Marah / Berteriak"
        elif "..." in translated_text or (translated_text.startswith("(") and translated_text.endswith(")")):
            group_name = "Berbisik / Pelan"
        elif "!?" in translated_text or "?!" in translated_text:
            group_name = "Kaget / Shock" if "Kaget / Shock" in font_groups else "Kaget / Shock / Tersentak"

    members = font_groups.get(group_name) or font_groups.get("Dialog Normal") or []
    if not members:
        return None

    manager = font_manager or GLOBAL_FONT_MANAGER
    resolve_primary = getattr(manager, "resolve_primary_font", None)
    if callable(resolve_primary):
        for candidate in members:
            resolved = resolve_primary(candidate)
            if resolved:
                return resolved

    chosen_font = members[0]
    from src.utils.dafont import DaFontDownloader
    if manager and not manager.has_font(chosen_font):
        dl_dir = os.path.join("temp", "downloaded_fonts")
        path = DaFontDownloader.search_and_download(chosen_font, dl_dir)
        if path:
            try:
                manager.import_font(path)
            except Exception as e:
                print(f"Failed to import downloaded font: {e}")

    if manager and manager.has_font(chosen_font):
        return (resolve_primary(chosen_font) if callable(resolve_primary) else None) or chosen_font
    return None


def set_global_font_manager(manager: FontManager):
    global GLOBAL_FONT_MANAGER
    GLOBAL_FONT_MANAGER = manager


def get_font_manager() -> FontManager | None:
    return GLOBAL_FONT_MANAGER
