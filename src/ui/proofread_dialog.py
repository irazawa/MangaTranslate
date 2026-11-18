"""Chapter-wide sequential proofread & QC dialog for MangaTranslate."""

from __future__ import annotations

import os
from functools import partial

from PyQt5.QtCore import Qt, QSignalBlocker
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from src.core.prompts import format_heart_emoticon_lines
from src.ui import theme
from src.ui.icons import app_icon


class ChapterProofreadDialog(QDialog):
    """Sequential table view to proofread and edit all OCR & translated dialogue across a chapter."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent or main_window)
        self.main_window = main_window
        self._entries: list[dict] = []
        self._entry_by_uid: dict[tuple[str, int], dict] = {}
        self._pending_edits: dict[tuple[str, int], dict[str, str]] = {}
        self._populating_table = False

        self.setWindowTitle("Chapter Proofread & QC")
        self.setWindowIcon(app_icon("check", theme.COLORS["accent"], 16))
        self.resize(1040, 680)
        self._apply_theme_qss()
        self._build_ui()
        self.reload_chapter_entries()

    def _apply_theme_qss(self):
        c = theme.COLORS
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {c['bg']};
                color: {c['text']};
                font-family: {theme.FONT_FAMILY};
            }}
            QLabel {{
                color: {c['text']};
            }}
            QLabel#qc-muted {{
                color: {c['muted']};
                font-size: 9pt;
            }}
            QLineEdit, QComboBox {{
                background-color: {c['panel']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 5px 8px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border-color: {c['accent']};
            }}
            QTableWidget {{
                background-color: {c['panel']};
                alternate-background-color: {c['card_alt']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                gridline-color: {c['border']};
                selection-background-color: {c['card']};
                selection-color: {c['accent']};
            }}
            QHeaderView::section {{
                background-color: {c['card']};
                color: {c['text']};
                padding: 6px 8px;
                border: 1px solid {c['border']};
                font-weight: 600;
            }}
            QPushButton {{
                background-color: {c['card']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                border-color: {c['accent']};
            }}
            QPushButton#qc-apply-btn {{
                background-color: {c['accent']};
                color: {c['bg']};
                border: none;
            }}
            QPushButton#qc-apply-btn:hover {{
                background-color: {c['accent_hover']};
            }}
            """
        )

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        header_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_lbl = QLabel("<b>Chapter Proofread &amp; QC</b>")
        title_lbl.setStyleSheet("font-size: 13pt;")
        self.chapter_summary_label = QLabel("Loading chapter entries...")
        self.chapter_summary_label.setObjectName("qc-muted")
        title_col.addWidget(title_lbl)
        title_col.addWidget(self.chapter_summary_label)
        header_row.addLayout(title_col, 1)

        refresh_btn = QPushButton("Reload")
        refresh_btn.setIcon(app_icon("refresh", theme.COLORS["text"], 14))
        refresh_btn.clicked.connect(self.reload_chapter_entries)
        header_row.addWidget(refresh_btn)
        root.addLayout(header_row)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter dialogue, OCR, or page filename...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._populate_table)
        filter_row.addWidget(self.search_input, 2)

        self.page_combo = QComboBox()
        self.page_combo.addItem("All Pages", None)
        self.page_combo.currentIndexChanged.connect(self._populate_table)
        filter_row.addWidget(self.page_combo, 1)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "All Bubbles",
            "Untranslated / Empty",
            "Current Page Only",
            "Short / Flagged (<3 chars)",
        ])
        self.filter_combo.currentIndexChanged.connect(self._populate_table)
        filter_row.addWidget(self.filter_combo, 1)
        root.addLayout(filter_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([
            "Page / Bubble",
            "Original / OCR Text",
            "Translation (Editable)",
            "Jump",
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.EditKeyPressed
            | QAbstractItemView.AnyKeyPressed
        )
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(3, 84)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.itemChanged.connect(self._on_item_changed)
        root.addWidget(self.table, 1)

        footer_row = QHBoxLayout()
        footer_row.setSpacing(8)
        self.status_summary_label = QLabel("Double-click or press F2 to edit OCR/translation directly.")
        self.status_summary_label.setObjectName("qc-muted")
        footer_row.addWidget(self.status_summary_label, 1)

        self.jump_button = QPushButton("Jump to Selected")
        self.jump_button.setIcon(app_icon("arrow-right", theme.COLORS["text"], 14))
        self.jump_button.clicked.connect(self.jump_to_selected)
        footer_row.addWidget(self.jump_button)

        self.apply_button = QPushButton("Apply All Changes")
        self.apply_button.setObjectName("qc-apply-btn")
        self.apply_button.setIcon(app_icon("check", theme.COLORS["bg"], 14))
        self.apply_button.clicked.connect(self.apply_changes)
        footer_row.addWidget(self.apply_button)

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        footer_row.addWidget(self.close_button)
        root.addLayout(footer_row)

    @staticmethod
    def _area_values(area) -> tuple[str, str, str]:
        if isinstance(area, dict):
            ocr_txt = str(area.get("original_text", "") or "")
            tl_txt = str(area.get("text", "") or "")
            hist_id = str(area.get("history_id") or area.get("id") or "")
            return ocr_txt, tl_txt, hist_id
        ocr_txt = str(getattr(area, "original_text", "") or "")
        tl_txt = str(getattr(area, "text", "") or "")
        hist_id = str(getattr(area, "history_id", "") or "")
        return ocr_txt, tl_txt, hist_id

    def _collect_chapter_sources(self) -> list[tuple[str, str | None, str, list]]:
        """Return ordered list of (image_key, file_path, page_label, areas_list)."""
        mw = self.main_window
        current_key = mw.get_current_data_key() if getattr(mw, "current_image_path", None) else None
        all_data = getattr(mw, "all_typeset_data", {}) or {}
        seen_keys: set[str] = set()
        sources: list[tuple[str, str | None, str, list]] = []

        for file_path in list(getattr(mw, "image_files", []) or []):
            key = mw.get_current_data_key(path=file_path)
            if not key or key in seen_keys:
                continue
            seen_keys.add(key)
            if key == current_key:
                areas = list(getattr(mw, "typeset_areas", []) or [])
            else:
                rec = all_data.get(key) or {}
                areas = list(rec.get("areas", []) or [])
            sources.append((key, file_path, os.path.basename(file_path), areas))

        # Include any extra project records (e.g., multi-page PDF keys) not in flat image_files list
        for key, rec in all_data.items():
            if not key or key in seen_keys or not isinstance(rec, dict):
                continue
            areas = (
                list(getattr(mw, "typeset_areas", []) or [])
                if key == current_key
                else list(rec.get("areas", []) or [])
            )
            if not areas:
                continue
            seen_keys.add(key)
            page_label = os.path.basename(str(key))
            sources.append((key, None, page_label, areas))

        return sources

    def reload_chapter_entries(self):
        self._entries.clear()
        self._entry_by_uid.clear()
        self._pending_edits.clear()

        sources = self._collect_chapter_sources()
        with QSignalBlocker(self.page_combo):
            prev_page = self.page_combo.currentData()
            self.page_combo.clear()
            self.page_combo.addItem("All Pages", None)
            for key, _fpath, page_label, _areas in sources:
                self.page_combo.addItem(page_label, key)
            if prev_page is not None:
                idx = self.page_combo.findData(prev_page)
                if idx >= 0:
                    self.page_combo.setCurrentIndex(idx)

        total_bubbles = 0
        translated_bubbles = 0
        pages_with_bubbles = 0
        for key, file_path, page_label, areas in sources:
            if areas:
                pages_with_bubbles += 1
            for area_idx, area in enumerate(areas):
                ocr_txt, tl_txt, hist_id = self._area_values(area)
                total_bubbles += 1
                if tl_txt.strip():
                    translated_bubbles += 1
                uid = (key, area_idx)
                entry = {
                    "uid": uid,
                    "key": key,
                    "file_path": file_path,
                    "page_label": page_label,
                    "area_idx": area_idx,
                    "area": area,
                    "history_id": hist_id,
                    "orig_ocr": ocr_txt,
                    "orig_tl": tl_txt,
                }
                self._entries.append(entry)
                self._entry_by_uid[uid] = entry

        empty_count = max(0, total_bubbles - translated_bubbles)
        self.chapter_summary_label.setText(
            f"{len(sources)} Pages ({pages_with_bubbles} with bubbles) · {total_bubbles} Bubbles · {translated_bubbles} Translated · {empty_count} Empty"
        )
        self._populate_table()
        self._update_pending_label()

    def _effective_values(self, entry: dict) -> tuple[str, str]:
        patch = self._pending_edits.get(entry["uid"])
        if patch is not None:
            return patch["ocr"], patch["tl"]
        return entry["orig_ocr"], entry["orig_tl"]

    def _matches_filter(self, entry: dict, search_q: str, page_key: str | None, filter_mode: str, current_key: str | None) -> bool:
        if page_key is not None and entry["key"] != page_key:
            return False
        ocr_txt, tl_txt = self._effective_values(entry)
        tl_stripped = tl_txt.strip()
        if filter_mode == "Untranslated / Empty" and tl_stripped:
            return False
        if filter_mode == "Current Page Only" and entry["key"] != current_key:
            return False
        if filter_mode == "Short / Flagged (<3 chars)":
            flagged = (len(tl_stripped) < 3) or tl_stripped.startswith("[")
            if not flagged:
                return False
        if search_q:
            hay = f"{entry['page_label']} {ocr_txt} {tl_txt}".lower()
            if search_q not in hay:
                return False
        return True

    def _populate_table(self):
        mw = self.main_window
        current_key = mw.get_current_data_key() if getattr(mw, "current_image_path", None) else None
        search_q = (self.search_input.text() or "").strip().lower()
        page_key = self.page_combo.currentData()
        filter_mode = self.filter_combo.currentText()

        visible_entries = [
            e for e in self._entries
            if self._matches_filter(e, search_q, page_key, filter_mode, current_key)
        ]

        self._populating_table = True
        try:
            self.table.setRowCount(len(visible_entries))
            for row_idx, entry in enumerate(visible_entries):
                ocr_txt, tl_txt = self._effective_values(entry)
                is_empty = not tl_txt.strip()

                meta_item = QTableWidgetItem(f"{entry['page_label']}  #{entry['area_idx'] + 1}")
                meta_item.setFlags(meta_item.flags() & ~Qt.ItemIsEditable)
                meta_item.setData(Qt.UserRole, entry["uid"])
                if is_empty:
                    meta_item.setForeground(QColor(theme.COLORS["warning"]))
                self.table.setItem(row_idx, 0, meta_item)

                ocr_item = QTableWidgetItem(ocr_txt)
                ocr_item.setData(Qt.UserRole, entry["uid"])
                self.table.setItem(row_idx, 1, ocr_item)

                tl_item = QTableWidgetItem(tl_txt)
                tl_item.setData(Qt.UserRole, entry["uid"])
                if is_empty:
                    tl_item.setBackground(QColor(theme.COLORS["card_alt"]))
                self.table.setItem(row_idx, 2, tl_item)

                jump_btn = QPushButton("Jump")
                jump_btn.setCursor(Qt.PointingHandCursor)
                jump_btn.clicked.connect(partial(self.jump_to_entry, entry["uid"]))
                self.table.setCellWidget(row_idx, 3, jump_btn)
        finally:
            self._populating_table = False

    def _on_item_changed(self, item: QTableWidgetItem):
        if self._populating_table or item is None:
            return
        col = item.column()
        if col not in (1, 2):
            return
        row = item.row()
        meta_item = self.table.item(row, 0)
        if meta_item is None:
            return
        uid = meta_item.data(Qt.UserRole)
        entry = self._entry_by_uid.get(uid)
        if entry is None:
            return
        ocr_item = self.table.item(row, 1)
        tl_item = self.table.item(row, 2)
        new_ocr = ocr_item.text() if ocr_item is not None else entry["orig_ocr"]
        new_tl = tl_item.text() if tl_item is not None else entry["orig_tl"]
        if new_ocr == entry["orig_ocr"] and new_tl == entry["orig_tl"]:
            self._pending_edits.pop(uid, None)
        else:
            self._pending_edits[uid] = {"ocr": new_ocr, "tl": new_tl}
        self._update_pending_label()

    def _update_pending_label(self):
        n = len(self._pending_edits)
        if n > 0:
            self.status_summary_label.setText(f"{n} bubble edit(s) pending — click 'Apply All Changes' to save.")
        else:
            self.status_summary_label.setText("Double-click or press F2 to edit OCR/translation directly.")

    def get_modified_count(self) -> int:
        return len(self._pending_edits)

    def jump_to_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        meta_item = self.table.item(row, 0)
        if meta_item is None:
            return
        uid = meta_item.data(Qt.UserRole)
        if uid is not None:
            self.jump_to_entry(uid)

    def jump_to_entry(self, uid):
        entry = self._entry_by_uid.get(uid)
        if entry is None:
            return
        mw = self.main_window
        target_path = entry.get("file_path")
        current_path = getattr(mw, "current_image_path", None)
        need_switch = bool(
            target_path
            and (
                not current_path
                or os.path.normcase(os.path.abspath(target_path)) != os.path.normcase(os.path.abspath(current_path))
            )
        )
        if need_switch:
            if target_path in getattr(mw, "image_files", []) and hasattr(mw, "file_list_widget"):
                row_idx = mw.image_files.index(target_path)
                mw.file_list_widget.setCurrentRow(row_idx)
            elif hasattr(mw, "load_item"):
                mw.load_item(target_path)

        # Select the target bubble on canvas
        areas = list(getattr(mw, "typeset_areas", []) or [])
        area_idx = entry["area_idx"]
        target_area = None
        if 0 <= area_idx < len(areas):
            target_area = areas[area_idx]
        elif entry["area"] in areas:
            target_area = entry["area"]
        if target_area is not None and hasattr(mw, "set_selected_area"):
            mw.set_selected_area(target_area, notify=True)
            if hasattr(mw, "image_scroll") and hasattr(target_area, "get_text_rect"):
                try:
                    rect = target_area.get_text_rect()
                    zoom = float(getattr(mw, "zoom_factor", 1.0) or 1.0)
                    mw.image_scroll.ensureVisible(int(rect.center().x() * zoom), int(rect.center().y() * zoom), 120, 120)
                except Exception:
                    pass

    def apply_changes(self) -> int:
        if not self._pending_edits:
            if hasattr(self.main_window, "show_toast"):
                self.main_window.show_toast("No Changes", "No proofread edits to apply.", kind="info")
            return 0

        mw = self.main_window
        current_key = mw.get_current_data_key() if getattr(mw, "current_image_path", None) else None
        modified_keys = {uid[0] for uid in self._pending_edits}
        if current_key and current_key in modified_keys and hasattr(mw, "_push_undo_snapshot"):
            mw._push_undo_snapshot("Chapter Proofread Edit")

        hist_map = {
            str(e.get("history_id") or e.get("id")): e
            for e in (getattr(mw, "history_entries", []) or [])
            if isinstance(e, dict) and (e.get("history_id") or e.get("id"))
        }

        applied = 0
        for uid, patch in list(self._pending_edits.items()):
            key, area_idx = uid
            entry = self._entry_by_uid.get(uid)
            if entry is None:
                continue

            if key == current_key:
                target_areas = getattr(mw, "typeset_areas", []) or []
            else:
                rec = (getattr(mw, "all_typeset_data", {}) or {}).get(key) or {}
                target_areas = rec.get("areas", []) or []

            if not (0 <= area_idx < len(target_areas)):
                continue
            area = target_areas[area_idx]

            new_ocr = patch["ocr"]
            raw_tl = patch["tl"]
            is_upright = (
                (area.get("orientation") if isinstance(area, dict) else getattr(area, "orientation", "horizontal"))
                == "vertical_upright"
            )
            new_tl = format_heart_emoticon_lines(raw_tl) if not is_upright else raw_tl

            if isinstance(area, dict):
                area["original_text"] = new_ocr
                if new_tl != entry["orig_tl"]:
                    area["text"] = new_tl
                    area["segments"] = None
            else:
                area.original_text = new_ocr
                if new_tl != entry["orig_tl"]:
                    if hasattr(area, "update_plain_text"):
                        area.update_plain_text(new_tl)
                    else:
                        area.text = new_tl

            hist_id = entry.get("history_id")
            if hist_id and hist_id in hist_map:
                h_entry = hist_map[hist_id]
                h_entry["original_text"] = new_ocr
                h_entry["translated_text"] = new_tl

            rec = (getattr(mw, "all_typeset_data", {}) or {}).get(key)
            if isinstance(rec, dict) and new_tl != entry["orig_tl"]:
                rec["exported_saved"] = False
            elif key and hasattr(mw, "_update_typeset_record"):
                rec = mw._update_typeset_record(key, areas=list(target_areas))
                if new_tl != entry["orig_tl"]:
                    rec["exported_saved"] = False

            entry["orig_ocr"] = new_ocr
            entry["orig_tl"] = new_tl
            applied += 1

        self._pending_edits.clear()
        self._update_pending_label()
        self._populate_table()

        if current_key and current_key in modified_keys and hasattr(mw, "redraw_all_typeset_areas"):
            mw.redraw_all_typeset_areas()
        if hasattr(mw, "_refresh_layers_list"):
            mw._refresh_layers_list()
        if hasattr(mw, "_refresh_file_list_statuses"):
            mw._refresh_file_list_statuses()
        if hasattr(mw, "refresh_history_views"):
            mw.refresh_history_views()
        if hasattr(mw, "update_undo_redo_buttons_state"):
            mw.update_undo_redo_buttons_state()
        if hasattr(mw, "save_project"):
            mw.save_project(is_auto=True)
        if hasattr(mw, "show_toast"):
            mw.show_toast("Proofread Applied", f"Applied edits to {applied} bubble(s).", kind="success")
        return applied


__all__ = ["ChapterProofreadDialog"]
