"""Method domain uibuild, dipindahkan utuh dari main_window.py.

Fase 1 pemecahan monolit: isi method tidak diubah sama sekali.
Mixin ini hanya berguna sebagai bagian dari MangaOCRApp -- ia mengandalkan
atribut yang dibuat di MangaOCRApp.__init__.
"""

from src.ui.main_window_mixins._imports import *  # noqa: F401,F403


class UibuildMixin:
    def setup_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu('&File')
        self.save_project_action = QAction('Save Project', self)
        self.save_project_action.triggered.connect(self.save_project)
        file_menu.addAction(self.save_project_action)
        self.load_project_action = QAction('Load Project', self)
        self.load_project_action.triggered.connect(self.load_project)
        file_menu.addAction(self.load_project_action)

        # --- Recent Projects submenu ---
        self.recent_projects_menu = QMenu('Recent Projects', self)
        file_menu.addMenu(self.recent_projects_menu)
        self._rebuild_recent_projects_menu()

        self._action_shortcut_map.update({
            'save_project': self.save_project_action,
            'load_project': self.load_project_action,
        })

        file_menu.addSeparator()
        batch_save_action = QAction('Batch Save...', self)
        batch_save_action.triggered.connect(self.open_batch_save_dialog)
        file_menu.addAction(batch_save_action)
        export_pdf_action = QAction('Export Typeset to PDF...', self)
        export_pdf_action.triggered.connect(self.export_to_pdf)
        file_menu.addAction(export_pdf_action)
        export_cbz_action = QAction('Export Typeset to CBZ...', self)
        export_cbz_action.triggered.connect(self.export_to_cbz)
        file_menu.addAction(export_cbz_action)

        view_menu = menu_bar.addMenu('&View')
        toggle_theme_action = QAction('Toggle Light/Dark Mode', self); toggle_theme_action.triggered.connect(self.toggle_theme); view_menu.addAction(toggle_theme_action)
        view_menu.addSeparator()
        self.toggle_folder_action = QAction('Toggle Folder Panel', self)
        self.toggle_folder_action.setShortcut(QKeySequence("F3"))
        self.toggle_folder_action.triggered.connect(self.toggle_left_panel)
        view_menu.addAction(self.toggle_folder_action)
        self.toggle_tools_action = QAction('Toggle Tools Panel', self)
        self.toggle_tools_action.setShortcut(QKeySequence("F4"))
        self.toggle_tools_action.triggered.connect(self.toggle_right_panel)
        view_menu.addAction(self.toggle_tools_action)
        self.toggle_focus_action = QAction(NavText.FOCUS_MODE_ACTION, self)
        self.toggle_focus_action.setShortcut(QKeySequence("F2"))
        self.toggle_focus_action.triggered.connect(self.toggle_focus_mode)
        view_menu.addAction(self.toggle_focus_action)
        
        filter_menu = menu_bar.addMenu('&Filter')
        curves_action = QAction('Curves Adjustment...', self)
        curves_action.triggered.connect(self.open_image_curves_dialog)
        filter_menu.addAction(curves_action)

        # --- Edit menu ---
        edit_menu = menu_bar.addMenu('&Edit')
        find_replace_action = QAction('Find && Replace...', self)
        find_replace_action.setShortcut(QKeySequence("Ctrl+H"))
        find_replace_action.triggered.connect(self.open_find_replace_dialog)
        edit_menu.addAction(find_replace_action)

        chapter_proofread_action = QAction('Chapter Proofread && QC...', self)
        chapter_proofread_action.setShortcut(QKeySequence("Ctrl+Shift+P"))
        chapter_proofread_action.triggered.connect(self.open_chapter_proofread_dialog)
        edit_menu.addAction(chapter_proofread_action)

        detect_bubbles_action = QAction('Detect Bubbles on Page', self)
        detect_bubbles_action.setToolTip("Run interactive manual bubble detection on the current page")
        detect_bubbles_action.triggered.connect(self.start_interactive_batch_detection)
        edit_menu.addAction(detect_bubbles_action)

        self.use_box_action = None
        settings_center_action = QAction('Settings', self)
        settings_center_action.triggered.connect(lambda: self.open_settings_dialog('general'))
        menu_bar.addAction(settings_center_action)

        # Legacy individual dialogs (tersembunyi, bisa dipakai dari kode)
        project_stats_action = QAction('Project Statistics...', self)
        project_stats_action.triggered.connect(self.show_project_stats_dialog)
        session_analytics_action = QAction('Session Analytics...', self)
        session_analytics_action.triggered.connect(self.show_session_analytics_dialog)

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.setup_menu_bar()
        self.setStatusBar(QStatusBar(self))
        self.statusBar().addPermanentWidget(QProgressBar())
        self.overall_progress_bar = self.statusBar().findChild(QProgressBar)
        self.overall_progress_bar.setVisible(False)
        self.overall_progress_bar.setMaximumWidth(200)

        # Main splitter for resizable panels
        self.splitter = QSplitter(Qt.Horizontal)

        # Left Panel (File List)
        self.left_panel_widget = QWidget()
        self.left_panel_widget.setMinimumWidth(240)
        self.left_panel_layout = QVBoxLayout(self.left_panel_widget)
        self.left_panel_layout.setContentsMargins(10, 10, 10, 10)
        self.left_panel_layout.addWidget(QLabel("<h3>Image Files</h3>", objectName="h3"))
        self.chapter_progress_label = QLabel("No folder loaded")
        self.chapter_progress_label.setObjectName("rp-tiny-label")
        self.chapter_progress_label.setWordWrap(True)
        self.left_panel_layout.addWidget(self.chapter_progress_label)
        self.file_list_widget = QListWidget()
        self.file_list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_list_widget.currentItemChanged.connect(self.on_file_selected)
        self.left_panel_layout.addWidget(self.file_list_widget)
        self.chapter_qc_button = QPushButton("Proofread / QC Chapter")
        self.chapter_qc_button.setIcon(app_icon("check", theme.COLORS["accent"], 14))
        self.chapter_qc_button.setToolTip("Review and edit all OCR & translated bubbles across the entire chapter sequentially (Ctrl+Shift+P).")
        self.chapter_qc_button.clicked.connect(self.open_chapter_proofread_dialog)
        self.left_panel_layout.addWidget(self.chapter_qc_button)
        load_folder_button = QPushButton("Load Folder")
        load_folder_button.clicked.connect(self.load_folder)
        self.left_panel_layout.addWidget(load_folder_button)
        self.splitter.addWidget(self.left_panel_widget)

        # Center Panel (Image Viewer)
        center_panel_widget = QWidget()
        self.center_panel_widget = center_panel_widget
        center_layout = QVBoxLayout(center_panel_widget)
        center_layout.setContentsMargins(0,10,0,0)
        center_layout.setSpacing(5)
        self.image_canvas_widget = QWidget()
        self.image_canvas_widget.setMinimumSize(0, 0)
        self.image_canvas_widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.image_label = SelectableImageLabel(self)
        self.image_label.setParent(self.image_canvas_widget)
        self.image_label.move(0, 0)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(0, 0)
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.image_label.areaDoubleClicked.connect(self.start_inline_edit)
        self.image_scroll = QScrollArea()
        self.image_scroll.setWidgetResizable(False)
        self.image_scroll.setFrameShape(QFrame.NoFrame)
        self.image_scroll.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)
        self.image_scroll.setMinimumSize(0, 0)
        self.image_scroll.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.image_scroll.setWidget(self.image_canvas_widget)

        # --- Welcome / Start Screen (Fitur #19) ---
        self.welcome_widget = self._build_welcome_widget()

        # QStackedWidget: index 0 = welcome screen, index 1 = canvas
        self.center_stack = QStackedWidget()
        self.center_stack.setMinimumSize(0, 0)
        self.center_stack.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.center_stack.addWidget(self.welcome_widget)
        self.center_stack.addWidget(self.image_scroll)
        self.center_stack.setCurrentIndex(0)  # Mulai di welcome screen
        center_layout.addWidget(self.center_stack)

        # Navigation and Zoom Controls
        self.nav_zoom_widget = QWidget()
        nav_zoom_layout = QHBoxLayout(self.nav_zoom_widget)
        nav_zoom_layout.setContentsMargins(10, 5, 10, 5)
        
        # Premium toggle Folder btn
        self.toggle_left_btn = QPushButton(NavText.HIDE_FOLDER)
        self.toggle_left_btn.setToolTip("Toggle Left folder list panel (F3)")
        self.toggle_left_btn.setCheckable(True)
        self.toggle_left_btn.setChecked(True)
        self.toggle_left_btn.clicked.connect(self.toggle_left_panel)
        self.toggle_left_btn.setStyleSheet(toggle_button_qss())
        nav_zoom_layout.addWidget(self.toggle_left_btn)
        
        self.prev_button = QPushButton("<< Prev")
        self.prev_button.clicked.connect(self.load_prev_image)
        nav_zoom_layout.addWidget(self.prev_button)
        nav_zoom_layout.addStretch()
        
        self.zoom_out_button = QPushButton("Zoom Out (-)"); self.zoom_out_button.clicked.connect(self.zoom_out)
        self.zoom_label = QLabel(f" Zoom: {self.zoom_factor:.1f}x ")
        self.zoom_in_button = QPushButton("Zoom In (+)"); self.zoom_in_button.clicked.connect(self.zoom_in)
        nav_zoom_layout.addWidget(self.zoom_out_button); nav_zoom_layout.addWidget(self.zoom_label); nav_zoom_layout.addWidget(self.zoom_in_button)
        nav_zoom_layout.addStretch()
        
        # Premium Focus Mode btn
        self.focus_mode_btn = QPushButton(NavText.FOCUS_MODE)
        self.focus_mode_btn.setToolTip("Toggle Canvas Only view (F2)")
        self.focus_mode_btn.clicked.connect(self.toggle_focus_mode)
        self.focus_mode_btn.setStyleSheet(compact_primary_button_qss())
        nav_zoom_layout.addWidget(self.focus_mode_btn)

        # Quick Compare toggle button
        self.compare_mode_btn = QPushButton(NavText.COMPARE_MODE)
        self.compare_mode_btn.setIcon(app_icon("eye", theme.COLORS["text"], size=14, active_color=theme.COLORS["accent"]))
        self.compare_mode_btn.setIconSize(QSize(14, 14))
        self.compare_mode_btn.setToolTip("Tahan untuk lihat gambar asli tanpa typeset overlay (Quick Compare)")
        self.compare_mode_btn.setCheckable(True)
        self.compare_mode_btn.toggled.connect(self._on_compare_mode_toggled)
        self.compare_mode_btn.setStyleSheet(toggle_button_qss())
        nav_zoom_layout.addWidget(self.compare_mode_btn)
        
        self.next_button = QPushButton("Next >>")
        self.next_button.clicked.connect(self.on_next_clicked)
        nav_zoom_layout.addWidget(self.next_button)
        
        # Premium toggle Tools btn
        self.toggle_right_btn = QPushButton(NavText.HIDE_TOOLS)
        self.toggle_right_btn.setToolTip(WorkspaceText.RIGHT_PANEL_TOGGLE_TOOLTIP)
        self.toggle_right_btn.setCheckable(True)
        self.toggle_right_btn.setChecked(True)
        self.toggle_right_btn.clicked.connect(self.toggle_right_panel)
        self.toggle_right_btn.setStyleSheet(toggle_button_qss())
        nav_zoom_layout.addWidget(self.toggle_right_btn)
        
        center_layout.addWidget(self.nav_zoom_widget)
        self.splitter.addWidget(center_panel_widget)

        # Right Panel (Controls)
        right_panel_layout = self.setup_right_panel()
        right_panel_content = QWidget()
        right_panel_content.setObjectName("right-panel")
        right_panel_content.setMinimumSize(0, 0)
        right_panel_content.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        right_panel_content.setLayout(right_panel_layout)

        self.right_panel_scroll = QScrollArea()
        self.right_panel_scroll.setObjectName("right-panel-scroll")
        self.right_panel_scroll.setWidgetResizable(True)
        self.right_panel_scroll.setFrameShape(QFrame.NoFrame)
        self.right_panel_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.right_panel_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.right_panel_scroll.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)
        self.right_panel_scroll.setMinimumWidth(380)
        self.right_panel_scroll.setMinimumHeight(0)
        self.right_panel_scroll.setMaximumWidth(600)
        self.right_panel_scroll.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)
        self.right_panel_scroll.setWidget(right_panel_content)
        self.splitter.addWidget(self.right_panel_scroll)

        # Make splitter adaptive across screen sizes
        self.splitter.setChildrenCollapsible(True)
        self.splitter.setHandleWidth(6)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(2, 0)

        # Load saved splitter sizes if present
        self.splitter.setSizes(self._normalized_workspace_splitter_sizes(SETTINGS.get('splitter_sizes')))
        self._update_center_panel_constraints()

        main_layout.addWidget(self.splitter)
        self._apply_right_panel_styles()
        self._refresh_workspace_surface_theme()

    def setup_right_panel(self):
        """Modern icon-sidebar + stacked-widget layout untuk Tools & Workspace panel."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Header bar ──────────────────────────────────────────────────────────
        header_bar = QWidget()
        header_bar.setObjectName("rp-header-bar")
        header_bar.setFixedHeight(46)
        header_h = QHBoxLayout(header_bar)
        header_h.setContentsMargins(14, 0, 14, 0)
        header_h.setSpacing(8)

        header_icon = icon_label("zap", theme.COLORS['accent'], size=16)
        header_h.addWidget(header_icon)

        header = QLabel(WorkspaceText.RIGHT_PANEL_TITLE)
        header.setObjectName("panel-title")
        header_h.addWidget(header)
        header_h.addStretch()
        main_layout.addWidget(header_bar)

        # ── Separator ────────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("rp-sep")
        main_layout.addWidget(sep)

        # ── Body: icon sidebar (left) + stacked content (right) ─────────────────
        body_widget = QWidget()
        body_widget.setMinimumWidth(0)
        body_widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        body_h = QHBoxLayout(body_widget)
        body_h.setContentsMargins(0, 0, 0, 0)
        body_h.setSpacing(0)

        # ── Icon sidebar ─────────────────────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setObjectName("rp-sidebar")
        sidebar.setFixedWidth(70)
        sidebar_v = QVBoxLayout(sidebar)
        sidebar_v.setContentsMargins(4, 8, 4, 8)
        sidebar_v.setSpacing(2)

        # Build chat widget first
        try:
            from src.ui.chat_widget import AIChatWidget
            self._chat_widget = AIChatWidget(main_app=self, parent=None)
        except Exception as _chat_err:
            print(f"[ChatWidget] Failed to load: {_chat_err}")
            self._chat_widget = None

        # Tab definitions: (label_short, icon_name, tooltip, widget_builder)
        tab_defs = [
            ("OCR",      "scan",     "AI OCR & translation target",   self._create_translate_tab),
            ("Full",     "rocket",   "Full-page auto translation",    self._create_full_translate_tab),
            ("Typeset",  "type",     "Typography & text styling",     self._create_typeset_tab),
            ("Layers",   "layers",   "Canvas layer manager",          self._create_layers_tab),
            ("Cleanup",  "eraser",   "Background box & area cleanup", self._create_cleanup_tab),
            ("AI Cfg",   "cpu",      "AI models & custom styles",     self._create_ai_hardware_tab),
        ]
        if self._chat_widget is not None:
            # Insert chat after OCR
            tab_defs.insert(1, ("Chat", "message", "AI Chat & Assistant", None))

        # QStackedWidget as content area
        self.right_stack = QStackedWidget()
        self.right_stack.setObjectName("rp-stack")
        self.right_stack.setMinimumSize(0, 0)
        self.right_stack.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        # Compatibility alias so code referencing self.tabs still works for tab switching
        class _TabShim:
            """Shim so legacy `self.tabs.setCurrentIndex(n)` / `setCurrentWidget(w)` calls work cleanly."""
            def __init__(self, stack, page_map):
                self._stack = stack
                self._page_map = page_map
            def _sync_sidebar(self, idx):
                for p_idx, btn in self._page_map.items():
                    btn.setChecked(p_idx == idx)
            def setCurrentIndex(self, i):
                self._stack.setCurrentIndex(i)
                self._sync_sidebar(i)
            def setCurrentWidget(self, w):
                idx = self._stack.indexOf(w)
                if idx >= 0:
                    self._stack.setCurrentIndex(idx)
                    self._sync_sidebar(idx)
            def currentIndex(self):
                return self._stack.currentIndex()
            def currentWidget(self):
                return self._stack.currentWidget()
            def indexOf(self, w):
                return self._stack.indexOf(w)
            def addTab(self, w, label):
                self._stack.addWidget(w)
            def tabBar(self):
                class _FakeBar:
                    def setExpanding(self, v): pass
                    def setUsesScrollButtons(self, v): pass
                    def setElideMode(self, v): pass
                    def setToolTip(self, v): pass
                return _FakeBar()
            def setStyleSheet(self, s): pass
            def setDocumentMode(self, v): pass
            def setMovable(self, v): pass

        self._sidebar_buttons = []
        self._stack_page_map = {}  # page_index -> btn
        self.tabs = _TabShim(self.right_stack, self._stack_page_map)

        def _make_sidebar_btn(icon_name, label, tip, page_idx):
            btn = QToolButton()
            btn.setObjectName("rp-nav-btn")
            btn.setText(label)
            btn.setIcon(app_icon(icon_name, theme.COLORS["muted"], 20, active_color=theme.COLORS["accent"]))
            btn.setIconSize(QSize(20, 20))
            btn.setToolTip(tip)
            btn.setCheckable(True)
            btn.setFixedSize(60, 56)
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            btn.setProperty("page", page_idx)
            btn.setProperty("icon_name", icon_name)
            btn.clicked.connect(lambda checked, idx=page_idx: self._on_sidebar_nav(idx))
            sidebar_v.addWidget(btn)
            self._sidebar_buttons.append(btn)
            self._stack_page_map[page_idx] = btn
            return btn

        page_idx = 0
        for short_label, marker, tip, builder in tab_defs:
            if builder is None:
                # Chat widget — already built
                widget = self._chat_widget
                page = widget
                if page is not None:
                    page.setMinimumWidth(0)
                    page.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
            else:
                widget = builder()
                if isinstance(widget, QScrollArea):
                    page = self._configure_workspace_scroll_area(widget)
                else:
                    scroll = QScrollArea()
                    scroll.setWidgetResizable(True)
                    scroll.setFrameShape(QFrame.NoFrame)
                    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                    scroll.setWidget(widget)
                    page = self._configure_workspace_scroll_area(scroll)

            try:
                page.setMinimumSize(0, 0)
                page.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
            except Exception:
                pass
            self.right_stack.addWidget(page)
            _make_sidebar_btn(marker, short_label, tip, page_idx)
            page_idx += 1

        sidebar_v.addStretch()
        body_h.addWidget(sidebar)

        # ── Vertical separator ───────────────────────────────────────────────────
        vsep = QFrame()
        vsep.setFrameShape(QFrame.VLine)
        vsep.setObjectName("rp-vsep")
        body_h.addWidget(vsep)

        # ── Content area ─────────────────────────────────────────────────────────
        body_h.addWidget(self.right_stack, 1)

        main_layout.addWidget(body_widget, 1)

        # ── Bottom status & actions bar ──────────────────────────────────────────
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setObjectName("rp-sep")
        main_layout.addWidget(sep2)

        bottom_bar = QWidget()
        bottom_bar.setObjectName("rp-bottom-bar")
        bottom_bar.setMinimumWidth(0)
        bottom_v = QVBoxLayout(bottom_bar)
        bottom_v.setContentsMargins(8, 8, 8, 8)
        bottom_v.setSpacing(6)

        # Kept None so legacy guards stay safe while redundant Batch Now / Detect All buttons are retired.
        self.process_batch_button = None
        self.batch_process_button = None

        # ── Confirm/Cancel detection (hidden unless manual detection active) ─
        detect_row = QHBoxLayout()
        detect_row.setSpacing(6)
        self.confirm_items_button = QPushButton("Confirm (0)")
        self.confirm_items_button.setObjectName("rp-confirm-btn")
        self.confirm_items_button.setMinimumWidth(0)
        self.confirm_items_button.setIcon(app_icon("check", theme.COLORS["success"], 14))
        self.confirm_items_button.setIconSize(QSize(14, 14))
        self.confirm_items_button.clicked.connect(self.process_confirmed_detections)
        self.confirm_items_button.setVisible(False)
        detect_row.addWidget(self.confirm_items_button, 1)
        self.cancel_detection_button = QPushButton("Cancel")
        self.cancel_detection_button.setObjectName("rp-danger-btn")
        self.cancel_detection_button.setMinimumWidth(0)
        self.cancel_detection_button.setIcon(app_icon("x", theme.COLORS["danger"], 14))
        self.cancel_detection_button.setIconSize(QSize(14, 14))
        self.cancel_detection_button.clicked.connect(self.cancel_interactive_batch)
        self.cancel_detection_button.setVisible(False)
        detect_row.addWidget(self.cancel_detection_button, 1)
        bottom_v.addLayout(detect_row)

        # ── Edit action row ─────────────────────────────────────────────────────
        edit_row = QHBoxLayout()
        edit_row.setSpacing(5)
        self.undo_button = QPushButton("Undo")
        self.undo_button.setObjectName("rp-action-btn")
        self.undo_button.setMinimumWidth(0)
        self.undo_button.setIcon(app_icon("undo", theme.COLORS["text"], 14))
        self.undo_button.setIconSize(QSize(14, 14))
        self.undo_button.clicked.connect(self.undo_last_action)
        self.undo_button.setEnabled(False)
        edit_row.addWidget(self.undo_button, 1)

        self.redo_button = QPushButton("Redo")
        self.redo_button.setObjectName("rp-action-btn")
        self.redo_button.setMinimumWidth(0)
        self.redo_button.setIcon(app_icon("redo", theme.COLORS["text"], 14))
        self.redo_button.setIconSize(QSize(14, 14))
        self.redo_button.clicked.connect(self.redo_last_action)
        self.redo_button.setEnabled(False)
        edit_row.addWidget(self.redo_button, 1)

        self.reset_button = QPushButton("Reset")
        self.reset_button.setObjectName("rp-action-btn")
        self.reset_button.setMinimumWidth(0)
        self.reset_button.setIcon(app_icon("refresh", theme.COLORS["text"], 14))
        self.reset_button.setIconSize(QSize(14, 14))
        self.reset_button.clicked.connect(self.reset_view_to_original)
        edit_row.addWidget(self.reset_button, 1)

        self.save_button = QPushButton("Save")
        self.save_button.setObjectName("rp-save-btn")
        self.save_button.setMinimumWidth(0)
        self.save_button.setIcon(app_icon("save", theme.COLORS["bg"], 14))
        self.save_button.setIconSize(QSize(14, 14))
        self.save_button.clicked.connect(self.save_image)
        edit_row.addWidget(self.save_button, 1)
        bottom_v.addLayout(edit_row)

        # ── Undo History Timeline + Status metrics + Token rates (kept alive off-layout so bottom bar stays clean) ──
        self._bottom_telemetry_container = QWidget(bottom_bar)
        self._bottom_telemetry_container.setVisible(False)
        telemetry_v = QVBoxLayout(self._bottom_telemetry_container)
        telemetry_v.setContentsMargins(0, 0, 0, 0)
        telemetry_v.setSpacing(4)

        timeline_header = QHBoxLayout()
        timeline_header.setContentsMargins(2, 4, 2, 0)
        timeline_header.setSpacing(4)
        timeline_header.addWidget(icon_label("clock", theme.COLORS["muted"], 12))
        timeline_title_lbl = QLabel("History")
        timeline_title_lbl.setObjectName("rp-tiny-label")
        timeline_header.addWidget(timeline_title_lbl)
        timeline_header.addStretch(1)
        self._timeline_clear_btn = QPushButton()
        self._timeline_clear_btn.setObjectName("rp-action-btn")
        self._timeline_clear_btn.setIcon(app_icon("x", theme.COLORS["muted"], 10))
        self._timeline_clear_btn.setIconSize(QSize(10, 10))
        self._timeline_clear_btn.setFixedSize(18, 18)
        self._timeline_clear_btn.setToolTip("Clear undo history")
        self._timeline_clear_btn.clicked.connect(self._clear_undo_history)
        timeline_header.addWidget(self._timeline_clear_btn)
        telemetry_v.addLayout(timeline_header)

        self.undo_timeline_list = QListWidget()
        self.undo_timeline_list.setObjectName("undo-timeline")
        self.undo_timeline_list.setFixedHeight(110)
        self.undo_timeline_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.undo_timeline_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.undo_timeline_list.setStyleSheet(self._undo_timeline_qss())
        self.undo_timeline_list.itemClicked.connect(self._on_timeline_item_clicked)
        telemetry_v.addWidget(self.undo_timeline_list)

        metrics_widget = QWidget()
        metrics_widget.setObjectName("rp-metrics")
        metrics_widget.setMinimumWidth(0)
        metrics_widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        metrics_grid = QGridLayout(metrics_widget)
        metrics_grid.setContentsMargins(6, 5, 6, 5)
        metrics_grid.setHorizontalSpacing(5)
        metrics_grid.setVerticalSpacing(3)

        def _mlabel(text, bold=False):
            lbl = QLabel(text)
            lbl.setMinimumWidth(0)
            lbl.setObjectName("rp-metric-key" if not bold else "rp-metric-val")
            return lbl

        # Row 0
        metrics_grid.addWidget(_mlabel("Workers"), 0, 0)
        self.active_workers_label = QLabel("0"); self.active_workers_label.setMinimumWidth(0); self.active_workers_label.setObjectName("rp-metric-val")
        metrics_grid.addWidget(self.active_workers_label, 0, 1)

        metrics_grid.addWidget(_mlabel("RPM"), 0, 2)
        self.rpm_label = QLabel("0/0"); self.rpm_label.setMinimumWidth(0); self.rpm_label.setObjectName("rp-metric-val")
        metrics_grid.addWidget(self.rpm_label, 0, 3)

        metrics_grid.addWidget(_mlabel("RPD"), 0, 4)
        self.rpd_label = QLabel("0/0"); self.rpd_label.setMinimumWidth(0); self.rpd_label.setObjectName("rp-metric-val")
        metrics_grid.addWidget(self.rpd_label, 0, 5)

        # Row 1
        metrics_grid.addWidget(_mlabel("Cost"), 1, 0)
        self.cost_label = QLabel("$0.0000"); self.cost_label.setMinimumWidth(0); self.cost_label.setObjectName("rp-cost-val")
        metrics_grid.addWidget(self.cost_label, 1, 1)

        metrics_grid.addWidget(_mlabel("IDR"), 1, 2)
        self.cost_idr_label = QLabel("Rp 0"); self.cost_idr_label.setMinimumWidth(0); self.cost_idr_label.setObjectName("rp-metric-val")
        metrics_grid.addWidget(self.cost_idr_label, 1, 3)

        metrics_grid.addWidget(_mlabel("Snippets"), 1, 4)
        self.translated_label = QLabel("0"); self.translated_label.setMinimumWidth(0); self.translated_label.setObjectName("rp-metric-val")
        metrics_grid.addWidget(self.translated_label, 1, 5)

        # Row 2 — provider + model  (spans full width)
        metrics_grid.addWidget(_mlabel("Provider"), 2, 0)
        self.provider_label = QLabel("-"); self.provider_label.setObjectName("rp-metric-val")
        self.provider_label.setMinimumWidth(0)
        self.provider_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        metrics_grid.addWidget(self.provider_label, 2, 1)
        metrics_grid.addWidget(_mlabel("Model"), 2, 2)
        self.model_label = QLabel("-"); self.model_label.setObjectName("rp-metric-val")
        self.model_label.setWordWrap(True)
        self.model_label.setMinimumWidth(0)
        self.model_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        metrics_grid.addWidget(self.model_label, 2, 3, 1, 3)

        telemetry_v.addWidget(metrics_widget)

        token_grid = QGridLayout()
        token_grid.setContentsMargins(2, 0, 2, 0)
        token_grid.setHorizontalSpacing(10)
        token_grid.setVerticalSpacing(2)
        self.input_tokens_label = QLabel("In: 0 tok")
        self.input_tokens_label.setMinimumWidth(0)
        self.input_tokens_label.setObjectName("rp-tiny-label")
        token_grid.addWidget(self.input_tokens_label, 0, 0)
        self.output_tokens_label = QLabel("Out: 0 tok")
        self.output_tokens_label.setMinimumWidth(0)
        self.output_tokens_label.setObjectName("rp-tiny-label")
        token_grid.addWidget(self.output_tokens_label, 0, 1)
        self.rate_label_input = QLabel("$0.0000/in")
        self.rate_label_input.setMinimumWidth(0)
        self.rate_label_input.setObjectName("rp-tiny-label")
        token_grid.addWidget(self.rate_label_input, 1, 0)
        self.rate_label_output = QLabel("$0.0000/out")
        self.rate_label_output.setMinimumWidth(0)
        self.rate_label_output.setObjectName("rp-tiny-label")
        token_grid.addWidget(self.rate_label_output, 1, 1)
        token_grid.setColumnStretch(2, 1)
        telemetry_v.addLayout(token_grid)
        self.metrics_widget = metrics_widget

        # ── Cooldown label ───────────────────────────────────────────────────────
        self.countdown_label = QLabel("Cooldown: 60s")
        self.countdown_label.setObjectName("rp-countdown")
        self.countdown_label.setVisible(False)
        bottom_v.addWidget(self.countdown_label)

        main_layout.addWidget(bottom_bar)

        # ── Activate first tab ───────────────────────────────────────────────────
        if self._sidebar_buttons:
            self._on_sidebar_nav(0)

        return main_layout

    def _apply_right_panel_styles(self):
        """Apply modern dark sidebar skin to the Tools & Workspace column."""
        try:
            panel_widget = self.right_panel_scroll
        except Exception:
            return
        if not panel_widget:
            return

        panel_qss = """
            /* ── Root panel ─────────────────────────────────────────────────── */
            #right-panel {
                background-color: #0b0e17;
                border-left: 1px solid #1a2235;
            }

            /* ── Header bar ─────────────────────────────────────────────────── */
            #rp-header-bar {
                background-color: #0d111b;
                border-bottom: 1px solid #1a2235;
            }
            #right-panel QLabel#panel-title {
                color: #e2e8f0;
                font-size: 13pt;
                font-weight: 700;
                letter-spacing: 0.3px;
                background: transparent;
                padding: 0px;
            }

            /* ── Separators ─────────────────────────────────────────────────── */
            #rp-sep {
                background-color: #1a2235;
                border: none;
                max-height: 1px;
            }
            #rp-vsep {
                background-color: #1a2235;
                border: none;
                max-width: 1px;
            }

            /* ── Icon sidebar ───────────────────────────────────────────────── */
            #rp-sidebar {
                background-color: #0d111b;
            }
            QToolButton#rp-nav-btn {
                background: transparent;
                border: none;
                border-radius: 10px;
                color: #4a5c78;
                font-size: 8.5pt;
                font-weight: 600;
                padding: 4px 2px;
            }
            QToolButton#rp-nav-btn:hover {
                background: #141c2e;
                color: #94a3b8;
            }
            QToolButton#rp-nav-btn:checked {
                background: #162035;
                color: #38bdf8;
                border: 1px solid #1e3a5f;
            }

            /* ── Stacked content area ───────────────────────────────────────── */
            #rp-stack {
                background-color: #0b0e17;
            }
            #rp-stack QWidget {
                color: #cbd5e1;
                font-size: 10pt;
            }
            #rp-stack QScrollArea {
                background: transparent;
                border: none;
            }

            /* ── Group boxes ────────────────────────────────────────────────── */
            #rp-stack QGroupBox {
                background: rgba(255,255,255,0.015);
                border: 1px solid #1e293b;
                border-radius: 10px;
                margin-top: 12px;
                padding: 10px 8px 10px 8px;
            }
            #rp-stack QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #38bdf8;
                font-weight: 700;
                font-size: 9.5pt;
                letter-spacing: 0.3px;
            }

            /* ── Section label titles (used instead of QGroupBox in new tabs) */
            QLabel#rp-section-title {
                color: #38bdf8;
                font-size: 9.5pt;
                font-weight: 700;
                padding-bottom: 2px;
                background: transparent;
            }

            /* ── Input controls ─────────────────────────────────────────────── */
            #rp-stack QComboBox,
            #rp-stack QLineEdit,
            #rp-stack QSpinBox,
            #rp-stack QDoubleSpinBox {
                background-color: #0f1624;
                border: 1px solid #1e2d42;
                border-radius: 7px;
                padding: 5px 8px;
                color: #cbd5e1;
                min-height: 26px;
            }
            #rp-stack QComboBox:focus,
            #rp-stack QLineEdit:focus,
            #rp-stack QSpinBox:focus,
            #rp-stack QDoubleSpinBox:focus {
                border-color: #38bdf8;
            }
            #rp-stack QComboBox::drop-down {
                border: none;
                width: 22px;
            }
            #rp-stack QComboBox::down-arrow {
                width: 10px;
                height: 10px;
            }

            /* ── Checkboxes & radios ─────────────────────────────────────────── */
            #rp-stack QCheckBox,
            #rp-stack QRadioButton {
                color: #94a3b8;
                spacing: 7px;
                background: transparent;
            }
            #rp-stack QCheckBox::indicator,
            #rp-stack QRadioButton::indicator {
                width: 15px;
                height: 15px;
                border: 1px solid #2d3f58;
                border-radius: 4px;
                background: #0f1624;
            }
            #rp-stack QCheckBox::indicator:checked {
                background: #38bdf8;
                border-color: #38bdf8;
            }
            #rp-stack QRadioButton::indicator {
                border-radius: 8px;
            }
            #rp-stack QRadioButton::indicator:checked {
                background: #38bdf8;
                border-color: #38bdf8;
            }

            /* ── Standard button ─────────────────────────────────────────────── */
            #rp-stack QPushButton {
                background-color: #141c2e;
                color: #94a3b8;
                border: 1px solid #1e2d42;
                border-radius: 8px;
                padding: 6px 12px;
                font-weight: 600;
                font-size: 9.5pt;
            }
            #rp-stack QPushButton:enabled:hover {
                background-color: #1e3050;
                color: #e2e8f0;
                border-color: #2d4a72;
            }
            #rp-stack QPushButton:enabled:pressed {
                background-color: #1a4276;
                color: #ffffff;
            }
            #rp-stack QPushButton:disabled {
                background-color: #0d1220;
                color: #374151;
                border-color: #131c2e;
            }

            /* ── Sliders ─────────────────────────────────────────────────────── */
            #rp-stack QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: #1e293b;
                border-radius: 2px;
            }
            #rp-stack QSlider::handle:horizontal {
                background: #38bdf8;
                border: none;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            #rp-stack QSlider::sub-page:horizontal {
                background: #38bdf8;
                border-radius: 2px;
            }

            /* ── Bottom bar ──────────────────────────────────────────────────── */
            #rp-bottom-bar {
                background-color: #0d111b;
                border-top: 1px solid #1a2235;
            }

            /* ── Bottom action buttons ───────────────────────────────────────── */
            QPushButton#rp-action-btn {
                background-color: #141c2e;
                color: #94a3b8;
                border: 1px solid #1e2d42;
                border-radius: 7px;
                padding: 5px 6px;
                font-size: 8.5pt;
                font-weight: 600;
            }
            QPushButton#rp-action-btn:enabled:hover {
                background-color: #1e3050;
                color: #e2e8f0;
                border-color: #38bdf8;
            }
            QPushButton#rp-action-btn:disabled {
                color: #2d3f55;
                border-color: #111827;
                background-color: #0d1220;
            }

            QPushButton#rp-save-btn {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #0c4a6e, stop:1 #0369a1);
                color: #e0f2fe;
                border: 1px solid #0284c7;
                border-radius: 7px;
                padding: 5px 6px;
                font-size: 8.5pt;
                font-weight: 700;
            }
            QPushButton#rp-save-btn:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #0369a1, stop:1 #0284c7);
                border-color: #38bdf8;
            }

            QPushButton#rp-confirm-btn {
                background-color: #052e16;
                color: #6ee7b7;
                border: 1px solid #065f46;
                border-radius: 7px;
                padding: 5px 10px;
                font-size: 9pt;
                font-weight: 600;
            }
            QPushButton#rp-confirm-btn:hover {
                background-color: #065f46;
                color: #a7f3d0;
                border-color: #34d399;
            }

            QPushButton#rp-danger-btn {
                background-color: #2d0f0f;
                color: #fca5a5;
                border: 1px solid #7f1d1d;
                border-radius: 7px;
                padding: 5px 10px;
                font-size: 9pt;
                font-weight: 600;
            }
            QPushButton#rp-danger-btn:hover {
                background-color: #7f1d1d;
                color: #fecaca;
            }

            /* ── Metrics grid ────────────────────────────────────────────────── */
            #rp-metrics {
                background: rgba(255,255,255,0.02);
                border: 1px solid #1a2235;
                border-radius: 8px;
            }
            QLabel#rp-metric-key {
                color: #4a5c78;
                font-size: 8.5pt;
                background: transparent;
                padding: 0;
            }
            QLabel#rp-metric-val {
                color: #94a3b8;
                font-size: 8.5pt;
                font-weight: 600;
                background: transparent;
                padding: 0;
            }
            QLabel#rp-cost-val {
                color: #34d399;
                font-size: 8.5pt;
                font-weight: 700;
                background: transparent;
                padding: 0;
            }

            /* ── Token row ───────────────────────────────────────────────────── */
            QLabel#rp-tiny-label {
                color: #374151;
                font-size: 8pt;
                background: transparent;
                padding: 0;
            }

            /* ── Countdown ───────────────────────────────────────────────────── */
            QLabel#rp-countdown {
                color: #fbbf24;
                font-size: 9pt;
                font-weight: 600;
                background: transparent;
            }
        """
        for source, target in {
            "#0b0e17": theme.COLORS["bg"],
            "#0d111b": theme.COLORS["panel"],
            "#1a2235": theme.COLORS["border"],
            "#e2e8f0": theme.COLORS["text"],
            "#4a5c78": theme.COLORS["muted"],
            "#141c2e": theme.COLORS["card_alt"],
            "#94a3b8": theme.COLORS["muted"],
            "#162035": theme.COLORS["card_alt"],
            "#38bdf8": theme.COLORS["accent"],
            "#1e3a5f": theme.COLORS["border"],
            "#cbd5e1": theme.COLORS["text"],
            "#1e293b": theme.COLORS["border"],
            "#0f1624": theme.COLORS["card_alt"],
            "#1e2d42": theme.COLORS["border"],
            "#2d3f58": theme.COLORS["border"],
            "#1e3050": theme.COLORS["card_alt"],
            "#2d4a72": theme.COLORS["accent"],
            "#0d1220": theme.COLORS["panel"],
            "#374151": theme.COLORS["muted"],
            "#131c2e": theme.COLORS["border"],
            "#111827": theme.COLORS["border"],
            "#334155": theme.COLORS["border"],
        }.items():
            panel_qss = panel_qss.replace(source, target)
        panel_widget.setStyleSheet(panel_qss)

    def _create_cleanup_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 14, 10, 12)
        layout.setSpacing(12)

        selection_group = QGroupBox("Text Box && Area Cleanup")
        selection_layout = QVBoxLayout(selection_group)
        selection_layout.setContentsMargins(10, 14, 10, 12)
        selection_layout.setSpacing(8)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        mode_row.addWidget(QLabel("Mode:"))
        self.selection_mode_combo = ScrollableComboBox(self)
        self.selection_mode_combo.addItems(SELECTION_MODE_LABELS)
        self._fit_workspace_combo(self.selection_mode_combo, 10)
        mode_row.addWidget(self.selection_mode_combo, 1)
        selection_layout.addLayout(mode_row)

        self.selection_mode_combo.currentTextChanged.connect(self.selection_mode_changed)
        pen_buttons_layout = QVBoxLayout()
        pen_buttons_layout.setSpacing(6)
        confirm_row = QHBoxLayout()
        confirm_row.setSpacing(6)
        self.confirm_button = QPushButton("Confirm"); self.confirm_button.setMinimumWidth(0); self.confirm_button.clicked.connect(self.confirm_pen_selection); self.confirm_button.setVisible(False)
        self.cancel_button = QPushButton("Cancel"); self.cancel_button.setMinimumWidth(0); self.cancel_button.clicked.connect(self.cancel_pen_selection); self.cancel_button.setVisible(False)
        confirm_row.addWidget(self.confirm_button, 1); confirm_row.addWidget(self.cancel_button, 1)
        pen_buttons_layout.addLayout(confirm_row)

        self.brush_controls_widget = QWidget()
        self.brush_controls_widget.setMinimumWidth(0)
        brush_v = QVBoxLayout(self.brush_controls_widget)
        brush_v.setContentsMargins(0, 0, 0, 0)
        brush_v.setSpacing(6)

        brush_size_row = QHBoxLayout()
        brush_size_row.setSpacing(6)
        brush_size_row.addWidget(QLabel("Brush Size:"))
        self.brush_size_spinbox = QSpinBox()
        self.brush_size_spinbox.setRange(5, 200)
        self.brush_size_spinbox.setValue(25)
        self.brush_size_spinbox.valueChanged.connect(lambda val: self.image_label.set_inpaint_brush_size(val) if hasattr(self, 'image_label') else None)
        brush_size_row.addWidget(self.brush_size_spinbox, 1)
        brush_v.addLayout(brush_size_row)

        brush_eng_lbl = QLabel(InpaintText.WORKSPACE_ENGINE_LABEL)
        brush_eng_lbl.setStyleSheet(f"color: {theme.COLORS['text']}; font-size: 8.5pt;")
        brush_v.addWidget(brush_eng_lbl)
        self.brush_inpaint_engine_combo = QComboBox()
        self._populate_inpaint_engine_combo(self.brush_inpaint_engine_combo, "brush")
        self._fit_workspace_combo(self.brush_inpaint_engine_combo, 12)
        self.brush_inpaint_engine_combo.setToolTip(
            "Model AI inpainting aktif (sinkron otomatis dengan pilihan di tab Full dan Settings)."
        )
        self.brush_inpaint_engine_combo.currentIndexChanged.connect(
            lambda *_: self._on_inpaint_engine_changed(self.brush_inpaint_engine_combo)
        )
        brush_v.addWidget(self.brush_inpaint_engine_combo)

        self.brush_inpaint_status_row = QWidget()
        self.brush_inpaint_status_row.setMinimumWidth(0)
        brush_status_hl = QHBoxLayout(self.brush_inpaint_status_row)
        brush_status_hl.setContentsMargins(0, 0, 0, 0)
        brush_status_hl.setSpacing(6)
        self.brush_inpaint_status_label = QLabel("")
        self.brush_inpaint_status_label.setMinimumWidth(0)
        self.brush_inpaint_status_label.setWordWrap(True)
        self.brush_inpaint_status_label.setStyleSheet(
            f"color: {theme.COLORS['warning']}; font-size: 8pt;"
        )
        brush_status_hl.addWidget(self.brush_inpaint_status_label, 1)
        self.brush_inpaint_download_btn = QPushButton(InpaintText.BTN_DOWNLOAD_INLINE)
        self.brush_inpaint_download_btn.setMinimumWidth(0)
        self.brush_inpaint_download_btn.setStyleSheet("padding: 4px 10px;")
        self.brush_inpaint_download_btn.setIcon(app_icon("download", theme.COLORS['accent'], 13))
        self.brush_inpaint_download_btn.setIconSize(QSize(13, 13))
        self.brush_inpaint_download_btn.setToolTip("Unduh model inpainting terpilih langsung.")
        self.brush_inpaint_download_btn.clicked.connect(
            lambda: self._download_selected_workspace_inpaint_engine("brush")
        )
        brush_status_hl.addWidget(self.brush_inpaint_download_btn)
        self.brush_inpaint_status_row.setVisible(False)
        brush_v.addWidget(self.brush_inpaint_status_row)

        brush_btn_row = QGridLayout()
        brush_btn_row.setSpacing(6)
        self.inpaint_confirm_button = QPushButton(InpaintText.BTN_CLEAN_LABEL)
        self.inpaint_confirm_button.setMinimumWidth(0)
        self.inpaint_confirm_button.setToolTip("Apply inpainting to the painted brush mask")
        self.inpaint_confirm_button.clicked.connect(lambda: self.apply_inpaint_brush_selection(run_ocr_translate=self._is_inpaint_ocr_mode()))
        brush_btn_row.addWidget(self.inpaint_confirm_button, 0, 0)

        self.inpaint_clear_button = QPushButton("Clear Brush")
        self.inpaint_clear_button.setMinimumWidth(0)
        self.inpaint_clear_button.clicked.connect(lambda: self.image_label.clear_inpaint_mask() if hasattr(self, 'image_label') else None)
        brush_btn_row.addWidget(self.inpaint_clear_button, 0, 1)

        self.inpaint_compare_button = QPushButton("Compare")
        self.inpaint_compare_button.setMinimumWidth(0)
        self.inpaint_compare_button.setCheckable(True)
        self.inpaint_compare_button.setToolTip("Show the page before inpainting so OCR can read the original text.")
        self.inpaint_compare_button.toggled.connect(lambda checked: self.compare_mode_btn.setChecked(checked) if hasattr(self, 'compare_mode_btn') else None)
        brush_btn_row.addWidget(self.inpaint_compare_button, 1, 0)

        self.inpaint_cancel_button = QPushButton("Reset Bg")
        self.inpaint_cancel_button.setMinimumWidth(0)
        self.inpaint_cancel_button.setToolTip("Cancel the saved inpainting result for this page.")
        self.inpaint_cancel_button.clicked.connect(self.cancel_inpaint_result)
        brush_btn_row.addWidget(self.inpaint_cancel_button, 1, 1)
        brush_v.addLayout(brush_btn_row)

        self.inpaint_running_panel = QFrame()
        self.inpaint_running_panel.setMinimumWidth(0)
        self.inpaint_running_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.inpaint_running_panel.setStyleSheet(
            f"QFrame {{ background: {theme.COLORS['card_alt']}; "
            f"border: 1px solid {theme.COLORS['accent']}; border-radius: 6px; }}"
        )
        run_panel_v = QVBoxLayout(self.inpaint_running_panel)
        run_panel_v.setContentsMargins(10, 9, 10, 9)
        run_panel_v.setSpacing(6)
        run_head = QHBoxLayout()
        run_head.setContentsMargins(0, 0, 0, 0)
        run_head.setSpacing(6)
        self.inpaint_running_label = QLabel(InpaintText.JOB_STATUS_STARTED)
        self.inpaint_running_label.setMinimumWidth(0)
        self.inpaint_running_label.setWordWrap(True)
        self.inpaint_running_label.setStyleSheet(
            f"color: {theme.COLORS['accent_hover']}; font-size: 8pt; font-weight: 600; border: none;"
        )
        run_head.addWidget(self.inpaint_running_label, 1)
        self.inpaint_elapsed_label = QLabel("0 dtk")
        self.inpaint_elapsed_label.setStyleSheet(
            f"color: {theme.COLORS['muted']}; font-size: 8pt; border: none;"
        )
        run_head.addWidget(self.inpaint_elapsed_label)
        run_panel_v.addLayout(run_head)
        self.inpaint_running_bar = QProgressBar()
        self.inpaint_running_bar.setFixedHeight(6)
        self.inpaint_running_bar.setRange(0, 0)
        self.inpaint_running_bar.setTextVisible(False)
        run_panel_v.addWidget(self.inpaint_running_bar)
        self.inpaint_cancel_job_btn = QPushButton(InpaintText.BTN_CANCEL_JOB)
        self.inpaint_cancel_job_btn.setMinimumWidth(0)
        self.inpaint_cancel_job_btn.setStyleSheet("padding: 4px 10px;")
        self.inpaint_cancel_job_btn.setIcon(app_icon("x", theme.COLORS['danger'], 13))
        self.inpaint_cancel_job_btn.setIconSize(QSize(13, 13))
        self.inpaint_cancel_job_btn.clicked.connect(self._cancel_inpaint_brush_job)
        run_panel_v.addWidget(self.inpaint_cancel_job_btn)
        self.inpaint_running_panel.setVisible(False)
        brush_v.addWidget(self.inpaint_running_panel)

        self.brush_controls_widget.setVisible(False)
        pen_buttons_layout.addWidget(self.brush_controls_widget)

        selection_layout.addLayout(pen_buttons_layout)

        self.create_bubble_checkbox = QCheckBox("White bubble (black outline)")
        self.create_bubble_checkbox.setMinimumWidth(0)
        self.create_bubble_checkbox.setToolTip("When enabled, confirmed selections render a white bubble with a black outline behind the text.")
        selection_layout.addWidget(self.create_bubble_checkbox)

        self.use_background_box_checkbox = QCheckBox("Use Background Box for Text")
        self.use_background_box_checkbox.setMinimumWidth(0)
        self.use_background_box_checkbox.setChecked(bool(SETTINGS.get('cleanup', {}).get('use_background_box', True)))
        self.use_background_box_checkbox.setToolTip("When enabled, translated text is placed inside a background box. Disable for transparent overlay.")
        selection_layout.addWidget(self.use_background_box_checkbox)

        self.constrain_text_checkbox = QCheckBox("Keep Text Inside Area")
        self.constrain_text_checkbox.setMinimumWidth(0)
        self.constrain_text_checkbox.setChecked(bool(SETTINGS.get('cleanup', {}).get('constrain_text', True)))
        self.constrain_text_checkbox.setToolTip("When enabled, text wraps within the area bounds even when the background box is hidden.")
        selection_layout.addWidget(self.constrain_text_checkbox)

        self.inpaint_checkbox = QCheckBox("Use Inpainting (clean bg)")
        self.inpaint_checkbox.setMinimumWidth(0)
        self.inpaint_checkbox.setChecked(bool(SETTINGS.get('cleanup', {}).get('use_inpaint', True)))
        self.inpaint_checkbox.setToolTip("Use Inpainting (Remove Original Text): erase underlying text via your configured IOPaint / Inpaint backend.")
        selection_layout.addWidget(self.inpaint_checkbox)

        apply_mode_box = QVBoxLayout()
        apply_mode_box.setSpacing(4)
        self.apply_mode_selected_radio = QRadioButton("Selected Area")
        self.apply_mode_global_radio = QRadioButton("Global Default")
        self.apply_mode_selected_radio.setMinimumWidth(0)
        self.apply_mode_global_radio.setMinimumWidth(0)
        saved_mode = self._default_cleanup_value('apply_mode') or 'selected'
        if saved_mode == 'global':
            self.apply_mode_global_radio.setChecked(True)
        else:
            self.apply_mode_selected_radio.setChecked(True)
        apply_mode_box.addWidget(self.apply_mode_selected_radio)
        apply_mode_box.addWidget(self.apply_mode_global_radio)

        self.apply_mode_status_label = QLabel()
        self.apply_mode_status_label.setMinimumWidth(0)
        self.apply_mode_status_label.setStyleSheet(f"color: {theme.COLORS['accent']}; font-size: 8.5pt; font-weight: 700;")
        def _update_apply_mode_label():
            self.apply_mode_status_label.setText(
                "Mode: Global Default" if self.apply_mode_global_radio.isChecked() else "Mode: Selected Area"
            )
        _update_apply_mode_label()
        apply_mode_box.addWidget(self.apply_mode_status_label)
        selection_layout.addLayout(apply_mode_box)

        self.apply_all_button = QPushButton("Apply to All Areas")
        self.apply_all_button.setMinimumWidth(0)
        self.apply_all_button.setToolTip("Update defaults only or push current cleanup toggles to every existing area.")
        def _on_apply_all_clicked():
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

            dlg = QDialog(self)
            dlg.setWindowTitle("Apply to All Areas")
            v = QVBoxLayout(dlg)
            v.addWidget(QLabel("Choose how to apply the change to all existing areas:"))
            btn_layout = QHBoxLayout()
            update_defaults_btn = QPushButton("Update Defaults Only")
            force_update_btn = QPushButton("Force Update All")
            cancel_btn = QPushButton("Cancel")
            btn_layout.addWidget(update_defaults_btn)
            btn_layout.addWidget(force_update_btn)
            btn_layout.addWidget(cancel_btn)
            v.addLayout(btn_layout)

            def _update_defaults_only():
                use_box_val = bool(self.use_background_box_checkbox.isChecked())
                use_inpaint_val = bool(self.inpaint_checkbox.isChecked())
                constrain_text_val = bool(self.constrain_text_checkbox.isChecked())
                self._set_global_cleanup_default('use_background_box', use_box_val)
                self._set_global_cleanup_default('use_inpaint', use_inpaint_val)
                self._set_global_cleanup_default('constrain_text', constrain_text_val)
                self.show_toast("Apply to all", "Global defaults updated. Existing areas keep their individual overrides.", kind="success")
                self._sync_cleanup_controls_from_selection()
                dlg.accept()

            def _force_update_all():
                use_box_val = bool(self.use_background_box_checkbox.isChecked())
                use_inpaint_val = bool(self.inpaint_checkbox.isChecked())
                constrain_text_val = bool(self.constrain_text_checkbox.isChecked())
                self._set_global_cleanup_default('use_background_box', use_box_val)
                self._set_global_cleanup_default('use_inpaint', use_inpaint_val)
                self._set_global_cleanup_default('constrain_text', constrain_text_val)
                default_box = self._default_cleanup_value('use_background_box')
                default_inpaint = self._default_cleanup_value('use_inpaint')
                default_constrain = self._default_cleanup_value('constrain_text')
                for record in (self.all_typeset_data or {}).values():
                    areas = record.get('areas', []) if isinstance(record, dict) else []
                    for area in areas:
                        if use_box_val == default_box:
                            area.clear_override('use_background_box')
                        else:
                            area.set_override('use_background_box', use_box_val)
                        if use_inpaint_val == default_inpaint:
                            area.clear_override('use_inpaint')
                        else:
                            area.set_override('use_inpaint', use_inpaint_val)
                        if constrain_text_val == default_constrain:
                            area.clear_override('constrain_text')
                        else:
                            area.set_override('constrain_text', constrain_text_val)
                try:
                    self.redraw_all_typeset_areas()
                except Exception:
                    pass
                label = getattr(self, 'image_label', None)
                if label is not None:
                    try:
                        label.update()
                    except Exception:
                        pass
                self._sync_cleanup_controls_from_selection()
                self.show_toast("Apply to all", "Global defaults updated and applied to every typeset area.", kind="success")
                dlg.accept()

            update_defaults_btn.clicked.connect(_update_defaults_only)
            force_update_btn.clicked.connect(_force_update_all)
            cancel_btn.clicked.connect(dlg.reject)
            dlg.exec_()

        self.apply_all_button.clicked.connect(_on_apply_all_clicked)
        selection_layout.addWidget(self.apply_all_button)

        def _on_apply_mode_changed():
            mode = 'global' if self.apply_mode_global_radio.isChecked() else 'selected'
            self._set_global_cleanup_default('apply_mode', mode)
            _update_apply_mode_label()
            self._sync_cleanup_controls_from_selection()
        self.apply_mode_selected_radio.toggled.connect(_on_apply_mode_changed)
        self.apply_mode_global_radio.toggled.connect(_on_apply_mode_changed)

        self.use_background_box_checkbox.toggled.connect(
            lambda state: self._apply_cleanup_change('use_background_box', bool(state))
        )
        self.constrain_text_checkbox.toggled.connect(
            lambda state: self._apply_cleanup_change('constrain_text', bool(state))
        )
        self.inpaint_checkbox.toggled.connect(
            lambda state: self._apply_cleanup_change('use_inpaint', bool(state))
        )
        layout.addWidget(selection_group)

        # ── Integrated Inpainting Engine Card (Unified Full & Brush) ────────────
        inpaint_card = QGroupBox("Inpainting Engine (Full && Brush)")
        inpaint_v = QVBoxLayout(inpaint_card)
        inpaint_v.setContentsMargins(12, 12, 12, 12)
        inpaint_v.setSpacing(8)

        cleanup_eng_lbl = QLabel(InpaintText.LABEL_UNIFIED_ENGINE)
        cleanup_eng_lbl.setStyleSheet(f"color: {theme.COLORS['text']}; font-size: 8.5pt;")
        inpaint_v.addWidget(cleanup_eng_lbl)
        self.cleanup_inpaint_engine_combo = QComboBox()
        self._populate_inpaint_engine_combo(self.cleanup_inpaint_engine_combo, "full")
        self._fit_workspace_combo(self.cleanup_inpaint_engine_combo, 12)
        self.cleanup_inpaint_engine_combo.setToolTip(
            "Model inpainting tunggal untuk Full-Page Translate dan Inpainting Brush (default: Built-in Big-LaMa)."
        )
        self.cleanup_inpaint_engine_combo.currentIndexChanged.connect(
            lambda *_: self._on_inpaint_engine_changed(self.cleanup_inpaint_engine_combo)
        )
        inpaint_v.addWidget(self.cleanup_inpaint_engine_combo)

        self.cleanup_inpaint_summary_label = QLabel("")
        self.cleanup_inpaint_summary_label.setWordWrap(True)
        self.cleanup_inpaint_summary_label.setMinimumWidth(0)
        self.cleanup_inpaint_summary_label.setStyleSheet(
            f"background: {theme.COLORS['card_alt']}; color: {theme.COLORS['accent_hover']}; "
            f"border: 1px solid {theme.COLORS['border']}; border-radius: 6px; "
            f"padding: 7px 10px; font-size: 8.5pt;"
        )
        inpaint_v.addWidget(self.cleanup_inpaint_summary_label)

        self.cleanup_download_missing_btn = QPushButton(InpaintText.BTN_DOWNLOAD)
        self.cleanup_download_missing_btn.setMinimumWidth(0)
        self.cleanup_download_missing_btn.setIcon(app_icon("download", theme.COLORS["accent"], 14))
        self.cleanup_download_missing_btn.setIconSize(QSize(14, 14))
        self.cleanup_download_missing_btn.setToolTip("Unduh model AI yang dipilih di atas jika belum tersedia lokal.")
        self.cleanup_download_missing_btn.clicked.connect(lambda: self._download_next_missing_inpaint_engine())
        self.cleanup_download_missing_btn.setVisible(False)
        inpaint_v.addWidget(self.cleanup_download_missing_btn)

        self.cleanup_inpaint_dl_bar = QProgressBar()
        self.cleanup_inpaint_dl_bar.setFixedHeight(6)
        self.cleanup_inpaint_dl_bar.setRange(0, 100)
        self.cleanup_inpaint_dl_bar.setTextVisible(False)
        self.cleanup_inpaint_dl_bar.setVisible(False)
        inpaint_v.addWidget(self.cleanup_inpaint_dl_bar)

        cfg_inpaint_btn = QPushButton("Kelola Model && Settings Inpaint")
        cfg_inpaint_btn.setMinimumWidth(0)
        cfg_inpaint_btn.setToolTip("Unduh model AI bawaan, atur GPU/CPU, atau konfigurasi opsional IOPaint server")
        cfg_inpaint_btn.setIcon(app_icon("settings", theme.COLORS["accent"], 14))
        cfg_inpaint_btn.setIconSize(QSize(14, 14))
        cfg_inpaint_btn.clicked.connect(lambda: self.open_settings_dialog('cleanup'))
        inpaint_v.addWidget(cfg_inpaint_btn)
        layout.addWidget(inpaint_card)

        self._sync_inpaint_engine_combos()
        self._refresh_inpaint_summary_badges()
        self._sync_cleanup_controls_from_selection()
        layout.addStretch()
        return tab

    def _create_proofreader_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 16, 14, 14)

        description = QLabel("Send recent translations to the AI proofreader to polish grammar and flow.")
        description.setWordWrap(True)
        layout.addWidget(description)

        self.proofreader_empty_label = QLabel("No entries sent from History.")
        self.proofreader_empty_label.setAlignment(Qt.AlignCenter)
        self.proofreader_empty_label.setStyleSheet("color: #7f8ba7; font-style: italic;")
        layout.addWidget(self.proofreader_empty_label)

        self.proofreader_table = self._create_result_table()
        self.proofreader_table.setProperty('result_limit', self.history_preview_limit)
        self.proofreader_table.setVisible(False)
        self.result_table_registry['proofreader'].add(self.proofreader_table)
        layout.addWidget(self.proofreader_table)

        proof_controls = QHBoxLayout()
        proof_controls.addStretch()
        proof_confirm_all = QPushButton("Confirm All")
        proof_confirm_all.clicked.connect(partial(self.confirm_all_result_entries, 'proofreader'))
        proof_controls.addWidget(proof_confirm_all)
        # Batch PF button
        batch_pf_btn = QPushButton("Batch PF (AI Contextual Translate)")
        batch_pf_btn.clicked.connect(self.batch_pf_contextual_translate)
        proof_controls.addWidget(batch_pf_btn)
        proof_view_all = QPushButton("View All")
        proof_view_all.clicked.connect(self.show_proofreader_modal)
        proof_controls.addWidget(proof_view_all)
        layout.addLayout(proof_controls)

        self.batch_pf_btn = batch_pf_btn
        self.proofreader_confirm_all_button = proof_confirm_all

        self.proofreader_view_all_button = proof_view_all
        self.proofreader_tab_widget = tab
        self.refresh_history_views()
        return tab

    def _create_quality_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 16, 14, 14)

        description = QLabel("Request a final quality review to check consistency and naturalness.")
        description.setWordWrap(True)
        layout.addWidget(description)

        self.quality_empty_label = QLabel("No entries sent from History.")
        self.quality_empty_label.setAlignment(Qt.AlignCenter)
        self.quality_empty_label.setStyleSheet("color: #7f8ba7; font-style: italic;")
        layout.addWidget(self.quality_empty_label)

        self.quality_table = self._create_result_table()
        self.quality_table.setProperty('result_limit', self.history_preview_limit)
        self.quality_table.setVisible(False)
        self.result_table_registry['quality'].add(self.quality_table)
        layout.addWidget(self.quality_table)

        quality_controls = QHBoxLayout()
        quality_controls.addStretch()
        quality_confirm_all = QPushButton("Confirm All")
        quality_confirm_all.clicked.connect(partial(self.confirm_all_result_entries, 'quality'))
        quality_controls.addWidget(quality_confirm_all)
        # Batch QC button
        batch_qc_btn = QPushButton("Batch QC (AI Style/Tone Check)")
        batch_qc_btn.clicked.connect(self.batch_qc_style_tone_check)
        quality_controls.addWidget(batch_qc_btn)
        quality_view_all = QPushButton("View All")
        quality_view_all.clicked.connect(self.show_quality_modal)
        quality_controls.addWidget(quality_view_all)
        layout.addLayout(quality_controls)

        self.batch_qc_btn = batch_qc_btn
        self.quality_confirm_all_button = quality_confirm_all
        self.quality_view_all_button = quality_view_all
        self.quality_tab_widget = tab
        self.refresh_history_views()
        return tab

    def _create_scene_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 16, 14, 14)
        
        # Scene Selector & Management
        mgmt_layout = QHBoxLayout()
        self.scene_selector = QComboBox()
        self.scene_selector.currentIndexChanged.connect(self.on_scene_selection_changed)
        mgmt_layout.addWidget(QLabel("Scene:"))
        mgmt_layout.addWidget(self.scene_selector, 1)
        
        new_scene_btn = QPushButton("New")
        new_scene_btn.clicked.connect(self.prompt_create_scene)
        mgmt_layout.addWidget(new_scene_btn)
        
        del_scene_btn = QPushButton("Delete")
        del_scene_btn.clicked.connect(self.prompt_delete_scene)
        mgmt_layout.addWidget(del_scene_btn)
        
        layout.addLayout(mgmt_layout)
        
        # Description / Info
        self.scene_info_label = QLabel("Select or create a scene to manage dialogues.")
        self.scene_info_label.setWordWrap(True)
        layout.addWidget(self.scene_info_label)

        # AI Tools for Scene
        ai_tools_layout = QHBoxLayout()
        ai_params_group = QGroupBox("AI Scene Tools")
        ai_group_layout = QHBoxLayout(ai_params_group)
        ai_group_layout.setContentsMargins(5, 5, 5, 5)
        
        self.scene_pf_btn = QPushButton("Proofread Scene")
        self.scene_pf_btn.clicked.connect(lambda: self.process_scene_with_ai("proofreading"))
        ai_group_layout.addWidget(self.scene_pf_btn)
        
        self.scene_qc_btn = QPushButton("Quality Check")
        self.scene_qc_btn.clicked.connect(lambda: self.process_scene_with_ai("quality"))
        ai_group_layout.addWidget(self.scene_qc_btn)
        
        self.scene_natural_btn = QPushButton("Naturalize")
        self.scene_natural_btn.clicked.connect(lambda: self.process_scene_with_ai("naturalization"))
        ai_group_layout.addWidget(self.scene_natural_btn)
        
        ai_tools_layout.addWidget(ai_params_group)

        # Scene Model Selector
        model_layout = QHBoxLayout()
        
        # Checkbox to sync with main AI Hardware tab
        self.use_main_model_checkbox = QCheckBox("Use Main Model (from Hardware Tab)")
        self.use_main_model_checkbox.setChecked(True)
        self.use_main_model_checkbox.setToolTip("If checked, uses the model selected in the AI Hardware configuration.")
        model_layout.addWidget(self.use_main_model_checkbox)

        # Scene-specific combo (hidden if sync is on)
        self.scene_model_combo = QComboBox()
        self.populate_ai_models_combo(self.scene_model_combo)
        self.scene_model_combo.setVisible(False)
        model_layout.addWidget(self.scene_model_combo, 1)
        
        # Toggle visibility logic
        self.use_main_model_checkbox.toggled.connect(lambda checked: self.scene_model_combo.setVisible(not checked))

        ai_group_layout.insertLayout(0, model_layout)

        layout.addLayout(ai_tools_layout)
        
        # Table
        self.scene_table = self._create_result_table()
        self.scene_table.setProperty('result_limit', None)
        self.result_table_registry['scene'].add(self.scene_table)
        layout.addWidget(self.scene_table)
        
        # Apply Actions
        apply_layout = QHBoxLayout()
        self.apply_scene_btn = QPushButton("Apply All to Canvas")
        self.apply_scene_btn.setToolTip("Apply current text in this scene to the actual bubbles on canvas.")
        self.apply_scene_btn.clicked.connect(self.apply_scene_to_canvas)
        apply_layout.addStretch()
        apply_layout.addWidget(self.apply_scene_btn)
        layout.addLayout(apply_layout)
        
        self.refresh_scene_ui_state()
        return tab

    def _create_ai_hardware_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(12)

        # ── Active Pipeline Mode Banner ───────────────────────────────────────
        hero = QFrame()
        hero.setStyleSheet(
            f"QFrame {{ background: {theme.COLORS['card']}; border: 1px solid {theme.COLORS['border']}; "
            f"border-left: 3px solid {theme.COLORS['accent']}; border-radius: 8px; }}"
        )
        hero_v = QVBoxLayout(hero)
        hero_v.setContentsMargins(12, 10, 12, 10)
        hero_v.setSpacing(6)
        hero_row = QHBoxLayout()
        hero_row.setSpacing(6)
        hero_title = QLabel("AI Translation")
        hero_title.setMinimumWidth(0)
        hero_title.setStyleSheet(f"color: {theme.COLORS['text']}; font-weight: 800; font-size: 10pt; border: none;")
        mode_pill = QLabel("AI-ONLY")
        mode_pill.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        mode_pill.setStyleSheet(
            f"color: {theme.COLORS['accent']}; background: rgba(56, 189, 248, 0.12); "
            f"border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 999px; "
            f"padding: 2px 8px; font-size: 7.5pt; font-weight: 700;"
        )
        hero_row.addWidget(hero_title)
        hero_row.addStretch()
        hero_row.addWidget(mode_pill)
        hero_v.addLayout(hero_row)
        hero_sub = QLabel("Select your active translation model and tone style.")
        hero_sub.setWordWrap(True)
        hero_sub.setMinimumWidth(0)
        hero_sub.setStyleSheet(f"color: {theme.COLORS['muted']}; font-size: 8.5pt; border: none;")
        hero_v.addWidget(hero_sub)
        layout.addWidget(hero)

        # ── AI Model & Translation ────────────────────────────────────────────
        ai_group = QGroupBox("AI Models && Translation")
        ai_v = QVBoxLayout(ai_group)
        ai_v.setContentsMargins(12, 14, 12, 12)
        ai_v.setSpacing(8)

        _ai_lbl_style = f"color: {theme.COLORS['muted']}; font-size: 8.5pt; font-weight: 600;"

        model_lbl = QLabel("AI Model:")
        model_lbl.setStyleSheet(_ai_lbl_style)
        ai_v.addWidget(model_lbl)
        self.ai_model_combo = QComboBox()
        self._fit_workspace_combo(self.ai_model_combo, 12)
        self.ai_model_combo.currentTextChanged.connect(self.on_ai_model_changed)
        ai_v.addWidget(self.ai_model_combo)

        style_lbl = QLabel("Style:")
        style_lbl.setStyleSheet(_ai_lbl_style)
        ai_v.addWidget(style_lbl)
        self.style_combo = QComboBox()
        self.style_combo.addItems(self.translation_styles)
        self._fit_workspace_combo(self.style_combo, 12)
        default_style = SETTINGS.get('general', {}).get('default_translation_style', 'Santai (Default)')
        if default_style in self.translation_styles:
            self.style_combo.setCurrentText(default_style)
        ai_v.addWidget(self.style_combo)

        cfg_api_btn = QPushButton("Providers && API Settings")
        cfg_api_btn.setMinimumWidth(0)
        cfg_api_btn.setToolTip("Manage Providers & API Keys in Settings")
        cfg_api_btn.setIcon(app_icon("settings", theme.COLORS["accent"], 14))
        cfg_api_btn.setIconSize(QSize(14, 14))
        cfg_api_btn.clicked.connect(lambda: self.open_settings_dialog('api'))
        ai_v.addWidget(cfg_api_btn)

        layout.addWidget(ai_group)

        # ── Custom Styles ─────────────────────────────────────────────────────
        custom_style_group = QGroupBox("Custom Styles")
        cs_layout = QVBoxLayout(custom_style_group)
        cs_layout.setContentsMargins(12, 14, 12, 12)
        cs_layout.setSpacing(8)

        self.style_input = QLineEdit(self)
        self.style_input.setMinimumWidth(0)
        self.style_input.setPlaceholderText("Enter custom style name...")
        cs_layout.addWidget(self.style_input)

        style_btn_row = QHBoxLayout()
        style_btn_row.setSpacing(8)
        add_style_btn = QPushButton("+ Add")
        add_style_btn.setMinimumWidth(0)
        add_style_btn.setStyleSheet(compact_primary_button_qss())
        add_style_btn.clicked.connect(lambda: (self.add_custom_style(self.style_input.text()) and self.style_input.clear()))
        style_btn_row.addWidget(add_style_btn, 1)
        remove_style_btn = QPushButton("Remove")
        remove_style_btn.setMinimumWidth(0)
        remove_style_btn.clicked.connect(lambda: self.remove_selected_style())
        style_btn_row.addWidget(remove_style_btn, 1)
        cs_layout.addLayout(style_btn_row)

        cs_hint = QLabel("Added styles appear immediately in the Style dropdown above; Remove deletes the selected style.")
        cs_hint.setWordWrap(True)
        cs_hint.setStyleSheet(f"color: {theme.COLORS['muted']}; font-size: 8pt;")
        cs_layout.addWidget(cs_hint)

        layout.addWidget(custom_style_group)
        layout.addStretch()
        return tab

    def setup_styles(self):
        self.apply_appearance_from_settings()

    def _refresh_welcome_theme(self):
        center_stack = getattr(self, 'center_stack', None)
        welcome_widget = getattr(self, 'welcome_widget', None)
        if center_stack is None or welcome_widget is None:
            return
        try:
            current_index = center_stack.currentIndex()
            welcome_index = center_stack.indexOf(welcome_widget)
            if welcome_index < 0:
                return
            new_welcome = self._build_welcome_widget()
            center_stack.removeWidget(welcome_widget)
            welcome_widget.deleteLater()
            center_stack.insertWidget(welcome_index, new_welcome)
            self.welcome_widget = new_welcome
            if current_index == welcome_index:
                center_stack.setCurrentIndex(welcome_index)
        except Exception:
            pass

    def setup_shortcuts(self):
        self._shortcut_callbacks = {
            'undo': self.undo_last_action,
            'redo': self.redo_last_action,
            'save_image': self.save_image,
            'confirm_pen': self.confirm_pen_via_shortcut,
            'next': self.on_next_clicked,
            'prev': self.load_prev_image,
            'emergency_close': self.emergency_save_and_exit,
        }
        for idx in range(len(SELECTION_MODE_LABELS)):
            self._shortcut_callbacks[f'selection_mode_{idx}'] = partial(self.set_selection_mode_by_index, idx)
        self.reload_shortcuts()

    def _build_welcome_widget(self):
        """Bangun widget welcome screen yang indah dengan quick actions dan recent projects."""
        from PyQt5.QtWidgets import (
            QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
            QScrollArea, QFrame, QSizePolicy, QGridLayout, QToolButton
        )
        from PyQt5.QtCore import Qt, QSize
        from PyQt5.QtGui import QFont, QColor, QPalette

        outer = QWidget()
        outer.setObjectName("welcome-outer")
        outer.setStyleSheet(f"""
            QWidget#welcome-outer {{
                background: {theme.COLORS["bg"]};
            }}
        """)

        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Scroll area supaya konten tidak terpotong di layar kecil
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(60, 50, 60, 50)
        vbox.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        header_row.setSpacing(12)
        header_row.setAlignment(Qt.AlignCenter)
        header_icon = icon_label("book", theme.COLORS["accent"], size=36)
        header_icon.setStyleSheet("background: transparent; margin-bottom: 4px;")
        header_row.addWidget(header_icon)
        header_lbl = QLabel("MangaTranslate")
        header_lbl.setAlignment(Qt.AlignCenter)
        header_lbl.setStyleSheet(f"""
            color: {theme.COLORS["text"]};
            font-size: 32pt;
            font-weight: 800;
            font-family: {theme.FONT_FAMILY};
            letter-spacing: 1px;
            margin-bottom: 4px;
            background: transparent;
        """)
        header_row.addWidget(header_lbl)
        vbox.addLayout(header_row)

        sub_lbl = QLabel(welcome_subtitle_html())
        sub_lbl.setAlignment(Qt.AlignCenter)
        sub_lbl.setTextFormat(Qt.RichText)
        sub_lbl.setStyleSheet(f"""
            color: {theme.COLORS["muted"]};
            font-size: 11pt;
            font-family: {theme.FONT_FAMILY};
            margin-bottom: 36px;
        """)
        vbox.addWidget(sub_lbl)

        # ── Separator ─────────────────────────────────────────────────────────
        def make_sep():
            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setStyleSheet(f"color: {theme.COLORS['border']}; margin: 0 0 24px 0;")
            return sep

        # ── Quick Actions ──────────────────────────────────────────────────────
        qa_title = QLabel("Quick Start")
        qa_title.setStyleSheet(f"""
            color: {theme.COLORS["muted"]};
            font-size: 9pt;
            font-weight: 700;
            letter-spacing: 2px;
            text-transform: uppercase;
            font-family: {theme.FONT_FAMILY};
            margin-bottom: 12px;
        """)
        vbox.addWidget(qa_title)

        qa_row = QHBoxLayout()
        qa_row.setSpacing(12)

        def make_action_btn(icon_name, label, slot, color_start, color_end, border_color):
            btn = QToolButton()
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            btn.setIcon(app_icon(icon_name, theme.COLORS["accent"], 26))
            btn.setIconSize(QSize(26, 26))
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setFixedHeight(90)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QToolButton {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {color_start}, stop:1 {color_end});
                    border: 1px solid {border_color};
                    border-radius: 12px;
                    color: {theme.COLORS["text"]};
                    font-size: 10pt;
                    font-weight: 600;
                    font-family: {theme.FONT_FAMILY};
                    padding: 12px 8px;
                    text-align: center;
                }}
                QToolButton:hover {{
                    border: 1px solid {theme.COLORS["accent"]};
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {theme.COLORS["card_alt"]}, stop:1 {theme.COLORS["panel"]});
                }}
                QToolButton:pressed {{
                    background: {theme.COLORS["border"]};
                }}
            """)
            btn.setText(label)
            btn.clicked.connect(slot)
            return btn

        btn_folder = make_action_btn(
            "folder", "Open Folder",
            self.load_folder,
            theme.COLORS["card_alt"], theme.COLORS["panel"], theme.COLORS["border"]
        )
        btn_project = make_action_btn(
            "layers", "Load Project",
            self.load_project,
            theme.COLORS["card_alt"], theme.COLORS["panel"], theme.COLORS["border"]
        )
        qa_row.addWidget(btn_folder)
        qa_row.addWidget(btn_project)
        vbox.addLayout(qa_row)

        vbox.addSpacing(32)
        vbox.addWidget(make_sep())

        # ── Recent Projects ────────────────────────────────────────────────────
        rp_header = QHBoxLayout()
        rp_title = QLabel("Recent Projects")
        rp_title.setStyleSheet(f"""
            color: {theme.COLORS["muted"]};
            font-size: 9pt;
            font-weight: 700;
            letter-spacing: 2px;
            font-family: {theme.FONT_FAMILY};
            margin-bottom: 12px;
        """)
        rp_header.addWidget(rp_title)
        rp_header.addStretch()
        clear_recent_btn = QPushButton("Clear All")
        clear_recent_btn.setFixedHeight(24)
        clear_recent_btn.setCursor(Qt.PointingHandCursor)
        clear_recent_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {theme.COLORS["muted"]};
                border: 1px solid {theme.COLORS["border"]};
                border-radius: 4px;
                padding: 0 8px;
                font-size: 8pt;
                font-family: {theme.FONT_FAMILY};
            }}
            QPushButton:hover {{ color: {theme.COLORS["danger"]}; border-color: {theme.COLORS["danger"]}; }}
        """)
        clear_recent_btn.clicked.connect(self._clear_recent_projects)
        rp_header.addWidget(clear_recent_btn)
        vbox.addLayout(rp_header)

        # Container untuk grid kartu recent — di-refresh oleh _refresh_welcome_screen()
        self._welcome_recent_container = QWidget()
        self._welcome_recent_container.setStyleSheet("background: transparent;")
        self._welcome_recent_grid = QGridLayout(self._welcome_recent_container)
        self._welcome_recent_grid.setSpacing(10)
        self._welcome_recent_grid.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(self._welcome_recent_container)

        # Label "no recent" (akan di-show/hide oleh _populate_recent_cards)
        # PENTING: inisialisasi _welcome_no_recent_lbl SEBELUM _populate_recent_cards() dipanggil
        self._welcome_no_recent_lbl = QLabel("No recent projects yet.\nOpen a folder or load a project to get started.")
        self._welcome_no_recent_lbl.setAlignment(Qt.AlignCenter)
        self._welcome_no_recent_lbl.setStyleSheet(f"""
            color: {theme.COLORS["muted"]};
            font-size: 10pt;
            font-family: {theme.FONT_FAMILY};
            padding: 24px;
        """)
        vbox.addWidget(self._welcome_no_recent_lbl)

        self._populate_recent_cards()  # Isi awal (setelah semua atribut diset)

        vbox.addSpacing(32)
        vbox.addWidget(make_sep())

        # ── Keyboard Shortcuts ────────────────────────────────────────────────
        ks_title = QLabel("Keyboard Shortcuts")
        ks_title.setStyleSheet(f"""
            color: {theme.COLORS["muted"]};
            font-size: 9pt;
            font-weight: 700;
            letter-spacing: 2px;
            font-family: {theme.FONT_FAMILY};
            margin-bottom: 10px;
        """)
        vbox.addWidget(ks_title)

        shortcuts_data = [
            ("Space", "Next Image"),
            ("Esc", "Save Project"),
            ("F2", NavText.FOCUS_MODE_SHORTCUT),
            ("F3", "Toggle Folder Panel"),
            ("F4", "Toggle Tools Panel"),
            ("1–9", "Switch Selection Mode"),
            ("Ctrl+S", "Save Project"),
            ("Ctrl+H", "Find & Replace"),
            ("Ctrl+C / Ctrl+V", "Copy / Paste Area"),
        ]

        sc_grid = QGridLayout()
        sc_grid.setSpacing(6)
        sc_grid.setHorizontalSpacing(20)
        for i, (key, desc) in enumerate(shortcuts_data):
            col = (i % 2) * 2
            row = i // 2
            key_lbl = QLabel(key)
            key_lbl.setStyleSheet(f"""
                color: {theme.COLORS["accent"]};
                font-family: {theme.CODE_FONT_FAMILY};
                font-size: 9pt;
                font-weight: 700;
                background: {theme.COLORS["card_alt"]};
                border: 1px solid {theme.COLORS["border"]};
                border-radius: 4px;
                padding: 2px 8px;
            """)
            key_lbl.setFixedWidth(130)
            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet(f"""
                color: {theme.COLORS["muted"]};
                font-size: 9pt;
                font-family: {theme.FONT_FAMILY};
            """)
            sc_grid.addWidget(key_lbl, row, col)
            sc_grid.addWidget(desc_lbl, row, col + 1)

        vbox.addLayout(sc_grid)
        vbox.addStretch(1)

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)
        return outer

    def _populate_recent_cards(self):
        """Isi ulang grid kartu recent projects dari SETTINGS."""
        from PyQt5.QtWidgets import (
            QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
        )
        from PyQt5.QtCore import Qt
        import os

        grid = getattr(self, '_welcome_recent_grid', None)
        if grid is None:
            return

        # Bersihkan widget lama dari grid
        while grid.count():
            item = grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        recent = SETTINGS.get('recent_projects', [])
        no_recent_lbl = getattr(self, '_welcome_no_recent_lbl', None)
        if no_recent_lbl:
            no_recent_lbl.setVisible(len(recent) == 0)

        container = getattr(self, '_welcome_recent_container', None)
        if container:
            container.setVisible(len(recent) > 0)

        cols = 2  # Kartu ditampilkan dalam 2 kolom
        for idx, proj_path in enumerate(recent[:10]):
            card = self._make_recent_project_card(proj_path)
            row, col = divmod(idx, cols)
            grid.addWidget(card, row, col)

    def _refresh_welcome_screen(self):
        """Refresh kartu recent projects di welcome screen tanpa rebuild seluruh widget."""
        self._populate_recent_cards()
