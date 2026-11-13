# Manga OCR & Typeset Tool v14.9.9.2
"""Compact `.manga_proj` ZIP + sparse lossless WebP patch storage and helpers."""

from __future__ import annotations

import base64
import copy
import hashlib
import io
import json
import os
import time
import zipfile
from typing import Any

import numpy as np
from PIL import Image, ImageFile

try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover - optional in environments without PyMuPDF
    fitz = None

from src.core.app_info import APP_VERSION

PROJECT_SCHEMA_VERSION = 5

CLEANED_STATE_KEYS = ("cleaned_patch", "cleaned_image_webp", "cleaned_image_png")
PRE_INPAINT_STATE_KEYS = ("pre_inpaint_webp", "pre_inpaint_image_png")
IMAGE_STATE_KEYS = CLEANED_STATE_KEYS + PRE_INPAINT_STATE_KEYS

DEFAULT_PATCH_AREA_THRESHOLD = 0.85
PDF_PAGE_SEPARATOR = "::page::"


def safe_open_pil(file_path: str) -> Image.Image:
    """Open an image file as RGB, tolerating truncated/malformed streams."""
    if not file_path or not os.path.isfile(file_path):
        raise FileNotFoundError(f"Image file not found: {file_path}")
    try:
        with Image.open(file_path) as img:
            img.load()
            return img.convert("RGB")
    except Exception:
        with open(file_path, "rb") as handle:
            raw = handle.read()
        prev_flag = ImageFile.LOAD_TRUNCATED_IMAGES
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        try:
            with Image.open(io.BytesIO(raw)) as img:
                img.load()
                return img.convert("RGB")
        except Exception:
            parser = ImageFile.Parser()
            parser.feed(raw)
            img = parser.close()
            return img.convert("RGB")
        finally:
            ImageFile.LOAD_TRUNCATED_IMAGES = prev_flag


def parse_pdf_data_key(key: str | None) -> tuple[str | None, int | None]:
    """Split a `<pdf_path>::page::<index>` key into `(pdf_path, page_index)`."""
    if not isinstance(key, str) or PDF_PAGE_SEPARATOR not in key:
        return None, None
    pdf_path, _, page_str = key.rpartition(PDF_PAGE_SEPARATOR)
    try:
        return pdf_path, int(page_str)
    except (TypeError, ValueError):
        return None, None


def _open_pdf_page_image(
    pdf_path: str,
    page_idx: int,
    pdf_document: Any = None,
    dpi: int = 150,
) -> Image.Image | None:
    if page_idx < 0:
        return None
    doc = pdf_document
    owned = False
    try:
        if doc is None or getattr(doc, "name", None) and os.path.abspath(doc.name) != os.path.abspath(pdf_path):
            if fitz is None or not os.path.isfile(pdf_path):
                return None
            doc = fitz.open(pdf_path)
            owned = True
        if page_idx >= len(doc):
            return None
        page = doc.load_page(page_idx)
        pix = page.get_pixmap(dpi=dpi, alpha=False)
        mode = "RGB" if pix.n == 3 else "RGBA"
        return Image.frombytes(mode, (pix.width, pix.height), pix.samples).convert("RGB")
    except Exception:
        return None
    finally:
        if owned and doc is not None:
            try:
                doc.close()
            except Exception:
                pass


def open_source_image_for_key(key: str | None, pdf_document: Any = None, dpi: int = 150) -> Image.Image | None:
    """Resolve and load the unmodified source image for an image or PDF page key."""
    if not key:
        return None
    pdf_path, page_idx = parse_pdf_data_key(key)
    if pdf_path is not None and page_idx is not None:
        return _open_pdf_page_image(pdf_path, page_idx, pdf_document=pdf_document, dpi=dpi)
    if not os.path.isfile(key):
        return None
    try:
        return safe_open_pil(key)
    except Exception:
        return None


def can_resolve_source_for_key(key: str | None, pdf_document: Any = None, _pdf_count_cache: dict | None = None) -> bool:
    """Return True if the original image or PDF page referenced by `key` exists on disk."""
    if not key or not isinstance(key, str):
        return False
    pdf_path, page_idx = parse_pdf_data_key(key)
    if pdf_path is not None and page_idx is not None:
        if page_idx < 0:
            return False
        if pdf_document is not None:
            doc_name = getattr(pdf_document, "name", None)
            if not doc_name or os.path.abspath(doc_name) == os.path.abspath(pdf_path):
                try:
                    return page_idx < len(pdf_document)
                except Exception:
                    pass
        if not os.path.isfile(pdf_path) or fitz is None:
            return False
        norm_pdf = os.path.abspath(pdf_path)
        if _pdf_count_cache is not None and norm_pdf in _pdf_count_cache:
            return page_idx < _pdf_count_cache[norm_pdf]
        try:
            with fitz.open(norm_pdf) as doc:
                count = len(doc)
            if _pdf_count_cache is not None:
                _pdf_count_cache[norm_pdf] = count
            return page_idx < count
        except Exception:
            return False
    return os.path.isfile(key)


