"""Test karakterisasi untuk logika font.

Merekam perilaku APA ADANYA sebelum logikanya diangkat keluar dari FontMixin.
Test ini harus tetap hijau sesudah ekstraksi -- itulah gunanya.

Diuji lewat objek stub yang mewarisi FontMixin: method-method itu hanya
menyentuh self.<atribut>, jadi tidak perlu membangun MangaOCRApp penuh.
"""

import pytest
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox

from src.ui.main_window_mixins.font import FontMixin


class FakeFontManager:
    """Cukup untuk logika yang diuji; FontManager asli baca disk."""

    def __init__(self, fonts=("Arial", "Comic Sans", "Heroes Legend")):
        self._fonts = list(fonts)

    def list_fonts(self):
        return list(self._fonts)

    def create_qfont(self, display_name, base_font=None):
        return QFont(display_name, 11)

    def display_name_for_font(self, font, fallback=None):
        return font.family() if font else (fallback or "")


class Host(FontMixin):
    """Objek minimal yang menyediakan atribut yang dibaca FontMixin."""

    def __init__(self, **kwargs):
        self.font_manager = FakeFontManager()
        self.typeset_font = None
        self.typeset_char_spacing_value = 100.0
        self.font_groups = {}
        for key, value in kwargs.items():
            setattr(self, key, value)


@pytest.fixture
def spin(qapp):
    widget = QDoubleSpinBox()
    widget.setRange(-100, 500)
    widget.setValue(24.0)
    return widget


@pytest.fixture
def dropdown(qapp):
    widget = QComboBox()
    widget.addItems(["Arial", "Comic Sans", "Heroes Legend"])
    return widget


# --- _build_current_font ---------------------------------------------------

def test_pakai_font_dari_dropdown_bila_ada(qapp, dropdown, spin):
    dropdown.setCurrentText("Comic Sans")
    host = Host(font_dropdown=dropdown, font_size_spin=spin)
    assert host._build_current_font().family() == "Comic Sans"


def test_jatuh_ke_typeset_font_bila_dropdown_kosong(qapp, spin):
    host = Host(font_size_spin=spin, typeset_font=QFont("Georgia", 30))
    assert host._build_current_font().family() == "Georgia"


def test_jatuh_ke_arial_bila_tidak_ada_sumber_lain(qapp, spin):
    host = Host(font_size_spin=spin)
    assert host._build_current_font().family() == "Arial"


def test_ukuran_diambil_dari_spinbox(qapp, dropdown, spin):
    spin.setValue(37.5)
    host = Host(font_dropdown=dropdown, font_size_spin=spin)
    assert host._build_current_font().pointSizeF() == pytest.approx(37.5)


@pytest.mark.parametrize("nilai", [0.0, -5.0])
def test_ukuran_tidak_masuk_akal_dipaksa_ke_12(qapp, dropdown, spin, nilai):
    spin.setValue(nilai)
    host = Host(font_dropdown=dropdown, font_size_spin=spin)
    assert host._build_current_font().pointSizeF() == pytest.approx(12.0)


def test_ukuran_default_24_bila_tidak_ada_spinbox(qapp, dropdown):
    host = Host(font_dropdown=dropdown)
    assert host._build_current_font().pointSizeF() == pytest.approx(24.0)


def test_toggle_gaya_diterapkan(qapp, dropdown, spin):
    bold, italic, underline = QCheckBox(), QCheckBox(), QCheckBox()
    bold.setChecked(True)
    underline.setChecked(True)
    host = Host(font_dropdown=dropdown, font_size_spin=spin,
                bold_toggle=bold, italic_toggle=italic, underline_toggle=underline)
    font = host._build_current_font()
    assert (font.bold(), font.italic(), font.underline()) == (True, False, True)


def test_char_spacing_kosong_jadi_100(qapp, dropdown, spin):
    host = Host(font_dropdown=dropdown, font_size_spin=spin)
    host.typeset_char_spacing_value = None
    assert host._build_current_font().letterSpacing() == pytest.approx(100.0)


def test_char_spacing_dipakai_apa_adanya(qapp, dropdown, spin):
    host = Host(font_dropdown=dropdown, font_size_spin=spin)
    host.typeset_char_spacing_value = 65.0
    assert host._build_current_font().letterSpacing() == pytest.approx(65.0)


# --- penyaringan grup di _populate_typeset_font_dropdown -------------------

def test_dropdown_menampilkan_semua_font_tanpa_grup(qapp, dropdown, spin):
    host = Host(font_dropdown=dropdown, font_size_spin=spin)
    host._populate_typeset_font_dropdown()
    assert [dropdown.itemText(i) for i in range(dropdown.count())] == \
        ["Arial", "Comic Sans", "Heroes Legend"]


def test_dropdown_disaring_oleh_grup(qapp, dropdown, spin):
    host = Host(font_dropdown=dropdown, font_size_spin=spin)
    host.font_groups = {"SFX": ["Heroes Legend", "Tidak Terpasang"]}
    host._populate_typeset_font_dropdown(group="SFX")
    # "Tidak Terpasang" tidak ada di font_manager -> tidak ikut muncul
    assert [dropdown.itemText(i) for i in range(dropdown.count())] == ["Heroes Legend"]


def test_font_pilihan_dipilih_bila_tersedia(qapp, dropdown, spin):
    host = Host(font_dropdown=dropdown, font_size_spin=spin)
    host._populate_typeset_font_dropdown(preferred_display="Comic Sans")
    assert dropdown.currentText() == "Comic Sans"


def test_jatuh_ke_item_pertama_bila_pilihan_tidak_ada(qapp, dropdown, spin):
    host = Host(font_dropdown=dropdown, font_size_spin=spin)
    host._populate_typeset_font_dropdown(preferred_display="Font Hantu")
    assert dropdown.currentText() == "Arial"
