"""Test langsung untuk logika font yang sudah diangkat ke src.core.fonts.

Bedanya dengan test_font_logic.py: di sini TIDAK ada satu pun widget. Tidak ada
QComboBox, QDoubleSpinBox, atau MangaOCRApp -- hanya nilai biasa masuk, QFont
keluar. Itulah hasil nyata Fase 2 untuk domain font.
"""

import pytest
from PyQt5.QtGui import QFont

from src.core.fonts import (
    DEFAULT_FONT_GROUPS,
    FontManager,
    build_font,
    fonts_in_group,
    merge_default_font_groups,
)


class StubManager:
    def create_qfont(self, display_name, base_font=None):
        return QFont(display_name, 11)


# --- build_font ------------------------------------------------------------

def test_display_menang_atas_fallback(qapp):
    font = build_font(StubManager(), display="Comic Sans",
                      fallback_font=QFont("Georgia", 30))
    assert font.family() == "Comic Sans"


def test_fallback_dipakai_tanpa_display(qapp):
    font = build_font(StubManager(), display=None, fallback_font=QFont("Georgia", 30))
    assert font.family() == "Georgia"


def test_arial_bila_tidak_ada_sumber(qapp):
    assert build_font(None).family() == "Arial"


def test_tanpa_manager_display_diabaikan(qapp):
    font = build_font(None, display="Comic Sans", fallback_font=QFont("Georgia", 30))
    assert font.family() == "Georgia"


@pytest.mark.parametrize("masuk,harapan", [
    (None, 24.0),      # tidak disebut -> default
    (37.5, 37.5),
    (0, 12.0),         # nol tidak masuk akal -> dipaksa
    (-8, 12.0),
])
def test_pembatasan_ukuran(qapp, masuk, harapan):
    assert build_font(StubManager(), display="Arial",
                      size=masuk).pointSizeF() == pytest.approx(harapan)


def test_gaya_none_tidak_menimpa_bawaan(qapp):
    tebal = QFont("Georgia", 12)
    tebal.setBold(True)
    font = build_font(None, fallback_font=tebal, bold=None)
    assert font.bold() is True


def test_gaya_false_menimpa_bawaan(qapp):
    tebal = QFont("Georgia", 12)
    tebal.setBold(True)
    font = build_font(None, fallback_font=tebal, bold=False)
    assert font.bold() is False


@pytest.mark.parametrize("masuk,harapan", [(None, 100.0), (0, 100.0), (65.0, 65.0)])
def test_char_spacing(qapp, masuk, harapan):
    font = build_font(StubManager(), display="Arial", char_spacing=masuk)
    assert font.letterSpacing() == pytest.approx(harapan)


# --- fonts_in_group --------------------------------------------------------

def test_grup_mempertahankan_urutan_daftar_font():
    fonts = ["Arial", "Comic Sans", "Heroes Legend"]
    assert fonts_in_group(fonts, ["Heroes Legend", "Arial"]) == ["Arial", "Heroes Legend"]


def test_anggota_grup_yang_tidak_terpasang_diabaikan():
    assert fonts_in_group(["Arial"], ["Arial", "Font Hantu"]) == ["Arial"]


@pytest.mark.parametrize("grup", [None, []])
def test_grup_kosong_menghasilkan_daftar_kosong(grup):
    assert fonts_in_group(["Arial", "Comic Sans"], grup) == []


def test_default_font_groups_resolve_all_installed_manga_fonts(qapp):
    fm = FontManager("src/fonts")
    all_fonts = fm.list_fonts()
    installed = set(all_fonts) - {fm.default_display}
    covered = set()

    for group_name, entries in DEFAULT_FONT_GROUPS.items():
        resolved = fonts_in_group(all_fonts, entries, font_manager=fm)
        assert resolved, f"Group {group_name!r} resolved no fonts"
        missing = [e for e in entries if not fm.resolve_font_names(e)]
        assert not missing, f"Group {group_name!r} has missing fonts: {missing}"
        covered.update(resolved)

    assert installed - covered == set()


def test_merge_default_font_groups_upgrades_legacy_and_keeps_custom():
    legacy = {
        "Dialog Normal": ["CC Wild Words", "MyCustomComicFont"],
        "Grup Spesial Ku": ["Arial", "MyCustomComicFont"],
    }
    merged = merge_default_font_groups(legacy)

    assert "Dialog Normal" in merged
    assert "Cute / Shoujo / Chibi" in merged
    assert "Narasi / Sistem / Kotak Info" in merged
    assert "CC Wild Words" not in merged["Dialog Normal"]
    assert "MyCustomComicFont" in merged["Dialog Normal"]
    assert merged["Grup Spesial Ku"] == ["Arial", "MyCustomComicFont"]
