"""Integrated in-process manga inpainting engine registry, downloader, and runner."""

from __future__ import annotations

import gc
import hashlib
import os
import threading
import urllib.request
from dataclasses import dataclass
from typing import Callable, Iterable, Optional

import cv2
import numpy as np
from PIL import Image


_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUILTIN_INPAINT_MODELS_DIR = os.path.join(_PROJECT_ROOT, "src", "models", "inpainting")
LEGACY_IOPAINT_CHECKPOINTS_DIR = os.path.join(
    _PROJECT_ROOT, "Inpainting", "models", "torch", "hub", "checkpoints"
)
TORCH_HUB_CHECKPOINTS_DIR = os.path.join(os.path.expanduser("~"), ".cache", "torch", "hub", "checkpoints")

DEFAULT_INPAINT_ENGINE = "big_lama"
DEFAULT_FULL_INPAINT_ENGINE = DEFAULT_INPAINT_ENGINE
DEFAULT_BRUSH_INPAINT_ENGINE = DEFAULT_INPAINT_ENGINE
DEFAULT_SD_INPAINT_MODEL = "Sanster/anything-4.0-inpainting"
DEFAULT_SD_INPAINT_STEPS = 20

SD_INPAINT_PRESETS: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class ModelFileSpec:
    filename: str
    url: str
    md5: str
    min_bytes: int = 1024


@dataclass(frozen=True)
class InpaintEngineSpec:
    id: str
    label: str
    short_label: str
    badge: str
    description: str
    size_hint: str
    needs_download: bool = True
    gpu_recommended: bool = False
    supports_full: bool = True
    supports_brush: bool = True
    files: tuple[ModelFileSpec, ...] = ()
    is_sd: bool = False
    is_external: bool = False


INPAINT_ENGINE_SPECS: dict[str, InpaintEngineSpec] = {
    "big_lama": InpaintEngineSpec(
        id="big_lama",
        label="Built-in Big-LaMa",
        short_label="Big-LaMa (Built-in)",
        badge="Default · Cepat",
        description=(
            "Model AI bawaan serbaguna dan cepat untuk manga hitam-putih maupun berwarna. "
            "Berjalan mulus di CPU maupun GPU."
        ),
        size_hint="~196 MB",
        needs_download=True,
        gpu_recommended=False,
        files=(
            ModelFileSpec(
                filename="big-lama.pt",
                url="https://github.com/Sanster/models/releases/download/add_big_lama/big-lama.pt",
                md5="e3aa4aaa15225a33ec84f9f4bc47e500",
                min_bytes=50_000_000,
            ),
        ),
    ),
    "manga_inpaintor": InpaintEngineSpec(
        id="manga_inpaintor",
        label="Built-in Manga Inpaintor",
        short_label="Manga Inpaintor",
        badge="Khusus Manga B/W",
        description=(
            "Dirancang khusus untuk manga hitam-putih; mengekstrak dan menyambung "
            "garis/screentone yang tertimpa teks (output grayscale)."
        ),
        size_hint="~245 MB",
        needs_download=True,
        gpu_recommended=False,
        files=(
            ModelFileSpec(
                filename="manga_inpaintor.jit",
                url="https://github.com/Sanster/models/releases/download/manga/manga_inpaintor.jit",
                md5="7d8b269c4613b6b3768af714610da86c",
                min_bytes=10_000_000,
            ),
            ModelFileSpec(
                filename="erika.jit",
                url="https://github.com/Sanster/models/releases/download/manga/erika.jit",
                md5="0c926d5a4af8450b0d00bc5b9a095644",
                min_bytes=5_000_000,
            ),
        ),
    ),
    "migan": InpaintEngineSpec(
        id="migan",
        label="Built-in MI-GAN",
        short_label="MI-GAN (Ringan)",
        badge="Ringan & Halus",
        description=(
            "Model inpainting sangat ringan (~27 MB) dengan transisi warna dan tekstur halus "
            "untuk manga berwarna maupun grayscale."
        ),
        size_hint="~27 MB",
        needs_download=True,
        gpu_recommended=False,
        files=(
            ModelFileSpec(
                filename="migan_traced.pt",
                url="https://github.com/Sanster/models/releases/download/migan/migan_traced.pt",
                md5="76eb3b1a71c400ee3290524f7a11b89c",
                min_bytes=5_000_000,
            ),
        ),
    ),
    "opencv_ns": InpaintEngineSpec(
        id="opencv_ns",
        label="OpenCV Navier-Stokes (Offline)",
        short_label="OpenCV-NS (Offline)",
        badge="Tanpa AI · Instan",
        description="Inpainting klasik super cepat tanpa model AI tambahan; ideal untuk balon teks polos.",
        size_hint="0 MB",
        needs_download=False,
    ),
    "opencv_telea": InpaintEngineSpec(
        id="opencv_telea",
        label="OpenCV Telea (Offline)",
        short_label="OpenCV-Telea (Offline)",
        badge="Tanpa AI · Instan",
        description="Algoritma OpenCV Telea instan tanpa model AI; ideal untuk area sederhana.",
        size_hint="0 MB",
        needs_download=False,
    ),
    "iopaint_server": InpaintEngineSpec(
        id="iopaint_server",
        label="External IOPaint Server (Opsional)",
        short_label="IOPaint Server (Eksternal)",
        badge="Server Lokal",
        description=(
            "Mengirim job ke server HTTP IOPaint terpisah (port 8080) bagi pengguna mahir "
            "yang ingin menjalankan backend eksternal."
        ),
        size_hint="Eksternal",
        needs_download=False,
        is_external=True,
    ),
}

_ENGINE_ORDER = (
    "big_lama",
    "manga_inpaintor",
    "migan",
    "opencv_ns",
    "opencv_telea",
    "iopaint_server",
)

