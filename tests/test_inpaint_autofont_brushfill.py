"""Regression tests for:
1. Full-page bubble/text pixel inpainting (bold kanji interior hole-fill & clipped furigana rescue)
2. Bubble-aware Auto Font Size & wrapped Smart Auto-Fit + Typeset UI controls
3. Closed-loop auto-fill for manual Inpaint Brush strokes
"""

import copy
import math

import cv2
import numpy as np
import pytest
from PIL import Image
from PyQt5.QtCore import QEvent, QPoint, QPointF, QRect, Qt
from PyQt5.QtGui import QColor, QFont, QImage, QMouseEvent, QPixmap, QPolygon

import src.core.config as cfg
import src.ui.dialogs as dlg_mod
from src.ui.canvas import (
    SelectableImageLabel,
    TypesetArea,
    compute_auto_font_scale,
    compute_auto_font_size,
)
from src.ui.main_window import FullPageTranslateWorker, MangaOCRApp


def _make_bold_kanji_bubble_image():
    """Create a 320x320 manga page with dark exterior, 6px black bubble ring,
    thick >=28px kanji strokes, and adjacent clipped furigana inside pure white interior.
    """
    img = np.full((320, 320, 3), 24, dtype=np.uint8)
    # Pure white speech bubble interior
    cv2.ellipse(img, (160, 160), (112, 122), 0, 0, 360, (255, 255, 255), -1)
    # 6px black bubble outline
    cv2.ellipse(img, (160, 160), (112, 122), 0, 0, 360, (0, 0, 0), 6)

    # Thick solid bold kanji block (>28px thick so naive 17x17 close fails!)
    cv2.rectangle(img, (132, 92), (168, 212), (0, 0, 0), -1)
    # Horizontal thick crossbar intersecting middle & extending left past tight text rect
    cv2.rectangle(img, (108, 128), (176, 158), (0, 0, 0), -1)
    # Detached right-side kanji/furigana slightly outside tight text rect
    cv2.rectangle(img, (186, 118), (212, 172), (0, 0, 0), -1)
    return img


def test_safe_bubble_interior_preserves_thick_kanji_centers():
    img = _make_bold_kanji_bubble_image()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Zone matches white bubble interior (excluding dark outline and dark kanji strokes)
    zone = (gray >= 200).astype(np.uint8)
    # Keep only interior white bubble component (center white point (95, 160))
    _n, lbl, _st, _ = cv2.connectedComponentsWithStats(zone, connectivity=8)
    bubble_zone = (lbl == lbl[160, 95]).astype(np.uint8)

    safe_int = FullPageTranslateWorker._safe_bubble_interior(bubble_zone)

    # Deep center of 36px bold kanji must be solid inside safe interior (not hollowed out!)
    assert safe_int[150, 150] > 0
    assert safe_int[142, 145] > 0
    # Outer black bubble wall & outside artwork must stay strictly excluded (0)
    assert safe_int[160, 160 - 112] == 0
    assert safe_int[20, 20] == 0


def test_build_text_pixel_mask_cleans_bold_and_clipped_kanji_without_leaking():
    img = _make_bold_kanji_bubble_image()
    # Tight/clipped detection polygon that misses left crossbar tips and right furigana block
    tight_poly = QPolygon(QRect(130, 100, 44, 102))
    expanded_rect = QRect(70, 56, 180, 208)

    worker = FullPageTranslateWorker(
        None,
        "",
        {"inpaint_padding": 5, "use_inpaint": True},
        False,
        page_pil=Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)),
    )

    # Both with expanded_rects and even with expanded_rects=None (sealed bubble rescue)
    for exp in ([expanded_rect], None):
        worker._direct_bubble_cleaned_bgr = None
        worker._build_text_pixel_mask(img, [tight_poly], expanded_rects=exp)
        cleaned = worker._direct_bubble_cleaned_bgr
        assert cleaned is not None

        # Deep bold kanji center erased cleanly to white
        assert int(cleaned[150, 150].min()) >= 245
        # Left protruding stroke tip erased cleanly (no straight vertical cut!)
        assert int(cleaned[142, 112].min()) >= 245
        # Detached right-side furigana erased cleanly
        assert int(cleaned[140, 198].min()) >= 245
        # Black bubble outline and dark outside artwork preserved
        assert int(cleaned[160, 160 - 112].max()) <= 35
        assert int(cleaned[15, 15].max()) <= 35