def record_has_cleaned_image(record: Any) -> bool:
    return isinstance(record, dict) and any(bool(record.get(k)) for k in CLEANED_STATE_KEYS)


def record_has_pre_inpaint_image(record: Any) -> bool:
    return isinstance(record, dict) and any(bool(record.get(k)) for k in PRE_INPAINT_STATE_KEYS)


def copy_image_state_fields(src_record: Any, dst_record: dict | None = None) -> dict:
    """Shallow-copy image state keys without copying immutable binary `bytes` payloads."""
    out = dst_record if isinstance(dst_record, dict) else {}
    if not isinstance(src_record, dict):
        return out
    for key in IMAGE_STATE_KEYS:
        val = src_record.get(key)
        if not val:
            continue
        out[key] = dict(val) if isinstance(val, dict) else val
    return out


def strip_cleaned_state(record: dict) -> None:
    if isinstance(record, dict):
        for key in CLEANED_STATE_KEYS:
            record.pop(key, None)


def strip_pre_inpaint_state(record: dict) -> None:
    if isinstance(record, dict):
        for key in PRE_INPAINT_STATE_KEYS:
            record.pop(key, None)


def _encode_webp_bytes(pil_img: Image.Image) -> bytes:
    buf = io.BytesIO()
    pil_img.save(buf, format="WEBP", lossless=True, method=4)
    return buf.getvalue()


def _decode_image_blob(blob: Any, mode: str | None = None) -> Image.Image | None:
    if not blob:
        return None
    raw = None
    if isinstance(blob, dict):
        raw = blob.get("bytes")
    elif isinstance(blob, (bytes, bytearray, memoryview)):
        raw = bytes(blob)
    elif isinstance(blob, str):
        try:
            raw = base64.b64decode(blob)
        except Exception:
            return None
    if not raw:
        return None
    try:
        with Image.open(io.BytesIO(raw)) as img:
            img.load()
            return img.convert(mode) if mode else img.copy()
    except Exception:
        return None


def encode_cleaned_state(
    cleaned_pil: Image.Image | None,
    orig_pil: Image.Image | None = None,
    *,
    patch_area_threshold: float = DEFAULT_PATCH_AREA_THRESHOLD,
) -> dict[str, Any]:
    """Encode a cleaned page as a sparse lossless RGBA WebP patch or full lossless WebP."""
    if cleaned_pil is None:
        return {}
    cleaned_rgb = cleaned_pil.convert("RGB")
    if orig_pil is not None:
        orig_rgb = orig_pil.convert("RGB")
        if orig_rgb.size == cleaned_rgb.size:
            a_clean = np.asarray(cleaned_rgb, dtype=np.uint8)
            a_orig = np.asarray(orig_rgb, dtype=np.uint8)
            diff_mask = np.any(a_clean != a_orig, axis=2)
            if not np.any(diff_mask):
                return {}
            ys = np.where(np.any(diff_mask, axis=1))[0]
            xs = np.where(np.any(diff_mask, axis=0))[0]
            y1, y2 = int(ys[0]), int(ys[-1]) + 1
            x1, x2 = int(xs[0]), int(xs[-1]) + 1
            pw, ph = x2 - x1, y2 - y1
            total_area = cleaned_rgb.width * cleaned_rgb.height
            if total_area > 0 and (pw * ph) <= total_area * patch_area_threshold:
                rgba = np.empty((ph, pw, 4), dtype=np.uint8)
                crop_mask = diff_mask[y1:y2, x1:x2]
                rgba[..., :3] = np.where(crop_mask[..., None], a_clean[y1:y2, x1:x2], 0)
                rgba[..., 3] = np.where(crop_mask, 255, 0)
                patch_pil = Image.fromarray(rgba, "RGBA")
                return {
                    "cleaned_patch": {
                        "x": x1,
                        "y": y1,
                        "w": pw,
                        "h": ph,
                        "format": "webp",
                        "bytes": _encode_webp_bytes(patch_pil),
                    }
                }
    return {
        "cleaned_image_webp": {
            "format": "webp",
            "bytes": _encode_webp_bytes(cleaned_rgb),
        }
    }


