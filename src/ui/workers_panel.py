"""Tab Workers: monitor worker aktif, antrian, batch, dan aksi hentikan.

Panel ini membaca state dari WorkersMonitorMixin (main window) dan menyegarkan
tampilan tiap detik lewat watchdog tick. Baris tabel di-update in-place agar
tombol aksi tidak ikut ter-rebuild setiap tick.
"""

import os
import time

from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)
from PyQt5.QtCore import Qt

from src.ui import theme
from src.ui.texts import WorkersText as WT

_STAGE_FALLBACK = "Menunggu"


def estimate_eta(durations, remaining):
    """Estimasi sisa detik dari durasi unit-unit selesai (detik). None jika tidak ada data."""
    if remaining <= 0:
        return 0
    if not durations:
        return None
    avg = sum(durations) / len(durations)
    return avg * remaining


def format_duration(seconds):
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}j {m}m {s}d"
    if m:
        return f"{m}m {s}d"
    return f"{s}d"


def _item(text, color=None):
    item = QTableWidgetItem(str(text) if text not in (None, '') else "—")
    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
    if color:
        item.setForeground(QColor(color))
    return item


def _stage_text(info):
    stage = info.get('stage', '')
    label = WT.STAGE_LABELS.get(stage, stage or _STAGE_FALLBACK)
    detail = info.get('detail') or ''
    return f"{label} · {detail}" if detail and stage != 'job' else (detail or label)


