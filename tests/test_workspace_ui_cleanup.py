"""Regression tests for workspace sidebar SVG icons, retired batch buttons,
unescaped Qt mnemonics, and 380px right-panel width fit across all tabs.
"""

import ast
import copy
import re
from pathlib import Path

import pytest
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QPushButton,
    QRadioButton,
    QSizePolicy,
)

import src.core.config as cfg
import src.ui.dialogs as dlg_mod
from src.ui.icons import _PATHS
from src.ui.main_window import MangaOCRApp

_UNESCAPED_AMP_RE = re.compile(r"(?<!&)&(?!&)")
_SRC_UI_DIR = Path(__file__).resolve().parent.parent / "src" / "ui"


@pytest.fixture(scope="module")
def app_win(qapp):
    """Instantiate MangaOCRApp once offscreen with settings persistence stubbed."""
    snapshot = copy.deepcopy(cfg.SETTINGS)
    orig_cfg_save = cfg.save_settings
    orig_dlg_save = dlg_mod.save_settings
    cfg.save_settings = lambda *a, **kw: True
    dlg_mod.save_settings = lambda *a, **kw: True

    win = MangaOCRApp()
    win.right_panel_scroll.setVisible(True)
    win.resize(1366, 900)
    win.show()
    for _ in range(4):
        qapp.processEvents()
    win.splitter.setSizes([240, 740, 380])
    for _ in range(4):
        qapp.processEvents()

    yield win

    win.close()
    qapp.processEvents()
    cfg.SETTINGS.clear()
    cfg.SETTINGS.update(snapshot)
    cfg.save_settings = orig_cfg_save
    dlg_mod.save_settings = orig_dlg_save


def test_sidebar_buttons_use_valid_svg_icons(app_win):
    buttons = app_win._sidebar_buttons
    assert len(buttons) == 7
    assert app_win.right_stack.count() == 7

    for btn in buttons:
        icon_name = btn.property("icon_name")
        assert icon_name in _PATHS, f"Unknown icon key {icon_name!r} on tab {btn.text()!r}"
        assert icon_name != "dot", f"Tab {btn.text()!r} fell back to 'dot' icon"
        assert not btn.icon().isNull(), f"Tab {btn.text()!r} has null icon"


def test_all_ui_app_icon_calls_reference_known_svg_keys():
    missing = []
    for py_path in sorted(_SRC_UI_DIR.rglob("*.py")):
        tree = ast.parse(py_path.read_text(encoding="utf-8"), filename=str(py_path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            func_name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            if func_name != "app_icon":
                continue

            key_node = node.args[0] if node.args else None
            if key_node is None:
                for kw in node.keywords:
                    if kw.arg == "name":
                        key_node = kw.value
                        break
            if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                if key_node.value not in _PATHS:
                    missing.append((py_path.name, node.lineno, key_node.value))

    assert not missing, f"Unknown app_icon keys (would fall back to 'dot'): {missing}"


def test_retired_batch_buttons_and_edit_menu_fallback(app_win):
    assert getattr(app_win, "process_batch_button", "MISSING") is None
    assert getattr(app_win, "batch_process_button", "MISSING") is None

    edit_actions = []
    for top_action in app_win.menuBar().actions():
        menu = top_action.menu()
        if menu is not None and top_action.text() in ("&Edit", "Edit"):
            edit_actions = [a.text() for a in menu.actions()]
            break
    assert "Detect Bubbles on Page" in edit_actions

    # Handlers guarding retired buttons must not raise AttributeError when buttons are None.
    app_win.set_ui_for_detection(True)
    app_win.set_ui_for_detection(False)
    app_win.set_ui_for_confirmation(True)
    app_win.set_ui_for_confirmation(False)
    app_win.handle_worker_error_ui("test worker error")


def test_right_panel_fits_380px_without_overflow_or_unescaped_ampersands(app_win, qapp):
    rp = app_win.right_panel_scroll
    rpc = rp.widget()
    vp_w = rp.viewport().width()
    assert rpc.minimumSizeHint().width() <= vp_w, (
        f"Right panel min width {rpc.minimumSizeHint().width()} exceeds viewport {vp_w}"
    )

    for idx in range(app_win.right_stack.count()):
        app_win._on_sidebar_nav(idx)
        for _ in range(3):
            qapp.processEvents()

    bad_mnemonics = []
    for cls in (QGroupBox, QPushButton, QCheckBox, QRadioButton):
        for widget in rpc.findChildren(cls):
            label = widget.title() if isinstance(widget, QGroupBox) else widget.text()
            if label and _UNESCAPED_AMP_RE.search(label):
                bad_mnemonics.append((cls.__name__, widget.objectName(), label))
    assert not bad_mnemonics, f"Unescaped '&' mnemonics found: {bad_mnemonics}"

    tab_combos = {
        0: [app_win.ocr_lang_combo, app_win.translate_combo],
        1: [app_win._chat_widget.chat_content_widget._model_combo],
        2: [app_win.full_mode_combo, app_win.full_translator_combo, app_win.full_scope_combo],
        5: [app_win.selection_mode_combo],
        6: [app_win.ai_model_combo, app_win.style_combo],
    }
    for tab_idx, combos in tab_combos.items():
        app_win._on_sidebar_nav(tab_idx)
        for _ in range(3):
            qapp.processEvents()
        for combo in combos:
            assert combo.minimumWidth() == 0
            assert combo.sizePolicy().horizontalPolicy() == QSizePolicy.Ignored
            assert combo.width() <= vp_w, f"Combo width {combo.width()} > viewport {vp_w} on tab {tab_idx}"

    # Verify Typeset spacing & warp readouts stay comfortably inside their page viewport.
    app_win._on_sidebar_nav(3)
    for _ in range(3):
        qapp.processEvents()
    typeset_scroll = app_win.right_stack.widget(3)
    ts_vp_w = typeset_scroll.viewport().width()
    ts_container = typeset_scroll.widget()
    for w in (
        app_win.font_size_spin,
        app_win.line_spacing_value_label,
        app_win.char_spacing_value_label,
        app_win.warp_intensity_value_label,
    ):
        right_edge = w.mapTo(ts_container, QPoint(w.width(), 0)).x()
        assert right_edge <= ts_vp_w, f"Typeset control right edge {right_edge} > viewport {ts_vp_w}"