def encode_pre_inpaint_state(pre_pil: Image.Image | None) -> dict[str, Any]:
    """Encode an explicit pre-inpaint base image as lossless WebP bytes."""
    if pre_pil is None:
        return {}
    return {
        "pre_inpaint_webp": {
            "format": "webp",
            "bytes": _encode_webp_bytes(pre_pil.convert("RGB")),
        }
    }


def decode_pre_inpaint_image(record: Any) -> Image.Image | None:
    """Decode explicit `pre_inpaint_webp` or legacy `pre_inpaint_image_png` from a record."""
    if not isinstance(record, dict):
        return None
    for key in PRE_INPAINT_STATE_KEYS:
        img = _decode_image_blob(record.get(key), mode="RGB")
        if img is not None:
            return img
    return None


def decode_cleaned_image(
    record: Any,
    orig_pil: Image.Image | None = None,
    orig_key: str | None = None,
    pdf_document: Any = None,
    orig_path: str | None = None,
) -> Image.Image | None:
    """Reconstruct a cleaned RGB image from `cleaned_patch`, `cleaned_image_webp`, or `cleaned_image_png`."""
    if not isinstance(record, dict):
        return None

    patch = record.get("cleaned_patch")
    if isinstance(patch, dict):
        patch_img = _decode_image_blob(patch, mode="RGBA")
        if patch_img is not None:
            base = orig_pil.convert("RGB") if orig_pil is not None else None
            if base is None:
                lookup_key = orig_key or orig_path
                if lookup_key:
                    base = open_source_image_for_key(lookup_key, pdf_document=pdf_document)
            if base is None:
                base = decode_pre_inpaint_image(record)
            if base is not None:
                x = int(patch.get("x", 0))
                y = int(patch.get("y", 0))
                pw, ph = patch_img.size
                bx0 = max(0, x)
                by0 = max(0, y)
                bx1 = min(base.width, x + pw)
                by1 = min(base.height, y + ph)
                if bx1 > bx0 and by1 > by0:
                    sx0 = bx0 - x
                    sy0 = by0 - y
                    sx1 = sx0 + (bx1 - bx0)
                    sy1 = sy0 + (by1 - by0)
                    base_arr = np.array(base, dtype=np.uint8, copy=True)
                    patch_arr = np.asarray(patch_img, dtype=np.uint8)[sy0:sy1, sx0:sx1]
                    alpha = patch_arr[..., 3]
                    opaque = alpha == 255
                    if np.any(opaque):
                        base_arr[by0:by1, bx0:bx1][opaque] = patch_arr[opaque, :3]
                    semi = (alpha > 0) & ~opaque
                    if np.any(semi):
                        dst_region = base_arr[by0:by1, bx0:bx1]
                        a = (alpha[semi].astype(np.float32) / 255.0)[..., None]
                        dst_region[semi] = np.clip(
                            patch_arr[semi, :3].astype(np.float32) * a
                            + dst_region[semi].astype(np.float32) * (1.0 - a),
                            0,
                            255,
                        ).astype(np.uint8)
                    return Image.fromarray(base_arr, "RGB")
                return base

    for key in ("cleaned_image_webp", "cleaned_image_png"):
        img = _decode_image_blob(record.get(key), mode="RGB")
        if img is not None:
            return img
    return None


def serialize_typeset_records(all_typeset_data: Any, *, drop_empty: bool = True) -> dict[str, dict]:
    """Serialize in-memory `all_typeset_data` entries into JSON/archive-ready records."""
    if not isinstance(all_typeset_data, dict):
        return {}
    serialized: dict[str, dict] = {}
    for key, payload in all_typeset_data.items():
        if not isinstance(payload, dict):
            continue
        raw_areas = payload.get("areas") or []
        raw_redo = payload.get("redo") or []
        areas = [a.to_payload() if hasattr(a, "to_payload") else copy.deepcopy(a) for a in raw_areas]
        redo = [a.to_payload() if hasattr(a, "to_payload") else copy.deepcopy(a) for a in raw_redo]
        record: dict[str, Any] = {"areas": areas, "redo": redo}
        copy_image_state_fields(payload, record)
        if drop_empty and not areas and not redo and not record_has_cleaned_image(record) and not record_has_pre_inpaint_image(record):
            continue
        serialized[key] = record
    return serialized


