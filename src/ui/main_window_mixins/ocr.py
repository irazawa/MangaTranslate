"""Method domain ocr, dipindahkan utuh dari main_window.py.

Fase 1 pemecahan monolit: isi method tidak diubah sama sekali.
Mixin ini hanya berguna sebagai bagian dari MangaOCRApp -- ia mengandalkan
atribut yang dibuat di MangaOCRApp.__init__.
"""

from src.ui.main_window_mixins._imports import *  # noqa: F401,F403


class OcrMixin:
    def _get_ai_ocr_entries(self):
        entries = []
        ocr_config = SETTINGS.get('ocr', {}) or {}
        provider_labels = getattr(APIManagerDialog, 'OCR_PROVIDERS', {}) if 'APIManagerDialog' in globals() else {}
        for provider_key, cfg in ocr_config.items():
            if not isinstance(cfg, dict):
                continue
            models = cfg.get('models')
            if not isinstance(models, list):
                continue
            provider_label = provider_labels.get(provider_key, provider_key.title())
            for model in models:
                if not isinstance(model, dict):
                    continue
                if not model.get('active'):
                    continue
                model_id = (model.get('id') or '').strip()
                if not model_id:
                    continue
                model_name = model.get('name', '').strip() or model_id
                display = f"AI OCR ({provider_label}: {model_name})"
                entries.append({
                    'display': display,
                    'data': {
                        'engine': 'AI_OCR',
                        'code': 'ai',
                        'provider': provider_key,
                        'provider_label': provider_label,
                        'model_id': model_id,
                        'model_name': model_name,
                    }
                })
        return entries

    def run_manga_ocr_installer(self, cpu_only=False):
        label = (
            "Reinstalling Manga-OCR with CPU-only PyTorch... This may take several minutes."
            if cpu_only else
            "Installing manga-ocr and its dependencies (PyTorch etc.)... This may take a few minutes."
        )
        progress_dlg = QProgressDialog(label, "Cancel", 0, 0, self)
        progress_dlg.setWindowModality(Qt.WindowModal)
        progress_dlg.setWindowTitle("Reinstalling Manga-OCR (CPU)" if cpu_only else "Installing Manga-OCR")
        # Apply premium dark theme styling
        progress_dlg.setStyleSheet(theme.progress_dialog_qss())
        progress_dlg.show()

        from src.ui.dialogs import PipInstallWorker
        if cpu_only:
            # Step 1: replace torch/torchvision with CPU-only builds.
            # Step 2: install manga-ocr from PyPI (torch already pinned to CPU).
            # Using --index-url in step 1 replaces PyPI so manga-ocr must be a
            # separate command that still uses the normal PyPI index.
            commands = [
                ["torch", "torchvision",
                 "--force-reinstall",
                 "--index-url", "https://download.pytorch.org/whl/cpu"],
                ["manga-ocr"],
            ]
        else:
            commands = [["manga-ocr"]]
        worker = PipInstallWorker(commands)

        def on_progress(status):
            progress_dlg.setLabelText(status)

        def on_finished(success, message):
            progress_dlg.close()
            if success:
                # manga_ocr was installed successfully by pip.
                # However, PyTorch DLL (c10.dll) cannot be loaded from a session that
                # already failed to import it at startup — a restart is required.
                self.populate_ocr_languages()
                self.show_banner(
                    "manga-ocr-install-complete",
                    "Installation Complete",
                    "Manga-OCR has been successfully installed!\n\n"
                    "Please restart the application to activate Manga-OCR.",
                    kind="success",
                )
            else:
                self.show_banner("manga-ocr-install-error", "Manga-OCR install failed", message, kind="error")

        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        progress_dlg.canceled.connect(worker.terminate)

        worker.start()
        self._manga_ocr_installer_worker = worker

    def on_ocr_lang_changed(self, index):
        """Dipanggil saat pengguna memilih bahasa baru dari dropdown."""
        if index < 0: return
        lang_data = self.ocr_lang_combo.itemData(index)
        if lang_data:
            self.ocr_engine_info_label.setText(f"Engine: {lang_data['engine']}")
            self.initialize_ocr_engine(lang_data)
            # Enable/disable per-language orientation controls depending on selected OCR language/engine
            en_combo = getattr(self, 'en_orientation_combo', None)
            jp_combo = getattr(self, 'jp_orientation_combo', None)
            if en_combo is not None and jp_combo is not None:
                engine = (lang_data.get('engine') or '').lower()
                code = (lang_data.get('code') or '').lower()
                # By default allow both
                enable_en = True
                enable_jp = True
                # If engine strongly indicates Japanese (Manga-OCR) or code is 'ja', disable EN
                if 'manga' in engine or code.startswith('ja'):
                    enable_en = False
                    enable_jp = True
                # If engine is EasyOCR/Tesseract and language is English, disable JP
                elif 'easyocr' in engine or 'tesseract' in engine or code.startswith('en'):
                    enable_en = True
                    enable_jp = False
                en_combo.setEnabled(enable_en)
                jp_combo.setEnabled(enable_jp)

    def preprocess_for_ocr(self, cv_image, orientation_hint="Auto-Detect"):
        # Basic orientation detection remains; preprocessing pipeline optional
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        if h == 0 or w == 0:
            return cv_image, 0
        angle = 0
        if orientation_hint == "Auto-Detect":
            try:
                coords = cv2.findNonZero(cv2.bitwise_not(gray))
                if coords is not None:
                    rect = cv2.minAreaRect(coords)
                    angle = rect[-1]
                    if w < h and angle < -45:
                        angle = -(90 + angle)
                    elif w > h and angle > 45:
                        angle = 90 - angle
                    else:
                        angle = -angle
            except cv2.error:
                angle = 0
        elif orientation_hint == "Vertical":
            if w > h:
                angle = 90

        # Rotate grayscale for subsequent preprocessing
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated_gray = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

        # Preprocessing: histogram equalization, Gaussian blur, Otsu threshold
        try:
            equalized = cv2.equalizeHist(rotated_gray)
            blurred = cv2.GaussianBlur(equalized, (3, 3), 0)
            _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        except cv2.error:
            # Fall back to original rotated gray if any op fails
            otsu = rotated_gray

        # Return BGR image expected by OCR engines
        processed_bgr = cv2.cvtColor(otsu, cv2.COLOR_GRAY2BGR)
        return processed_bgr, angle

    def perform_ocr(self, image_to_process, settings: dict) -> str:
        """
        [DIUBAH] Menjalankan OCR pada gambar yang diberikan berdasarkan pengaturan.
        """
        ocr_engine = settings['ocr_engine']
        # [MODIFIED] Check 'force_ai_ocr' override
        if SETTINGS.get('force_ai_ocr', False):
            ocr_engine = "AI_OCR"
        orientation = settings.get('orientation', 'Auto-Detect')
        ocr_lang = settings.get('ocr_lang', 'ja')
        raw_text = ""

        # For AI_OCR and MOFRL-GPT we must not alter the crop at all; send the pure raw image.
        if ocr_engine not in ("AI_OCR", "MOFRL-GPT"):
            # Penyesuaian rotasi sesuai orientasi (apply for non-AI engines)
            h, w = image_to_process.shape[:2]
            if orientation == "Vertical" and w > h:
                # rotate so that vertical text becomes horizontal for OCR engines that expect horizontal lines
                image_to_process = cv2.rotate(image_to_process, cv2.ROTATE_90_CLOCKWISE)
            elif orientation == "Horizontal" and h > w:
                # if user selected horizontal but image is taller than wide, rotate to horizontal
                image_to_process = cv2.rotate(image_to_process, cv2.ROTATE_90_COUNTERCLOCKWISE)

        # Jalankan OCR sesuai engine
        if ocr_engine == "Manga-OCR":
            if self.manga_ocr_reader:
                pil_img = Image.fromarray(cv2.cvtColor(image_to_process, cv2.COLOR_BGR2RGB))
                raw_text = self.manga_ocr_reader(pil_img)
            else:
                return "[ERROR: Manga-OCR not installed or initialized]"

        elif ocr_engine == "EasyOCR":
            if not self.easyocr_reader:
                return "[ERROR: EasyOCR not initialized. Select language and apply.]"
            gray = cv2.cvtColor(image_to_process, cv2.COLOR_BGR2GRAY)
            results = self.easyocr_reader.readtext(gray, detail=0, paragraph=True)
            raw_text = "\n".join(results)

        elif ocr_engine == "PaddleOCR":
            if not self.paddle_ocr_reader:
                return f"[ERROR: PaddleOCR for '{ocr_lang}' not ready. Please select it in the UI first.]"
            try:
                # PaddleOCR may expose ocr() or predict() depending on version.
                # Try common call patterns and normalize output.
                result = None
                texts = []
                try:
                    # prefer .ocr if available (older versions)
                    if hasattr(self.paddle_ocr_reader, 'ocr'):
                        result = self.paddle_ocr_reader.ocr(image_to_process, cls=True)
                    elif hasattr(self.paddle_ocr_reader, 'predict'):
                        result = self.paddle_ocr_reader.predict(image_to_process)
                    else:
                        # last-resort: try calling object directly
                        result = self.paddle_ocr_reader(image_to_process)
                except Exception:
                    # fallback to predict with image path or other signature is not attempted here
                    result = None

                # Normalize result to a list of lines
                if not result:
                    raw_text = ""
                else:
                    # result can be: [[(poly, (text, conf)), ...], ...] or similar
                    # Try several common shapes
                    candidate = None
                    if isinstance(result, (list, tuple)) and len(result) > 0:
                        candidate = result[0]

                    if isinstance(candidate, list):
                        for entry in candidate:
                            # entry can be [bbox, (text, prob)] or [ [points], (text, prob) ]
                            try:
                                if isinstance(entry, (list, tuple)) and len(entry) >= 2:
                                    text_blob = None
                                    # entry[1] may be (text, prob) or text string
                                    if isinstance(entry[1], (list, tuple)) and len(entry[1]) > 0:
                                        text_blob = entry[1][0]
                                    elif isinstance(entry[1], str):
                                        text_blob = entry[1]
                                    if text_blob:
                                        texts.append(text_blob)
                            except Exception:
                                continue
                    else:
                        # try to walk nested dict/list for 'text' keys
                        try:
                            # common dict-based result contains 'data' or similar
                            for page in result:
                                for line in page:
                                    if isinstance(line, dict):
                                        t = line.get('text') or line.get('transcription')
                                        if t:
                                            texts.append(t)
                                    elif isinstance(line, (list, tuple)) and len(line) >= 2:
                                        sub = line[1]
                                        if isinstance(sub, (list, tuple)) and len(sub) > 0:
                                            texts.append(sub[0])
                        except Exception:
                            pass

                    raw_text = "\n".join([t for t in texts if t])
            except Exception as e:
                print(f"Error during PaddleOCR execution: {e}")
                raw_text = "[PADDLEOCR RUNTIME ERROR]"

        elif ocr_engine == "DocTR":
            if not self.doctr_predictor: 
                return "[ERROR: DocTR not initialized]"
            
            try:
                # Convert BGR to RGB
                rgb_image = cv2.cvtColor(image_to_process, cv2.COLOR_BGR2RGB)
                
                # Predict
                result = self.doctr_predictor([rgb_image])
                
                # Extract text
                texts = []
                for page in result.pages:
                    for block in page.blocks:
                        for line in block.lines:
                            line_text = ' '.join([word.value for word in line.words])
                            texts.append(line_text)
                
                raw_text = "\n".join(texts)
            except Exception as e:
                print(f"Error during DocTR execution: {e}")
                raw_text = "[DOCTR RUNTIME ERROR]"

        elif ocr_engine == "AI_OCR":
            provider = settings.get('ocr_ai_provider')
            model_id = settings.get('ocr_ai_model_id')
            model_name = settings.get('ocr_ai_model_name')
            result = self._call_ai_ocr(image_to_process, provider, model_id, model_name)
            return result
        
        elif ocr_engine == "MOFRL-GPT":
            raw_text = self._call_mofrl_ocr(image_to_process, settings)
            return raw_text

        elif ocr_engine == "RapidOCR":
            if not self.rapid_ocr_reader: return "[ERROR: RapidOCR not initialized]"
            result, _ = self.rapid_ocr_reader(image_to_process)
            if result:
                raw_text = "\n".join([res[1] for res in result])

        elif ocr_engine == "Tesseract":
            try:
                gray = cv2.cvtColor(image_to_process, cv2.COLOR_BGR2GRAY)
                psm = 5 if orientation == "Vertical" else 6
                custom_config = f'--oem 1 --psm {psm}'
                writable_path = get_writable_tessdata_path()
                if writable_path and os.path.exists(writable_path):
                    custom_config += f' --tessdata-dir "{writable_path}"'
                raw_text = pytesseract.image_to_string(gray, lang=ocr_lang, config=custom_config).strip()
            except pytesseract.TesseractError as e:
                print(f"Tesseract Error in Worker: {e}")
                return f"[TESSERACT ERROR: {e}]"

        return raw_text

    def _get_ai_ocr_prompt(self, lang):
        if lang == "Japanese":
            return (
                "Task: Optical Character Recognition (OCR) for Japanese text.\n"
                "Input: an image.\n"
                "Output: ONLY the recognized text in natural reading order.\n\n"
                "Rules:\n"
                "- Do NOT explain or add any commentary.\n"
                "- Do NOT output markdown or formatting symbols.\n"
                "- Keep line breaks if they appear in the original image.\n"
                "- Preserve punctuation (。, 、, …, !, ? etc.).\n"
                "- When a small note or furigana is written next to a kanji, output it in parentheses after the kanji.\n"
                "  Example: 漢字 + note → 漢字(note)\n"
                "- If the note appears *before* the kanji (vertically aligned text), treat it the same way: 漢字(note).\n"
                "- If the note is unrelated annotation or translation note, also wrap it in parentheses.\n"
                "- Do NOT merge notes and kanji into a single block like [note][kanji].\n"
                "- Do NOT drop ellipses (…)\n"
                "- Just return the plain text with correct kanji-note pairing."
            )
        elif lang == "English":
            return (
                "Task: Optical Character Recognition (OCR) for English text.\n"
                "Input: an image.\n"
                "Output: ONLY the recognized text in natural reading order.\n\n"
                "Rules:\n"
                "- Do NOT explain or add any commentary.\n"
                "- Do NOT output markdown or formatting symbols.\n"
                "- Maintain original line breaks.\n"
                "- Preserve punctuation.\n"
                "- Return ONLY the plain text."
            )
        elif lang == "Korean":
            return (
                "Task: Optical Character Recognition (OCR) for Korean text (Hangul).\n"
                "Input: an image.\n"
                "Output: ONLY the recognized text in natural reading order.\n\n"
                "Rules:\n"
                "- Do NOT explain or add any commentary.\n"
                "- Do NOT output markdown or formatting symbols.\n"
                "- Maintain original line breaks.\n"
                "- Preserve punctuation.\n"
                "- Return ONLY the plain text."
            )
        elif lang == "Chinese":
            return (
                "Task: Optical Character Recognition (OCR) for Chinese text.\n"
                "Input: an image.\n"
                "Output: ONLY the recognized text in natural reading order.\n\n"
                "Rules:\n"
                "- Do NOT explain or add any commentary.\n"
                "- Do NOT output markdown or formatting symbols.\n"
                "- Maintain original line breaks.\n"
                "- Preserve punctuation.\n"
                "- Return ONLY the plain text."
            )
        else:
             return (
                "Task: Optical Character Recognition (OCR).\n"
                "Input: an image.\n"
                "Output: ONLY the recognized text in natural reading order.\n\n"
                "Rules:\n"
                "- Do NOT explain or add any commentary.\n"
                "- Output the text exactly as seen in the image.\n"
                "- Preserve punctuation and line breaks.\n"
                "- Return ONLY the plain text."
            )

    def _ai_ocr_provider_label(self, provider_key):
        normalized = str(provider_key or '').strip().lower()
        if normalized == 'gemini':
            return 'Gemini'
        if normalized == 'openai':
            return 'OpenAI'
        if normalized == 'openrouter':
            return 'OpenRouter'
        return provider_key or 'AI OCR'

    def _record_ai_ocr_cost_usage(self, data, provider_key, model_id, prompt_text, extracted_text, image_b64):
        provider_label = self._ai_ocr_provider_label(provider_key)
        usage = data.get('usage') if isinstance(data, dict) else {}
        if not isinstance(usage, dict):
            usage = {}

        def _int_from(*keys):
            for key in keys:
                value = usage.get(key)
                if value is None:
                    continue
                try:
                    return int(value)
                except (TypeError, ValueError):
                    continue
            return 0

        input_tokens = _int_from('prompt_tokens', 'input_tokens', 'prompt_token_count')
        output_tokens = _int_from('completion_tokens', 'output_tokens', 'candidates_token_count')
        if input_tokens <= 0 and output_tokens <= 0:
            prompt_tokens = max(1, len(prompt_text or '') // 4)
            image_tokens = max(256, len(image_b64 or '') // 2048)
            input_tokens = prompt_tokens + image_tokens
            output_tokens = max(1, len(extracted_text or '') // 4)

        if hasattr(self, "api_cost_signal"):
            self.api_cost_signal.emit(input_tokens, output_tokens, provider_label, model_id)

    def _call_ai_ocr(self, image_bgr, provider_key, model_id, model_name=None):
        if not provider_key or not model_id:
            return "[AI OCR ERROR: No active model configured]"

        provider_cfg = SETTINGS.get('ocr', {}).get(provider_key, {})
        url = (provider_cfg.get('url') or '').strip()
        if url and url.startswith("http://") and not ('localhost' in url or '127.0.0.1' in url):
            url = "https://" + url[7:]
        api_key = (provider_cfg.get('api_key') or '').strip()

        if not url:
            return "[AI OCR ERROR: API URL missing]"
        if not api_key:
            return "[AI OCR ERROR: API key missing]"

        success, buffer = cv2.imencode('.png', image_bgr)
        if not success:
            return "[AI OCR ERROR: Encoding image failed]"

        image_b64 = base64.b64encode(buffer.tobytes()).decode('utf-8')
        ai_lang = SETTINGS.get('ai_ocr_lang', 'Japanese')
        prompt_text = self._get_ai_ocr_prompt(ai_lang)

        data_url = f"data:image/png;base64,{image_b64}"
        
        # [CACHE SYSTEM]
        cache_key = hashlib.sha256((image_b64 + prompt_text + model_id).encode('utf-8')).hexdigest()
        cache_file = os.path.join(self.cache_dir, f"aiocr_{cache_key}.json")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                    print(f"[CACHE HIT] Returning cached OCR result for {cache_key}")
                    return cached_data.get('text', '')
            except Exception:
                pass

        # Prepare several payload variants to account for provider schema differences.
        payload_variants = []

        # Variant A: OpenRouter-style image_url with data URI
        payload_variants.append({
            "model": model_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": data_url}}
                    ]
                }
            ]
        })

        # Variant B: input_image with image_data (some providers expect this)
        payload_variants.append({
            "model": model_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "input_image", "image_data": data_url}
                    ]
                }
            ]
        })

        # Variant C: simple text prompt concatenated with data URI (fallback)
        payload_variants.append({
            "model": model_id,
            "messages": [
                {
                    "role": "user",
                    "content": prompt_text + "\n\nImage: " + data_url
                }
            ]
        })

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Ensure temp debug folder
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp')
        try:
            os.makedirs(temp_dir, exist_ok=True)
        except Exception:
            temp_dir = None

        # Save crop image for debugging
        if temp_dir:
            try:
                # Put debug images under temp/img/aiocr/
                img_dir = os.path.join(temp_dir, 'img', 'aiocr')
                os.makedirs(img_dir, exist_ok=True)
                timestamp = int(time.time())
                crop_path = os.path.join(img_dir, f'aiocr_crop_{timestamp}.png')
                with open(crop_path, 'wb') as f:
                    f.write(buffer.tobytes())
            except Exception:
                crop_path = None
        else:
            crop_path = None

        last_exception = None
        variant_index = 0
        for payload in payload_variants:
            variant_index += 1
            ppath = None
            rpath = None
            rjson_path = None
            errpath = None
            if temp_dir:
                try:
                    ppath = os.path.join(temp_dir, f'aiocr_payload_v{variant_index}.json')
                    with open(ppath, 'w', encoding='utf-8') as pf:
                        json.dump(payload, pf, ensure_ascii=False, indent=2)
                except Exception:
                    pass

            try:
                provider_label = self._ai_ocr_provider_label(provider_key)
                if hasattr(self, 'check_and_increment_usage') and not self.check_and_increment_usage(provider_label, model_id):
                    return f"[AI OCR ERROR: Rate limit reached for {model_id}]"
                # provider-specific overrides
                pr_timeout = int(provider_cfg.get('timeout', 45) or 45)
                pr_retries = int(provider_cfg.get('retries', 2) or 2)
                pr_backoff = float(provider_cfg.get('backoff', 1.5) or 1.5)
                response = robust_post(url, headers=headers, json_payload=payload,
                                       timeout=pr_timeout, max_retries=pr_retries, backoff_factor=pr_backoff)
            except requests.RequestException as exc:
                last_exception = exc
                # save response text if any
                if temp_dir:
                    try:
                        errpath = os.path.join(temp_dir, f'aiocr_response_v{variant_index}_error.txt')
                        with open(errpath, 'w', encoding='utf-8') as ef:
                            ef.write(str(exc))
                    except Exception:
                        pass
                # try next variant
                continue

            try:
                data = response.json()
            except ValueError:
                # Save raw response for diagnostics
                if temp_dir:
                    try:
                        rpath = os.path.join(temp_dir, f'aiocr_response_v{variant_index}_raw.txt')
                        with open(rpath, 'w', encoding='utf-8') as rf:
                            rf.write(response.text)
                    except Exception:
                        pass
                # try next variant
                continue

            # Save provider response for debugging
            if temp_dir:
                try:
                    rjson_path = os.path.join(temp_dir, f'aiocr_response_v{variant_index}.json')
                    with open(rjson_path, 'w', encoding='utf-8') as rf:
                        json.dump(data, rf, ensure_ascii=False, indent=2)
                except Exception:
                    pass

            extracted = self._extract_ai_ocr_text(data)
            # if the model explicitly says there's no image, keep trying other variants
            if extracted and 'i cannot see any image' not in extracted.lower():
                self._record_ai_ocr_cost_usage(data, provider_key, model_id, prompt_text, extracted, image_b64)
                # [CACHE SAVE]
                try:
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump({'text': extracted, 'model': model_id, 'timestamp': time.time()}, f)
                except Exception:
                    pass

                # Optionally remove debug files for this run
                try:
                    if SETTINGS.get('cleanup', {}).get('remove_ai_temp_files') and temp_dir:
                        for p in (crop_path, ppath, rpath, rjson_path, errpath):
                            try:
                                if p and os.path.exists(p) and os.path.commonpath([os.path.abspath(p), os.path.abspath(temp_dir)]) == os.path.abspath(temp_dir):
                                    os.remove(p)
                            except Exception:
                                pass
                except Exception:
                    pass
                return extracted

        # If we reach here, all variants failed
        if last_exception:
            return f"[AI OCR REQUEST ERROR: {last_exception}]"
        return "[AI OCR ERROR: Empty or unrecognized response from provider]"

    def _call_mofrl_ocr(self, image_bgr, settings):
        """
        MOFRL-GPT: OCR berbasis GPT multimodal (OpenAI/Gemini/OpenRouter)
        Ambil API key dari SETTINGS['apis'][provider]['keys'][0]['value'].
        """
        import base64, cv2, json, requests, traceback

        try:
            translate_cfg = SETTINGS.get('translation', {})
            provider = translate_cfg.get('provider', 'OpenAI').lower()
            model = translate_cfg.get('model', 'gpt-5-nano').lower()

            apis_cfg = SETTINGS.get('apis', {})

            def extract_key(list_obj):
                if not list_obj:
                    return ""
                first = list_obj[0]
                if isinstance(first, dict):
                    return first.get("value", "")
                elif isinstance(first, str):
                    return first
                return ""

            # choose api_url and api_key based on provider
            api_url = ""
            api_key = ""
            if provider.startswith("openai"):
                api_url = "https://api.openai.com/v1/chat/completions"
                api_key = extract_key(apis_cfg.get('openai', {}).get('keys', []))
            elif provider.startswith("gemini"):
                api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                api_key = extract_key(apis_cfg.get('gemini', {}).get('keys', []))
            elif provider.startswith("openrouter"):
                api_url = "https://openrouter.ai/api/v1/chat/completions"
                api_key = extract_key(apis_cfg.get('openrouter', {}).get('keys', []))
            else:
                return f"[MOFRL ERROR: Provider '{provider}' belum didukung]"

            if not api_key:
                return f"[MOFRL ERROR: API key kosong untuk provider {provider}]"

            # encode crop (raw) and save debug copy
            success, buffer = cv2.imencode('.png', image_bgr)
            if not success:
                return "[MOFRL ERROR: Gagal encode gambar]"
            image_b64 = base64.b64encode(buffer).decode('utf-8')

            ai_lang = SETTINGS.get('ai_ocr_lang', 'Japanese')
            prompt = self._get_ai_ocr_prompt(ai_lang)
            # Prepare temp debug folder
            temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp')
            try:
                os.makedirs(temp_dir, exist_ok=True)
            except Exception:
                temp_dir = None

            if temp_dir:
                try:
                    # Put debug images under temp/img/mofrl/
                    img_dir = os.path.join(temp_dir, 'img', 'mofrl')
                    os.makedirs(img_dir, exist_ok=True)
                    ts = int(time.time())
                    crop_path = os.path.join(img_dir, f'mofrl_crop_{ts}.png')
                    with open(crop_path, 'wb') as cf:
                        cf.write(buffer.tobytes())
                except Exception:
                    pass

            headers = {"Content-Type": "application/json"}
            last_exception = None

            # For OpenAI/OpenRouter try several payload variants (data_uri, input_image, inline text)
            if provider.startswith('openai') or provider.startswith('openrouter'):
                headers["Authorization"] = f"Bearer {api_key}"
                token_field = "max_tokens"
                if model.startswith("gpt-5"):
                    token_field = "max_completion_tokens"

                payload_variants = []
                # Variant A: image_url with data URI
                payload_variants.append({
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
                            ]
                        }
                    ],
                    token_field: 2048
                })

                # Variant B: input_image with image_data
                payload_variants.append({
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "input_image", "image_data": f"data:image/png;base64,{image_b64}"}
                            ]
                        }
                    ],
                    token_field: 2048
                })

                # Variant C: prompt + data URI in single content
                payload_variants.append({
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt + "\n\nImage: " + f"data:image/png;base64,{image_b64}"
                        }
                    ],
                    token_field: 2048
                })

                variant_index = 0
                for payload in payload_variants:
                    variant_index += 1
                    # save payload
                    if temp_dir:
                        try:
                            ppath = os.path.join(temp_dir, f'mofrl_payload_v{variant_index}.json')
                            with open(ppath, 'w', encoding='utf-8') as pf:
                                json.dump(payload, pf, ensure_ascii=False, indent=2)
                        except Exception:
                            pass

                    try:
                        # Use apis settings if available for timeout/retries/backoff
                        apis_provider_cfg = apis_cfg.get(provider, {}) or {}
                        pr_timeout = int(apis_provider_cfg.get('timeout', 90) or 90)
                        pr_retries = int(apis_provider_cfg.get('retries', 2) or 2)
                        pr_backoff = float(apis_provider_cfg.get('backoff', 1.5) or 1.5)
                        response = robust_post(api_url, headers=headers, json_payload=payload,
                                               timeout=pr_timeout, max_retries=pr_retries, backoff_factor=pr_backoff)
                    except requests.RequestException as exc:
                        last_exception = exc
                        if temp_dir:
                            try:
                                errpath = os.path.join(temp_dir, f'mofrl_response_v{variant_index}_error.txt')
                                with open(errpath, 'w', encoding='utf-8') as ef:
                                    ef.write(str(exc))
                            except Exception:
                                pass
                        continue

                    try:
                        resp_json = response.json()
                    except Exception:
                        if temp_dir:
                            try:
                                rpath = os.path.join(temp_dir, f'mofrl_response_v{variant_index}_raw.txt')
                                with open(rpath, 'w', encoding='utf-8') as rf:
                                    rf.write(response.text)
                            except Exception:
                                pass
                        continue

                    if temp_dir:
                        try:
                            rjson_path = os.path.join(temp_dir, f'mofrl_response_v{variant_index}.json')
                            with open(rjson_path, 'w', encoding='utf-8') as rf:
                                json.dump(resp_json, rf, ensure_ascii=False, indent=2)
                        except Exception:
                            pass

                    # extract text like AI OCR helper
                    extracted = self._extract_ai_ocr_text(resp_json)
                    if extracted and 'i cannot see any image' not in extracted.lower():
                        # Optionally remove debug files for this run
                        try:
                            if SETTINGS.get('cleanup', {}).get('remove_ai_temp_files') and temp_dir:
                                for p in (crop_path, ppath, rpath, rjson_path, errpath):
                                    try:
                                        if p and os.path.exists(p) and os.path.commonpath([os.path.abspath(p), os.path.abspath(temp_dir)]) == os.path.abspath(temp_dir):
                                            os.remove(p)
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                        return extracted

                if last_exception:
                    return f"[MOFRL ERROR: {last_exception}]"
                return "[MOFRL ERROR: Empty or unrecognized response from provider]"

            elif provider.startswith('gemini'):
                # Gemini expects inline_data and uses API key in query param
                api_url_with_key = api_url + f"?key={api_key}"
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt},
                                {"inline_data": {"mime_type": "image/png", "data": image_b64}}
                            ]
                        }
                    ]
                }

                if temp_dir:
                    try:
                        ppath = os.path.join(temp_dir, 'mofrl_payload_gemini.json')
                        with open(ppath, 'w', encoding='utf-8') as pf:
                            json.dump(payload, pf, ensure_ascii=False, indent=2)
                    except Exception:
                        pass

                try:
                    response = requests.post(api_url_with_key, headers=headers, data=json.dumps(payload), timeout=90)
                    response.raise_for_status()
                except requests.RequestException as exc:
                    return f"[MOFRL ERROR: {exc}]"

                try:
                    resp_json = response.json()
                except Exception:
                    if temp_dir:
                        try:
                            rpath = os.path.join(temp_dir, 'mofrl_response_gemini_raw.txt')
                            with open(rpath, 'w', encoding='utf-8') as rf:
                                rf.write(response.text)
                        except Exception:
                            pass
                    return "[MOFRL ERROR: Invalid JSON from Gemini]"

                if temp_dir:
                    try:
                        rjson_path = os.path.join(temp_dir, 'mofrl_response_gemini.json')
                        with open(rjson_path, 'w', encoding='utf-8') as rf:
                            json.dump(resp_json, rf, ensure_ascii=False, indent=2)
                    except Exception:
                        pass

                # Try to extract content similar to existing code
                result = ""
                # check candidates/content structure
                candidates = resp_json.get('candidates') or []
                if candidates and isinstance(candidates[0], dict) and 'content' in candidates[0]:
                    parts = candidates[0]['content'].get('parts', [])
                    if parts:
                        result = '\n'.join(p.get('text', '') for p in parts if isinstance(p, dict)).strip()

                # fallback
                if not result:
                    result = resp_json.get('output_text') or resp_json.get('text') or ''
                    if isinstance(result, list):
                        result = '\n'.join([r for r in result if isinstance(r, str)])
                    result = (result or '').strip()

                if not result:
                    # Optionally remove debug files
                    try:
                        if SETTINGS.get('cleanup', {}).get('remove_ai_temp_files') and temp_dir:
                            for p in (crop_path, ppath, rpath, rjson_path):
                                try:
                                    if p and os.path.exists(p) and os.path.commonpath([os.path.abspath(p), os.path.abspath(temp_dir)]) == os.path.abspath(temp_dir):
                                        os.remove(p)
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    return "[MOFRL ERROR: hasil kosong]"
                try:
                    if SETTINGS.get('cleanup', {}).get('remove_ai_temp_files') and temp_dir:
                        for p in (crop_path, ppath, rpath, rjson_path):
                            try:
                                if p and os.path.exists(p) and os.path.commonpath([os.path.abspath(p), os.path.abspath(temp_dir)]) == os.path.abspath(temp_dir):
                                    os.remove(p)
                            except Exception:
                                pass
                except Exception:
                    pass
                return result

        except Exception as e:
            traceback.print_exc()
            return f"[MOFRL ERROR: {e}]"

    def _extract_ai_ocr_text(self, response_json):
        if not isinstance(response_json, dict):
            return ""

        choices = response_json.get('choices')
        if isinstance(choices, list) and choices:
            message = choices[0].get('message', {}) if isinstance(choices[0], dict) else {}
            content = message.get('content') if isinstance(message, dict) else None
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                parts = []
                for chunk in content:
                    if isinstance(chunk, dict):
                        text_val = chunk.get('text') or chunk.get('content')
                        if isinstance(text_val, str) and text_val.strip():
                            parts.append(text_val.strip())
                if parts:
                    return '\n'.join(parts).strip()

        # Some providers might return 'message' directly as string
        message = response_json.get('message')
        if isinstance(message, str):
            return message.strip()

        if isinstance(message, dict):
            content = message.get('content')
            if isinstance(content, str):
                return content.strip()

        # Fallback to top-level 'text' or 'output_text'
        for key in ('text', 'output_text'):
            val = response_json.get(key)
            if isinstance(val, str):
                return val.strip()
            if isinstance(val, list):
                parts = [v.strip() for v in val if isinstance(v, str)]
                if parts:
                    return '\n'.join(parts)
        return ""
