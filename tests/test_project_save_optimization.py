"""Tests for compact `.manga_proj` ZIP+patch storage and backward compatibility."""

import base64
import io
import json
import os
import zipfile

import numpy as np
from PIL import Image
from PyQt5.QtCore import QMutex, QRect
from PyQt5.QtGui import QColor, QFont, QPolygon
from PyQt5.QtWidgets import QPushButton

from src.core.project_archive import (
    PROJECT_SCHEMA_VERSION,
    decode_cleaned_image,
    encode_cleaned_state,
    read_project_archive,
    record_has_cleaned_image,
    write_project_archive,
)
from src.core.workers import BatchSaveWorker, ProjectSaveWorker
from src.ui.canvas import TypesetArea
from src.ui.main_window_mixins.history import HistoryMixin
from src.ui.main_window_mixins.inpaint import InpaintMixin
from src.ui.main_window_mixins.layer import LayerMixin
from src.ui.main_window_mixins.projectio import ProjectioMixin
from src.ui.main_window_mixins.typeset import TypesetMixin


def _make_manga_page(width=200, height=300, seed=7):
    rng = np.random.default_rng(seed)
    arr = rng.integers(20, 235, size=(height, width, 3), dtype=np.uint8)
    return Image.fromarray(arr, "RGB")


def _paint_patch_box(pil_img, box=(30, 40, 90, 110), color=(255, 255, 255)):
    arr = np.array(pil_img, copy=True)
    x1, y1, x2, y2 = box
    arr[y1:y2, x1:x2] = color
    return Image.fromarray(arr, "RGB")


def _to_png_b64(pil_img):
    buf = io.BytesIO()
    pil_img.convert("RGB").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def test_encode_decode_sparse_patch_is_lossless_and_skips_unchanged():
    orig = _make_manga_page()
    assert encode_cleaned_state(orig, orig_pil=orig) == {}

    cleaned = _paint_patch_box(orig, box=(25, 35, 85, 95), color=(250, 250, 250))
    state = encode_cleaned_state(cleaned, orig_pil=orig)
    assert "cleaned_patch" in state
    assert "cleaned_image_png" not in state
    assert state["cleaned_patch"]["x"] == 25
    assert state["cleaned_patch"]["y"] == 35
    assert state["cleaned_patch"]["w"] == 60
    assert state["cleaned_patch"]["h"] == 60
    assert isinstance(state["cleaned_patch"]["bytes"], (bytes, bytearray))

    reconstructed = decode_cleaned_image(state, orig_pil=orig)
    assert reconstructed is not None
    assert np.array_equal(np.asarray(reconstructed), np.asarray(cleaned))


def test_encode_falls_back_to_full_webp_when_no_orig_or_mostly_changed():
    orig = _make_manga_page()
    full_change = _paint_patch_box(orig, box=(0, 0, orig.width, orig.height), color=(10, 200, 30))

    state_big = encode_cleaned_state(full_change, orig_pil=orig)
    assert "cleaned_image_webp" in state_big
    assert np.array_equal(np.asarray(decode_cleaned_image(state_big)), np.asarray(full_change))

    state_no_orig = encode_cleaned_state(full_change, orig_pil=None)
    assert "cleaned_image_webp" in state_no_orig
    assert np.array_equal(np.asarray(decode_cleaned_image(state_no_orig)), np.asarray(full_change))


