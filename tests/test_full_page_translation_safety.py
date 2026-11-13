"""Regression tests for Full-Page Translation safety, modal lock, and logger fix."""

from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from PIL import Image
from PyQt5.QtCore import QMutex, QRect
from PyQt5.QtGui import QColor, QFont, QPolygon
from PyQt5.QtWidgets import QPushButton, QWidget

from src.core.project_archive import decode_cleaned_image, encode_cleaned_state, record_has_cleaned_image
from src.ui.canvas import TypesetArea
from src.ui.dialogs import FullPageProgressDialog
from src.ui.main_window import FullPageTranslateWorker
from src.ui.main_window_mixins.history import HistoryMixin
from src.ui.main_window_mixins.inpaint import InpaintMixin
from src.ui.main_window_mixins.translate import TranslateMixin
from src.ui.main_window_mixins.typeset import TypesetMixin
from src.ui.texts import ActionText, FullPageBatchText


def _make_page(width=120, height=160, seed=1):
    rng = np.random.default_rng(seed)
    arr = rng.integers(30, 220, size=(height, width, 3), dtype=np.uint8)
    return Image.fromarray(arr, "RGB")


class _FakeStatusBar:
    def showMessage(self, *_args, **_kwargs):
        pass


class _DummyTranslateHost(TranslateMixin, TypesetMixin, InpaintMixin, HistoryMixin):
    def __init__(self, tmp_path, qapp):
        self._widget_parent = QWidget()
        self.all_typeset_data = {}
        self.typeset_areas = []
        self.redo_stack = []
        self.history_entries = []
        self.pdf_document = None
        self.current_pdf_page = -1
        self.current_image_path = None
        self.current_image_pil = None
        self.unmodified_image_pil = None
        self.active_curves_points = None
        self.original_pixmap = None
        self.paint_mutex = QMutex()
        self.auto_translate_page_btn = QPushButton(ActionText.FULL_PAGE_TRANSLATE)
        self.auto_translate_page_btn.setEnabled(False)
        self.banners = []
        self.toasts = []
        self.redraw_calls = 0
        self.AI_PROVIDERS = {
            "OpenRouter": {
                "test-model": {"temperature": 0.2, "max_tokens": 512},
            }
        }
        self._dummy_area_font = QFont("Arial", 16)

    def statusBar(self):
        return _FakeStatusBar()

    def get_current_data_key(self, path=None, page=-1):
        return path if path is not None else self.current_image_path

    def _encode_cleaned_state(self, pil_image, orig_pil=None):
        return encode_cleaned_state(pil_image, orig_pil=orig_pil)

    def _decode_cleaned_image(self, record, orig_pil=None, key=None):
        return decode_cleaned_image(record, orig_pil=orig_pil, orig_key=key)

    def _apply_base_image(self, pil_image):
        self.current_image_pil = pil_image.convert("RGB")

    def _create_typeset_area(self, rect, text, settings, polygon=None, original_text="", manual_inpaint=False, is_manual=False):
        return TypesetArea(
            rect=rect,
            text=text,
            font=self._dummy_area_font,
            color=QColor("#000000"),
            polygon=polygon,
            original_text=original_text,
        )

    def _push_undo_snapshot(self, label):
        self.history_entries.append(label)

    def redraw_all_typeset_areas(self, refresh_layers=False):
        self.redraw_calls += 1

    def show_banner(self, key, title, msg, kind="info"):
        self.banners.append((key, title, msg, kind))

    def show_toast(self, title, msg, kind="info"):
        self.toasts.append((title, msg, kind))


def test_translate_with_openrouter_empty_response_logs_and_retries(caplog, qapp, tmp_path):
    host = _DummyTranslateHost(tmp_path, qapp)

    responses = [
        SimpleNamespace(text='{"choices":[{"message":{"content":""}}]}', json=lambda: {"choices": [{"message": {"content": ""}}]}),
        SimpleNamespace(text='{"choices":[{"message":{"content":"Halo dunia"}}]}', json=lambda: {"choices": [{"message": {"content": "Halo dunia"}}]}),
    ]
    calls = {"n": 0}

    def _fake_post(*_args, **_kwargs):
        idx = calls["n"]
        calls["n"] += 1
        return responses[min(idx, len(responses) - 1)]

    with (
        patch("src.ui.main_window_mixins.translate.get_translate_provider_settings", return_value={"api_key": "k", "url": "https://openrouter.ai/api/v1/chat/completions"}),
        patch("src.ui.main_window_mixins.translate.robust_post", side_effect=_fake_post),
        patch("time.sleep", return_value=None),
    ):
        translated = host.translate_with_ai("こんにちは", "Indonesian", "OpenRouter", "test-model", {})

    assert calls["n"] == 2
    assert translated == "Halo dunia"
    assert any("returned empty response" in rec.message for rec in caplog.records)


