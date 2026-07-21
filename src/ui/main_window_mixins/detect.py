"""Method domain detect, dipindahkan utuh dari main_window.py.

Fase 1 pemecahan monolit: isi method tidak diubah sama sekali.
Mixin ini hanya berguna sebagai bagian dari MangaOCRApp -- ia mengandalkan
atribut yang dibuat di MangaOCRApp.__init__.
"""

from src.ui.main_window_mixins._imports import *  # noqa: F401,F403


class DetectMixin:
    def _find_speech_bubble_mask_contour(self, full_cv_image, text_rect):
        padding = 25
        search_qt_rect = text_rect.adjusted(-padding, -padding, padding, padding)
        h, w, _ = full_cv_image.shape
        search_qt_rect.setLeft(max(0, search_qt_rect.left()))
        search_qt_rect.setTop(max(0, search_qt_rect.top()))
        search_qt_rect.setRight(min(w - 1, search_qt_rect.right()))
        search_qt_rect.setBottom(min(h - 1, search_qt_rect.bottom()))
        if search_qt_rect.width() <= 0 or search_qt_rect.height() <= 0: return None
        search_area_cv = full_cv_image[search_qt_rect.top():search_qt_rect.bottom(), search_qt_rect.left():search_qt_rect.right()]
        gray = cv2.cvtColor(search_area_cv, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 41, 5)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours: return None
        text_center_relative = QPoint(text_rect.center().x() - search_qt_rect.left(), text_rect.center().y() - search_qt_rect.top())
        candidate_contours = [cnt for cnt in contours if cv2.pointPolygonTest(cnt, (text_center_relative.x(), text_center_relative.y()), False) >= 0 and cv2.contourArea(cnt) > text_rect.width() * text_rect.height() * 0.5]
        if not candidate_contours: return None
        best_contour = max(candidate_contours, key=cv2.contourArea)
        final_mask = np.zeros(full_cv_image.shape[:2], dtype=np.uint8)
        shifted_contour = best_contour + np.array([search_qt_rect.left(), search_qt_rect.top()])
        cv2.drawContours(final_mask, [shifted_contour], -1, 255, thickness=cv2.FILLED)
        return final_mask

    def detect_bubble_with_dl_model(self, full_cv_image, settings):
        provider = settings['dl_provider']
        model_file = settings['dl_model_file']
        model_key = ""

        if provider == "Kitsumed": model_key = 'kitsumed_onnx' if model_file == 'model_dynamic.onnx' else 'kitsumed_pt'
        elif provider == "Ogkalu": model_key = 'ogkalu_pt'

        if not model_key: return None
        model_type = self.dl_models[model_key]['type']

        if model_type == 'onnx':
            # model_dynamic.onnx adalah ekspor YOLOv8-seg; output-nya tensor deteksi,
            # bukan mask mentah. Decode lewat ultralytics bila tersedia.
            if self.is_yolo_available:
                return self._run_yolov8_inference(model_key, full_cv_image, settings)
            return self._run_onnx_inference(model_key, full_cv_image, settings)
        elif model_type == 'yolo': return self._run_yolov8_inference(model_key, full_cv_image, settings)
        return None

    def _ensure_bubble_model_ready(self, settings):
        """Pastikan file model bubble detector ada; tawarkan download otomatis jika hilang."""
        provider = settings.get('dl_provider')
        model_file = settings.get('dl_model_file')
        if provider == "Kitsumed":
            model_key = 'kitsumed_onnx' if model_file == 'model_dynamic.onnx' else 'kitsumed_pt'
        elif provider == "Ogkalu":
            model_key = 'ogkalu_pt'
        else:
            return True

        model_path = self.dl_models[model_key]['path']
        if os.path.exists(model_path):
            return True

        url, size_label = self.BUBBLE_MODEL_URLS[model_key]
        reply = QMessageBox.question(
            self,
            "Download Model",
            f"Model bubble detector '{os.path.basename(model_path)}' tidak ditemukan.\n"
            f"Apakah Anda ingin mengunduhnya secara otomatis dari Hugging Face ({size_label})?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._download_model_file(url, model_path, self.start_interactive_batch_detection, "Unduh Model Bubble")
        return False

    def find_speech_bubble_mask(self, full_cv_image, text_rect, settings, for_saving=False):
        if settings['use_dl_detector']:
            if not for_saving:
                self.statusBar().showMessage(f"Detecting bubble with {settings['dl_provider']} model...", 2000)
                QApplication.processEvents()

            combined_dl_mask = self.detect_bubble_with_dl_model(full_cv_image, settings)

            if combined_dl_mask is not None:
                contours, _ = cv2.findContours(combined_dl_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                text_center = (text_rect.center().x(), text_rect.center().y())

                for cnt in contours:
                    if cv2.pointPolygonTest(cnt, text_center, False) >= 0:
                        single_bubble_mask = np.zeros_like(combined_dl_mask)
                        cv2.drawContours(single_bubble_mask, [cnt], -1, 255, thickness=cv2.FILLED)
                        return single_bubble_mask

        if not for_saving:
            self.statusBar().showMessage("Detecting bubble with contour method...", 2000)
            QApplication.processEvents()
        return self._find_speech_bubble_mask_contour(full_cv_image, text_rect)

    def draw_area_bubble(self, painter, area):
        path = QPainterPath()
        cleanup_polygon = area.get_cleanup_polygon() if hasattr(area, 'get_cleanup_polygon') else None
        if cleanup_polygon:
            path.addPolygon(QPolygonF(cleanup_polygon))
        else:
            rect = QRectF(area.get_cleanup_rect() if hasattr(area, 'get_cleanup_rect') else area.rect)
            radius = max(8.0, min(rect.width(), rect.height()) * 0.18)
            path.addRoundedRect(rect, radius, radius)

        painter.setBrush(QBrush(area.get_bubble_fill_color()))
        outline_width = max(1.0, float(getattr(area, 'bubble_outline_width', 3.0) or 3.0))
        painter.setPen(QPen(area.get_bubble_outline_color(), outline_width))
        painter.drawPath(path)

    def on_dl_detector_state_changed(self, state):
        is_checked = (state == Qt.Checked)
        provider = self.dl_model_provider_combo.currentText()
        model_file = self.dl_model_file_combo.currentText()
        is_available = True
        tooltip = f"Uses {provider}'s {model_file} for advanced bubble detection."

        if not model_file: is_available = False; tooltip = "No model selected or available."
        elif model_file.endswith('.onnx'):
            if not self.is_onnx_available: is_available = False; tooltip = "Disabled: 'onnxruntime' not installed."
            elif not os.path.exists(self.dl_models['kitsumed_onnx']['path']): is_available = False; tooltip = f"Disabled: Model file not found."
        elif model_file.endswith('.pt'):
            if not self.is_yolo_available: is_available = False; tooltip = "Disabled: 'ultralytics' not installed."
            else:
                key = 'ogkalu_pt' if provider == 'Ogkalu' else 'kitsumed_pt'
                if not os.path.exists(self.dl_models[key]['path']): is_available = False; tooltip = f"Disabled: Model file not found."

        self.dl_bubble_detector_checkbox.setEnabled(is_available)
        self.dl_bubble_detector_checkbox.setToolTip(tooltip)
        if not is_available: self.dl_bubble_detector_checkbox.setChecked(False)

    def split_extended_bubbles(self, detections, split_threshold=2.5):
        new_detections = []
        for item in detections:
            poly = item['polygon']
            bbox = poly.boundingRect()
            if bbox.width() <= 0 or bbox.height() <= 0: continue
            aspect_ratio = bbox.width() / bbox.height()

            if aspect_ratio > split_threshold:
                mid_x = bbox.left() + bbox.width() // 2
                poly1 = QPolygon(QRect(bbox.left(), bbox.top(), bbox.width() // 2, bbox.height()))
                poly2 = QPolygon(QRect(mid_x, bbox.top(), bbox.width() // 2, bbox.height()))
                new_detections.append({'polygon': poly1, 'text': None}) # Teks akan di-OCR ulang
                new_detections.append({'polygon': poly2, 'text': None})
            elif (1 / aspect_ratio) > split_threshold:
                mid_y = bbox.top() + bbox.height() // 2
                poly1 = QPolygon(QRect(bbox.left(), bbox.top(), bbox.width(), bbox.height() // 2))
                poly2 = QPolygon(QRect(bbox.left(), mid_y, bbox.width(), bbox.height() // 2))
                new_detections.append({'polygon': poly1, 'text': None})
                new_detections.append({'polygon': poly2, 'text': None})
            else:
                new_detections.append(item)
        return new_detections

    def on_detection_complete(self, image_path, detections):
        self.detected_items_map[image_path] = detections
        current_key = self._resolve_detection_key(self.get_current_data_key())
        if current_key == image_path:
            self.image_label.set_detected_items(detections)

    def on_detection_finished(self):
        self.set_ui_for_detection(False)
        self.overall_progress_bar.setVisible(False)
        if self.get_current_settings()['auto_split_bubbles']:
            self.statusBar().showMessage("Splitting extended items...", 3000)
            QApplication.processEvents()
            for path, detections in self.detected_items_map.items():
                self.detected_items_map[path] = self.split_extended_bubbles(detections)

        if self.last_detection_mode == "Text" and self.detected_items_map:
            self.preview_mode_active = True
            self.cancel_detection_button.setText("Cancel Preview")
            self.cancel_detection_button.setVisible(True)
            self.file_list_widget.setEnabled(True)
            self.prev_button.setEnabled(True)
            self.next_button.setEnabled(True)
        else:
            self.preview_mode_active = False
            self.cancel_detection_button.setVisible(False)
            self.cancel_detection_button.setText("Cancel Detection")

        self.statusBar().showMessage("Detection complete. Please review the highlighted areas.", 5000)
        self.show_toast("Detection complete", "Please review the highlighted areas.", kind="success")
        self.show_desktop_notification("Bubble Detection Selesai", "Proses pendeteksian balon teks/teks otomatis telah selesai.")
        self.set_ui_for_confirmation(True)

    def process_confirmed_detections(self):
        self.statusBar().showMessage("Processing confirmed items...")
        QApplication.processEvents()

        total_items = sum(len(items) for items in self.detected_items_map.values())
        if total_items == 0:
            self.show_toast("No items", "No items were confirmed for processing.", kind="info")
            self.cancel_interactive_batch()
            return

        # Gunakan settings user apa adanya (OCR engine, mode translate, dan model AI
        # mengikuti pilihan di UI — tidak ada paksaan pipeline khusus untuk batch)
        settings = self.get_current_settings()

        # Simpan halaman saat ini untuk kembali nanti
        current_image_path = self.current_image_path
        current_pdf_page = self.current_pdf_page

        try:
            for image_path, detections in self.detected_items_map.items():
                # Muat gambar untuk halaman ini jika berbeda dengan yang sedang aktif
                if image_path != self.get_current_data_key():
                    # Untuk file gambar biasa
                    if not image_path.lower().endswith('.pdf'):
                        if image_path != self.current_image_path:
                            # Simpan data halaman saat ini
                            current_key = self.get_current_data_key()
                            if current_key:
                                self._update_typeset_record(
                                    current_key,
                                    areas=list(self.typeset_areas),
                                    redo=list(self.redo_stack),
                                )
                            
                            # Muat gambar baru
                            self.current_image_path = image_path
                            self.load_image(image_path)
                    # Untuk PDF (handle khusus)
                    elif '::page::' in image_path:
                        # Ekstrak path dan page number
                        path_part, page_str = image_path.split('::page::')
                        page_num = int(page_str)
                        
                        # Muat halaman PDF yang sesuai
                        if self.pdf_document and self.pdf_document.name == path_part:
                            self.load_pdf_page(page_num)
                        else:
                            # Jika PDF belum dimuat, muat dulu
                            self.load_item(path_part)
                            self.load_pdf_page(page_num)

                # Proses setiap deteksi untuk halaman ini
                for item in detections:
                    polygon = item['polygon']
                    text = item['text'] # Bisa None jika dari Bubble Detect
                    # Salin settings per job agar flag paksaan AI-only ikut terpakai
                    # dan worker tidak saling menimpa dict yang sama
                    self.process_confirmed_polygon(polygon, pre_detected_text=text, settings_override=dict(settings))
                    
        except Exception as e:
            self.on_worker_error(f"Error processing batch: {e}")
        finally:
            # Kembali ke halaman asal
            try:
                if current_image_path != self.get_current_data_key():
                    if current_image_path.lower().endswith('.pdf') and current_pdf_page != -1:
                        self.load_pdf_page(current_pdf_page)
                    else:
                        self.load_item(current_image_path)
            except:
                pass

        # Worker sudah mulai dari process_confirmed_polygon, jadi kita hanya perlu membersihkan UI
        self.cancel_interactive_batch()

    def remove_detected_item(self, index_to_remove):
        current_key = self.get_current_data_key()
        resolved_key = self._resolve_detection_key(current_key) or current_key
        if resolved_key in self.detected_items_map and 0 <= index_to_remove < len(self.detected_items_map[resolved_key]):
            del self.detected_items_map[resolved_key][index_to_remove]
            if self.detected_items_map.get(resolved_key):
                self.image_label.set_detected_items(self.detected_items_map[resolved_key])
            else:
                self.image_label.clear_detected_items()
            self.update_confirmation_button_text()

    def set_ui_for_detection(self, is_detecting):
        self.batch_process_button.setEnabled(not is_detecting)
        self.file_list_widget.setEnabled(not is_detecting)
        self.prev_button.setEnabled(not is_detecting); self.next_button.setEnabled(not is_detecting)
        if is_detecting:
            self.cancel_detection_button.setText("Cancel Detection")
            self.cancel_detection_button.setVisible(True)
        self.overall_progress_bar.setVisible(is_detecting)
        if is_detecting: self.overall_progress_bar.setValue(0); self.statusBar().showMessage("Starting detection...")
        else: self.overall_progress_bar.setVisible(False)

    def _resolve_detection_key(self, key):
        if not key:
            return None
        if key in self.detected_items_map:
            return key
        if "::page::" in key:
            base_key = key.split('::page::')[0]
            if base_key in self.detected_items_map:
                return base_key
        return None

    def _refresh_detection_overlay(self):
        if not self.image_label:
            return
        if not self.is_in_confirmation_mode:
            self.image_label.clear_detected_items()
            return
        current_key = self._resolve_detection_key(self.get_current_data_key())
        if current_key and current_key in self.detected_items_map:
            self.image_label.set_detected_items(self.detected_items_map[current_key])
        else:
            self.image_label.clear_detected_items()

    # --- Metode Baru untuk Bubble Finder ---
    def find_bubble_in_rect(self, selection_rect):
        """Menjalankan deteksi bubble pada area yang dipilih pengguna."""
        if not self.current_image_pil:
            return
        
        settings = self.get_current_settings()
        if not settings.get('use_dl_detector'):
            self.show_banner("bubble-detector-disabled", "Detector disabled", "Please enable 'Gunakan DL Model untuk Bubble' in the Cleanup tab to use this feature.", kind="warning")
            self.image_label.clear_selection()
            return
            
        self.statusBar().showMessage(f"Finding bubble with {settings['dl_provider']} model...")
        QApplication.processEvents()
        
        try:
            # Crop image
            cropped_pil = self.current_image_pil.crop((
                selection_rect.left(), selection_rect.top(),
                selection_rect.right(), selection_rect.bottom()
            ))
            cropped_cv = cv2.cvtColor(np.array(cropped_pil), cv2.COLOR_RGB2BGR)

            # Run inference on the crop
            mask = self.detect_bubble_with_dl_model(cropped_cv, settings)
            
            if mask is None or cv2.countNonZero(mask) == 0:
                self.statusBar().showMessage("No bubble found in the selected area.", 3000)
                self.image_label.clear_selection()
                return

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                self.statusBar().showMessage("No valid bubble contour found.", 3000)
                self.image_label.clear_selection()
                return

            # Ambil kontur terbesar
            best_contour = max(contours, key=cv2.contourArea)

            # Geser koordinat poligon kembali ke sistem koordinat gambar penuh
            offset = selection_rect.topLeft()
            full_image_polygon = QPolygon([QPoint(p[0][0] + offset.x(), p[0][1] + offset.y()) for p in best_contour])

            # Tampilkan untuk konfirmasi
            self.image_label.set_pending_item(full_image_polygon)
            self.statusBar().showMessage("Bubble found! Right-click to confirm, Middle-click to cancel.", 5000)

        except Exception as e:
            self.on_worker_error(f"Error during interactive bubble detection: {e}")
            self.image_label.clear_selection()

    def detect_text_with_ocr_engine(self, cv_image, settings):
        """Detect text regions and return recognized text polygons."""
        engine = (settings.get('ocr_engine') or 'Tesseract')
        advanced = settings.get('batch_text_detection_enabled', False)

        try:
            raw_results = self._collect_engine_detections(cv_image, settings, engine, advanced)
        except Exception as e:
            print(f"Error during text detection with {engine}: {e}")
            raw_results = []

        if not raw_results:
            return []

        if advanced:
            raw_results = self._tighten_detection_polygons(cv_image, raw_results)

        filtered = self._filter_detection_noise(raw_results, cv_image.shape, advanced=advanced)
        if not filtered:
            return []

        merged = self._merge_text_boxes_to_blocks(filtered, cv_image.shape, strict=advanced)
        if advanced and merged:
            merged = self._tighten_detection_polygons(cv_image, merged)

        final = self._filter_detection_noise(merged, cv_image.shape, advanced=advanced)
        return final

    def _collect_engine_detections(self, cv_image, settings, engine, advanced):
        engine = engine or 'Tesseract'

        if engine == 'DocTR':
            return self._collect_doctr_detections(cv_image, advanced=advanced)
        if engine == 'EasyOCR':
            return self._collect_easyocr_detections(cv_image, advanced=advanced)
        if engine == 'PaddleOCR':
            return self._collect_paddleocr_detections(cv_image, advanced=advanced)
        if engine == 'RapidOCR':
            return self._collect_rapidocr_detections(cv_image, advanced=advanced)
        if engine == 'Manga-OCR':
            return self._collect_manga_detections(cv_image, settings, advanced=advanced)
        if engine == 'AI_OCR':
            regions = self._collect_morphological_regions(cv_image, advanced=advanced)
            results = []
            for _, polygon in regions:
                recognized = self._recognize_polygon(cv_image, polygon, 'AI_OCR', settings)
                results.append((recognized, polygon))
            return results
        if engine == 'Tesseract':
            if advanced:
                return self._collect_tesseract_advanced_detections(cv_image, settings, advanced=True)
            return self._collect_tesseract_native_detections(cv_image, settings.get('ocr_lang') or 'eng')
        return self._collect_easyocr_detections(cv_image, advanced=advanced)

    def _collect_doctr_detections(self, cv_image, advanced=False):
        if not self.doctr_predictor:
            return []

        rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        result = self.doctr_predictor([rgb_image])
        items = []
        height, width = cv_image.shape[:2]

        for page in result.pages:
            for block in page.blocks:
                for line in block.lines:
                    line_text = ' '.join(word.value for word in line.words)
                    geometry = line.geometry
                    x1 = int(geometry[0][0] * width)
                    y1 = int(geometry[0][1] * height)
                    x2 = int(geometry[1][0] * width)
                    y2 = int(geometry[1][1] * height)
                    polygon = QPolygon([
                        QPoint(x1, y1),
                        QPoint(x2, y1),
                        QPoint(x2, y2),
                        QPoint(x1, y2),
                    ])
                    items.append((line_text, polygon))

        return items

    def _collect_easyocr_detections(self, cv_image, advanced=False):
        if not self.easyocr_reader:
            return []
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        try:
            ocr_result = self.easyocr_reader.readtext(gray, detail=1)
        except Exception as e:
            print(f"EasyOCR detection error: {e}")
            return []

        items = []
        min_prob = 0.45 if advanced else 0.30
        for bbox, text, prob in ocr_result:
            if advanced and prob < min_prob:
                continue
            polygon = QPolygon([QPoint(int(p[0]), int(p[1])) for p in bbox])
            items.append((text, polygon))
        return items

    def _collect_paddleocr_detections(self, cv_image, advanced=False):
        if not self.paddle_ocr_reader:
            return []
        try:
            ocr_result = self.paddle_ocr_reader.ocr(cv_image, cls=True)
        except Exception as e:
            print(f"PaddleOCR detection error: {e}")
            return []

        items = []
        if ocr_result and ocr_result[0]:
            for line in ocr_result[0]:
                polygon = QPolygon([QPoint(int(p[0]), int(p[1])) for p in line[0]])
                items.append((line[1][0], polygon))
        return items

    def _collect_rapidocr_detections(self, cv_image, advanced=False):
        if not self.rapid_ocr_reader:
            return []
        try:
            ocr_result, _ = self.rapid_ocr_reader(cv_image)
        except Exception as e:
            print(f"RapidOCR detection error: {e}")
            return []

        items = []
        if ocr_result:
            for box_info in ocr_result:
                polygon = QPolygon([QPoint(int(p[0]), int(p[1])) for p in box_info[0]])
                items.append((box_info[1], polygon))
        return items

    def _collect_easy_detection_regions(self, cv_image, advanced=False):
        return self._collect_easyocr_detections(cv_image, advanced=advanced)

    def _collect_manga_detections(self, cv_image, settings, advanced=False):
        if not self.manga_ocr_reader:
            return []

        use_easy = settings.get('manga_use_easy_detection', True)
        if use_easy:
            regions = self._collect_easy_detection_regions(cv_image, advanced=advanced)
        else:
            regions = self._collect_morphological_regions(cv_image, advanced=advanced)

        results = []
        for text, polygon in regions:
            recognized = self._recognize_polygon(cv_image, polygon, 'Manga-OCR', settings)
            results.append((recognized or text, polygon))
        return results

    def _collect_tesseract_native_detections(self, cv_image, lang_code):
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        try:
            config_str = '--oem 1 --psm 3'
            writable_path = get_writable_tessdata_path()
            if writable_path and os.path.exists(writable_path):
                config_str += f' --tessdata-dir "{writable_path}"'
            data = pytesseract.image_to_data(gray, lang=lang_code, config=config_str, output_type=pytesseract.Output.DICT)
        except Exception as e:
            print(f"Tesseract detection error: {e}")
            return []

        blocks = {}
        for i in range(len(data['text'])):
            text = (data['text'][i] or '').strip()
            if not text:
                continue
            try:
                conf = float(data['conf'][i])
            except ValueError:
                conf = 0.0
            if conf < 45:
                continue
            block_key = (data.get('page_num', [0])[i], data['block_num'][i])
            rect = QRect(data['left'][i], data['top'][i], data['width'][i], data['height'][i])
            blocks.setdefault(block_key, {'texts': [], 'rects': []})
            blocks[block_key]['texts'].append(text)
            blocks[block_key]['rects'].append(rect)

        results = []
        for info in blocks.values():
            if not info['texts']:
                continue
            combined_text = ' '.join(info['texts'])
            union_rect = info['rects'][0]
            for rect in info['rects'][1:]:
                union_rect = union_rect.united(rect)
            polygon = QPolygon([
                QPoint(union_rect.left(), union_rect.top()),
                QPoint(union_rect.right(), union_rect.top()),
                QPoint(union_rect.right(), union_rect.bottom()),
                QPoint(union_rect.left(), union_rect.bottom()),
            ])
            results.append((combined_text, polygon))
        return results

    def _collect_tesseract_advanced_detections(self, cv_image, settings, advanced=False):
        if settings.get('tesseract_use_easy_detection', True):
            regions = self._collect_easy_detection_regions(cv_image, advanced=advanced)
            results = []
            for _, polygon in regions:
                text = self._recognize_polygon(cv_image, polygon, 'Tesseract', settings)
                results.append((text, polygon))
            return results
        return self._collect_tesseract_native_detections(cv_image, settings.get('ocr_lang') or 'eng')

    def _filter_detection_noise(self, items, image_shape, advanced=False):
        if not items:
            return []
        h, w = image_shape[:2]
        min_area_ratio = 0.00004 if advanced else 0.00003
        min_area = max(80, min_area_ratio * w * h)
        max_area_ratio = 0.85 if advanced else 0.9
        filtered = []
        for text, polygon in items:
            cleaned = self._clean_detected_text(text)
            if not cleaned:
                continue
            if len(cleaned) <= 1 and not cleaned.isalnum():
                continue
            if re.fullmatch(r'[\W_]+', cleaned):
                continue
            letters = sum(ch.isalpha() for ch in cleaned)
            digits = sum(ch.isdigit() for ch in cleaned)
            if advanced:
                if letters == 0 and digits == 0 and len(cleaned) <= 3:
                    continue
                if re.fullmatch(r'[!\?\-•°??????]+', cleaned):
                    continue
                repeated = re.search(r'(.)\1{2,}', cleaned)
                if repeated and len(cleaned) <= 5:
                    if repeated.group(1) != '~':
                        continue
            unique_chars = set(cleaned)
            if len(unique_chars) == 1 and cleaned[0] in "!?…??????#@*/":
                continue
            punctuation = sum(1 for ch in cleaned if not ch.isalnum() and not ch.isspace())
            if advanced and punctuation / max(1, len(cleaned)) > 0.6:
                continue

            rect = polygon.boundingRect()
            area = rect.width() * rect.height()
            if area < min_area:
                continue
            if area > w * h * max_area_ratio:
                continue
            if rect.width() < 6 or rect.height() < 6:
                continue
            aspect_ratio = rect.width() / max(1, rect.height())
            if advanced and (aspect_ratio > 9.0 or aspect_ratio < 0.12):
                continue

            filtered.append((cleaned, self._clamp_polygon(polygon, w, h)))
        return filtered

    def _clean_detected_text(self, text):
        if not text:
            return ''
        cleaned = re.sub(r'\s+', ' ', text)
        return cleaned.strip()

    def _tighten_detection_polygons(self, cv_image, items):
        if not items:
            return []
        h, w = cv_image.shape[:2]
        refined = []
        for text, polygon in items:
            refined_polygon = self._refine_polygon_with_image(cv_image, polygon)
            refined.append((text, self._clamp_polygon(refined_polygon, w, h)))
        return refined

    def detect_panels_yolo(self):
        if not self.current_image_path:
            self.show_banner("panel-detect-no-image", "No image", "Buka gambar manga terlebih dahulu.", kind="warning")
            return

        model_path = self.panel_model_path_input.text().strip()
        if not model_path:
            model_path = os.path.join(ROOT_DIR, "src", "models", "manga_panel_detector_fp32.pt")
        
        # Jika file model belum ada, lakukan download otomatis!
        if not os.path.exists(model_path):
            reply = QMessageBox.question(
                self,
                "Download Model",
                "Model YOLO26 panel detector tidak ditemukan.\nApakah Anda ingin mengunduhnya secara otomatis dari Hugging Face (~10MB)?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.download_panel_model(model_path, self.detect_panels_yolo)
                return
            else:
                return

        from src.core.config import YOLO
        if YOLO is None:
            self.show_banner("panel-detect-dependency", "Dependency error", "Pustaka 'ultralytics' (YOLO) tidak terpasang atau tidak terdeteksi.", kind="error")
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.statusBar().showMessage("Menjalankan deteksi panel dengan YOLO...")
        QApplication.processEvents()

        try:
            cv_img = cv2.imread(self.current_image_path)
            if cv_img is None:
                raise Exception("Gagal membaca file gambar.")

            use_gpu = self.use_gpu_checkbox.isChecked() and self.is_gpu_available
            device = "cuda" if use_gpu else "cpu"
            
            model = YOLO(model_path)
            results = model(cv_img, verbose=False, device=device)
            
            detected_rects = []
            if results and results[0].boxes is not None:
                for box in results[0].boxes:
                    xyxy = box.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])
                    # Class 0: panel, Class 1: text
                    # Hanya ambil objek jika kelasnya adalah panel (0)
                    cls_id = int(box.cls[0].cpu().numpy())
                    if cls_id == 0:
                        detected_rects.append(QRect(x1, y1, x2 - x1, y2 - y1))
            
            self.detected_panels = detected_rects
            self.statusBar().showMessage(f"Berhasil mendeteksi {len(detected_rects)} panel.", 3000)
            
            self.show_panels_checkbox.setChecked(True)
            self.image_label.update()
            
            if detected_rects:
                reply = QMessageBox.question(
                    self,
                    "Sort RTL",
                    f"Ditemukan {len(detected_rects)} panel. Apakah Anda ingin langsung mengurutkan balon teks berdasarkan urutan baca RTL?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.sort_areas_rtl()
            else:
                self.show_toast("Deteksi selesai", "Tidak ditemukan panel pada halaman ini.", kind="info")

        except Exception as e:
            self.show_banner("panel-detect-error", "Panel detection failed", f"Gagal mendeteksi panel: {e}", kind="error")
        finally:
            QApplication.restoreOverrideCursor()

    def detect_panels_opencv_fallback(self):
        if not self.current_image_path:
            return []
        try:
            cv_img = cv2.imread(self.current_image_path)
            if cv_img is None:
                return []
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            panels = []
            h, w = gray.shape
            min_panel_area = (h * w) * 0.01
            max_panel_area = (h * w) * 0.95
            
            for cnt in contours:
                x, y, gw, gh = cv2.boundingRect(cnt)
                area = gw * gh
                if min_panel_area < area < max_panel_area:
                    rect = QRect(x, y, gw, gh)
                    is_dup = False
                    for p in panels:
                        intersect = p.intersected(rect)
                        if intersect.width() * intersect.height() > 0.8 * area:
                            is_dup = True
                            break
                    if not is_dup:
                        panels.append(rect)
            
            return panels
        except Exception as e:
            print(f"Error in OpenCV panel detection fallback: {e}")
            return []
