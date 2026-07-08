# Test & CI Foundation for MangaTranslate

**Tanggal**: 2026-07-08
**Status**: Draft (menunggu review user)
**Versi aplikasi target**: v14.9.0+
**Sub-proyek**: Siklus #1 dari 3 (Test/CI → Reliabilitas → Performance)

---

## 1. Konteks & Motivasi

MangaTranslate v14.9.0 adalah aplikasi desktop Windows-first (PyQt5) untuk OCR, terjemahan, dan typeset manga. Hasil audit konteks:

- `src/ui/main_window.py` = **17.130 baris / 800KB** — mendekati batas maintainable
- **Zero automated test** di proyek (semua file `test_*` hanya ada di `venv`/`Inpainting`)
- Verifikasi hanya `py_compile` manual, tidak ada CI
- Crash `0xC0000005` (threading) tercatat berulang di `.agents/code.md` §3.4
- 6 fitur pending di `.agents/feature_ideas.md`

**Pain point utama**: Tanpa test, refactor monolith dan fix crash berisiko tinggi karena tidak mungkin diverifikasi tidak menimbulkan regresi.

## 2. Tujuan & Non-Tujuan

### Tujuan (Goals)
1. Membangun **fondasi test otomatis** yang bisa di-scale di siklus berikutnya
2. Membangun **CI pipeline** (GitHub Actions) yang running setiap push/PR
3. Menangkap regression paling cepat (import error, settings corruption, crypto failure) sebelum reach user

