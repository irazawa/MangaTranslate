"""Method domain inpaint, dipindahkan utuh dari main_window.py.

Fase 1 pemecahan monolit: isi method tidak diubah sama sekali.
Mixin ini hanya berguna sebagai bagian dari MangaOCRApp -- ia mengandalkan
atribut yang dibuat di MangaOCRApp.__init__.
"""

from src.ui.main_window_mixins._imports import *  # noqa: F401,F403


class InpaintMixin:
    # [BARU] Inisialisasi on-demand untuk model inpainting
    def initialize_inpaint_engine(self, settings=None):
        """Menginisialisasi engine inpainting LaMa yang dipilih."""
        if settings is None:
            settings = self.get_current_settings()
        model_key = settings.get('inpaint_model_key')

        # Jika pengguna memilih mode OpenCV (atau tidak memilih model LaMa sama sekali),
        # pastikan state lama_cleaner dilepas agar tidak dicoba lagi.
        if not model_key:
            self.inpaint_model = None
            self.current_inpaint_model_key = None
            return

        if model_key == self.current_inpaint_model_key and self.inpaint_model is not None:
            return

        if not self.is_lama_available:
            print("Lama Cleaner not available; falling back to OpenCV inpaint.")
            self.inpaint_model = None
            self.current_inpaint_model_key = None
            return

        model_info = self.dl_models.get(model_key)
        if not model_info or not os.path.exists(model_info['path']):
            print(f"Model file not found: {model_info['path'] if model_info else 'None'}")
            self.inpaint_model = None
            self.current_inpaint_model_key = None
            return

        is_gui_thread = (QThread.currentThread() == self.thread())
        if is_gui_thread:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.statusBar().showMessage(f"Initializing inpainting model: {model_key}...")
        
        try:
            # Tentukan device (CPU/GPU)
            use_gpu = settings.get('use_gpu', False)
            device = "cuda" if use_gpu and self.is_gpu_available else "cpu"
            
            # Inisialisasi model manager
            from lama_cleaner.model_manager import ModelManager
            model_manager = ModelManager()
            
            # Tentukan jenis model
            model_type = "lama"  # Kedua model menggunakan arsitektur LaMa
            
            # Load model (try/catch karena API lama/baru bisa berbeda)
            loaded_model = None
            try:
                loaded_model = model_manager.init_model(device, model_info['path'], model_type=model_type)
            except Exception:
                # fallback jika api berbeda
                try:
                    loaded_model = model_manager.load_model(model_info['path'], device=device)
                except Exception as e:
                    print(f"Could not load model via ModelManager: {e}")
                    loaded_model = None

            if loaded_model is None:
                raise RuntimeError("Failed to initialize inpainting model instance.")

            # Bungkus model menjadi callable yang selalu mengembalikan PIL.Image
            self.inpaint_model = lambda pil_img, pil_mask: self._run_lama_inpaint(loaded_model, pil_img, pil_mask)
            self.current_inpaint_model_key = model_key
            if is_gui_thread:
                self.statusBar().showMessage(f"Inpainting model {model_key} initialized on {device.upper()}.", 3000)
            else:
                print(f"Inpainting model {model_key} initialized on {device.upper()} (background thread).")
            
        except Exception as e:
            print(f"Error initializing inpainting model {model_key}: {e}")
            self.inpaint_model = None
            self.current_inpaint_model_key = None
            
        finally:
            if is_gui_thread:
                QApplication.restoreOverrideCursor()

    def _run_lama_inpaint(self, model, pil_image, pil_mask):
        """
        Helper untuk memanggil model lama/baru dari lama_cleaner dan
        mengembalikan hasil sebagai numpy array (RGB).
        Menangani beberapa varian API yang mungkin tersedia.
        """
        try:
            # Pastikan mask ukuran sama dengan image
            if pil_mask.size != pil_image.size:
                pil_mask = pil_mask.resize(pil_image.size)

            # Coba beberapa cara pemanggilan model yang umum
            result = None
            try:
                # model bisa callable
                result = model(pil_image, pil_mask)
            except Exception:
                pass

            if result is None and hasattr(model, "process"):
                try:
                    result = model.process(pil_image, pil_mask)
                except Exception:
                    pass

            if result is None and hasattr(model, "inpaint"):
                try:
                    result = model.inpaint(pil_image, pil_mask)
                except Exception:
                    pass

            if result is None and hasattr(model, "run"):
                try:
                    # some apis expect keyword args
                    try:
                        result = model.run(image=pil_image, mask=pil_mask)
                    except TypeError:
                        result = model.run(pil_image, pil_mask)
                except Exception:
                    pass

            if result is None:
                raise RuntimeError("Inpainting model did not return a result (unsupported API).")

            # Normalisasi hasil menjadi PIL.Image atau numpy array (RGB)
            if isinstance(result, tuple) or isinstance(result, list):
                # kadang model mengembalikan (image, ...)
                candidate = result[0]
            else:
                candidate = result

            if hasattr(candidate, "convert") and hasattr(candidate, "size"):
                # PIL Image
                pil_out = candidate.convert("RGB")
                return np.array(pil_out)[:, :, ::-1]  # convert RGB->BGR for OpenCV path if necessary later
            elif isinstance(candidate, np.ndarray):
                # Pastikan format RGB
                arr = candidate
                if arr.ndim == 3 and arr.shape[2] == 3:
                    # as-is, convert to RGB ordering expected later
                    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR) if arr.dtype == np.uint8 else arr
                return arr
            elif isinstance(candidate, dict):
                # coba beberapa key umum
                for k in ("result", "image", "output", "pred"):
                    if k in candidate:
                        v = candidate[k]
                        if hasattr(v, "convert"):
                            return np.array(v.convert("RGB"))[:, :, ::-1]
                        if isinstance(v, np.ndarray):
                            return v
                raise RuntimeError("Unsupported dict result from inpaint model.")
            else:
                raise RuntimeError("Unsupported result type from inpaint model.")

        except Exception as e:
            print(f"Error running inpaint model: {e}")
            return None

    def _is_inpaint_brush_mode(self, mode=None):
        mode = mode if mode is not None else self.selection_mode_combo.currentText()
        return mode in ("Inpaint Brush", "Inpaint Brush + OCR Translate")

    def _is_inpaint_ocr_mode(self, mode=None):
        mode = mode if mode is not None else self.selection_mode_combo.currentText()
        return mode == "Inpaint Brush + OCR Translate"

    def _get_inpaint_brush_mask_and_rect(self):
        mask_img = self.image_label.get_inpaint_mask() if hasattr(self, 'image_label') else None
        if mask_img is None or mask_img.isNull():
            self.show_toast("No Mask", "Please paint an area on the canvas first.", kind="warning")
            return None, None
        if mask_img.size() != self.original_pixmap.size():
            self.image_label.clear_inpaint_mask()
            self.show_toast("Mask Reset", "The mask did not match the current image. Please paint again.", kind="warning")
            return None, None

        qimg_mask = mask_img.convertToFormat(QImage.Format_Grayscale8)
        w, h = qimg_mask.width(), qimg_mask.height()
        ptr = qimg_mask.bits()
        ptr.setsize(h * qimg_mask.bytesPerLine())
        arr = np.ascontiguousarray(np.array(ptr).reshape((h, qimg_mask.bytesPerLine()))[:, :w])
        ys, xs = np.where(arr > 0)
        if xs.size == 0 or ys.size == 0:
            self.show_toast("No Mask", "Please paint an area on the canvas first.", kind="warning")
            return None, None
        rect = QRect(int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1))
        return Image.fromarray(arr), rect

    def _current_pre_inpaint_image(self, fallback_pil):
        _, record = self._current_inpaint_record()
        pre_image = self._decode_image_png(record.get('pre_inpaint_image_png')) if record else None
        if pre_image is not None:
            return pre_image
        return fallback_pil

    def apply_inpaint_brush_selection(self, run_ocr_translate=False):
        if getattr(self, 'original_pixmap', None) is None:
            self.show_toast("No Image", "Please load an image first.", kind="warning")
            return
        existing = getattr(self, '_inpaint_brush_worker', None)
        if existing is not None and existing.isRunning():
            return
        pil_mask, mask_rect = self._get_inpaint_brush_mask_and_rect()
        if pil_mask is None:
            return

        if getattr(self, 'current_image_pil', None) is not None and self.current_image_pil.size == (self.original_pixmap.width(), self.original_pixmap.height()):
            pil_image = self.current_image_pil.convert('RGB')
        else:
            qimg = self.original_pixmap.toImage().convertToFormat(QImage.Format_RGB888)
            w, h = qimg.width(), qimg.height()
            ptr = qimg.bits()
            ptr.setsize(h * qimg.bytesPerLine())
            arr_img = np.ascontiguousarray(np.array(ptr).reshape((h, qimg.bytesPerLine()))[:, :w * 3].reshape((h, w, 3)))
            pil_image = Image.fromarray(arr_img)

        clean_base = self._current_clean_base_image(pil_image)
        if run_ocr_translate:
            ocr_source = self._current_pre_inpaint_image(pil_image)
            if self._queue_ocr_translate_rect(mask_rect, source_pil_image=ocr_source):
                self.show_toast("OCR Queued", "OCR and translation queued for the painted area.", kind="info")

        self.show_toast("Inpainting...", "Running AI Inpainting on painted area...", kind="info")
        if hasattr(self, 'inpaint_confirm_button'):
            self.inpaint_confirm_button.setEnabled(False)

        from src.core.workers import InpaintBrushWorker
        worker = InpaintBrushWorker(self, clean_base, pil_mask, self.get_current_settings())
        worker.signals.progress.connect(lambda msg: self.statusBar().showMessage(msg, 3000))
        worker.signals.error.connect(self._on_inpaint_brush_error)
        worker.signals.finished.connect(self._on_inpaint_brush_finished)
        worker.finished.connect(self._on_inpaint_brush_thread_finished)
        self._inpaint_brush_worker = worker
        worker.start()

    def _on_inpaint_brush_thread_finished(self):
        # Lepas referensi hanya setelah QThread benar-benar selesai (aturan thread safety repo)
        self._inpaint_brush_worker = None

    def _on_inpaint_brush_error(self, err_msg):
        if hasattr(self, 'inpaint_confirm_button'):
            self.inpaint_confirm_button.setEnabled(True)
        self.show_banner("inpaint-brush-err", "Inpainting Failed", f"Error: {err_msg}", kind="error")

    def _current_inpaint_record(self):
        key = self.get_current_data_key()
        record = self.all_typeset_data.get(key, {}) if key else {}
        return key, record if isinstance(record, dict) else {}

    def _refresh_inpaint_result_controls(self):
        _, record = self._current_inpaint_record()
        has_inpaint_state = bool(record.get('cleaned_image_png') and record.get('pre_inpaint_image_png'))
        for button_name in ('inpaint_compare_button', 'inpaint_cancel_button'):
            button = getattr(self, button_name, None)
            if button is not None:
                button.setEnabled(has_inpaint_state)
        if not has_inpaint_state and getattr(self, 'inpaint_compare_button', None) is not None:
            self._set_compare_controls_checked(False)

    def adjust_inpaint_brush_size(self, delta):
        spinbox = getattr(self, 'brush_size_spinbox', None)
        if spinbox is None:
            return
        value = max(spinbox.minimum(), min(spinbox.maximum(), spinbox.value() + int(delta)))
        spinbox.setValue(value)
        self.statusBar().showMessage(f"Inpaint brush size: {value}px", 1200)

    def cancel_inpaint_result(self):
        key, record = self._current_inpaint_record()
        pre_inpaint_png = record.get('pre_inpaint_image_png')
        if not key or not pre_inpaint_png:
            self.show_toast("No Inpaint Result", "No saved inpainting result to cancel on this page.", kind="info")
            return
        pre_image = self._decode_image_png(pre_inpaint_png)
        if pre_image is None:
            self.show_banner("inpaint-cancel-error", "Cancel Inpainting Failed", "The saved before-inpaint image could not be restored.", kind="error")
            return

        cleaned_image = self._decode_cleaned_image(record)
        if cleaned_image is not None:
            self._apply_base_image(cleaned_image)
        self._push_undo_snapshot("Cancel Inpaint Clean")
        self._set_compare_controls_checked(False)
        self._compare_mode_active = False
        self._apply_base_image(pre_image)
        self._update_typeset_record(
            key,
            areas=list(self.typeset_areas),
            redo=list(self.redo_stack),
            remove_cleaned_image=True,
            remove_pre_inpaint_image=True,
        )
        if hasattr(self, 'image_label'):
            self.image_label.clear_inpaint_mask()
        self.redraw_all_typeset_areas()
        self._refresh_inpaint_result_controls()
        self.show_toast("Inpainting Cancelled", "Restored the page before inpainting.", kind="success")

    def _on_inpaint_brush_finished(self, result_pil):
        if hasattr(self, 'inpaint_confirm_button'):
            self.inpaint_confirm_button.setEnabled(True)
        try:
            key = self.get_current_data_key()
            record = self.all_typeset_data.get(key, {}) if key else {}
            pre_inpaint_png = record.get('pre_inpaint_image_png') if isinstance(record, dict) else None
            if not pre_inpaint_png:
                pre_inpaint_png = self._encode_cleaned_image(self.current_image_pil)

            self._push_undo_snapshot("Inpaint Brush Clean")
            self._set_compare_controls_checked(False)
            self._compare_mode_active = False
            self._apply_base_image(result_pil)
            self._update_typeset_record(
                key,
                areas=list(self.typeset_areas),
                redo=list(self.redo_stack),
                cleaned_image_png=self._encode_cleaned_image(self.current_image_pil),
                pre_inpaint_image_png=pre_inpaint_png,
            )

            if hasattr(self, 'image_label'):
                self.image_label.clear_inpaint_mask()

            self.redraw_all_typeset_areas()
            self._refresh_inpaint_result_controls()
            self.show_toast("Inpaint Cleaned", "Background area cleaned successfully.", kind="success")
        except Exception as e:
            self._on_inpaint_brush_error(str(e))
