"""Method domain history, dipindahkan utuh dari main_window.py.

Fase 1 pemecahan monolit: isi method tidak diubah sama sekali.
Mixin ini hanya berguna sebagai bagian dari MangaOCRApp -- ia mengandalkan
atribut yang dibuat di MangaOCRApp.__init__.
"""

from src.ui.main_window_mixins._imports import *  # noqa: F401,F403


class HistoryMixin:
    def _undo_timeline_qss(self) -> str:
        return (
            theme.list_widget_qss("QListWidget#undo-timeline", compact=True)
            + f"""
            QListWidget#undo-timeline {{
                font-size: 8pt;
            }}
            QScrollBar:vertical {{
                background: {theme.COLORS["panel"]};
                width: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {theme.COLORS["border"]};
                border-radius: 3px;
            }}
            """
        )

    def _create_history_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 16, 14, 14)

        description = QLabel("Review the latest translation results. Only the five most recent entries are shown here.")
        description.setWordWrap(True)
        layout.addWidget(description)

        self.history_table = self._create_result_table()
        self.history_table.setProperty('result_limit', self.history_preview_limit)
        self.result_table_registry['history'].add(self.history_table)
        layout.addWidget(self.history_table)

        controls_layout = QHBoxLayout()
        controls_layout.addStretch()
        history_view_all = QPushButton("View All")
        history_view_all.clicked.connect(self.show_history_modal)
        controls_layout.addWidget(history_view_all)
        layout.addLayout(controls_layout)

        self.history_view_all_button = history_view_all
        self.refresh_history_views()
        return tab

    def send_history_entry_to_proofreader(self, history_id):
        self._stage_history_entry_for_review(history_id, 'proofreader')

    def send_history_entry_to_quality(self, history_id):
        self._stage_history_entry_for_review(history_id, 'quality')

    def _stage_history_entry_for_review(self, history_id, target):
        target = (target or '').lower()
        if target not in ('proofreader', 'quality'):
            return

        entry = self.get_history_entry(history_id)
        if not entry:
            self.show_banner("history-entry-missing", "Entry missing", "Unable to find this history entry. It may have been removed.", kind="warning")
            return

        record = {
            'history_id': history_id,
            'id': history_id,
            'original_text': entry.get('original_text', ''),
            'translated_text': entry.get('translated_text', ''),
            'translation_style': entry.get('translation_style', ''),
            'timestamp': time.time(),
        }
        if entry.get('manual'):
            record['manual'] = True
        if entry.get('manual_inpaint') is not None:
            record['manual_inpaint'] = bool(entry.get('manual_inpaint'))
        if entry.get('ai_model'):
            record['ai_model'] = entry.get('ai_model')
        if entry.get('staged'):
            record['staged'] = bool(entry.get('staged'))

        if target == 'proofreader':
            dest_list = self.proofreader_entries
            existing = self.get_proofreader_entry(history_id)
            tab_label = "Proofreader"
        else:
            dest_list = self.quality_entries
            existing = self.get_quality_entry(history_id)
            tab_label = "Quality Checker"

        if existing:
            staged_flag = existing.get('staged')
            existing.update(record)
            if staged_flag is not None:
                existing['staged'] = staged_flag
            try:
                dest_list.remove(existing)
            except ValueError:
                pass
            dest_list.insert(0, existing)
        else:
            dest_list.insert(0, record)

        self.refresh_history_views()
        self.statusBar().showMessage(f"Entry {history_id} dipindahkan ke {tab_label}.", 3000)

    def move_entry_to_deleted_history(self, history_id):
        # Find the entry in history
        entry = self.get_history_entry(history_id)
        if not entry:
            # Maybe it's in a scene? Or maybe we just can't find it.
            # If we strictly want to preserve DELETED items from canvas, 
            # we should look it up from the area before it's gone?
            # Actually catch: delete_typeset_area calls this.
            return

        target_scene = "Deleted History"
        if target_scene not in self.scenes:
            self.create_scene(target_scene)
        
        # Check if already in deleted history
        deleted_list = self.scenes[target_scene]
        if any(e.get('id') == history_id for e in deleted_list):
            return

        # Clone and add
        new_entry = copy.deepcopy(entry)
        # Mark as deleted from canvas
        new_entry['deleted_from_canvas'] = True
        new_entry['deletion_timestamp'] = time.time()
        
        self.scenes[target_scene].insert(0, new_entry)
        
        # NOTE: Do we remove from main history? 
        # Requirement: "pindahkan secara otomatis" (move automatically).
        # So yes, we should probably remove from the main history view 
        # OR just keep it in history but mark it?
        # User said "Deleted History" category/folder.
        # Let's keep it simple: Add to scene "Deleted History". 
        # Removing from self.history_entries might confuse the "History" tab which logs *everything*.
        # But if the user says "item ... dipindahkan", it implies move.
        # Let's remove from history entries to be safe/clean.
        try:
             self.history_entries.remove(entry)
             if history_id in self.history_lookup:
                 del self.history_lookup[history_id]
        except ValueError:
             pass

        self.refresh_history_views()

    def show_history_modal(self):
        self._show_result_modal('history', 'History (All Entries)')

    def generate_history_id(self):
        self.history_counter += 1
        return f"H{self.history_counter:05d}"

    def get_history_entry(self, history_id):
        for entry in self.history_entries:
            if entry['id'] == history_id:
                return entry
        return None

    def rebuild_history_for_image(self, image_key, areas):
        if not image_key or not areas:
            return
        for area in areas:
            self.register_history_entry(image_key, area, getattr(area, 'original_text', ''), getattr(area, 'text', ''))

    def register_history_entry(self, image_key, area, original_text, translated_text):
        if not getattr(area, 'history_id', None):
            area.history_id = self.generate_history_id()
        history_id = area.history_id

        if original_text is not None:
            area.original_text = original_text
        if translated_text is not None:
            preserve_segments = False
            try:
                segments = area.get_segments()
                if segments:
                    existing_plain = area._segments_to_plain_text(segments)
                    preserve_segments = (existing_plain == translated_text)
            except Exception:
                preserve_segments = False
            if preserve_segments:
                area.text = translated_text or ''
            else:
                area.update_plain_text(translated_text)

        entry = self.get_history_entry(history_id)
        notes = area.review_notes if isinstance(getattr(area, 'review_notes', {}), dict) else {}
        if not isinstance(notes, dict):
            notes = {}
            area.review_notes = notes
        manual_flag = bool(notes.get('manual'))
        manual_inpaint = notes.get('manual_inpaint')
        model_label = notes.get('ai_model')
        record = {
            'id': history_id,
            'history_id': history_id,
            'image_key': image_key,
            'original_text': area.original_text or '',
            'translated_text': translated_text if translated_text is not None else area.text or '',
            'translation_style': getattr(area, 'translation_style', ''),
            'timestamp': time.time(),
        }
        if manual_flag:
            record['manual'] = True
            if not record['original_text']:
                record['original_text'] = 'Manual Input'
        if manual_inpaint is not None:
            record['manual_inpaint'] = bool(manual_inpaint)
        if model_label:
            record['ai_model'] = model_label

        if entry:
            entry.update(record)
        else:
            self.history_entries.append(record)

        self.history_lookup[history_id] = {'image_key': image_key, 'area': area}
        return record

    def apply_history_update(self, history_id, *, translated_text=None, original_text=None, translation_style=None, ai_model=None):
        entry = self.get_history_entry(history_id)
        if not entry:
            return False

        if original_text is not None:
            entry['original_text'] = original_text
        if translated_text is not None:
            entry['translated_text'] = translated_text
        if translation_style is not None:
            entry['translation_style'] = translation_style
        if ai_model is not None:
            entry['ai_model'] = ai_model
        entry['timestamp'] = time.time()

        lookup = self.history_lookup.get(history_id)
        if not lookup:
            return False

        area = lookup.get('area')
        if not area:
            return False

        if original_text is not None:
            area.original_text = original_text
        if translation_style is not None:
            area.translation_style = translation_style
        if translated_text is not None:
            area.update_plain_text(translated_text)
        if ai_model is not None:
            notes = area.review_notes if isinstance(getattr(area, 'review_notes', {}), dict) else {}
            if not isinstance(notes, dict):
                notes = {}
            notes['ai_model'] = ai_model
            area.review_notes = notes

        image_key = lookup.get('image_key')
        image_record = self.all_typeset_data.get(image_key)
        if image_record:
            image_record.setdefault('redo', []).clear()

        if image_key == self.get_current_data_key():
            # Push snapshot SEBELUM perubahan teks terjemahan
            if translated_text is not None:
                snippet = translated_text[:20] + ('…' if len(translated_text) > 20 else '')
                self._push_undo_snapshot(f"Translate: {snippet}")
            self.redo_stack.clear()
            self.redraw_all_typeset_areas()
            self.update_undo_redo_buttons_state()

        self.refresh_history_views()
        return True

    def reset_history_state(self):
        self.history_entries.clear()
        self.proofreader_entries.clear()
        self.quality_entries.clear()
        self.history_lookup.clear()
        self.history_counter = 0
        self.refresh_history_views()

    def refresh_history_views(self):
        if getattr(self, '_is_refreshing_history', False): return
        self._is_refreshing_history = True
        try:
            sources = [
                ('history', self.history_entries),
                ('proofreader', self.proofreader_entries),
                ('quality', self.quality_entries),
                ('scene', self.scenes.get(self.current_scene_name, []) if self.current_scene_name else []),
            ]

            for source, dataset in sources:
                tables = list(self.result_table_registry.get(source, []))
                if not tables:
                    continue
                dataset = dataset or []

                # Filter history by current image
                if source == 'history' and self.current_image_path:
                    dataset = [e for e in dataset if e.get('image_key') == self.current_image_path]

                for table in tables:
                    limit_property = table.property('result_limit')
                    limit_value = None
                    if limit_property not in (None, '', False):
                        try:
                            limit_value = int(limit_property)
                        except (TypeError, ValueError):
                            limit_value = None

                    if source == 'history':
                        entries = self._get_recent_entries(dataset, limit_value if limit_value and limit_value > 0 else None)
                    else:
                        if limit_value and limit_value > 0:
                            entries = list(dataset[:limit_value])
                        else:
                            entries = list(dataset)
                    self.populate_result_table(table, entries, source)

            self.update_result_buttons_state()
            self._update_recent_translations_list()
        finally:
            self._is_refreshing_history = False

    def undo_last_action(self):
        """Navigasi mundur satu langkah di undo history timeline."""
        if self._undo_history_idx >= 0:
            restore_idx = self._undo_history_idx
            self._restore_snapshot(restore_idx)
            self._undo_history_idx = restore_idx - 1
            self.update_undo_redo_buttons_state()
            self._refresh_undo_timeline()
            if hasattr(self, 'image_label'):
                self.image_label.clear_selection()
        else:
            # Fallback legacy: pop satu area
            if self.typeset_areas:
                undone_area = self.typeset_areas.pop()
                self.redo_stack.append(undone_area)
                if self.selected_typeset_area is undone_area:
                    self.clear_selected_area()
                self.redraw_all_typeset_areas()
                self.update_undo_redo_buttons_state()
                if hasattr(self, 'image_label'):
                    self.image_label.clear_selection()

    def redo_last_action(self):
        """Navigasi maju satu langkah di undo history timeline."""
        if self._undo_history and self._undo_history_idx < len(self._undo_history) - 1:
            self._restore_snapshot(self._undo_history_idx + 1)
        else:
            # Fallback legacy redo
            if self.redo_stack:
                redone_area = self.redo_stack.pop()
                self.typeset_areas.append(redone_area)
                self.set_selected_area(redone_area)
                self.redraw_all_typeset_areas()
                self.update_undo_redo_buttons_state()
                if hasattr(self, 'image_label'):
                    self.image_label.clear_selection()

    def update_undo_redo_buttons_state(self):
        """Update enabled state tombol Undo dan Redo berdasarkan snapshot history."""
        can_undo = self._undo_history_idx >= 0
        can_redo = bool(self._undo_history) and self._undo_history_idx < len(self._undo_history) - 1
        self.undo_button.setEnabled(can_undo)
        self.redo_button.setEnabled(can_redo)

    def _push_undo_snapshot(self, label="Action"):
        """
        Ambil snapshot deep-copy dari typeset_areas sebelum perubahan.
        Push ke _undo_history dan potong redo branch.
        """
        import copy as _copy
        try:
            snapshot = []
            for area in self.typeset_areas:
                if hasattr(area, 'to_payload'):
                    snapshot.append(area.to_payload())
                else:
                    snapshot.append(_copy.deepcopy(area))
            current_key = self.get_current_data_key() if self.current_image_path else None
            current_record = self.all_typeset_data.get(current_key, {}) if current_key else {}
            image_png = self._encode_cleaned_image(self.current_image_pil) if self.current_image_pil is not None else None
            pre_inpaint_png = current_record.get('pre_inpaint_image_png') if isinstance(current_record, dict) else None
            snapshot_payload = {
                'areas': snapshot,
                'image_png': image_png,
                'had_cleaned_image': bool(isinstance(current_record, dict) and current_record.get('cleaned_image_png')),
                'pre_inpaint_image_png': pre_inpaint_png,
            }

            # Potong redo branch (state setelah posisi aktif)
            if self._undo_history_idx < len(self._undo_history) - 1:
                self._undo_history = self._undo_history[:self._undo_history_idx + 1]

            self._undo_history.append({'label': label, 'snapshot': snapshot_payload})

            # Cap ke max history
            if len(self._undo_history) > self._MAX_UNDO_HISTORY:
                self._undo_history = self._undo_history[-self._MAX_UNDO_HISTORY:]

            self._undo_history_idx = len(self._undo_history) - 1
            self._refresh_undo_timeline()
        except Exception as e:
            print(f"[UndoTimeline] Push snapshot failed: {e}")

    def _refresh_undo_timeline(self):
        """Perbarui QListWidget timeline dengan seluruh undo history."""
        if not hasattr(self, 'undo_timeline_list'):
            return
        lst = self.undo_timeline_list
        lst.blockSignals(True)
        lst.clear()

        from PyQt5.QtGui import QColor
        from PyQt5.QtWidgets import QListWidgetItem

        if not self._undo_history:
            empty_item = QListWidgetItem("  (kosong)")
            empty_item.setForeground(QColor(theme.COLORS['muted']))
            empty_item.setFlags(empty_item.flags() & ~Qt.ItemIsSelectable)
            lst.addItem(empty_item)
            lst.blockSignals(False)
            return

        for i, entry in enumerate(self._undo_history):
            is_current = (i == self._undo_history_idx)
            is_redo    = (i > self._undo_history_idx)

            if is_current:
                prefix = "▶"
                color  = theme.COLORS['accent']   # state aktif
            elif is_redo:
                prefix = "◁"
                color  = theme.COLORS['muted']   # state yang bisa di-redo
            else:
                prefix = "·"
                color  = theme.COLORS['muted']   # masa lalu

            item = QListWidgetItem(f"  {prefix}  {i + 1}. {entry['label']}")
            item.setData(Qt.UserRole, i)
            item.setForeground(QColor(color))
            lst.addItem(item)

        # Scroll ke item aktif
        if 0 <= self._undo_history_idx < lst.count():
            lst.scrollToItem(lst.item(self._undo_history_idx))
            lst.setCurrentRow(self._undo_history_idx)

        lst.blockSignals(False)

    def _clear_undo_history(self):
        """Bersihkan seluruh undo history timeline."""
        self._undo_history.clear()
        self._undo_history_idx = -1
        self._refresh_undo_timeline()
        self.update_undo_redo_buttons_state()

    def _sanitize_history_entries(self, history_data, area_lookup, warnings):
        sanitized = []
        max_counter = 0
        for entry in history_data or []:
            if not isinstance(entry, dict):
                warnings.append("Ignored malformed history entry.")
                continue
            hist_id = entry.get('history_id') or entry.get('id')
            if hist_id is None:
                warnings.append("A history entry without identifier was skipped.")
                continue
            hist_id = str(hist_id)
            if hist_id.startswith('H') and hist_id[1:].isdigit():
                numeric = int(hist_id[1:])
                max_counter = max(max_counter, numeric)
            elif hist_id.isdigit():
                numeric = int(hist_id)
                hist_id = f"H{numeric:05d}"
                max_counter = max(max_counter, numeric)
            else:
                warnings.append(f"History id '{hist_id}' has unexpected format.")
            record = dict(entry)
            record['history_id'] = hist_id
            record['id'] = hist_id
            record['timestamp'] = float(record.get('timestamp', time.time()))
            record['original_text'] = record.get('original_text', '')
            record['translated_text'] = record.get('translated_text', '')
            record['translation_style'] = record.get('translation_style', '')
            area_info = area_lookup.get(hist_id)
            if area_info:
                record['image_key'] = area_info['image_key']
                area = area_info['area']
                if record['original_text']:
                    area.original_text = record['original_text']
                if record['translation_style']:
                    area.translation_style = record['translation_style']
                if record['translated_text']:
                    # Only populate text from history when the area has no text of
                    # its own (e.g. area created without going through the normal
                    # translation pipeline).  When typeset_data already loaded a
                    # non-empty text into the area, trust that value — it reflects
                    # any manual edits the user made after the AI translation.
                    if not (area.text or '').strip():
                        area.update_plain_text(record['translated_text'])
            else:
                if 'image_key' not in record:
                    warnings.append(f"History entry {hist_id} has no matching area.")
            sanitized.append(record)
        return sanitized, max_counter
