"""Test karakterisasi untuk logika OCR murni, sebelum diangkat dari OcrMixin.

Sama seperti test_font_logic.py: diuji lewat objek stub, merekam perilaku apa
adanya. Harus tetap hijau sesudah ekstraksi.
"""

import numpy as np
import pytest

from src.ui.main_window_mixins.ocr import OcrMixin


class Host(OcrMixin):
    pass


@pytest.fixture
def host():
    return Host()


# --- _extract_ai_ocr_text: bentuk respons yang berbeda-beda per provider ----

def test_bentuk_openai_content_string(host):
    resp = {"choices": [{"message": {"content": "  halo dunia  "}}]}
    assert host._extract_ai_ocr_text(resp) == "halo dunia"


def test_bentuk_content_berupa_daftar_potongan(host):
    resp = {"choices": [{"message": {"content": [
        {"text": " baris satu "},
        {"content": "baris dua"},
        {"text": "   "},          # kosong -> dibuang
        {"bukan_teks": 1},        # tanpa kunci teks -> dilewati
    ]}}]}
    assert host._extract_ai_ocr_text(resp) == "baris satu\nbaris dua"


def test_message_langsung_berupa_string(host):
    assert host._extract_ai_ocr_text({"message": " teks "}) == "teks"


def test_message_berupa_dict(host):
    assert host._extract_ai_ocr_text({"message": {"content": " teks "}}) == "teks"


@pytest.mark.parametrize("kunci", ["text", "output_text"])
def test_fallback_kunci_tingkat_atas(host, kunci):
    assert host._extract_ai_ocr_text({kunci: "  hasil  "}) == "hasil"


@pytest.mark.parametrize("kunci", ["text", "output_text"])
def test_fallback_kunci_berupa_daftar(host, kunci):
    assert host._extract_ai_ocr_text({kunci: [" a ", " b ", 5]}) == "a\nb"


@pytest.mark.parametrize("masukan", [None, "string", 42, [], {}, {"choices": []}])
def test_masukan_tak_dikenal_menghasilkan_string_kosong(host, masukan):
    assert host._extract_ai_ocr_text(masukan) == ""


def test_choices_menang_atas_message(host):
    resp = {"choices": [{"message": {"content": "dari choices"}}], "message": "dari message"}
    assert host._extract_ai_ocr_text(resp) == "dari choices"


# --- preprocess_for_ocr ----------------------------------------------------

def _gambar(h=40, w=60):
    img = np.full((h, w, 3), 255, dtype=np.uint8)
    img[10:20, 5:50] = 0          # sedikit "teks" hitam
    return img


def test_mengembalikan_bgr_dengan_dimensi_sama(host):
    img = _gambar()
    out, angle = host.preprocess_for_ocr(img, orientation_hint="Horizontal")
    assert out.shape == img.shape
    assert angle == 0


def test_gambar_kosong_melempar_error_bukan_kembali_mulus(host):
    """Merekam perilaku NYATA, bukan yang diniatkan.

    preprocess_for_ocr punya penjaga `if h == 0 or w == 0: return cv_image, 0`,
    tapi penjaga itu MATI: cv2.cvtColor di baris sebelumnya sudah melempar
    lebih dulu untuk gambar 0x0. Bug laten yang sudah ada sebelum refactor ini
    -- sengaja tidak diperbaiki di sini agar ekstraksi tetap murni.
    """
    import cv2
    kosong = np.zeros((0, 0, 3), dtype=np.uint8)
    with pytest.raises(cv2.error):
        host.preprocess_for_ocr(kosong)


def test_hint_vertical_memutar_gambar_lebar(host):
    _out, angle = host.preprocess_for_ocr(_gambar(h=30, w=80), orientation_hint="Vertical")
    assert angle == 90


def test_hint_vertical_tidak_memutar_gambar_tinggi(host):
    _out, angle = host.preprocess_for_ocr(_gambar(h=80, w=30), orientation_hint="Vertical")
    assert angle == 0


def test_hasil_terbinerisasi(host):
    out, _angle = host.preprocess_for_ocr(_gambar(), orientation_hint="Horizontal")
    assert set(np.unique(out)).issubset({0, 255})
