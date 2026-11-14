# Manga OCR & Typeset Tool v14.9.9.3
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


FONT_GROUPS_VERSION = 2

_LEGACY_FONT_ALIASES = frozenset({
    "CC Wild Words",
    "Anime Ace 3",
    "Badaboom BB",
    "Komika Axis Bold",
    "Patrick Hand",
    "Shadows Into Light",
    "Amatic SC",
    "Caveat",
    "Sacramento",
    "Great Vibes",
    "SF Comic Script Bold",
    "Komika Slick",
    "Creepster",
    "Feast of Flesh BB",
    "Komika Display",
})

DEFAULT_FONT_GROUPS: dict[str, list[str]] = {
    "Dialog Normal": [
        "CC Wild Words Roman",
        "CC Wild Words Italic",
        "CC Wild Words Bold Italic",
        "mangat",
        "mangatb",
        "mangati",
        "animeace2_reg",
        "animeace2_bld",
        "animeace2_ital",
        "ComicNeue-Regular",
        "ComicNeue-Bold",
        "ComicNeue-Italic",
        "ComicNeueSansID",
        "BalsamiqSans-Regular",
        "BalsamiqSans-Bold",
        "BalsamiqSans-Italic",
        "KOMTXT__",
        "KOMTXTB_",
        "KOMTXTI_",
        "KOMTXTBI",
        "KOMTXTT_",
        "KOMTXTTI",
        "KOMTXTK_",
        "KOMTXTKB",
        "KOMTXTKI",
        "KOMTXKBI",
        "Comic Book",
        "Comic Book Bold",
        "Comic Book Italic",
        "Comic Book Bold Italic",
        "adam",
        "adamb",
        "adambital",
        "manga_speak",
        "manga_speak_bold",
        "ArchitectsDaughter-Regular",
        "Gilles_Handwriting",
    ],
    "Marah / Berteriak": [
        "BADABB__",
        "Bangers-Regular",
        "LuckiestGuy-Regular",
        "mouthbrebb",
        "mouthbrebb_b",
        "deathrattlebb_reg",
        "KOMIKAX_",
        "Action Comics",
        "Action Comics Black",
        "Ka Blam",
        "Ka Blam Under",
        "Ka-Boing!",
        "Bigdex",
        "AVENGEANCE MIGHTIEST AVENGER",
        "intsh",
        "intshc",
        "intshe",
        "intshl",
        "intsho",
        "iwantv2",
        "iwantv2b",
        "iwantv2c",
        "iwantv2e",
        "iwantv2s",
        "KOMIKJ__",
        "KOMIKJI_",
    ],
    "Berbisik / Pelan": [
        "PatrickHand-Regular",
        "ShadowsIntoLight-Regular",
        "Kalam-Regular",
        "Kalam-Bold",
        "IndieFlower-Regular",
        "KOMIKAH_",
        "KOMIKAHB",
        "KOMIKHI_",
        "KOMIKHBI",
        "KOMIKASL",
        "KOMIKSLI",
        "left hand comic",
        "arfmoochikncheez",
        "dnk",
        "The Kids Mraker",
        "The Last Comic On Earth",
        "Think Smart ",
        "Wigglye",
        "SketchyComic",
    ],
    "Santai / Ke-enakan": [
        "ShortStack-Regular",
        "Mali-Regular",
        "Mali-Bold",
        "AmaticSC-Regular",
        "AmaticSC-Bold",
        "Caveat-Regular",
        "Caveat-Medium",
        "Caveat-SemiBold",
        "Caveat-Bold",
        "Caveat-VariableFont_wght",
        "Comico",
        "Smile Candy",
        "Poppin-Story",
        "Happy Night",
        "Autumn Crush",
        "Really Big",
        "Trailer Park Girl",
    ],
    "Cute / Shoujo / Chibi": [
        "Mali-Regular",
        "Mali-Bold",
        "ShortStack-Regular",
        "Courgette-Regular",
        "IndieFlower-Regular",
        "Smile Candy",
        "Poppin-Story",
        "Happy Night",
        "Autumn Crush",
        "BalsamiqSans-Regular",
        "BalsamiqSans-Italic",
        "AmaticSC-Regular",
        "Caveat-Regular",
    ],
    "Sexy / Intim": [
        "Love Marker",
        "Love Marker Italic",
        "Courgette-Regular",
        "Sacramento-Regular",
        "GreatVibes-Regular",
        "PlayfairDisplay-VariableFont_wght",
        "PlayfairDisplay-Italic-VariableFont_wght",
    ],
    "Kaget / Shock": [
        "SF Comic Script Bold",
        "SF Comic Script",
        "SF Comic Script Condensed",
        "SF Comic Script Extended",
        "SF Comic Script Outline",
        "SF Comic Script Shaded",
        "SF Slapstick Comic",
        "SF Slapstick Comic Bold",
        "SF Slapstick Comic Oblique",
        "SF Slapstick Comic Bold Oblique",
        "SF Slapstick Comic Shaded",
        "SF Slapstick Comic Shaded Oblique",
        "KOMIKASK",
        "KOMIKSKI",
        "KOMIKSLI",
        "Outrun future",
        "Outrun future Bold",
        "Outrun future Bold Italic",
        "Ka-Boing!",
        "Bangers-Regular",
    ],
    "Tegang / Horor": [
        "Creepster-Regular",
        "Nosifer-Regular",
        "FEASFBRG",
        "FEASFBI_",
        "deathrattlebb_reg",
        "KOMIKAB_",
        "KOMIKAP_",
        "KOMIKAGL",
        "Danger Diabolik",
        "Night Shift - Demo",
        "Ape Shit ",
        "DirtyBrush",
        "LaPicaDemo-LaPicaDemo",
        "#44v2",
        "#44v2c",
        "#44v2e",
        "#44v2i",
        "#44v2s",
    ],
    "Aksi / SFX": [
        "PermanentMarker-Regular",
        "Shojumaru-Regular",
        "soundfx",
        "Komigo3D-Regular",
        "Heroes Legend",
        "Heroes Legend Hollow",
        "Indiana-Jonas-48p",
        "Indiana-Jonas-48ip",
        "KMKDSP__",
        "KMKDSPB_",
        "KMKDSPT_",
        "KMKDSPW_",
        "KMKDSPBW",
        "KMKDSPK_",
        "KMKDSPKB",
        "KMKDSPKW",
        "KMKDSKBW",
        "KMKDSPSH",
        "KOMTIT__",
        "KOMTITA_",
        "KOMTITBR",
        "KOMTITE_",
        "KOMTITG_",
        "KOMTITK_",
        "KOMTITP_",
        "KOMTITS_",
        "KOMTITTL",
        "KOMTITT_",
        "KOMTITWR",
        "KOMTITW_",
    ],
    "Narasi / Sistem / Kotak Info": [
        "ShareTechMono-Regular",
        "SpecialElite-Regular",
        "Inter-VariableFont_opsz,wght",
        "Inter-Italic-VariableFont_opsz,wght",
        "Cinzel-Bold",
        "PlayfairDisplay-VariableFont_wght",
        "PlayfairDisplay-Italic-VariableFont_wght",
    ],
}