_LEGACY_LABEL_ALIASES: dict[str, str] = {
    "big_lama": "big_lama",
    "big-lama": "big_lama",
    "biglama": "big_lama",
    "lama": "big_lama",
    "built-in big-lama": "big_lama",
    "big-lama (built-in)": "big_lama",
    "manga_inpaintor": "manga_inpaintor",
    "manga-inpaintor": "manga_inpaintor",
    "manga": "manga_inpaintor",
    "manga inpaintor": "manga_inpaintor",
    "built-in manga inpaintor": "manga_inpaintor",
    "migan": "migan",
    "mi-gan": "migan",
    "mi_gan": "migan",
    "migan (ringan)": "migan",
    "built-in mi-gan": "migan",
    # Stable Diffusion Inpaint disabled — gracefully migrate saved configs to Big-LaMa
    "sd_inpaint": "big_lama",
    "sd-inpaint": "big_lama",
    "sd": "big_lama",
    "stable diffusion": "big_lama",
    "stable diffusion inpaint": "big_lama",
    "built-in stable diffusion inpaint": "big_lama",
    "opencv_ns": "opencv_ns",
    "opencv-ns": "opencv_ns",
    "opencv-ns (offline)": "opencv_ns",
    "opencv navier-stokes": "opencv_ns",
    "opencv navier-stokes (offline)": "opencv_ns",
    "opencv_telea": "opencv_telea",
    "opencv-telea": "opencv_telea",
    "opencv-telea (offline)": "opencv_telea",
    "opencv telea": "opencv_telea",
    "opencv telea (offline)": "opencv_telea",
    "iopaint_server": "iopaint_server",
    "iopaint": "iopaint_server",
    "iopaint server": "iopaint_server",
    "iopaint server (eksternal)": "iopaint_server",
    "external iopaint server (opsional)": "iopaint_server",
}


def get_inpaint_spec(engine_id: str | None) -> InpaintEngineSpec:
    norm = normalize_inpaint_engine_id(engine_id)
    return INPAINT_ENGINE_SPECS[norm]


def list_inpaint_engines(context: str = "full") -> list[InpaintEngineSpec]:
    specs: list[InpaintEngineSpec] = []
    for eid in _ENGINE_ORDER:
        spec = INPAINT_ENGINE_SPECS[eid]
        if context == "full" and not spec.supports_full:
            continue
        if context == "brush" and not spec.supports_brush:
            continue
        specs.append(spec)
    return specs


def normalize_inpaint_engine_id(
    value: object,
    legacy_model_name: object = None,
    default: str = DEFAULT_FULL_INPAINT_ENGINE,
) -> str:
    """Resolve user/legacy config value to canonical engine id."""
    for candidate in (value, legacy_model_name):
        if candidate is None:
            continue
        text = str(candidate).strip().lower()
        if not text:
            continue
        if text in _LEGACY_LABEL_ALIASES:
            return _LEGACY_LABEL_ALIASES[text]
        for alias, target in _LEGACY_LABEL_ALIASES.items():
            if len(alias) >= 4 and alias in text:
                return target
    return default if default in INPAINT_ENGINE_SPECS else DEFAULT_FULL_INPAINT_ENGINE


def engine_display_label(engine_id: str | None, short: bool = False) -> str:
    spec = get_inpaint_spec(engine_id)
    return spec.short_label if short else spec.label


def resolve_inpaint_engine_id(cleanup_cfg: dict | None) -> str:
    """Resolve the single unified inpaint engine id (shared by Full & Brush)."""
    cfg = cleanup_cfg if isinstance(cleanup_cfg, dict) else {}
    legacy_name = str(cfg.get("inpaint_model_name", "") or "").strip()

    # Existing installs saved inpaint_model_name="IOPaint Server" before built-in
    # integration existed. Unless an explicit unified/legacy engine key is set,
    # preserve explicit OpenCV choices but migrate the old IOPaint default cleanly
    # to built-in Big-LaMa.
    legacy_fallback = DEFAULT_INPAINT_ENGINE
    if legacy_name.lower().startswith("opencv"):
        legacy_fallback = normalize_inpaint_engine_id(legacy_name, default=DEFAULT_INPAINT_ENGINE)

    unified_raw = cfg.get("inpaint_engine")
    if unified_raw:
        return normalize_inpaint_engine_id(unified_raw, default=legacy_fallback)

    full_raw = cfg.get("full_inpaint_engine")
    if full_raw:
        return normalize_inpaint_engine_id(full_raw, default=legacy_fallback)

    brush_raw = cfg.get("brush_inpaint_engine")
    if brush_raw:
        return normalize_inpaint_engine_id(brush_raw, default=legacy_fallback)

    return legacy_fallback


def resolve_cleanup_engine_ids(cleanup_cfg: dict | None) -> tuple[str, str]:
    """Return unified `(engine_id, engine_id)` tuple for Full & Brush."""
    unified = resolve_inpaint_engine_id(cleanup_cfg)
    return unified, unified


def _configure_cpu_torch_threads() -> None:
    """Tune intra-op PyTorch CPU threads while leaving headroom for GUI responsiveness."""
    try:
        import torch

        cpu_cnt = os.cpu_count() or 4
        target_threads = min(6, max(2, cpu_cnt - 2)) if cpu_cnt > 4 else max(1, cpu_cnt - 1)
        if torch.get_num_threads() != target_threads:
            torch.set_num_threads(target_threads)
    except Exception:
        pass


def _candidate_model_dirs(extra_dirs: Iterable[str] | None = None) -> list[str]:
    dirs = [
        BUILTIN_INPAINT_MODELS_DIR,
        LEGACY_IOPAINT_CHECKPOINTS_DIR,
        TORCH_HUB_CHECKPOINTS_DIR,
    ]
    if extra_dirs:
        dirs.extend(d for d in extra_dirs if d)
    seen: list[str] = []
    for d in dirs:
        norm = os.path.normpath(d)
        if norm not in seen:
            seen.append(norm)
    return seen