def test_project_save_worker_writes_compact_zip_and_roundtrips(tmp_path):
    img_path = tmp_path / "page1.png"
    empty_path = tmp_path / "page2.png"
    orig = _make_manga_page(width=240, height=320)
    orig.save(img_path)
    orig.save(empty_path)

    cleaned = _paint_patch_box(orig, box=(40, 50, 100, 120), color=(255, 255, 255))
    cleaned_state = encode_cleaned_state(cleaned, orig_pil=orig)

    area = TypesetArea(QRect(40, 50, 60, 70), "Halo", QFont("Arial", 12), QColor("#000000"))
    target_proj = tmp_path / "demo.manga_proj"
    snapshot = {
        "project_dir": str(tmp_path),
        "current_image_path": str(img_path),
        "current_pdf_page": -1,
        "typeset_data": {
            str(img_path): {
                "areas": [area.to_payload()],
                "redo": [],
                **cleaned_state,
            },
            str(empty_path): {"areas": [], "redo": []},
        },
        "history_entries": [],
        "proofreader_entries": [],
        "quality_entries": [],
        "history_counter": 1,
        "typeset_font": TypesetArea.font_to_dict(QFont("Arial", 12)),
        "typeset_color": "#000000",
        "settings": {},
        "app_version": "14.9.8.7",
    }

    worker = ProjectSaveWorker(str(target_proj), snapshot)
    results = []
    worker.finished.connect(lambda ok, msg: results.append((ok, msg)))
    worker.run()
    assert results == [(True, "Project saved.")]
    assert zipfile.is_zipfile(target_proj)

    with zipfile.ZipFile(target_proj, "r") as zf:
        names = zf.namelist()
        assert "project.json" in names
        assert any(name.startswith("assets/") and name.endswith(".webp") for name in names)
        raw_json = json.loads(zf.read("project.json").decode("utf-8"))
        assert raw_json["schema_version"] == PROJECT_SCHEMA_VERSION
        assert "page2.png" not in raw_json["typeset_data"]
        p1 = raw_json["typeset_data"]["page1.png"]
        assert "cleaned_image_png" not in p1
        assert "pre_inpaint_image_png" not in p1
        assert "asset" in p1["cleaned_patch"]

    loaded, fmt = read_project_archive(str(target_proj))
    assert fmt == "zip"
    rec = loaded["typeset_data"]["page1.png"]
    assert "bytes" in rec["cleaned_patch"]
    rebuilt = decode_cleaned_image(rec, orig_path=str(img_path))
    assert np.array_equal(np.asarray(rebuilt), np.asarray(cleaned))


def test_legacy_v4_json_loads_and_migrates_to_compact_zip(tmp_path):
    img_path = tmp_path / "01.jpg"
    orig = _make_manga_page(width=220, height=300, seed=11)
    orig.save(img_path, format="PNG")
    # Re-open exact decoded RGB from disk so diff matches disk source
    disk_orig = Image.open(img_path).convert("RGB")
    cleaned = _paint_patch_box(disk_orig, box=(20, 30, 70, 90), color=(255, 255, 255))

    legacy_proj = tmp_path / "legacy.manga_proj"
    missing_key = str(tmp_path / "missing_page.png")
    legacy_payload = {
        "schema_version": 4,
        "project_dir_rel": ".",
        "project_dir": str(tmp_path),
        "current_image_path": str(img_path),
        "current_pdf_page": -1,
        "image_order": ["01.jpg", "missing_page.png"],
        "typeset_data": {
            "01.jpg": {
                "areas": [],
                "redo": [],
                "cleaned_image_png": _to_png_b64(cleaned),
                "pre_inpaint_image_png": _to_png_b64(disk_orig),
            },
            "missing_page.png": {
                "areas": [],
                "redo": [],
                "cleaned_image_png": _to_png_b64(cleaned),
                "pre_inpaint_image_png": _to_png_b64(disk_orig),
            },
        },
        "history_entries": [],
        "proofreader_entries": [],
        "quality_entries": [],
        "history_counter": 0,
    }
    legacy_proj.write_text(json.dumps(legacy_payload, indent=1), encoding="utf-8")
    legacy_size = legacy_proj.stat().st_size

    loaded, fmt = read_project_archive(str(legacy_proj))
    assert fmt == "json"
    assert np.array_equal(
        np.asarray(decode_cleaned_image(loaded["typeset_data"]["01.jpg"])),
        np.asarray(cleaned),
    )

    snapshot = {
        "project_dir": str(tmp_path),
        "current_image_path": str(img_path),
        "current_pdf_page": -1,
        "typeset_data": {
            str(img_path): loaded["typeset_data"]["01.jpg"],
            missing_key: loaded["typeset_data"]["missing_page.png"],
        },
        "history_entries": [],
        "proofreader_entries": [],
        "quality_entries": [],
        "history_counter": 0,
        "typeset_font": None,
        "typeset_color": "#000000",
        "settings": {},
        "app_version": "14.9.8.7",
    }
    write_project_archive(str(legacy_proj), snapshot, convert_legacy=True)
    assert zipfile.is_zipfile(legacy_proj)
    assert legacy_proj.stat().st_size < legacy_size * 0.6

    migrated, fmt2 = read_project_archive(str(legacy_proj))
    assert fmt2 == "zip"
    rec_disk = migrated["typeset_data"]["01.jpg"]
    assert "cleaned_patch" in rec_disk
    assert "pre_inpaint_image_png" not in rec_disk
    assert np.array_equal(
        np.asarray(decode_cleaned_image(rec_disk, orig_path=str(img_path))),
        np.asarray(cleaned),
    )

    # Missing source file on disk must keep both cleaned and pre_inpaint images
    rec_missing = migrated["typeset_data"]["missing_page.png"]
    assert record_has_cleaned_image(rec_missing)
    assert decode_cleaned_image(rec_missing) is not None
    assert "pre_inpaint_webp" in rec_missing or "pre_inpaint_image_png" in rec_missing


