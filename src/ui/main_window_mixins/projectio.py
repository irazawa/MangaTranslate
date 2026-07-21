"""Method domain projectio, dipindahkan utuh dari main_window.py.

Fase 1 pemecahan monolit: isi method tidak diubah sama sekali.
Mixin ini hanya berguna sebagai bagian dari MangaOCRApp -- ia mengandalkan
atribut yang dibuat di MangaOCRApp.__init__.
"""

from src.ui.main_window_mixins._imports import *  # noqa: F401,F403


class ProjectioMixin:
    def emergency_save_and_exit(self):
        try:
            if getattr(self, 'project_dir', None):
                # Commit active typeset areas to in-memory dictionary
                if getattr(self, 'current_image_path', None):
                    key = self.get_current_data_key()
                    self._update_typeset_record(key, areas=list(self.typeset_areas), redo=list(self.redo_stack))

                if not getattr(self, 'current_project_path', None):
                    self.current_project_path, _ = self._make_project_file_path()

                if self.current_project_path:
                    from src.ui.canvas import TypesetArea
                    self.paint_mutex.lock()
                    try:
                        serialized_typeset = {}
                        for k, rec in (self.all_typeset_data or {}).items():
                            try:
                                areas = rec.get('areas', []) or []
                                redo = rec.get('redo', []) or []
                                serialized_typeset[k] = {
                                    'areas': [area.to_payload() if isinstance(area, TypesetArea) else area for area in areas],
                                    'redo': [r.to_payload() if isinstance(r, TypesetArea) else r for r in redo],
                                }
                                for image_state_key in ('cleaned_image_png', 'pre_inpaint_image_png'):
                                    if rec.get(image_state_key):
                                        serialized_typeset[k][image_state_key] = rec.get(image_state_key)
                            except Exception:
                                serialized_typeset[k] = {'areas': [], 'redo': []}

                        snapshot = {
                            'project_dir': self.project_dir,
                            'current_image_path': self.current_image_path,
                            'current_pdf_page': int(self.current_pdf_page) if isinstance(self.current_pdf_page, int) else -1,
                            'typeset_data': serialized_typeset,
                            'history_entries': list(self.history_entries) if getattr(self, 'history_entries', None) is not None else [],
                            'proofreader_entries': list(self.proofreader_entries) if getattr(self, 'proofreader_entries', None) is not None else [],
                            'quality_entries': list(self.quality_entries) if getattr(self, 'quality_entries', None) is not None else [],
                            'history_counter': int(self.history_counter) if getattr(self, 'history_counter', None) is not None else 0,
                            'typeset_font': TypesetArea.font_to_dict(self.typeset_font) if getattr(self, 'typeset_font', None) else None,
                            'typeset_color': self.typeset_color.name() if getattr(self, 'typeset_color', None) else '#000000',
                            'settings': self._collect_project_settings() if hasattr(self, '_collect_project_settings') else {},
                            'app_version': APP_VERSION,
                        }
                    finally:
                        self.paint_mutex.unlock()

                    project_file_dir = os.path.dirname(os.path.abspath(self.current_project_path))
                    abs_project_dir = os.path.abspath(snapshot.get('project_dir')) if snapshot.get('project_dir') else None
                    abs_image_path = snapshot.get('current_image_path')

                    rel_project_dir = None
                    rel_image_path = None
                    if abs_project_dir:
                        try:
                            rel_project_dir = os.path.relpath(abs_project_dir, project_file_dir)
                        except ValueError:
                            rel_project_dir = None
                    if abs_image_path:
                        try:
                            rel_image_path = os.path.relpath(abs_image_path, project_file_dir)
                        except ValueError:
                            rel_image_path = None

                    raw_typeset = snapshot.get('typeset_data', {})
                    compact_typeset = {}
                    image_order = []
                    for abs_key, record in raw_typeset.items():
                        basename = os.path.basename(abs_key)
                        compact_typeset[basename] = record
                        image_order.append(basename)

                    payload = {
                        'schema_version': 4,
                        'project_dir_rel': rel_project_dir,
                        'current_image_path_rel': rel_image_path,
                        'project_dir': abs_project_dir,
                        'current_image_path': abs_image_path,
                        'current_pdf_page': int(snapshot.get('current_pdf_page', -1)),
                        'image_order': image_order,
                        'typeset_data': compact_typeset,
                        'history_entries': snapshot.get('history_entries', []),
                        'proofreader_entries': snapshot.get('proofreader_entries', []),
                        'quality_entries': snapshot.get('quality_entries', []),
                        'history_counter': int(snapshot.get('history_counter', 0)),
                        'typeset_font': snapshot.get('typeset_font'),
                        'typeset_color': snapshot.get('typeset_color'),
                        'settings': snapshot.get('settings', {}),
                        'saved_at': time.time(),
                        'app_version': snapshot.get('app_version', APP_VERSION),
                    }

                    target_dir = os.path.dirname(self.current_project_path) or self.project_dir
                    if target_dir:
                        os.makedirs(target_dir, exist_ok=True)

                    tmp_path = self.current_project_path + '.tmp'
                    with open(tmp_path, 'w', encoding='utf-8') as handle:
                        json.dump(payload, handle, ensure_ascii=False, indent=1)
                    os.replace(tmp_path, self.current_project_path)
        except Exception as e:
            print(f"Error in emergency save: {e}", file=sys.stderr)

        try:
            ec_cfg = SETTINGS.get('emergency_close', {})
            action_type = ec_cfg.get('action_type', 'url')
            target = ec_cfg.get('target', 'https://youtube.com').strip()

            if action_type == 'url':
                if not (target.startswith("http://") or target.startswith("https://")):
                    target = "https://" + target
                
                brave_paths = [
                    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                    r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
                    os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe")
                ]
                
                brave_opened = False
                for path in brave_paths:
                    if os.path.exists(path):
                        try:
                            subprocess.Popen([path, target], creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                            brave_opened = True
                            break
                        except Exception:
                            pass
                
                if not brave_opened:
                    import webbrowser
                    webbrowser.open(target)

            elif action_type == 'app':
                if target:
                    try:
                        subprocess.Popen(target, shell=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                    except Exception as e:
                        print(f"Error launching app {target}: {e}", file=sys.stderr)

            elif action_type == 'focus':
                if target and os.name == 'nt':
                    try:
                        import ctypes
                        
                        def focus_window(title_sub):
                            EnumWindows = ctypes.windll.user32.EnumWindows
                            EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_pointer, ctypes.c_pointer)
                            GetWindowText = ctypes.windll.user32.GetWindowTextW
                            GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
                            IsWindowVisible = ctypes.windll.user32.IsWindowVisible
                            ShowWindow = ctypes.windll.user32.ShowWindow
                            SetForegroundWindow = ctypes.windll.user32.SetForegroundWindow

                            def foreach_window(hwnd, lParam):
                                if IsWindowVisible(hwnd):
                                    length = GetWindowTextLength(hwnd)
                                    buff = ctypes.create_unicode_buffer(length + 1)
                                    GetWindowText(hwnd, buff, length + 1)
                                    title = buff.value
                                    if title_sub.lower() in title.lower():
                                        ShowWindow(hwnd, 9)
                                        SetForegroundWindow(hwnd)
                                        return False
                                return True

                            EnumWindows(EnumWindowsProc(foreach_window), 0)
                            
                        focus_window(target)
                    except Exception as e:
                        print(f"Error focusing window {target}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error in emergency action execution: {e}", file=sys.stderr)

        os._exit(0)

    def reload_shortcuts(self):
        self.shortcut_sequences = self._build_shortcut_map()

        # Update action-based shortcuts
        for key, action in (self._action_shortcut_map or {}).items():
            self._apply_action_shortcut(action, self.shortcut_sequences.get(key, ''))

        # Dispose old QShortcut instances
        for shortcut in self._active_shortcuts.values():
            try:
                shortcut.activated.disconnect()
            except Exception:
                pass
            shortcut.setParent(None)
            shortcut.deleteLater()
        self._active_shortcuts.clear()

        # Recreate shortcuts from definitions
        for key, callback in (self._shortcut_callbacks or {}).items():
            sequence = self.shortcut_sequences.get(key, '')
            if not sequence:
                continue
            try:
                qshortcut = QShortcut(QKeySequence(sequence), self)
                qshortcut.activated.connect(callback)
                self._active_shortcuts[key] = qshortcut
            except Exception:
                print(f"Failed to bind shortcut '{sequence}' for {key}", file=sys.stderr)
        # Also parse mouse-based shortcuts from sequences using a prefix like 'MOUSE:press:Left'
        # Supported formats: MOUSE:press:Left, MOUSE:release:Right, MOUSE:double:Left
        self._mouse_shortcuts.clear()
        mouse_sources = list((self._shortcut_callbacks or {}).items())
        # Allow action-backed shortcuts (menu actions) to be triggered by mouse bindings too
        for key, action in (self._action_shortcut_map or {}).items():
            if action is not None:
                mouse_sources.append((key, action.trigger))
        for key, callback in mouse_sources:
            seq = (self.shortcut_sequences.get(key, '') or '').strip()
            if not seq or not seq.upper().startswith('MOUSE:'):
                continue
            parts = seq.split(':')
            if len(parts) >= 3:
                evt = parts[1].lower()
                btn = mouse_name_to_button(parts[2])
                if btn is not None:
                    self._mouse_shortcuts[(evt, btn)] = callback

    def _load_openrouter_models(self):
        translate_cfg = SETTINGS.get('translate', {})
        pricing_db = getattr(self, 'openrouter_pricing_db', {})

        for provider_key, meta in LOCAL_TRANSLATE_PROVIDERS.items():
            provider = meta.get('display', provider_key)
            provider_cfg = translate_cfg.get(provider_key, {}) or {}
            models = provider_cfg.get('models')
            if not isinstance(models, list):
                models = meta.get('models', []) or []
            provider_dict = self.AI_PROVIDERS.setdefault(provider, {})
            provider_dict.clear()

            for model in models:
                if not isinstance(model, dict):
                    continue
                model_id = (model.get('id') or '').strip()
                if not model_id:
                    continue
                name = (model.get('name') or model_id).strip()
                description = (model.get('description') or '').strip()

                db_info = pricing_db.get(model_id, {}) if provider == 'OpenRouter' else {}
                db_pricing = db_info.get('pricing', {'input': 0.0, 'output': 0.0})

                provider_dict[model_id] = {
                    'display': f"{name}",
                    'pricing': {
                        'input': db_pricing.get('input', 0.0),
                        'output': db_pricing.get('output', 0.0)
                    },
                    'limits': {
                        'rpm': 300,
                        'rpd': 20000
                    },
                    'active': bool(model.get('active', True)),
                    'description': description,
                    'id': model_id,
                    'name': name,
                    'provider_key': provider_key
                }
            self._apply_ai_model_overrides_from_settings(provider_filter=provider)

    def load_usage_data(self):
        self.usage_mutex.lock()
        try:
            # Migration from legacy home directory path to root-level .cache path
            legacy_path = os.path.join(os.path.expanduser("~"), "manga_ocr_usage_v16.json")
            if os.path.exists(legacy_path) and not os.path.exists(self.usage_file_path):
                try:
                    import shutil
                    shutil.copy2(legacy_path, self.usage_file_path)
                    os.remove(legacy_path)
                    print(f"[MIGRATION] Migrated usage stats file from {legacy_path} to {self.usage_file_path}")
                except Exception as ex:
                    print(f"[MIGRATION ERROR] Failed to migrate usage file: {ex}")

            if os.path.exists(self.usage_file_path):
                with open(self.usage_file_path, 'r', encoding='utf-8') as f:
                    self.usage_data = json.load(f)
            else:
                self.usage_data = {}

            if 'provider_usage' not in self.usage_data:
                self.usage_data['provider_usage'] = {}

            for provider, models in self.AI_PROVIDERS.items():
                if provider not in self.usage_data['provider_usage']:
                    self.usage_data['provider_usage'][provider] = {}
                for model_name in models:
                    if model_name not in self.usage_data['provider_usage'][provider]:
                        self.usage_data['provider_usage'][provider][model_name] = {'daily_count': 0, 'minute_count': 0, 'current_minute': ''}

            if 'date' not in self.usage_data or self.usage_data.get('date') != str(date.today()):
                self.usage_data['date'] = str(date.today())
                for provider, models in self.AI_PROVIDERS.items():
                    for model_name in models:
                        self.usage_data['provider_usage'][provider][model_name]['daily_count'] = 0
                        self.usage_data['provider_usage'][provider][model_name]['minute_count'] = 0

            self.total_cost = self.usage_data.get('total_cost', 0.0)
            self._touch_profile_activity()
            self.update_cost_display()
            self.save_usage_data()
        except Exception as e:
            print(f"Could not load or create usage data file: {e}")
            self.usage_data = {'date': str(date.today()), 'total_cost': 0.0, 'provider_usage': {}}
            for provider, models in self.AI_PROVIDERS.items():
                self.usage_data['provider_usage'][provider] = {}
                for model_name in models:
                    self.usage_data['provider_usage'][provider][model_name] = {'daily_count': 0, 'minute_count': 0, 'current_minute': ''}
            self._touch_profile_activity()
        finally:
            self.usage_mutex.unlock()

    def save_usage_data(self):
        self.usage_mutex.lock()
        tmp_path = self.usage_file_path + '.tmp'
        try:
            self._record_profile_session_snapshot()
            self.usage_data['total_cost'] = self.total_cost
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(self.usage_data, f, ensure_ascii=False, indent=2)
            if os.path.exists(self.usage_file_path):
                try:
                    os.remove(self.usage_file_path)
                except Exception:
                    pass
            os.replace(tmp_path, self.usage_file_path)
        except Exception as e:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            print(f"Could not save usage data: {e}")
        finally:
            self.usage_mutex.unlock()

    def _find_project_file(self, directory):
        try:
            entries = os.listdir(directory)
        except OSError:
            return None
        base_name = os.path.basename(directory.rstrip(os.sep)) or 'project'
        preferred = os.path.join(directory, f"{base_name}.manga_proj")
        if os.path.isfile(preferred):
            return preferred
        candidates = []
        for name in entries:
            if name.lower().endswith('.manga_proj'):
                candidate_path = os.path.join(directory, name)
                try:
                    mtime = os.path.getmtime(candidate_path)
                except OSError:
                    continue
                candidates.append((mtime, candidate_path))
        if not candidates:
            return None
        candidates.sort(reverse=True)
        return candidates[0][1]

    def _make_project_file_path(self, preferred_name=None, base_dir=None):
        base_dir = os.path.abspath(base_dir or (self.project_dir or os.getcwd()))
        preferred = preferred_name or os.path.basename(base_dir.rstrip(os.sep)) or 'project'
        sanitized = re.sub(r'[\/:*?"<>|]', '_', preferred).strip()
        if not sanitized:
            sanitized = 'project'
        candidate = os.path.join(base_dir, f"{sanitized}.manga_proj")
        note = None
        if os.name == 'nt':
            abs_candidate = os.path.abspath(candidate)
            if len(abs_candidate) >= 245:
                digest = hashlib.sha256(abs_candidate.encode('utf-8')).hexdigest()[:10]
                candidate = os.path.join(base_dir, f"project_{digest}.manga_proj")
                note = f"Project filename shortened to avoid Windows path limit (using {os.path.basename(candidate)})."
        return candidate, note

    def _initialize_new_project(self, directory, status_message=None):
        self.project_dir = os.path.abspath(directory)
        self.cache_dir = os.path.join(self.project_dir, '.cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.all_typeset_data.clear()
        self.reset_history_state()
        folder_name = os.path.basename(self.project_dir.rstrip(os.sep)) or 'project'
        self.current_project_path, note = self._make_project_file_path(folder_name)
        if note:
            self.statusBar().showMessage(note, 6000)
        try:
            if self.project_dir not in self.file_watcher.directories():
                self.file_watcher.addPath(self.project_dir)
        except Exception:
            pass
        self.update_file_list()
        self.save_project(is_auto=True)
        if status_message is None:
            status_message = ActionText.NEW_PROJECT_AUTOSAVED
        self.setWindowTitle(app_title(os.path.basename(self.current_project_path)))
        self.statusBar().showMessage(status_message, 4000)
        # Sembunyikan welcome screen, tampilkan canvas
        self.hide_welcome_screen()

    def load_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Manga Folder", self.project_dir or "")
        if not dir_path:
            return
    
        dir_path = os.path.abspath(dir_path)
        current_dir = os.path.abspath(self.project_dir) if self.project_dir else None
        if current_dir and os.path.normcase(current_dir) == os.path.normcase(dir_path):
            return
    
        self.save_project(is_auto=True)
    
        if self.project_dir and self.project_dir in self.file_watcher.directories():
            try:
                self.file_watcher.removePath(self.project_dir)
            except Exception:
                pass
    
        if self.pdf_document:
            self.pdf_document.close()
            self.pdf_document = None
        self.current_pdf_page = -1
    
        project_file = self._find_project_file(dir_path)
        if project_file and os.path.isfile(project_file):
            if self._load_project_from_path(project_file, show_dialogs=False):
                self.statusBar().showMessage(f"Loaded project: {os.path.basename(project_file)}", 4000)
                return
            self.statusBar().showMessage("Failed to load existing project; starting new project.", 5000)
    
        self._initialize_new_project(dir_path)

    def load_item(self, file_path):
        # Save previous typeset areas before changing image path!
        if self.current_image_path:
            old_key = self.get_current_data_key(path=self.current_image_path, page=self.current_pdf_page if self.pdf_document else -1)
            self._update_typeset_record(old_key, areas=list(self.typeset_areas), redo=list(self.redo_stack))

        # Clear old confirmation state
        self.image_label.clear_detected_items()
        self.image_label.cancel_pending_item() # Hapus juga item yang menunggu

        self.current_image_path = file_path

        if not file_path.lower().endswith('.pdf') and self.pdf_document:
            self.pdf_document.close()
            self.pdf_document = None
            self.current_pdf_page = -1

        if file_path.lower().endswith('.pdf'):
            self.load_pdf(file_path)
        else:
            self.load_image(file_path)

        self.update_nav_buttons()

    def load_image(self, file_path):
        try:
            # Use robust opener to handle truncated/corrupt JPEGs
            self.current_image_pil = self.safe_open_image(file_path)

            key = self.get_current_data_key()
            img_data = self.all_typeset_data.get(key, {'areas': [], 'redo': []})
            cleaned_image = self._decode_cleaned_image(img_data)
            self._apply_base_image(cleaned_image or self.current_image_pil)
            self.typeset_areas = img_data['areas']
            self.redo_stack = img_data['redo']
            self.set_selected_area(None, notify=True)

            self.rebuild_history_for_image(key, self.typeset_areas)
            # Buang mask kuas inpaint halaman sebelumnya agar tidak diterapkan ke halaman baru
            if hasattr(self, 'image_label'):
                self.image_label.clear_inpaint_mask()
            self._set_compare_controls_checked(False)
            self._compare_mode_active = False
            self._refresh_inpaint_result_controls()
            # Reset undo timeline saat ganti halaman (Feature #1)
            self._undo_history.clear()
            self._undo_history_idx = -1
            self.redraw_all_typeset_areas()
            self.update_undo_redo_buttons_state()
            self._refresh_undo_timeline()
            self._refresh_detection_overlay()
            self.refresh_history_views()
            self._schedule_window_geometry_guard(rebalance=False)
        except Exception as e:
            self.show_banner("image-load-error", "Error loading image", f"Could not load image: {file_path}\nError: {e}", kind="error")
            self.clear_view()

    def load_pdf(self, file_path):
        try:
            if not self.pdf_document or self.pdf_document.name != file_path:
                if self.pdf_document: self.pdf_document.close()
                self.pdf_document = fitz.open(file_path)
                self.current_pdf_page = 0
            self.load_pdf_page(self.current_pdf_page)
        except Exception as e:
            self.show_banner("pdf-load-error", "Error loading PDF", f"Could not load PDF file: {file_path}\nError: {e}", kind="error")
            self.pdf_document = None
            self.current_pdf_page = -1

    def load_pdf_page(self, page_number):
        if not self.pdf_document or not (0 <= page_number < self.pdf_document.page_count):
            return

        if self.current_pdf_page != -1 and self.current_pdf_page != page_number:
            key = self.get_current_data_key(page=self.current_pdf_page)
            self._update_typeset_record(key, areas=self.typeset_areas, redo=self.redo_stack)

        self.current_pdf_page = page_number
        page = self.pdf_document.load_page(page_number)
        pix = page.get_pixmap(dpi=150)
        self.current_image_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        key = self.get_current_data_key()
        img_data = self.all_typeset_data.get(key, {'areas': [], 'redo': []})
        cleaned_image = self._decode_cleaned_image(img_data)
        self._apply_base_image(cleaned_image or self.current_image_pil)
        self.typeset_areas = img_data['areas']
        self.redo_stack = img_data['redo']
        self.set_selected_area(None, notify=True)

        self.rebuild_history_for_image(key, self.typeset_areas)
        # Buang mask kuas inpaint halaman sebelumnya agar tidak diterapkan ke halaman baru
        if hasattr(self, 'image_label'):
            self.image_label.clear_inpaint_mask()
        self._set_compare_controls_checked(False)
        self._compare_mode_active = False
        self._refresh_inpaint_result_controls()
        self.redraw_all_typeset_areas()
        self.update_undo_redo_buttons_state()
        self._refresh_detection_overlay()
        self.refresh_history_views()
        self.update_nav_buttons()
        self._schedule_window_geometry_guard(rebalance=False)

    def load_next_image(self):
        if self.is_in_confirmation_mode: return
        if self.pdf_document:
            if self.current_pdf_page < self.pdf_document.page_count - 1:
                self.load_pdf_page(self.current_pdf_page + 1)
        else:
            current_row = self.file_list_widget.currentRow()
            if current_row < self.file_list_widget.count() - 1:
                self.file_list_widget.setCurrentRow(current_row + 1)

    def load_prev_image(self):
        if self.is_in_confirmation_mode: return
        if self.pdf_document:
            if self.current_pdf_page > 0:
                self.load_pdf_page(self.current_pdf_page - 1)
        else:
            current_row = self.file_list_widget.currentRow()
            if current_row > 0:
                self.file_list_widget.setCurrentRow(current_row - 1)

    def save_image(self):
        if not self.typeset_pixmap:
            self.show_banner("save-image-no-image", "No image", "There is no image to save.", kind="warning")
            return

        # Get settings
        gen_cfg = SETTINGS.get('general', {})
        def_fmt = gen_cfg.get('save_format', 'PNG').upper()
        quality = int(gen_cfg.get('save_quality', 95))
        
        ext_map = {'PNG': '.png', 'JPG': '.jpg', 'JPEG': '.jpg', 'WEBP': '.webp'}
        def_ext = ext_map.get(def_fmt, '.png')
        
        filters = "PNG Image (*.png);;JPEG Image (*.jpg);;WebP Image (*.webp)"
        
        # Select filter based on setting
        initial_filter = ""
        if 'PNG' in def_fmt: initial_filter = "PNG Image (*.png)"
        elif 'JPG' in def_fmt or 'JPEG' in def_fmt: initial_filter = "JPEG Image (*.jpg)"
        elif 'WEBP' in def_fmt: initial_filter = "WebP Image (*.webp)"

        if self.pdf_document:
            original_filename = os.path.basename(self.current_image_path)
            name, _ = os.path.splitext(original_filename)
            save_suggestion = os.path.join(os.path.dirname(self.current_image_path), f"{name}_page_{self.current_pdf_page + 1}_typeset{def_ext}")
        else:
            original_filename = os.path.basename(self.current_image_path)
            name, _ = os.path.splitext(original_filename)
            save_suggestion = os.path.join(os.path.dirname(self.current_image_path), f"{name}_typeset{def_ext}")

        filePath, _ = QFileDialog.getSaveFileName(self, "Save Typeset Image", save_suggestion, filters, initial_filter)
        if filePath:
            # Non-blocking save: copy QPixmap to QImage under mutex, then save in background
            self.paint_mutex.lock()
            try:
                pix_copy = self.typeset_pixmap.copy()
                qimage = pix_copy.toImage().copy()
            finally:
                self.paint_mutex.unlock()

            # Start background worker to save the QImage
            # We let the worker infer format from extension, but pass quality preference
            image_worker = ImageSaveWorker(qimage, filePath, quality=quality)
            image_thread = QThread()
            image_worker.moveToThread(image_thread)

            image_worker.finished.connect(self.on_image_save_finished)
            image_worker.error.connect(self.on_image_save_error)

            self.image_save_worker = image_worker
            self.image_save_thread = image_thread
            image_thread.started.connect(image_worker.run)
            image_thread.start()

    def on_image_save_finished(self, success, message):
        if self.image_save_thread:
            try:
                self.image_save_thread.quit()
                self.image_save_thread.wait()
            except Exception:
                pass
            self.image_save_thread = None
        self.image_save_worker = None
        if success:
            self.show_toast("Image saved", message, kind="success")
        else:
            self.show_banner("image-save-error", "Image save failed", message, kind="error")

    def on_image_save_error(self, msg):
        self.show_banner("image-save-error", "Image save failed", msg, kind="error")

    def _build_project_payload(self):
        self._snapshot_current_image_state()
        payload = {
            'schema_version': 2,
            'project_dir': os.path.abspath(self.project_dir) if self.project_dir else None,
            'current_image_path': self.current_image_path,
            'current_pdf_page': int(self.current_pdf_page) if isinstance(self.current_pdf_page, int) else -1,
            'typeset_data': self._serialize_typeset_map(),
            'history_entries': copy.deepcopy(self.history_entries),
            'proofreader_entries': copy.deepcopy(self.proofreader_entries),
            'quality_entries': copy.deepcopy(self.quality_entries),
            'history_counter': int(self.history_counter),
            'typeset_font': TypesetArea.font_to_dict(self.typeset_font),
            'typeset_color': self.typeset_color.name(),
            'typeset_defaults': copy.deepcopy(self.typeset_defaults),
            'settings': self._collect_project_settings(),
            'scenes': copy.deepcopy(self.scenes),
            'scene_order': copy.deepcopy(self.scene_order),
            'current_scene_name': self.current_scene_name,
            'saved_at': time.time(),
            'app_version': APP_VERSION,
        }
        config_block = {'theme': self.current_theme}
        if getattr(self, 'autosave_timer', None):
            config_block['autosave_interval_ms'] = int(self.autosave_timer.interval())
        payload['config'] = config_block
        return payload

    def _read_project_file(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
        return data, 'json'

    def _apply_project_payload(self, payload, project_path):
        warnings = []
        project_file_dir = os.path.abspath(os.path.dirname(project_path))

        # --- Resolve project_dir: prefer relative path, fallback to absolute ---
        project_dir = None
        rel_project_dir = payload.get('project_dir_rel')
        abs_project_dir = payload.get('project_dir')

        if rel_project_dir:
            # Try resolving relative path against .manga_proj file location
            resolved = os.path.normpath(os.path.join(project_file_dir, rel_project_dir))
            if os.path.isdir(resolved):
                project_dir = resolved

        if not project_dir and abs_project_dir:
            # Fallback to absolute path (backward compatibility with schema_version <= 2)
            abs_candidate = os.path.abspath(abs_project_dir)
            if os.path.isdir(abs_candidate):
                project_dir = abs_candidate

        if not project_dir:
            fallback_dir = project_file_dir
            if abs_project_dir:
                warnings.append(f"Project directory not found: {abs_project_dir}. Using {fallback_dir} instead.")
            else:
                warnings.append("Project directory missing in save data; using project file location.")
            project_dir = fallback_dir
        self.project_dir = project_dir
        self.cache_dir = os.path.join(self.project_dir, '.cache')
        os.makedirs(self.cache_dir, exist_ok=True)

        self.reset_history_state()

        try:
            if self.project_dir not in self.file_watcher.directories():
                self.file_watcher.addPath(self.project_dir)
        except Exception:
            pass

        font_info = payload.get('typeset_font') or {}
        try:
            self.typeset_font = TypesetArea.font_from_dict(font_info)
        except Exception as exc:
            self.typeset_font = QFont('Arial', 9, QFont.Bold)
            warnings.append(f"Failed to load project font: {exc}; default font applied.")
        color_value = payload.get('typeset_color', '#000000')
        color_obj = QColor(color_value)
        if not color_obj.isValid():
            warnings.append(f"Invalid text color '{color_value}', using black.")
            color_obj = QColor('#000000')
        self.typeset_color = color_obj

        defaults_payload = payload.get('typeset_defaults')
        if isinstance(defaults_payload, dict):
            self.typeset_defaults = defaults_payload
        else:
            self.typeset_defaults = self._create_initial_typeset_defaults()
        self._apply_typeset_defaults()

        project_settings_payload = payload.get('settings')
        if isinstance(project_settings_payload, dict):
            cleanup_block = project_settings_payload.get('cleanup')
            if isinstance(cleanup_block, dict):
                apply_mode_value = cleanup_block.get('apply_mode')
                if apply_mode_value in ('global', 'selected') and getattr(self, 'apply_mode_global_radio', None):
                    try:
                        selected_radio = self.apply_mode_selected_radio
                        global_radio = self.apply_mode_global_radio
                        with QSignalBlocker(selected_radio), QSignalBlocker(global_radio):
                            global_radio.setChecked(apply_mode_value == 'global')
                            selected_radio.setChecked(apply_mode_value != 'global')
                    except Exception:
                        pass
                    self._set_global_cleanup_default('apply_mode', apply_mode_value)
                    if getattr(self, 'apply_mode_status_label', None):
                        self.apply_mode_status_label.setText("Mode: Global" if apply_mode_value == 'global' else "Mode: Selected Area")
                if 'use_background_box' in cleanup_block:
                    self._set_global_cleanup_default('use_background_box', bool(cleanup_block['use_background_box']))
                if 'use_inpaint' in cleanup_block:
                    self._set_global_cleanup_default('use_inpaint', bool(cleanup_block['use_inpaint']))
                if 'constrain_text' in cleanup_block:
                    self._set_global_cleanup_default('constrain_text', bool(cleanup_block['constrain_text']))
            self._sync_cleanup_controls_from_selection()

        serialized_typeset = payload.get('typeset_data') or payload.get('all_data') or {}
        # Pass project_dir so schema-v4 basename keys can be resolved to full paths
        typeset_map, type_warnings = self._deserialize_typeset_map(
            serialized_typeset, self.typeset_font, self.typeset_color,
            project_dir=self.project_dir,
        )
        warnings.extend(type_warnings)
        self.all_typeset_data = typeset_map

        area_lookup = {}
        area_id_max = 0
        for key, record in self.all_typeset_data.items():
            cleaned_areas = []
            for area in record.get('areas', []):
                if not isinstance(area, TypesetArea):
                    continue
                hist_id = getattr(area, 'history_id', None)
                if hist_id:
                    hist_id = str(hist_id)
                    area.history_id = hist_id
                    if hist_id.startswith('H') and hist_id[1:].isdigit():
                        area_id_max = max(area_id_max, int(hist_id[1:]))
                    area_lookup[hist_id] = {'image_key': key, 'area': area}
                cleaned_areas.append(area)
            record['areas'] = cleaned_areas
            redo_clean = []
            for redo_area in record.get('redo', []):
                if isinstance(redo_area, TypesetArea):
                    redo_area.history_id = str(getattr(redo_area, 'history_id', '') or '') or None
                redo_clean.append(redo_area)
            record['redo'] = redo_clean

        history_data = payload.get('history_entries')
        sanitized_history, history_max = self._sanitize_history_entries(history_data, area_lookup, warnings)

        counter_from_payload = payload.get('history_counter')
        if isinstance(counter_from_payload, str) and counter_from_payload.isdigit():
            counter_from_payload = int(counter_from_payload)
        elif not isinstance(counter_from_payload, int):
            counter_from_payload = 0

        self.history_counter = max(counter_from_payload, history_max, area_id_max)
        self.history_entries = sanitized_history
        existing_ids = {entry['history_id'] for entry in self.history_entries}

        for key, record in self.all_typeset_data.items():
            for area in record['areas']:
                hist_id = getattr(area, 'history_id', None)
                if hist_id and hist_id not in existing_ids:
                    if hist_id.startswith('H') and hist_id[1:].isdigit():
                        self.history_counter = max(self.history_counter, int(hist_id[1:]))
                    new_entry = {
                        'id': hist_id,
                        'history_id': hist_id,
                        'image_key': key,
                        'original_text': area.original_text or '',
                        'translated_text': area.text or '',
                        'translation_style': getattr(area, 'translation_style', ''),
                        'timestamp': time.time(),
                    }
                    self.history_entries.append(new_entry)
                    existing_ids.add(hist_id)
                    area_lookup[hist_id] = {'image_key': key, 'area': area}
                if not hist_id:
                    new_id = self.generate_history_id()
                    area.history_id = new_id
                    new_entry = {
                        'id': new_id,
                        'history_id': new_id,
                        'image_key': key,
                        'original_text': area.original_text or '',
                        'translated_text': area.text or '',
                        'translation_style': getattr(area, 'translation_style', ''),
                        'timestamp': time.time(),
                    }
                    self.history_entries.append(new_entry)
                    existing_ids.add(new_id)
                    area_lookup[new_id] = {'image_key': key, 'area': area}

        proof_entries = self._sanitize_review_entries(payload.get('proofreader_entries'))
        quality_entries = self._sanitize_review_entries(payload.get('quality_entries'))
        self.proofreader_entries = proof_entries
        self.quality_entries = quality_entries

        # Load Scenes
        loaded_scenes = payload.get('scenes', {})
        loaded_scene_order = payload.get('scene_order', [])
        loaded_current_scene = payload.get('current_scene_name')

        if isinstance(loaded_scenes, dict):
            # Sanitize scenes
            clean_scenes = {}
            for s_name, s_entries in loaded_scenes.items():
                if isinstance(s_name, str) and isinstance(s_entries, list):
                    clean_scenes[s_name] = self._sanitize_review_entries(s_entries)
            self.scenes = clean_scenes
        else:
            self.scenes = {}

        if isinstance(loaded_scene_order, list):
            self.scene_order = [s for s in loaded_scene_order if isinstance(s, str) and s in self.scenes]
            # Ensure all scenes are in order list
            for s_name in self.scenes:
                if s_name not in self.scene_order:
                    self.scene_order.append(s_name)
        else:
            self.scene_order = list(self.scenes.keys())

        if isinstance(loaded_current_scene, str) and loaded_current_scene in self.scenes:
            self.current_scene_name = loaded_current_scene
        elif self.scene_order:
            self.current_scene_name = self.scene_order[0]
        else:
            self.current_scene_name = None

        self.history_lookup.clear()
        for hist_id, info in area_lookup.items():
            if hist_id in existing_ids:
                self.history_lookup[hist_id] = info

        # --- Resolve current_image_path: prefer relative, fallback to absolute ---
        rel_image_path = payload.get('current_image_path_rel')
        abs_image_path = payload.get('current_image_path')
        saved_image_path = None

        if rel_image_path:
            resolved_img = os.path.normpath(os.path.join(project_file_dir, rel_image_path))
            if os.path.isfile(resolved_img):
                saved_image_path = resolved_img

        if not saved_image_path and abs_image_path:
            if os.path.isfile(abs_image_path):
                saved_image_path = abs_image_path

        saved_pdf_page = payload.get('current_pdf_page', -1)
        self.current_pdf_page = int(saved_pdf_page) if isinstance(saved_pdf_page, int) else -1
        self.current_project_path = os.path.abspath(project_path)

        self.update_file_list()
        if saved_image_path and saved_image_path in self.image_files:
            row = self.image_files.index(saved_image_path)
            self.file_list_widget.setCurrentRow(row)
        elif saved_image_path and self.image_files:
            # Try matching by filename basename as last resort (e.g. folder moved but files intact)
            target_basename = os.path.basename(saved_image_path)
            matched = [f for f in self.image_files if os.path.basename(f) == target_basename]
            if matched:
                row = self.image_files.index(matched[0])
                self.file_list_widget.setCurrentRow(row)
            else:
                self.file_list_widget.setCurrentRow(0)
                warnings.append(f"Image '{target_basename}' not found in folder; opened first file instead.")
        elif self.image_files:
            self.file_list_widget.setCurrentRow(0)

        self.refresh_history_views()
        # Sembunyikan welcome screen, tampilkan canvas
        self.hide_welcome_screen()
        return warnings

    def _load_project_from_path(self, file_path, *, show_dialogs=True):
        warnings = []
        # Auto-save current project before switching
        self.save_project(is_auto=True)

        # Hapus watcher lama
        if self.project_dir and self.project_dir in self.file_watcher.directories():
            try:
                self.file_watcher.removePath(self.project_dir)
            except Exception:
                pass

        # Tutup PDF lama jika ada
        if self.pdf_document:
            self.pdf_document.close()
            self.pdf_document = None
        self.current_pdf_page = -1

        try:
            payload, fmt = self._read_project_file(file_path)

            warnings = self._apply_project_payload(payload, file_path)

            # Update judul window
            self.setWindowTitle(
                app_title(os.path.basename(self.current_project_path))
            )

            # Start autosave only if user enabled it
            try:
                if getattr(self, 'autosave_enabled', True):
                    self.autosave_timer.start()
            except Exception:
                pass

            # Tampilkan warning jika ada
            if warnings and show_dialogs:
                self.show_banner(
                    "project-load-warnings",
                    "Project loaded with warnings",
                    "\n".join(warnings),
                    kind="warning",
                )

            # Info success
            if show_dialogs:
                self.show_toast("Project loaded", "Project loaded successfully.", kind="success")
            elif warnings:
                self.statusBar().showMessage("; ".join(warnings), 5000)

            # Tambahkan ke recent projects
            self._add_to_recent_projects(file_path)

            return True

        except Exception as exc:
            if show_dialogs:
                self.show_banner("project-load-error", "Project load failed", str(exc), kind="error")
            else:
                self.statusBar().showMessage(f"Failed to load project: {exc}", 5000)
            return False

    def save_project(self, is_auto=False):
        if not self.project_dir:
            if not is_auto:
                self.show_banner("save-project-no-folder", "No project", "Please load a folder before saving a project.", kind="warning")
            return False

        # ponytail: guard must stay ABOVE the snapshot build — the snapshot serializes the
        # whole project on the GUI thread under paint_mutex, so a rejected save must bail first.
        if getattr(self, 'project_save_thread', None) and getattr(self, 'project_save_thread', None).isRunning():
            if not is_auto:
                self.show_toast("Save in progress", "A project save is already running.", kind="info")
            return False

        # Commit active typeset areas to in-memory dictionary first to avoid copy-paste loss
        if self.current_image_path:
            key = self.get_current_data_key()
            self._update_typeset_record(key, areas=list(self.typeset_areas), redo=list(self.redo_stack))

        if not self.current_project_path:
            if is_auto:
                self.current_project_path, note = self._make_project_file_path()
                if note:
                    self.statusBar().showMessage(note, 6000)
            else:
                suggested_name = os.path.basename(self.project_dir.rstrip(os.sep)) if self.project_dir else 'project'
                default_path = os.path.join(self.project_dir, f"{suggested_name}.manga_proj") if self.project_dir else ''
                file_path, _ = QFileDialog.getSaveFileName(self, "Save Project", default_path, "Manga Project (*.manga_proj)")
                if not file_path:
                    return False
                if not file_path.lower().endswith('.manga_proj'):
                    file_path += '.manga_proj'
                chosen_path = os.path.abspath(file_path)
                if os.name == 'nt' and len(chosen_path) >= 245:
                    preferred = os.path.splitext(os.path.basename(chosen_path))[0]
                    shortened, note = self._make_project_file_path(preferred, os.path.dirname(chosen_path))
                    if len(os.path.abspath(shortened)) >= 245:
                        shortened, note = self._make_project_file_path(preferred)
                    self.current_project_path = shortened
                    if note:
                        self.statusBar().showMessage(note, 6000)
                else:
                    self.current_project_path = chosen_path
        else:
            if os.name == 'nt' and len(os.path.abspath(self.current_project_path)) >= 245:
                preferred = os.path.splitext(os.path.basename(self.current_project_path))[0]
                base_dir = os.path.dirname(self.current_project_path)
                shortened, note = self._make_project_file_path(preferred, base_dir)
                if len(os.path.abspath(shortened)) >= 245:
                    shortened, note = self._make_project_file_path(preferred)
                if shortened != self.current_project_path:
                    self.current_project_path = shortened
                    if note:
                        self.statusBar().showMessage(note, 6000)

        # Create a quick snapshot under mutex to avoid races, then perform heavy IO in background
        try:
            self.paint_mutex.lock()
            try:
                serialized_typeset = {}
                for k, rec in (self.all_typeset_data or {}).items():
                    try:
                        areas = rec.get('areas', []) or []
                        redo = rec.get('redo', []) or []
                        serialized_typeset[k] = {
                            'areas': [area.to_payload() if isinstance(area, TypesetArea) else area for area in areas],
                            'redo': [r.to_payload() if isinstance(r, TypesetArea) else r for r in redo],
                        }
                        for image_state_key in ('cleaned_image_png', 'pre_inpaint_image_png'):
                            if rec.get(image_state_key):
                                serialized_typeset[k][image_state_key] = rec.get(image_state_key)
                    except Exception:
                        serialized_typeset[k] = {'areas': [], 'redo': []}

                snapshot = {
                    'project_dir': self.project_dir,
                    'current_image_path': self.current_image_path,
                    'current_pdf_page': int(self.current_pdf_page) if isinstance(self.current_pdf_page, int) else -1,
                    'typeset_data': serialized_typeset,
                    'history_entries': list(self.history_entries) if getattr(self, 'history_entries', None) is not None else [],
                    'proofreader_entries': list(self.proofreader_entries) if getattr(self, 'proofreader_entries', None) is not None else [],
                    'quality_entries': list(self.quality_entries) if getattr(self, 'quality_entries', None) is not None else [],
                    'history_counter': int(self.history_counter) if getattr(self, 'history_counter', None) is not None else 0,
                    'typeset_font': TypesetArea.font_to_dict(self.typeset_font) if getattr(self, 'typeset_font', None) else None,
                    'typeset_color': self.typeset_color.name() if getattr(self, 'typeset_color', None) else '#000000',
                    'settings': self._collect_project_settings() if hasattr(self, '_collect_project_settings') else {},
                    'app_version': APP_VERSION,
                }
            finally:
                self.paint_mutex.unlock()
        except Exception as exc:
            if not is_auto:
                self.show_banner("project-save-prepare-error", "Project save failed", f"Failed to prepare project data: {exc}", kind="error")
            return False
        # Ensure target directory exists
        target_dir = os.path.dirname(self.current_project_path) or (self.project_dir or os.getcwd())
        try:
            os.makedirs(target_dir, exist_ok=True)
        except OSError:
            pass

        # Store save state
        self.project_save_is_auto = is_auto

        # Start background worker to write the project file
        worker = ProjectSaveWorker(self.current_project_path, snapshot)
        thread = QThread()
        worker.moveToThread(thread)

        worker.finished.connect(self.on_project_save_finished)
        worker.error.connect(self.on_project_save_error)
        
        # Clean up asynchronously to avoid GIL deadlocks on the GUI thread
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_save_thread_finished)

        # store references so we can cancel/inspect
        self.project_save_worker = worker
        self.project_save_thread = thread

        thread.started.connect(worker.run)
        thread.start()
        # Let autosave or UI continue; indicate to user
        if not is_auto:
            self.statusBar().showMessage("Saving project in background...", 3000)
        return True

    def on_project_save_finished(self, success, message):
        is_auto = getattr(self, 'project_save_is_auto', False)
        if not is_auto:
            if success:
                self.show_toast("Project saved", message, kind="success")
            else:
                self.show_banner("project-save-error", "Project save failed", message, kind="error")

    def _on_save_thread_finished(self):
        self.project_save_thread = None
        self.project_save_worker = None

    def on_project_save_error(self, msg):
        self.show_banner("project-save-error", "Project save failed", msg, kind="error")

    def auto_save_project(self):
        if QApplication.activeModalWidget() is not None:
            return 
    
        if self.current_project_path and os.path.exists(os.path.dirname(self.current_project_path)):
            if self.save_project(is_auto=True): 
                self.statusBar().showMessage(f"Project auto-saved at {time.strftime('%H:%M:%S')}", 3000)

    def load_project(self):
        default_dir = self.project_dir or ''
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Project", default_dir, "Manga Project (*.manga_proj)")
        if not file_path:
            return
        self._load_project_from_path(file_path)

    def _make_recent_project_card(self, proj_path: str):
        """Buat satu kartu recent project."""
        from PyQt5.QtWidgets import (
            QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
        )
        from PyQt5.QtCore import Qt
        import os, time

        card = QWidget()
        card.setFixedHeight(68)
        card.setCursor(Qt.PointingHandCursor)
        exists = os.path.isfile(proj_path)
        card_bg = theme.COLORS["card_alt"] if exists else theme.COLORS["panel"]
        card_hover = theme.COLORS["panel"] if exists else theme.COLORS["card_alt"]
        card_border = theme.COLORS["border"] if exists else theme.COLORS["danger"]
        card_accent = theme.COLORS["accent"] if exists else theme.COLORS["danger"]
        name_color = theme.COLORS["text"] if exists else theme.COLORS["danger"]
        card.setStyleSheet(f"""
            QWidget {{
                background: {card_bg};
                border: 1px solid {card_border};
                border-radius: 10px;
            }}
            QWidget:hover {{
                background: {card_hover};
                border-color: {card_accent};
            }}
        """)

        h = QHBoxLayout(card)
        h.setContentsMargins(12, 8, 8, 8)
        h.setSpacing(10)

        icon_lbl = QLabel("🗂️" if exists else "⚠️")
        icon_lbl.setFixedWidth(28)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 18pt; background: transparent; border: none;")

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        name_lbl = QLabel(os.path.basename(proj_path))
        name_lbl.setStyleSheet(f"""
            color: {name_color};
            font-size: 9.5pt;
            font-weight: 600;
            font-family: {theme.FONT_FAMILY};
            background: transparent;
            border: none;
        """)
        name_lbl.setToolTip(proj_path)
        path_lbl = QLabel(os.path.dirname(proj_path))
        path_lbl.setStyleSheet(f"""
            color: {theme.COLORS["muted"]};
            font-size: 8pt;
            font-family: {theme.FONT_FAMILY};
            background: transparent;
            border: none;
        """)
        path_lbl.setToolTip(proj_path)
        # Truncate path kalau terlalu panjang
        max_chars = 45
        dir_text = os.path.dirname(proj_path)
        if len(dir_text) > max_chars:
            dir_text = "…" + dir_text[-(max_chars - 1):]
        path_lbl.setText(dir_text)

        info_col.addWidget(name_lbl)
        info_col.addWidget(path_lbl)

        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(20, 20)
        remove_btn.setCursor(Qt.PointingHandCursor)
        remove_btn.setToolTip("Remove from recent list")
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {theme.COLORS["muted"]};
                border: none;
                font-size: 9pt;
                font-weight: bold;
                border-radius: 10px;
                padding: 0;
            }}
            QPushButton:hover {{ color: {theme.COLORS["danger"]}; background: {theme.COLORS["card_alt"]}; }}
        """)
        remove_btn.clicked.connect(lambda checked=False, p=proj_path: self._remove_single_recent(p))

        h.addWidget(icon_lbl)
        h.addLayout(info_col, 1)
        h.addWidget(remove_btn)

        # Klik card (bukan tombol ✕) → buka project
        # Gunakan mousePressEvent pada card
        def card_clicked(event, p=proj_path):
            from PyQt5.QtCore import Qt
            if event.button() == Qt.LeftButton:
                self.open_recent_project(p)

        card.mousePressEvent = card_clicked
        return card

    def _rebuild_recent_projects_menu(self):
        """Membangun ulang submenu Recent Projects dari settings."""
        menu = getattr(self, 'recent_projects_menu', None)
        if not menu:
            return
        menu.clear()
        recent = SETTINGS.get('recent_projects', [])
        if not recent:
            no_action = menu.addAction('(No recent projects)')
            no_action.setEnabled(False)
            self._refresh_welcome_screen()
            return
        for proj_path in recent:
            display = os.path.basename(proj_path)
            action = menu.addAction(display)
            action.setToolTip(proj_path)
            action.triggered.connect(lambda checked=False, p=proj_path: self.open_recent_project(p))
        menu.addSeparator()
        clear_action = menu.addAction('Clear Recent')
        clear_action.triggered.connect(self._clear_recent_projects)
        # Sinkronkan welcome screen agar kartu recent selalu up-to-date
        self._refresh_welcome_screen()

    def _add_to_recent_projects(self, file_path: str):
        """Tambahkan path project ke recent projects (max 10 entri)."""
        if not file_path:
            return
        recent = list(SETTINGS.get('recent_projects', []))
        # Hapus jika sudah ada (akan di-push ke atas)
        if file_path in recent:
            recent.remove(file_path)
        recent.insert(0, file_path)
        # Batasi 10 entri
        SETTINGS['recent_projects'] = recent[:10]
        save_settings(SETTINGS)
        self._rebuild_recent_projects_menu()

    def _clear_recent_projects(self):
        """Hapus semua entri recent projects."""
        SETTINGS['recent_projects'] = []
        save_settings(SETTINGS)
        self._rebuild_recent_projects_menu()

    def open_recent_project(self, file_path: str):
        """Buka project dari recent projects list."""
        if not os.path.exists(file_path):
            self.show_banner(
                "recent-project-missing",
                "File not found",
                f"Project file not found:\n{file_path}\n\nIt will be removed from recent projects.",
                kind="warning",
            )
            recent = list(SETTINGS.get('recent_projects', []))
            if file_path in recent:
                recent.remove(file_path)
            SETTINGS['recent_projects'] = recent
            save_settings(SETTINGS)
            self._rebuild_recent_projects_menu()
            return
        self._load_project_from_path(file_path)

    def show_project_stats_dialog(self):
        """Tampilkan dialog statistik project saat ini."""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QScrollArea, QWidget, QGridLayout, QFrame

        if not self.project_dir:
            self.show_toast("No project", "Load a folder/project first.", kind="info")
            return

        # --- Hitung statistik ---
        total_pages = len([f for f in self.image_files if "_typeset" not in f.lower()])
        pages_with_typeset = 0
        total_areas = 0
        total_words = 0
        areas_with_text = 0
        empty_areas = 0
        model_usage = {}

        for key, data in self.all_typeset_data.items():
            areas = data.get('areas', [])
            if areas:
                pages_with_typeset += 1
            for area in areas:
                total_areas += 1
                text = ''
                if hasattr(area, 'text'):
                    text = area.text or ''
                elif isinstance(area, dict):
                    text = area.get('text', '') or ''
                if text.strip():
                    areas_with_text += 1
                    total_words += len(text.split())
                else:
                    empty_areas += 1
                # Model usage
                model_label = None
                if hasattr(area, 'review_notes') and isinstance(area.review_notes, dict):
                    model_label = area.review_notes.get('ai_model')
                elif isinstance(area, dict):
                    model_label = area.get('ai_model_label') or area.get('ai_model')
                    if not model_label and 'review_notes' in area and isinstance(area['review_notes'], dict):
                        model_label = area['review_notes'].get('ai_model')

                if isinstance(model_label, (list, tuple)) and len(model_label) >= 2:
                    model_label = f"{model_label[0]} ({model_label[1]})"
                elif not model_label or not isinstance(model_label, str):
                    model_label = 'Unknown'

                model_usage[model_label] = model_usage.get(model_label, 0) + 1

        completion_pct = round((pages_with_typeset / total_pages * 100), 1) if total_pages > 0 else 0.0
        area_completion_pct = round((areas_with_text / total_areas * 100), 1) if total_areas > 0 else 0.0
        session_cost_idr = int(self.total_cost * self.usd_to_idr_rate)

        # --- Dialog ---
        dlg = QDialog(self)
        dlg.setWindowTitle("\U0001f4ca Project Statistics")
        dlg.setModal(True)
        dlg.resize(420, 500)

        scroll = QScrollArea(dlg)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        vbox = QVBoxLayout(inner)
        vbox.setContentsMargins(20, 16, 20, 16)
        vbox.setSpacing(14)

        def make_section(title):
            lbl = QLabel(f"<b style='color:#38bdf8; font-size:11pt;'>{title}</b>")
            vbox.addWidget(lbl)
            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setStyleSheet("color: #1e293b;")
            vbox.addWidget(sep)

        def make_row(label, value):
            row = QLabel(f"<span style='color:#94a3b8;'>{label}:</span>  <b style='color:#f1f5f9;'>{value}</b>")
            row.setTextFormat(Qt.RichText)
            vbox.addWidget(row)

        make_section("\U0001f4c1 Project")
        make_row("Folder", os.path.basename(self.project_dir))
        make_row("Total Pages", str(total_pages))
        make_row("Pages with Typeset", f"{pages_with_typeset} ({completion_pct}%)")

        make_section("\u270f\ufe0f Areas")
        make_row("Total Areas", str(total_areas))
        make_row("Areas with Text", f"{areas_with_text} ({area_completion_pct}%)")
        make_row("Empty Areas", str(empty_areas))
        make_row("Total Words Translated", f"{total_words:,}")

        make_section("\U0001f4b0 Session Cost")
        make_row("Estimated Cost", f"${self.total_cost:.6f}  (~Rp {session_cost_idr:,})")
        make_row("Snippets Translated", str(getattr(self, 'translated_count', 0)))

        if model_usage:
            make_section("\U0001f916 Model Usage (areas)")
            for model, count in sorted(model_usage.items(), key=lambda x: -x[1]):
                make_row(model, str(count))

        vbox.addStretch(1)
        scroll.setWidget(inner)

        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(0, 0, 0, 12)
        outer.addWidget(scroll, 1)

        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(dlg.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(close_btn)
        outer.addLayout(btn_row)

        dlg.exec_()

    def _on_unified_pricing_saved(self, updated_providers: dict, updated_openrouter_db: dict):
        """
        Callback dari UnifiedHelpDialog saat user menyimpan perubahan harga.
        Update AI_PROVIDERS dan openrouter_pricing_db agar add_api_cost pakai harga baru.
        """
        # Update pricing per model di AI_PROVIDERS
        for provider, models in updated_providers.items():
            if provider not in self.AI_PROVIDERS:
                self.AI_PROVIDERS[provider] = {}
            for model_id, info in models.items():
                if model_id in self.AI_PROVIDERS[provider]:
                    self.AI_PROVIDERS[provider][model_id]['pricing'] = info.get('pricing', {})
                    if isinstance(info.get('limits'), dict):
                        self.AI_PROVIDERS[provider][model_id]['limits'] = info.get('limits', {})
                else:
                    self.AI_PROVIDERS[provider][model_id] = info

        # Update openrouter_pricing_db
        for model_id, info in updated_openrouter_db.items():
            if not hasattr(self, 'openrouter_pricing_db'):
                self.openrouter_pricing_db = {}
            if model_id in self.openrouter_pricing_db:
                self.openrouter_pricing_db[model_id]['pricing'] = info.get('pricing', {})
                if isinstance(info.get('limits'), dict):
                    self.openrouter_pricing_db[model_id]['limits'] = info.get('limits', {})
            else:
                self.openrouter_pricing_db[model_id] = info

        try:
            self._persist_ai_model_overrides_to_settings()
        except Exception as exc:
            print(f"Could not persist model overrides: {exc}")

        self.show_toast("Pricing updated", "Harga model dan limit RPM/RPD berhasil diperbarui.", kind="success")

    def export_to_pdf(self):
        if not self.project_dir:
            self.show_banner("export-no-folder", "No folder loaded", "Please load a folder containing images first.", kind="warning")
            return

        image_files_to_export = []
        for file_path in self.image_files:
            if "_typeset" in file_path.lower():
                continue

            path_part, ext = os.path.splitext(file_path)
            typeset_path = f"{path_part}_typeset.png"

            if os.path.exists(typeset_path):
                image_files_to_export.append(typeset_path)

        if not image_files_to_export:
            self.show_banner("export-no-typeset-files", "No typeset files found", "No '_typeset.png' files were found in the current folder to export.", kind="warning")
            return

        folder_name = os.path.basename(self.project_dir)
        save_suggestion = os.path.join(self.project_dir, f"{folder_name}_typeset.pdf")

        pdf_path, _ = QFileDialog.getSaveFileName(self, "Save Typeset PDF As", save_suggestion, "PDF Files (*.pdf)")
        if not pdf_path: return

        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', os.path.basename(s))]

        image_files_to_export.sort(key=natural_sort_key)

        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.statusBar().showMessage("Exporting to PDF... Please wait.")

        try:
            images_pil = []
            for i, f in enumerate(image_files_to_export):
                self.overall_progress_bar.setVisible(True)
                self.update_overall_progress(int((i/len(image_files_to_export))*100), f"Converting {os.path.basename(f)}...")
                img = Image.open(self._get_safe_path(f)).convert("RGB")
                images_pil.append(img)

            if images_pil:
                self.update_overall_progress(100, "Saving PDF...")
                images_pil[0].save(self._get_safe_path(pdf_path), "PDF", resolution=100.0, save_all=True, append_images=images_pil[1:])
                self.show_toast("PDF exported", f"Exported {len(images_pil)} typeset images to {pdf_path}", kind="success", timeout_ms=5000)
            else:
                raise Exception("No images could be processed.")

        except Exception as e:
            self.show_banner("pdf-export-error", "PDF export failed", str(e), kind="error")
        finally:
            QApplication.restoreOverrideCursor() # DIUBAH: hapus argumen
            self.overall_progress_bar.setVisible(False)
            self.statusBar().showMessage("Ready", 3000)

    def export_to_cbz(self):
        """Export semua halaman yang sudah di-typeset ke format CBZ (Comic Book Zip)."""
        if not self.project_dir:
            self.show_banner("export-no-folder", "No folder loaded", "Please load a folder containing images first.", kind="warning")
            return

        import zipfile

        # Kumpulkan file yang sudah di-typeset
        image_files_to_export = []
        for file_path in self.image_files:
            if "_typeset" in file_path.lower():
                continue
            path_part, _ = os.path.splitext(file_path)
            for ext in ('_typeset.png', '_typeset.webp', '_typeset.jpg'):
                typeset_path = f"{path_part}{ext}"
                if os.path.exists(typeset_path):
                    image_files_to_export.append(typeset_path)
                    break

        if not image_files_to_export:
            self.show_banner(
                "export-no-typeset-files",
                "No typeset files found",
                "No typeset images were found. Please run Batch Save first to generate typeset files.",
                kind="warning",
            )
            return

        # Urutkan secara natural (1, 2, 10 bukan 1, 10, 2)
        def natural_sort_key(s):
            return [int(t) if t.isdigit() else t.lower()
                    for t in re.split('([0-9]+)', os.path.basename(s))]
        image_files_to_export.sort(key=natural_sort_key)

        # Dialog simpan
        folder_name = os.path.basename(self.project_dir)
        save_suggestion = os.path.join(self.project_dir, f"{folder_name}_typeset.cbz")
        cbz_path, _ = QFileDialog.getSaveFileName(
            self, "Save Typeset CBZ As", save_suggestion, "Comic Book Zip (*.cbz)")
        if not cbz_path:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.statusBar().showMessage("Exporting to CBZ... Please wait.")
        self.overall_progress_bar.setVisible(True)

        try:
            with zipfile.ZipFile(self._get_safe_path(cbz_path), 'w', zipfile.ZIP_DEFLATED) as zf:
                total = len(image_files_to_export)
                for i, img_path in enumerate(image_files_to_export):
                    self.update_overall_progress(
                        int(((i + 1) / total) * 100),
                        f"Adding {os.path.basename(img_path)}..."
                    )
                    # Tambahkan file ke zip dengan nama yang berurutan
                    arcname = f"{i + 1:04d}_{os.path.basename(img_path)}"
                    zf.write(self._get_safe_path(img_path), arcname)

            self.show_toast(
                "CBZ exported",
                f"Exported {len(image_files_to_export)} typeset pages to {cbz_path}",
                kind="success",
                timeout_ms=5000,
            )

        except Exception as e:
            self.show_banner("cbz-export-error", "CBZ export failed", str(e), kind="error")
        finally:
            QApplication.restoreOverrideCursor()
            self.overall_progress_bar.setVisible(False)
            self.statusBar().showMessage("Ready", 3000)

    def check_if_saved(self, file_path):
        path_part, ext = os.path.splitext(file_path)
        # Check for common extensions
        for check_ext in ['.png', '.jpg', '.jpeg', '.webp']:
            if os.path.exists(f"{path_part}_typeset{check_ext}"):
                return True
        return False
