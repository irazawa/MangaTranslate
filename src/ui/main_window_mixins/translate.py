"""Method domain translate, dipindahkan utuh dari main_window.py.

Fase 1 pemecahan monolit: isi method tidak diubah sama sekali.
Mixin ini hanya berguna sebagai bagian dari MangaOCRApp -- ia mengandalkan
atribut yang dibuat di MangaOCRApp.__init__.
"""

from src.ui.main_window_mixins._imports import *  # noqa: F401,F403


class TranslateMixin:
    def _create_translate_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(14)

        # ── OCR & Language ──────────────────────────────────────────────────
        ocr_group = QGroupBox("OCR & Language")
        ocr_form = QFormLayout(ocr_group)
        ocr_form.setContentsMargins(12, 16, 12, 12)
        ocr_form.setSpacing(10)
        ocr_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        ocr_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.ocr_lang_combo = QComboBox()
        self.ocr_lang_combo.currentIndexChanged.connect(self.on_ocr_lang_changed)
        ocr_form.addRow("OCR Language:", self.ocr_lang_combo)

        self.ocr_engine_info_label = QLabel("Engine akan dipilih otomatis.")
        self.ocr_engine_info_label.setWordWrap(True)
        self.ocr_engine_info_label.setStyleSheet("color:#4a5c78; font-size:8.5pt; font-style:italic;")
        ocr_form.addRow(self.ocr_engine_info_label)

        self.force_ai_ocr_checkbox = QCheckBox("Force AI OCR")
        self.force_ai_ocr_checkbox.setChecked(bool(SETTINGS.get('force_ai_ocr', False)))
        self.force_ai_ocr_checkbox.setToolTip("If enabled, all OCR uses the AI provider below.")
        self.force_ai_ocr_checkbox.stateChanged.connect(lambda val: (
            SETTINGS.update({'force_ai_ocr': bool(self.force_ai_ocr_checkbox.isChecked())}) or
            save_settings(SETTINGS) or
            self.ai_ocr_lang_combo.setEnabled(bool(val))
        ))
        ocr_form.addRow(self.force_ai_ocr_checkbox)

        self.ai_ocr_lang_combo = QComboBox()
        self.ai_ocr_lang_combo.addItems([
            "Japanese", "English", "Korean", "Chinese (Simplified)", "Chinese (Traditional)",
            "Indonesian", "Portuguese (Brazil)", "Spanish", "French", "Russian", "Thai", "Vietnamese",
            "General/Multi-Language"
        ])
        saved_ai_lang = SETTINGS.get('ai_ocr_lang', 'Japanese')
        self.ai_ocr_lang_combo.setCurrentText(saved_ai_lang)
        self.ai_ocr_lang_combo.currentTextChanged.connect(
            lambda val: SETTINGS.update({'ai_ocr_lang': val}) or save_settings(SETTINGS)
        )
        ocr_form.addRow("AI OCR Lang:", self.ai_ocr_lang_combo)

        self.translate_combo = QComboBox()
        self.translate_combo.addItems(["Indonesian", "English"])
        self.translate_combo.setCurrentText("Indonesian")
        ocr_form.addRow("Translate to:", self.translate_combo)

        self.orientation_combo = QComboBox()
        self.orientation_combo.addItems(["Auto-Detect", "Horizontal", "Vertical"])
        ocr_form.addRow("Orientation:", self.orientation_combo)

        layout.addWidget(ocr_group)

        # ── Per-Language Orientation ─────────────────────────────────────────
        lang_ori_group = QGroupBox("Per-Language Orientation")
        lang_ori_form = QFormLayout(lang_ori_group)
        lang_ori_form.setContentsMargins(12, 16, 12, 12)
        lang_ori_form.setSpacing(10)
        lang_ori_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lang_ori_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.en_orientation_combo = QComboBox()
        self.en_orientation_combo.addItems(["Auto-Detect", "Horizontal", "Vertical"])
        self.en_orientation_combo.setCurrentText(SETTINGS.get('lang_orientation', {}).get('en', 'Auto-Detect'))
        self.en_orientation_combo.currentTextChanged.connect(lambda val: self._on_lang_orientation_changed('en', val))
        lang_ori_form.addRow("English:", self.en_orientation_combo)

        self.jp_orientation_combo = QComboBox()
        self.jp_orientation_combo.addItems(["Auto-Detect", "Horizontal", "Vertical"])
        self.jp_orientation_combo.setCurrentText(SETTINGS.get('lang_orientation', {}).get('ja', 'Auto-Detect'))
        self.jp_orientation_combo.currentTextChanged.connect(lambda val: self._on_lang_orientation_changed('ja', val))
        lang_ori_form.addRow("Japanese:", self.jp_orientation_combo)

        layout.addWidget(lang_ori_group)

        # ── Detection Source ─────────────────────────────────────────────────
        detection_group = QGroupBox("OCR Detection Source")
        det_layout = QVBoxLayout(detection_group)
        det_layout.setContentsMargins(12, 16, 12, 12)
        det_layout.setSpacing(8)

        self.manga_use_easy_detection_checkbox = QCheckBox("Manga-OCR: use EasyOCR regions")
        self.manga_use_easy_detection_checkbox.setChecked(True)
        self.manga_use_easy_detection_checkbox.setToolTip(
            "When enabled, EasyOCR proposes text regions and Manga-OCR performs recognition."
        )
        det_layout.addWidget(self.manga_use_easy_detection_checkbox)

        self.tesseract_use_easy_detection_checkbox = QCheckBox("Tesseract: use EasyOCR regions")
        self.tesseract_use_easy_detection_checkbox.setChecked(True)
        self.tesseract_use_easy_detection_checkbox.setToolTip(
            "When enabled, EasyOCR proposes text regions before Tesseract recognition."
        )
        det_layout.addWidget(self.tesseract_use_easy_detection_checkbox)

        layout.addWidget(detection_group)

        layout.addStretch()
        return tab

    def _create_full_translate_tab(self):
        """Tab khusus 'Full': one-click full-page auto translation dengan selector mode.

        Tombol dan selector dipindah ke sini dari tab OCR supaya entry-nya jelas.
        Selector menentukan `use_ai_vision` yang dibaca di start_full_page_translation.
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(14)

        full_group = QGroupBox("Full-Page Translation")
        full_layout = QVBoxLayout(full_group)
        full_layout.setContentsMargins(12, 16, 12, 12)
        full_layout.setSpacing(10)

        info = QLabel(
            "Proses otomatis: deteksi → OCR (engine dari tab OCR) → "
            "IOPaint → translate.\n"
            "Pilih cakupan: halaman aktif, halaman terpilih, atau seluruh proyek "
            "(halaman yang sudah di-typeset dilewati).\n"
            "• Lokal per-region: RF-DETR layout + OCR tiap region.\n"
            "• AI Vision: kirim 1 halaman utuh ke VLM (Gemini/OpenAI/OpenRouter).\n"
            "• Penerjemah: model AI Translate (tab AI Cfg) atau langsung dari AI OCR/Vision."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color:#4a5c78; font-size:8.5pt; font-style:italic;")
        full_layout.addWidget(info)

        mode_form = QFormLayout()
        mode_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        mode_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self.full_mode_combo = QComboBox()
        # itemData = nilai use_ai_vision yang dibaca worker
        self.full_mode_combo.addItem("Lokal per-region (morfologi)", False)
        self.full_mode_combo.addItem("AI Vision full-page (1 API call)", True)
        self.full_mode_combo.setCurrentIndex(0)
        self.full_mode_combo.setToolTip(
            "Lokal: deteksi morfologi + OCR per blok pakai engine terpilih.\n"
            "AI Vision: 1 gambar utuh ke VLM, balik JSON box+terjemahan (hemat token)."
        )
        mode_form.addRow("Mode:", self.full_mode_combo)

        self.full_translator_combo = QComboBox()
        # itemData: 'ai_translate' = model dari tab AI Cfg; 'ai_ocr' = terjemahan
        # langsung oleh model AI OCR/Vision dalam panggilan yang sama
        self.full_translator_combo.addItem("Model AI Translate (tab AI Cfg)", 'ai_translate')
        self.full_translator_combo.addItem("Langsung dari AI OCR/Vision", 'ai_ocr')
        self.full_translator_combo.setCurrentIndex(0)
        self.full_translator_combo.setToolTip(
            "Model AI Translate: OCR dulu, lalu terjemahkan pakai model di tab AI Cfg.\n"
            "Langsung: model AI OCR/Vision menerjemahkan sekaligus dalam satu panggilan."
        )
        mode_form.addRow("Penerjemah:", self.full_translator_combo)

        self.full_scope_combo = QComboBox()
        self.full_scope_combo.addItem(FullPageBatchText.SCOPE_CURRENT, 'current')
        self.full_scope_combo.addItem(FullPageBatchText.SCOPE_SELECTED, 'selected')
        self.full_scope_combo.addItem(FullPageBatchText.SCOPE_PROJECT, 'project')
        self.full_scope_combo.setToolTip(
            f"{FullPageBatchText.SCOPE_CURRENT_TIP}\n"
            f"{FullPageBatchText.SCOPE_SELECTED_TIP}\n"
            f"{FullPageBatchText.SCOPE_PROJECT_TIP}"
        )
        mode_form.addRow("Cakupan:", self.full_scope_combo)

        self._full_selected_pages = []
        self.full_pick_pages_btn = QPushButton(FullPageBatchText.PICK_PAGES_BTN.format(count=0))
        self.full_pick_pages_btn.setToolTip(FullPageBatchText.SCOPE_SELECTED_TIP)
        self.full_pick_pages_btn.clicked.connect(
            lambda: self._open_full_page_picker()
        )
        self.full_pick_pages_btn.setVisible(False)
        self.full_scope_combo.currentIndexChanged.connect(self._on_full_scope_changed)

        full_layout.addLayout(mode_form)
        full_layout.addWidget(self.full_pick_pages_btn)

        self.auto_translate_page_btn = QPushButton(ActionText.FULL_PAGE_TRANSLATE)
        self.auto_translate_page_btn.setStyleSheet(compact_primary_button_qss())
        self.auto_translate_page_btn.clicked.connect(self.start_full_page_translation)
        full_layout.addWidget(self.auto_translate_page_btn)

        inpaint_restore_row = QHBoxLayout()
        inpaint_restore_row.setSpacing(6)
        self.full_restore_area_inpaint_btn = QPushButton(FullPageBatchText.RESTORE_AREA_INPAINT_BTN)
        self.full_restore_area_inpaint_btn.setToolTip(FullPageBatchText.RESTORE_AREA_INPAINT_TIP)
        self.full_restore_area_inpaint_btn.setEnabled(False)
        self.full_restore_area_inpaint_btn.clicked.connect(lambda: self.restore_selected_area_inpaint())
        inpaint_restore_row.addWidget(self.full_restore_area_inpaint_btn)

        self.full_cancel_page_inpaint_btn = QPushButton(FullPageBatchText.CANCEL_PAGE_INPAINT_BTN)
        self.full_cancel_page_inpaint_btn.setToolTip(FullPageBatchText.CANCEL_PAGE_INPAINT_TIP)
        self.full_cancel_page_inpaint_btn.setEnabled(False)
        self.full_cancel_page_inpaint_btn.clicked.connect(self.cancel_inpaint_result)
        inpaint_restore_row.addWidget(self.full_cancel_page_inpaint_btn)
        full_layout.addLayout(inpaint_restore_row)

        layout.addWidget(full_group)
        layout.addStretch()
        return tab

    def increment_translated_count(self):
        self.translated_count += 1
        self._touch_profile_activity(translated=1)
        if hasattr(self, "translated_label"):
            self.translated_label.setText(str(self.translated_count))

    def on_translation_mode_changed(self):
        # [BARU] Mengelola checkbox yang saling eksklusif
        sender = self.sender()
        if sender == self.ai_only_translate_checkbox and self.ai_only_translate_checkbox.isChecked():
            self.deepl_only_checkbox.setChecked(False)
        elif sender == self.deepl_only_checkbox and self.deepl_only_checkbox.isChecked():
            self.ai_only_translate_checkbox.setChecked(False)

        is_ai_only = self.ai_only_translate_checkbox.isChecked()
        is_deepl_only = self.deepl_only_checkbox.isChecked()
        
        # Nonaktifkan opsi yang tidak relevan
        self.translate_combo.setEnabled(not is_ai_only and not is_deepl_only)
        self.style_combo.setEnabled(is_ai_only)
        self.ai_model_combo.setEnabled(is_ai_only or self.enhanced_pipeline_checkbox.isChecked())

    # [DIUBAH] Fungsi abstrak untuk memanggil AI dengan perulangan percobaan hingga 5x
    def translate_with_ai(self, text_to_translate, target_lang, provider, model_name, settings, is_enhanced=False, ocr_results=None):
        import time
        max_attempts = 5
        last_exc = None
        for attempt in range(1, max_attempts + 1):
            try:
                if provider == 'Gemini':
                    result = self.translate_with_gemini(text_to_translate, target_lang, model_name, settings, is_enhanced, ocr_results)
                elif provider == 'OpenAI':
                    result = self.translate_with_openai(text_to_translate, target_lang, model_name, settings, is_enhanced, ocr_results)
                elif get_translate_provider_key(provider) in LOCAL_TRANSLATE_PROVIDERS:
                    model_info = self.AI_PROVIDERS.get(provider, {}).get(model_name, {})
                    result = self.translate_with_openrouter(text_to_translate, target_lang, model_name, settings, model_info, is_enhanced, ocr_results, provider)
                else:
                    return f"[ERROR: Unknown AI provider '{provider}']"

                # Cek apakah hasil menunjukkan kegagalan/error
                if isinstance(result, str):
                    upper_result = result.upper()
                    if any(err in upper_result for err in ("[ERROR", "[FAILED", "API KEY NOT CONFIGURED", "REQUEST ERROR")):
                        raise Exception(f"AI Provider error: {result}")
                
                # Pasca-proses: Hapus tanda titik tunggal di akhir baris/kalimat agar tidak kelihatan seperti hasil AI kaku
                if isinstance(result, str) and result:
                    processed_lines = []
                    for line in result.splitlines():
                        stripped = line.rstrip()
                        if stripped.endswith('。'):
                            stripped = stripped[:-1].rstrip()
                        elif stripped.endswith('.') and not stripped.endswith('..'):
                            stripped = stripped[:-1].rstrip()
                        processed_lines.append(stripped)
                    result = '\n'.join(processed_lines)
                
                return result
            except Exception as e:
                last_exc = e
                print(f"[AI TRANSLATE] Percobaan {attempt}/{max_attempts} gagal untuk provider {provider}: {e}")
                if attempt < max_attempts:
                    time.sleep(1.0)
        
        # Setelah 5x gagal, lemparkan exception agar penangan fallback di worker terpicu
        raise Exception(f"Seluruh {max_attempts} percobaan terjemahan AI gagal. Error terakhir: {last_exc}")

    # Kirim prompt batch mentah (sudah berisi instruksi penomoran) ke provider AI pilihan
    def call_ai_for_batch(self, prompt, provider, model_name, max_output_tokens=500012):
        if not prompt or not prompt.strip():
            return ""
        try:
            if provider == 'Gemini':
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(
                    prompt,
                    generation_config={"max_output_tokens": max_output_tokens, "temperature": 0.5},
                    request_options={"timeout": 120},
                    safety_settings=[
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    ]
                )
                if response.parts:
                    if hasattr(self, "api_cost_signal"):
                        self.api_cost_signal.emit(len(prompt), len(response.text), 'Gemini', model_name)
                    return response.text.strip()
                return "[GEMINI ERROR] Empty response"

            if provider == 'OpenAI':
                client = getattr(self, "openai_client", None) or openai_client
                if client is None:
                    return "[OPENAI ERROR] Client not configured"
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max(1024, min(max_output_tokens, 16384)),
                )
                output = (response.choices[0].message.content or "").strip()
                if hasattr(response, "usage") and hasattr(self, "api_cost_signal"):
                    self.api_cost_signal.emit(response.usage.prompt_tokens, response.usage.completion_tokens, "OpenAI", model_name)
                return output or "[OPENAI ERROR] Empty response"

            provider_key = get_translate_provider_key(provider)
            if provider_key in LOCAL_TRANSLATE_PROVIDERS:
                provider_meta = LOCAL_TRANSLATE_PROVIDERS.get(provider_key, {})
                provider_display = provider_meta.get('display', provider or 'OpenRouter')
                provider_cfg = get_translate_provider_settings(provider_key)
                api_key = provider_cfg.get('api_key', '').strip()
                if not api_key and not provider_meta.get('api_key_optional'):
                    return f"[{provider_display.upper()} API KEY NOT CONFIGURED]"
                url = provider_cfg.get('url', '').strip() or provider_meta.get('url', "https://openrouter.ai/api/v1/chat/completions")
                model_info = self.AI_PROVIDERS.get(provider, {}).get(model_name, {})
                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": float(model_info.get('temperature', 0.7)) if model_info else 0.7,
                    "max_tokens": int(model_info.get('max_tokens', 2048)) if model_info else 2048,
                }
                pr_timeout = int(provider_cfg.get('timeout', 60) or 60)
                response = robust_post(url, headers=headers, json_payload=payload,
                                       timeout=pr_timeout, max_retries=3, backoff_factor=1.5)
                data = response.json()
                choices = data.get('choices')
                output_text = ""
                if isinstance(choices, list) and choices:
                    msg = choices[0].get('message', {})
                    content = msg.get('content')
                    if isinstance(content, list):
                        output_text = "".join(part.get('text', '') for part in content if isinstance(part, dict))
                    elif isinstance(content, str):
                        output_text = content
                if not output_text:
                    if 'error' in data:
                        return f"[{provider_display.upper()} ERROR: {data['error'].get('message', 'Unknown error')}]"
                    return f"[{provider_display.upper()} ERROR: Empty response]"
                usage = data.get('usage') or {}
                if hasattr(self, "api_cost_signal"):
                    self.api_cost_signal.emit(usage.get('prompt_tokens', 0), usage.get('completion_tokens', 0), provider_display, model_name)
                return output_text.strip()

            return f"[ERROR: Unknown AI provider '{provider}']"
        except Exception as exc:
            return f"[ERROR] Batch AI call failed: {exc}"

    # [DIUBAH] Fungsi terjemahan Gemini yang dimodifikasi
    def translate_with_gemini(
        self,
        text_to_translate,
        target_lang,
        model_name,
        settings,
        is_enhanced=False,
        ocr_results=None,
        selected_style="Santai (Default)"
    ):
        if not text_to_translate.strip():
            return ""
        if not GEMINI_API_KEY or "your_gemini_key_here" in GEMINI_API_KEY:
            return "[GEMINI API KEY NOT CONFIGURED]"
        try:
            model = genai.GenerativeModel(model_name)
            prompt_enhancements = self._build_prompt_enhancements(settings)

            base_rule = (
                f"Your response must ONLY contain the final translation in {target_lang}, as RAW plain text.\n"
                f"- Do NOT wrap output in quotes, brackets, parentheses, or code fences.\n"
                f"- Do NOT include explanations, notes, the original text, markdown, or labels.\n"
                f"- Preserve line breaks if the input has multiple lines.\n"
            )

            if is_enhanced and ocr_results:
                prompt = f"""
    You are an expert manga translator.

    1. Automatically detect the language of the OCR text.
    2. If the text is Japanese:
    - Merge the following two OCR results into the most accurate Japanese text.
    - Silently correct any OCR mistakes.
    - Translate into natural, colloquial {target_lang}.
    3. If the text is already {target_lang}, return it exactly as-is.
    4. If the text is another language (not Japanese and not {target_lang}), translate it into {target_lang}.
    {prompt_enhancements}
    {base_rule}

    OCR Results:
    - Manga-OCR: {ocr_results.get('manga_ocr', '')}
    - Tesseract: {ocr_results.get('tesseract', '')}
    """
            else:
                prompt = f"""
    You are an expert manga translator.

    1. Automatically detect the language of the input text.
    2. If the text is Japanese:
    - Silently correct OCR mistakes.
    - Translate into natural, colloquial {target_lang}.
    3. If the text is already {target_lang}, return it exactly as-is.
    4. If the text is another language (not Japanese and not {target_lang}), translate it into {target_lang}.
    {prompt_enhancements}
    {base_rule}

    Raw OCR Text:
    {text_to_translate}
    """

            # ? Tambah config untuk batasi output tokens + longgarkan safety_settings
            # request_options.timeout mencegah panggilan Gemini menggantung tanpa batas
            response = model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": 500012,  # batas aman
                    "temperature": settings.get("temperature", 0.5) if isinstance(settings, dict) else 0.5
                },
                request_options={"timeout": 120},
                safety_settings=[
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                ]
            )

            if response.parts:
                if hasattr(self, "api_cost_signal"):
                    self.api_cost_signal.emit(len(prompt), len(response.text), 'Gemini', model_name)

                # ? Update counter
                if hasattr(self, "snippet_translated_signal"):
                    self.snippet_translated_signal.emit()

                return response.text.strip()
            return "[GEMINI FAILED]"
        except Exception as e:
            print(f"Error calling Gemini API for full translation: {e}")
            return "[GEMINI ERROR]"

    # [BARU] Fungsi terjemahan OpenAI
    def translate_with_openai(
        self,
        text_to_translate: str,
        target_lang: str,
        model_name: str,
        settings: dict,
        is_enhanced: bool = False,
        ocr_results: dict | None = None,
    ):
        """
        Terjemahkan teks manga via OpenAI Chat Completions.
        - Gunakan caching untuk system prompt (biar hemat).
        - OCR text user tidak dicache karena selalu berbeda.
        """

        # ---------- Helper: sanitizer output ----------
        def _sanitize_output(s: str) -> str:
            if not s:
                return s
            s = s.strip()
            import re
            fence_match = re.fullmatch(r"```[a-zA-Z0-9_-]*\n([\s\S]*?)\n```", s)
            if fence_match:
                s = fence_match.group(1).strip()
            return s

        # ---------- Guard ----------
        if not text_to_translate or not text_to_translate.strip():
            return ""
        if not getattr(self, "is_openai_available", False):
            return "[OPENAI NOT CONFIGURED]"

        try:
            # --- Build prompts ---
            prompt_enhancements = self._build_prompt_enhancements(settings) if hasattr(self, "_build_prompt_enhancements") else ""
            target_lang = (target_lang or "Indonesian").strip()

            base_rule = (
                f"Output ONLY the final translation in {target_lang}, as RAW plain text. "
                f"No quotes, no code fences, no markdown, no labels, no explanations, "
                f"no original text, no notes, no extra commentary. "
                f"Preserve line breaks if the OCR text is multi-line dialogue."
            )

            style_rules = (
                "Translation style rules:\n"
                "- Dialogue should sound natural and colloquial, like authentic manga speech.\n"
                "- Adapt tone: casual for friends, polite for formal situations, exaggerated for comedic or dramatic scenes.\n"
                "- Keep character-specific quirks (stuttering, slang, verbal tics) if detectable.\n"
                "- Keep consistency of names, nicknames, and terms across translations.\n"
                "- If OCR contains sound effects (e.g., '????', '???'), translate to natural equivalents or expressive onomatopoeia.\n"
                "- Do NOT add translator notes.\n"
            )

            if is_enhanced and ocr_results:
                system_prompt = (
                    f"You are an expert manga translator.\n"
                    f"1. Automatically detect the language of the text.\n"
                    f"2. If Japanese ? merge and correct the following OCR outputs, then translate into natural {target_lang}.\n"
                    f"3. If already in {target_lang} ? return as-is with no changes.\n"
                    f"4. If in another language ? translate into {target_lang}.\n"
                    f"{style_rules} {prompt_enhancements} {base_rule}"
                )
                user_prompt = (
                    "OCR Results:\n"
                    f"1. Manga-OCR: {ocr_results.get('manga_ocr', '')}\n"
                    f"2. Tesseract: {ocr_results.get('tesseract', '')}"
                )
            else:
                system_prompt = (
                    f"You are an expert manga translator.\n"
                    f"1. Automatically detect the language of the input text.\n"
                    f"2. If Japanese ? silently correct OCR mistakes, then translate into natural {target_lang}.\n"
                    f"3. If already in {target_lang} ? return as-is with no changes.\n"
                    f"4. If in another language ? translate into {target_lang}.\n"
                    f"{style_rules} {prompt_enhancements} {base_rule}"
                )
                user_prompt = f"Raw OCR Text:\n{text_to_translate}"

            # --- Build request ---
            model_lower = (model_name or "").lower()
            supports_temperature = not (
                model_lower.startswith("gpt-5-mini") or model_lower.startswith("gpt-5-nano")
            )
            desired_temp = settings.get("temperature", 0.5) if isinstance(settings, dict) else 0.5

            req_kwargs = {
                "model": model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt,
                        # ?? simpan system prompt di cache biar hemat
                        "cache_control": {"type": "ephemeral"}
                    },
                    {"role": "user", "content": user_prompt},  # OCR text ? tidak dicache
                ],
            }
            if supports_temperature and desired_temp is not None:
                req_kwargs["temperature"] = float(desired_temp)

            # --- Call API ---
            client = getattr(self, "openai_client", None)
            if client is None:
                client = openai_client

            response = client.chat.completions.create(**req_kwargs)
            output_text = (response.choices[0].message.content or "").strip()
            output_text = _sanitize_output(output_text)

            # --- Hitung biaya dengan token usage dari API ---
            if hasattr(response, "usage"):
                in_tokens = response.usage.prompt_tokens
                out_tokens = response.usage.completion_tokens
                if hasattr(self, "api_cost_signal"):
                    self.api_cost_signal.emit(in_tokens, out_tokens, "OpenAI", model_name)

            # ? Update counter
            if hasattr(self, "snippet_translated_signal"):
                self.snippet_translated_signal.emit()

            return output_text or ""

        except Exception as e:
            err_msg = str(e)
            if "Unsupported value" in err_msg and "temperature" in err_msg:
                return "[OPENAI ERROR] Model ini tidak mendukung parameter temperature. Abaikan 'temperature' untuk model ini."
            if "invalid_request_error" in err_msg or "Error code: 400" in err_msg:
                return "[OPENAI ERROR] Permintaan tidak valid. Periksa parameter (model, messages, dsb)."
            if "rate_limit" in err_msg or "Rate limit" in err_msg:
                return "[OPENAI ERROR] Kena rate limit. Coba lagi beberapa saat."
            print(f"Error calling OpenAI API: {e}")
            return "[OPENAI ERROR]"

    def translate_with_openrouter(
        self,
        text_to_translate: str,
        target_lang: str,
        model_id: str,
        settings: dict | None = None,
        model_info: dict | None = None,
        is_enhanced: bool = False,
        ocr_results: dict | None = None,
        provider: str = 'OpenRouter'
    ):
        if not text_to_translate.strip():
            return ""

        provider_key = get_translate_provider_key(provider)
        provider_meta = LOCAL_TRANSLATE_PROVIDERS.get(provider_key, {})
        provider_display = provider_meta.get('display', provider or 'OpenRouter')
        error_prefix = provider_display.upper()

        provider_cfg = get_translate_provider_settings(provider_key)
        api_key = provider_cfg.get('api_key', '').strip()
        if not api_key and not provider_meta.get('api_key_optional'):
            return f"[{error_prefix} API KEY NOT CONFIGURED]"

        url = provider_cfg.get('url', '').strip() or provider_meta.get('url', "https://openrouter.ai/api/v1/chat/completions")
        if provider_key == 'openrouter' and url and url.startswith("http://") and not ('localhost' in url or '127.0.0.1' in url):
            url = "https://" + url[7:]

        # --- Dynamic prompt ---
        mode = settings.get('mode') if settings else None
        if mode == 'info':
            system_prompt = (
                f"You are an expert manga translator. Translate the user's text into clear, natural {target_lang} for narration or informational text. "
                f"Keep it smooth, neutral, and suitable for manga narration boxes.\n"
                f"IMPORTANT RULES:\n"
                f"- If a Japanese text includes a kanji followed by parentheses like 漢字(かんじ) or word(note), treat the text inside parentheses as a reading or small note — do NOT translate it literally.\n"
                f"- Translate only based on the main kanji meaning, not the content in parentheses.\n"
                f"- Example: 勇者(ゆうしゃ) → translate as 'Hero', not 'Yuusha'.\n"
                f"- Preserve parentheses if they indicate pronunciation notes or clarifications that exist in the original dialogue.\n"
                f"- Avoid slang or overly casual tone.\n"
                f"- Only output the final translation in {target_lang}.\n"
                f"- No markdown, notes, or extra explanation.\n"
                f"- Preserve line breaks.\n"
            )
        else:
            system_prompt = (
                f"You are an expert manga translator. Translate the user's text into natural, fluent {target_lang} suitable for published manga dialogue. "
                f"Keep the meaning, tone, and nuances from the original text.\n"
                f"IMPORTANT RULES:\n"
                f"- If the Japanese text contains kanji with parentheses — e.g. 漢字(かんじ) or name(note) — treat the content inside parentheses as furigana or reading aid, not as part of the dialogue.\n"
                f"- Translate the main kanji normally, but ignore or omit the reading inside parentheses in the final translation.\n"
                f"- Example: 神様(かみさま) → 'God', not 'Kamisama'.\n"
                f"- If parentheses contain explanatory notes (not reading), keep them translated in parentheses in {target_lang}.\n"
                f"- Use natural and neutral tone — not overly formal, but avoid slang or street language like 'lo', 'gue', or 'nih'.\n"
                f"- Output ONLY the final translation in {target_lang}.\n"
                f"- No quotes, markdown, or explanations.\n"
                f"- Preserve line breaks.\n"
            )

        if settings and settings.get('translation_style'):
            system_prompt += f" Use the style: {settings['translation_style']}."

        messages = [{"role": "system", "content": system_prompt}]
        user_content = ""
        if is_enhanced and isinstance(ocr_results, dict):
            user_content = "\n\n".join(filter(None, [
                ocr_results.get('manga_ocr', ''),
                ocr_results.get('tesseract', '')
            ])).strip() or text_to_translate
        else:
            user_content = text_to_translate
        messages.append({"role": "user", "content": user_content})

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": float(model_info.get('temperature', 0.7)) if model_info else 0.7,
            "max_tokens": int(model_info.get('max_tokens', 1024)) if model_info else 1024,
        }

        pr_timeout = int(provider_cfg.get('timeout', 60) or 60)
        pr_retries = int(provider_cfg.get('retries', 3) or 3)
        pr_backoff = float(provider_cfg.get('backoff', 1.5) or 1.5)

        try:
            response = robust_post(url, headers=headers, json_payload=payload,
                                timeout=pr_timeout, max_retries=pr_retries, backoff_factor=pr_backoff)
            data = response.json()
        except Exception as exc:
            return f"[{error_prefix} REQUEST ERROR: {exc}]"

        choices = data.get('choices')
        output_text = ""
        if isinstance(choices, list) and choices:
            msg = choices[0].get('message', {})
            content = msg.get('content')
            if isinstance(content, list):
                output_text = "".join(part.get('text', '') for part in content if isinstance(part, dict))
            elif isinstance(content, str):
                output_text = content

        if not output_text:
            if 'error' in data:
                return f"[{error_prefix} ERROR: {data['error'].get('message', 'Unknown error')}]"
            logger.warning(f"{provider_display} returned empty response: {response.text}")
            return f"[{error_prefix} ERROR: Empty response]"

        usage = data.get('usage') or {}
        if hasattr(self, "api_cost_signal"):
            self.api_cost_signal.emit(usage.get('prompt_tokens', 0), usage.get('completion_tokens', 0), provider_display, model_id)
        return output_text.strip()

    def get_translation_styles(self):
        return list(self.translation_styles)

    def load_translation_styles_from_disk(self):
        try:
            if os.path.exists(self._styles_storage_path):
                with open(self._styles_storage_path, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
                    if isinstance(data, list):
                        # merge unique while preserving built-ins first
                        new_styles = []
                        for s in data:
                            if s and s not in self.translation_styles:
                                self.translation_styles.append(s)
                                new_styles.append(s)

                        # If the style combo exists (UI already created), add loaded styles to it
                        try:
                            if getattr(self, 'style_combo', None) and new_styles:
                                for s in new_styles:
                                    try:
                                        self.style_combo.addItem(s)
                                    except Exception:
                                        pass
                        except Exception:
                            pass
        except Exception:
            # ignore load failures
            pass

    def save_translation_styles_to_disk(self):
        try:
            # ensure dir
            d = os.path.dirname(self._styles_storage_path)
            if d and not os.path.exists(d):
                os.makedirs(d, exist_ok=True)
            with open(self._styles_storage_path, 'w', encoding='utf-8') as fh:
                json.dump([s for s in self.translation_styles if s], fh, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def translate_text(self, text, target_lang):
        if not text or not text.strip():
            return ""

        # If DeepL has an active key, prefer it for non-AI translations
        deepl_key = get_active_key('deepl')
        if deepl_key:
            try:
                lang_map = {"Indonesian": "ID", "English": "EN-US", "Japanese": "JA", "Chinese": "ZH", "Korean": "KO"}
                url = "https://api-free.deepl.com/v2/translate"
                params = {"auth_key": deepl_key, "text": text, "target_lang": lang_map.get(target_lang, "ID")}
                response = requests.post(url, data=params, timeout=20); response.raise_for_status()
                return response.json()["translations"][0]["text"]
            except Exception as e:
                return f"[Translation Error (DeepL): {e}]"

        # If any API provider has active key, let higher-level logic use AI providers.
        any_key = False
        for prov in SETTINGS.get('apis', {}).values():
            if any(k.get('active') for k in (prov.get('keys') or [])):
                any_key = True
                break

        if not any_key:
            # No API keys at all: fallback to free translator library
            # Try googletrans first, then deep-translator
            try:
                from googletrans import Translator as GoogleTranslator
                tr = GoogleTranslator()
                res = tr.translate(text, dest=("id" if target_lang.lower().startswith("ind") else "en"))
                return getattr(res, 'text', str(res))
            except Exception:
                try:
                    from deep_translator import GoogleTranslator as DTGoogle
                    dest = 'id' if target_lang.lower().startswith('ind') else 'en'
                    return DTGoogle(source='auto', target=dest).translate(text)
                except Exception as e:
                    return f"[No API keys and no fallback translator available: {e}]"

        return "[No translation performed: use AI providers]"

    def _update_recent_translations_list(self):
        if not hasattr(self, 'typeset_recent_list'):
            return
        
        self.typeset_recent_list.clear()
        
        # Get up to 20 unique recent translations
        recent_texts = []
        for entry in reversed(getattr(self, 'history_entries', [])):
            text = entry.get('translated_text', '').strip()
            if text and text not in recent_texts:
                recent_texts.append(text)
                if len(recent_texts) >= 20:
                    break
                    
        for text in recent_texts:
            # truncate display if too long
            display_text = text if len(text) <= 60 else text[:57] + '...'
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, text)
            self.typeset_recent_list.addItem(item)

    def _on_recent_translation_clicked(self, item):
        text = item.data(Qt.UserRole)
        if text and self.selected_typeset_area:
            snippet = text[:20] + ('…' if len(text) > 20 else '')
            self._push_undo_snapshot(f"Apply Recent: {snippet}")
            self.selected_typeset_area.text = text
            self.redraw_all_typeset_areas()
            self.update_undo_redo_buttons_state()

    def _queue_ocr_translate_rect(self, unzoomed_rect, source_pil_image=None):
        source = source_pil_image or self.current_image_pil
        if source is None or not unzoomed_rect:
            return False
        left = max(0, int(unzoomed_rect.x()))
        top = max(0, int(unzoomed_rect.y()))
        right = min(source.width, int(unzoomed_rect.x() + unzoomed_rect.width()))
        bottom = min(source.height, int(unzoomed_rect.y() + unzoomed_rect.height()))
        if right <= left or bottom <= top:
            return False

        safe_rect = QRect(left, top, right - left, bottom - top)
        cropped_img = source.crop((left, top, right, bottom))
        cropped_cv_img = cv2.cvtColor(np.array(cropped_img), cv2.COLOR_RGB2BGR)
        job = {
            'image_path': self.get_current_data_key(),
            'rect': safe_rect,
            'polygon': None,
            'cropped_cv_img': cropped_cv_img,
            'settings': self.get_current_settings()
        }
        if self.batch_mode_checkbox.isChecked():
            self.add_to_batch_queue(job)
        else:
            self.add_job_to_queue(job)
        return True

    def trigger_click_to_translate(self, point):
        """Memproses klik pengguna pada kanvas untuk mendeteksi balon teks secara asinkron dan menerjemahkannya."""
        if not self.current_image_pil:
            return
        
        settings = self.get_current_settings()
        self.statusBar().showMessage("Detecting bubble at clicked point...")
        QApplication.processEvents()
        
        try:
            cv_image = cv2.cvtColor(np.array(self.current_image_pil), cv2.COLOR_RGB2BGR)
            # Create a 2x2 rect centered at the click point
            click_rect = QRect(point.x() - 1, point.y() - 1, 2, 2)
            
            mask = self.find_speech_bubble_mask(cv_image, click_rect, settings)
            if mask is None or cv2.countNonZero(mask) == 0:
                # Fallback to a neat manual rectangle centered at the click point
                self.statusBar().showMessage("No bubble found. Creating manual area...", 3000)
                fallback_rect = QRect(point.x() - 60, point.y() - 30, 120, 60)
                w, h = self.current_image_pil.width, self.current_image_pil.height
                x = max(0, min(fallback_rect.x(), w - 1))
                y = max(0, min(fallback_rect.y(), h - 1))
                width = max(10, min(fallback_rect.width(), w - x))
                height = max(10, min(fallback_rect.height(), h - y))
                fallback_rect = QRect(x, y, width, height)
                
                # Directly process this rect area!
                self.process_rect_area(self.zoom_coords(fallback_rect))
                return

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                self.statusBar().showMessage("No speech bubble contours found.", 3000)
                return

            best_contour = max(contours, key=cv2.contourArea)
            full_image_polygon = QPolygon([QPoint(int(p[0][0]), int(p[0][1])) for p in best_contour])
            
            # Directly process this polygon area for OCR & Translation!
            self.statusBar().showMessage("Bubble detected! Running AI OCR and translation...", 3000)
            self.process_confirmed_polygon(full_image_polygon)
            
        except Exception as e:
            self.statusBar().showMessage(f"Click-to-Translate failed: {e}", 4000)

    def on_full_page_translation_finished(self, created_areas, msg):
        worker = getattr(self, '_full_page_worker', None)
        cleaned_pil = getattr(worker, 'cleaned_image_pil', None) if worker is not None else None
        inpaint_requested = bool(getattr(worker, 'settings', {}).get('use_inpaint', True)) if worker is not None else False
        self.auto_translate_page_btn.setText(ActionText.FULL_PAGE_TRANSLATE)
        self.auto_translate_page_btn.setEnabled(True)
        if worker is not None:
            worker.wait(3000)  # pastikan thread benar-benar berhenti sebelum referensi dilepas
        self._full_page_worker = None

        if not created_areas:
            self.show_toast("Selesai", str(msg), kind="info")
            return

        self._push_undo_snapshot("Full-Page Translate")

        # Pasang hasil inpaint full-page (satu panggilan dari worker) sebagai base
        # image — mekanisme yang sama dengan Inpaint Brush (cleaned/pre_inpaint
        # record), jadi Undo/Cancel Inpaint tetap bekerja seperti biasa.
        page_cleaned = False
        pre_inpaint_png = None
        record_key = self.get_current_data_key()
        if cleaned_pil is not None:
            try:
                record = self.all_typeset_data.get(record_key, {}) if record_key else {}
                pre_inpaint_png = record.get('pre_inpaint_image_png') if isinstance(record, dict) else None
                if not pre_inpaint_png:
                    pre_inpaint_png = self._encode_cleaned_image(self.current_image_pil)
                self._apply_base_image(cleaned_pil)
                page_cleaned = True
            except Exception as e:
                print(f"Gagal menerapkan hasil inpaint halaman: {e}")
        elif inpaint_requested:
            self.show_banner(
                "full-page-inpaint-miss", "Inpaint halaman gagal",
                "Teks digambar tanpa pembersihan latar. Cek server IOPaint (127.0.0.1:8080) lalu ulangi.",
                kind="warning"
            )

        applied = 0
        for area_payload in created_areas:
            try:
                area = self._create_typeset_area(
                    rect=area_payload['rect'],
                    text=area_payload['text'],
                    settings=area_payload['settings'],
                    polygon=area_payload['polygon'],
                    original_text=area_payload['original_text'],
                    # Full-page membersihkan latar di worker — matikan live cv2.inpaint per area
                    manual_inpaint=False,
                    is_manual=False
                )
                area.set_override('use_inpaint', False)
                if page_cleaned:
                    # Latar sudah bersih — kotak background hanya menutupi artwork
                    area.set_override('use_background_box', False)
                self.typeset_areas.append(area)
                applied += 1
            except Exception as e:
                # Satu area gagal tidak boleh menggagalkan seluruh halaman
                print(f"Gagal membuat area typeset: {e}")

        if record_key:
            if page_cleaned:
                self._update_typeset_record(
                    record_key,
                    areas=list(self.typeset_areas),
                    redo=list(self.redo_stack),
                    cleaned_image_png=self._encode_cleaned_image(self.current_image_pil),
                    pre_inpaint_image_png=pre_inpaint_png,
                )
                self._refresh_inpaint_result_controls()
            else:
                self._update_typeset_record(
                    record_key,
                    areas=list(self.typeset_areas),
                    redo=list(self.redo_stack),
                )

        self.redraw_all_typeset_areas(refresh_layers=True)
        if applied < len(created_areas):
            self.show_banner(
                "full-page-partial", "Sebagian area gagal",
                f"{applied} dari {len(created_areas)} balon berhasil diterapkan ke canvas.",
                kind="warning"
            )
        self.statusBar().showMessage(f"Berhasil menerjemahkan {applied} balon teks di halaman ini.", 4000)
        self.show_toast("Page translated", f"Berhasil menerjemahkan {applied} balon teks di halaman ini.", kind="success")

    def on_full_page_translation_error(self, err_msg):
        self.auto_translate_page_btn.setText(ActionText.FULL_PAGE_TRANSLATE)
        self.auto_translate_page_btn.setEnabled(True)
        worker = getattr(self, '_full_page_worker', None)
        if worker is not None:
            worker.wait(3000)  # pastikan thread benar-benar berhenti sebelum referensi dilepas
        self._full_page_worker = None
        self.statusBar().showMessage("Penerjemahan halaman gagal.", 3000)
        self.show_banner("full-page-translation-error", "Penerjemahan halaman gagal", str(err_msg), kind="error")

    # ── Batch Full-Page Translation ────────────────────────────────────

    @staticmethod
    def _is_typeset_output_file(path) -> bool:
        """True bila file itu sendiri adalah hasil simpan *_typeset (mis. 01_typeset.png)."""
        if not path:
            return False
        stem = os.path.splitext(os.path.basename(str(path)))[0].lower()
        return stem.endswith('_typeset') or '_typeset' in stem

    def _has_typeset_pair(self, path) -> bool:
        """True bila halaman asli (mis. 01.jpg) sudah punya hasil *_typeset di disk atau di daftar file."""
        if not path or self._is_typeset_output_file(path):
            return False
        if hasattr(self, 'check_if_saved') and self.check_if_saved(path):
            return True
        path_part, _ = os.path.splitext(str(path))
        for ext in ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.PNG', '.JPG', '.JPEG', '.WEBP'):
            if os.path.exists(f"{path_part}_typeset{ext}"):
                return True
        norm_dir = os.path.normcase(os.path.abspath(os.path.dirname(str(path)))) if os.path.dirname(str(path)) else ''
        stem_lower = os.path.splitext(os.path.basename(str(path)))[0].lower()
        target_prefix = f"{stem_lower}_typeset"
        for other in getattr(self, 'image_files', []) or []:
            other_dir = os.path.normcase(os.path.abspath(os.path.dirname(str(other)))) if os.path.dirname(str(other)) else ''
            if norm_dir and other_dir and norm_dir != other_dir:
                continue
            other_stem = os.path.splitext(os.path.basename(str(other)))[0].lower()
            if other_stem == target_prefix or other_stem.startswith(f"{target_prefix}."):
                return True
        return False

    def _is_page_already_typeset(self, path) -> bool:
        """True bila file adalah *_typeset, punya pasangan *_typeset, atau sudah punya area typeset."""
        if not path:
            return True
        if self._is_typeset_output_file(path):
            return True
        if self._has_typeset_pair(path):
            return True
        key = self.get_current_data_key(path)
        record = self.all_typeset_data.get(key)
        if isinstance(record, dict) and record.get('areas'):
            return True
        return False

    def _on_full_scope_changed(self, _idx):
        scope = self.full_scope_combo.currentData()
        self.full_pick_pages_btn.setVisible(scope == 'selected')

    def _update_full_pick_pages_btn(self):
        valid = {p for p in self.image_files if not self._is_page_already_typeset(p)}
        count = sum(1 for p in self._full_selected_pages if p in valid)
        self.full_pick_pages_btn.setText(FullPageBatchText.PICK_PAGES_BTN.format(count=count))

    def _open_full_page_picker(self):
        """Dialog centang halaman. Return list path terpilih, None bila dibatalkan."""
        valid = set(self.image_files)
        if not valid:
            self.show_banner(
                "full-batch-no-files", "Tidak ada halaman",
                "Buka folder atau proyek manga terlebih dahulu.", kind="warning"
            )
            return None

        if self.current_image_path:
            active_key = self.get_current_data_key()
            self._update_typeset_record(active_key, areas=list(self.typeset_areas), redo=list(self.redo_stack))

        dlg = QDialog(self)
        dlg.setWindowTitle(FullPageBatchText.PICK_TITLE)
        dlg.setModal(True)
        dlg.resize(440, 520)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(16, 14, 16, 12)
        lay.setSpacing(10)

        hint = QLabel(FullPageBatchText.PICK_HINT)
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#4a5c78; font-size:8.5pt; font-style:italic;")
        lay.addWidget(hint)

        lst = QListWidget()
        prev_picked = set(self._full_selected_pages)
        for path in self.image_files:
            # Sembunyikan file output *_typeset (mis. 01_typeset.png) dari daftar pilih
            if self._is_typeset_output_file(path):
                continue
            already_done = self._is_page_already_typeset(path)
            item = QListWidgetItem(os.path.basename(path))
            item.setData(Qt.UserRole, path)
            item.setData(Qt.UserRole + 1, already_done)
            item.setCheckState(
                Qt.Checked if (path in prev_picked and not already_done) else Qt.Unchecked
            )
            if already_done:
                suffix = "(sudah _typeset)" if self._has_typeset_pair(path) else "(sudah typeset)"
                item.setText(f"{os.path.basename(path)}  {suffix}")
                item.setForeground(QColor("#4a5c78"))
            lst.addItem(item)
        lay.addWidget(lst)

        btn_row = QHBoxLayout()
        check_all = QPushButton(FullPageBatchText.PICK_CHECK_ALL)
        uncheck_all = QPushButton(FullPageBatchText.PICK_UNCHECK_ALL)
        check_all.clicked.connect(
            lambda: [
                lst.item(i).setCheckState(Qt.Checked)
                for i in range(lst.count())
                if not lst.item(i).data(Qt.UserRole + 1)
            ]
        )
        uncheck_all.clicked.connect(
            lambda: [lst.item(i).setCheckState(Qt.Unchecked) for i in range(lst.count())]
        )
        btn_row.addWidget(check_all)
        btn_row.addWidget(uncheck_all)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        lay.addWidget(buttons)

        if dlg.exec_() != QDialog.Accepted:
            return None
        picked = [
            lst.item(i).data(Qt.UserRole)
            for i in range(lst.count())
            if lst.item(i).checkState() == Qt.Checked
        ]
        self._full_selected_pages = [p for p in picked if p in valid]
        self._update_full_pick_pages_btn()
        return self._full_selected_pages

    def _collect_full_page_settings(self):
        """Rakit settings pipeline full-page (dipakai mode tunggal & batch)."""
        settings = self.get_current_settings()

        def _canon_provider(name):
            return {'gemini': 'Gemini', 'openai': 'OpenAI', 'openrouter': 'OpenRouter'}.get(
                str(name).lower(), name
            )

        tr_combo = getattr(self, 'full_translator_combo', None)
        translator_choice = (tr_combo.currentData() if tr_combo is not None else None) or 'ai_translate'
        settings['full_translator'] = translator_choice

        # Model penerjemah (dipakai _translate_batch): default model AI Translate
        # dari tab AI Cfg; pilihan 'ai_ocr' memakai provider/model AI OCR langsung.
        if translator_choice == 'ai_ocr' and settings.get('ocr_engine') == 'AI_OCR' and settings.get('ocr_ai_provider'):
            provider = _canon_provider(settings.get('ocr_ai_provider', ''))
            model_name = settings.get('ocr_ai_model_id', '')
        else:
            provider, model_name = self.get_selected_model_name()
            if hasattr(self, 'ai_model_combo'):
                idx = self.ai_model_combo.currentIndex()
                if idx >= 0:
                    data = self.ai_model_combo.itemData(idx, Qt.UserRole)
                    if data:
                        provider, model_name = data

        settings['ai_model'] = (provider, model_name)

        # Model untuk panggilan AI Vision full-page: selalu pakai model AI OCR (VLM)
        # bila dikonfigurasi — model translate belum tentu bisa menerima gambar.
        if settings.get('ocr_ai_provider') and settings.get('ocr_ai_model_id'):
            settings['vision_model'] = (
                _canon_provider(settings.get('ocr_ai_provider')),
                settings.get('ocr_ai_model_id'),
            )
        else:
            settings['vision_model'] = (provider, model_name)
        settings['target_lang'] = self.translate_combo.currentText()
        # Pipeline Full selalu membersihkan teks (deteksi → OCR → inpaint → translate);
        # tidak bergantung pada checkbox cleanup global — itu milik flow default.
        settings['use_inpaint'] = True

        combo = getattr(self, 'full_mode_combo', None)
        use_ai_vision = bool(combo.currentData()) if combo is not None else False
        return settings, use_ai_vision

    def _start_full_page_batch(self, scope):
        """Jalankan full-page translation utk cakupan 'selected' / 'project'."""
        from src.ui.main_window import BatchFullPageWorker  # hindari circular import

        if not self.image_files:
            self.show_banner(
                "full-batch-no-files", "Tidak ada halaman",
                "Buka folder atau proyek manga terlebih dahulu.", kind="warning"
            )
            return
        worker = getattr(self, '_full_page_worker', None)
        if worker is not None and worker.isRunning():
            self.show_banner(
                "full-page-busy", "Sedang berjalan",
                "Penerjemahan halaman masih diproses. Tunggu hingga selesai.", kind="warning"
            )
            return
        batch = getattr(self, '_full_batch_worker', None)
        if batch is not None and batch.isRunning():
            self.show_banner(
                "full-batch-busy", "Sedang berjalan",
                FullPageBatchText.BATCH_BUSY, kind="warning"
            )
            return

        if self.current_image_path:
            active_key = self.get_current_data_key()
            self._update_typeset_record(active_key, areas=list(self.typeset_areas), redo=list(self.redo_stack))

        if scope == 'selected':
            candidates = [p for p in getattr(self, '_full_selected_pages', []) if p in set(self.image_files)]
            if not candidates:
                picked = self._open_full_page_picker()
                if not picked:
                    self.show_banner(
                        "full-batch-need-pick", "Pilih halaman",
                        FullPageBatchText.START_NEED_PICK, kind="warning"
                    )
                    return
                candidates = picked
        else:
            candidates = list(self.image_files)

        # Halaman yang sudah di-typeset, file *_typeset, maupun halaman asli yang sudah
        # punya pasangan *_typeset (mis. 01.jpg + 01_typeset.png) dianggap selesai → dilewati.
        targets = []
        for path in candidates:
            if self._is_page_already_typeset(path):
                continue
            targets.append(path)
        if not targets:
            self.show_toast("Batch full-page", FullPageBatchText.START_NO_TARGETS, kind="info")
            return

        settings, use_ai_vision = self._collect_full_page_settings()

        self._full_batch_worker = BatchFullPageWorker(self, targets, settings, use_ai_vision)
        dialog = FullPageBatchProgressDialog(self, total_pages=len(targets))
        self._full_batch_dialog = dialog

        batch_worker = self._full_batch_worker
        batch_worker.page_started.connect(
            lambda cur, tot, name: (
                dialog.set_page(cur, tot, name),
                dialog.set_step(FullPageBatchText.DIALOG_STEP_WAIT),
            )
        )
        batch_worker.page_step.connect(lambda _pct, msg: dialog.set_step(msg))
        batch_worker.page_finished.connect(self._on_batch_page_finished)
        batch_worker.stats_updated.connect(
            lambda done, skipped, failed: (
                dialog.set_stats(done, skipped, failed),
                dialog.set_done_pages(done),
            )
        )
        batch_worker.batch_finished.connect(self._on_full_batch_finished)
        dialog.cancel_requested.connect(batch_worker.cancel)
        # Cleanup referensi thread hanya setelah QThread benar-benar selesai.
        batch_worker.finished.connect(self._on_full_batch_thread_done)
        batch_worker.finished.connect(batch_worker.deleteLater)

        dialog.show()
        batch_worker.start()

    def _on_batch_page_finished(self, path, created_areas, cleaned_b64, pre_b64):
        """Terapkan hasil satu halaman batch ke record data (bukan canvas)."""
        if self._is_page_already_typeset(path):
            return  # sudah di-typeset / punya pasangan _typeset — jangan menimpa (penjaga race)
        key = self.get_current_data_key(path)
        page_cleaned = cleaned_b64 is not None
        new_areas = []
        for payload in created_areas:
            try:
                area = self._create_typeset_area(
                    rect=payload['rect'],
                    text=payload['text'],
                    settings=payload['settings'],
                    polygon=payload['polygon'],
                    original_text=payload['original_text'],
                    # Full-page membersihkan latar di worker — matikan live cv2.inpaint per area
                    manual_inpaint=False,
                    is_manual=False
                )
                area.set_override('use_inpaint', False)
                if page_cleaned:
                    area.set_override('use_background_box', False)
                new_areas.append(area)
            except Exception as e:
                print(f"Gagal membuat area typeset ({os.path.basename(path)}): {e}")
        self._update_typeset_record(
            key,
            areas=new_areas,
            redo=[],
            cleaned_image_png=cleaned_b64,
            pre_inpaint_image_png=pre_b64,
        )
        if key == self.get_current_data_key():
            self.typeset_areas = list(new_areas)
            self.redo_stack = []

    def _on_full_batch_finished(self, done, skipped, failed):
        dialog = getattr(self, '_full_batch_dialog', None)
        if dialog is not None:
            dialog.mark_finished()
            dialog.accept()
            self._full_batch_dialog = None
        # Muat ulang halaman aktif agar hasil batch (bila halaman ini ikut
        # diproses / sudah punya record baru) tampil di canvas.
        if self.current_image_path:
            self.load_image(self.current_image_path)
        self.show_toast(
            "Batch full-page",
            FullPageBatchText.TOAST_DONE_FMT.format(done=done, skipped=skipped, failed=failed),
            kind="success" if failed == 0 else "warning"
        )

    def _on_full_batch_thread_done(self):
        # Dipanggil dari sinyal QThread.finished — thread sudah benar-benar
        # mati, aman melepas referensi.
        self._full_batch_worker = None