def _relativize_path(path: Any, base_dir: str | None) -> str | None:
    if not path or not isinstance(path, str) or not base_dir:
        return None
    pdf_path, page_idx = parse_pdf_data_key(path)
    if pdf_path is not None and page_idx is not None:
        try:
            rel_pdf = os.path.relpath(pdf_path, base_dir)
            return f"{rel_pdf}{PDF_PAGE_SEPARATOR}{page_idx}"
        except ValueError:
            return None
    try:
        return os.path.relpath(path, base_dir)
    except ValueError:
        return None


def _to_typeset_storage_key(abs_key: str, abs_project_dir: str | None, proj_file_dir: str | None) -> str:
    base = abs_project_dir or proj_file_dir
    if base:
        rel = _relativize_path(abs_key, base)
        if rel and not rel.startswith("..") and not os.path.isabs(rel):
            return rel
    rel_proj = _relativize_path(abs_key, proj_file_dir)
    return rel_proj if rel_proj else abs_key


def _resolve_abs_key(key: str, project_dir: str | None, proj_file_dir: str | None) -> str:
    if not key or not isinstance(key, str):
        return key
    pdf_path, page_idx = parse_pdf_data_key(key)
    base = project_dir or proj_file_dir or ""
    if pdf_path is not None and page_idx is not None:
        abs_pdf = pdf_path if os.path.isabs(pdf_path) or not base else os.path.normpath(os.path.join(base, pdf_path))
        return f"{abs_pdf}{PDF_PAGE_SEPARATOR}{page_idx}"
    if os.path.isabs(key) or not base:
        return key
    return os.path.normpath(os.path.join(base, key))


def _externalize_asset(meta: Any, assets_written: dict[str, bytes]) -> Any:
    if isinstance(meta, str):
        try:
            raw = base64.b64decode(meta)
        except Exception:
            return meta
        digest = hashlib.sha1(raw).hexdigest()[:16]
        asset_rel = f"assets/{digest}.png"
        assets_written.setdefault(asset_rel, raw)
        return {"format": "png", "asset": asset_rel}
    if isinstance(meta, dict):
        raw = meta.get("bytes")
        if raw:
            ext = str(meta.get("format") or "webp").lower()
            digest = hashlib.sha1(raw).hexdigest()[:16]
            asset_rel = f"assets/{digest}.{ext}"
            assets_written.setdefault(asset_rel, bytes(raw))
            cleaned_meta = {k: v for k, v in meta.items() if k != "bytes"}
            cleaned_meta["asset"] = asset_rel
            return cleaned_meta
        return dict(meta)
    return meta


