"""Logika OCR murni: masuk data, keluar data. Tanpa widget, tanpa jaringan.

Diangkat dari OcrMixin pada Fase 2 pemecahan main_window.py. Kedua fungsi di
sini memang sudah tidak menyentuh `self` sama sekali saat masih jadi method --
memindahkannya membuat fakta itu terlihat sekaligus bisa diuji sendiri.
"""

import cv2


def preprocess_for_ocr(cv_image, orientation_hint="Auto-Detect"):
    """Luruskan lalu binerisasi gambar untuk engine OCR.

    Return (gambar_BGR, sudut_putar_derajat).

    Catatan: penjaga h/w == 0 di bawah tidak pernah tercapai untuk gambar 0x0
    karena cvtColor melempar lebih dulu. Perilaku itu dipertahankan apa adanya
    saat pemindahan; ada test yang menguncinya (test_ocr_logic.py).
    """
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    if h == 0 or w == 0:
        return cv_image, 0
    angle = 0
    if orientation_hint == "Auto-Detect":
        try:
            coords = cv2.findNonZero(cv2.bitwise_not(gray))
            if coords is not None:
                rect = cv2.minAreaRect(coords)
                angle = rect[-1]
                if w < h and angle < -45:
                    angle = -(90 + angle)
                elif w > h and angle > 45:
                    angle = 90 - angle
                else:
                    angle = -angle
        except cv2.error:
            angle = 0
    elif orientation_hint == "Vertical":
        if w > h:
            angle = 90

    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated_gray = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    try:
        equalized = cv2.equalizeHist(rotated_gray)
        blurred = cv2.GaussianBlur(equalized, (3, 3), 0)
        _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    except cv2.error:
        otsu = rotated_gray

    processed_bgr = cv2.cvtColor(otsu, cv2.COLOR_GRAY2BGR)
    return processed_bgr, angle


def extract_ai_ocr_text(response_json):
    """Ambil teks dari respons OCR berbasis AI, apa pun bentuknya.

    Provider berbeda mengembalikan bentuk berbeda: choices/message/content ala
    OpenAI (string maupun daftar potongan), 'message' langsung, atau 'text' /
    'output_text' di tingkat atas. Return string kosong bila tidak dikenali.
    """
    if not isinstance(response_json, dict):
        return ""

    choices = response_json.get('choices')
    if isinstance(choices, list) and choices:
        message = choices[0].get('message', {}) if isinstance(choices[0], dict) else {}
        content = message.get('content') if isinstance(message, dict) else None
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = []
            for chunk in content:
                if isinstance(chunk, dict):
                    text_val = chunk.get('text') or chunk.get('content')
                    if isinstance(text_val, str) and text_val.strip():
                        parts.append(text_val.strip())
            if parts:
                return '\n'.join(parts).strip()

    message = response_json.get('message')
    if isinstance(message, str):
        return message.strip()

    if isinstance(message, dict):
        content = message.get('content')
        if isinstance(content, str):
            return content.strip()

    for key in ('text', 'output_text'):
        val = response_json.get(key)
        if isinstance(val, str):
            return val.strip()
        if isinstance(val, list):
            parts = [v.strip() for v in val if isinstance(v, str)]
            if parts:
                return '\n'.join(parts)
    return ""
