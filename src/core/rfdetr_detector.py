"""Deteksi layout halaman manga berbasis RF-DETR Seg 2XL (koharu).

Model lokal di `src/models/mayocreamkoharu-layout-rfdetr-seg-2xl-1152`
(checkpoint mayocream/koharu-layout-rfdetr-seg-2xl-1152, format rfdetr==1.7.0:
model.safetensors + inference_config.json).

Kelas deteksi: 0=text, 1=onomatopoeia, 2=bubble, 3=panel — semuanya
dikembalikan oleh `detect_layout_regions`; pemanggil memilih kelas yang
dipakai. Pipeline full-page memakai instance kelas "text" sebagai region
OCR apa adanya (satu instance = satu area terjemahan, tanpa penggabungan
antar instance); onomatopoeia/SFX dikecualikan agar konsisten dengan prompt
AI Vision full-page yang juga mengabaikan SFX, termasuk teks dobel-kelas
yang juga terdeteksi sebagai onomatopoeia.
"""

import os
import threading
import warnings

import cv2
from PIL import Image

from src.core.config import ROOT_DIR

MODEL_DIR_NAME = "mayocreamkoharu-layout-rfdetr-seg-2xl-1152"
MODEL_WEIGHTS = os.path.join(ROOT_DIR, "src", "models", MODEL_DIR_NAME, "model.safetensors")
MODEL_RESOLUTION = 1152
CLASS_NAMES = ["text", "onomatopoeia", "bubble", "panel"]
# Threshold rekomendasi dari inference_config.json checkpoint.
CLASS_THRESHOLDS = {"text": 0.25, "onomatopoeia": 0.20, "bubble": 0.50, "panel": 0.50}
# Predict memakai ambang serendah threshold kelas mana pun, lalu disaring
# ulang per kelas (pola dari model card checkpoint ini).
PREDICT_THRESHOLD = 0.20

_lock = threading.Lock()
_infer_lock = threading.Lock()
_model = None


def is_model_available():
    return os.path.exists(MODEL_WEIGHTS)


def _get_model():
    """Load model sekali secara lazy; aman dipanggil dari worker thread."""
    global _model
    with _lock:
        if _model is None:
            if not is_model_available():
                raise FileNotFoundError(f"Model RF-DETR tidak ditemukan: {MODEL_WEIGHTS}")
            import torch
            from rfdetr import RFDETRSeg2XLarge
            from rfdetr.config import PretrainWeightsCompatibilityWarning
            from safetensors.torch import load_file

            if not torch.cuda.is_available():
                try:
                    torch.set_num_threads(max(4, os.cpu_count() or 4))
                except Exception:
                    pass

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", PretrainWeightsCompatibilityWarning)
                model = RFDETRSeg2XLarge(
                    pretrain_weights=None,
                    resolution=MODEL_RESOLUTION,
                    num_select=160,
                    num_classes=len(CLASS_NAMES),
                )
            incompatible = model.model.model.load_state_dict(
                load_file(MODEL_WEIGHTS, device="cpu"), strict=True
            )
            if incompatible.missing_keys or incompatible.unexpected_keys:
                raise RuntimeError(f"Bobot RF-DETR tidak cocok: {incompatible}")
            model.model.class_names = CLASS_NAMES.copy()
            # Pipeline hanya memakai bounding box (xyxy, class_id, confidence);
            # matikan head & postprocess mask segmentasi agar tidak menginterpolasi
            # 160 mask resolusi penuh per halaman di CPU.
            try:
                if hasattr(model.model, "postprocess") and hasattr(model.model.postprocess, "segmentation"):
                    model.model.postprocess.segmentation = False
                if hasattr(model.model.model, "segmentation_head"):
                    model.model.model.segmentation_head = None
                model.model.model.eval()
                if hasattr(model.model.model, "export"):
                    model.model.model.export()
                model.model.inference_model = model.model.model
                model._is_optimized_for_inference = True
                model._optimized_dtype = torch.float32
                model._optimized_resolution = MODEL_RESOLUTION
            except Exception:
                pass
            _model = model
    return _model


def detect_layout_regions(cv_image):
    """Deteksi elemen layout halaman manga (ndarray BGR).

    Mengembalikan list dict `{'xyxy': (x1, y1, x2, y2), 'class': str, 'score': float}`
    untuk semua kelas (text/onomatopoeia/bubble/panel) yang lolos threshold
    per kelasnya. Raise exception bila model/dependency tidak tersedia —
    pemanggil yang memutuskan fallback.
    """
    model = _get_model()
    import torch
    rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
    pil_rgb = Image.fromarray(rgb)
    with _infer_lock, torch.inference_mode():
        detections = model.predict(
            pil_rgb,
            threshold=PREDICT_THRESHOLD,
            shape=(MODEL_RESOLUTION, MODEL_RESOLUTION),
            include_source_image=False,
        )
    regions = []
    for xyxy, class_id, confidence in zip(detections.xyxy, detections.class_id, detections.confidence):
        class_idx = int(class_id)
        name = CLASS_NAMES[class_idx] if 0 <= class_idx < len(CLASS_NAMES) else None
        if name is None or float(confidence) < CLASS_THRESHOLDS.get(name, PREDICT_THRESHOLD):
            continue
        x1, y1, x2, y2 = (int(round(float(v))) for v in xyxy)
        regions.append({"xyxy": (x1, y1, x2, y2), "class": name, "score": float(confidence)})

    # Buang teks yang juga terdeteksi sebagai onomatopoeia (SFX dobel-kelas):
    # model kadang memberi skor "text" rendah pada SFX yang menempel di artwork
    # (atau memecah SFX 2 baris menjadi beberapa box onomatopoeia), padahal SFX
    # dikecualikan dari pipeline full-page.
    sfx_regions = [r for r in regions if r["class"] == "onomatopoeia"]

    def _covered_by_sfx(region):
        rx1, ry1, rx2, ry2 = region["xyxy"]
        rw, rh = max(1, rx2 - rx1), max(1, ry2 - ry1)
        area = rw * rh
        r_score = region["score"]
        covered = None
        for sfx in sfx_regions:
            if sfx["score"] < 0.5 and sfx["score"] < r_score:
                continue
            sx1, sy1, sx2, sy2 = sfx["xyxy"]
            ix1, iy1 = max(rx1, sx1), max(ry1, sy1)
            ix2, iy2 = min(rx2, sx2), min(ry2, sy2)
            if ix2 <= ix1 or iy2 <= iy1:
                continue
            if (ix2 - ix1) * (iy2 - iy1) >= 0.5 * area:
                return True
            if covered is None:
                import numpy as np
                covered = np.zeros((rh, rw), dtype=np.uint8)
            covered[iy1 - ry1:iy2 - ry1, ix1 - rx1:ix2 - rx1] = 1
        return bool(covered is not None and int(covered.sum()) >= 0.5 * area)

    return [
        r for r in regions
        if r["class"] != "text" or not _covered_by_sfx(r)
    ]