def write_project_archive(
    target_path: str,
    snapshot: dict[str, Any],
    *,
    convert_legacy: bool = True,
    pdf_document: Any = None,
) -> None:
    """Write `.manga_proj` atomically as a ZIP archive (`project.json` + `assets/*`)."""
    proj_file_dir = os.path.dirname(os.path.abspath(target_path))
    raw_project_dir = snapshot.get("project_dir")
    abs_project_dir = os.path.abspath(raw_project_dir) if raw_project_dir else None
    current_image_path = snapshot.get("current_image_path")

    assets_written: dict[str, bytes] = {}
    pdf_count_cache: dict[str, int] = {}
    compact_typeset: dict[str, dict[str, Any]] = {}
    compact_image_order: list[str] = []

    raw_typeset = serialize_typeset_records(snapshot.get("typeset_data") or {}, drop_empty=True)
    for orig_key, rec in raw_typeset.items():
        abs_key = _resolve_abs_key(orig_key, abs_project_dir, proj_file_dir)
        source_exists = can_resolve_source_for_key(abs_key, pdf_document=pdf_document, _pdf_count_cache=pdf_count_cache)

        out_rec: dict[str, Any] = {
            "areas": rec.get("areas") or [],
            "redo": rec.get("redo") or [],
        }

        has_modern_cleaned = bool(rec.get("cleaned_patch") or rec.get("cleaned_image_webp"))
        legacy_cleaned_png = rec.get("cleaned_image_png")

        if has_modern_cleaned:
            if rec.get("cleaned_patch"):
                out_rec["cleaned_patch"] = _externalize_asset(rec["cleaned_patch"], assets_written)
            elif rec.get("cleaned_image_webp"):
                out_rec["cleaned_image_webp"] = _externalize_asset(rec["cleaned_image_webp"], assets_written)
        elif legacy_cleaned_png:
            if convert_legacy:
                cleaned_pil = _decode_image_blob(legacy_cleaned_png, mode="RGB")
                if cleaned_pil is not None:
                    orig_pil = open_source_image_for_key(abs_key, pdf_document=pdf_document) if source_exists else None
                    new_state = encode_cleaned_state(cleaned_pil, orig_pil=orig_pil)
                    for state_k, state_v in new_state.items():
                        out_rec[state_k] = _externalize_asset(state_v, assets_written)
            else:
                out_rec["cleaned_image_png"] = _externalize_asset(legacy_cleaned_png, assets_written)

        # Keep pre-inpaint base only if source file is unavailable OR caller kept custom WebP (e.g. baked Curves)
        if not source_exists:
            if rec.get("pre_inpaint_webp"):
                out_rec["pre_inpaint_webp"] = _externalize_asset(rec["pre_inpaint_webp"], assets_written)
            elif rec.get("pre_inpaint_image_png"):
                if convert_legacy:
                    pre_pil = _decode_image_blob(rec["pre_inpaint_image_png"], mode="RGB")
                    if pre_pil is not None:
                        pre_state = encode_pre_inpaint_state(pre_pil)
                        out_rec["pre_inpaint_webp"] = _externalize_asset(pre_state["pre_inpaint_webp"], assets_written)
                else:
                    out_rec["pre_inpaint_image_png"] = _externalize_asset(rec["pre_inpaint_image_png"], assets_written)
        elif rec.get("pre_inpaint_webp"):
            out_rec["pre_inpaint_webp"] = _externalize_asset(rec["pre_inpaint_webp"], assets_written)

        if not out_rec["areas"] and not out_rec["redo"] and not record_has_cleaned_image(out_rec) and not record_has_pre_inpaint_image(out_rec):
            continue
        storage_key = _to_typeset_storage_key(abs_key, abs_project_dir, proj_file_dir)
        compact_typeset[storage_key] = out_rec
        compact_image_order.append(storage_key)

    payload: dict[str, Any] = {
        "schema_version": PROJECT_SCHEMA_VERSION,
        "project_dir_rel": _relativize_path(abs_project_dir, proj_file_dir),
        "current_image_path_rel": _relativize_path(current_image_path, proj_file_dir),
        "project_dir": abs_project_dir,
        "current_image_path": current_image_path,
        "current_pdf_page": int(snapshot.get("current_pdf_page", -1)),
        "image_order": compact_image_order,
        "typeset_data": compact_typeset,
        "history_entries": snapshot.get("history_entries") or [],
        "proofreader_entries": snapshot.get("proofreader_entries") or [],
        "quality_entries": snapshot.get("quality_entries") or [],
        "history_counter": int(snapshot.get("history_counter", 0)),
        "typeset_font": snapshot.get("typeset_font"),
        "typeset_color": snapshot.get("typeset_color"),
        "settings": snapshot.get("settings") or {},
        "saved_at": float(snapshot.get("saved_at") or time.time()),
        "app_version": snapshot.get("app_version") or APP_VERSION,
    }

    tmp_path = target_path + ".tmp"
    try:
        with zipfile.ZipFile(tmp_path, "w") as zf:
            zf.writestr(
                "project.json",
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
                compress_type=zipfile.ZIP_DEFLATED,
            )
            for asset_rel in sorted(assets_written.keys()):
                zf.writestr(asset_rel, assets_written[asset_rel], compress_type=zipfile.ZIP_STORED)
        os.replace(tmp_path, target_path)
    except Exception:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        raise


def read_project_archive(file_path: str) -> tuple[dict[str, Any], str]:
    """Read either a v5 ZIP `.manga_proj` archive or a legacy v1-v4 JSON `.manga_proj`."""
    if zipfile.is_zipfile(file_path):
        with zipfile.ZipFile(file_path, "r") as zf:
            data = json.loads(zf.read("project.json").decode("utf-8"))
            typeset_data = data.get("typeset_data")
            if isinstance(typeset_data, dict):
                for rec in typeset_data.values():
                    if not isinstance(rec, dict):
                        continue
                    for key in IMAGE_STATE_KEYS:
                        val = rec.get(key)
                        if isinstance(val, dict) and val.get("asset"):
                            try:
                                val["bytes"] = zf.read(val["asset"])
                            except KeyError:
                                pass
            return data, "zip"

    with open(file_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data, "json"