def test_fullpage_progress_dialog_is_modal_and_blocks_reject_until_finished(qapp):
    parent = QWidget()
    dlg = FullPageProgressDialog(parent, "03.jpg")
    cancel_emits = []
    dlg.cancel_requested.connect(lambda: cancel_emits.append(True))

    assert dlg.isModal() is True
    assert "03.jpg" in dlg.page_label.text()

    dlg.show()
    dlg.set_progress(45, "OCR paralel 2/4 blok...")
    assert dlg.progress_bar.value() == 45
    assert dlg.step_label.text() == "OCR paralel 2/4 blok..."

    # Pressing Esc / reject while running must request cancel instead of closing immediately
    dlg.reject()
    assert len(cancel_emits) == 1
    assert dlg.cancel_btn.isEnabled() is False
    assert dlg.cancel_btn.text() == FullPageBatchText.DIALOG_CANCELLING
    assert dlg.isVisible() is True

    dlg.mark_finished()
    dlg.accept()
    assert dlg.isVisible() is False


def test_full_page_result_does_not_overwrite_different_active_page(qapp, tmp_path):
    p3 = str(tmp_path / "03.jpg")
    p5 = str(tmp_path / "05.jpg")
    orig3 = _make_page(seed=3)
    orig5 = _make_page(seed=5)
    orig3.save(p3)
    orig5.save(p5)

    cleaned3_arr = np.array(orig3, copy=True)
    cleaned3_arr[20:60, 20:80] = 255
    cleaned3 = Image.fromarray(cleaned3_arr, "RGB")

    host = _DummyTranslateHost(tmp_path, qapp)
    existing5_area = host._create_typeset_area(QRect(5, 5, 40, 20), "Halaman 5 Asli", {})
    host.all_typeset_data[p5] = {"areas": [existing5_area], "redo": []}

    # Worker started on page 3...
    worker = FullPageTranslateWorker(host, p3, {"use_inpaint": True}, False, target_key=p3)
    worker.cleaned_image_pil = cleaned3
    host._full_page_worker = worker
    dlg = FullPageProgressDialog(host._widget_parent, "03.jpg")
    dlg.show()
    host._full_page_dialog = dlg

    # ...and active page changed to page 5 before finishing
    host.current_image_path = p5
    host.current_image_pil = orig5.copy()
    host.typeset_areas = [existing5_area]

    rect3 = QRect(22, 22, 50, 30)
    payloads3 = [{
        "rect": rect3,
        "text": "Halaman 3 Terjemahan",
        "original_text": "元のテキスト",
        "polygon": QPolygon([rect3.topLeft(), rect3.topRight(), rect3.bottomRight(), rect3.bottomLeft()]),
        "settings": {"use_inpaint": True},
    }]

    host.on_full_page_translation_finished(payloads3, "Success")

    # Page 5 active state and image MUST stay completely untouched
    assert host.current_image_path == p5
    assert np.array_equal(np.asarray(host.current_image_pil), np.asarray(orig5))
    assert len(host.typeset_areas) == 1
    assert host.typeset_areas[0].text == "Halaman 5 Asli"
    assert not record_has_cleaned_image(host.all_typeset_data[p5])
    assert host.redraw_calls == 0

    # Page 3 record received the cleaned image and translated area cleanly
    rec3 = host.all_typeset_data[p3]
    assert len(rec3["areas"]) == 1
    assert rec3["areas"][0].text == "Halaman 3 Terjemahan"
    assert record_has_cleaned_image(rec3)
    decoded3 = decode_cleaned_image(rec3, orig_pil=orig3)
    assert decoded3 is not None
    assert np.array_equal(np.asarray(decoded3), np.asarray(cleaned3))
    assert host._full_page_dialog is None


def test_full_page_cancelled_and_error_close_modal_cleanly(qapp, tmp_path):
    p3 = str(tmp_path / "03.jpg")
    orig3 = _make_page(seed=9)
    orig3.save(p3)

    host = _DummyTranslateHost(tmp_path, qapp)
    host.current_image_path = p3
    host.current_image_pil = orig3.copy()

    # 1) Cancellation path discards areas and closes modal
    worker = FullPageTranslateWorker(host, p3, {"use_inpaint": True}, False, target_key=p3)
    worker._is_cancelled = True
    host._full_page_worker = worker
    dlg = FullPageProgressDialog(host._widget_parent, "03.jpg")
    dlg.show()
    host._full_page_dialog = dlg

    host.on_full_page_translation_finished([{"rect": QRect(0, 0, 10, 10), "text": "x", "original_text": "y", "polygon": QPolygon(), "settings": {}}], "Dibatalkan.")
    assert host._full_page_dialog is None
    assert host._full_page_worker is None
    assert host.auto_translate_page_btn.isEnabled() is True
    assert host.auto_translate_page_btn.text() == ActionText.FULL_PAGE_TRANSLATE
    assert host.typeset_areas == []

    # 2) Error path closes modal and re-enables button
    dlg2 = FullPageProgressDialog(host._widget_parent, "03.jpg")
    dlg2.show()
    host._full_page_dialog = dlg2
    host.auto_translate_page_btn.setEnabled(False)
    host.on_full_page_translation_error("API down")
    assert host._full_page_dialog is None
    assert host.auto_translate_page_btn.isEnabled() is True
    assert any(b[0] == "full-page-translation-error" for b in host.banners)
