"""Regression & UI tests for Gradient/Screentone/Layer rendering and revamped AdvancedTextEditDialog."""

import copy

from PIL import Image
import pytest
from PyQt5.QtCore import QPointF, QRect, Qt
from PyQt5.QtGui import QColor, QFont, QImage, QPainter

import src.core.config as cfg
import src.ui.dialogs as dlg_mod
from src.ui.advanced_text_editor_dialog import AdvancedTextEditDialog
from src.ui.canvas import TypesetArea
from src.ui.main_window import MangaOCRApp


def _make_app(qapp):
    snapshot = copy.deepcopy(cfg.SETTINGS)
    orig_cfg_save = cfg.save_settings
    orig_dlg_save = dlg_mod.save_settings
    cfg.save_settings = lambda *a, **kw: True
    dlg_mod.save_settings = lambda *a, **kw: True
    win = MangaOCRApp()
    qapp.processEvents()
    return win, snapshot, orig_cfg_save, orig_dlg_save


def _restore_app(win, snapshot, orig_cfg_save, orig_dlg_save, qapp):
    win.close()
    qapp.processEvents()
    cfg.SETTINGS.clear()
    cfg.SETTINGS.update(snapshot)
    cfg.save_settings = orig_cfg_save
    dlg_mod.save_settings = orig_dlg_save


def _count_color_pixels(img: QImage, pred) -> tuple[int, tuple[int, int, int, int] | None]:
    count = 0
    min_x, min_y, max_x, max_y = 10**9, 10**9, -1, -1
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            if pred(c):
                count += 1
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
    bbox = (min_x, min_y, max_x, max_y) if count else None
    return count, bbox


def test_gradient_fill_renders_wrapping_horizontal_and_vertical(qapp):
    win, snap, s1, s2 = _make_app(qapp)
    try:
        pil_blank = Image.new("RGB", (320, 320), (255, 255, 255))
        rect = QRect(40, 40, 190, 220)

        for orient in ("horizontal", "vertical"):
            area = TypesetArea(
                rect=rect,
                text="GRADASI RAPI DI DALAM BUBBLE",
                font=QFont("Arial", 16, QFont.Bold),
                color=QColor("#000000"),
                orientation=orient,
                text_outline=False,
                gradient_enabled=True,
                gradient_colors=["#ff0000", "#0000ff"],
                gradient_angle=0.0,
                smart_fit_enabled=True,
            )
            img = QImage(320, 320, QImage.Format_ARGB32_Premultiplied)
            img.fill(Qt.white)
            settings = dict(win.get_current_settings())
            settings.update({"use_background_box": False, "constrain_text": True, "use_auto_text_color": True})
            painter = QPainter(img)
            try:
                win.draw_single_area(
                    painter,
                    area,
                    pil_blank,
                    for_saving=True,
                    settings=settings,
                )
            finally:
                painter.end()

            red_count, red_box = _count_color_pixels(
                img, lambda c: c.red() > 170 and c.blue() < 110 and c.green() < 110
            )
            blue_count, blue_box = _count_color_pixels(
                img, lambda c: c.blue() > 170 and c.red() < 110 and c.green() < 110
            )
            assert red_count > 60, f"Expected red gradient pixels in {orient} mode, got {red_count}"
            assert blue_count > 60, f"Expected blue gradient pixels in {orient} mode, got {blue_count}"
            # Word-wrapping must keep text inside the rect (small glyph overhang margin <= 10px)
            assert red_box[0] >= rect.left() - 10 and blue_box[2] <= rect.right() + 10
            assert red_box[1] >= rect.top() - 10 and blue_box[3] <= rect.bottom() + 10
    finally:
        _restore_app(win, snap, s1, s2, qapp)


