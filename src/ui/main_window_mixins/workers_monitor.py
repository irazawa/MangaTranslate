"""Mixin pemantau worker untuk MangaOCRApp.

Menyediakan registry aktivitas worker (tahap, model, durasi), watchdog deteksi
macet, mekanisme batalkan/paksa-hentikan, pelacak batch + estimasi selesai,
dan builder tab Workers. Data disajikan oleh src/ui/workers_panel.py.
"""

import time
from collections import deque

from PyQt5.QtCore import QTimer

from src.ui import theme
from src.ui.icons import app_icon
from src.ui.texts import ActionText
from src.ui.workers_panel import WorkersPanel, format_duration

# Worker dianggap macet jika tidak ganti tahap selama sebanyak ini
WORKER_STUCK_SECONDS = 120

_STAGE_LABELS = {
    'job': 'Menyiapkan',
    'ocr': 'OCR',
    'translate': 'Translate',
    'api_wait': 'Tunggu API',
}


class WorkersMonitorMixin:
    """Registry + watchdog + aksi kill untuk semua worker antrian/batch."""

    def setup_workers_monitor(self):
        self._worker_activity = {}      # worker_id -> info tahap berjalan
        self._job_durations = deque(maxlen=30)  # durasi job (detik) untuk ETA
        self._batch_run = None          # info batch yang sedang berjalan
        self._zombie_threads = []       # thread paksa-henti yang belum mati
        self._stuck_banner_keys = set()
        self.worker_watchdog_timer = QTimer(self)
        self.worker_watchdog_timer.setInterval(1000)
        self.worker_watchdog_timer.timeout.connect(self._workers_watchdog_tick)
        self.worker_watchdog_timer.start()

    # --- Builder tab (dipanggil uibuild via tab_defs) ---
    def _create_workers_tab(self):
        self.workers_panel = WorkersPanel(self)
        return self.workers_panel

    # --- Slot sinyal worker ---
    def on_worker_stage(self, worker_id, key, detail, model):
        now = time.time()
        info = self._worker_activity.get(worker_id)
        if info is None:
            self._worker_activity[worker_id] = {
                'stage': key, 'detail': detail, 'model': model,
                'since': now, 'job_started_at': now, 'job_label': detail if key == 'job' else '',
            }
            return
        if key == 'job':
            # Job baru pada worker yang sama -> catat durasi job sebelumnya untuk ETA
            if info.get('stage') != 'job':
                self._job_durations.append(max(0.5, now - info.get('job_started_at', now)))
            info['job_started_at'] = now
            info['job_label'] = detail
        info['stage'] = key
        info['detail'] = detail
        info['model'] = model
        info['since'] = now

    def on_batch_progress(self, done, total, current, model):
        run = self._batch_run
        if run is None:
            return
        now = time.time()
        if done > run.get('done', 0) and done < total:
            run['durations'].append(max(0.5, now - run.get('last_emit_at', now)))
        run['done'] = max(run.get('done', 0), done)
        run['current'] = current
        run['model'] = model
        run['last_emit_at'] = now

    # --- Watchdog ---
    def _workers_watchdog_tick(self):
        now = time.time()

        # Bersihkan thread sisa paksa-henti yang sudah benar-benar mati
        alive_zombies = []
        for thread in self._zombie_threads:
            try:
                if thread.isRunning():
                    alive_zombies.append(thread)
                else:
                    thread.deleteLater()
            except RuntimeError:
                pass  # wrapper C++ sudah dihapus
        self._zombie_threads = alive_zombies

        # Registry hanya untuk worker yang masih hidup
        for wid in list(self._worker_activity.keys()):
            if wid not in self.worker_pool:
                del self._worker_activity[wid]

        stuck_workers = []
        for wid, info in self._worker_activity.items():
            elapsed = now - info.get('since', now)
            info['elapsed'] = elapsed
            is_stuck = elapsed > WORKER_STUCK_SECONDS and info.get('stage') in ('job', 'ocr', 'translate')
            info['stuck'] = is_stuck
            if is_stuck:
                stuck_workers.append((wid, info))
            else:
                key = f"worker-stuck-{wid}"
                if key in self._stuck_banner_keys:
                    self._stuck_banner_keys.discard(key)
                    self.dismiss_banner(key)

        # Efisiensi antrian: worker macet di translate jangan blokir item berikutnya.
        # Spawn worker cadangan (cap MAX_WORKERS) agar antrian tetap mengalir.
        try:
            queue_size = self.get_queue_length()
        except Exception:
            queue_size = 0
        if queue_size > 0 and len(self.worker_pool) < self.MAX_WORKERS:
            if any(i.get('stage') == 'translate' for _, i in stuck_workers):
                self.start_worker()

        for wid, info in stuck_workers:
            key = f"worker-stuck-{wid}"
            if key not in self._stuck_banner_keys:
                self._stuck_banner_keys.add(key)
                detail = info.get('detail') or '-'
                self.show_banner(
                    key, "Worker macet",
                    f"Worker #{wid} tidak ada progres {format_duration(info['elapsed'])} "
                    f"di tahap {_STAGE_LABELS.get(info['stage'], info['stage'])} ({detail}).",
                    kind="warning",
                    action_text="Hentikan Paksa",
                    action=lambda w=wid: self.force_kill_worker(w),
                )

        panel = getattr(self, 'workers_panel', None)
        if panel is not None:
            panel.refresh_view()

    # --- Aksi per worker (dipanggil dari tab Workers) ---
    def cancel_worker(self, worker_id):
        entry = self.worker_pool.get(worker_id)
        if not entry:
            return
        thread, worker = entry
        try:
            worker.stop()
        except RuntimeError:
            return
        self.show_toast("Batalkan worker", f"Worker #{worker_id} berhenti setelah tugas berjalan selesai.", kind="info")

    def force_kill_worker(self, worker_id):
        entry = self.worker_pool.get(worker_id)
        if not entry:
            return
        thread, worker = entry
        try:
            worker.stop()
        except RuntimeError:
            pass
        thread.terminate()
        try:
            if thread.wait(2000):
                thread.deleteLater()
                try:
                    worker.deleteLater()
                except RuntimeError:
                    pass
            else:
                self._zombie_threads.append(thread)
        except RuntimeError:
            pass
        self.worker_pool.pop(worker_id, None)
        self._worker_activity.pop(worker_id, None)
        key = f"worker-stuck-{worker_id}"
        self._stuck_banner_keys.discard(key)
        self.dismiss_banner(key)
        self.update_active_workers_label()
        self.show_toast("Worker dihentikan paksa", f"Worker #{worker_id} diterminasi. Item kerjanya bisa diulang.", kind="warning")

    def cancel_full_page_translation(self):
        worker = getattr(self, '_full_page_worker', None)
        if worker is not None and worker.isRunning():
            if hasattr(worker, 'cancel'):
                worker.cancel()
            else:
                worker._is_cancelled = True
            self.show_toast("Batalkan full-page", "Full-page translation dibatalkan pada halaman berjalan.", kind="info")

    def force_kill_full_page_translation(self):
        worker = getattr(self, '_full_page_worker', None)
        if worker is None or not worker.isRunning():
            return
        worker.terminate()
        if not worker.wait(2000):
            self._zombie_threads.append(worker)
        else:
            self._full_page_worker = None
        if hasattr(self, '_close_full_page_progress_dialog'):
            self._close_full_page_progress_dialog()
        btn = getattr(self, 'auto_translate_page_btn', None)
        if btn is not None:
            btn.setText(ActionText.FULL_PAGE_TRANSLATE)
            btn.setIcon(app_icon("rocket", theme.COLORS['bg'], size=15))
            btn.setEnabled(True)
        self.show_toast("Full-page dihentikan paksa", "Thread full-page translation diterminasi.", kind="warning")

    def cancel_batch_job(self):
        worker = getattr(self, 'batch_processor_worker', None)
        if worker is None:
            return
        try:
            if not self.batch_processor_thread.isRunning():
                return
        except RuntimeError:
            return
        worker.cancel()
        self.show_toast("Batalkan batch", "Batch dihentikan setelah halaman berjalan selesai.", kind="info")

    def force_kill_batch(self):
        thread = getattr(self, 'batch_processor_thread', None)
        worker = getattr(self, 'batch_processor_worker', None)
        if thread is None:
            return
        try:
            if not thread.isRunning():
                return
        except RuntimeError:
            return
        if worker is not None:
            try:
                worker.cancel()
            except RuntimeError:
                pass
        thread.terminate()
        if not thread.wait(2000):
            self._zombie_threads.append(thread)
        self._batch_run = None
        self.show_toast("Batch dihentikan paksa", "Thread batch processor diterminasi.", kind="warning")