def test_auto_font_size_scales_with_bubble_dimensions_and_caps_single_words():
    base_font = QFont("Arial", 14)
    sample_dialogue = "Kita pakai serangan biasa aja, ya!"

    small_rect = QRect(0, 0, 110, 120)
    large_rect = QRect(0, 0, 280, 300)

    small_pt = compute_auto_font_size(small_rect, sample_dialogue, base_font)
    large_pt = compute_auto_font_size(large_rect, sample_dialogue, base_font)

    assert large_pt > small_pt + 6.0
    assert small_pt >= 7.0
    assert large_pt <= 64.0

    # Short exclamation shouldn't blow up to poster size inside a huge bubble
    short_pt = compute_auto_font_size(QRect(0, 0, 220, 220), "NO,", base_font)
    assert 16.0 <= short_pt <= 42.0

    # Vertical orientation swaps wrap width/height axes consistently
    tall_rect = QRect(0, 0, 120, 260)
    vert_pt = compute_auto_font_size(tall_rect, sample_dialogue, base_font, orientation="vertical")
    assert vert_pt >= 10.0


def test_smart_fit_scale_wraps_multiline_dialogue_cleanly(qapp):
    font = QFont("Arial", 10)
    area = TypesetArea(
        QRect(0, 0, 240, 220),
        "Jika aku ingat dengan benar, ada rumor kuat di kota.",
        font,
        QColor("#000000"),
        smart_fit_enabled=True,
    )
    scale = compute_auto_font_scale(QRect(0, 0, 240, 220), area)
    # Wrapped fit must scale UP substantially (>1.3x) rather than squeezing whole text onto 1 tiny line
    assert scale > 1.3


def test_closed_loop_brush_autofills_enclosed_interior_and_ignores_open_lines(qapp):
    label = SelectableImageLabel(parent=None)

    class _DummyMW:
        selection_mode_combo = type("C", (), {"currentText": staticmethod(lambda: "Inpaint Brush")})()
        original_pixmap = QPixmap(240, 240)
        zoom_factor = 1.0
        is_in_confirmation_mode = False
        hovered_area = None

        @staticmethod
        def unzoom_coords(pt, as_point=False):
            return QPoint(int(pt.x()), int(pt.y()))

    dummy_mw = _DummyMW()
    dummy_mw.original_pixmap.fill(Qt.white)
    label.main_window = dummy_mw
    label.set_inpaint_brush_size(20)
    label.resize(240, 240)

    def _mouse(ev_type, x, y, btn=Qt.LeftButton, buttons=Qt.LeftButton):
        return QMouseEvent(ev_type, QPointF(x, y), btn, buttons, Qt.NoModifier)

    # 1) Draw closed circle centered at (120, 120), radius 60
    pts = [
        (int(round(120 + 60 * math.cos(a))), int(round(120 + 60 * math.sin(a))))
        for a in np.linspace(0, 2 * math.pi, 37)
    ]
    label.mousePressEvent(_mouse(QEvent.MouseButtonPress, pts[0][0], pts[0][1]))
    for x, y in pts[1:]:
        label.mouseMoveEvent(_mouse(QEvent.MouseMove, x, y))
    label.mouseReleaseEvent(_mouse(QEvent.MouseButtonRelease, pts[-1][0], pts[-1][1], buttons=Qt.NoButton))

    assert label.inpaint_mask is not None
    assert label.inpaint_mask.pixelColor(120, 120).red() == 255
    assert label.inpaint_mask.pixelColor(100, 120).red() == 255
    assert label.inpaint_mask.pixelColor(12, 12).red() == 0

    # 2) Nearly-closed loop leaving a small ~10px gap (< brush diameter 20) still auto-fills interior
    label.clear_inpaint_mask()
    near_pts = [
        (int(round(120 + 55 * math.cos(a))), int(round(120 + 55 * math.sin(a))))
        for a in np.linspace(0, 2 * math.pi - 0.16, 32)
    ]
    label.mousePressEvent(_mouse(QEvent.MouseButtonPress, near_pts[0][0], near_pts[0][1]))
    for x, y in near_pts[1:]:
        label.mouseMoveEvent(_mouse(QEvent.MouseMove, x, y))
    label.mouseReleaseEvent(_mouse(QEvent.MouseButtonRelease, near_pts[-1][0], near_pts[-1][1], buttons=Qt.NoButton))

    assert label.inpaint_mask.pixelColor(120, 120).red() == 255
    assert label.inpaint_mask.pixelColor(12, 12).red() == 0

    # 3) Open straight line stroke must NOT auto-fill exterior pixels
    label.clear_inpaint_mask()
    label.mousePressEvent(_mouse(QEvent.MouseButtonPress, 30, 120))
    for x in range(40, 201, 10):
        label.mouseMoveEvent(_mouse(QEvent.MouseMove, x, 120))
    label.mouseReleaseEvent(_mouse(QEvent.MouseButtonRelease, 200, 120, buttons=Qt.NoButton))

    assert label.inpaint_mask.pixelColor(120, 60).red() == 0
    assert label.inpaint_mask.pixelColor(120, 180).red() == 0