### Non-Tujuan (YAGNI — dikerjakan di siklus lain)
- ❌ Test worker threading (siklus #2 Reliabilitas)
- ❌ Test OCR/translate pipeline dengan mock API (terlalu kompleks untuk smoke)
- ❌ Test UI interaction (klik tombol, keyboard event)
- ❌ Coverage threshold (premature — setelah ada 20+ test baru dipikirkan)
- ❌ Refactor kode produksi apapun
- ❌ Ubah `requirements.txt` produksi

## 3. Pendekatan

**pytest + pytest-qt + GitHub Actions (2-job paralel)**

Alasan memilih:
- `pytest-qt` punya `qtbot` fixture yang handle inisialisasi `QApplication` otomatis
- pytest adalah standar Python, komunitas besar, dokumentasi lengkap
- Skala baik saat test bertambah di siklus berikutnya

Alternatif yang ditolak:
- **B: unittest + QTest** — zero dependency tapi verbose (~60% lebih banyak boilerplate), harus setup QApplication manual
- **C: Skrip polos no framework** — tercepat tapi tidak ada test discovery, kontra tujuan "fondasi jangka panjang"

## 4. Arsitektur & Struktur File

```
MangaTranslate/
├── tests/                          # BARU
│   ├── __init__.py
│   ├── conftest.py                 # pytest fixtures global + QApplication singleton
│   ├── test_smoke_import.py        # app bisa di-import tanpa error
│   ├── test_smoke_settings.py      # settings load/save round-trip
│   ├── test_smoke_crypto.py        # API key encrypt/decrypt cycle
│   ├── test_smoke_geometry.py      # polygon_to_list/list_to_polygon round-trip
│   └── test_smoke_window.py        # MainWindow instantiate (offscreen)
├── requirements-dev.txt            # BARU — pytest, pytest-qt (terpisah dari prod)
├── pytest.ini                      # BARU — config: offscreen, markers, path
├── .github/workflows/test.yml      # BARU — CI
├── .agents/templates/install-precommit.ps1  # OPSIONAL — pasang pre-commit hook
└── requirements.txt                # TIDAK diubah
```

**Filosofi isolasi**: Setiap file test = satu unit tanggung jawab, bisa jalan & dipahami independen. `conftest.py` adalah satu-satunya tempat yang setup `QApplication` (singleton PyQt wajib) supaya tidak duplikasi.

## 5. Rincian Test Cases

### 5.1 `test_smoke_import.py` (risk: 🟢)
Verifikasi modul kritis bisa di-import tanpa ImportError. Mencakup import yang memicu efek samping (load settings, dll).

```python
def test_import_config():
    """config.py memanggil load_or_create_settings() saat import — 
    jika ini pecah, semuanya pecah."""
    import src.core.config

def test_import_crypto():
    import src.utils.crypto

def test_import_geometry():
    import src.utils.geometry

def test_import_app_info():
    import src.core.app_info
```

### 5.2 `test_smoke_settings.py` (risk: 🟢)
Verifikasi settings bisa load, modify, save, reload dengan nilai utuh.

```python
def test_settings_roundtrip(tmp_settings):
    """Load default → modify → save → reload → nilai sama."""
    from src.core.config import load_or_create_settings, save_settings
    s = load_or_create_settings(str(tmp_settings))
    # save_quality pasti ada di default_settings() default value 95
    original_q = s["general"]["save_quality"]
    s["general"]["save_quality"] = 77
    save_settings(s, str(tmp_settings))
    s2 = load_or_create_settings(str(tmp_settings))
    assert s2["general"]["save_quality"] == 77
    # Cleanup: restore supaya tidak bocor nilai ke test lain
    s2["general"]["save_quality"] = original_q
    save_settings(s2, str(tmp_settings))
```

**Catatan**: default arg `load_or_create_settings(path=SETTINGS_PATH)` di-evaluasi saat **def-time**, sehingga `monkeypatch.setattr("...SETTINGS_PATH", ...)` **tidak** affect pemanggilan tanpa argumen. Karena itu test harus **selalu** pass `str(tmp_settings)` eksplisit sebagai argumen.

### 5.3 `test_smoke_crypto.py` (risk: 🟢)
Verifikasi API key encrypt → muncul prefix `gAAAAA` → decrypt kembali ke nilai asli.

```python
def test_crypto_roundtrip(tmp_secret_key):
    """Encrypt harus ubah plaintext → gAAAAA..., decrypt harus restore."""
    from src.utils.crypto import encrypt_settings_keys, decrypt_settings_keys
    PLAINTEXT = "sk-test-123-abc"
    settings = {
        "apis": {
            "gemini": {"keys": [{"name": "test", "value": PLAINTEXT, "active": True}]}
        }
    }
    encrypt_settings_keys(settings)
    encrypted = settings["apis"]["gemini"]["keys"][0]["value"]
    assert encrypted != PLAINTEXT
    assert encrypted.startswith("gAAAAA")
    decrypt_settings_keys(settings)
    decrypted = settings["apis"]["gemini"]["keys"][0]["value"]
    assert decrypted == PLAINTEXT

def test_idempotent_decrypt():
    """Decrypt dua kali tidak boleh corrupt key yang sudah plaintext."""
    # implementasi: decrypt settings yang key-nya sudah plaintext → tetap plaintext
```

### 5.4 `test_smoke_geometry.py` (risk: 🟢)
Verifikasi converter polygon dua-arah, mencakup format compact (v4) dan legacy (v1-3).

```python
def test_polygon_compact_roundtrip():
    """list[[x,y],...] → polygon → list harus identik."""
    from src.utils.geometry import polygon_to_list, list_to_polygon
    pts = [[10, 20], [30, 40], [50, 60]]
    poly = list_to_polygon(pts)
    back = polygon_to_list(poly)
    assert back == pts

def test_legacy_polygon_compat():
    """Format v1-3 {x:.., y:..} harus tetap diterima converter."""
    from src.utils.geometry import list_to_polygon
    legacy = [{"x": 10, "y": 20}, {"x": 30, "y": 40}]
    # list_to_polygon harus graceful handle kedua format
    poly = list_to_polygon(legacy)
    assert poly is not None
```

### 5.5 `test_smoke_window.py` (risk: 🟡)
Verifikasi `MangaOCRApp` bisa di-instantiate di mode offscreen. **Marker `@pytest.mark.smoke`**, di-skip di CI non-Windows.

```python
import sys
import pytest

@pytest.mark.smoke
@pytest.mark.skipif(sys.platform != 'win32', reason="MainWindow full init needs Windows deps")
def test_window_instantiates(qtbot, tmp_settings):
    """MainWindow harus bisa di-instantiate tanpa exception."""
    from src.ui.main_window import MangaOCRApp
    from src.core.app_info import APP_VERSION
    win = MangaOCRApp()
    qtbot.addWidget(win)
    # Title harus mengandung versi aplikasi (dari app_info, bukan hardcoded)
    assert APP_VERSION in win.windowTitle()
    win.close()
```

**Catatan risiko**: `MangaOCRApp.__init__` memanggil `initialize_core_engines()` (L838) yang lazy & defensive — Manga-OCR hanya init jika `check_manga_ocr()` True, `sync_tessdata_files()` di-try/except. Tapi tetap ada risiko kecil gagal jika `populate_ocr_languages()` butuh tesseract binary. Jika fail, marker memungkinkan skip tanpa memblock CI.

## 6. `conftest.py` — Fixture Global

```python
import os
import sys

# Set SEBELUM import PyQt5 agar Qt tidak coba connect display
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from PyQt5.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """QApplication singleton eksplisit untuk kontrol environment."""
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def tmp_settings(tmp_path, monkeypatch):
    """Redirect SETTINGS_PATH ke tmp supaya settings.json user tidak terkorupsi."""
    fake = tmp_path / "settings.json"
    monkeypatch.setattr("src.core.config.SETTINGS_PATH", str(fake))
    return fake


@pytest.fixture
def tmp_secret_key(tmp_path, monkeypatch):
    """Redirect key Fernet ke tmp supaya .secret.key production tidak dipakai.

    PENTING: crypto.py menghitung path inline di fungsi _get_fernet() via
    os.path.join dari __file__, BUKAN via module attribute. Jadi monkeypatch
    attr tidak bekerja. Patch fungsi _get_fernet() langsung.
    """
    from cryptography.fernet import Fernet
    fake_key_file = tmp_path / ".secret.key"
    fake_key_file.write_bytes(Fernet.generate_key())
    import src.utils.crypto as crypto
    monkeypatch.setattr(crypto, "_get_fernet", lambda: fake_key_file.read_bytes())
    return fake_key_file
```

## 7. `pytest.ini` — Konfigurasi

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --strict-markers
    --tb=short
markers =
    smoke: marks tests that instantiate full MainWindow (deselect with -m "not smoke")
```

## 8. `requirements-dev.txt`

```
pytest>=7.4
pytest-qt>=4.2
```

**Penting**: File ini **terpisah** dari `requirements.txt` produksi. Dev/CI install keduanya: `pip install -r requirements.txt -r requirements-dev.txt`.

## 9. CI Workflow — GitHub Actions

Strategi: **2 job paralel**.

### Job 1: Lightweight (Linux, ~1 menit)
```yaml
name: Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lightweight-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install minimal deps
        run: pip install PyQt5 cryptography pytest pytest-qt
      - name: Run lightweight tests
        env:
          QT_QPA_PLATFORM: offscreen
        run: pytest -m "not smoke" -v
```

### Job 2: Full Smoke (Windows, ~8 menit)
```yaml
  full-smoke:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install all deps
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Run all tests
        env:
          QT_QPA_PLATFORM: offscreen
        run: pytest -v
```

### Rasionalisasi Split
- **Job 1** (Linux, lightweight) berjalan ~1 menit → feedback cepat saat PR. Tangkap regression pure logic (test #1-4). Tidak butuh torch/tesseract/paddleocr.
- **Job 2** (Windows, full) berjalan ~8 menit → tangkap regression MainWindow (test #5). Diperlukan karena app Windows-first dan beberapa path kode platform-specific.
- Keduanya **required check** untuk merge proteksi branch.

### Estimasi Biaya GitHub Actions
- Repo publik: **unlimited** free minutes untuk Linux runners.
- Windows runner: **2000 free minutes/bulan** untuk repo publik.
- Job 2 (~8 menit × ~30 PR/bulan) = ~240 menit → aman di dalam quota.

## 10. Pre-commit Hook (Opsional)

File `.agents/templates/install-precommit.ps1` disediakan. **Default: tidak diaktifkan otomatis** — user pilih sendiri.

```powershell
# .agents/templates/install-precommit.ps1
# Pasang git hook yang jalankan lightweight test sebelum commit
$hookPath = ".git/hooks/pre-commit"
@"
# Run lightweight tests before commit
$env:QT_QPA_PLATFORM = "offscreen"
venv\Scripts\python.exe -m pytest -m "not smoke" -v
if (`$LASTEXITCODE -ne 0) {
    Write-Host "Tests failed. Commit blocked."
    exit 1
}
exit 0
"@ | Out-File -FilePath $hookPath -Encoding utf8
Write-Host "Pre-commit hook installed at $hookPath"
```

User jalankan manual: `powershell -File .agents/templates/install-precommit.ps1`

## 11. Error Handling & Testing Strategy

### Prinsip Fail-Fast
- Test **tidak boleh** `try/except Exception: pass` — itu meniadakan kegunaan test.
- Setiap assertion harus eksplisit.
- Jika MainWindow instantiate throw exception, biarkan test fail dengan traceback lengkap — itu yang mau kita tangkap.

### Isolasi Fixture
- `tmp_settings` & `tmp_secret_key` memakai `monkeypatch` + `tmp_path` untuk memastikan tidak ada side effect ke file user.
- Tidak ada shared mutable state antar test.

### Deterministik
- Tidak ada test yang bergantung pada waktu/waktu startup/urutan file.
- Hash dan assertion string pakai literal, bukan generated.

## 12. Verifikasi & Acceptance Criteria

Implementasi dianggap selesai jika:

1. ✅ `pytest -m "not smoke" -v` jalan lokal di Windows dan **pass** (test #1-4)
2. ✅ `pytest -v` (semua) jalan lokal di Windows dan **pass** (test #1-5)
3. ✅ CI workflow `.github/workflows/test.yml` ter-push ke `main`
4. ✅ Job 1 (Linux lightweight) **pass** di GitHub Actions
5. ✅ Job 2 (Windows full smoke) **pass** di GitHub Actions
6. ✅ `requirements.txt` produksi **tidak berubah**
7. ✅ `venv\Scripts\python.exe -m py_compile` jalan untuk semua file `.py` baru
8. ✅ Tidak ada file produksi yang diubah (zero regression risk)

## 13. Risiko & Mitigasi

| Risiko | Probabilitas | Mitigasi |
|--------|-------------|----------|
| `MangaOCRApp.__init__` fail di Windows CI (butuh tesseract/GPU) | Sedang | Marker `@pytest.mark.smoke` + `skipif` platform. Jika konsisten fail, turunkan ke `xfail` atau skip permanen sampai siklus reliabilitas. |
| `tmp_secret_key` fixture salah path | Rendah | Fallback ke `monkeypatch.chdir(tmp_path)` |
| `polygon_to_list` return QPolygon bukan list | Rendah | Cek signature asli saat eksekusi, sesuaikan assertion |
| Install torch di Windows CI timeout | Rendah | Job 2 tidak wajib, bisa di-marked `continue-on-error: true` sementara |
| `requirements.txt` tidak sync dengan CI env | Sedang | Job 2 install eksplisit dari `requirements.txt` |

## 14. Implementasi Selanjutnya

Setelah spec ini di-approve, transisi ke **writing-plans skill** untuk breakdown implementasi step-by-step (file creation order, isi persis setiap file, perintah verifikasi).

Setelah implementasi, siklus berikutnya:
- **Siklus #2**: Reliabilitas — fix crash 0xC0000005, error handling terpusat (di atas fondasi test ini)
- **Siklus #3**: Performance & UX — startup cepat, lazy-load, rendering smooth (di atas dasar yang stabil)