def test_screentone_and_concentric_outline_layers_render_within_bounds(qapp):
    win, snap, s1, s2 = _make_app(qapp)
    try:
        img_pat = QImage(280, 220, QImage.Format_ARGB32_Premultiplied)
        img_pat.fill(Qt.white)
        area_pat = TypesetArea(
            rect=QRect(30, 30, 160, 140),
            text="POLA ARSIR KOMIK PANJANG",
            font=QFont("Arial", 22, QFont.Bold),
            color=QColor("#111111"),
            pattern_fill_enabled=True,
            pattern_type="dot",
            pattern_scale=1.0,
        )
        p1 = QPainter(img_pat)
        try:
            win.draw_area_text(p1, area_pat)
        finally:
            p1.end()

        dark_count, dark_box = _count_color_pixels(img_pat, lambda c: c.red() < 160)
        assert dark_count > 120
        assert dark_box[0] >= 20 and dark_box[2] <= 200

        # Concentric outline layers on effect == 'none'
        img_layers = QImage(280, 160, QImage.Format_ARGB32_Premultiplied)
        img_layers.fill(Qt.white)
        area_layers = TypesetArea(
            rect=QRect(20, 20, 220, 110),
            text="LAPISAN OUTLINE",
            font=QFont("Arial", 24, QFont.Bold),
            color=QColor("#ffffff"),
            outline_layers=[
                {"width": 3.0, "color": "#ef4444"},
                {"width": 7.0, "color": "#2563eb"},
            ],
        )
        p2 = QPainter(img_layers)
        try:
            win.draw_area_text(p2, area_layers)
        finally:
            p2.end()

        red_ring, _ = _count_color_pixels(img_layers, lambda c: c.red() > 170 and c.blue() < 110)
        blue_ring, _ = _count_color_pixels(img_layers, lambda c: c.blue() > 170 and c.red() < 110)
        assert red_ring > 60
        assert blue_ring > 60
    finally:
        _restore_app(win, snap, s1, s2, qapp)


def test_advanced_text_editor_dialog_tabs_live_preview_and_preserve_on_ai_translate(qapp):
    win, snap, s1, s2 = _make_app(qapp)
    try:
        # Standalone sanity check with parent=None and area=None
        standalone = AdvancedTextEditDialog(parent=None, area=None, font_manager=None)
        qapp.processEvents()
        assert standalone.tabs.count() == 4
        assert not standalone.preview_widget._pixmap.isNull()
        standalone.close()

        area = TypesetArea(
            rect=QRect(50, 50, 240, 160),
            text="Halo pembaca manga!",
            font=QFont("Arial", 18),
            color=QColor("#111827"),
            gradient_enabled=True,
            gradient_colors=["#ff0000", "#0000ff"],
            gradient_angle=45.0,
            margins={"top": 6, "right": 8, "bottom": 6, "left": 8},
        )
        dlg = AdvancedTextEditDialog(parent=win, area=area, font_manager=win.font_manager)
        dlg.resize(1120, 740)
        dlg.show()
        qapp.processEvents()

        # Check loaded state and live preview
        assert dlg.tabs.count() == 4
        assert dlg.gradient_enabled_checkbox.isChecked() is True
        assert dlg.margin_top_spin.value() == 6
        assert not dlg.preview_widget._pixmap.isNull()

        # Swap gradient colors & verify middle stops list handling
        dlg._swap_gradient_colors()
        assert dlg.gradient_colors_store == ["#0000ff", "#ff0000"]
        dlg.gradient_colors_store.insert(1, "#00ff00")
        dlg._update_gradient_buttons_style()
        assert dlg._gradient_extra_stops_row.count() == 1
        dlg._remove_gradient_stop()
        assert dlg.gradient_colors_store == ["#0000ff", "#ff0000"]

        # Interactive curve editor <-> spinbox sync + "Aktifkan Mode Curved"
        dlg._activate_curved_mode()
        assert dlg.effect_combo.currentData() == "curved"
        dlg.curve_editor.curveChanged.emit(0.15, 0.85, 0.80, 0.10)
        assert dlg.cp1x_spin.value() == pytest.approx(0.15)
        assert dlg.cp1y_spin.value() == pytest.approx(0.85)
        dlg.cp2y_spin.setValue(0.33)
        assert dlg.curve_editor.cp2 == QPointF(0.80, 0.33)
        dlg._reset_bezier_curve()
        assert dlg.cp1x_spin.value() == pytest.approx(0.25)

        # User edits must NOT be clobbered after clicking AI Translate
        dlg.margin_top_spin.setValue(18)
        dlg.text_outline_checkbox.setChecked(True)
        dlg.shadow_enabled_checkbox.setChecked(True)
        dlg.pattern_enabled_checkbox.setChecked(True)

        orig_get_model = win.get_selected_model_name
        orig_translate = win.translate_with_ai
        win.get_selected_model_name = lambda: ("openrouter", "mock-model")
        win.translate_with_ai = lambda *a, **kw: "Terjemahan baru AI"
        try:
            dlg._on_ai_translate_clicked()
        finally:
            win.get_selected_model_name = orig_get_model
            win.translate_with_ai = orig_translate

        assert "Terjemahan baru AI" in dlg.text_edit.toPlainText()
        assert dlg.margin_top_spin.value() == 18
        assert dlg.gradient_enabled_checkbox.isChecked() is True
        assert dlg.shadow_enabled_checkbox.isChecked() is True

        dlg._handle_accept()
        res = dlg.get_result()
        assert res is not None
        assert res["plain_text"] == "Terjemahan baru AI"
        assert res["margins"]["top"] == 18
        assert res["gradient_enabled"] is True
        assert res["gradient_colors"] == ["#0000ff", "#ff0000"]
        assert res["text_outline"] is True
        assert res["text_outline_style"] in ("stroke", "glow")
        assert res["shadow_enabled"] is True
        assert res["pattern_fill_enabled"] is True
        assert res["effect"] == "curved"
        assert len(res["bezier_points"]) == 2
        dlg.close()
    finally:
        _restore_app(win, snap, s1, s2, qapp)