def test_app_typeset_autofont_ui_and_area_sizing(qapp):
    snapshot = copy.deepcopy(cfg.SETTINGS)
    orig_cfg_save = cfg.save_settings
    orig_dlg_save = dlg_mod.save_settings
    cfg.save_settings = lambda *a, **kw: True
    dlg_mod.save_settings = lambda *a, **kw: True

    win = MangaOCRApp()
    try:
        win.right_panel_scroll.setVisible(True)
        win.resize(1366, 900)
        win.show()
        qapp.processEvents()

        assert hasattr(win, "auto_font_size_checkbox")
        assert hasattr(win, "fit_font_size_button")
        assert win.auto_font_size_checkbox.isChecked() is True

        settings = win.get_current_settings()
        assert settings.get("auto_font_size") is True

        small_area = win._create_typeset_area(
            QRect(10, 10, 110, 120), "Halo dunia, ini percobaan teks!", settings
        )
        large_area = win._create_typeset_area(
            QRect(20, 20, 260, 280), "Halo dunia, ini percobaan teks!", settings
        )
        assert large_area.font_info["pointSize"] > small_area.font_info["pointSize"] + 4.0

        # Selecting and pressing Fit Box updates both font_info and text_segments
        large_area.apply_point_size(9.0)
        win.typeset_areas = [large_area]
        win.set_selected_area(large_area, notify=True)
        win._on_fit_font_size_clicked()
        assert large_area.font_info["pointSize"] > 18.0
        assert large_area.text_segments[0]["font"]["pointSize"] == pytest.approx(
            large_area.font_info["pointSize"]
        )
    finally:
        win.close()
        qapp.processEvents()
        cfg.SETTINGS.clear()
        cfg.SETTINGS.update(snapshot)
        cfg.save_settings = orig_cfg_save
        dlg_mod.save_settings = orig_dlg_save


def test_inpaint_brush_ocr_translate_disables_background_box(qapp, monkeypatch):
    snapshot = copy.deepcopy(cfg.SETTINGS)
    orig_cfg_save = cfg.save_settings
    orig_dlg_save = dlg_mod.save_settings
    cfg.save_settings = lambda *a, **kw: True
    dlg_mod.save_settings = lambda *a, **kw: True

    win = MangaOCRApp()
    try:
        win.use_background_box_checkbox.setChecked(True)
        win.original_pixmap = QPixmap(160, 160)
        win.original_pixmap.fill(Qt.white)
        win.current_image_pil = Image.new("RGB", (160, 160), (255, 255, 255))
        win.image_label.set_inpaint_brush_size(20)
        win.image_label.inpaint_mask = QImage(160, 160, QImage.Format_Grayscale8)
        win.image_label.inpaint_mask.fill(0)
        win.image_label._paint_mask_stroke(QPoint(50, 50), QPoint(100, 100))

        queued_jobs = []
        monkeypatch.setattr(win, "add_job_to_queue", lambda job: queued_jobs.append(job))

        import src.core.workers as workers_mod

        class _DummyBrushWorker:
            def __init__(self, *a, **kw):
                self.signals = type(
                    "S",
                    (),
                    {
                        "progress": type("Sig", (), {"connect": lambda *_: None})(),
                        "error": type("Sig", (), {"connect": lambda *_: None})(),
                        "finished": type("Sig", (), {"connect": lambda *_: None})(),
                    },
                )()
                self.finished = type("Sig", (), {"connect": lambda *_: None})()

            def isRunning(self):
                return False

            def start(self):
                pass

        monkeypatch.setattr(workers_mod, "InpaintBrushWorker", _DummyBrushWorker)

        win.apply_inpaint_brush_selection(run_ocr_translate=True)
        assert len(queued_jobs) == 1
        job_settings = queued_jobs[0]["settings"]
        assert job_settings["use_background_box"] is False
        assert job_settings["use_inpaint"] is False

        area = win._create_typeset_area(queued_jobs[0]["rect"], "Teks bersih", job_settings)
        assert area.get_override("use_background_box", True) is False
        assert area.get_override("use_inpaint", True) is False

        win.typeset_areas = [area]
        win.set_selected_area(area, notify=True)
        assert win.use_background_box_checkbox.isChecked() is False
    finally:
        win.close()
        qapp.processEvents()
        cfg.SETTINGS.clear()
        cfg.SETTINGS.update(snapshot)
        cfg.save_settings = orig_cfg_save
        dlg_mod.save_settings = orig_dlg_save