def find_model_file(
    filename: str,
    min_bytes: int = 1024,
    extra_dirs: Iterable[str] | None = None,
) -> Optional[str]:
    """Search known local directories for an existing valid model file."""
    for folder in _candidate_model_dirs(extra_dirs):
        candidate = os.path.join(folder, filename)
        try:
            if os.path.isfile(candidate) and os.path.getsize(candidate) >= max(1, int(min_bytes)):
                return candidate
        except OSError:
            continue
    return None


def resolve_engine_model_paths(
    engine_id: str,
    extra_dirs: Iterable[str] | None = None,
) -> dict[str, str]:
    """Return mapping `{filename: path}` for all files found locally for `engine_id`."""
    spec = get_inpaint_spec(engine_id)
    found: dict[str, str] = {}
    for file_spec in spec.files:
        path = find_model_file(file_spec.filename, min_bytes=file_spec.min_bytes, extra_dirs=extra_dirs)
        if path:
            found[file_spec.filename] = path
    return found


def is_sd_model_cached(repo_id: str | None = None) -> bool:
    """Return True if a Diffusers SD repo/path appears available locally without network."""
    target = str(repo_id or DEFAULT_SD_INPAINT_MODEL).strip() or DEFAULT_SD_INPAINT_MODEL
    if os.path.isdir(target):
        return os.path.isfile(os.path.join(target, "model_index.json"))
    try:
        from huggingface_hub import snapshot_download
    except Exception:
        return False
    try:
        snapshot_download(repo_id=target, local_files_only=True)
        return True
    except Exception:
        return False


def is_engine_ready(
    engine_id: str,
    sd_repo_id: str | None = None,
    extra_dirs: Iterable[str] | None = None,
) -> bool:
    """Return True if all local files needed for `engine_id` are present."""
    spec = get_inpaint_spec(engine_id)
    if not spec.needs_download:
        return True
    if spec.is_sd:
        return is_sd_model_cached(sd_repo_id)
    paths = resolve_engine_model_paths(spec.id, extra_dirs=extra_dirs)
    return len(paths) == len(spec.files)


def format_inpaint_engine_option(
    engine_id_or_spec: str | InpaintEngineSpec | None,
    sd_repo_id: str | None = None,
    extra_dirs: Iterable[str] | None = None,
) -> tuple[str, str, bool]:
    """Return `(dropdown_label, status_badge, is_ready)` for UI selectors."""
    spec = (
        engine_id_or_spec
        if isinstance(engine_id_or_spec, InpaintEngineSpec)
        else get_inpaint_spec(engine_id_or_spec)
    )
    if spec.id == "iopaint_server":
        return (f"{spec.short_label} · Eksternal", "Server Eksternal", True)
    if not spec.needs_download:
        return (f"{spec.short_label} · Siap Offline", "Siap Offline", True)
    if is_engine_ready(spec.id, sd_repo_id=sd_repo_id, extra_dirs=extra_dirs):
        return (f"{spec.short_label} · Siap", "Siap", True)
    return (f"{spec.short_label} · Unduh {spec.size_hint}", f"Belum diunduh ({spec.size_hint})", False)


def get_missing_engine_ids(
    cleanup_cfg: dict | None,
    extra_dirs: Iterable[str] | None = None,
) -> list[str]:
    """Return missing local AI engine IDs for the active unified inpaint engine."""
    cfg = cleanup_cfg if isinstance(cleanup_cfg, dict) else {}
    engine_id = resolve_inpaint_engine_id(cfg)
    spec = get_inpaint_spec(engine_id)
    if spec.needs_download and not is_engine_ready(engine_id, extra_dirs=extra_dirs):
        return [engine_id]
    return []


def verify_file_md5(file_path: str, expected_md5: str) -> bool:
    digest = hashlib.md5()
    with open(file_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower() == str(expected_md5).strip().lower()


def download_file_verified(
    url: str,
    dest_path: str,
    expected_md5: str | None = None,
    progress_cb: Callable[[int, str], None] | None = None,
    check_cancel: Callable[[], bool] | None = None,
    label: str = "",
) -> str:
    """Atomically download `url` to `dest_path` with optional MD5 verification."""
    os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
    part_path = dest_path + ".part"
    if os.path.exists(part_path):
        try:
            os.remove(part_path)
        except OSError:
            pass

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MangaTranslate-InpaintDownloader/1.0"},
    )
    digest = hashlib.md5() if expected_md5 else None
    display = label or os.path.basename(dest_path)

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            total_header = resp.headers.get("Content-Length")
            total_bytes = int(total_header) if total_header and total_header.isdigit() else 0
            downloaded = 0
            with open(part_path, "wb") as out_f:
                while True:
                    if check_cancel and check_cancel():
                        raise RuntimeError("Download dibatalkan oleh pengguna.")
                    chunk = resp.read(256 * 1024)
                    if not chunk:
                        break
                    out_f.write(chunk)
                    if digest is not None:
                        digest.update(chunk)
                    downloaded += len(chunk)
                    if progress_cb and total_bytes > 0:
                        pct = min(99, int(downloaded * 100 / total_bytes))
                        mb_done = downloaded / (1024 * 1024)
                        mb_tot = total_bytes / (1024 * 1024)
                        progress_cb(pct, f"Mengunduh {display}: {mb_done:.1f}/{mb_tot:.1f} MB ({pct}%)")

        if expected_md5 and digest is not None:
            actual = digest.hexdigest().lower()
            if actual != str(expected_md5).strip().lower():
                raise RuntimeError(
                    f"Checksum MD5 tidak cocok untuk {display} ({actual} != {expected_md5})."
                )

        os.replace(part_path, dest_path)
        if progress_cb:
            progress_cb(100, f"{display} siap digunakan.")
        return dest_path
    except Exception:
        try:
            if os.path.exists(part_path):
                os.remove(part_path)
        except OSError:
            pass
        raise


