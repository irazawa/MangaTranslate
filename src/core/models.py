# Manga OCR & Typeset Tool v14.4.1
# ==============================
# ?? Import modul bawaan Python
# ==============================
# (tidak ada impor yang dibutuhkan)

# ==============================
# ?? Library pihak ketiga
# ==============================
# (tidak ada impor yang dibutuhkan)

class EnhancedResult:
    def __init__(self, text: str):
        self.text = text
        self.parts = bool(text)                          # True jika ada teks, False jika kosong