class WorkersPanel(QWidget):
    def __init__(self, window):
        super().__init__()
        self._win = window
        self._worker_rows = {}       # key (worker_id | 'fullpage') -> row index
        self._queue_signature = None
        self._init_ui()

    # ------------------------------------------------------------------ UI
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(12)

        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        hint = QLabel(WT.HINT)
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {theme.COLORS['muted']}; font-size: 9pt;")
        layout.addWidget(hint)

        layout.addWidget(QLabel(WT.WORKERS_SECTION))
        self.worker_table = QTableWidget(0, 7)
        self.worker_table.setHorizontalHeaderLabels(
            [WT.COL_WORKER, WT.COL_TASK, WT.COL_STAGE, WT.COL_MODEL, WT.COL_DURATION, WT.COL_STATUS, WT.COL_ACTION])
        self.worker_table.verticalHeader().setVisible(False)
        self.worker_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.worker_table.setSelectionMode(QTableWidget.NoSelection)
        self.worker_table.setFocusPolicy(Qt.NoFocus)
        self.worker_table.setStyleSheet(theme.table_qss() + theme.table_header_qss())
        self.worker_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.worker_table)

        layout.addWidget(QLabel(WT.QUEUE_SECTION))
        self.queue_table = QTableWidget(0, 3)
        self.queue_table.setHorizontalHeaderLabels([WT.COL_INDEX, WT.COL_ITEM, WT.COL_MODEL])
        self.queue_table.verticalHeader().setVisible(False)
        self.queue_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.queue_table.setSelectionMode(QTableWidget.NoSelection)
        self.queue_table.setFocusPolicy(Qt.NoFocus)
        self.queue_table.setStyleSheet(theme.table_qss() + theme.table_header_qss())
        self.queue_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.queue_table)

        layout.addWidget(QLabel(WT.BATCH_SECTION))
        self.batch_card = QFrame()
        self.batch_card.setStyleSheet(theme.card_qss())
        batch_layout = QVBoxLayout(self.batch_card)
        batch_layout.setContentsMargins(12, 10, 12, 10)
        batch_layout.setSpacing(8)

        self.batch_status_label = QLabel("")
        self.batch_status_label.setWordWrap(True)
        batch_layout.addWidget(self.batch_status_label)

        self.batch_progress = QProgressBar()
        self.batch_progress.setStyleSheet(theme.progress_bar_qss())
        self.batch_progress.setRange(0, 100)
        batch_layout.addWidget(self.batch_progress)

        self.batch_detail_label = QLabel("")
        self.batch_detail_label.setWordWrap(True)
        batch_layout.addWidget(self.batch_detail_label)

        batch_btn_row = QHBoxLayout()
        self.batch_cancel_btn = QPushButton(WT.BTN_CANCEL_BATCH)
        self.batch_cancel_btn.setStyleSheet(theme.secondary_button_qss())
        self.batch_cancel_btn.clicked.connect(self._win.cancel_batch_job)
        self.batch_force_btn = QPushButton(WT.BTN_FORCE_BATCH)
        self.batch_force_btn.setStyleSheet(theme.danger_button_qss())
        self.batch_force_btn.clicked.connect(self._win.force_kill_batch)
        batch_btn_row.addWidget(self.batch_cancel_btn)
        batch_btn_row.addWidget(self.batch_force_btn)
        batch_btn_row.addStretch()
        batch_layout.addLayout(batch_btn_row)
        layout.addWidget(self.batch_card)

        layout.addStretch()

    # ------------------------------------------------------------- helpers
    def _queue_snapshot(self):
        win = self._win
        try:
            win.queue_mutex.lock()
            return list(win.processing_queue)
        except Exception:
            return []
        finally:
            try:
                win.queue_mutex.unlock()
            except Exception:
                pass

    def _collect_worker_rows(self):
        """Kembalikan list (key, info) untuk tabel worker, termasuk full-page."""
        win = self._win
        rows = []
        activity = getattr(win, '_worker_activity', {})
        for wid in sorted(getattr(win, 'worker_pool', {}).keys()):
            info = dict(activity.get(wid) or {})
            info.setdefault('stage', 'job')
            rows.append((wid, info))
        fp = getattr(win, '_full_page_worker', None)
        if fp is not None:
            try:
                if fp.isRunning():
                    rows.append(('fullpage', {
                        'stage': 'translate', 'detail': '', 'model': '',
                        'since': None, 'job_started_at': None,
                        'job_label': WT.FULLPAGE_TASK, 'fullpage': True,
                    }))
            except RuntimeError:
                pass
        return rows

    def _make_action_cell(self, key, info):
        container = QWidget()
        row_layout = QHBoxLayout(container)
        row_layout.setContentsMargins(2, 2, 2, 2)
        row_layout.setSpacing(4)
        cancel_btn = QPushButton(WT.BTN_CANCEL)
        cancel_btn.setStyleSheet(theme.secondary_button_qss())
        force_btn = QPushButton(WT.BTN_FORCE)
        force_btn.setStyleSheet(theme.danger_button_qss())
        if key == 'fullpage':
            cancel_btn.clicked.connect(self._win.cancel_full_page_translation)
            force_btn.clicked.connect(self._win.force_kill_full_page_translation)
        else:
            cancel_btn.clicked.connect(lambda _=False, w=key: self._win.cancel_worker(w))
            force_btn.clicked.connect(lambda _=False, w=key: self._win.force_kill_worker(w))
        row_layout.addWidget(cancel_btn)
        row_layout.addWidget(force_btn)
        row_layout.addStretch()
        force_btn.setVisible(bool(info.get('stuck')) or key == 'fullpage')
        container._force_btn = force_btn  # akses saat update status
        return container

    def _rebuild_worker_table(self, rows):
        table = self.worker_table
        table.setRowCount(0)
        self._worker_rows = {}
        for row_idx, (key, _info) in enumerate(rows):
            table.insertRow(row_idx)
            for col in range(7):
                table.setItem(row_idx, col, _item(""))
            table.setCellWidget(row_idx, 6, self._make_action_cell(key, _info))
            self._worker_rows[key] = row_idx

    # ------------------------------------------------------------- refresh
    def refresh_view(self, force=False):
        if not force and not self.isVisible():
            return
        win = self._win
        now = time.time()

        rows = self._collect_worker_rows()
        if set(self._worker_rows.keys()) != {key for key, _ in rows}:
            self._rebuild_worker_table(rows)

        stuck_count = 0
        for key, info in rows:
            row = self._worker_rows.get(key)
            if row is None:
                continue
            if info.get('stuck'):
                stuck_count += 1
            started = info.get('job_started_at') or info.get('since')
            duration = format_duration(now - started) if started else "—"
            self.worker_table.setItem(row, 0, _item(f"#{key}" if key != 'fullpage' else "FP"))
            self.worker_table.setItem(row, 1, _item(info.get('job_label') or "—"))
            self.worker_table.setItem(row, 2, _item(_stage_text(info)))
            self.worker_table.setItem(row, 3, _item(info.get('model') or "—"))
            self.worker_table.setItem(row, 4, _item(duration))
            if info.get('stuck'):
                status_text, status_color = WT.STATUS_STUCK, theme.COLORS['danger']
            elif info.get('stage') == 'api_wait':
                status_text, status_color = WT.STATUS_API_WAIT, theme.COLORS['warning']
            else:
                status_text, status_color = WT.STATUS_RUNNING, theme.COLORS['success']
            self.worker_table.setItem(row, 5, _item(status_text, status_color))
            cell = self.worker_table.cellWidget(row, 6)
            if cell is not None and hasattr(cell, '_force_btn'):
                cell._force_btn.setVisible(bool(info.get('stuck')) or key == 'fullpage')

        if not rows:
            self.worker_table.setRowCount(1)
            if self.worker_table.columnCount():
                span_item = _item(WT.EMPTY_WORKERS)
                self.worker_table.setItem(0, 0, span_item)
                try:
                    self.worker_table.setSpan(0, 0, 1, 7)
                except Exception:
                    pass
        else:
            try:
                self.worker_table.clearSpans()
            except Exception:
                pass

        # --- Tabel antrian ---
        queue = self._queue_snapshot()
        signature = (len(queue), tuple(os.path.basename(str(j.get('image_path', ''))) for j in queue[:5]))
        if signature != self._queue_signature:
            self._queue_signature = signature
            self.queue_table.setRowCount(0)
            for row_idx, job in enumerate(queue[:50]):
                self.queue_table.insertRow(row_idx)
                self.queue_table.setItem(row_idx, 0, _item(row_idx + 1))
                label = os.path.basename(str(job.get('image_path', '')))
                pre_text = job.get('text')
                if pre_text:
                    label = f"{label} · \"{str(pre_text)[:40]}\""
                self.queue_table.setItem(row_idx, 1, _item(label))
                settings = job.get('settings') or {}
                model = settings.get('ai_model_label')
                if not model and isinstance(settings.get('ai_model'), (tuple, list)):
                    model = " · ".join(str(part) for part in settings['ai_model'])
                self.queue_table.setItem(row_idx, 2, _item(model or "—"))
            if len(queue) > 50:
                extra_row = self.queue_table.rowCount()
                self.queue_table.insertRow(extra_row)
                self.queue_table.setItem(extra_row, 0, _item("…"))
                self.queue_table.setItem(extra_row, 1, _item(f"+{len(queue) - 50} item lagi"))
                self.queue_table.setItem(extra_row, 2, _item(""))

        # --- Ringkasan + ETA ---
        durations = list(getattr(win, '_job_durations', None) or [])
        active = len(rows)
        summary_parts = [f"{WT.WORKERS_SECTION}: {active}", f"{WT.QUEUE_SECTION}: {len(queue)}"]
        if durations:
            avg = sum(durations) / len(durations)
            summary_parts.append(WT.AVG_FMT.format(avg=format_duration(avg)))
            if queue:
                eta = estimate_eta(durations, len(queue))
                if eta is not None:
                    busy = max(1, active - stuck_count)
                    summary_parts.append(f"{WT.SUMMARY_ETA_FMT.format(eta=format_duration(eta / busy))}")
        self.summary_label.setText(" · ".join(summary_parts))

        # --- Kartu batch ---
        run = getattr(win, '_batch_run', None)
        if run:
            total = max(1, run.get('total', 0))
            done = run.get('done', 0)
            self.batch_card.setVisible(True)
            self.batch_status_label.setText(WT.BATCH_DONE_FMT.format(done=done, total=total))
            self.batch_progress.setValue(int(done * 100 / total))
            elapsed = now - run.get('started_at', now)
            detail_parts = [WT.BATCH_ELAPSED_FMT.format(elapsed=format_duration(elapsed))]
            eta = estimate_eta(run.get('durations') or [], max(0, total - done))
            if eta is not None:
                detail_parts.append(WT.BATCH_ETA_FMT.format(eta=format_duration(eta)))
            if run.get('current'):
                detail_parts.append(WT.BATCH_CURRENT_FMT.format(current=run['current']))
            if run.get('model'):
                detail_parts.append(run['model'])
            self.batch_detail_label.setText(" · ".join(detail_parts))
        else:
            self.batch_card.setVisible(True)
            self.batch_status_label.setText(WT.BATCH_IDLE)
            self.batch_progress.setValue(0)
            self.batch_detail_label.setText("")
