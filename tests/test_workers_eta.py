"""Karakterisasi kalkulasi ETA & format durasi tab Workers."""

from src.ui.workers_panel import estimate_eta, format_duration


def test_eta_kosong_mengembalikan_none():
    assert estimate_eta([], 5) is None


def test_eta_sisa_nol():
    assert estimate_eta([10.0, 20.0], 0) == 0


def test_eta_rata_rata_dikali_sisa():
    # rata-rata 15 detik x 4 sisa = 60
    assert estimate_eta([10.0, 20.0], 4) == 60.0


def test_eta_negatif_diperlakukan_sebagai_selesai():
    assert estimate_eta([10.0], -3) == 0


def test_format_durasi():
    assert format_duration(0) == "0d"
    assert format_duration(59) == "59d"
    assert format_duration(90) == "1m 30d"
    assert format_duration(3675) == "1j 1m 15d"
    assert format_duration(-5) == "0d"
