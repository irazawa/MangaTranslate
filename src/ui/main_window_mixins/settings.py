"""Method domain settings, dipindahkan utuh dari main_window.py.

Fase 1 pemecahan monolit: isi method tidak diubah sama sekali.
Mixin ini hanya berguna sebagai bagian dari MangaOCRApp -- ia mengandalkan
atribut yang dibuat di MangaOCRApp.__init__.
"""

from src.ui.main_window_mixins._imports import *  # noqa: F401,F403


class SettingsMixin:
    def open_settings_dialog(self, focus_tab: str = 'profile'):
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

    def show_settings_workspace(self, focus_tab: str = 'profile'):
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
            # 1. OCR Language default
            default_ocr = gen_cfg.get('default_ocr_lang', 'Japanese (Manga-OCR)')
            if hasattr(self, 'ocr_lang_combo'):
                idx = self.ocr_lang_combo.findText(default_ocr)
                if idx != -1:
                    self.ocr_lang_combo.setCurrentIndex(idx)

            # 2. AI-Only Translate default
            default_ai_only = bool(gen_cfg.get('default_ai_only_translate', False))
            if hasattr(self, 'ai_only_translate_checkbox'):
                self.ai_only_translate_checkbox.setChecked(default_ai_only)

            # 3. AI Model default
            default_ai_model = gen_cfg.get('default_ai_model', '')
            if default_ai_model and hasattr(self, 'ai_model_combo'):
                idx = self.ai_model_combo.findText(default_ai_model)
                if idx != -1:
                    self.ai_model_combo.setCurrentIndex(idx)

            # 3.5 Default Translation Style
            default_style = gen_cfg.get('default_translation_style', 'Santai (Default)')
            if default_style and hasattr(self, 'style_combo'):
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

    def get_current_settings(self):
        lang_data = self.ocr_lang_combo.currentData()
        ocr_engine = lang_data.get('engine') if isinstance(lang_data, dict) else None
        ocr_lang_code = lang_data.get('code') if isinstance(lang_data, dict) else None
        ai_provider = None
        ai_model_id = None
        ai_model_name = None
        ai_provider_label = None
        if isinstance(lang_data, dict) and ocr_engine == 'AI_OCR':
            ai_provider = lang_data.get('provider')
            ai_model_id = lang_data.get('model_id')
            ai_model_name = lang_data.get('model_name')
            ai_provider_label = lang_data.get('provider_label')
        selected_model_info = self.get_selected_model_info() or {}
        selected_model_label = selected_model_info.get('display') or selected_model_info.get('name')

        inpaint_model_text = self.inpaint_model_combo.currentText()
        # Hanya model LaMa yang membutuhkan dependency eksternal. Jika pengguna memilih OpenCV,
        # biarkan kuncinya None supaya engine LaMa tidak lagi dipanggil.
        inpaint_model_key = None
        if "Big-LaMa" in inpaint_model_text:
            inpaint_model_key = 'big_lama'
        elif "Anime" in inpaint_model_text:
            inpaint_model_key = 'anime_inpaint'
            
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

        return {
            'ocr_engine': ocr_engine,
            'ocr_lang': ocr_lang_code,
            'ocr_ai_provider': ai_provider,
            'ocr_ai_provider_label': ai_provider_label,
            'ocr_ai_model_id': ai_model_id,
            'ocr_ai_model_name': ai_model_name,
            'orientation': self.orientation_combo.currentText(),
            'target_lang': self.translate_combo.currentText(),
            'use_ai': True,
            'font': font_for_settings,
            'color': color_for_settings,
            'enhanced_pipeline': self.enhanced_pipeline_checkbox.isChecked(),
            'use_ai_only_translate': self.ai_only_translate_checkbox.isChecked(),
            'use_deepl_only_translate': self.deepl_only_checkbox.isChecked(),
            'use_dl_detector': self.dl_bubble_detector_checkbox.isChecked(),
            'dl_provider': self.dl_model_provider_combo.currentText(),
            'dl_model_file': self.dl_model_file_combo.currentText(),
            'ai_model': self.get_selected_model_name(),
            'ai_model_label': selected_model_label,
            'ai_model_info': selected_model_info,
            'translation_style': self.style_combo.currentText(),
            'auto_split_bubbles': self.split_bubbles_checkbox.isChecked(),
            'safe_mode': self.safe_mode_checkbox.isChecked(),
            'use_gpu': self.use_gpu_checkbox.isChecked(),
            # Pastikan ini sesuai dengan hardware Anda
            'use_inpaint': use_inpaint_value,
            'inpaint_model_name': inpaint_model_text,
            'inpaint_model_key': inpaint_model_key,
            'inpaint_server_url': SETTINGS.get('cleanup', {}).get('inpaint_server_url', DEFAULT_INPAINT_SERVER_URL),
            'inpaint_server_timeout': SETTINGS.get('cleanup', {}).get('inpaint_server_timeout', DEFAULT_INPAINT_SERVER_TIMEOUT),
            'inpaint_padding': self.inpaint_padding_spinbox.value(),
            # Optimasi CPU
            'cpu_threads': 4,  # Sesuaikan dengan jumlah core CPU Anda
            'enable_mkldnn': True,  # Optimasi untuk CPU Intel
            'orientation_mode': self.typeset_orientation,
            'create_bubble': getattr(self, 'create_bubble_checkbox', None) and self.create_bubble_checkbox.isChecked(),
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
            'use_auto_text_color': bool(SETTINGS.get('cleanup', {}).get('auto_text_color', True)),
            'constrain_text': constrain_text_value,
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