def download_engine_models(
    engine_id: str,
    sd_repo_id: str | None = None,
    progress_cb: Callable[[int, str], None] | None = None,
    check_cancel: Callable[[], bool] | None = None,
    extra_dirs: Iterable[str] | None = None,
) -> dict[str, str]:
    """Ensure local weights for `engine_id` are present on disk, downloading missing ones."""
    spec = get_inpaint_spec(engine_id)
    if not spec.needs_download:
        if progress_cb:
            progress_cb(100, f"{spec.short_label} sudah siap tanpa unduhan.")
        return {}

    if spec.is_sd:
        target = str(sd_repo_id or DEFAULT_SD_INPAINT_MODEL).strip() or DEFAULT_SD_INPAINT_MODEL
        if is_sd_model_cached(target):
            if progress_cb:
                progress_cb(100, f"Model Stable Diffusion '{target}' sudah tersedia di cache.")
            return {"sd_repo_id": target}
        try:
            from huggingface_hub import snapshot_download
        except Exception as exc:
            raise RuntimeError(
                f"Paket huggingface_hub/diffusers belum siap untuk mengunduh '{target}': {exc}"
            ) from exc

        if check_cancel and check_cancel():
            raise RuntimeError("Download dibatalkan oleh pengguna.")
        if progress_cb:
            progress_cb(
                10,
                f"Mengunduh Stable Diffusion Inpaint ({target}, ~4.2 GB) ke cache HuggingFace...",
            )
        local_dir = snapshot_download(
            repo_id=target,
            ignore_patterns=["*.ckpt", "*.msgpack", "*.h5", "*.ot", "*flax*", "*tf*"],
        )
        if progress_cb:
            progress_cb(100, f"Model Stable Diffusion '{target}' siap digunakan.")
        return {"sd_repo_id": local_dir}

    target_dir = BUILTIN_INPAINT_MODELS_DIR
    os.makedirs(target_dir, exist_ok=True)
    existing = resolve_engine_model_paths(spec.id, extra_dirs=extra_dirs)
    total_files = max(1, len(spec.files))
    resolved: dict[str, str] = dict(existing)

    for idx, fspec in enumerate(spec.files):
        if fspec.filename in resolved:
            continue
        dest = os.path.join(target_dir, fspec.filename)

        def _file_cb(file_pct: int, msg: str, base_idx: int = idx) -> None:
            if progress_cb:
                overall = int(((base_idx + (file_pct / 100.0)) / total_files) * 100)
                progress_cb(min(100, overall), msg)

        resolved[fspec.filename] = download_file_verified(
            fspec.url,
            dest,
            expected_md5=fspec.md5,
            progress_cb=_file_cb,
            check_cancel=check_cancel,
            label=fspec.filename,
        )

    if progress_cb:
        progress_cb(100, f"{spec.short_label} siap digunakan.")
    return resolved


# ---------------------------------------------------------------------------
# Image preprocessing / ROI helpers matching IOPaint
# ---------------------------------------------------------------------------

