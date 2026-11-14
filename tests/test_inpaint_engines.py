"""Tests for integrated built-in inpainting engines, separate Full/Brush routing, and UI sync."""

from __future__ import annotations

import copy
import json
import os
import re
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest
import torch
from PIL import Image
from PyQt5.QtCore import QEvent, QMutex, QPoint, QPointF, QRect, Qt
from PyQt5.QtGui import QColor, QFont, QImage, QMouseEvent, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QGroupBox,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
)

import launcher_app
import src.core.config as cfg_mod
import src.core.inpaint as inpaint_mod
import src.core.workers as workers_mod
import src.ui.canvas as canvas_mod
import src.ui.dialogs as dlg_mod
from src.core.inpaint import (
    InpaintEngineManager,
    format_inpaint_engine_option,
    get_missing_engine_ids,
    is_engine_ready,
    normalize_inpaint_engine_id,
    resolve_cleanup_engine_ids,
)
from src.ui.canvas import SelectableImageLabel
from src.ui.main_window import FullPageTranslateWorker, MangaOCRApp
from src.ui.main_window_mixins.typeset import TypesetArea

_UNESCAPED_AMP_RE = re.compile(r"(?<!&)&(?!&)")


def _make_ui_harness() -> MangaOCRApp:
    win = MangaOCRApp.__new__(MangaOCRApp)
    QMainWindow.__init__(win)
    win.is_gpu_available = False
    win.selected_typeset_area = None
    win.pdf_document = None
    win.dl_models = {}
    win.translate_combo = SimpleNamespace(currentText=lambda: "Indonesian", findText=lambda *_: -1)
    win.ai_model_combo = SimpleNamespace(currentText=lambda: "OpenRouter", findText=lambda *_: -1)
    win.ocr_lang_combo = SimpleNamespace(currentData=lambda: {"engine": "AI_OCR", "code": "auto"}, findText=lambda *_: -1)
    win.orientation_combo = SimpleNamespace(currentText=lambda: "Auto-Detect")
    win.style_combo = SimpleNamespace(currentText=lambda: "Santai (Default)", findText=lambda *_: -1)
    win.history_preview_limit = 5
    win.result_table_registry = {"proofreader": set()}
    win.font_manager = None
    win.typeset_font = QFont("Arial", 14)
    win.typeset_color = QColor("#000000")
    win.typeset_char_spacing_value = 100.0
    win.typeset_line_spacing_value = 1.1
    win.typeset_alignment = "center"
    win.typeset_orientation = "horizontal"
    win.typeset_outline_enabled = True
    win.typeset_outline_width = 2.0
    win.typeset_outline_color = QColor("#000000")
    win.typeset_outline_style = "stroke"
    win.get_selected_model_info = lambda: {"name": "test-model", "display": "test-model"}
    win.get_selected_model_name = lambda: "test-model"
    win.show_toast = MagicMock()
    win.redraw_all_typeset_areas = MagicMock()
    win.set_selection_tool = MagicMock()
    win._is_inpaint_ocr_mode = lambda: False
    win._sync_cleanup_controls_from_selection = lambda: None
    win._default_cleanup_value = lambda key: bool(cfg_mod.SETTINGS.get("cleanup", {}).get(key, True))
    return win


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_normalize_and_legacy_migration():
    assert normalize_inpaint_engine_id("Built-in Big-LaMa") == "big_lama"
    assert normalize_inpaint_engine_id("Manga Inpaintor") == "manga_inpaintor"
    assert normalize_inpaint_engine_id("MI-GAN (Ringan)") == "migan"
    # Disabled Stable Diffusion Inpaint safely migrates to Big-LaMa
    assert normalize_inpaint_engine_id("Stable Diffusion Inpaint") == "big_lama"
    assert normalize_inpaint_engine_id("sd_inpaint") == "big_lama"
    assert normalize_inpaint_engine_id("OpenCV-NS") == "opencv_ns"
    assert normalize_inpaint_engine_id("OpenCV-Telea") == "opencv_telea"
    assert normalize_inpaint_engine_id("External IOPaint Server (Opsional)") == "iopaint_server"
    assert all(spec.id != "sd_inpaint" for spec in inpaint_mod.list_inpaint_engines("full"))
    assert all(spec.id != "sd_inpaint" for spec in inpaint_mod.list_inpaint_engines("brush"))

    # Legacy IOPaint default migrates automatically to built-in big_lama
    assert resolve_cleanup_engine_ids({"inpaint_model_name": "IOPaint Server"}) == (
        "big_lama",
        "big_lama",
    )
    # Explicit legacy OpenCV selection is preserved
    assert resolve_cleanup_engine_ids({"inpaint_model_name": "OpenCV-Telea"}) == (
        "opencv_telea",
        "opencv_telea",
    )
    # Unified selection resolves both Full & Brush to the single selected engine
    assert resolve_cleanup_engine_ids(
        {"inpaint_engine": "manga_inpaintor", "full_inpaint_engine": "big_lama", "brush_inpaint_engine": "migan"}
    ) == ("manga_inpaintor", "manga_inpaintor")


