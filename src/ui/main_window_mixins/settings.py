"""Method domain settings, dipindahkan utuh dari main_window.py.

Fase 1 pemecahan monolit: isi method tidak diubah sama sekali.
Mixin ini hanya berguna sebagai bagian dari MangaOCRApp -- ia mengandalkan
atribut yang dibuat di MangaOCRApp.__init__.
"""

from src.ui.main_window_mixins._imports import *  # noqa: F401,F403


class SettingsMixin:
    def open_settings_dialog(self, focus_tab: str = 'general'):
        self.show_settings_workspace(focus_tab)

    def open_openrouter_settings_dialog(self):
        self.show_settings_workspace('translation')

    def _ensure_settings_workspace(self):
        workspace = getattr(self, 'settings_workspace_widget', None)
        stack = getattr(self, 'center_stack', None)
        if workspace is not None and stack is not None and stack.indexOf(workspace) >= 0:
            return workspace
        if stack is None:
            return None
        from src.ui.settings_workspace import SettingsWorkspace
        workspace = SettingsWorkspace(self)
        workspace.back_requested.connect(self.hide_settings_workspace)
        self.settings_workspace_widget = workspace
        stack.addWidget(workspace)
        return workspace

    def show_settings_workspace(self, focus_tab: str = 'general'):
        stack = getattr(self, 'center_stack', None)
        if stack is None:
            return
        workspace = self._ensure_settings_workspace()
        if workspace is None:
            return
        try:
            workspace.refresh()
            workspace.set_active_section(focus_tab)
        except Exception:
            traceback.print_exc()

        left = getattr(self, 'left_panel_widget', None)
        right = getattr(self, 'right_panel_scroll', None)
        nav = getattr(self, 'nav_zoom_widget', None)
        if left is not None:
            self._settings_left_was_visible = left.isVisible()
            left.setVisible(False)
        if right is not None:
            self._settings_right_was_visible = right.isVisible()
            right.setVisible(False)
        if nav is not None:
            self._settings_nav_was_visible = nav.isVisible()
            nav.setVisible(False)
        stack.setCurrentWidget(workspace)
        self._update_center_panel_constraints(left_visible=False, right_visible=False)

    def hide_settings_workspace(self):
        stack = getattr(self, 'center_stack', None)
        if stack is None:
            return
        has_project = bool(getattr(self, 'project_dir', None) or getattr(self, 'current_image_path', None))
        if not has_project:
            self.show_welcome_screen()
            return

        stack.setCurrentIndex(1)
        nav = getattr(self, 'nav_zoom_widget', None)
        if nav is not None:
            nav.setVisible(bool(getattr(self, '_settings_nav_was_visible', True)))

        left = getattr(self, 'left_panel_widget', None)
        left_visible = bool(getattr(self, '_settings_left_was_visible', True))
        if left is not None:
            left.setVisible(left_visible)
            toggle_btn = getattr(self, 'toggle_left_btn', None)
            if toggle_btn is not None:
                toggle_btn.setChecked(left_visible)
                toggle_btn.setText(NavText.HIDE_FOLDER if left_visible else NavText.SHOW_FOLDER)

        right = getattr(self, 'right_panel_scroll', None)
        right_visible = bool(getattr(self, '_settings_right_was_visible', True))
        if right is not None:
            right.setVisible(right_visible)
            toggle_btn = getattr(self, 'toggle_right_btn', None)
            if toggle_btn is not None:
                toggle_btn.setChecked(right_visible)
                toggle_btn.setText(NavText.HIDE_TOOLS if right_visible else NavText.SHOW_TOOLS)
        self._schedule_window_geometry_guard()

    def apply_appearance_from_settings(self):
        appearance_cfg = SETTINGS.get('appearance', {})
        if not isinstance(appearance_cfg, dict):
            appearance_cfg = {}
        resolved = set_active_appearance(
            appearance_cfg,
            system_dark=self._system_prefers_dark_theme(),
        )
        self.current_theme = resolved.get('effective_mode', 'dark')
        self.setStyleSheet(app_stylesheet())
        self._refresh_theme_dependent_styles()
        return resolved

    def apply_defaults_from_settings(self, apply_runtime_controls=True):
        """Memuat default presets dari settings.json dan menerapkan ke UI."""
        gen_cfg = SETTINGS.get('general', {}) if isinstance(SETTINGS.get('general'), dict) else {}
        
        if apply_runtime_controls:
            # 1. OCR Language / AI OCR default
            default_ocr = gen_cfg.get('default_ocr_lang', '')
            if default_ocr and getattr(self, 'ocr_lang_combo', None) is not None:
                idx = self.ocr_lang_combo.findText(default_ocr)
                if idx != -1:
                    self.ocr_lang_combo.setCurrentIndex(idx)

            # 2. Force AI OCR & AI-Only Translate defaults
            if getattr(self, 'force_ai_ocr_checkbox', None) is not None:
                with QSignalBlocker(self.force_ai_ocr_checkbox):
                    self.force_ai_ocr_checkbox.setChecked(bool(SETTINGS.get('force_ai_ocr', True)))
            default_ai_only = bool(gen_cfg.get('default_ai_only_translate', True))
            if getattr(self, 'ai_only_translate_checkbox', None) is not None:
                self.ai_only_translate_checkbox.setChecked(default_ai_only)

            # 3. Cleanup toggles & engines synced from Settings
            cleanup_cfg = SETTINGS.get('cleanup', {}) if isinstance(SETTINGS.get('cleanup'), dict) else {}
            if getattr(self, 'inpaint_checkbox', None) is not None and not getattr(self, 'selected_typeset_area', None):
                with QSignalBlocker(self.inpaint_checkbox):
                    self.inpaint_checkbox.setChecked(bool(cleanup_cfg.get('use_inpaint', True)))
            self._sync_inpaint_engine_combos()
            self._refresh_inpaint_summary_badges()

            # 4. AI Model default
            default_ai_model = gen_cfg.get('default_ai_model', '')
            if default_ai_model and getattr(self, 'ai_model_combo', None) is not None:
                idx = self.ai_model_combo.findText(default_ai_model)
                if idx != -1:
                    self.ai_model_combo.setCurrentIndex(idx)

            # 4.5 Default Translation Style
            default_style = gen_cfg.get('default_translation_style', 'Santai (Default)')
            if default_style and getattr(self, 'style_combo', None) is not None:
                idx = self.style_combo.findText(default_style)
                if idx != -1:
                    self.style_combo.setCurrentIndex(idx)
                
        # 4. Typesetting Defaults
        # Update the font template used for NEW areas only.
        # We do NOT force-override the live typeset panel controls if the user
        # is already editing (i.e. an area is selected), because those controls
        # reflect the SELECTED AREA's properties, not the global default.
        default_font_family = gen_cfg.get('default_font_family', '')
        if default_font_family and self.font_manager:
            new_font = self.font_manager.create_qfont(default_font_family)
        else:
            default_display = self.font_manager.list_fonts()[0] if self.font_manager else 'Arial'
            new_font = self.font_manager.create_qfont(default_display) if self.font_manager else QFont('Arial')
            
        default_size = gen_cfg.get('default_font_size', 14)
        new_font.setPointSize(int(default_size))
        
        default_bold = gen_cfg.get('default_font_bold', False)
        new_font.setWeight(QFont.Bold if default_bold else QFont.Normal)
        new_font.setLetterSpacing(QFont.PercentageSpacing, 100.0)
        
        # Store as the font template for new areas.
        # Only replace self.typeset_font if there is NO active area selected
        # (to avoid stomping a font the user explicitly chose for a selected area).
        has_selection = getattr(self, 'selected_typeset_area', None) is not None
        if not has_selection:
            self.typeset_font = new_font

        # Update the in-memory typeset_defaults so future areas inherit these settings.
        # This dict is what _create_typeset_area reads for new areas.
        self.typeset_defaults = {
            'font_display': (self.font_manager.display_name_for_font(new_font) if self.font_manager else ''),
            'font_size': float(default_size),
            'bold': bool(default_bold),
            'italic': new_font.italic(),
            'underline': new_font.underline(),
            'line_spacing': float(getattr(self, 'typeset_line_spacing_value', 1.1)),
            'char_spacing': float(getattr(self, 'typeset_char_spacing_value', 100.0)),
            'alignment': getattr(self, 'typeset_alignment', 'center'),
            'orientation': getattr(self, 'typeset_orientation', 'horizontal'),
            'outline': bool(getattr(self, 'typeset_outline_enabled', False)),
            'outline_width': float(getattr(self, 'typeset_outline_width', 2.0)),
            'outline_color': (self.typeset_outline_color.name() if isinstance(getattr(self, 'typeset_outline_color', None), QColor) else '#000000'),
            'outline_style': getattr(self, 'typeset_outline_style', 'stroke'),
            'color': (self.typeset_color.name() if isinstance(getattr(self, 'typeset_color', None), QColor) else '#000000'),
            'gradient_enabled': bool(getattr(self, 'typeset_gradient_enabled', False)),
            'gradient_angle': float(getattr(self, 'typeset_gradient_angle', 0.0)),
            'gradient_colors': list(getattr(self, 'typeset_gradient_colors', ["#FF0000", "#0000FF"])),
        }

        # Only update the live typeset panel UI if nothing is selected.
        # When a text area IS selected, the panel shows that area's properties
        # and should not be disturbed by a settings change.
        if not has_selection:
            if hasattr(self, 'font_dropdown'):
                self._populate_typeset_font_dropdown()
                display_name = self.font_manager.display_name_for_font(new_font) if self.font_manager else ''
                if display_name:
                    with QSignalBlocker(self.font_dropdown):
                        self.font_dropdown.setCurrentText(display_name)
            if hasattr(self, 'font_size_spin'):
                with QSignalBlocker(self.font_size_spin):
                    self.font_size_spin.setValue(float(default_size))
            if hasattr(self, 'bold_toggle'):
                with QSignalBlocker(self.bold_toggle):
                    self.bold_toggle.setChecked(bool(default_bold))

    def _apply_ai_model_overrides_from_settings(self, provider_filter=None):
        overrides = SETTINGS.get('ai_model_overrides', {})
        if not isinstance(overrides, dict):
            return
        for provider, models in overrides.items():
            if provider_filter and provider != provider_filter:
                continue
            if not isinstance(models, dict):
                continue
            provider_dict = self.AI_PROVIDERS.setdefault(provider, {})
            for model_id, override in models.items():
                if not isinstance(override, dict):
                    continue
                target = provider_dict.setdefault(model_id, {'display': model_id})
                pricing = override.get('pricing')
                if isinstance(pricing, dict):
                    target.setdefault('pricing', {})
                    for field in ('input', 'output'):
                        if field in pricing:
                            try:
                                target['pricing'][field] = float(pricing[field])
                            except (TypeError, ValueError):
                                pass
                limits = override.get('limits')
                if isinstance(limits, dict):
                    target.setdefault('limits', {})
                    for field in ('rpm', 'rpd'):
                        if field in limits:
                            try:
                                value = int(limits[field])
                            except (TypeError, ValueError):
                                continue
                            if value > 0:
                                target['limits'][field] = value

                if provider == 'OpenRouter' and hasattr(self, 'openrouter_pricing_db') and model_id in self.openrouter_pricing_db:
                    db_target = self.openrouter_pricing_db[model_id]
                    if isinstance(pricing, dict):
                        db_target.setdefault('pricing', {}).update(target.get('pricing', {}))
                    if isinstance(limits, dict):
                        db_target.setdefault('limits', {}).update(target.get('limits', {}))

    def _persist_ai_model_overrides_to_settings(self):
        overrides = {}
        for provider, models in getattr(self, 'AI_PROVIDERS', {}).items():
            if not isinstance(models, dict):
                continue
            provider_payload = {}
            for model_id, info in models.items():
                if not isinstance(info, dict):
                    continue
                payload = {}
                pricing = info.get('pricing')
                if isinstance(pricing, dict):
                    payload['pricing'] = {
                        'input': float(pricing.get('input', 0.0) or 0.0),
                        'output': float(pricing.get('output', 0.0) or 0.0),
                    }
                limits = info.get('limits')
                if isinstance(limits, dict):
                    limit_payload = {}
                    for field in ('rpm', 'rpd'):
                        try:
                            value = int(limits.get(field, 0) or 0)
                        except (TypeError, ValueError):
                            value = 0
                        if value > 0:
                            limit_payload[field] = value
                    if limit_payload:
                        payload['limits'] = limit_payload
                if payload:
                    provider_payload[model_id] = payload
            if provider_payload:
                overrides[provider] = provider_payload
        SETTINGS['ai_model_overrides'] = overrides
        save_settings(SETTINGS)

    def _populate_inpaint_engine_combo(
        self,
        combo,
        context: str = "full",
        sd_repo: str | None = None,
        option_cache: dict | None = None,
    ):
        if combo is None:
            return
        current_eid = combo.currentData()
        with QSignalBlocker(combo):
            combo.clear()
            for spec in list_inpaint_engines(context):
                if option_cache is not None and spec.id in option_cache:
                    text, badge, ready = option_cache[spec.id]
                else:
                    text, badge, ready = format_inpaint_engine_option(spec)
                    if option_cache is not None:
                        option_cache[spec.id] = (text, badge, ready)
                dot_color = (
                    theme.COLORS['muted']
                    if spec.id == "iopaint_server"
                    else (theme.COLORS['success'] if ready else theme.COLORS['warning'])
                )
                combo.addItem(status_dot_icon(dot_color, 8), text, spec.id)
                idx = combo.count() - 1
                tip = f"{spec.label}\nStatus: {badge}\n{spec.description}"
                combo.setItemData(idx, tip, Qt.ToolTipRole)
            if current_eid:
                sel = combo.findData(current_eid)
                if sel != -1:
                    combo.setCurrentIndex(sel)

    def _refresh_all_inpaint_engine_combos(self, sd_repo: str | None = None, option_cache: dict | None = None):
        cache = option_cache if option_cache is not None else {}
        for attr_name in (
            'full_inpaint_engine_combo',
            'cleanup_inpaint_engine_combo',
            'brush_inpaint_engine_combo',
        ):
            combo = getattr(self, attr_name, None)
            if combo is not None:
                self._populate_inpaint_engine_combo(combo, context="full", option_cache=cache)
        self._sync_inpaint_engine_combos()

    def _sync_inpaint_engine_combos(self):
        cleanup_cfg = SETTINGS.get('cleanup', {}) if isinstance(SETTINGS.get('cleanup'), dict) else {}
        unified_eid = resolve_inpaint_engine_id(cleanup_cfg)

        for attr_name in (
            'full_inpaint_engine_combo',
            'cleanup_inpaint_engine_combo',
            'brush_inpaint_engine_combo',
        ):
            combo = getattr(self, attr_name, None)
            if combo is None:
                continue
            with QSignalBlocker(combo):
                idx = combo.findData(unified_eid)
                if idx != -1:
                    combo.setCurrentIndex(idx)

    def _notify_inpaint_engine_selection(self, engine_id: str, role_label: str = "Full & Brush"):
        spec = get_inpaint_spec(engine_id)
        if not is_engine_ready(spec.id):
            msg = (
                f"{role_label}: {spec.short_label} ({spec.size_hint}) belum ada di lokal. "
                "Klik tombol Unduh atau biarkan terunduh otomatis saat dijalankan."
            )
            if hasattr(self, 'show_toast'):
                self.show_toast("Model Inpaint", msg, kind="info")

    def _set_inpaint_engine(self, engine_id: str, *, persist: bool = True, notify: bool = False):
        norm_id = normalize_inpaint_engine_id(engine_id, default=DEFAULT_INPAINT_ENGINE)
        cleanup_cfg = SETTINGS.setdefault('cleanup', {})
        cleanup_cfg['inpaint_engine'] = norm_id
        cleanup_cfg['full_inpaint_engine'] = norm_id
        cleanup_cfg['brush_inpaint_engine'] = norm_id
        cleanup_cfg['inpaint_model_name'] = engine_display_label(norm_id)
        if persist:
            save_settings(SETTINGS)
        self._refresh_inpaint_summary_badges()
        if notify:
            self._notify_inpaint_engine_selection(norm_id, "Inpainting Model")

    def _set_full_inpaint_engine(self, engine_id: str, *, persist: bool = True, notify: bool = False):
        self._set_inpaint_engine(engine_id, persist=persist, notify=notify)

    def _set_brush_inpaint_engine(self, engine_id: str, *, persist: bool = True, notify: bool = False):
        self._set_inpaint_engine(engine_id, persist=persist, notify=notify)

    def _on_inpaint_engine_changed(self, combo=None):
        src = combo if combo is not None else self.sender()
        eid = src.currentData() if src is not None else None
        if eid:
            self._set_inpaint_engine(str(eid), persist=True, notify=True)

    def _on_full_inpaint_engine_changed(self, combo=None):
        self._on_inpaint_engine_changed(combo)

    def _on_brush_inpaint_engine_changed(self, combo=None):
        self._on_inpaint_engine_changed(combo)

    def _refresh_inpaint_summary_badges(self):
        cleanup_cfg = SETTINGS.get('cleanup', {}) if isinstance(SETTINGS.get('cleanup'), dict) else {}
        unified_eid = resolve_inpaint_engine_id(cleanup_cfg)
        hw_label = "GPU CUDA" if getattr(self, 'is_gpu_available', False) else "CPU"
        option_cache: dict = {}

        self._refresh_all_inpaint_engine_combos(option_cache=option_cache)

        spec_obj = get_inpaint_spec(unified_eid)
        _, badge, is_ready_flag = option_cache.get(
            unified_eid, format_inpaint_engine_option(spec_obj)
        )
        dl_active = getattr(self, '_workspace_inpaint_dl_worker', None) is not None

        summary_lbl = getattr(self, 'cleanup_inpaint_summary_label', None)
        if summary_lbl is not None:
            summary_lbl.setText(
                f"Full & Brush: {spec_obj.short_label} ({badge})\n"
                f"Mode Hardware: {hw_label}"
            )

        needs_dl = bool(spec_obj.needs_download and not is_ready_flag)
        for row_attr, lbl_attr, btn_attr in (
            ('full_inpaint_status_row', 'full_inpaint_status_label', 'full_inpaint_download_btn'),
            ('brush_inpaint_status_row', 'brush_inpaint_status_label', 'brush_inpaint_download_btn'),
        ):
            row_w = getattr(self, row_attr, None)
            lbl_w = getattr(self, lbl_attr, None)
            btn_w = getattr(self, btn_attr, None)
            if row_w is not None:
                row_w.setVisible(needs_dl)
            if lbl_w is not None and needs_dl:
                lbl_w.setText(
                    InpaintText.BADGE_MISSING_FMT.format(
                        name=spec_obj.short_label,
                        size=spec_obj.size_hint,
                    )
                )
            if btn_w is not None:
                btn_w.setEnabled(needs_dl and not dl_active)
                btn_w.setText(InpaintText.BTN_DOWNLOADING if dl_active else InpaintText.BTN_DOWNLOAD_INLINE)

        dl_missing_btn = getattr(self, 'cleanup_download_missing_btn', None)
        if dl_missing_btn is not None:
            dl_missing_btn.setVisible(needs_dl)
            if needs_dl:
                dl_missing_btn.setText(
                    InpaintText.BTN_DOWNLOADING
                    if dl_active
                    else InpaintText.BTN_DOWNLOAD_MISSING_FMT.format(names=spec_obj.short_label)
                )
                dl_missing_btn.setEnabled(not dl_active)

        if hasattr(self, '_update_full_tab_hints'):
            self._update_full_tab_hints()

    def _download_selected_workspace_inpaint_engine(self, role: str = "full"):
        cleanup_cfg = SETTINGS.get('cleanup', {}) if isinstance(SETTINGS.get('cleanup'), dict) else {}
        target = resolve_inpaint_engine_id(cleanup_cfg)
        spec = get_inpaint_spec(target)
        if not spec.needs_download or is_engine_ready(target):
            self._refresh_inpaint_summary_badges()
            return
        self._start_workspace_inpaint_download(target)

    def _download_next_missing_inpaint_engine(self):
        cleanup_cfg = SETTINGS.get('cleanup', {}) if isinstance(SETTINGS.get('cleanup'), dict) else {}
        missing = get_missing_engine_ids(cleanup_cfg)
        if not missing:
            self._refresh_inpaint_summary_badges()
            return
        self._start_workspace_inpaint_download(missing[0])

    def _start_workspace_inpaint_download(self, engine_id: str):
        if getattr(self, '_workspace_inpaint_dl_worker', None) is not None:
            if hasattr(self, 'show_toast'):
                self.show_toast("Unduhan Aktif", "Tunggu unduhan model sebelumnya selesai dulu.", kind="info")
            return
        cleanup_cfg = SETTINGS.get('cleanup', {}) if isinstance(SETTINGS.get('cleanup'), dict) else {}
        norm_id = normalize_inpaint_engine_id(engine_id)
        label = engine_display_label(norm_id, short=True)

        for bar_attr in ('full_inpaint_dl_bar', 'cleanup_inpaint_dl_bar'):
            bar = getattr(self, bar_attr, None)
            if bar is not None:
                bar.setRange(0, 100)
                bar.setValue(0)
                bar.setVisible(True)
        if hasattr(self, 'statusBar'):
            self.statusBar().showMessage(InpaintText.DOWNLOAD_STARTED_FMT.format(name=label), 0)
        if hasattr(self, 'show_toast'):
            self.show_toast("Mengunduh Model", InpaintText.DOWNLOAD_STARTED_FMT.format(name=label), kind="info")

        from src.core.workers import InpaintModelDownloadWorker
        worker = InpaintModelDownloadWorker(norm_id)
        worker.progress.connect(self._on_workspace_inpaint_dl_progress)
        worker.finished_ok.connect(self._on_workspace_inpaint_dl_finished)
        worker.finished.connect(self._on_workspace_inpaint_dl_thread_done)
        self._workspace_inpaint_dl_worker = worker
        self._refresh_inpaint_summary_badges()
        worker.start()

    def _on_workspace_inpaint_dl_progress(self, pct: int, msg: str):
        val = max(0, min(100, int(pct)))
        for bar_attr in ('full_inpaint_dl_bar', 'cleanup_inpaint_dl_bar'):
            bar = getattr(self, bar_attr, None)
            if bar is not None:
                bar.setValue(val)
        if hasattr(self, 'statusBar'):
            self.statusBar().showMessage(f"{msg} ({val}%)", 0)

    def _on_workspace_inpaint_dl_finished(self, engine_id: str, success: bool, detail: str):
        if hasattr(self, 'statusBar'):
            self.statusBar().showMessage(detail, 4500)
        if hasattr(self, 'show_toast'):
            self.show_toast(
                "Model Siap" if success else "Unduhan Gagal",
                detail,
                kind="success" if success else "warning",
            )

    def _on_workspace_inpaint_dl_thread_done(self):
        self._workspace_inpaint_dl_worker = None
        for bar_attr in ('full_inpaint_dl_bar', 'cleanup_inpaint_dl_bar'):
            bar = getattr(self, bar_attr, None)
            if bar is not None:
                bar.setVisible(False)
                bar.setValue(0)
        self._refresh_inpaint_summary_badges()

    def get_current_settings(self):
        ocr_combo = getattr(self, 'ocr_lang_combo', None)
        lang_data = ocr_combo.currentData() if ocr_combo is not None else None
        ocr_engine = lang_data.get('engine') if isinstance(lang_data, dict) else 'AI_OCR'
        ocr_lang_code = lang_data.get('code') if isinstance(lang_data, dict) else 'auto'
        ai_provider = None
        ai_model_id = None
        ai_model_name = None
        ai_provider_label = None
        if isinstance(lang_data, dict) and ocr_engine == 'AI_OCR':
            ai_provider = lang_data.get('provider')
            ai_model_id = lang_data.get('model_id')
            ai_model_name = lang_data.get('model_name')
            ai_provider_label = lang_data.get('provider_label')
        elif SETTINGS.get('force_ai_ocr', True) and hasattr(self, '_get_ai_ocr_entries'):
            ai_entries = self._get_ai_ocr_entries()
            if ai_entries:
                ai_data = ai_entries[0].get('data') or {}
                ai_provider = ai_data.get('provider')
                ai_model_id = ai_data.get('model_id')
                ai_model_name = ai_data.get('model_name')
                ai_provider_label = ai_data.get('provider_label')
        selected_model_info = self.get_selected_model_info() or {}
        selected_model_label = selected_model_info.get('display') or selected_model_info.get('name')

        cleanup_cfg = SETTINGS.get('cleanup', {}) if isinstance(SETTINGS.get('cleanup'), dict) else {}
        unified_eid = resolve_inpaint_engine_id(cleanup_cfg)
        for attr_name in ('full_inpaint_engine_combo', 'cleanup_inpaint_engine_combo', 'brush_inpaint_engine_combo'):
            combo = getattr(self, attr_name, None)
            if combo is not None and combo.currentData():
                unified_eid = normalize_inpaint_engine_id(combo.currentData(), default=unified_eid)
                break
        inpaint_model_text = engine_display_label(unified_eid)
        inpaint_model_key = None

        inpaint_pad_spin = getattr(self, 'inpaint_padding_spinbox', None)
        inpaint_padding_val = int(inpaint_pad_spin.value()) if inpaint_pad_spin is not None else int(cleanup_cfg.get('inpaint_padding', 5) or 5)

        font_for_settings = QFont(self._build_current_font())
        self.typeset_font = font_for_settings
        color_for_settings = QColor(self.typeset_color)
        char_spacing_value = float(self.typeset_char_spacing_value)
        line_spacing_value = float(self.typeset_line_spacing_value)
        apply_mode_global = getattr(self, 'apply_mode_global_radio', None) and self.apply_mode_global_radio.isChecked()
        if apply_mode_global:
            use_inpaint_value = self._default_cleanup_value('use_inpaint')
            use_background_box_value = self._default_cleanup_value('use_background_box')
            constrain_text_value = self._default_cleanup_value('constrain_text')
        else:
            use_inpaint_value = bool(self.inpaint_checkbox.isChecked()) if getattr(self, 'inpaint_checkbox', None) else self._default_cleanup_value('use_inpaint')
            use_background_box_value = bool(self.use_background_box_checkbox.isChecked()) if getattr(self, 'use_background_box_checkbox', None) else self._default_cleanup_value('use_background_box')
            constrain_text_value = bool(self.constrain_text_checkbox.isChecked()) if getattr(self, 'constrain_text_checkbox', None) else self._default_cleanup_value('constrain_text')

        ori_combo = getattr(self, 'orientation_combo', None)
        trans_combo = getattr(self, 'translate_combo', None)
        enh_cb = getattr(self, 'enhanced_pipeline_checkbox', None)
        ai_only_cb = getattr(self, 'ai_only_translate_checkbox', None)
        deepl_cb = getattr(self, 'deepl_only_checkbox', None)
        dl_cb = getattr(self, 'dl_bubble_detector_checkbox', None)
        dl_prov_combo = getattr(self, 'dl_model_provider_combo', None)
        dl_file_combo = getattr(self, 'dl_model_file_combo', None)
        style_combo = getattr(self, 'style_combo', None)
        split_cb = getattr(self, 'split_bubbles_checkbox', None)
        safe_cb = getattr(self, 'safe_mode_checkbox', None)
        gpu_cb = getattr(self, 'use_gpu_checkbox', None)

        return {
            'ocr_engine': ocr_engine,
            'ocr_lang': ocr_lang_code,
            'ocr_ai_provider': ai_provider,
            'ocr_ai_provider_label': ai_provider_label,
            'ocr_ai_model_id': ai_model_id,
            'ocr_ai_model_name': ai_model_name,
            'orientation': ori_combo.currentText() if ori_combo is not None else 'Auto-Detect',
            'target_lang': trans_combo.currentText() if trans_combo is not None else SETTINGS.get('general', {}).get('default_target_lang', 'Indonesian'),
            'use_ai': True,
            'font': font_for_settings,
            'color': color_for_settings,
            'enhanced_pipeline': bool(enh_cb.isChecked()) if enh_cb is not None else False,
            'use_ai_only_translate': bool(ai_only_cb.isChecked()) if ai_only_cb is not None else True,
            'use_deepl_only_translate': bool(deepl_cb.isChecked()) if deepl_cb is not None else False,
            'use_dl_detector': bool(dl_cb.isChecked()) if dl_cb is not None else False,
            'dl_provider': dl_prov_combo.currentText() if dl_prov_combo is not None else 'Kitsumed',
            'dl_model_file': dl_file_combo.currentText() if dl_file_combo is not None else '',
            'ai_model': self.get_selected_model_name(),
            'ai_model_label': selected_model_label,
            'ai_model_info': selected_model_info,
            'translation_style': style_combo.currentText() if style_combo is not None else 'Santai (Default)',
            'auto_split_bubbles': bool(split_cb.isChecked()) if split_cb is not None else False,
            'safe_mode': bool(safe_cb.isChecked()) if safe_cb is not None else False,
            'use_gpu': bool(gpu_cb.isChecked()) if gpu_cb is not None else bool(getattr(self, 'is_gpu_available', False)),
            # Optimasi CPU / Cleanup
            'use_inpaint': use_inpaint_value,
            'inpaint_engine': unified_eid,
            'full_inpaint_engine': unified_eid,
            'brush_inpaint_engine': unified_eid,
            'inpaint_model_name': inpaint_model_text,
            'inpaint_model_key': inpaint_model_key,
            'inpaint_device': cleanup_cfg.get('inpaint_device', 'auto'),
            'inpaint_server_url': cleanup_cfg.get('inpaint_server_url', DEFAULT_INPAINT_SERVER_URL),
            'inpaint_server_timeout': cleanup_cfg.get('inpaint_server_timeout', DEFAULT_INPAINT_SERVER_TIMEOUT),
            'inpaint_padding': inpaint_padding_val,
            'cpu_threads': 4,
            'enable_mkldnn': True,
            'orientation_mode': self.typeset_orientation,
            'create_bubble': bool(getattr(self, 'create_bubble_checkbox', None) and self.create_bubble_checkbox.isChecked()),
            'use_background_box': use_background_box_value,
            'text_effect': 'none',
            'effect_intensity': 20.0,
            'bezier_points': None,
            'alignment': self.typeset_alignment,
            'line_spacing': line_spacing_value,
            'char_spacing': char_spacing_value,
            'text_outline': bool(self.typeset_outline_enabled),
            'outline_width': float(self.typeset_outline_width),
            'outline_color': self.typeset_outline_color.name() if isinstance(self.typeset_outline_color, QColor) else '#000000',
            'outline_style': getattr(self, 'typeset_outline_style', 'stroke'),
            'margins': {'top': 0, 'right': 0, 'bottom': 0, 'left': 0},
            'manga_use_easy_detection': bool(getattr(self, 'manga_use_easy_detection_checkbox', None) and self.manga_use_easy_detection_checkbox.isChecked()),
            'tesseract_use_easy_detection': bool(getattr(self, 'tesseract_use_easy_detection_checkbox', None) and self.tesseract_use_easy_detection_checkbox.isChecked()),
            'use_auto_text_color': bool(cleanup_cfg.get('auto_text_color', True)),
            'constrain_text': constrain_text_value,
            'auto_font_size': (
                bool(self.auto_font_size_checkbox.isChecked())
                if getattr(self, 'auto_font_size_checkbox', None) is not None
                else bool(SETTINGS.get('typeset', {}).get('auto_font_size', True))
            ),
        }

    def _apply_typeset_settings(self, settings_dict):
        if not settings_dict or not getattr(self, 'font_dropdown', None):
            return
        preferred_display = settings_dict.get('font_display')
        self._populate_typeset_font_dropdown(preferred_display)

        if getattr(self, 'font_size_spin', None):
            with QSignalBlocker(self.font_size_spin):
                self.font_size_spin.setValue(float(settings_dict.get('font_size', 24.0)))
        if getattr(self, 'bold_toggle', None):
            with QSignalBlocker(self.bold_toggle):
                self.bold_toggle.setChecked(bool(settings_dict.get('bold', False)))
        if getattr(self, 'italic_toggle', None):
            with QSignalBlocker(self.italic_toggle):
                self.italic_toggle.setChecked(bool(settings_dict.get('italic', False)))
        if getattr(self, 'underline_toggle', None):
            with QSignalBlocker(self.underline_toggle):
                self.underline_toggle.setChecked(bool(settings_dict.get('underline', False)))
        self._set_line_spacing_value(settings_dict.get('line_spacing', 1.1))
        self._set_char_spacing_value(settings_dict.get('char_spacing', 100.0))

        self.typeset_alignment = settings_dict.get('alignment', 'center')
        self.typeset_orientation = settings_dict.get('orientation', 'horizontal')
        self._update_alignment_buttons()
        self._update_orientation_buttons()

        self.typeset_outline_enabled = bool(settings_dict.get('outline', False))
        if getattr(self, 'outline_toggle', None):
            with QSignalBlocker(self.outline_toggle):
                self.outline_toggle.setChecked(self.typeset_outline_enabled)

        outline_width = settings_dict.get('outline_width')
        if outline_width is None:
            outline_width = SETTINGS.get('typeset', {}).get('outline_width', SETTINGS.get('typeset', {}).get('outline_thickness', self.typeset_outline_width))
        try:
            outline_width = float(outline_width)
        except Exception:
            outline_width = self.typeset_outline_width
        outline_width = max(0.0, min(outline_width, 12.0))
        self.typeset_outline_width = outline_width
        if getattr(self, 'outline_width_spin', None):
            with QSignalBlocker(self.outline_width_spin):
                self.outline_width_spin.setValue(self.typeset_outline_width)

        outline_color_value = settings_dict.get('outline_color')
        if outline_color_value is None:
            outline_color_value = SETTINGS.get('typeset', {}).get('outline_color', '#000000')
        outline_color = QColor(outline_color_value) if outline_color_value else QColor('#000000')
        if not outline_color.isValid():
            outline_color = QColor('#000000')
        self.typeset_outline_color = outline_color
        style_val = (settings_dict.get('outline_style') or 'stroke')
        if isinstance(style_val, str):
            style_val = style_val.lower()
        self.typeset_outline_style = style_val if style_val in ('stroke', 'glow') else 'stroke'
        self._update_outline_color_button()
        self._refresh_outline_controls_enabled()

        color_value = settings_dict.get('color', '#000000')
        color_obj = QColor(color_value)
        if color_obj.isValid():
            self.typeset_color = color_obj
        self._update_color_button()
        
        # Gradient defaults
        self.typeset_gradient_enabled = bool(settings_dict.get('gradient_enabled', False))
        self.typeset_gradient_angle = float(settings_dict.get('gradient_angle', 0.0))
        self.typeset_gradient_colors = list(settings_dict.get('gradient_colors', ["#FF0000", "#0000FF"]))
        if getattr(self, 'gradient_group', None):
            with QSignalBlocker(self.gradient_group):
                self.gradient_group.setChecked(self.typeset_gradient_enabled)
        if getattr(self, 'grad_angle_spin', None):
            with QSignalBlocker(self.grad_angle_spin):
                self.grad_angle_spin.setValue(self.typeset_gradient_angle)
        if getattr(self, 'grad_color_list', None):
             self._update_gradient_list_ui(self.typeset_gradient_colors)

        self.typeset_font = self._build_current_font()
        self._update_typeset_preview()

    def _collect_project_settings(self):
        try:
            settings = self.get_current_settings() or {}
        except Exception:
            settings = {}
        serialized = {}
        for key, value in settings.items():
            if isinstance(value, QFont):
                serialized[key] = TypesetArea.font_to_dict(value)
            elif isinstance(value, QColor):
                serialized[key] = value.name()
            elif isinstance(value, (QRect, QRectF)):
                serialized[key] = rect_to_dict(value)
            elif isinstance(value, (QPoint, QPointF)):
                serialized[key] = {'x': coerce_int(value.x()), 'y': coerce_int(value.y())}
            elif isinstance(value, (set, tuple)):
                serialized[key] = list(value)
            else:
                serialized[key] = value
        serialized['cleanup'] = {
            'use_background_box': self._default_cleanup_value('use_background_box'),
            'use_inpaint': self._default_cleanup_value('use_inpaint'),
            'constrain_text': self._default_cleanup_value('constrain_text'),
            'apply_mode': self._default_cleanup_value('apply_mode'),
        }
        return serialized