def test_batch_save_worker_uses_cleaned_patch(qapp, tmp_path):
    img_path = tmp_path / "p1.png"
    orig = _make_manga_page(width=180, height=220, seed=3)
    orig.save(img_path)
    disk_orig = Image.open(img_path).convert("RGB")
    cleaned = _paint_patch_box(disk_orig, box=(20, 20, 120, 120), color=(0, 255, 0))
    state = encode_cleaned_state(cleaned, orig_pil=disk_orig)

    area = TypesetArea(QRect(30, 30, 80, 40), "Tes", QFont("Arial", 12), QColor("#000000"))

    class DummyApp:
        @staticmethod
        def get_current_data_key(path=None, page=-1):
            return path

        @staticmethod
        def draw_single_area(painter, area_obj, pil_img, for_saving=False, settings=None):
            pass

    worker = BatchSaveWorker(
        DummyApp(),
        [str(img_path)],
        fmt="PNG",
        typeset_data={str(img_path): {"areas": [area], **state}},
    )
    saved = []
    errors = []
    worker.signals.file_saved.connect(saved.append)
    worker.signals.error.connect(errors.append)
    worker.run()

    assert errors == []
    assert saved == [str(img_path)]
    out_img = Image.open(tmp_path / "p1_typeset.png").convert("RGB")
    assert np.array_equal(np.asarray(out_img), np.asarray(cleaned))


class _Host(TypesetMixin, InpaintMixin, ProjectioMixin, HistoryMixin, LayerMixin):
    """Minimal mixin host covering compare/cancel/restore/undo with cleaned_patch."""

    def __init__(self, image_path, qapp):
        self.project_dir = os.path.dirname(image_path)
        self.current_image_path = image_path
        self.current_pdf_page = -1
        self.pdf_document = None
        self.all_typeset_data = {}
        self.typeset_areas = []
        self.redo_stack = []
        self.selected_typeset_area = None
        self.paint_mutex = QMutex()
        self.original_pixmap = None
        self.typeset_pixmap = None
        self.current_image_pil = None
        self.unmodified_image_pil = None
        self.unmodified_original_pixmap = None
        self.active_curves_points = None
        self._compare_mode_active = False
        self._undo_history = []
        self._undo_history_idx = -1
        self._MAX_UNDO_HISTORY = 50
        self.inpaint_compare_button = QPushButton("Compare")
        self.inpaint_compare_button.setCheckable(True)
        self.inpaint_cancel_button = QPushButton("Cancel")
        self.undo_button = QPushButton("Undo")
        self.redo_button = QPushButton("Redo")

    def get_current_data_key(self, path=None, page=-1):
        return path if path is not None else self.current_image_path

    def safe_open_image(self, file_path):
        return Image.open(file_path).convert("RGB")

    def get_current_settings(self):
        return {"inpaint_padding": 5}

    def _apply_base_image(self, pil_image):
        self.current_image_pil = pil_image.convert("RGB")
        self.unmodified_image_pil = self.current_image_pil.copy()

    def _encode_cleaned_state(self, pil_image, orig_pil=None):
        return encode_cleaned_state(pil_image, orig_pil=orig_pil)

    def _decode_cleaned_image(self, record, orig_pil=None, key=None):
        return decode_cleaned_image(
            record,
            orig_pil=orig_pil,
            orig_key=key or self.get_current_data_key(),
            pdf_document=self.pdf_document,
        )

    def _resolve_pre_inpaint_image(self, key=None, record=None, fallback_pil=None):
        from src.core.project_archive import decode_pre_inpaint_image, open_source_image_for_key

        rec = record if isinstance(record, dict) else self.all_typeset_data.get(key or self.get_current_data_key(), {})
        explicit = decode_pre_inpaint_image(rec)
        if explicit is not None:
            return explicit
        target_key = key or self.get_current_data_key()
        disk_img = open_source_image_for_key(target_key, pdf_document=self.pdf_document)
        if disk_img is not None:
            return disk_img
        return fallback_pil

    def _has_inpaint_state(self, key=None, record=None):
        from src.core.project_archive import can_resolve_source_for_key, record_has_pre_inpaint_image

        rec = record if isinstance(record, dict) else self.all_typeset_data.get(key or self.get_current_data_key(), {})
        if not record_has_cleaned_image(rec):
            return False
        target_key = key or self.get_current_data_key()
        return record_has_pre_inpaint_image(rec) or can_resolve_source_for_key(target_key, pdf_document=self.pdf_document)

    def _set_compare_controls_checked(self, checked):
        self.inpaint_compare_button.setChecked(bool(checked))

    def redraw_all_typeset_areas(self, refresh_layers=True):
        pass

    def update_display(self):
        pass

    def _refresh_layers_list(self):
        pass

    def _refresh_undo_timeline(self):
        pass

    def clear_selected_area(self):
        self.selected_typeset_area = None

    def show_toast(self, *args, **kwargs):
        pass

    def show_banner(self, *args, **kwargs):
        pass

    def move_entry_to_deleted_history(self, *args, **kwargs):
        pass