def test_model_discovery_and_sd_disabled(tmp_path, monkeypatch):
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    monkeypatch.setattr(inpaint_mod, "BUILTIN_INPAINT_MODELS_DIR", str(models_dir))
    monkeypatch.setattr(inpaint_mod, "LEGACY_IOPAINT_CHECKPOINTS_DIR", str(tmp_path / "none1"))
    monkeypatch.setattr(inpaint_mod, "TORCH_HUB_CHECKPOINTS_DIR", str(tmp_path / "none2"))

    assert not is_engine_ready("big_lama")
    assert is_engine_ready("opencv_ns")
    assert is_engine_ready("opencv_telea")
    assert is_engine_ready("iopaint_server")

    # Partial manga_inpaintor (only 1 of 2 files) must report not ready
    (models_dir / "manga_inpaintor.jit").write_bytes(b"0" * 10_000_000)
    assert not is_engine_ready("manga_inpaintor")
    (models_dir / "erika.jit").write_bytes(b"0" * 5_000_000)
    assert is_engine_ready("manga_inpaintor")

    # Disabled sd_inpaint migrates to big_lama readiness rather than checking SD directories
    sd_dir = tmp_path / "sd_local"
    sd_dir.mkdir()
    (sd_dir / "model_index.json").write_text("{}", encoding="utf-8")
    assert not is_engine_ready("sd_inpaint", sd_repo_id=str(sd_dir))