def test_categorized_symbols_and_love_variations_insertion(qapp):
    dlg = AdvancedTextEditDialog(parent=None, area=None, font_manager=None)
    try:
        expected_keys = {
            "love_classic",
            "love_variations",
            "love_kaomoji",
            "sparkles_stars",
            "music",
            "manga_reactions",
            "punctuation",
        }
        assert set(dlg.symbol_submenus.keys()) == expected_keys

        love_actions = []
        for k in ("love_classic", "love_variations", "love_kaomoji"):
            love_actions.extend(dlg.symbol_submenus[k].actions())
        assert len(love_actions) >= 50

        dlg.text_edit.clear()
        dlg.symbol_submenus["love_classic"].actions()[1].trigger()
        dlg.symbol_submenus["love_variations"].actions()[11].trigger()
        dlg.symbol_submenus["love_kaomoji"].actions()[0].trigger()
        qapp.processEvents()

        text = dlg.text_edit.toPlainText()
        assert "♡" in text
        assert "💕" in text
        assert "(♡˙︶˙♡)" in text
        assert not dlg.preview_widget._pixmap.isNull()
    finally:
        dlg.close()


def test_vertical_upright_orientation_render_autofit_and_controls(qapp):
    from src.ui.canvas import compute_auto_font_size

    win, snap, s1, s2 = _make_app(qapp)
    try:
        # 1. Sidebar Typeset 3rd orientation button works cleanly
        win.orientation_vertical_upright_button.setChecked(True)
        qapp.processEvents()
        assert win.typeset_orientation == "vertical_upright"

        # 2. Auto font size fits "INI APA...?" cleanly in a tall narrow bubble
        tall_rect = QRect(40, 20, 76, 250)
        fitted = compute_auto_font_size(
            tall_rect,
            "INI APA...?",
            QFont("Arial", 14),
            orientation="vertical_upright",
        )
        assert 9.0 <= fitted <= 30.0

        # 3. Render both plain/rich and gradient vector modes upright stacked inside rect
        pil_blank = Image.new("RGB", (180, 300), (255, 255, 255))
        for use_grad in (False, True):
            area = TypesetArea(
                rect=tall_rect,
                text="INI APA...?",
                font=QFont("Arial", 14, QFont.Bold),
                color=QColor("#111111"),
                orientation="vertical_upright",
                gradient_enabled=use_grad,
                gradient_colors=["#ef4444", "#2563eb"],
                gradient_angle=90.0,
                smart_fit_enabled=True,
            )
            img = QImage(180, 300, QImage.Format_ARGB32_Premultiplied)
            img.fill(Qt.white)
            settings = dict(win.get_current_settings())
            settings.update({"use_background_box": False, "constrain_text": True, "use_auto_text_color": not use_grad})
            painter = QPainter(img)
            try:
                win.draw_single_area(painter, area, pil_blank, for_saving=True, settings=settings)
            finally:
                painter.end()

            ink_count, ink_box = _count_color_pixels(img, lambda c: c.red() < 230 or c.blue() < 230)
            assert ink_count > 80
            assert ink_box[0] >= tall_rect.left() - 6 and ink_box[2] <= tall_rect.right() + 6
            assert ink_box[1] >= tall_rect.top() - 6 and ink_box[3] <= tall_rect.bottom() + 6
            # Upright vertical stacking spans significantly taller than wide
            assert (ink_box[3] - ink_box[1]) > (ink_box[2] - ink_box[0]) * 2.0

        # 4. AdvancedTextEditDialog round-trips vertical_upright
        area_up = TypesetArea(
            rect=tall_rect,
            text="INI APA...?",
            font=QFont("Arial", 14),
            color=QColor("#111111"),
            orientation="vertical_upright",
        )
        dlg = AdvancedTextEditDialog(parent=win, area=area_up, font_manager=win.font_manager)
        qapp.processEvents()
        assert dlg.orientation_combo.currentData() == "vertical_upright"
        assert not dlg.preview_widget._pixmap.isNull()
        dlg._handle_accept()
        assert dlg.get_result()["orientation"] == "vertical_upright"
        dlg.close()
    finally:
        _restore_app(win, snap, s1, s2, qapp)
