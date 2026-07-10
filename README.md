# MangaTranslate

MangaTranslate adalah aplikasi desktop Windows-first berbasis Python dan PyQt5 untuk membantu workflow OCR, penerjemahan, clean-up, dan typesetting halaman manga atau komik. Aplikasi ini mendukung input gambar, folder, dan PDF, dengan pemrosesan berat dijalankan di background worker agar antarmuka tetap responsif.

Versi saat ini: `14.9.4`.

## Fitur Utama

- OCR interaktif dari area pilihan pada kanvas, termasuk seleksi kotak, oval, pen tool, dan click-to-translate.
- Pipeline OCR standar dan enhanced untuk menggabungkan hasil Manga-OCR, Tesseract, dan penerjemahan berbasis AI sesuai konfigurasi pengguna.
- Dukungan engine OCR lokal dan opsional seperti Manga-OCR, Tesseract, EasyOCR, PaddleOCR, DocTR, dan RapidOCR sesuai dependensi yang tersedia.
- Integrasi penerjemah melalui Gemini, OpenAI, DeepL, OpenRouter, 9Router, dan Ollama, dengan API key disimpan melalui konfigurasi lokal terenkripsi.
- Typesetting berbasis layer dengan pengaturan font, warna, outline, alignment, opacity, lock, visibility, dan urutan layer.
- Undo/redo untuk perubahan typesetting, recent translations, dan riwayat proyek terakhir.
- Clean-up teks melalui inpainting lokal, termasuk integrasi IOPaint server dan fallback OpenCV.
- Batch processing untuk OCR, translate, save image, proofread, dan quality check.
- Settings workspace untuk konfigurasi profil, OCR, API, tampilan, pricing, analytics, dan optional media tools.
- AI Chat dan media player terintegrasi untuk bantuan dan pemutaran file lokal atau media berbasis `yt-dlp` jika dipasang.

## Arsitektur Singkat

Entry point aplikasi adalah `main.py`, yang membuat instance `MangaOCRApp` di `src/ui/main_window.py`. UI utama memakai PyQt5, dengan canvas interaktif di `src/ui/canvas.py`, dialog dan settings di `src/ui/dialogs.py` serta `src/ui/settings_workspace.py`, dan styling bersama di `src/ui/theme.py`.

Operasi berat seperti OCR, translate, batch processing, save project, save image, dan inpainting dijalankan melalui worker di `src/core/workers.py`. Worker berkomunikasi dengan UI menggunakan signal PyQt agar GUI thread tidak diblokir.

Konfigurasi aplikasi dikelola oleh `src/core/config.py` dan disimpan ke `settings.json`. API key dienkripsi melalui helper di `src/utils/crypto.py` dan file kunci lokal `.secret.key` tidak boleh dibagikan.

## Struktur Direktori Penting

```text
MangaTranslate/
├── main.py                     # Entry point aplikasi
├── launcher.bat                # Launcher/bootstrapper Windows
├── requirements.txt            # Dependensi Python utama
├── settings.json               # Konfigurasi user lokal
├── Inpainting/                 # Komponen/server inpainting terpisah
├── tessdata/                   # Data Tesseract OCR
├── src/
│   ├── core/                   # Config, cache, metadata, worker background
│   ├── ui/                     # PyQt5 UI, canvas, dialogs, panels, theme
│   ├── utils/                  # Helper umum, crypto, geometry, downloader
│   ├── data/                   # Data runtime untuk chat/media lokal
│   ├── fonts/                  # Font kustom user
│   └── models/                 # Model lokal aplikasi
└── .cache/                     # Cache OCR/translation dan data runtime
```

## Persyaratan

- Windows 10 atau Windows 11 64-bit.
- Python 3.9 atau lebih baru tersedia di PATH.
- Koneksi internet jika menggunakan penerjemah cloud, download model/dependensi, atau fitur media online.
- Tesseract, FFmpeg, Deno, `yt-dlp`, dan dependency OCR tertentu bersifat opsional sesuai fitur yang digunakan.

## Instalasi dan Menjalankan Aplikasi

Clone repositori, lalu jalankan launcher Windows dari root proyek.

```bash
git clone https://github.com/irazawa/MangaTranslate.git
cd MangaTranslate
```

Di Windows, double-click `launcher.bat` atau jalankan dari terminal. Launcher akan menyiapkan virtual environment jika diperlukan, memasang dependensi dari `requirements.txt`, lalu menampilkan menu untuk menjalankan aplikasi utama, server inpainting, atau keduanya.

Untuk menjalankan langsung dari virtual environment yang sudah tersedia:

```powershell
venv\Scripts\python.exe main.py
```

Jika menggunakan fitur clean-up berbasis IOPaint, jalankan opsi launcher yang memulai server inpainting bersama aplikasi utama.

## Workflow Dasar

1. Buka folder gambar manga, file proyek `.manga_proj`, atau PDF dari aplikasi.
2. Pilih mode seleksi pada toolbar atau gunakan tombol angka.
3. Seleksi area teks pada canvas untuk OCR, translate, atau membuat layer manual.
4. Atur hasil typesetting melalui panel layer dan pengaturan teks.
5. Simpan proyek dengan `Ctrl+S` atau ekspor gambar typeset dengan `Ctrl+Shift+S`.

## Mode Seleksi dan Shortcut

| Shortcut | Mode |
| --- | --- |
| `1` | Transform / Hand |
| `2` | Pen Tool |
| `3` | Direct OCR Rect |
| `4` | Direct OCR Oval |
| `5` | Manual Text Rect |
| `6` | Manual Text Pen |
| `7` | Bubble Finder Rect |
| `8` | Bubble Finder Oval |
| `9` | Click-to-Translate |
| `0` | Inpaint Brush OCR |

| Shortcut | Aksi |
| --- | --- |
| `F2` | Focus mode / canvas only |
| `F3` | Toggle panel folder kiri |
| `F4` | Toggle panel tools kanan |
| `Ctrl+S` | Save project |
| `Ctrl+O` | Load project |
| `Ctrl+Shift+S` | Save typeset image |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |
| `Ctrl+H` | Find and replace |
| `Ctrl+C` / `Ctrl+V` | Copy / paste area |

## File Proyek dan Keamanan

Project disimpan sebagai file `.manga_proj` dengan `schema_version` 4. Path gambar disimpan secara relatif jika memungkinkan agar proyek lebih mudah dipindahkan antar folder.

Jangan commit atau membagikan file konfigurasi pribadi yang berisi data sensitif. API key disimpan terenkripsi, tetapi tetap perlakukan `settings.json` dan `.secret.key` sebagai data lokal pengguna.

## Verifikasi Pengembangan

Gunakan virtual environment proyek untuk menjalankan pengecekan Python. Untuk file Python yang diubah, jalankan compile check berikut:

```powershell
venv\Scripts\python.exe -m py_compile path\to\changed_file.py
```

Untuk perubahan UI, gunakan mode offscreen saat membuat smoke test agar tidak mengganggu desktop pengguna:

```powershell
$env:QT_QPA_PLATFORM="offscreen"; venv\Scripts\python.exe -m pytest
```

## Aturan Versi

Setelah perubahan coding selesai dan sebelum commit atau push, naikkan versi aplikasi sesuai scope perubahan. Mulai dari `src/core/app_info.py` (`APP_VERSION`), lalu sinkronkan teks versi yang terlihat di program, README, dan `.agents/code.md` bila relevan. Jangan ubah `schema_version` kecuali format file proyek ikut berubah.
