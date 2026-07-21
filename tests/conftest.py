"""Fixture bersama. Satu QApplication untuk seluruh sesi test.

ponytail: fixture 6 baris ini menggantikan dependency pytest-qt. Ceiling: tidak
ada qtbot untuk mensimulasikan klik/keyboard. Kalau nanti benar-benar perlu
menguji interaksi widget, barulah pasang pytest-qt.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# CRITICAL -- aturan yang sama seperti di main.py: torch HARUS dimuat sebelum
# cv2/PyQt5. Kalau tidak, DLL OpenCV bentrok dengan c10.dll milik torch dan
# Windows melempar access violation (0xC0000005) saat torch diimpor belakangan
# lewat src.core.config -> check_dependency. Test tidak melewati main.py, jadi
# urutan itu harus ditegakkan di sini juga.
try:
    import torch  # noqa: F401
except Exception:
    pass

import pytest


@pytest.fixture(scope="session")
def qapp():
    """QFont butuh QGuiApplication hidup untuk membaca font database."""
    from PyQt5.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app
