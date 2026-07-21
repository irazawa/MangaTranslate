"""Method domain batch, dipindahkan utuh dari main_window.py.

Fase 1 pemecahan monolit: isi method tidak diubah sama sekali.
Mixin ini hanya berguna sebagai bagian dari MangaOCRApp -- ia mengandalkan
atribut yang dibuat di MangaOCRApp.__init__.
"""

from PyQt5.QtCore import QThread, Qt
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox


class BatchMixin:
    def batch_pf_contextual_translate(self):
        """
        Batch send all PF entries (original text only) to AI for contextual translation.
        Result: Each bubble gets updated with contextual translation.
        """
        if not self.proofreader_entries:
            self.show_toast("No PF entries", "Tidak ada entry PF yang bisa diproses.", kind="info")
            return
        provider, model_name = self.get_selected_model_name()
        if not model_name:
            self.show_banner("batch-pf-no-model", "AI model missing", "Pilih AI model dulu sebelum batch PF.", kind="warning")
            return
        # Build prompt: send all original texts, ask AI to translate contextually so text flows naturally
        pf_texts = [e.get('original_text', '') for e in self.proofreader_entries if e.get('original_text')]
        if not pf_texts:
            self.show_toast("No texts", "Tidak ada original text di PF entries.", kind="info")
            return
        # Request JSON array first to make parsing reliable
        prompt = (
            "IMPORTANT: Return ONLY a JSON array of strings. Example: [\"dialog1\", \"dialog2\"]\n"
            "Terjemahkan dialog berikut ke bahasa Indonesia secara kontekstual sehingga hasilnya saling nyambung dan alami. "
            "Berikan hasil terjemahan dalam urutan yang sama. Jika tidak bisa mengekspor JSON, kembalikan teks setiap dialog pada baris terpisah.\n\n" +
            "\n".join(pf_texts)
        )
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            temperature = 0.35
            response_text = self._invoke_ai_review(provider, model_name, prompt, temperature=temperature)
        finally:
            QApplication.restoreOverrideCursor()
        if not response_text:
            self.show_banner("batch-pf-ai-error", "AI error", "Tidak ada respon dari AI.", kind="error")
            return
        # Parse response: get list of results
        results = self._parse_ai_list_response(response_text, expected_count=len(pf_texts))
        if len(results) != len(pf_texts):
            resp = QMessageBox.question(self, "Mismatch",
                                        f"AI mengembalikan {len(results)} item, tapi jumlah dialog yang dikirim {len(pf_texts)}.\n"
                                        "Terima hasil yang dapat diambil terbaik (best-effort mapping) dan lanjutkan?",
                                        QMessageBox.Yes | QMessageBox.No)
            if resp != QMessageBox.Yes:
                return
            if len(results) > len(pf_texts):
                results = results[:len(pf_texts)]
            else:
                results = results + [orig for orig in pf_texts[len(results):]]

        # Stage results: set translated_text, ai_model and staged flag, but do NOT apply to bubbles yet
        for entry, new_text in zip(self.proofreader_entries, results):
            entry['translated_text'] = new_text
            entry['ai_model'] = model_name
            entry['staged'] = True

    def batch_qc_style_tone_check(self):
        """
        Batch send all QC entries (translated text) to AI for style/tone validation.
        Result: Each bubble gets updated with validated/adjusted translation.
        """
        if not self.quality_entries:
            self.show_toast("No QC entries", "Tidak ada entry QC yang bisa diproses.", kind="info")
            return
        provider, model_name = self.get_selected_model_name()
        if not model_name:
            self.show_banner("batch-qc-no-model", "AI model missing", "Pilih AI model dulu sebelum batch QC.", kind="warning")
            return
        qc_texts = [e.get('translated_text', '') for e in self.quality_entries if e.get('translated_text')]
        if not qc_texts:
            self.show_toast("No texts", "Tidak ada hasil translate di QC entries.", kind="info")
            return
        prompt = (
            "IMPORTANT: Return ONLY a JSON array of strings. Example: [\"rev1\", \"rev2\"]\n"
            "Berikut adalah hasil terjemahan dialog manga. Tolong cek gaya bahasa, suasana, dan tone agar sesuai dan alami. "
            "Jika perlu, sesuaikan gaya bahasa agar konsisten dan cocok dengan konteks manga. Berikan hasil revisi dalam urutan yang sama.\n\n" +
            "\n".join(qc_texts)
        )
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            temperature = 0.3
            response_text = self._invoke_ai_review(provider, model_name, prompt, temperature=temperature)
        finally:
            QApplication.restoreOverrideCursor()
        if not response_text:
            self.show_banner("batch-qc-ai-error", "AI error", "Tidak ada respon dari AI.", kind="error")
            return
        results = self._parse_ai_list_response(response_text, expected_count=len(qc_texts))
        if len(results) != len(qc_texts):
            resp = QMessageBox.question(self, "Mismatch",
                                        f"AI mengembalikan {len(results)} item, tapi jumlah dialog yang dikirim {len(qc_texts)}.\n"
                                        "Terima hasil yang dapat diambil terbaik (best-effort mapping) dan lanjutkan?",
                                        QMessageBox.Yes | QMessageBox.No)
            if resp != QMessageBox.Yes:
                return
            if len(results) > len(qc_texts):
                results = results[:len(qc_texts)]
            else:
                results = results + [orig for orig in qc_texts[len(results):]]
        for entry, new_text in zip(self.quality_entries, results):
            entry['translated_text'] = new_text
            entry['ai_model'] = model_name
            entry['staged'] = True

        self.refresh_history_views()
        self.show_toast("Batch QC selesai", "Hasil telah di-stage. Tekan 'Confirm' pada baris untuk menerapkan ke bubble.", kind="success", timeout_ms=5000)

    def on_batch_mode_changed(self, state):
        is_checked = (state == Qt.Checked)
        self.process_batch_button.setVisible(is_checked)
        if not is_checked and self.batch_processing_queue:
            reply = QMessageBox.question(self, 'Clear Batch Queue?',
                                           f"You have {len(self.batch_processing_queue)} items in the batch. Do you want to process them now? \n\nChoosing 'No' will discard them.",
                                           QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.Yes: self.start_batch_processing()
            else: self.batch_processing_queue.clear(); self.update_batch_button_text()

    def add_to_batch_queue(self, job):
        self.batch_processing_queue.append(job); self.update_batch_button_text()
        self.statusBar().showMessage(f"Added to batch. Queue has {len(self.batch_processing_queue)} items.")
        if len(self.batch_processing_queue) >= self.BATCH_SIZE_LIMIT:
            self.statusBar().showMessage(f"Batch limit of {self.BATCH_SIZE_LIMIT} reached. Processing automatically...")
            self.start_batch_processing()

    def update_batch_button_text(self):
        count = len(self.batch_processing_queue)
        self.process_batch_button.setText(f"Process Batch Now ({count} items)")
        self.process_batch_button.setEnabled(count > 0)

    def start_batch_processing(self):
        if not self.batch_processing_queue: return
        if self.batch_processor_thread and self.batch_processor_thread.isRunning():
            self.show_toast("Batch busy", "A batch is already being processed.", kind="info"); return

        self.statusBar().showMessage(f"Starting to process batch of {len(self.batch_processing_queue)} items...")

        queue_to_process = self.batch_processing_queue[:]; self.batch_processing_queue.clear(); self.update_batch_button_text()

        settings = self.get_current_settings()
        self.batch_processor_thread = QThread()
        self.batch_processor_worker = BatchProcessorWorker(self, queue_to_process, settings)
        self.batch_processor_worker.moveToThread(self.batch_processor_thread)
        self.batch_processor_worker.signals.batch_job_complete.connect(self.on_queue_job_complete) # Re-use the single job complete handler
        self.batch_processor_worker.signals.batch_finished.connect(self.on_api_batch_finished)
        self.batch_processor_worker.signals.error.connect(self.on_worker_error)
        self.batch_processor_thread.started.connect(self.batch_processor_worker.run)
        self.batch_processor_thread.finished.connect(self.batch_processor_thread.deleteLater)
        self.batch_processor_thread.start()

    def on_api_batch_finished(self):
        self.statusBar().showMessage("Batch processing finished.", 5000)
        self.batch_processor_thread.quit()
        self.show_toast("Batch translate complete", "Proses batch translation untuk halaman yang dipilih telah selesai.", kind="success")
        self.show_desktop_notification("Batch Translate Selesai", "Proses batch translation untuk halaman yang dipilih telah selesai.")

    def start_interactive_batch_detection(self):
        # [DIUBAH] Deteksi hanya berjalan pada halaman yang sedang aktif, bukan seluruh folder
        if self.current_image_pil is None:
            self.show_banner("batch-detect-no-files", "No page loaded", "Buka gambar atau halaman PDF terlebih dahulu untuk menggunakan fitur ini.", kind="warning")
            return

        if self.detection_thread and self.detection_thread.isRunning():
            self.show_toast("Detection busy", "A detection process is already running.", kind="info")
            return

        # [DIUBAH] Menggunakan mode deteksi yang dipilih user
        detection_mode = "Text" if self.text_detect_radio.isChecked() else "Bubble"

        settings = self.get_current_settings()
        if detection_mode == "Bubble" and not self._ensure_bubble_model_ready(settings):
            return

        self.detected_items_map.clear()
        self.last_detection_mode = detection_mode
        self.preview_mode_active = False
        self.set_ui_for_detection(True)

        settings['batch_text_detection_enabled'] = (detection_mode == "Text")
        jobs = [(self.get_current_data_key(), self.current_image_pil.copy())]
        self.detection_thread = QThread()
        self.detection_worker = AutoDetectorWorker(self, jobs, settings, detection_mode)
        self.detection_worker.moveToThread(self.detection_thread)
        self.detection_worker.signals.detection_complete.connect(self.on_detection_complete)
        self.detection_worker.signals.overall_progress.connect(self.update_overall_progress)
        self.detection_worker.signals.error.connect(self.on_worker_error)
        self.detection_worker.signals.finished.connect(self.on_detection_finished)
        self.detection_thread.started.connect(self.detection_worker.run)
        self.detection_thread.start()

    def cancel_interactive_batch(self):
        if self.detection_worker: self.detection_worker.cancel()
        if self.detection_thread: self.detection_thread.quit(); self.detection_thread.wait()

        self.detection_thread = None; self.detection_worker = None
        self.detected_items_map.clear(); self.image_label.clear_detected_items()
        self.set_ui_for_detection(False); self.set_ui_for_confirmation(False)
        self.preview_mode_active = False
        self.cancel_detection_button.setText("Cancel Detection")
        self.cancel_detection_button.setVisible(False)
        self.statusBar().showMessage("Batch detection cancelled.", 3000)

    def open_batch_save_dialog(self):
        if not self.image_files:
            self.show_banner("batch-save-no-folder", "No folder loaded", "Please load a folder to use the batch save feature.", kind="warning")
            return

        dialog = BatchSaveDialog(self.image_files, self)
        if dialog.exec_() == QDialog.Accepted:
            files_to_save = dialog.get_selected_files()
            if files_to_save: self.execute_batch_save(files_to_save)
            else: self.show_toast("No files selected", "No files were selected to save.", kind="info")

    def execute_batch_save(self, files_to_save):
        if self.batch_save_thread and self.batch_save_thread.isRunning():
            self.show_toast("Batch save in progress", "A batch save process is already running.", kind="info")
            return

        # Get settings
        gen_cfg = SETTINGS.get('general', {})
        save_fmt = gen_cfg.get('save_format', 'PNG')
        save_qual = int(gen_cfg.get('save_quality', -1))

        self.overall_progress_bar.setVisible(True); self.overall_progress_bar.setValue(0)
        self.statusBar().showMessage("Starting batch save...")
        self._batch_save_errors = []
        self._batch_save_saved_count = 0

        # Get current settings dictionary on the main GUI thread safely
        current_settings = self.get_current_settings()

        # Prepare a clean copy of the needed typeset data
        typeset_data_snapshot = {}
        for path in files_to_save:
            key = self.get_current_data_key(path=path)
            if key in self.all_typeset_data:
                record = self.all_typeset_data[key]
                typeset_data_snapshot[key] = {
                    'areas': list(record.get('areas', []))
                }
                if record.get('cleaned_image_png'):
                    typeset_data_snapshot[key]['cleaned_image_png'] = record.get('cleaned_image_png')

        self.batch_save_thread = QThread()
        self.batch_save_worker = BatchSaveWorker(
            self,
            files_to_save,
            fmt=save_fmt,
            quality=save_qual,
            settings=current_settings,
            typeset_data=typeset_data_snapshot
        )
        self.batch_save_worker.moveToThread(self.batch_save_thread)
        self.batch_save_worker.signals.progress.connect(self.update_overall_progress)
        self.batch_save_worker.signals.file_saved.connect(self.on_batch_file_saved)
        self.batch_save_worker.signals.error.connect(self.on_batch_save_error)
        self.batch_save_worker.signals.finished.connect(self.on_batch_save_finished)
        self.batch_save_thread.started.connect(self.batch_save_worker.run)
        self.batch_save_thread.start()

    def on_batch_file_saved(self, file_path):
        self._batch_save_saved_count += 1

    def on_batch_save_error(self, error_msg):
        self._batch_save_errors.append(error_msg)
        self.show_banner("batch-save-error-live", "Batch save issue", error_msg, kind="warning")

    def on_batch_save_finished(self):
        errors = list(getattr(self, '_batch_save_errors', []))
        saved_count = getattr(self, '_batch_save_saved_count', 0)
        if errors:
            self.statusBar().showMessage("Batch save finished with errors.", 5000)
        else:
            self.statusBar().showMessage("Batch save complete.", 5000)
        self.overall_progress_bar.setVisible(False)
        self.batch_save_thread.quit(); self.batch_save_thread.wait()
        if errors:
            shown_errors = "\n".join(errors[:8])
            more = "" if len(errors) <= 8 else f"\n...and {len(errors) - 8} more error(s)."
            self.show_banner(
                "batch-save-errors",
                "Batch Save Finished With Errors",
                f"Saved {saved_count} file(s), but {len(errors)} file(s) failed:\n\n{shown_errors}{more}",
                kind="warning",
            )
        else:
            self.dismiss_banner("batch-save-error-live")
            self.dismiss_banner("batch-save-errors")
            self.show_toast(
                "Batch Save Complete",
                f"All selected files have been saved. Saved file(s): {saved_count}",
                kind="success",
                timeout_ms=5000,
            )