def test_inpaint_compare_restore_cancel_and_undo_without_pre_inpaint_png(qapp, tmp_path):
    img_path = tmp_path / "page.png"
    orig = _make_manga_page(width=180, height=240, seed=21)
    orig.save(img_path)
    disk_orig = Image.open(img_path).convert("RGB")
    cleaned = _paint_patch_box(disk_orig, box=(30, 40, 100, 110), color=(255, 255, 255))

    host = _Host(str(img_path), qapp)
    host._apply_base_image(disk_orig)

    # Simulate finishing inpaint brush without saving pre_inpaint_image_png
    host._on_inpaint_brush_finished(cleaned)
    rec = host.all_typeset_data[str(img_path)]
    assert "cleaned_patch" in rec
    assert "pre_inpaint_image_png" not in rec
    assert host.inpaint_compare_button.isEnabled()
    assert host.inpaint_cancel_button.isEnabled()
    assert np.array_equal(np.asarray(host.current_image_pil), np.asarray(cleaned))

    # Compare ON -> disk original; Compare OFF -> cleaned patch
    from src.ui.main_window import MangaOCRApp
    MangaOCRApp._on_compare_mode_toggled(host, True)
    assert np.array_equal(np.asarray(host.current_image_pil), np.asarray(disk_orig))
    MangaOCRApp._on_compare_mode_toggled(host, False)
    assert np.array_equal(np.asarray(host.current_image_pil), np.asarray(cleaned))

    # Restore area pixels under a typeset area covering the painted box
    restore_rect = QRect(30, 40, 70, 70)
    area = TypesetArea(restore_rect, "Hi", QFont("Arial", 10), QColor("#000000"))
    area.set_cleanup_polygon(QPolygon([restore_rect.topLeft(), restore_rect.topRight(), restore_rect.bottomRight(), restore_rect.bottomLeft()]))
    host.typeset_areas = [area]
    assert host._restore_area_inpaint_pixels(area, commit_record=True) is True
    assert np.array_equal(np.asarray(host.current_image_pil), np.asarray(disk_orig))
    # All cleaned pixels restored -> cleaned state auto-removed!
    assert not record_has_cleaned_image(host.all_typeset_data[str(img_path)])

    # Re-apply inpaint then cancel_inpaint_result + undo/redo snapshot round-trip
    host._on_inpaint_brush_finished(cleaned)
    assert record_has_cleaned_image(host.all_typeset_data[str(img_path)])
    host.cancel_inpaint_result()
    assert not record_has_cleaned_image(host.all_typeset_data[str(img_path)])
    assert np.array_equal(np.asarray(host.current_image_pil), np.asarray(disk_orig))

    # Undo back to cleaned state via _restore_snapshot
    MangaOCRApp._restore_snapshot(host, host._undo_history_idx)
    assert record_has_cleaned_image(host.all_typeset_data[str(img_path)])
    assert np.array_equal(np.asarray(host.current_image_pil), np.asarray(cleaned))
