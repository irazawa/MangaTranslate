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

        self.use_box_action = None
        settings_center_action = QAction('Settings', self)
        settings_center_action.triggered.connect(lambda: self.open_settings_dialog('profile'))
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
        self.file_list_widget = QListWidget()
        self.file_list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_list_widget.currentItemChanged.connect(self.on_file_selected)
        self.left_panel_layout.addWidget(self.file_list_widget)
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
        right_panel_content.setLayout(right_panel_layout)
        right_panel_content.setMinimumHeight(0)

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

        header_icon = QLabel("⚡")
        header_icon.setStyleSheet("font-size:16px; background:transparent; color:#38bdf8;")
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

        # Tab definitions: (label_short, emoji, tooltip, widget_builder)
        tab_defs = [
            ("OCR",      "🔍", "Translate & OCR settings",     self._create_translate_tab),
            ("Typeset",  "✏️", "Typography & text styling",    self._create_typeset_tab),
            ("Layers",   "🗂️", "Canvas layer manager",         self._create_layers_tab),
            ("Cleanup",  "🧹", "Inpainting & detection tools",  self._create_cleanup_tab),
            ("History",  "📋", "Translation history log",       self._create_history_tab),
            ("Scenes",   "🎬", "Scene / dialogue manager",      self._create_scene_tab),
            ("AI Cfg",   "🤖", "AI models & hardware config",   self._create_ai_hardware_tab),
        ]
        if self._chat_widget is not None:
            # Insert chat after OCR
            tab_defs.insert(1, ("Chat", "💬", "AI Chat & Video", None))

        compact_markers = {
            "OCR": "OCR",
            "Typeset": "TXT",
            "Layers": "LYR",
            "Cleanup": "CLN",
            "History": "HIS",
            "Scenes": "SCN",
            "AI Cfg": "AI",
            "Chat": "CHAT",
        }
        tab_defs = [
            (label, compact_markers.get(label, marker), tip, builder)
            for label, marker, tip, builder in tab_defs
        ]

        # QStackedWidget as content area
        self.right_stack = QStackedWidget()
        self.right_stack.setObjectName("rp-stack")
        self.right_stack.setMinimumSize(0, 0)
        self.right_stack.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        # Compatibility alias so code referencing self.tabs still works for tab switching
        # We create a minimal shim object
        class _TabShim:
            """Shim so legacy `self.tabs.setCurrentIndex(n)` calls still work."""
            def __init__(self, stack):
                self._stack = stack
            def setCurrentIndex(self, i):
                self._stack.setCurrentIndex(i)
            def currentIndex(self):
                return self._stack.currentIndex()
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
        self.tabs = _TabShim(self.right_stack)

        self._sidebar_buttons = []
        self._stack_page_map = {}  # page_index -> btn

        def _make_sidebar_btn(marker, label, tip, page_idx):
            btn = QToolButton()
            btn.setObjectName("rp-nav-btn")
            btn.setText(f"{marker}\n{label}")
            btn.setToolTip(tip)
            btn.setCheckable(True)
            btn.setFixedSize(60, 56)
            btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
            btn.setProperty("page", page_idx)
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
        bottom_v = QVBoxLayout(bottom_bar)
        bottom_v.setContentsMargins(10, 8, 10, 8)
        bottom_v.setSpacing(6)

        # ── Batch action row ────────────────────────────────────────────────────
        batch_row = QHBoxLayout()
        batch_row.setSpacing(6)
        self.process_batch_button = QPushButton("⚡ Batch Now")
        self.process_batch_button.setObjectName("rp-action-btn")
        self.process_batch_button.setText("Batch Now")
        self.process_batch_button.setToolTip("Process batch queue now")
        self.process_batch_button.clicked.connect(self.start_batch_processing)
        batch_row.addWidget(self.process_batch_button)

        self.batch_process_button = QPushButton("🔍 Detect All")
        self.batch_process_button.setObjectName("rp-action-btn")
        self.batch_process_button.setText("Detect All")
        self.batch_process_button.setToolTip("Detects all bubbles/text on the current page")
        self.batch_process_button.clicked.connect(self.start_interactive_batch_detection)
        batch_row.addWidget(self.batch_process_button)
        bottom_v.addLayout(batch_row)
        self.on_batch_mode_changed(False)

        # ── Confirm/Cancel detection (hidden by default) ──────────────────────
        detect_row = QHBoxLayout()
        detect_row.setSpacing(6)
        self.confirm_items_button = QPushButton("✔ Confirm (0)")
        self.confirm_items_button.setObjectName("rp-confirm-btn")
        self.confirm_items_button.setText("Confirm (0)")
        self.confirm_items_button.clicked.connect(self.process_confirmed_detections)
        self.confirm_items_button.setVisible(False)
        detect_row.addWidget(self.confirm_items_button)
        self.cancel_detection_button = QPushButton("✕ Cancel")
        self.cancel_detection_button.setObjectName("rp-danger-btn")
        self.cancel_detection_button.setText("Cancel")
        self.cancel_detection_button.clicked.connect(self.cancel_interactive_batch)
        self.cancel_detection_button.setVisible(False)
        detect_row.addWidget(self.cancel_detection_button)
        bottom_v.addLayout(detect_row)

        # ── Edit action row ─────────────────────────────────────────────────────
        edit_row = QHBoxLayout()
        edit_row.setSpacing(6)
        self.undo_button = QPushButton("↩ Undo")
        self.undo_button.setObjectName("rp-action-btn")
        self.undo_button.setText("Undo")
        self.undo_button.clicked.connect(self.undo_last_action)
        self.undo_button.setEnabled(False)
        edit_row.addWidget(self.undo_button)

        self.redo_button = QPushButton("↪ Redo")
        self.redo_button.setObjectName("rp-action-btn")
        self.redo_button.setText("Redo")
        self.redo_button.clicked.connect(self.redo_last_action)
        self.redo_button.setEnabled(False)
        edit_row.addWidget(self.redo_button)

        self.reset_button = QPushButton("🔄 Reset")
        self.reset_button.setObjectName("rp-action-btn")
        self.reset_button.setText("Reset")
        self.reset_button.clicked.connect(self.reset_view_to_original)
        edit_row.addWidget(self.reset_button)

        self.save_button = QPushButton("💾 Save")
        self.save_button.setObjectName("rp-save-btn")
        self.save_button.setText("Save")
        self.save_button.clicked.connect(self.save_image)
        edit_row.addWidget(self.save_button)
        bottom_v.addLayout(edit_row)

        # ── Undo History Timeline (Feature #1) ──────────────────────────────────
        timeline_header = QHBoxLayout()
        timeline_header.setContentsMargins(2, 4, 2, 0)
        timeline_header.setSpacing(4)
        timeline_title_lbl = QLabel("🕐 History")
        timeline_title_lbl.setObjectName("rp-tiny-label")
        timeline_title_lbl.setText("History")
        timeline_header.addWidget(timeline_title_lbl)
        timeline_header.addStretch(1)
        self._timeline_clear_btn = QPushButton("✕")
        self._timeline_clear_btn.setObjectName("rp-action-btn")
        self._timeline_clear_btn.setText("x")
        self._timeline_clear_btn.setFixedSize(18, 18)
        self._timeline_clear_btn.setToolTip("Clear undo history")
        self._timeline_clear_btn.clicked.connect(self._clear_undo_history)
        timeline_header.addWidget(self._timeline_clear_btn)
        bottom_v.addLayout(timeline_header)

        self.undo_timeline_list = QListWidget()
        self.undo_timeline_list.setObjectName("undo-timeline")
        self.undo_timeline_list.setFixedHeight(110)
        self.undo_timeline_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.undo_timeline_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.undo_timeline_list.setStyleSheet(self._undo_timeline_qss())
        self.undo_timeline_list.itemClicked.connect(self._on_timeline_item_clicked)
        bottom_v.addWidget(self.undo_timeline_list)

        # ── Status metrics (compact 2-row grid) ─────────────────────────────────
        metrics_widget = QWidget()
        metrics_widget.setObjectName("rp-metrics")
        metrics_grid = QGridLayout(metrics_widget)
        metrics_grid.setContentsMargins(8, 6, 8, 6)
        metrics_grid.setHorizontalSpacing(8)
        metrics_grid.setVerticalSpacing(3)

        def _mlabel(text, bold=False):
            lbl = QLabel(text)
            lbl.setObjectName("rp-metric-key" if not bold else "rp-metric-val")
            return lbl

        # Row 0
        metrics_grid.addWidget(_mlabel("Workers"), 0, 0)
        self.active_workers_label = QLabel("0"); self.active_workers_label.setObjectName("rp-metric-val")
        metrics_grid.addWidget(self.active_workers_label, 0, 1)

        metrics_grid.addWidget(_mlabel("RPM"), 0, 2)
        self.rpm_label = QLabel("0/0"); self.rpm_label.setObjectName("rp-metric-val")
        metrics_grid.addWidget(self.rpm_label, 0, 3)

        metrics_grid.addWidget(_mlabel("RPD"), 0, 4)
        self.rpd_label = QLabel("0/0"); self.rpd_label.setObjectName("rp-metric-val")
        metrics_grid.addWidget(self.rpd_label, 0, 5)

        # Row 1
        metrics_grid.addWidget(_mlabel("Cost"), 1, 0)
        self.cost_label = QLabel("$0.0000"); self.cost_label.setObjectName("rp-cost-val")
        metrics_grid.addWidget(self.cost_label, 1, 1)

        metrics_grid.addWidget(_mlabel("IDR"), 1, 2)
        self.cost_idr_label = QLabel("Rp 0"); self.cost_idr_label.setObjectName("rp-metric-val")
        metrics_grid.addWidget(self.cost_idr_label, 1, 3)

        metrics_grid.addWidget(_mlabel("Snippets"), 1, 4)
        self.translated_label = QLabel("0"); self.translated_label.setObjectName("rp-metric-val")
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

        bottom_v.addWidget(metrics_widget)

        # ── Token rates (very small, collapsed to single row) ─────────────────
        token_row = QHBoxLayout()
        token_row.setSpacing(12)
        self.input_tokens_label = QLabel("In: 0 tok")
        self.input_tokens_label.setObjectName("rp-tiny-label")
        token_row.addWidget(self.input_tokens_label)
        self.output_tokens_label = QLabel("Out: 0 tok")
        self.output_tokens_label.setObjectName("rp-tiny-label")
        token_row.addWidget(self.output_tokens_label)
        self.rate_label_input = QLabel("$0.0000/in")
        self.rate_label_input.setObjectName("rp-tiny-label")
        token_row.addWidget(self.rate_label_input)
        self.rate_label_output = QLabel("$0.0000/out")
        self.rate_label_output.setObjectName("rp-tiny-label")
        token_row.addWidget(self.rate_label_output)
        token_row.addStretch()
        bottom_v.addLayout(token_row)

        # ── Cooldown label ───────────────────────────────────────────────────────
        self.countdown_label = QLabel("⏳ Cooldown: 60s")
        self.countdown_label.setObjectName("rp-countdown")
        self.countdown_label.setText("Cooldown: 60s")
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
                padding: 12px 10px 10px 10px;
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
                padding: 5px 10px;
                font-size: 9pt;
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
                padding: 5px 10px;
                font-size: 9pt;
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
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(14)

        # Auto-Detection Mode Group (NEW)
        detection_mode_group = QGroupBox("Auto-Detection Mode")
        detection_mode_layout = QHBoxLayout(detection_mode_group)
        self.bubble_detect_radio = QRadioButton("Bubble Detection")
        self.text_detect_radio = QRadioButton("Text Detection")
        self.bubble_detect_radio.setChecked(True) # Default
        detection_mode_layout.addWidget(self.bubble_detect_radio)
        detection_mode_layout.addWidget(self.text_detect_radio)
        layout.addWidget(detection_mode_group)

        selection_group = QGroupBox("Manual Selection Tool")
        selection_layout = QGridLayout(selection_group)
        
        selection_layout.addWidget(QLabel("Mode:"), 0, 0)
        self.selection_mode_combo = ScrollableComboBox(self)
        self.selection_mode_combo.addItems(SELECTION_MODE_LABELS)
        selection_layout.addWidget(self.selection_mode_combo, 0, 1, 1, 1)

        self.selection_mode_combo.currentTextChanged.connect(self.selection_mode_changed)
        pen_buttons_layout = QHBoxLayout()
        self.confirm_button = QPushButton("Confirm"); self.confirm_button.clicked.connect(self.confirm_pen_selection); self.confirm_button.setVisible(False)
        self.cancel_button = QPushButton("Cancel"); self.cancel_button.clicked.connect(self.cancel_pen_selection); self.cancel_button.setVisible(False)
        pen_buttons_layout.addWidget(self.confirm_button); pen_buttons_layout.addWidget(self.cancel_button)

        self.brush_controls_widget = QWidget()
        brush_layout = QHBoxLayout(self.brush_controls_widget)
        brush_layout.setContentsMargins(0, 0, 0, 0)
        brush_layout.addWidget(QLabel("Brush Size:"))
        self.brush_size_spinbox = QSpinBox()
        self.brush_size_spinbox.setRange(5, 200)
        self.brush_size_spinbox.setValue(25)
        self.brush_size_spinbox.valueChanged.connect(lambda val: self.image_label.set_inpaint_brush_size(val) if hasattr(self, 'image_label') else None)
        brush_layout.addWidget(self.brush_size_spinbox)
        self.inpaint_confirm_button = QPushButton("Confirm Clean")
        self.inpaint_confirm_button.clicked.connect(lambda: self.apply_inpaint_brush_selection(run_ocr_translate=self._is_inpaint_ocr_mode()))
        brush_layout.addWidget(self.inpaint_confirm_button)
        self.inpaint_clear_button = QPushButton("Clear Brush")
        self.inpaint_clear_button.clicked.connect(lambda: self.image_label.clear_inpaint_mask() if hasattr(self, 'image_label') else None)
        brush_layout.addWidget(self.inpaint_clear_button)
        self.inpaint_compare_button = QPushButton("Compare")
        self.inpaint_compare_button.setCheckable(True)
        self.inpaint_compare_button.setToolTip("Show the page before inpainting so OCR can read the original text.")
        self.inpaint_compare_button.toggled.connect(lambda checked: self.compare_mode_btn.setChecked(checked) if hasattr(self, 'compare_mode_btn') else None)
        brush_layout.addWidget(self.inpaint_compare_button)
        self.inpaint_cancel_button = QPushButton("X")
        self.inpaint_cancel_button.setToolTip("Cancel the saved inpainting result for this page.")
        self.inpaint_cancel_button.clicked.connect(self.cancel_inpaint_result)
        brush_layout.addWidget(self.inpaint_cancel_button)
        self.brush_controls_widget.setVisible(False)
        pen_buttons_layout.addWidget(self.brush_controls_widget)

        selection_layout.addLayout(pen_buttons_layout, 1, 0, 1, 2)

        self.create_bubble_checkbox = QCheckBox("Create white bubble with black outline")
        self.create_bubble_checkbox.setToolTip("When enabled, confirmed selections will render a bubble background behind the text.")
        selection_layout.addWidget(self.create_bubble_checkbox, 2, 0, 1, 2)
        # New: option to use a background box for rendered text (global cleanup option)
        self.use_background_box_checkbox = QCheckBox("Use Background Box for Text")
        # Initialize from saved SETTINGS if present
        self.use_background_box_checkbox.setChecked(bool(SETTINGS.get('cleanup', {}).get('use_background_box', True)))
        self.use_background_box_checkbox.setToolTip("When enabled, OCR/translated text will be placed inside a background box. If disabled, text is drawn directly over the image (transparent background).")
        selection_layout.addWidget(self.use_background_box_checkbox, 3, 0, 1, 2)

        self.constrain_text_checkbox = QCheckBox("Keep Text Inside Area")
        self.constrain_text_checkbox.setChecked(bool(SETTINGS.get('cleanup', {}).get('constrain_text', True)))
        self.constrain_text_checkbox.setToolTip("When enabled, text still wraps to the selected area when the background box is hidden. Turn off for one-line free text.")
        selection_layout.addWidget(self.constrain_text_checkbox, 4, 0, 1, 2)
        # Small control: apply mode (selected area vs global)
        apply_mode_layout = QHBoxLayout()
        self.apply_mode_selected_radio = QRadioButton("Apply to Selected Area")
        self.apply_mode_global_radio = QRadioButton("Apply Globally")
        # Restore saved apply mode if present in SETTINGS
        saved_mode = self._default_cleanup_value('apply_mode') or 'selected'
        if saved_mode == 'global':
            self.apply_mode_global_radio.setChecked(True)
        else:
            self.apply_mode_selected_radio.setChecked(True)
        apply_mode_layout.addWidget(self.apply_mode_selected_radio)
        apply_mode_layout.addWidget(self.apply_mode_global_radio)
        # small status label to show which mode is active
        self.apply_mode_status_label = QLabel()
        def _update_apply_mode_label():
            if self.apply_mode_global_radio.isChecked():
                self.apply_mode_status_label.setText("Mode: Global")
            else:
                self.apply_mode_status_label.setText("Mode: Selected Area")
        _update_apply_mode_label()
        apply_mode_layout.addWidget(self.apply_mode_status_label)
        selection_layout.addLayout(apply_mode_layout, 5, 0, 1, 2)

        # Apply to All Areas button
        self.apply_all_button = QPushButton("Apply to All Areas")
        self.apply_all_button.setToolTip("Apply the selected action either to update defaults only or force update every existing area.")
        def _on_apply_all_clicked():
            # Dialog with two choices
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox

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
                self._set_global_cleanup_default('use_background_box', use_box_val)
                constrain_text_val = bool(self.constrain_text_checkbox.isChecked())
                self._set_global_cleanup_default('use_inpaint', use_inpaint_val)
                self._set_global_cleanup_default('constrain_text', constrain_text_val)
                self.show_toast("Apply to all", "Global defaults updated. Existing areas keep their individual overrides.", kind="success")
                self._sync_cleanup_controls_from_selection()
                dlg.accept()

            def _force_update_all():
                use_box_val = bool(self.use_background_box_checkbox.isChecked())
                use_inpaint_val = bool(self.inpaint_checkbox.isChecked())
                self._set_global_cleanup_default('use_background_box', use_box_val)
                constrain_text_val = bool(self.constrain_text_checkbox.isChecked())
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
        selection_layout.addWidget(self.apply_all_button, 6, 0, 1, 2)

        # Whenever apply-mode is toggled, save to SETTINGS
        def _on_apply_mode_changed():
            mode = 'global' if self.apply_mode_global_radio.isChecked() else 'selected'
            self._set_global_cleanup_default('apply_mode', mode)
            _update_apply_mode_label()
            self._sync_cleanup_controls_from_selection()
        self.apply_mode_selected_radio.toggled.connect(_on_apply_mode_changed)
        self.apply_mode_global_radio.toggled.connect(_on_apply_mode_changed)

        # When user toggles the checkbox in the Cleanup tab, update either the hovered area or global default depending on apply mode
        def on_tab_checkbox_toggled(state):
            self._apply_cleanup_change('use_background_box', bool(state))
        self.use_background_box_checkbox.toggled.connect(on_tab_checkbox_toggled)

        def on_constrain_text_toggled(state):
            self._apply_cleanup_change('constrain_text', bool(state))
        self.constrain_text_checkbox.toggled.connect(on_constrain_text_toggled)
        layout.addWidget(selection_group)
        
        # [DIUBAH] Inpainting Group dengan model baru
        inpaint_group = QGroupBox("Inpainting (Text Removal)")
        inpaint_layout = QGridLayout(inpaint_group)
        self.inpaint_checkbox = QCheckBox("Gunakan Inpainting")
        # Initialize from SETTINGS default if present
        self.inpaint_checkbox.setChecked(bool(SETTINGS.get('cleanup', {}).get('use_inpaint', True)))
        inpaint_layout.addWidget(self.inpaint_checkbox, 0, 0, 1, 2)

        inpaint_models = ["IOPaint Server", "OpenCV-NS", "OpenCV-Telea"]
        if self.is_lama_available:
            if os.path.exists(self.dl_models['big_lama']['path']):
                inpaint_models.append("Big-LaMa")
            if os.path.exists(self.dl_models['anime_inpaint']['path']):
                inpaint_models.append("Anime-Inpainting")
        
        self.inpaint_model_combo = self._create_combo_box(inpaint_layout, "Model:", inpaint_models, 1, 0)
        self.inpaint_padding_spinbox = self._create_spin_box(inpaint_layout, "Padding (px):", 1, 25, 5, 2, 0)
        # When toggling inpaint checkbox, respect apply mode selection
        def on_inpaint_toggled(state):
            self._apply_cleanup_change('use_inpaint', bool(state))
        self.inpaint_checkbox.toggled.connect(on_inpaint_toggled)
        layout.addWidget(inpaint_group)

        # Ensure UI reflects either selected area overrides or global defaults
        self._sync_cleanup_controls_from_selection()

        dl_detect_group = QGroupBox("Bubble Detector Model (Advanced)")
        dl_layout = QGridLayout(dl_detect_group)
        self.dl_bubble_detector_checkbox = QCheckBox("Gunakan DL Model untuk Bubble"); dl_layout.addWidget(self.dl_bubble_detector_checkbox, 0, 0, 1, 2)
        self.dl_model_provider_combo = self._create_combo_box(dl_layout, "Provider:", ["Kitsumed", "Ogkalu"], 1, 0)
        self.dl_model_file_combo = self._create_combo_box(dl_layout, "Model:", [], 2, 0)
        self.split_bubbles_checkbox = QCheckBox("Otomatis Pisahkan Bubble Panjang")
        dl_layout.addWidget(self.split_bubbles_checkbox, 3, 0, 1, 2)
        self.dl_bubble_detector_checkbox.stateChanged.connect(self.on_dl_detector_state_changed)
        self.dl_model_provider_combo.currentTextChanged.connect(self.on_dl_provider_changed)
        layout.addWidget(dl_detect_group)
        self.on_dl_provider_changed(self.dl_model_provider_combo.currentText())

        # Panel & RTL Reader Group (NEW)
        panel_group = QGroupBox("Panel & RTL Reader (Advanced)")
        panel_layout = QGridLayout(panel_group)
        
        self.panel_model_path_input = QLineEdit()
        self.panel_model_path_input.setPlaceholderText("Default YOLO26 model path")
        self.panel_model_path_input.setText(SETTINGS.get('cleanup', {}).get('panel_model_path', ''))
        self.panel_model_path_input.textChanged.connect(self.on_panel_model_path_changed)
        
        browse_panel_btn = QPushButton("Browse")
        browse_panel_btn.clicked.connect(self.browse_panel_model)
        
        self.show_panels_checkbox = QCheckBox("Tampilkan Batas Panel (Debug)")
        self.show_panels_checkbox.setChecked(False)
        self.show_panels_checkbox.stateChanged.connect(self.on_show_panels_changed)
        
        detect_panels_btn = QPushButton("Auto-Detect Panels")
        detect_panels_btn.clicked.connect(self.detect_panels_yolo)
        
        sort_rtl_btn = QPushButton("Sort RTL")
        sort_rtl_btn.clicked.connect(self.sort_areas_rtl)
        
        panel_layout.addWidget(QLabel("YOLO Model:"), 0, 0)
        panel_layout.addWidget(self.panel_model_path_input, 0, 1)
        panel_layout.addWidget(browse_panel_btn, 0, 2)
        panel_layout.addWidget(self.show_panels_checkbox, 1, 0, 1, 3)
        panel_layout.addWidget(detect_panels_btn, 2, 0, 1, 1)
        panel_layout.addWidget(sort_rtl_btn, 2, 1, 1, 2)
        
        layout.addWidget(panel_group)

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
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(14)

        # ── AI Model & Translation ────────────────────────────────────────────
        ai_group = QGroupBox("AI Models & Translation")
        ai_form = QFormLayout(ai_group)
        ai_form.setContentsMargins(12, 16, 12, 12)
        ai_form.setSpacing(10)
        ai_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        ai_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.ai_model_combo = QComboBox()
        self.ai_model_combo.currentTextChanged.connect(self.on_ai_model_changed)
        ai_form.addRow("AI Model:", self.ai_model_combo)

        self.style_combo = QComboBox()
        self.style_combo.addItems(self.translation_styles)
        default_style = SETTINGS.get('general', {}).get('default_translation_style', 'Santai (Default)')
        if default_style in self.translation_styles:
            self.style_combo.setCurrentText(default_style)
        ai_form.addRow("Style:", self.style_combo)

        layout.addWidget(ai_group)

        # ── Custom Styles ─────────────────────────────────────────────────────
        custom_style_group = QGroupBox("Custom Styles")
        cs_layout = QVBoxLayout(custom_style_group)
        cs_layout.setContentsMargins(12, 14, 12, 12)
        cs_layout.setSpacing(8)

        style_row = QHBoxLayout()
        self.style_input = QLineEdit(self)
        self.style_input.setPlaceholderText("New style name...")
        style_row.addWidget(self.style_input, 1)
        add_style_btn = QPushButton("+ Add")
        add_style_btn.clicked.connect(lambda: (self.add_custom_style(self.style_input.text()) and self.style_input.clear()))
        style_row.addWidget(add_style_btn)
        remove_style_btn = QPushButton("Remove")
        remove_style_btn.clicked.connect(lambda: self.remove_selected_style())
        style_row.addWidget(remove_style_btn)
        cs_layout.addLayout(style_row)

        layout.addWidget(custom_style_group)

        # ── Processing Modes ─────────────────────────────────────────────────
        mode_group = QGroupBox("Processing Modes")
        mode_v = QVBoxLayout(mode_group)
        mode_v.setContentsMargins(12, 14, 12, 12)
        mode_v.setSpacing(8)

        self.enhanced_pipeline_checkbox = QCheckBox("Enhanced Pipeline  (JP Only · More API)")
        self.enhanced_pipeline_checkbox.stateChanged.connect(self.on_pipeline_mode_changed)
        mode_v.addWidget(self.enhanced_pipeline_checkbox)

        self.ai_only_translate_checkbox = QCheckBox("AI-Only Translate")
        self.ai_only_translate_checkbox.stateChanged.connect(self.on_translation_mode_changed)
        mode_v.addWidget(self.ai_only_translate_checkbox)

        self.deepl_only_checkbox = QCheckBox("DeepL-Only Translate")
        self.deepl_only_checkbox.stateChanged.connect(self.on_translation_mode_changed)
        mode_v.addWidget(self.deepl_only_checkbox)

        self.safe_mode_checkbox = QCheckBox("Safe Mode  (Filter Adult Content)")
        mode_v.addWidget(self.safe_mode_checkbox)

        self.batch_mode_checkbox = QCheckBox("Enable Batch Processing")
        self.batch_mode_checkbox.stateChanged.connect(self.on_batch_mode_changed)
        mode_v.addWidget(self.batch_mode_checkbox)

        layout.addWidget(mode_group)

        # ── Hardware & Performance ────────────────────────────────────────────
        hardware_group = QGroupBox("Hardware & Performance")
        hw_form = QFormLayout(hardware_group)
        hw_form.setContentsMargins(12, 16, 12, 12)
        hw_form.setSpacing(10)
        hw_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        hw_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        # GPU row with status indicator
        gpu_row = QHBoxLayout()
        self.use_gpu_checkbox = QCheckBox("Enable GPU")
        self.use_gpu_checkbox.setChecked(self.is_gpu_available)
        self.use_gpu_checkbox.setEnabled(self.is_gpu_available)
        if not self.is_gpu_available:
            self.use_gpu_checkbox.setToolTip("Tidak ada GPU NVIDIA yang terdeteksi.")
        self.use_gpu_checkbox.stateChanged.connect(self.update_gpu_status_label)
        gpu_row.addWidget(self.use_gpu_checkbox)
        gpu_row.addStretch()
        self.gpu_status_label = QLabel("● GPU OK" if self.is_gpu_available else "● No GPU")
        self.gpu_status_label.setObjectName("gpu-status")
        self.gpu_status_label.setStyleSheet(
            "color: #4ade80; font-weight:700; font-size:9pt;" if self.is_gpu_available
            else "color: #f87171; font-weight:700; font-size:9pt;"
        )
        gpu_row.addWidget(self.gpu_status_label)
        hw_form.addRow("Accel:", gpu_row)

        self.max_workers_spinbox = QSpinBox()
        self.max_workers_spinbox.setRange(1, 50)
        self.max_workers_spinbox.setValue(self.MAX_WORKERS)
        self.max_workers_spinbox.valueChanged.connect(self.on_max_workers_changed)
        hw_form.addRow("Max Workers:", self.max_workers_spinbox)

        self.spawn_threshold_spinbox = QSpinBox()
        self.spawn_threshold_spinbox.setRange(1, 10)
        self.spawn_threshold_spinbox.setValue(self.WORKER_SPAWN_THRESHOLD)
        self.spawn_threshold_spinbox.valueChanged.connect(self.on_spawn_threshold_changed)
        hw_form.addRow("Spawn Threshold:", self.spawn_threshold_spinbox)

        layout.addWidget(hardware_group)

        self.update_gpu_status_label()
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
            QScrollArea, QFrame, QSizePolicy, QGridLayout
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
        header_lbl = QLabel("📖 MangaTranslate")
        header_lbl.setAlignment(Qt.AlignCenter)
        header_lbl.setStyleSheet(f"""
            color: {theme.COLORS["text"]};
            font-size: 32pt;
            font-weight: 800;
            font-family: {theme.FONT_FAMILY};
            letter-spacing: 1px;
            margin-bottom: 4px;
        """)
        vbox.addWidget(header_lbl)

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

        def make_action_btn(icon, label, slot, color_start, color_end, border_color):
            btn = QPushButton()
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setFixedHeight(90)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {color_start}, stop:1 {color_end});
                    border: 1px solid {border_color};
                    border-radius: 12px;
                    color: {theme.COLORS["text"]};
                    font-size: 10pt;
                    font-weight: 600;
                    font-family: {theme.FONT_FAMILY};
                    padding: 8px;
                    text-align: center;
                }}
                QPushButton:hover {{
                    border: 1px solid {theme.COLORS["accent"]};
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {theme.COLORS["card_alt"]}, stop:1 {theme.COLORS["panel"]});
                }}
                QPushButton:pressed {{
                    background: {theme.COLORS["border"]};
                }}
            """)
            btn.setText(f"{icon}\n{label}")
            btn.clicked.connect(slot)
            return btn

        btn_folder = make_action_btn(
            "📁", "Open Folder",
            self.load_folder,
            theme.COLORS["card_alt"], theme.COLORS["panel"], theme.COLORS["border"]
        )
        btn_project = make_action_btn(
            "🗂️", "Load Project",
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
