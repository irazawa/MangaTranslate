"""Method domain layer untuk Canvas Layers Manager dan OCR/Translation Inspector."""

from src.ui.main_window_mixins._imports import *  # noqa: F401,F403


class LayerMixin:
    @staticmethod
    def _compact_preview_line(raw_text: str, limit: int = 42) -> str:
        collapsed = " ".join((raw_text or "").split())
        if len(collapsed) <= limit:
            return collapsed
        return collapsed[: max(1, limit - 1)].rstrip() + "…"

    def _layers_hero_qss(self) -> str:
        return (
            f"QFrame#layers-hero {{ background: {theme.COLORS['card']}; "
            f"border: 1px solid {theme.COLORS['border']}; "
            f"border-left: 3px solid {theme.COLORS['accent']}; border-radius: 8px; }}"
        )

    def _layers_list_qss(self) -> str:
        return (
            f"""
            QListWidget#layers-list {{
                background-color: {theme.COLORS["panel"]};
                border: 1px solid {theme.COLORS["border"]};
                border-radius: 8px;
                padding: 4px;
                color: {theme.COLORS["text"]};
                outline: none;
            }}
            QListWidget#layers-list::item {{
                background-color: {theme.COLORS["card_alt"]};
                border: 1px solid {theme.COLORS["border"]};
                border-radius: 6px;
                margin-bottom: 4px;
                padding: 2px;
            }}
            QListWidget#layers-list::item:hover {{
                background-color: {theme.COLORS["border"]};
                color: {theme.COLORS["text"]};
            }}
            QListWidget#layers-list::item:selected {{
                background-color: {theme.COLORS["border"]};
                border: 1px solid {theme.COLORS["accent"]};
                color: {theme.COLORS["accent"]};
            }}
            """
        )

    def _small_layer_button_qss(self, danger: bool = False, active: bool = False) -> str:
        if danger:
            return (
                f"background-color: {theme.COLORS['danger']};"
                f"border: 1px solid {theme.COLORS['danger']};"
                f"color: {theme.COLORS['bg']};"
                "border-radius: 4px; padding: 0px;"
            )
        border = theme.COLORS["accent"] if active else theme.COLORS["border"]
        color = theme.COLORS["accent"] if active else theme.COLORS["muted"]
        return (
            f"background-color: {theme.COLORS['card_alt']};"
            f"border: 1px solid {border};"
            f"color: {color};"
            "border-radius: 4px; padding: 0px;"
        )

    def _create_layers_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(10)

        # ── Hero summary card ────────────────────────────────────────────────
        self._layers_hero_frame = QFrame()
        self._layers_hero_frame.setObjectName("layers-hero")
        self._layers_hero_frame.setStyleSheet(self._layers_hero_qss())
        hero_v = QVBoxLayout(self._layers_hero_frame)
        hero_v.setContentsMargins(12, 10, 12, 10)
        hero_v.setSpacing(6)

        hero_top = QHBoxLayout()
        hero_top.setSpacing(6)
        hero_title = QLabel(LayersText.HERO_TITLE)
        hero_title.setMinimumWidth(0)
        hero_title.setStyleSheet(
            f"color: {theme.COLORS['text']}; font-weight: 800; font-size: 10pt; border: none;"
        )
        self.layers_count_badge = QLabel(LayersText.HERO_BADGE_FMT.format(count=0))
        self.layers_count_badge.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.layers_count_badge.setStyleSheet(
            f"color: {theme.COLORS['accent']}; background: rgba(56, 189, 248, 0.12); "
            f"border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 999px; "
            f"padding: 2px 8px; font-size: 7.5pt; font-weight: 700;"
        )
        hero_top.addWidget(hero_title)
        hero_top.addStretch()
        hero_top.addWidget(self.layers_count_badge)
        hero_v.addLayout(hero_top)

        hero_sub = QLabel(LayersText.HERO_SUBTITLE)
        hero_sub.setWordWrap(True)
        hero_sub.setMinimumWidth(0)
        hero_sub.setStyleSheet(f"color: {theme.COLORS['muted']}; font-size: 8.5pt; border: none;")
        hero_v.addWidget(hero_sub)
        layout.addWidget(self._layers_hero_frame)

        # ── Layers list group ────────────────────────────────────────────────
        list_group = QGroupBox(LayersText.LIST_GROUP_TITLE)
        list_v = QVBoxLayout(list_group)
        list_v.setContentsMargins(10, 14, 10, 10)
        list_v.setSpacing(8)

        self.layer_search_input = QLineEdit()
        self.layer_search_input.setMinimumWidth(0)
        self.layer_search_input.setClearButtonEnabled(True)
        self.layer_search_input.setPlaceholderText(LayersText.SEARCH_PLACEHOLDER)
        self.layer_search_input.textChanged.connect(self._filter_layers_list)
        list_v.addWidget(self.layer_search_input)

        self.layers_list_widget = QListWidget()
        self.layers_list_widget.setObjectName("layers-list")
        self.layers_list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.layers_list_widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.layers_list_widget.setMinimumWidth(0)
        self.layers_list_widget.setMinimumHeight(150)
        self.layers_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.layers_list_widget.customContextMenuRequested.connect(self._show_layer_context_menu)
        self.layers_list_widget.setStyleSheet(self._layers_list_qss())
        self.layers_list_widget.itemSelectionChanged.connect(self._on_layer_selection_changed)
        self.layers_list_widget.itemDoubleClicked.connect(self._on_layer_item_double_clicked)
        list_v.addWidget(self.layers_list_widget, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        add_layer_btn = QPushButton(LayersText.BTN_ADD_LAYER)
        add_layer_btn.setMinimumWidth(0)
        add_layer_btn.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        add_layer_btn.setIcon(app_icon("plus", theme.COLORS["text"], 13))
        add_layer_btn.setIconSize(QSize(13, 13))
        add_layer_btn.setStyleSheet(theme.secondary_button_qss())
        add_layer_btn.clicked.connect(self._add_new_manual_layer)

        self.layer_duplicate_btn = QPushButton(LayersText.BTN_DUPLICATE_LAYER)
        self.layer_duplicate_btn.setMinimumWidth(0)
        self.layer_duplicate_btn.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.layer_duplicate_btn.setIcon(app_icon("copy", theme.COLORS["text"], 13))
        self.layer_duplicate_btn.setIconSize(QSize(13, 13))
        self.layer_duplicate_btn.setStyleSheet(theme.secondary_button_qss())
        self.layer_duplicate_btn.clicked.connect(self._duplicate_selected_layer)

        clear_all_btn = QPushButton(LayersText.BTN_CLEAR_ALL)
        clear_all_btn.setMinimumWidth(0)
        clear_all_btn.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        clear_all_btn.setIcon(app_icon("trash", theme.COLORS["danger"], 13))
        clear_all_btn.setIconSize(QSize(13, 13))
        clear_all_btn.setStyleSheet(theme.danger_button_qss())
        clear_all_btn.clicked.connect(self._clear_all_layers)

        btn_row.addWidget(add_layer_btn, 1)
        btn_row.addWidget(self.layer_duplicate_btn, 1)
        btn_row.addWidget(clear_all_btn, 1)
        list_v.addLayout(btn_row)
        layout.addWidget(list_group, 1)

        # ── Selected Layer OCR & Translation Inspector ───────────────────────
        inspector_group = QGroupBox(LayersText.INSPECTOR_TITLE)
        insp_v = QVBoxLayout(inspector_group)
        insp_v.setContentsMargins(10, 14, 10, 10)
        insp_v.setSpacing(6)

        self.layer_inspector_status_label = QLabel(LayersText.INSPECTOR_EMPTY_HINT)
        self.layer_inspector_status_label.setWordWrap(True)
        self.layer_inspector_status_label.setMinimumWidth(0)
        self.layer_inspector_status_label.setStyleSheet(f"color: {theme.COLORS['muted']}; font-size: 8pt;")
        insp_v.addWidget(self.layer_inspector_status_label)

        opacity_layout = QHBoxLayout()
        opacity_layout.setSpacing(6)
        op_lbl = QLabel(LayersText.LABEL_OPACITY)
        op_lbl.setMinimumWidth(0)
        op_lbl.setStyleSheet(f"color: {theme.COLORS['muted']}; font-size: 8.5pt; font-weight: 600;")
        opacity_layout.addWidget(op_lbl)
        self.layer_opacity_slider = QSlider(Qt.Horizontal)
        self.layer_opacity_slider.setMinimumWidth(0)
        self.layer_opacity_slider.setRange(0, 100)
        self.layer_opacity_slider.setValue(100)
        self.layer_opacity_slider.setSingleStep(5)
        self.layer_opacity_slider.sliderPressed.connect(self._on_opacity_slider_pressed)
        self.layer_opacity_slider.valueChanged.connect(self._on_opacity_slider_changed)
        self.layer_opacity_slider.sliderReleased.connect(self._on_opacity_slider_released)
        opacity_layout.addWidget(self.layer_opacity_slider, 1)
        self.layer_opacity_label = QLabel("100%")
        self.layer_opacity_label.setMinimumWidth(34)
        self.layer_opacity_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        opacity_layout.addWidget(self.layer_opacity_label)
        insp_v.addLayout(opacity_layout)

        ocr_lbl = QLabel(LayersText.LABEL_OCR_TEXT)
        ocr_lbl.setMinimumWidth(0)
        ocr_lbl.setStyleSheet(f"color: {theme.COLORS['muted']}; font-size: 8.5pt; font-weight: 600;")
        insp_v.addWidget(ocr_lbl)

        self.layer_ocr_edit = QTextEdit()
        self.layer_ocr_edit.setAcceptRichText(False)
        self.layer_ocr_edit.setMinimumWidth(0)
        self.layer_ocr_edit.setFixedHeight(52)
        self.layer_ocr_edit.setPlaceholderText(LayersText.PLACEHOLDER_OCR_TEXT)
        insp_v.addWidget(self.layer_ocr_edit)

        tl_lbl = QLabel(LayersText.LABEL_TRANSLATED_TEXT)
        tl_lbl.setMinimumWidth(0)
        tl_lbl.setStyleSheet(f"color: {theme.COLORS['muted']}; font-size: 8.5pt; font-weight: 600;")
        insp_v.addWidget(tl_lbl)

        self.layer_trans_edit = QTextEdit()
        self.layer_trans_edit.setAcceptRichText(False)
        self.layer_trans_edit.setMinimumWidth(0)
        self.layer_trans_edit.setFixedHeight(62)
        self.layer_trans_edit.setPlaceholderText(LayersText.PLACEHOLDER_TRANSLATED_TEXT)
        insp_v.addWidget(self.layer_trans_edit)

        action_row = QHBoxLayout()
        action_row.setSpacing(6)
        self.layer_apply_text_btn = QPushButton(LayersText.BTN_APPLY_TEXT)
        self.layer_apply_text_btn.setMinimumWidth(0)
        self.layer_apply_text_btn.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.layer_apply_text_btn.setIcon(app_icon("check", theme.COLORS["bg"], 13))
        self.layer_apply_text_btn.setIconSize(QSize(13, 13))
        self.layer_apply_text_btn.setToolTip(LayersText.TIP_APPLY_TEXT)
        self.layer_apply_text_btn.setStyleSheet(compact_primary_button_qss())
        self.layer_apply_text_btn.clicked.connect(self._apply_inspector_text_changes)

        self.layer_retranslate_btn = QPushButton(LayersText.BTN_RETRANSLATE)
        self.layer_retranslate_btn.setMinimumWidth(0)
        self.layer_retranslate_btn.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.layer_retranslate_btn.setIcon(app_icon("sparkles", theme.COLORS["accent"], 13))
        self.layer_retranslate_btn.setIconSize(QSize(13, 13))
        self.layer_retranslate_btn.setToolTip(LayersText.TIP_RETRANSLATE)
        self.layer_retranslate_btn.setStyleSheet(theme.secondary_button_qss())
        self.layer_retranslate_btn.clicked.connect(self._retranslate_selected_layer_from_ocr)

        self.layer_advanced_edit_btn = QPushButton(LayersText.BTN_ADVANCED_EDIT)
        self.layer_advanced_edit_btn.setMinimumWidth(0)
        self.layer_advanced_edit_btn.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.layer_advanced_edit_btn.setIcon(app_icon("type", theme.COLORS["text"], 13))
        self.layer_advanced_edit_btn.setIconSize(QSize(13, 13))
        self.layer_advanced_edit_btn.setToolTip(LayersText.TIP_ADVANCED_EDIT)
        self.layer_advanced_edit_btn.setStyleSheet(theme.secondary_button_qss())
        self.layer_advanced_edit_btn.clicked.connect(
            lambda: self.start_inline_edit(self.selected_typeset_area)
            if getattr(self, 'selected_typeset_area', None) is not None else None
        )

        action_row.addWidget(self.layer_apply_text_btn, 1)
        action_row.addWidget(self.layer_retranslate_btn, 1)
        action_row.addWidget(self.layer_advanced_edit_btn, 1)
        insp_v.addLayout(action_row)

        for seq in ("Ctrl+Return", "Ctrl+Enter"):
            apply_sc = QShortcut(QKeySequence(seq), inspector_group)
            apply_sc.setContext(Qt.WidgetWithChildrenShortcut)
            apply_sc.activated.connect(self._apply_inspector_text_changes)

        layout.addWidget(inspector_group)
        self._sync_layer_inspector_from_selection()
        return tab

    def _update_layers_count_badge(self):
        badge = getattr(self, 'layers_count_badge', None)
        if badge is None:
            return
        count = len(getattr(self, 'typeset_areas', []) or [])
        fmt = LayersText.HERO_BADGE_SINGLE_FMT if count == 1 else LayersText.HERO_BADGE_FMT
        badge.setText(fmt.format(count=count))

    def _refresh_layers_list(self):
        if not hasattr(self, 'layers_list_widget') or self.layers_list_widget is None:
            return
        if getattr(self, 'is_transform_preview', False):
            return

        hero_frame = getattr(self, '_layers_hero_frame', None)
        if hero_frame is not None:
            hero_frame.setStyleSheet(self._layers_hero_qss())
        self._update_layers_count_badge()

        # Selection initiated inside QListWidget must NOT destroy list items mid-click
        # so double-click -> itemDoubleClicked fires reliably.
        if getattr(self, '_in_layer_list_selection', False):
            with QSignalBlocker(self.layers_list_widget):
                active = getattr(self, 'selected_typeset_area', None)
                for row_i in range(self.layers_list_widget.count()):
                    it = self.layers_list_widget.item(row_i)
                    if it is not None:
                        it.setSelected(it.data(Qt.UserRole) is active)
            self._sync_layer_inspector_from_selection()
            return

        self.layers_list_widget.blockSignals(True)
        self.layers_list_widget.clear()
        selected_item = None

        for idx, area in enumerate(list(getattr(self, 'typeset_areas', []) or [])):
            item = QListWidgetItem()
            item.setSizeHint(QSize(100, 68))
            item.setData(Qt.UserRole, area)

            custom_name = (getattr(area, 'layer_name', '') or '').strip()
            ocr_raw = " ".join((getattr(area, 'original_text', '') or '').split())
            tl_raw = " ".join((getattr(area, 'text', '') or '').split())
            is_manual = (not ocr_raw) or (ocr_raw == 'Manual Input')

            search_blob = f"#{idx + 1} {custom_name} {ocr_raw} {tl_raw}".lower()
            item.setData(Qt.UserRole + 1, search_blob)
            item.setToolTip(
                f"Layer #{idx + 1}" + (f" · {custom_name}" if custom_name else "")
                + f"\nOCR: {ocr_raw or '—'}\nTerjemahan: {tl_raw or '—'}"
            )
            self.layers_list_widget.addItem(item)

            w = QWidget()
            w.setMinimumWidth(0)
            card_v = QVBoxLayout(w)
            card_v.setContentsMargins(6, 4, 6, 4)
            card_v.setSpacing(2)

            # Row 1: index + custom name/manual tag + control buttons
            top_row = QHBoxLayout()
            top_row.setContentsMargins(0, 0, 0, 0)
            top_row.setSpacing(4)

            title_text = f"#{idx + 1}"
            if custom_name:
                title_text += f" · {self._compact_preview_line(custom_name, 16)}"
            elif is_manual:
                title_text += " · [Manual]"

            visible = getattr(area, 'visible', True)
            locked = getattr(area, 'locked', False)
            title_lbl = QLabel(title_text)
            title_lbl.setMinimumWidth(0)
            title_lbl.setStyleSheet(
                f"color: {theme.COLORS['accent'] if visible else theme.COLORS['muted']}; "
                "font-size: 8pt; font-weight: 700; background: transparent; border: none;"
            )
            top_row.addWidget(title_lbl, 1)

            eye_btn = QPushButton()
            eye_btn.setIcon(self._make_eye_icon(visible))
            eye_btn.setIconSize(QSize(14, 14))
            eye_btn.setFixedSize(22, 22)
            eye_btn.setMinimumWidth(0)
            eye_btn.setToolTip("Toggle Visibility")
            eye_btn.setStyleSheet(self._small_layer_button_qss(active=visible))
            eye_btn.clicked.connect(partial(self._toggle_layer_visibility, area, eye_btn))
            top_row.addWidget(eye_btn)

            lock_btn = QPushButton()
            lock_btn.setIcon(self._make_lock_icon(locked))
            lock_btn.setIconSize(QSize(14, 14))
            lock_btn.setFixedSize(22, 22)
            lock_btn.setMinimumWidth(0)
            lock_btn.setToolTip("Toggle Lock")
            lock_btn.setStyleSheet(self._small_layer_button_qss(danger=locked))
            lock_btn.clicked.connect(partial(self._toggle_layer_lock, area, lock_btn))
            top_row.addWidget(lock_btn)

            up_btn = QPushButton()
            up_btn.setIcon(app_icon("chevron-up", theme.COLORS['text'], size=11))
            up_btn.setIconSize(QSize(11, 11))
            up_btn.setFixedSize(20, 22)
            up_btn.setMinimumWidth(0)
            up_btn.setToolTip("Move Layer Up")
            up_btn.setStyleSheet(self._small_layer_button_qss())
            up_btn.clicked.connect(partial(self._move_layer_up, area))
            top_row.addWidget(up_btn)

            down_btn = QPushButton()
            down_btn.setIcon(app_icon("chevron-down", theme.COLORS['text'], size=11))
            down_btn.setIconSize(QSize(11, 11))
            down_btn.setFixedSize(20, 22)
            down_btn.setMinimumWidth(0)
            down_btn.setToolTip("Move Layer Down")
            down_btn.setStyleSheet(self._small_layer_button_qss())
            down_btn.clicked.connect(partial(self._move_layer_down, area))
            top_row.addWidget(down_btn)

            del_btn = QPushButton()
            del_btn.setIcon(self._make_trash_icon())
            del_btn.setIconSize(QSize(13, 13))
            del_btn.setFixedSize(22, 22)
            del_btn.setMinimumWidth(0)
            del_btn.setToolTip("Delete Layer")
            del_btn.setStyleSheet(self._small_layer_button_qss(danger=True))
            del_btn.clicked.connect(partial(self._delete_layer, area))
            top_row.addWidget(del_btn)
            card_v.addLayout(top_row)

            # Row 2: OCR & Translation preview lines
            ocr_disp = "— (Manual)" if is_manual else self._compact_preview_line(ocr_raw, 40)
            tl_disp = self._compact_preview_line(tl_raw, 40) if tl_raw else "(Kosong)"

            ocr_lbl = QLabel(f"OCR: {ocr_disp}")
            ocr_lbl.setMinimumWidth(0)
            ocr_lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            ocr_lbl.setStyleSheet(
                f"color: {theme.COLORS['muted']}; font-size: 8pt; background: transparent; border: none;"
            )
            card_v.addWidget(ocr_lbl)

            tl_lbl = QLabel(f"TL: {tl_disp}")
            tl_lbl.setMinimumWidth(0)
            tl_lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            tl_lbl.setStyleSheet(
                (
                    f"color: {theme.COLORS['text']}; font-size: 8.5pt; font-weight: 600;"
                    if visible else
                    f"color: {theme.COLORS['muted']}; font-size: 8.5pt; text-decoration: line-through;"
                )
                + " background: transparent; border: none;"
            )
            card_v.addWidget(tl_lbl)

            self.layers_list_widget.setItemWidget(item, w)
            if area is getattr(self, 'selected_typeset_area', None):
                item.setSelected(True)
                selected_item = item

        self.layers_list_widget.blockSignals(False)
        self._filter_layers_list()
        if selected_item is not None and not selected_item.isHidden():
            self.layers_list_widget.scrollToItem(selected_item)
        self._sync_layer_inspector_from_selection()

    def _filter_layers_list(self, _text=None):
        lst = getattr(self, 'layers_list_widget', None)
        search = getattr(self, 'layer_search_input', None)
        if lst is None:
            return
        query = (search.text() if search is not None else "").strip().lower()
        for row_i in range(lst.count()):
            item = lst.item(row_i)
            if item is None:
                continue
            if not query:
                item.setHidden(False)
            else:
                blob = str(item.data(Qt.UserRole + 1) or "")
                item.setHidden(query not in blob)

    def _sync_layer_inspector_from_selection(self):
        status_lbl = getattr(self, 'layer_inspector_status_label', None)
        ocr_edit = getattr(self, 'layer_ocr_edit', None)
        trans_edit = getattr(self, 'layer_trans_edit', None)
        apply_btn = getattr(self, 'layer_apply_text_btn', None)
        retrans_btn = getattr(self, 'layer_retranslate_btn', None)
        adv_btn = getattr(self, 'layer_advanced_edit_btn', None)
        dup_btn = getattr(self, 'layer_duplicate_btn', None)
        opacity_slider = getattr(self, 'layer_opacity_slider', None)
        opacity_lbl = getattr(self, 'layer_opacity_label', None)

        areas = getattr(self, 'typeset_areas', []) or []
        area = getattr(self, 'selected_typeset_area', None)
        valid = area is not None and area in areas

        if dup_btn is not None:
            dup_btn.setEnabled(valid)

        if not valid:
            if status_lbl is not None:
                status_lbl.setText(LayersText.INSPECTOR_EMPTY_HINT)
                status_lbl.setStyleSheet(f"color: {theme.COLORS['muted']}; font-size: 8pt;")
            for widget in (opacity_slider, ocr_edit, trans_edit, apply_btn, retrans_btn, adv_btn):
                if widget is not None:
                    widget.setEnabled(False)
            if ocr_edit is not None:
                with QSignalBlocker(ocr_edit):
                    ocr_edit.clear()
            if trans_edit is not None:
                with QSignalBlocker(trans_edit):
                    trans_edit.clear()
            if opacity_slider is not None:
                with QSignalBlocker(opacity_slider):
                    opacity_slider.setValue(100)
            if opacity_lbl is not None:
                opacity_lbl.setText("100%")
            return

        idx = areas.index(area)
        locked = bool(getattr(area, 'locked', False))
        custom_name = (getattr(area, 'layer_name', '') or '').strip()

        if status_lbl is not None:
            status_text = f"Layer #{idx + 1}"
            if custom_name:
                status_text += f" · {custom_name}"
            if locked:
                status_text += " · Terkunci (buka kunci untuk mengedit)"
            status_lbl.setText(status_text)
            status_lbl.setStyleSheet(
                f"color: {theme.COLORS['warning'] if locked else theme.COLORS['accent_hover']}; "
                "font-size: 8pt; font-weight: 600;"
            )

        if opacity_slider is not None:
            opacity_slider.setEnabled(True)
            opacity = int(getattr(area, 'opacity', 1.0) * 100)
            with QSignalBlocker(opacity_slider):
                opacity_slider.setValue(opacity)
            if opacity_lbl is not None:
                opacity_lbl.setText(f"{opacity}%")

        raw_ocr = getattr(area, 'original_text', '') or ''
        disp_ocr = '' if raw_ocr == 'Manual Input' else raw_ocr
        if ocr_edit is not None:
            ocr_edit.setEnabled(not locked)
            if not ocr_edit.hasFocus():
                with QSignalBlocker(ocr_edit):
                    ocr_edit.setPlainText(disp_ocr)

        if trans_edit is not None:
            trans_edit.setEnabled(not locked)
            if not trans_edit.hasFocus():
                with QSignalBlocker(trans_edit):
                    trans_edit.setPlainText(getattr(area, 'text', '') or '')

        for btn in (apply_btn, retrans_btn, adv_btn):
            if btn is not None:
                btn.setEnabled(not locked)

    def _apply_inspector_text_changes(self):
        area = getattr(self, 'selected_typeset_area', None)
        areas = getattr(self, 'typeset_areas', []) or []
        if area is None or area not in areas or getattr(area, 'locked', False):
            return

        ocr_edit = getattr(self, 'layer_ocr_edit', None)
        trans_edit = getattr(self, 'layer_trans_edit', None)
        new_ocr = ocr_edit.toPlainText().strip() if ocr_edit is not None else (getattr(area, 'original_text', '') or '')
        new_tl = trans_edit.toPlainText() if trans_edit is not None else (getattr(area, 'text', '') or '')
        final_ocr = new_ocr or "Manual Input"

        if (final_ocr == (getattr(area, 'original_text', '') or "Manual Input")) and (new_tl == (getattr(area, 'text', '') or '')):
            return

        self._push_undo_snapshot("Edit Layer Text")
        area.original_text = final_ocr
        area.update_plain_text(new_tl)

        hist_id = getattr(area, 'history_id', None)
        if hist_id:
            for entry in getattr(self, 'history_entries', []) or []:
                if entry.get('history_id') == hist_id or entry.get('id') == hist_id:
                    entry['original_text'] = area.original_text
                    entry['translated_text'] = area.text
                    break

        try:
            self.redo_stack.clear()
        except Exception:
            pass

        if getattr(self, 'current_image_path', None):
            key = self.get_current_data_key()
            if key:
                self._update_typeset_record(key, areas=list(self.typeset_areas), redo=list(self.redo_stack))

        self.redraw_all_typeset_areas(refresh_layers=True)
        if hasattr(self, 'update_undo_redo_buttons_state'):
            self.update_undo_redo_buttons_state()
        if hasattr(self, 'statusBar') and self.statusBar() is not None:
            self.statusBar().showMessage("Teks layer diperbarui.", 2500)

    def _retranslate_selected_layer_from_ocr(self):
        area = getattr(self, 'selected_typeset_area', None)
        areas = getattr(self, 'typeset_areas', []) or []
        if area is None or area not in areas or getattr(area, 'locked', False):
            return

        ocr_edit = getattr(self, 'layer_ocr_edit', None)
        src_text = (ocr_edit.toPlainText().strip() if ocr_edit is not None else (getattr(area, 'original_text', '') or '').strip())
        if not src_text or src_text == "Manual Input":
            if hasattr(self, 'show_toast'):
                self.show_toast("Teks OCR Kosong", "Isi Teks Asli (OCR) terlebih dahulu sebelum menerjemahkan ulang.", kind="warning")
            return

        model_sel = self.get_selected_model_name() if hasattr(self, 'get_selected_model_name') else (None, None)
        if isinstance(model_sel, tuple) and len(model_sel) >= 2:
            provider, model_name = model_sel[0], model_sel[1]
        else:
            provider, model_name = None, model_sel
        if not model_name:
            if hasattr(self, 'show_banner'):
                self.show_banner("layer-retranslate-no-model", "No model", "Pilih model AI Translate terlebih dahulu.", kind="warning")
            return

        btn = getattr(self, 'layer_retranslate_btn', None)
        if btn is not None:
            btn.setEnabled(False)
            btn.setText(LayersText.BTN_RETRANSLATING)
            QApplication.processEvents()

        try:
            settings = self.get_current_settings() if hasattr(self, 'get_current_settings') else {}
            target_lang = settings.get('target_lang', 'Indonesian')
            if provider:
                translated = self.translate_with_ai(src_text, target_lang, provider, model_name, settings)
            else:
                translated = self.translate_text(src_text, target_lang)

            tr_str = str(translated or "").strip()
            upper_tr = tr_str.upper()
            is_err = (
                not tr_str
                or (tr_str.startswith("[") and any(tok in upper_tr for tok in ("ERROR", "FAILED", "NOT CONFIGURED")))
            )
            if is_err:
                if hasattr(self, 'show_banner'):
                    self.show_banner("layer-retranslate-error", "Terjemahan gagal", tr_str or "AI tidak mengembalikan hasil.", kind="error")
                return

            if getattr(self, 'layer_trans_edit', None) is not None:
                with QSignalBlocker(self.layer_trans_edit):
                    self.layer_trans_edit.setPlainText(tr_str)
            self._apply_inspector_text_changes()
        except Exception as exc:
            if hasattr(self, 'show_banner'):
                self.show_banner("layer-retranslate-error", "Terjemahan gagal", str(exc), kind="error")
        finally:
            if btn is not None:
                btn.setEnabled(not bool(getattr(area, 'locked', False)))
                btn.setText(LayersText.BTN_RETRANSLATE)

    def _on_layer_item_double_clicked(self, item):
        if not item:
            return
        area = item.data(Qt.UserRole)
        if area is not None and hasattr(self, 'start_inline_edit'):
            self.start_inline_edit(area)

    def _toggle_layer_visibility(self, area, btn):
        area.visible = not getattr(area, 'visible', True)
        self.redraw_all_typeset_areas()
        if hasattr(self, 'image_label') and self.image_label is not None:
            self.image_label.update()
        self._refresh_layers_list()

    def _toggle_layer_lock(self, area, btn):
        area.locked = not getattr(area, 'locked', False)
        if hasattr(self, 'image_label') and self.image_label is not None:
            self.image_label.update()
        self._refresh_layers_list()

    def _on_layer_selection_changed(self):
        selected_items = self.layers_list_widget.selectedItems()
        if selected_items:
            area = selected_items[0].data(Qt.UserRole)
            self._in_layer_list_selection = True
            try:
                self.set_selected_area(area)
            finally:
                self._in_layer_list_selection = False

    def _move_layer_up(self, area):
        if area in self.typeset_areas:
            idx = self.typeset_areas.index(area)
            if idx > 0:
                self.typeset_areas.remove(area)
                self.typeset_areas.insert(idx - 1, area)
                if getattr(self, 'current_image_path', None):
                    key = self.get_current_data_key()
                    if key:
                        self._update_typeset_record(key, areas=list(self.typeset_areas), redo=list(self.redo_stack))
                self.redraw_all_typeset_areas()
                self._refresh_layers_list()

    def _move_layer_down(self, area):
        if area in self.typeset_areas:
            idx = self.typeset_areas.index(area)
            if idx < len(self.typeset_areas) - 1:
                self.typeset_areas.remove(area)
                self.typeset_areas.insert(idx + 1, area)
                if getattr(self, 'current_image_path', None):
                    key = self.get_current_data_key()
                    if key:
                        self._update_typeset_record(key, areas=list(self.typeset_areas), redo=list(self.redo_stack))
                self.redraw_all_typeset_areas()
                self._refresh_layers_list()

    def _delete_layer(self, area):
        self.delete_typeset_area(area)
        self._refresh_layers_list()

    def _add_new_manual_layer(self):
        if getattr(self, 'ocr_lang_combo', None) is not None:
            self.ocr_lang_combo.setCurrentText("Manual Text (Rect)")
        from src.ui.canvas import TypesetArea
        rect = QRect(100, 100, 200, 80)
        font = self._build_current_font()
        color = self.typeset_color if hasattr(self, 'typeset_color') and self.typeset_color else QColor("#000000")
        new_area = TypesetArea(rect, "SFX Text", font, color, original_text="Manual Input")
        self._push_undo_snapshot("New Layer")
        self.typeset_areas.append(new_area)
        if getattr(self, 'current_image_path', None):
            key = self.get_current_data_key()
            if key:
                self._update_typeset_record(key, areas=list(self.typeset_areas), redo=list(self.redo_stack))
        self.set_selected_area(new_area)
        self.redraw_all_typeset_areas()
        self._refresh_layers_list()

    def _duplicate_selected_layer(self):
        area = getattr(self, 'selected_typeset_area', None)
        areas = getattr(self, 'typeset_areas', []) or []
        if area is None or area not in areas:
            return
        from src.ui.canvas import TypesetArea
        new_area = TypesetArea.from_payload(area.to_payload())
        new_rect = new_area.rect.translated(20, 20)
        pix = getattr(self, 'original_pixmap', None)
        if pix is not None:
            w, h = pix.width(), pix.height()
            if new_rect.left() > w or new_rect.top() > h:
                new_rect.moveTo(20, 20)
            if new_rect.right() > w:
                new_rect.setWidth(max(10, w - new_rect.x()))
            if new_rect.bottom() > h:
                new_rect.setHeight(max(10, h - new_rect.y()))
        dx = int(round(new_rect.x() - new_area.rect.x()))
        dy = int(round(new_rect.y() - new_area.rect.y()))
        new_area.rect = new_rect
        for poly_attr in ('polygon', 'cleanup_rect', 'cleanup_polygon'):
            geom = getattr(new_area, poly_attr, None)
            if geom is not None:
                geom.translate(dx, dy)
        new_area.history_id = None
        if getattr(new_area, 'layer_name', ''):
            new_area.layer_name = f"{new_area.layer_name} Copy"

        self._push_undo_snapshot("Duplicate Layer")
        self.typeset_areas.append(new_area)
        if getattr(self, 'current_image_path', None):
            key = self.get_current_data_key()
            if key:
                self._update_typeset_record(key, areas=list(self.typeset_areas), redo=list(self.redo_stack))
        self.set_selected_area(new_area)
        self.redraw_all_typeset_areas()
        self._refresh_layers_list()
        if hasattr(self, 'update_undo_redo_buttons_state'):
            self.update_undo_redo_buttons_state()

    def _clear_all_layers(self):
        reply = QMessageBox.question(
            self, "Clear All Layers",
            "Are you sure you want to delete all text/typeset layers for this image?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._push_undo_snapshot("Clear All Areas")
            self.typeset_areas.clear()
            self.clear_selected_area()
            key, record = self._current_inpaint_record() if hasattr(self, '_current_inpaint_record') else (None, {})
            has_inpaint = self._has_inpaint_state(key, record) if hasattr(self, '_has_inpaint_state') else False
            if key and has_inpaint:
                pre_img = self._resolve_pre_inpaint_image(key, record)
                if pre_img is not None:
                    self._apply_base_image(pre_img)
                self._update_typeset_record(
                    key,
                    areas=[],
                    redo=list(self.redo_stack),
                    remove_cleaned_image=True,
                    remove_pre_inpaint_image=True,
                )
                self._refresh_inpaint_result_controls()
            elif key:
                self._update_typeset_record(key, areas=[], redo=list(self.redo_stack))
            self.redraw_all_typeset_areas()
            self._refresh_layers_list()
            self.update_undo_redo_buttons_state()

    def _show_layer_context_menu(self, pos):
        item = self.layers_list_widget.itemAt(pos)
        if not item:
            return
        area = item.data(Qt.UserRole)
        if not area:
            return

        menu = QMenu(self)
        rename_action = QAction("Rename Layer", self)
        rename_action.triggered.connect(partial(self._rename_layer, area))
        menu.addAction(rename_action)

        dup_action = QAction(LayersText.BTN_DUPLICATE_LAYER, self)
        dup_action.setIcon(app_icon("copy", theme.COLORS['text'], size=14))
        dup_action.triggered.connect(lambda: (self.set_selected_area(area), self._duplicate_selected_layer()))
        menu.addAction(dup_action)

        restore_inpaint_action = QAction(FullPageBatchText.LAYER_RESTORE_INPAINT_ACTION, self)
        restore_inpaint_action.setIcon(app_icon("undo", theme.COLORS['text'], size=14))
        restore_inpaint_action.triggered.connect(partial(self.restore_selected_area_inpaint, area))
        menu.addAction(restore_inpaint_action)

        opacity_menu = menu.addMenu("Set Opacity")
        for val in (100, 75, 50, 25, 0):
            act = QAction(f"{val}%", self)
            act.triggered.connect(partial(self._set_layer_opacity_direct, area, val))
            opacity_menu.addAction(act)

        menu.exec_(self.layers_list_widget.mapToGlobal(pos))

    def _rename_layer(self, area):
        current_name = getattr(area, 'layer_name', '')
        if not current_name:
            current_name = (area.text or "")[:20]
        new_name, ok = QInputDialog.getText(self, "Rename Layer", "Enter custom layer name:", text=current_name)
        if ok and new_name.strip():
            area.layer_name = new_name.strip()
            self._refresh_layers_list()

    def _set_layer_opacity_direct(self, area, val):
        area.opacity = val / 100.0
        if area is getattr(self, 'selected_typeset_area', None):
            slider = getattr(self, 'layer_opacity_slider', None)
            if slider is not None:
                with QSignalBlocker(slider):
                    slider.setValue(val)
            lbl = getattr(self, 'layer_opacity_label', None)
            if lbl is not None:
                lbl.setText(f"{val}%")
        self.redraw_all_typeset_areas(refresh_layers=False)