def ceil_modulo(value: int, mod: int) -> int:
    if mod <= 1 or value % mod == 0:
        return value
    return (value // mod + 1) * mod


def pad_img_to_modulo(img: np.ndarray, mod: int, pad_to_square: bool = False) -> np.ndarray:
    """Symmetrically pad `(H, W)` or `(H, W, C)` image so dimensions divide cleanly by `mod`."""
    height, width = img.shape[:2]
    out_h = ceil_modulo(height, mod)
    out_w = ceil_modulo(width, mod)
    if pad_to_square:
        side = max(out_h, out_w)
        out_h = side
        out_w = side
    pad_h = max(0, out_h - height)
    pad_w = max(0, out_w - width)
    if pad_h == 0 and pad_w == 0:
        return img
    if img.ndim == 2:
        return np.pad(img, ((0, pad_h), (0, pad_w)), mode="symmetric")
    return np.pad(img, ((0, pad_h), (0, pad_w), (0, 0)), mode="symmetric")


def resize_max_size(img: np.ndarray, size_limit: int, interpolation: int = cv2.INTER_CUBIC) -> np.ndarray:
    h, w = img.shape[:2]
    if max(h, w) <= size_limit:
        return img
    scale = float(size_limit) / float(max(h, w))
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    return cv2.resize(img, (new_w, new_h), interpolation=interpolation)


def boxes_from_mask(mask: np.ndarray) -> list[list[int]]:
    """Compute `[x1, y1, x2, y2]` bounding boxes for connected mask components."""
    binary = ((mask > 0).astype(np.uint8)) * 255
    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(binary)
    boxes: list[list[int]] = []
    for i in range(1, num_labels):
        x, y, w, h, area = stats[i]
        if area > 0 and w > 0 and h > 0:
            boxes.append([int(x), int(y), int(x + w), int(y + h)])
    return boxes


def _expand_crop_box(
    img_w: int,
    img_h: int,
    box: list[int],
    margin: int = 80,
    min_size: int = 160,
) -> tuple[int, int, int, int]:
    cx1, cy1, cx2, cy2 = [int(v) for v in box]
    cx = (cx1 + cx2) // 2
    cy = (cy1 + cy2) // 2
    l = max(cx1 - margin, 0)
    t = max(cy1 - margin, 0)
    r = min(cx2 + margin, img_w)
    b = min(cy2 + margin, img_h)

    cur_h = b - t
    cur_w = r - l
    eff_min = max(0, int(min_size or 0))
    if eff_min > cur_h and img_h > 0:
        t = max(cy - eff_min // 2, 0)
        b = min(t + eff_min, img_h)
        if b - t < eff_min:
            t = max(img_h - eff_min, 0)
    if eff_min > cur_w and img_w > 0:
        l = max(cx - eff_min // 2, 0)
        r = min(l + eff_min, img_w)
        if r - l < eff_min:
            l = max(img_w - eff_min, 0)
    return int(l), int(t), int(r), int(b)


def _merge_boxes_into_rois(
    mask: np.ndarray,
    margin: int = 80,
    min_size: int = 160,
) -> list[tuple[int, int, int, int]]:
    h, w = mask.shape[:2]
    raw_boxes = boxes_from_mask(mask)
    if not raw_boxes:
        return []
    merged: list[list[int]] = [
        list(_expand_crop_box(w, h, b, margin=margin, min_size=min_size))
        for b in raw_boxes
    ]
    changed = True
    while changed and len(merged) > 1:
        changed = False
        next_merged: list[list[int]] = []
        for box in merged:
            placed = False
            for m in next_merged:
                if not (box[2] < m[0] or box[0] > m[2] or box[3] < m[1] or box[1] > m[3]):
                    m[0] = min(m[0], box[0])
                    m[1] = min(m[1], box[1])
                    m[2] = max(m[2], box[2])
                    m[3] = max(m[3], box[3])
                    placed = True
                    changed = True
                    break
            if not placed:
                next_merged.append(box)
        merged = next_merged
    return [(b[0], b[1], b[2], b[3]) for b in merged]


def _normalize_rgb_and_mask(
    pil_image: Image.Image,
    pil_mask: Image.Image,
) -> tuple[np.ndarray, np.ndarray]:
    rgb = np.array(pil_image.convert("RGB"), dtype=np.uint8)
    mask = np.array(pil_mask.convert("L"), dtype=np.uint8)
    if mask.shape[:2] != rgb.shape[:2]:
        mask = cv2.resize(mask, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_NEAREST)
    return rgb, mask


def run_opencv_inpaint(
    pil_image: Image.Image,
    pil_mask: Image.Image,
    method: str = "opencv_ns",
    radius: int = 5,
) -> Image.Image:
    """Fast built-in OpenCV inpaint (`opencv_ns` or `opencv_telea`)."""
    rgb, mask = _normalize_rgb_and_mask(pil_image, pil_mask)
    if int(np.count_nonzero(mask)) == 0:
        return Image.fromarray(rgb)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    flag = cv2.INPAINT_TELEA if normalize_inpaint_engine_id(method) == "opencv_telea" else cv2.INPAINT_NS
    out_bgr = cv2.inpaint(bgr, (mask > 0).astype(np.uint8) * 255, max(1, int(radius)), flag)
    return Image.fromarray(cv2.cvtColor(out_bgr, cv2.COLOR_BGR2RGB))


# ---------------------------------------------------------------------------
# Single-slot heavy model manager
# ---------------------------------------------------------------------------

class InpaintEngineManager:
    """Thread-safe single-slot manager for in-process AI inpainting models."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._loaded_key: Optional[tuple[str, str, str]] = None
        self._loaded_payload: object = None

    @property
    def loaded_engine_key(self) -> Optional[tuple[str, str, str]]:
        with self._lock:
            return self._loaded_key

    def resolve_device(self, requested: str = "auto") -> str:
        req = str(requested or "auto").strip().lower()
        try:
            import torch
        except Exception:
            return "cpu"
        if req == "cpu":
            return "cpu"
        if req == "cuda":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return "cuda" if torch.cuda.is_available() else "cpu"

    def unload_loaded_model(self) -> None:
        """Unload currently cached model weights and release CPU/CUDA memory."""
        with self._lock:
            self._loaded_payload = None
            self._loaded_key = None
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass

    def _ensure_loaded(
        self,
        engine_id: str,
        device: str,
        sd_repo_id: str,
        auto_download: bool,
        progress_cb: Callable[[int, str], None] | None,
        check_cancel: Callable[[], bool] | None,
    ) -> object:
        spec = get_inpaint_spec(engine_id)
        variant = sd_repo_id if spec.is_sd else ""
        target_key = (spec.id, variant, device)

        if self._loaded_key == target_key and self._loaded_payload is not None:
            return self._loaded_payload

        # Unload any other heavy model before allocating new weights.
        if self._loaded_key is not None and self._loaded_key != target_key:
            self.unload_loaded_model()

        import torch

        if check_cancel and check_cancel():
            raise RuntimeError("Inpainting dibatalkan oleh pengguna.")

        if spec.id == "big_lama":
            paths = resolve_engine_model_paths("big_lama")
            if "big-lama.pt" not in paths:
                if not auto_download:
                    raise FileNotFoundError("Model Big-LaMa (big-lama.pt) belum tersedia secara lokal.")
                paths = download_engine_models("big_lama", progress_cb=progress_cb, check_cancel=check_cancel)
            if progress_cb:
                progress_cb(4, f"Memuat {spec.short_label} ke {device.upper()}...")
            model = torch.jit.load(paths["big-lama.pt"], map_location=device)
            model.eval()
            payload = {"model": model}
        elif spec.id == "manga_inpaintor":
            paths = resolve_engine_model_paths("manga_inpaintor")
            if len(paths) < 2:
                if not auto_download:
                    raise FileNotFoundError("Model Manga Inpaintor belum tersedia secara lokal.")
                paths = download_engine_models(
                    "manga_inpaintor", progress_cb=progress_cb, check_cancel=check_cancel
                )
            if progress_cb:
                progress_cb(4, f"Memuat {spec.short_label} ke {device.upper()}...")
            inpaint_model = torch.jit.load(paths["manga_inpaintor.jit"], map_location=device)
            inpaint_model.eval()
            line_model = torch.jit.load(paths["erika.jit"], map_location=device)
            line_model.eval()
            payload = {"model": inpaint_model, "lines": line_model}
        elif spec.id == "migan":
            paths = resolve_engine_model_paths("migan")
            if "migan_traced.pt" not in paths:
                if not auto_download:
                    raise FileNotFoundError("Model MI-GAN (migan_traced.pt) belum tersedia secara lokal.")
                paths = download_engine_models("migan", progress_cb=progress_cb, check_cancel=check_cancel)
            if progress_cb:
                progress_cb(4, f"Memuat {spec.short_label} ke {device.upper()}...")
            model = torch.jit.load(paths["migan_traced.pt"], map_location=device)
            model.eval()
            payload = {"model": model}
        elif spec.id == "sd_inpaint":
            if not is_sd_model_cached(sd_repo_id) and not auto_download:
                raise FileNotFoundError(
                    f"Model Stable Diffusion Inpaint '{sd_repo_id}' belum diunduh. "
                    "Klik Unduh di panel atau buka Settings -> Cleanup & Inpaint."
                )
            if not is_sd_model_cached(sd_repo_id):
                download_engine_models(
                    "sd_inpaint",
                    sd_repo_id=sd_repo_id,
                    progress_cb=progress_cb,
                    check_cancel=check_cancel,
                )
            if check_cancel and check_cancel():
                raise RuntimeError("Inpainting dibatalkan oleh pengguna.")
            if progress_cb:
                progress_cb(3, f"Memuat Stable Diffusion ({sd_repo_id}) ke {device.upper()}...")
            try:
                from diffusers import StableDiffusionInpaintPipeline
            except Exception as exc:
                raise RuntimeError(
                    f"Library diffusers/accelerate tidak dapat dimuat ({exc})."
                ) from exc

            torch_dtype = torch.float16 if device == "cuda" else torch.float32
            pipe = StableDiffusionInpaintPipeline.from_pretrained(
                sd_repo_id,
                torch_dtype=torch_dtype,
                safety_checker=None,
                requires_safety_checker=False,
                local_files_only=True,
            )
            if check_cancel and check_cancel():
                raise RuntimeError("Inpainting dibatalkan oleh pengguna.")
            pipe = pipe.to(device)
            try:
                pipe.enable_attention_slicing()
            except Exception:
                pass
            try:
                pipe.enable_vae_slicing()
            except Exception:
                pass
            payload = {"pipe": pipe}
        else:
            raise ValueError(f"Unsupported AI model load request: {engine_id}")

        self._loaded_key = target_key
        self._loaded_payload = payload
        return payload

    def _run_big_lama(self, payload: dict, device: str, rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
        import torch

        h, w = rgb.shape[:2]
        padded_img = pad_img_to_modulo(rgb, 8)
        padded_msk = pad_img_to_modulo(mask, 8)

        img_f = (padded_img.astype(np.float32) / 255.0).transpose(2, 0, 1)
        msk_f = (padded_msk > 0).astype(np.float32)[None, None, :, :]

        img_t = torch.from_numpy(np.ascontiguousarray(img_f)).unsqueeze(0).to(device)
        msk_t = torch.from_numpy(np.ascontiguousarray(msk_f)).to(device)

        with torch.inference_mode():
            out_t = payload["model"](img_t, msk_t)
            if isinstance(out_t, (tuple, list)):
                out_t = out_t[0]
            out_np = out_t[0].permute(1, 2, 0).detach().cpu().numpy()

        out_rgb = np.clip(out_np[:h, :w, :] * 255.0, 0, 255).astype(np.uint8)
        return self._composite_unmasked(rgb, mask, out_rgb)

    def _run_manga_inpaintor(self, payload: dict, device: str, rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
        import torch

        h, w = rgb.shape[:2]
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        padded_gray = pad_img_to_modulo(gray, 16)
        padded_msk = pad_img_to_modulo(mask, 16)

        with torch.inference_mode():
            gray_t = (
                torch.from_numpy(np.ascontiguousarray(padded_gray))
                .unsqueeze(0)
                .unsqueeze(0)
                .float()
                .to(device)
            )
            lines_t = torch.clamp(payload["lines"](gray_t), 0.0, 255.0)

            gray_norm = gray_t / 127.5 - 1.0
            lines_norm = lines_t / 127.5 - 1.0
            mask_t = (
                (
                    torch.from_numpy(np.ascontiguousarray(padded_msk))
                    .unsqueeze(0)
                    .unsqueeze(0)
                    .float()
                    .to(device)
                    / 255.0
                )
                > 0.5
            ).float()

            gen = torch.Generator(device=device)
            gen.manual_seed(42)
            noise = torch.randn(gray_norm.shape, generator=gen, device=device, dtype=gray_norm.dtype)

            out_t = payload["model"](gray_norm, lines_norm, mask_t, noise)
            if isinstance(out_t, (tuple, list)):
                out_t = out_t[0]
            out_gray = np.clip(out_t[0, 0].detach().cpu().numpy() * 127.5 + 127.5, 0, 255).astype(
                np.uint8
            )

        out_gray = out_gray[:h, :w]
        out_rgb = cv2.cvtColor(out_gray, cv2.COLOR_GRAY2RGB)
        return self._composite_unmasked(rgb, mask, out_rgb)

    def _run_migan_crop(self, payload: dict, device: str, crop_rgb: np.ndarray, crop_mask: np.ndarray) -> np.ndarray:
        import torch

        orig_h, orig_w = crop_rgb.shape[:2]
        resized_img = resize_max_size(crop_rgb, 512, interpolation=cv2.INTER_CUBIC)
        resized_msk = resize_max_size(crop_mask, 512, interpolation=cv2.INTER_NEAREST)
        rh, rw = resized_img.shape[:2]

        sq_img = pad_img_to_modulo(resized_img, 512, pad_to_square=True)
        sq_msk = pad_img_to_modulo(resized_msk, 512, pad_to_square=True)

        img_f = (sq_img.astype(np.float32) / 255.0) * 2.0 - 1.0
        img_f = img_f.transpose(2, 0, 1)
        msk_f = (sq_msk > 120).astype(np.float32)[None, None, :, :]

        with torch.inference_mode():
            img_t = torch.from_numpy(np.ascontiguousarray(img_f)).unsqueeze(0).to(device)
            msk_t = torch.from_numpy(np.ascontiguousarray(msk_f)).to(device)
            erased_t = img_t * (1.0 - msk_t)
            model_in = torch.cat([0.5 - msk_t, erased_t], dim=1)
            out_t = payload["model"](model_in)
            if isinstance(out_t, (tuple, list)):
                out_t = out_t[0]
            out_np = np.clip(
                (out_t[0].permute(1, 2, 0).detach().cpu().numpy() * 0.5 + 0.5), 0.0, 1.0
            ) * 255.0

        out_cropped = out_np[:rh, :rw, :].astype(np.uint8)
        if (rh, rw) != (orig_h, orig_w):
            out_cropped = cv2.resize(out_cropped, (orig_w, orig_h), interpolation=cv2.INTER_CUBIC)

        return self._composite_unmasked(crop_rgb, (crop_mask >= 127).astype(np.uint8) * 255, out_cropped)

    def _run_sd_crop(
        self,
        payload: dict,
        device: str,
        crop_rgb: np.ndarray,
        crop_mask: np.ndarray,
        sd_steps: int,
        sd_prompt: str,
        sd_negative_prompt: str,
        progress_cb: Callable[[int, str], None] | None = None,
        check_cancel: Callable[[], bool] | None = None,
        roi_index: int = 1,
        roi_total: int = 1,
    ) -> np.ndarray:
        import inspect
        import torch

        if check_cancel and check_cancel():
            raise RuntimeError("Inpainting dibatalkan oleh pengguna.")

        orig_h, orig_w = crop_rgb.shape[:2]
        work_rgb = resize_max_size(crop_rgb, 768, interpolation=cv2.INTER_CUBIC)
        work_msk = resize_max_size(crop_mask, 768, interpolation=cv2.INTER_NEAREST)
        rh, rw = work_rgb.shape[:2]

        padded_rgb = pad_img_to_modulo(work_rgb, 8)
        padded_msk = pad_img_to_modulo(work_msk, 8)
        ph, pw = padded_rgb.shape[:2]

        steps = max(4, min(60, int(sd_steps or DEFAULT_SD_INPAINT_STEPS)))
        total_rois = max(1, int(roi_total or 1))
        cur_roi = max(1, min(total_rois, int(roi_index or 1)))
        area_suffix = f" (area {cur_roi}/{total_rois})" if total_rois > 1 else ""
        device_tag = device.upper()

        if progress_cb:
            init_pct = 5 if total_rois == 1 else max(1, int(((cur_roi - 1) / float(total_rois)) * 100))
            progress_cb(init_pct, f"Stable Diffusion: Step 0/{steps}{area_suffix} ({device_tag})...")

        def _on_sd_step(pipe_obj, step_idx: int, _timestep, cb_kwargs: dict) -> dict:
            done = int(step_idx) + 1
            if check_cancel and check_cancel():
                try:
                    pipe_obj._interrupt = True
                except Exception:
                    pass
                if progress_cb:
                    progress_cb(-1, f"Membatalkan Stable Diffusion di step {done}/{steps}...")
                return cb_kwargs
            if progress_cb:
                roi_base = float(cur_roi - 1) / float(total_rois)
                roi_span = 1.0 / float(total_rois)
                pct = int(round((roi_base + roi_span * (float(done) / float(steps))) * 100.0))
                progress_cb(
                    max(1, min(99, pct)),
                    f"Stable Diffusion: Step {done}/{steps}{area_suffix} ({device_tag})",
                )
            return cb_kwargs

        gen = torch.Generator(device=device)
        gen.manual_seed(42)

        pipe = payload["pipe"]
        call_kwargs: dict[str, object] = {
            "prompt": sd_prompt or "",
            "negative_prompt": sd_negative_prompt or "",
            "image": Image.fromarray(padded_rgb),
            "mask_image": Image.fromarray(((padded_msk > 0).astype(np.uint8) * 255)),
            "height": int(ph),
            "width": int(pw),
            "num_inference_steps": steps,
            "guidance_scale": 7.5,
            "strength": 1.0,
            "generator": gen,
        }
        try:
            sig_params = inspect.signature(pipe.__call__).parameters
            accepts_step_cb = "callback_on_step_end" in sig_params or any(
                p.kind == inspect.Parameter.VAR_KEYWORD for p in sig_params.values()
            )
            if accepts_step_cb:
                call_kwargs["callback_on_step_end"] = _on_sd_step
                if "callback_on_step_end_tensor_inputs" in sig_params:
                    call_kwargs["callback_on_step_end_tensor_inputs"] = ["latents"]
        except Exception:
            pass

        out_pil = pipe(**call_kwargs).images[0]

        if check_cancel and check_cancel():
            raise RuntimeError("Inpainting dibatalkan oleh pengguna.")

        out_np = np.array(out_pil.convert("RGB"), dtype=np.uint8)[:rh, :rw, :]
        if (rh, rw) != (orig_h, orig_w):
            out_np = cv2.resize(out_np, (orig_w, orig_h), interpolation=cv2.INTER_CUBIC)
        return self._composite_unmasked(crop_rgb, crop_mask, out_np)

    @staticmethod
    def _composite_unmasked(orig_rgb: np.ndarray, mask: np.ndarray, filled_rgb: np.ndarray) -> np.ndarray:
        if filled_rgb.shape[:2] != orig_rgb.shape[:2]:
            filled_rgb = cv2.resize(
                filled_rgb,
                (orig_rgb.shape[1], orig_rgb.shape[0]),
                interpolation=cv2.INTER_CUBIC,
            )
        fg = (mask > 0)[:, :, None]
        return np.where(fg, filled_rgb, orig_rgb).astype(np.uint8)

    def _run_roi_crops(
        self,
        rgb: np.ndarray,
        mask: np.ndarray,
        crop_runner: Callable[[np.ndarray, np.ndarray, int, int], np.ndarray],
        margin: int = 80,
        min_size: int = 160,
        check_cancel: Callable[[], bool] | None = None,
        progress_cb: Callable[[int, str], None] | None = None,
        label: str = "",
    ) -> np.ndarray:
        result = rgb.copy()
        rois = _merge_boxes_into_rois(mask, margin=margin, min_size=min_size)
        if not rois:
            return result
        total = len(rois)
        for idx, (x1, y1, x2, y2) in enumerate(rois):
            if check_cancel and check_cancel():
                raise RuntimeError("Inpainting dibatalkan oleh pengguna.")
            crop_img = result[y1:y2, x1:x2]
            crop_msk = mask[y1:y2, x1:x2]
            if int(np.count_nonzero(crop_msk)) == 0:
                continue
            if progress_cb and label:
                pct = max(5, int((idx / float(total)) * 95))
                progress_cb(pct, f"{label}: Area {idx + 1}/{total}...")
            result[y1:y2, x1:x2] = crop_runner(crop_img, crop_msk, idx + 1, total)
        return result

    def inpaint(
        self,
        pil_image: Image.Image,
        pil_mask: Image.Image,
        engine_id: str = DEFAULT_FULL_INPAINT_ENGINE,
        *,
        device: str = "auto",
        sd_repo_id: str = DEFAULT_SD_INPAINT_MODEL,
        sd_steps: int = DEFAULT_SD_INPAINT_STEPS,
        sd_prompt: str = "",
        sd_negative_prompt: str = "",
        server_url: str = "http://127.0.0.1:8080",
        server_timeout: int = 600,
        auto_download: bool = True,
        progress_cb: Callable[[int, str], None] | None = None,
        check_cancel: Callable[[], bool] | None = None,
    ) -> Image.Image:
        """Run inpainting with the chosen built-in or external engine."""
        norm_id = normalize_inpaint_engine_id(engine_id)
        spec = get_inpaint_spec(norm_id)
        rgb, mask = _normalize_rgb_and_mask(pil_image, pil_mask)
        if int(np.count_nonzero(mask)) == 0:
            return Image.fromarray(rgb)

        if norm_id in ("opencv_ns", "opencv_telea"):
            if progress_cb:
                progress_cb(35, f"Menjalankan {spec.short_label}...")
            res = run_opencv_inpaint(pil_image, pil_mask, method=norm_id)
            if progress_cb:
                progress_cb(100, f"Inpaint {spec.short_label} selesai.")
            return res

        if norm_id == "iopaint_server":
            from src.core.workers import run_iopaint_inpaint

            if progress_cb:
                progress_cb(15, f"Mengirim area ke server IOPaint ({server_url})...")
            res = run_iopaint_inpaint(
                Image.fromarray(rgb),
                Image.fromarray(mask).convert("L"),
                server_url=server_url,
                timeout=max(10, int(server_timeout or 600)),
            )
            if res is None:
                raise RuntimeError(
                    f"Server IOPaint eksternal di {server_url} tidak merespons."
                )
            if progress_cb:
                progress_cb(100, "Inpaint IOPaint server selesai.")
            return res

        resolved_device = self.resolve_device(device)
        with self._lock:
            payload = self._ensure_loaded(
                norm_id,
                resolved_device,
                sd_repo_id=sd_repo_id or DEFAULT_SD_INPAINT_MODEL,
                auto_download=auto_download,
                progress_cb=progress_cb,
                check_cancel=check_cancel,
            )

            if resolved_device == "cpu":
                _configure_cpu_torch_threads()
            h, w = rgb.shape[:2]
            if norm_id == "migan":
                out_rgb = self._run_roi_crops(
                    rgb,
                    mask,
                    lambda c_img, c_msk, _i, _t: self._run_migan_crop(payload, resolved_device, c_img, c_msk),
                    margin=96,
                    min_size=192,
                    check_cancel=check_cancel,
                    progress_cb=progress_cb,
                    label=f"{spec.short_label} ({resolved_device.upper()})",
                )
                if progress_cb:
                    progress_cb(100, f"Inpaint {spec.short_label} selesai.")
                return Image.fromarray(out_rgb)

            # For Big-LaMa and Manga Inpaintor, crop compactly around mask regions
            # for any medium/large page so CPU inference stays fast (<1-2s per batch)
            # instead of running over the entire page canvas.
            rois = _merge_boxes_into_rois(mask, margin=80, min_size=160) if max(h, w) > 384 else []
            roi_area = sum((r[2] - r[0]) * (r[3] - r[1]) for r in rois) if rois else h * w
            runner_2 = (
                (lambda c_img, c_msk: self._run_manga_inpaintor(payload, resolved_device, c_img, c_msk))
                if norm_id == "manga_inpaintor"
                else (lambda c_img, c_msk: self._run_big_lama(payload, resolved_device, c_img, c_msk))
            )
            if rois and roi_area < 0.72 * (h * w):
                out_rgb = self._run_roi_crops(
                    rgb,
                    mask,
                    lambda c_img, c_msk, _i, _t: runner_2(c_img, c_msk),
                    margin=80,
                    min_size=160,
                    check_cancel=check_cancel,
                    progress_cb=progress_cb,
                    label=f"{spec.short_label} ({resolved_device.upper()})",
                )
            else:
                if progress_cb:
                    progress_cb(20, f"Memproses inpaint {spec.short_label} ({resolved_device.upper()})...")
                out_rgb = runner_2(rgb, mask)
            if progress_cb:
                progress_cb(100, f"Inpaint {spec.short_label} selesai.")
            return Image.fromarray(out_rgb)


_INPAINT_MANAGER_SINGLETON: Optional[InpaintEngineManager] = None
_MANAGER_INIT_LOCK = threading.Lock()


def get_inpaint_manager() -> InpaintEngineManager:
    global _INPAINT_MANAGER_SINGLETON
    with _MANAGER_INIT_LOCK:
        if _INPAINT_MANAGER_SINGLETON is None:
            _INPAINT_MANAGER_SINGLETON = InpaintEngineManager()
        return _INPAINT_MANAGER_SINGLETON