class _FakeLamaModule(torch.nn.Module):
    def forward(self, image: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        # Fill masked pixels with solid gray (0.5) cleanly
        return image * (1.0 - mask) + 0.5 * mask


class _FakeLineModule(torch.nn.Module):
    def forward(self, gray: torch.Tensor) -> torch.Tensor:
        return gray


class _FakeMangaModule(torch.nn.Module):
    def forward(
        self,
        gray_norm: torch.Tensor,
        lines_norm: torch.Tensor,
        mask: torch.Tensor,
        noise: torch.Tensor,
    ) -> torch.Tensor:
        # Fill masked area with bright gray (+0.5 in [-1, 1] -> ~191)
        return gray_norm * (1.0 - mask) + 0.5 * mask


class _FakeMiganModule(torch.nn.Module):
    def forward(self, model_in: torch.Tensor) -> torch.Tensor:
        # model_in has 4 channels [0.5 - mask, erased_r, erased_g, erased_b]; return neutral zero [-1,1] (~127)
        b, _c, h, w = model_in.shape
        return torch.zeros((b, 3, h, w), dtype=model_in.dtype, device=model_in.device)


def test_single_slot_manager_inference_and_unload_on_swap(tmp_path, monkeypatch):
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    monkeypatch.setattr(inpaint_mod, "BUILTIN_INPAINT_MODELS_DIR", str(models_dir))
    monkeypatch.setattr(inpaint_mod, "LEGACY_IOPAINT_CHECKPOINTS_DIR", str(tmp_path / "none1"))
    monkeypatch.setattr(inpaint_mod, "TORCH_HUB_CHECKPOINTS_DIR", str(tmp_path / "none2"))

    # Relax minimum size validation so tiny traced test modules pass
    monkeypatch.setitem(
        inpaint_mod.INPAINT_ENGINE_SPECS,
        "big_lama",
        inpaint_mod.InpaintEngineSpec(
            id="big_lama",
            label="Built-in Big-LaMa",
            short_label="Big-LaMa (Built-in)",
            badge="Default",
            description="test",
            size_hint="~1 MB",
            files=(inpaint_mod.ModelFileSpec("big-lama.pt", "https://invalid", "0", min_bytes=64),),
        ),
    )
    monkeypatch.setitem(
        inpaint_mod.INPAINT_ENGINE_SPECS,
        "manga_inpaintor",
        inpaint_mod.InpaintEngineSpec(
            id="manga_inpaintor",
            label="Built-in Manga Inpaintor",
            short_label="Manga Inpaintor",
            badge="Manga",
            description="test",
            size_hint="~1 MB",
            files=(
                inpaint_mod.ModelFileSpec("manga_inpaintor.jit", "https://invalid", "0", min_bytes=64),
                inpaint_mod.ModelFileSpec("erika.jit", "https://invalid", "0", min_bytes=64),
            ),
        ),
    )
    monkeypatch.setitem(
        inpaint_mod.INPAINT_ENGINE_SPECS,
        "migan",
        inpaint_mod.InpaintEngineSpec(
            id="migan",
            label="Built-in MI-GAN",
            short_label="MI-GAN (Ringan)",
            badge="Light",
            description="test",
            size_hint="~1 MB",
            files=(inpaint_mod.ModelFileSpec("migan_traced.pt", "https://invalid", "0", min_bytes=64),),
        ),
    )

    torch.jit.trace(
        _FakeLamaModule(),
        (torch.zeros(1, 3, 16, 16), torch.zeros(1, 1, 16, 16)),
    ).save(str(models_dir / "big-lama.pt"))
    torch.jit.trace(
        _FakeLineModule(),
        torch.zeros(1, 1, 16, 16),
    ).save(str(models_dir / "erika.jit"))
    torch.jit.trace(
        _FakeMangaModule(),
        (
            torch.zeros(1, 1, 16, 16),
            torch.zeros(1, 1, 16, 16),
            torch.zeros(1, 1, 16, 16),
            torch.zeros(1, 1, 16, 16),
        ),
    ).save(str(models_dir / "manga_inpaintor.jit"))
    torch.jit.trace(
        _FakeMiganModule(),
        torch.zeros(1, 4, 64, 64),
    ).save(str(models_dir / "migan_traced.pt"))

    # Odd dimensions (67x53) force pad_img_to_modulo coverage
    rgb = np.full((67, 53, 3), 240, dtype=np.uint8)
    rgb[:12, :12] = [10, 20, 30]
    mask = np.zeros((67, 53), dtype=np.uint8)
    mask[20:36, 15:35] = 255
    pil_img = Image.fromarray(rgb)
    pil_msk = Image.fromarray(mask).convert("L")

    mgr = InpaintEngineManager()

    # 1. Big-LaMa
    out1 = np.array(mgr.inpaint(pil_img, pil_msk, engine_id="big_lama", device="cpu", auto_download=False))
    assert out1.shape == (67, 53, 3)
    assert np.array_equal(out1[:12, :12], rgb[:12, :12])
    assert 120 <= int(out1[28, 25, 0]) <= 135
    assert mgr.loaded_engine_key == ("big_lama", "", "cpu")

    # 2. Swap to Manga Inpaintor -> previous model unloaded, single slot tracks manga_inpaintor
    out2 = np.array(
        mgr.inpaint(pil_img, pil_msk, engine_id="manga_inpaintor", device="cpu", auto_download=False)
    )
    assert out2.shape == (67, 53, 3)
    assert np.array_equal(out2[:12, :12], rgb[:12, :12])
    assert 180 <= int(out2[28, 25, 0]) <= 200
    assert mgr.loaded_engine_key == ("manga_inpaintor", "", "cpu")

    # 3. Swap to MI-GAN -> single slot tracks migan
    out3 = np.array(mgr.inpaint(pil_img, pil_msk, engine_id="migan", device="cpu", auto_download=False))
    assert out3.shape == (67, 53, 3)
    assert np.array_equal(out3[:12, :12], rgb[:12, :12])
    assert 120 <= int(out3[28, 25, 0]) <= 135
    assert mgr.loaded_engine_key == ("migan", "", "cpu")

    # 4. Explicit unload clears single slot
    mgr.unload_loaded_model()
    assert mgr.loaded_engine_key is None


def test_real_big_lama_smoke_if_available():
    if not is_engine_ready("big_lama"):
        return
    rgb = np.full((64, 64, 3), 255, dtype=np.uint8)
    rgb[20:44, 20:44] = 0
    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[18:46, 18:46] = 255
    mgr = inpaint_mod.get_inpaint_manager()
    out = np.array(
        mgr.inpaint(
            Image.fromarray(rgb),
            Image.fromarray(mask).convert("L"),
            engine_id="big_lama",
            device="cpu",
            auto_download=False,
        )
    )
    assert out.shape == (64, 64, 3)
    # Interior white bubble reconstruction removes the black square cleanly
    assert int(out[32, 32].mean()) >= 200
    mgr.unload_loaded_model()


def test_separate_full_vs_brush_routing_and_launcher(tmp_path, monkeypatch):
    calls = []

    class _StubManager:
        def inpaint(self, pil_image, pil_mask, engine_id="big_lama", **kwargs):
            calls.append(engine_id)
            return pil_image

    monkeypatch.setattr(inpaint_mod, "get_inpaint_manager", lambda: _StubManager())

    img = Image.new("RGB", (96, 96), (255, 255, 255))
    msk = Image.new("L", (96, 96), 0)
    msk_arr = np.zeros((96, 96), dtype=np.uint8)
    msk_arr[20:50, 20:50] = 255
    msk = Image.fromarray(msk_arr).convert("L")

    # Brush worker honors unified inpaint_engine
    brush_worker = workers_mod.InpaintBrushWorker(
        None,
        img,
        msk,
        {"inpaint_engine": "migan", "full_inpaint_engine": "big_lama", "brush_inpaint_engine": "sd_inpaint"},
    )
    done_results = []
    errors = []
    brush_worker.signals.finished.connect(done_results.append)
    brush_worker.signals.error.connect(errors.append)
    brush_worker.run()
    assert not errors
    assert len(done_results) == 1
    assert calls[-1] == "migan"

    # Full-page worker uses the same unified inpaint_engine resolution
    cv_img = np.full((96, 96, 3), 255, dtype=np.uint8)
    full_worker = FullPageTranslateWorker(
        None,
        "",
        {"inpaint_engine": "manga_inpaintor", "full_inpaint_engine": "big_lama", "brush_inpaint_engine": "big_lama"},
        False,
        page_pil=img,
    )
    full_worker._run_page_inpaint(cv_img, [], ai_mask=msk_arr)
    assert calls[-1] == "manga_inpaintor"

    # External IOPaint launcher guard: never launch Inpainting\run.bat by default
    assert launcher_app._should_start_external_inpainting(str(tmp_path)) is False
    (tmp_path / "settings.json").write_text(
        json.dumps({"cleanup": {"inpaint_engine": "big_lama"}}),
        encoding="utf-8",
    )
    assert launcher_app._should_start_external_inpainting(str(tmp_path)) is False
    (tmp_path / "settings.json").write_text(
        json.dumps({"cleanup": {"inpaint_engine": "iopaint_server"}}),
        encoding="utf-8",
    )
    assert launcher_app._should_start_external_inpainting(str(tmp_path)) is True


def test_ui_unified_inpaint_sync_and_settings_dialog(qapp, monkeypatch):
    saved_cleanup = copy.deepcopy(cfg_mod.SETTINGS.get("cleanup", {}))
    monkeypatch.setattr(cfg_mod, "save_settings", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(dlg_mod, "save_settings", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("src.ui.main_window_mixins.settings.save_settings", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("src.ui.main_window_mixins.translate.save_settings", lambda *_args, **_kwargs: None)

    try:
        cfg_mod.SETTINGS.setdefault("cleanup", {})["inpaint_engine"] = "big_lama"
        cfg_mod.SETTINGS["cleanup"]["full_inpaint_engine"] = "big_lama"
        cfg_mod.SETTINGS["cleanup"]["brush_inpaint_engine"] = "big_lama"

        win = _make_ui_harness()
        full_tab = win._create_full_translate_tab()
        cleanup_tab = win._create_cleanup_tab()

        # Verify combos fit inside 380px right workspace panel and have no unescaped '&'
        for tab in (full_tab, cleanup_tab):
            for gb in tab.findChildren(QGroupBox):
                assert not _UNESCAPED_AMP_RE.search(gb.title()), f"Unescaped & in QGroupBox {gb.title()!r}"
            for btn in tab.findChildren(QPushButton):
                assert not _UNESCAPED_AMP_RE.search(btn.text()), f"Unescaped & in button {btn.text()!r}"
            for combo in tab.findChildren(QComboBox):
                assert combo.minimumWidth() == 0
                assert combo.sizePolicy().horizontalPolicy() == QSizePolicy.Ignored

        # Cleanup tab now exposes a single unified dropdown & SD UI is absent
        assert hasattr(win, "cleanup_inpaint_engine_combo")
        assert not hasattr(win, "cleanup_full_engine_combo")
        assert not hasattr(win, "cleanup_brush_engine_combo")
        assert win.full_inpaint_engine_combo.findData("sd_inpaint") == -1

        # Changing Full combo to manga_inpaintor syncs Cleanup AND Brush combos identically
        idx_manga = win.full_inpaint_engine_combo.findData("manga_inpaintor")
        assert idx_manga != -1
        win.full_inpaint_engine_combo.setCurrentIndex(idx_manga)
        assert win.cleanup_inpaint_engine_combo.currentData() == "manga_inpaintor"
        assert win.brush_inpaint_engine_combo.currentData() == "manga_inpaintor"

        # Changing Brush combo to migan syncs Full AND Cleanup combos identically
        idx_migan_ws = win.brush_inpaint_engine_combo.findData("migan")
        assert idx_migan_ws != -1
        win.brush_inpaint_engine_combo.setCurrentIndex(idx_migan_ws)
        assert win.cleanup_inpaint_engine_combo.currentData() == "migan"
        assert win.full_inpaint_engine_combo.currentData() == "migan"

        current = win.get_current_settings()
        assert current["inpaint_engine"] == "migan"
        assert current["full_inpaint_engine"] == "migan"
        assert current["brush_inpaint_engine"] == "migan"

        # SettingsCenterDialog Cleanup tab shows ONE unified selector (no SD options) and syncs cleanly
        dlg = dlg_mod.SettingsCenterDialog(win, initial_tab="cleanup")
        assert hasattr(dlg, "cleanup_inpaint_engine_combo")
        assert not hasattr(dlg, "cleanup_sd_model_combo")
        assert dlg.cleanup_inpaint_engine_combo.currentData() == "migan"

        idx_lama = dlg.cleanup_inpaint_engine_combo.findData("big_lama")
        dlg.cleanup_inpaint_engine_combo.setCurrentIndex(idx_lama)
        assert dlg._commit_settings(close_dialog=False) is True
        assert cfg_mod.SETTINGS["cleanup"]["inpaint_engine"] == "big_lama"
        assert cfg_mod.SETTINGS["cleanup"]["full_inpaint_engine"] == "big_lama"
        assert cfg_mod.SETTINGS["cleanup"]["brush_inpaint_engine"] == "big_lama"
        assert win.full_inpaint_engine_combo.currentData() == "big_lama"
        assert win.brush_inpaint_engine_combo.currentData() == "big_lama"
        assert win.cleanup_inpaint_engine_combo.currentData() == "big_lama"

        dlg.close()
        full_tab.deleteLater()
        cleanup_tab.deleteLater()
    finally:
        cfg_mod.SETTINGS["cleanup"] = saved_cleanup


def test_format_engine_option_and_missing_list(monkeypatch):
    monkeypatch.setattr(
        inpaint_mod,
        "is_engine_ready",
        lambda eid, sd_repo_id=None, extra_dirs=None: eid != "migan",
    )

    text_lama, badge_lama, ready_lama = format_inpaint_engine_option("big_lama")
    assert ready_lama is True
    assert "Siap" in text_lama
    assert badge_lama == "Siap"

    text_migan, badge_migan, ready_migan = format_inpaint_engine_option("migan")
    assert ready_migan is False
    assert "Unduh" in text_migan
    assert "Belum diunduh" in badge_migan

    text_cv, _, ready_cv = format_inpaint_engine_option("opencv_ns")
    assert ready_cv is True
    assert "Offline" in text_cv

    text_ext, _, ready_ext = format_inpaint_engine_option("iopaint_server")
    assert ready_ext is True
    assert "Eksternal" in text_ext

    missing = get_missing_engine_ids({"inpaint_engine": "migan"})
    assert missing == ["migan"]


def test_sd_step_callback_progress_and_mid_denoising_cancel():
    class _FakeSDPipe:
        def __init__(self, cancel_after_step=None):
            self._interrupt = False
            self.cancel_after_step = cancel_after_step
            self.steps_executed = 0

        @property
        def interrupt(self):
            return self._interrupt

        def __call__(
            self,
            prompt="",
            negative_prompt="",
            image=None,
            mask_image=None,
            height=64,
            width=64,
            num_inference_steps=4,
            guidance_scale=7.5,
            strength=1.0,
            generator=None,
            callback_on_step_end=None,
            callback_on_step_end_tensor_inputs=None,
        ):
            self._interrupt = False
            for i in range(int(num_inference_steps)):
                if self.interrupt:
                    break
                self.steps_executed += 1
                if self.cancel_after_step is not None and (i + 1) >= self.cancel_after_step:
                    self._trigger_cancel = True
                if callback_on_step_end is not None:
                    callback_on_step_end(self, i, i, {"latents": None})
            return SimpleNamespace(images=[Image.fromarray(np.full((height, width, 3), 210, dtype=np.uint8))])

    mgr = InpaintEngineManager()
    rgb = np.full((64, 64, 3), 120, dtype=np.uint8)
    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[16:48, 16:48] = 255

    # Run full 4 steps and capture per-step progress
    events = []
    pipe_ok = _FakeSDPipe()
    out = mgr._run_sd_crop(
        {"pipe": pipe_ok},
        "cpu",
        rgb,
        mask,
        sd_steps=4,
        sd_prompt="",
        sd_negative_prompt="",
        progress_cb=lambda pct, msg: events.append((pct, msg)),
        check_cancel=lambda: False,
    )
    assert out.shape == (64, 64, 3)
    assert pipe_ok.steps_executed == 4
    step_msgs = [m for _p, m in events if "Step " in m]
    assert any("Step 1/4" in m for m in step_msgs)
    assert any("Step 4/4" in m for m in step_msgs)
    assert [p for p, m in events if "Step " in m][-1] >= 90

    # Trigger cancellation at step 2 -> _interrupt becomes True and execution halts cleanly
    pipe_cancel = _FakeSDPipe()
    step_count = {"n": 0}

    def _cancel_on_second_step():
        return step_count["n"] >= 2

    def _track_cb(pct, msg):
        if "Step 2/6" in msg:
            step_count["n"] = 2

    with pytest.raises(RuntimeError, match="dibatalkan"):
        mgr._run_sd_crop(
            {"pipe": pipe_cancel},
            "cpu",
            rgb,
            mask,
            sd_steps=6,
            sd_prompt="",
            sd_negative_prompt="",
            progress_cb=_track_cb,
            check_cancel=_cancel_on_second_step,
        )
    assert pipe_cancel.steps_executed == 3
    assert pipe_cancel._interrupt is True


def test_brush_worker_progress_cancel_and_ui_readiness_indicators(qapp, monkeypatch):
    saved_cleanup = copy.deepcopy(cfg_mod.SETTINGS.get("cleanup", {}))
    monkeypatch.setattr(cfg_mod, "save_settings", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(dlg_mod, "save_settings", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("src.ui.main_window_mixins.settings.save_settings", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("src.ui.main_window_mixins.translate.save_settings", lambda *_args, **_kwargs: None)

    # Part A: Worker step progress & clean cancellation without OpenCV fallback
    class _CancellingMgr:
        def inpaint(self, img, msk, engine_id="", progress_cb=None, check_cancel=None, **kwargs):
            if progress_cb:
                progress_cb(25, "Big-LaMa (CPU): Area 1/4...")
            worker_ref.cancel()
            assert check_cancel is not None and check_cancel() is True
            raise RuntimeError("Inpainting dibatalkan oleh pengguna.")

    monkeypatch.setattr(inpaint_mod, "get_inpaint_manager", lambda: _CancellingMgr())
    img = Image.fromarray(np.full((64, 64, 3), 255, dtype=np.uint8))
    msk = Image.fromarray(np.full((64, 64), 255, dtype=np.uint8)).convert("L")
    worker_ref = workers_mod.InpaintBrushWorker(None, img, msk, {"inpaint_engine": "migan"})

    pct_events = []
    cancelled_calls = []
    error_calls = []
    finished_calls = []
    worker_ref.signals.progress_percent.connect(lambda p, m: pct_events.append((p, m)))
    worker_ref.signals.cancelled.connect(lambda: cancelled_calls.append(True))
    worker_ref.signals.error.connect(error_calls.append)
    worker_ref.signals.finished.connect(finished_calls.append)
    worker_ref.run()

    assert any(p == 25 and "Area 1/4" in m for p, m in pct_events)
    assert cancelled_calls == [True]
    assert not error_calls
    assert not finished_calls

    # Part B: Workspace dropdown indicators, inline download CTA, & live running card
    ready_state = {"migan_ready": False}

    def _fake_ready(eid, sd_repo_id=None, extra_dirs=None):
        if eid == "migan":
            return ready_state["migan_ready"]
        return True

    monkeypatch.setattr(inpaint_mod, "is_engine_ready", _fake_ready)
    monkeypatch.setattr("src.ui.main_window_mixins.settings.is_engine_ready", _fake_ready)
    monkeypatch.setattr(dlg_mod, "is_engine_ready", _fake_ready)

    try:
        cfg_mod.SETTINGS.setdefault("cleanup", {})["inpaint_engine"] = "big_lama"
        cfg_mod.SETTINGS["cleanup"]["full_inpaint_engine"] = "big_lama"
        cfg_mod.SETTINGS["cleanup"]["brush_inpaint_engine"] = "big_lama"

        win = _make_ui_harness()
        full_tab = win._create_full_translate_tab()
        cleanup_tab = win._create_cleanup_tab()

        # Combo items carry readiness tags & status icons
        idx_lama = win.full_inpaint_engine_combo.findData("big_lama")
        idx_migan = win.brush_inpaint_engine_combo.findData("migan")
        assert idx_lama != -1 and idx_migan != -1
        assert "Siap" in win.full_inpaint_engine_combo.itemText(idx_lama)
        assert not win.full_inpaint_engine_combo.itemIcon(idx_lama).isNull()
        assert "Unduh" in win.brush_inpaint_engine_combo.itemText(idx_migan)
        assert not win.brush_inpaint_engine_combo.itemIcon(idx_migan).isNull()

        # Ready initially -> inline download rows stay hidden
        assert win.full_inpaint_status_row.isHidden()
        assert win.brush_inpaint_status_row.isHidden()
        assert win.cleanup_download_missing_btn.isHidden()

        # Select missing migan -> inline Unduh prompts & Cleanup missing button appear across unified UI
        win.brush_inpaint_engine_combo.setCurrentIndex(idx_migan)
        assert not win.brush_inpaint_status_row.isHidden()
        assert not win.full_inpaint_status_row.isHidden()
        assert "belum diunduh" in win.brush_inpaint_status_label.text()
        assert not win.cleanup_download_missing_btn.isHidden()

        # Simulate completed download -> combo turns green ("· Siap") and download CTA hides
        ready_state["migan_ready"] = True
        win._on_workspace_inpaint_dl_thread_done()
        idx_migan_after = win.brush_inpaint_engine_combo.findData("migan")
        assert "Siap" in win.brush_inpaint_engine_combo.itemText(idx_migan_after)
        assert win.brush_inpaint_status_row.isHidden()
        assert win.full_inpaint_status_row.isHidden()
        assert win.cleanup_download_missing_btn.isHidden()

        # Test live running progress panel transitions cleanly
        assert win.inpaint_running_panel.isHidden()
        win._start_inpaint_brush_progress_ui("Big-LaMa")
        assert not win.inpaint_running_panel.isHidden()
        win._on_inpaint_brush_progress_percent(50, "Big-LaMa (CPU): Area 1/2...")
        assert win.inpaint_running_bar.maximum() == 100
        assert win.inpaint_running_bar.value() == 50
        assert "Area 1/2" in win.inpaint_running_label.text()
        win._finish_inpaint_brush_ui("Selesai", 1000)
        assert win.inpaint_running_panel.isHidden()
        assert win.inpaint_confirm_button.isEnabled()
        assert win.inpaint_confirm_button.text() == "Clean"

        full_tab.deleteLater()
        cleanup_tab.deleteLater()
    finally:
        cfg_mod.SETTINGS["cleanup"] = saved_cleanup


def _make_canvas_draw_harness():
    """Minimal MangaOCRApp harness exercising real redraw/preview/mask paths without full UI."""
    win = _make_ui_harness()
    win.paint_mutex = QMutex(QMutex.Recursive)
    win.is_transform_preview = False
    win._transform_preview_pixmap = None
    win._compare_mode_active = False
    win.is_in_confirmation_mode = False
    win.zoom_factor = 1.0
    win.redo_stack = []
    win._last_redraw_request = 0.0
    win.backup_typeset_settings = None
    win.detected_panels = []
    win.show_panels_checkbox = None

    pil_img = Image.new("RGB", (240, 240), (240, 240, 240))
    arr = np.array(pil_img)
    # Dark text-like patch inside first area to exercise OpenCV inpainting
    arr[40:60, 40:80] = 20
    pil_img = Image.fromarray(arr)
    qimg = QImage(arr.data, 240, 240, 240 * 3, QImage.Format_RGB888).copy()

    win.current_image_pil = pil_img
    win.original_pixmap = QPixmap.fromImage(qimg)
    win.typeset_pixmap = win.original_pixmap.copy()

    a1 = TypesetArea(
        rect=QRect(24, 24, 90, 60),
        text="Halo",
        font=QFont("Arial", 12),
        color=QColor("#000000"),
    )
    a1.set_override("use_inpaint", True)
    a1.set_override("use_background_box", False)

    a2 = TypesetArea(
        rect=QRect(130, 120, 80, 60),
        text="Dunia",
        font=QFont("Arial", 12),
        color=QColor("#000000"),
    )
    a2.set_override("use_inpaint", True)
    a2.set_override("use_background_box", False)

    a3 = TypesetArea(
        rect=QRect(24, 150, 80, 40),
        text="Clean",
        font=QFont("Arial", 12),
        color=QColor("#000000"),
    )
    a3.set_override("use_inpaint", False)
    a3.set_override("use_background_box", False)

    win.typeset_areas = [a1, a2, a3]
    win.selected_typeset_area = a1
    win._area_uses_auto_text_color = lambda _area: False
    win.draw_area_text = lambda *_a, **_kw: None
    win.draw_area_text_plain = lambda *_a, **_kw: None
    win.get_current_settings = lambda: {
        "full_inpaint_engine": "big_lama",
        "inpaint_model_name": "Built-in Big-LaMa",
        "inpaint_device": "cpu",
        "sd_inpaint_model": "",
        "sd_inpaint_steps": 20,
        "sd_inpaint_prompt": "",
        "sd_inpaint_negative_prompt": "",
        "inpaint_padding": 4,
        "use_dl_detector": True,
        "dl_provider": "Kitsumed",
        "dl_model_file": "model_dynamic.onnx",
        "use_inpaint": True,
        "use_background_box": False,
        "constrain_text": True,
    }
    # Use the real MangaOCRApp redraw method rather than the UI-sync mock
    win.redraw_all_typeset_areas = MangaOCRApp.redraw_all_typeset_areas.__get__(win, MangaOCRApp)
    win.zoom_coords = lambda r: QRect(r) if isinstance(r, QRect) else QPoint(r)
    win.unzoom_coords = lambda p, as_point=False: (QPointF(p) if isinstance(p, (QPoint, QPointF)) else QRect(p))
    return win


def test_interactive_draw_and_transform_preview_never_block_gui_thread(qapp, monkeypatch):
    inpaint_calls = []
    dl_calls = []
    process_events_calls = []

    class _FailIfCalledInpaintMgr:
        def inpaint(self, pil_image, pil_mask, engine_id="big_lama", **kwargs):
            inpaint_calls.append(engine_id)
            return pil_image

    monkeypatch.setattr(inpaint_mod, "get_inpaint_manager", lambda: _FailIfCalledInpaintMgr())
    monkeypatch.setattr(inpaint_mod, "is_engine_ready", lambda *a, **kw: True)
    monkeypatch.setattr(QApplication, "processEvents", lambda *a, **kw: process_events_calls.append(True))

    win = _make_canvas_draw_harness()

    def _track_dl(full_cv, settings):
        dl_calls.append(full_cv.shape[:2])
        m = np.zeros(full_cv.shape[:2], dtype=np.uint8)
        m[20:90, 20:120] = 255
        return m

    win.detect_bubble_with_dl_model = _track_dl

    canvas_img = QImage(240, 240, QImage.Format_RGB888)
    painter = QPainter(canvas_img)
    try:
        # 1. Interactive canvas draw (for_saving=False) must use fast OpenCV, never AI/DL/processEvents
        win.draw_single_area(painter, win.typeset_areas[0], win.current_image_pil, for_saving=False)
        assert inpaint_calls == []
        assert dl_calls == []
        assert process_events_calls == []

        # 2. _prepare_transform_preview_base (triggered on Hand mouse press) must use for_saving=False
        assert win._prepare_transform_preview_base() is True
        assert inpaint_calls == []
        assert dl_calls == []
        assert process_events_calls == []

        # 3. Exporting / background save worker (for_saving=True) still uses AI inpaint & DL mask cleanly
        win.draw_single_area(painter, win.typeset_areas[0], win.current_image_pil, for_saving=True)
        assert inpaint_calls == ["big_lama"]
        assert len(dl_calls) == 1
        assert process_events_calls == []
    finally:
        painter.end()

    # 4. Click-to-translate path preserves DL detection (allow_dl=True default) without processEvents
    cv_img = np.full((240, 240, 3), 240, dtype=np.uint8)
    mask_dl = win.find_speech_bubble_mask(cv_img, QRect(40, 40, 10, 10), win.get_current_settings(), for_saving=False)
    assert mask_dl is not None
    assert len(dl_calls) == 2
    assert process_events_calls == []


def test_hand_move_and_pan_responsiveness(qapp, monkeypatch):
    inpaint_calls = []
    dl_calls = []
    process_events_calls = []

    class _SpyMgr:
        def inpaint(self, pil_image, pil_mask, engine_id="big_lama", **kwargs):
            inpaint_calls.append(engine_id)
            return pil_image

    monkeypatch.setattr(inpaint_mod, "get_inpaint_manager", lambda: _SpyMgr())
    monkeypatch.setattr(inpaint_mod, "is_engine_ready", lambda *a, **kw: True)
    monkeypatch.setattr(QApplication, "processEvents", lambda *a, **kw: process_events_calls.append(True))

    win = _make_canvas_draw_harness()
    win.detect_bubble_with_dl_model = lambda full_cv, settings: (dl_calls.append(True) or None)

    scroll = QScrollArea()
    scroll.resize(120, 120)
    label = SelectableImageLabel(win)
    label.resize(240, 240)
    scroll.setWidget(label)
    win.image_scroll = scroll
    win.image_label = label
    win.image_canvas_widget = label
    win.zoom_label = SimpleNamespace(setText=lambda _t: None)
    win.selection_mode_combo = SimpleNamespace(currentText=lambda: "Transform (Hand)")
    win.update_pen_tool_buttons_visibility = lambda *_a, **_kw: None
    win.clear_selected_area = lambda: win.set_selected_area(None)
    win._sync_typeset_controls_from_selection = lambda: None
    win._area_uses_auto_text_color = lambda area: area is win.typeset_areas[2]
    label.setPixmap(win.typeset_pixmap)
    label.set_transform_mode(True)

    # Press -> Drag -> Release text box with Transform (Hand)
    start_pos = QPoint(50, 50)
    move_pos = QPoint(75, 65)
    orig_rect = QRect(win.typeset_areas[0].rect)

    press_ev = QMouseEvent(QEvent.MouseButtonPress, start_pos, label.mapToGlobal(start_pos), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    move_ev = QMouseEvent(QEvent.MouseMove, move_pos, label.mapToGlobal(move_pos), Qt.NoButton, Qt.LeftButton, Qt.NoModifier)
    release_ev = QMouseEvent(QEvent.MouseButtonRelease, move_pos, label.mapToGlobal(move_pos), Qt.LeftButton, Qt.NoButton, Qt.NoModifier)

    label.mousePressEvent(press_ev)
    assert win.is_transform_preview is True
    label.mouseMoveEvent(move_ev)
    label.mouseReleaseEvent(release_ev)
    assert win.is_transform_preview is False
    assert win.typeset_areas[0].rect.topLeft() == orig_rect.topLeft() + QPoint(25, 15)
    assert getattr(win.typeset_areas[2], "_auto_text_color", None) == QColor(0, 0, 0)

    # Middle-mouse panning works cleanly without blocking
    pan_start = QPoint(60, 60)
    pan_end = QPoint(40, 45)
    scroll.horizontalScrollBar().setRange(0, 200)
    scroll.verticalScrollBar().setRange(0, 200)
    scroll.horizontalScrollBar().setValue(50)
    scroll.verticalScrollBar().setValue(50)
    pan_press = QMouseEvent(QEvent.MouseButtonPress, pan_start, QPoint(260, 260), Qt.MiddleButton, Qt.MiddleButton, Qt.NoModifier)
    pan_move = QMouseEvent(QEvent.MouseMove, pan_end, QPoint(240, 245), Qt.NoButton, Qt.MiddleButton, Qt.NoModifier)
    pan_release = QMouseEvent(QEvent.MouseButtonRelease, pan_end, QPoint(240, 245), Qt.MiddleButton, Qt.NoButton, Qt.NoModifier)

    label.mousePressEvent(pan_press)
    assert label.panning is True
    label.mouseMoveEvent(pan_move)
    label.mouseReleaseEvent(pan_release)
    assert label.panning is False
    assert scroll.horizontalScrollBar().value() == 70
    assert scroll.verticalScrollBar().value() == 65

    assert inpaint_calls == []
    assert dl_calls == []
    assert process_events_calls == []

    scroll.deleteLater()


def test_brush_overlay_cached_and_scroll_wheel_guarded(qapp, monkeypatch):
    from PyQt5.QtGui import QImage, QPaintEvent, QWheelEvent

    win = _make_canvas_draw_harness()
    scroll = QScrollArea()
    scroll.resize(200, 300)
    label = SelectableImageLabel(win)
    scroll.setWidget(label)
    win.image_scroll = scroll
    win.image_label = label
    win.image_canvas_widget = label
    win.selection_mode_combo = SimpleNamespace(currentText=lambda: "Inpaint Brush")
    win.pdf_document = object()
    win.detection_thread = None

    next_calls = []
    prev_calls = []
    monkeypatch.setattr(win, "load_next_image", lambda: next_calls.append(True))
    monkeypatch.setattr(win, "load_prev_image", lambda: prev_calls.append(True))

    label.resize(900, 1400)
    pm = QPixmap(900, 1400)
    pm.fill(Qt.white)
    label.setPixmap(pm)
    label.inpaint_mask = QImage(900, 1400, QImage.Format_Grayscale8)
    label.inpaint_mask.fill(0)
    monkeypatch.setattr(label, "_is_inpaint_brush_mode", lambda mode=None: True)

    alpha_calls = []
    orig_set_alpha = QImage.setAlphaChannel

    def _counting_set_alpha(self, alpha):
        alpha_calls.append(alpha.size())
        return orig_set_alpha(self, alpha)

    monkeypatch.setattr(QImage, "setAlphaChannel", _counting_set_alpha)

    # First paint populates overlay cache once from empty mask; incremental strokes update cache without setAlphaChannel
    label._paint_mask_stroke(QPoint(120, 120), QPoint(180, 160))
    assert alpha_calls == [label.inpaint_mask.size()]
    alpha_calls.clear()

    label._paint_mask_stroke(QPoint(180, 160), QPoint(240, 200))
    assert alpha_calls == []

    # Simulated scroll & Alt-Tab window exposure repaints must NEVER re-run full-image setAlphaChannel
    for top in (0, 200, 450, 700, 950):
        ev = QPaintEvent(QRect(0, top, 900, 350))
        label.paintEvent(ev)
    assert alpha_calls == []

    label.clear_inpaint_mask()
    label.paintEvent(QPaintEvent(QRect(0, 0, 900, 400)))
    assert alpha_calls == []

    # Guarded wheelEvent skips PDF page switching while InpaintBrushWorker is running
    class _BusyWorker:
        def __init__(self, running: bool):
            self._running = running

        def isRunning(self):
            return self._running

    win._inpaint_brush_worker = _BusyWorker(True)
    wheel_down = QWheelEvent(QPoint(100, 100), QPoint(100, 100), QPoint(0, 0), QPoint(0, -120), Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
    MangaOCRApp.wheelEvent(win, wheel_down)
    assert next_calls == []

    win._inpaint_brush_worker = _BusyWorker(False)
    MangaOCRApp.wheelEvent(win, wheel_down)
    assert next_calls == [True]

    scroll.deleteLater()


def test_compact_roi_cropping_used_on_medium_pages(monkeypatch):
    # Two spaced bubbles on an 850x1200 medium page must produce two small crops, never full-page
    msk = np.zeros((1200, 850), dtype=np.uint8)
    msk[120:220, 120:260] = 255
    msk[700:820, 500:660] = 255

    rois = inpaint_mod._merge_boxes_into_rois(msk, margin=80, min_size=160)
    assert len(rois) == 2
    total_area = sum((r[2] - r[0]) * (r[3] - r[1]) for r in rois)
    assert total_area < 0.30 * (850 * 1200)

    mgr = inpaint_mod.InpaintEngineManager()
    run_shapes = []
    monkeypatch.setattr(mgr, "_ensure_loaded", lambda *args, **kwargs: {"model": object()})

    def _fake_big_lama(_payload, _device, crop_rgb, _crop_msk):
        run_shapes.append(crop_rgb.shape[:2])
        return crop_rgb

    monkeypatch.setattr(mgr, "_run_big_lama", _fake_big_lama)
    rgb = Image.new("RGB", (850, 1200), (240, 240, 240))
    mgr.inpaint(rgb, Image.fromarray(msk).convert("L"), engine_id="big_lama", device="cpu")
    assert len(run_shapes) == 2
    assert all(max(sh) < 400 for sh in run_shapes)