def _clean_font_entries(raw_entries) -> list[str]:
    if isinstance(raw_entries, (list, tuple)):
        iterator = raw_entries
    elif isinstance(raw_entries, set):
        iterator = sorted(raw_entries)
    elif isinstance(raw_entries, str):
        iterator = [raw_entries]
    else:
        iterator = []
    cleaned: list[str] = []
    seen: set[str] = set()
    for entry in iterator:
        if not isinstance(entry, str):
            continue
        trimmed = entry.strip()
        if not trimmed or trimmed in seen:
            continue
        seen.add(trimmed)
        cleaned.append(trimmed)
    return cleaned


def normalize_font_groups(raw_groups) -> dict[str, list[str]]:
    """Normalize a user/config font_groups mapping into ordered unique strings."""
    if not isinstance(raw_groups, dict):
        return {}
    normalized: dict[str, list[str]] = {}
    for group_name, entries in raw_groups.items():
        if not isinstance(group_name, str) or not group_name.strip():
            continue
        normalized[group_name.strip()] = _clean_font_entries(entries)
    return normalized


def merge_default_font_groups(
    existing_groups,
    default_groups: dict[str, list[str]] | None = None,
) -> dict[str, list[str]]:
    """Populate curated manga font groups while preserving custom user groups/fonts."""
    defaults = default_groups if default_groups is not None else DEFAULT_FONT_GROUPS
    existing = normalize_font_groups(existing_groups)
    merged: dict[str, list[str]] = {}

    for group_name, curated in defaults.items():
        items = list(curated)
        seen_norm = {_normalize_font_token(x) for x in items}
        for custom in existing.get(group_name, []):
            if custom in _LEGACY_FONT_ALIASES:
                continue
            tok = _normalize_font_token(custom)
            if tok and tok not in seen_norm:
                items.append(custom)
                seen_norm.add(tok)
        merged[group_name] = items

    for group_name, entries in existing.items():
        if group_name not in merged:
            merged[group_name] = list(entries)

    return merged
