"""Method domain typeset, dipindahkan utuh dari main_window.py.

Fase 1 pemecahan monolit: isi method tidak diubah sama sekali.
Mixin ini hanya berguna sebagai bagian dari MangaOCRApp -- ia mengandalkan
atribut yang dibuat di MangaOCRApp.__init__.
"""

from src.ui.main_window_mixins._imports import *  # noqa: F401,F403


class TypesetMixin:
    def _apply_active_typeset_to_selected(self):
        area = self.selected_typeset_area
        if not area:
            return
            
        # Build current font info
        font = self._build_current_font()
        area.font_info = area.font_to_dict(font)
        if hasattr(self, 'typeset_color'):
            new_color = QColor(self.typeset_color)
            old_color = QColor(getattr(area, 'color_info', '#000000'))
            if new_color.isValid():
                if not old_color.isValid() or old_color.name() != new_color.name():
                    self._apply_manual_text_color_to_area(area, new_color)
                else:
                    area.color_info = new_color.name()
        if hasattr(self, 'typeset_line_spacing_value'):
            area.line_spacing = self.typeset_line_spacing_value
        if hasattr(self, 'typeset_char_spacing_value'):
            area.char_spacing = self.typeset_char_spacing_value
        if hasattr(self, 'typeset_alignment'):
            area.alignment = self.typeset_alignment
        if hasattr(self, 'typeset_orientation'):
            area.orientation = self.typeset_orientation
        if hasattr(self, 'typeset_outline_enabled'):
            area.text_outline = self.typeset_outline_enabled
            area.text_outline_width = self.typeset_outline_width
            area.text_outline_color = self.typeset_outline_color.name() if isinstance(self.typeset_outline_color, QColor) else str(self.typeset_outline_color)
            area.text_outline_style = self.typeset_outline_style

        if hasattr(self, 'warp_style_combo'):
            area.effect = self.warp_style_combo.currentText().lower()
        if hasattr(self, 'warp_intensity_slider'):
            area.effect_intensity = float(self.warp_intensity_slider.value())
        if hasattr(self, 'typeset_curve_editor') and area.effect == 'curved':
            cp1 = self.typeset_curve_editor.cp1
            cp2 = self.typeset_curve_editor.cp2
            area.bezier_points = [{'x': cp1.x(), 'y': cp1.y()}, {'x': cp2.x(), 'y': cp2.y()}]

        if hasattr(self, 'gradient_group'):
            area.gradient_enabled = bool(self.gradient_group.isChecked())
            area.gradient_colors = list(self.typeset_gradient_colors or ["#ffffff", "#000000"])
            if hasattr(self, 'grad_angle_spin'):
                area.gradient_angle = self.grad_angle_spin.value()
            
        self.redraw_all_typeset_areas()

    def _sync_typeset_controls_from_selection(self):
        area = self.selected_typeset_area
        if not area:
            if getattr(self, 'backup_typeset_settings', None) is not None:
                self._apply_typeset_settings(self.backup_typeset_settings)
                self.backup_typeset_settings = None
            else:
                self._apply_typeset_defaults()
            return

        # Synchronize color
        if hasattr(self, 'typeset_color') and area.color_info:
            self.typeset_color = QColor(area.color_info)
            self._update_color_button()

        # Synchronize font family and size
        if hasattr(self, 'font_dropdown'):
            font_family = area.font_info.get('family', 'Arial')
            idx = self.font_dropdown.findText(font_family)
            if idx != -1:
                with QSignalBlocker(self.font_dropdown):
                    self.font_dropdown.setCurrentIndex(idx)

        if hasattr(self, 'font_size_spin'):
            with QSignalBlocker(self.font_size_spin):
                font_size = area.font_info.get('pointSize', area.font_info.get('size'))
                if font_size is None:
                    font_size = SETTINGS.get('general', {}).get('default_font_size', 14)
                self.font_size_spin.setValue(float(font_size))

        if hasattr(self, 'bold_toggle'):
            with QSignalBlocker(self.bold_toggle):
                is_bold = bool(area.font_info.get('bold', False)) or (area.font_info.get('weight', QFont.Normal) >= QFont.Bold)
                self.bold_toggle.setChecked(is_bold)

        if hasattr(self, 'italic_toggle'):
            with QSignalBlocker(self.italic_toggle):
                self.italic_toggle.setChecked(bool(area.font_info.get('italic', False)))

        if hasattr(self, 'underline_toggle'):
            with QSignalBlocker(self.underline_toggle):
                self.underline_toggle.setChecked(bool(area.font_info.get('underline', False)))

        if hasattr(self, 'line_spacing_input'):
            with QSignalBlocker(self.line_spacing_input):
                self.line_spacing_input.setValue(area.line_spacing)

        if hasattr(self, 'char_spacing_input'):
            with QSignalBlocker(self.char_spacing_input):
                self.char_spacing_input.setValue(area.char_spacing)

        # Synchronize layout buttons
        if hasattr(self, 'typeset_alignment'):
            self.typeset_alignment = area.alignment
            self._update_alignment_buttons()

        if hasattr(self, 'typeset_orientation'):
            self.typeset_orientation = area.orientation
            self._update_orientation_buttons()

        # Outline group
        if hasattr(self, 'outline_toggle'):
            with QSignalBlocker(self.outline_toggle):
                self.outline_toggle.setChecked(bool(area.text_outline))
                self.typeset_outline_enabled = bool(area.text_outline)
                self.typeset_outline_width = area.text_outline_width
                self.typeset_outline_color = QColor(area.text_outline_color)
                self.typeset_outline_style = area.text_outline_style
                self._refresh_outline_controls_enabled()

        # Gradient group
        if hasattr(self, 'gradient_group'):
            with QSignalBlocker(self.gradient_group):
                self.gradient_group.setChecked(bool(area.gradient_enabled))
                self.typeset_gradient_enabled = bool(area.gradient_enabled)
                self.typeset_gradient_colors = list(area.gradient_colors or ["#ffffff", "#000000"])
                self.typeset_gradient_angle = area.gradient_angle
                self._update_gradient_list_ui(self.typeset_gradient_colors)
        if hasattr(self, 'grad_angle_spin'):
            with QSignalBlocker(self.grad_angle_spin):
                self.grad_angle_spin.setValue(area.gradient_angle)

        # Warp group
        if hasattr(self, 'warp_style_combo'):
            style_text = (getattr(area, 'effect', 'none') or 'none').capitalize()
            idx = self.warp_style_combo.findText(style_text)
            if idx != -1:
                with QSignalBlocker(self.warp_style_combo):
                    self.warp_style_combo.setCurrentIndex(idx)
            if hasattr(self, 'typeset_curve_editor'):
                self.typeset_curve_editor.setVisible(style_text.lower() == 'curved')

        if hasattr(self, 'warp_intensity_slider'):
            with QSignalBlocker(self.warp_intensity_slider):
                val = int(getattr(area, 'effect_intensity', 20.0))
                self.warp_intensity_slider.setValue(val)
                self.warp_intensity_value_label.setText(f"{float(val):.1f}")

        if hasattr(self, 'typeset_curve_editor') and getattr(area, 'bezier_points', None):
            bezier = area.get_bezier_points()
            if len(bezier) >= 2:
                with QSignalBlocker(self.typeset_curve_editor):
                    self.typeset_curve_editor.set_control_points(
                        bezier[0].get('x', 0.25),
                        bezier[0].get('y', 0.2),
                        bezier[1].get('x', 0.75),
                        bezier[1].get('y', 0.2)
                    )

    def _create_typeset_tab_legacy(self):
        """Legacy placeholder retained for backward compatibility."""
        return self._create_typeset_tab()

    def _create_typeset_tab(self):
        scroll = QScrollArea()
        self._configure_workspace_scroll_area(scroll)

        container = QWidget()
        container.setMinimumWidth(0)
        container.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        # ── Defaults card ──
        defaults_group = QGroupBox("Defaults")
        defaults_layout = QVBoxLayout(defaults_group)
        defaults_layout.setContentsMargins(12, 14, 12, 12)
        defaults_layout.setSpacing(10)

        defaults_description = QLabel("Save your current typography to reuse it on future text areas or restore the previously stored default.")
        defaults_description.setWordWrap(True)
        defaults_description.setStyleSheet("color: #8fa6c5; font-size: 8.5pt;")
        defaults_layout.addWidget(defaults_description)

        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)
        self.save_typeset_defaults_button = QPushButton("Save")
        self.save_typeset_defaults_button.setToolTip("Store the current typography as the default for new areas.")
        self.save_typeset_defaults_button.clicked.connect(self._handle_save_typeset_defaults)
        actions_layout.addWidget(self.save_typeset_defaults_button, 1)
        self.reset_typeset_defaults_button = QPushButton("Reset")
        self.reset_typeset_defaults_button.setToolTip("Restore the saved default typography settings.")
        self.reset_typeset_defaults_button.clicked.connect(self._handle_reset_typeset_defaults)
        actions_layout.addWidget(self.reset_typeset_defaults_button, 1)
        defaults_layout.addLayout(actions_layout)
        layout.addWidget(defaults_group)

        # ── Typography card ──
        font_group = QGroupBox("Typography")
        font_layout = QGridLayout(font_group)
        font_layout.setContentsMargins(12, 14, 12, 12)
        font_layout.setHorizontalSpacing(10)
        font_layout.setVerticalSpacing(10)
        font_layout.setColumnStretch(1, 1)

        font_layout.addWidget(QLabel("Font Group"), 0, 0)
        self.font_group_combo = QComboBox()
        self.font_group_combo.addItem("All")
        for group_name in getattr(self, 'font_groups', {}).keys():
            self.font_group_combo.addItem(group_name)
        self._fit_workspace_combo(self.font_group_combo, 14)
        self.font_group_combo.currentTextChanged.connect(lambda txt: self._on_font_group_changed(txt))
        font_layout.addWidget(self.font_group_combo, 0, 1)

        group_btn_layout = QHBoxLayout()
        group_btn_layout.setSpacing(6)
        self.add_group_btn = QPushButton("New")
        self.add_group_btn.setToolTip("Create a new font group.")
        self.add_group_btn.clicked.connect(self._on_add_font_group_clicked)
        group_btn_layout.addWidget(self.add_group_btn)
        self.remove_group_btn = QPushButton("Delete")
        self.remove_group_btn.setToolTip("Remove the selected font group.")
        self.remove_group_btn.clicked.connect(self._on_remove_font_group_clicked)
        group_btn_layout.addWidget(self.remove_group_btn)
        self.add_font_to_group_btn = QPushButton("Add Font")
        self.add_font_to_group_btn.setText("Add")
        self.add_font_to_group_btn.setToolTip("Add a font to the selected group.")
        self.add_font_to_group_btn.clicked.connect(self._on_add_font_to_group_clicked)
        group_btn_layout.addWidget(self.add_font_to_group_btn)
        font_layout.addLayout(group_btn_layout, 1, 0, 1, 2)

        font_layout.addWidget(QLabel("Family"), 2, 0)
        self.font_dropdown = QComboBox()
        from src.ui.widgets import FontDelegate
        self.font_dropdown.setItemDelegate(FontDelegate(self.font_manager, self.font_dropdown))
        self._fit_workspace_combo(self.font_dropdown, 16)
        self.font_dropdown.currentTextChanged.connect(self.on_typeset_font_change)
        font_layout.addWidget(self.font_dropdown, 2, 1)

        self.import_font_button = QPushButton("Import Font...")
        self.import_font_button.setToolTip("Add new font files from your computer (TTF, OTF, TTC, OTC).")
        self.import_font_button.clicked.connect(self.import_font)
        font_layout.addWidget(self.import_font_button, 3, 0, 1, 2)

        font_layout.addWidget(QLabel("Preview"), 4, 0)
        self.font_preview_label = QLabel("AaBb123")
        self.font_preview_label.setAlignment(Qt.AlignCenter)
        self.font_preview_label.setMinimumHeight(56)
        self.font_preview_label.setMinimumWidth(0)
        self.font_preview_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.font_preview_label.setStyleSheet(self._preview_label_qss())
        font_layout.addWidget(self.font_preview_label, 4, 1)

        self.auto_font_checkbox = QCheckBox("Enable Auto-Font (Smart)")
        self.auto_font_checkbox.setToolTip("Automatically selects the best font based on the translated text.")
        auto_font_enabled = SETTINGS.get('typeset', {}).get('auto_font_enabled', False)
        self.auto_font_checkbox.setChecked(auto_font_enabled)
        self.auto_font_checkbox.toggled.connect(self._on_auto_font_toggled)
        font_layout.addWidget(self.auto_font_checkbox, 5, 0, 1, 2)
        
        layout.addWidget(font_group)

        # ── Appearance card ──
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QGridLayout(appearance_group)
        appearance_layout.setContentsMargins(12, 14, 12, 12)
        appearance_layout.setHorizontalSpacing(10)
        appearance_layout.setVerticalSpacing(10)
        appearance_layout.setColumnStretch(1, 1)

        appearance_layout.addWidget(QLabel("Style"), 0, 0)
        style_row = QHBoxLayout()
        style_row.setSpacing(6)
        self.bold_toggle = self._create_tool_toggle(self._make_style_icon('B'), "Bold")
        self.bold_toggle.toggled.connect(self._on_typeset_style_changed)
        style_row.addWidget(self.bold_toggle)
        self.italic_toggle = self._create_tool_toggle(self._make_style_icon('I'), "Italic")
        self.italic_toggle.toggled.connect(self._on_typeset_style_changed)
        style_row.addWidget(self.italic_toggle)
        self.underline_toggle = self._create_tool_toggle(self._make_style_icon('U'), "Underline")
        self.underline_toggle.toggled.connect(self._on_typeset_style_changed)
        style_row.addWidget(self.underline_toggle)
        style_row.addStretch(1)
        appearance_layout.addLayout(style_row, 0, 1)

        appearance_layout.addWidget(QLabel("Text Color"), 1, 0)
        color_row = QHBoxLayout()
        color_row.setSpacing(6)
        self.color_button = QPushButton("Pick Color")
        self.color_button.setMaximumWidth(120)
        self.color_button.clicked.connect(self.choose_color)
        self.color_button.setToolTip("Pick the color used for new text areas.")
        color_row.addWidget(self.color_button)
        color_row.addStretch(1)
        appearance_layout.addLayout(color_row, 1, 1)

        appearance_layout.addWidget(QLabel("Outline"), 2, 0)
        outline_toggle_row = QHBoxLayout()
        outline_toggle_row.setSpacing(6)
        self.outline_toggle = self._create_tool_toggle(self._make_outline_icon(), "Toggle outline")
        self.outline_toggle.toggled.connect(self._on_typeset_outline_changed)
        outline_toggle_row.addWidget(self.outline_toggle)
        outline_toggle_row.addStretch(1)
        appearance_layout.addLayout(outline_toggle_row, 2, 1)

        appearance_layout.addWidget(QLabel("Outline Color"), 3, 0)
        outline_color_row = QHBoxLayout()
        outline_color_row.setSpacing(6)
        self.outline_color_button = QPushButton("Outline Color")
        self.outline_color_button.setMaximumWidth(120)
        self.outline_color_button.clicked.connect(self.choose_outline_color)
        outline_color_row.addWidget(self.outline_color_button)
        outline_color_row.addStretch(1)
        appearance_layout.addLayout(outline_color_row, 3, 1)

        appearance_layout.addWidget(QLabel("Outline Width"), 4, 0)
        outline_width_row = QHBoxLayout()
        outline_width_row.setSpacing(6)
        self.outline_width_spin = QDoubleSpinBox()
        self.outline_width_spin.setRange(0.0, 12.0)
        self.outline_width_spin.setDecimals(1)
        self.outline_width_spin.setSingleStep(0.1)
        self.outline_width_spin.setSuffix(" px")
        self.outline_width_spin.setMaximumWidth(100)
        self.outline_width_spin.valueChanged.connect(self._on_outline_width_changed)
        outline_width_row.addWidget(self.outline_width_spin)
        outline_width_row.addStretch(1)
        appearance_layout.addLayout(outline_width_row, 4, 1)

        layout.addWidget(appearance_group)

        # ── Gradient card ──
        gradient_group = QGroupBox("Gradient Coloring")
        gradient_group.setCheckable(True)
        self.gradient_group = gradient_group
        self.gradient_group.toggled.connect(self._on_typeset_gradient_toggled)
        
        grad_layout = QVBoxLayout(gradient_group)
        grad_layout.setContentsMargins(12, 14, 12, 12)
        grad_layout.setSpacing(10)

        angle_row = QHBoxLayout()
        angle_row.addWidget(QLabel("Angle:"))
        self.grad_angle_spin = QDoubleSpinBox()
        self.grad_angle_spin.setRange(0.0, 360.0)
        self.grad_angle_spin.setSingleStep(15.0)
        self.grad_angle_spin.setSuffix(" °")
        self.grad_angle_spin.setMaximumWidth(100)
        self.grad_angle_spin.valueChanged.connect(self._on_typeset_gradient_changed)
        angle_row.addWidget(self.grad_angle_spin)
        angle_row.addStretch(1)
        grad_layout.addLayout(angle_row)
        
        grad_layout.addWidget(QLabel("Colors:"))
        self.grad_color_list = QListWidget()
        self.grad_color_list.setFixedHeight(80)
        self.grad_color_list.setMinimumWidth(0)
        self.grad_color_list.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        grad_layout.addWidget(self.grad_color_list)
        
        btn_row = QHBoxLayout()
        add_c_btn = QPushButton("Add")
        add_c_btn.clicked.connect(self._on_add_gradient_color)
        rem_c_btn = QPushButton("Remove")
        rem_c_btn.clicked.connect(self._on_remove_gradient_color)
        btn_row.addWidget(add_c_btn)
        btn_row.addWidget(rem_c_btn)
        grad_layout.addLayout(btn_row)
        
        layout.addWidget(gradient_group)

        # ── Spacing & Size card ──
        spacing_group = QGroupBox("Spacing & Size")
        spacing_layout = QGridLayout(spacing_group)
        spacing_layout.setContentsMargins(12, 14, 12, 12)
        spacing_layout.setHorizontalSpacing(10)
        spacing_layout.setVerticalSpacing(10)
        spacing_layout.setColumnStretch(1, 1)

        spacing_layout.addWidget(QLabel("Font Size"), 0, 0)
        self.font_size_spin = QDoubleSpinBox()
        self.font_size_spin.setRange(4.0, 220.0)
        self.font_size_spin.setDecimals(1)
        self.font_size_spin.setSingleStep(1.0)
        self.font_size_spin.setSuffix(" pt")
        self.font_size_spin.setMaximumWidth(100)
        self.font_size_spin.valueChanged.connect(self._on_typeset_font_size_changed)
        self.font_size_spin.setToolTip("Adjust the point size for new text areas.")
        spacing_layout.addWidget(self.font_size_spin, 0, 1)

        spacing_layout.addWidget(QLabel("Line Spacing"), 1, 0)
        line_row = QHBoxLayout()
        line_row.setSpacing(8)
        self.line_spacing_input = QDoubleSpinBox()
        self.line_spacing_input.setRange(0.6, 3.0)
        self.line_spacing_input.setDecimals(2)
        self.line_spacing_input.setSingleStep(0.05)
        self.line_spacing_input.setMaximumWidth(100)
        self.line_spacing_input.setToolTip("Adjust the spacing between lines (0.60x - 3.00x).")
        self.line_spacing_input.valueChanged.connect(self._on_typeset_line_spacing_changed)
        line_row.addWidget(self.line_spacing_input)
        self.line_spacing_value_label = QLabel("1.00x")
        self.line_spacing_value_label.setMinimumWidth(50)
        line_row.addWidget(self.line_spacing_value_label)
        line_row.addStretch(1)
        spacing_layout.addLayout(line_row, 1, 1)

        spacing_layout.addWidget(QLabel("Char Spacing"), 2, 0)
        char_row = QHBoxLayout()
        char_row.setSpacing(8)
        self.char_spacing_input = QDoubleSpinBox()
        self.char_spacing_input.setRange(10.0, 400.0)
        self.char_spacing_input.setDecimals(0)
        self.char_spacing_input.setSingleStep(1.0)
        self.char_spacing_input.setSuffix(" %")
        self.char_spacing_input.setMaximumWidth(100)
        self.char_spacing_input.setToolTip("Adjust spacing between characters (percentage).")
        self.char_spacing_input.valueChanged.connect(self._on_typeset_char_spacing_changed)
        char_row.addWidget(self.char_spacing_input)
        self.char_spacing_value_label = QLabel("100%")
        self.char_spacing_value_label.setMinimumWidth(50)
        char_row.addWidget(self.char_spacing_value_label)
        char_row.addStretch(1)
        spacing_layout.addLayout(char_row, 2, 1)
        layout.addWidget(spacing_group)

        # ── Layout card ──
        layout_group = QGroupBox("Layout")
        layout_grid = QGridLayout(layout_group)
        layout_grid.setContentsMargins(12, 14, 12, 12)
        layout_grid.setHorizontalSpacing(10)
        layout_grid.setVerticalSpacing(10)
        layout_grid.setColumnStretch(1, 1)

        layout_grid.addWidget(QLabel("Alignment"), 0, 0)
        alignment_row = QHBoxLayout()
        alignment_row.setSpacing(6)
        self.alignment_group = QButtonGroup(self)
        self.alignment_group.setExclusive(True)
        self.align_left_button = self._create_tool_toggle(self._make_alignment_icon('left'), "Align left")
        self.align_center_button = self._create_tool_toggle(self._make_alignment_icon('center'), "Align center")
        self.align_right_button = self._create_tool_toggle(self._make_alignment_icon('right'), "Align right")
        for mode, button in (('left', self.align_left_button), ('center', self.align_center_button), ('right', self.align_right_button)):
            button.setCheckable(True)
            button.setProperty('align-mode', mode)
            self.alignment_group.addButton(button)
            button.toggled.connect(self._on_alignment_button_toggled)
            alignment_row.addWidget(button)
        alignment_row.addStretch(1)
        layout_grid.addLayout(alignment_row, 0, 1)

        layout_grid.addWidget(QLabel("Orientation"), 1, 0)
        orientation_row = QHBoxLayout()
        orientation_row.setSpacing(6)
        self.orientation_group = QButtonGroup(self)
        self.orientation_group.setExclusive(True)
        self.orientation_horizontal_button = self._create_tool_toggle(self._make_orientation_icon('horizontal'), "Horizontal text")
        self.orientation_vertical_button = self._create_tool_toggle(self._make_orientation_icon('vertical'), "Vertical text")
        for mode, button in (('horizontal', self.orientation_horizontal_button), ('vertical', self.orientation_vertical_button)):
            button.setCheckable(True)
            button.setProperty('orientation-mode', mode)
            self.orientation_group.addButton(button)
            button.toggled.connect(self._on_orientation_button_toggled)
            orientation_row.addWidget(button)
        orientation_row.addStretch(1)
        layout_grid.addLayout(orientation_row, 1, 1)
        layout.addWidget(layout_group)

        # ── Warp & Curve card ──
        warp_group = QGroupBox("Text Warp & Curve")
        warp_layout = QGridLayout(warp_group)
        warp_layout.setContentsMargins(12, 14, 12, 12)
        warp_layout.setHorizontalSpacing(10)
        warp_layout.setVerticalSpacing(10)
        warp_layout.setColumnStretch(1, 1)

        warp_layout.addWidget(QLabel("Warp Style"), 0, 0)
        self.warp_style_combo = ScrollableComboBox()
        self.warp_style_combo.addItems([
            "None",
            "Curved",
            "Arc",
            "Arch",
            "Flag",
            "Wave",
            "Wavy",
            "Jagged"
        ])
        self._fit_workspace_combo(self.warp_style_combo, 12)
        self.warp_style_combo.currentTextChanged.connect(self._on_warp_style_changed)
        warp_layout.addWidget(self.warp_style_combo, 0, 1)

        warp_layout.addWidget(QLabel("Intensity"), 1, 0)
        intensity_row = QHBoxLayout()
        self.warp_intensity_slider = QSlider(Qt.Horizontal)
        self.warp_intensity_slider.setRange(0, 100)
        self.warp_intensity_slider.setValue(20)
        self.warp_intensity_slider.setMaximumWidth(120)
        self.warp_intensity_slider.valueChanged.connect(self._on_warp_intensity_changed)
        intensity_row.addWidget(self.warp_intensity_slider)
        self.warp_intensity_value_label = QLabel("20.0")
        self.warp_intensity_value_label.setMinimumWidth(40)
        intensity_row.addWidget(self.warp_intensity_value_label)
        intensity_row.addStretch(1)
        warp_layout.addLayout(intensity_row, 1, 1)

        warp_layout.addWidget(QLabel("Curve Handles"), 2, 0)
        from src.ui.widgets import InteractiveCurveEditor
        self.typeset_curve_editor = InteractiveCurveEditor(self)
        self.typeset_curve_editor.curveChanged.connect(self._on_warp_curve_changed)
        warp_layout.addWidget(self.typeset_curve_editor, 2, 1, Qt.AlignLeft)
        self.typeset_curve_editor.setVisible(False)

        layout.addWidget(warp_group)

        # ── Preview card ──
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(12, 10, 12, 12)
        self.typeset_preview_label = QLabel()
        self.typeset_preview_label.setAlignment(Qt.AlignCenter)
        self.typeset_preview_label.setMinimumHeight(180)
        self.typeset_preview_label.setMinimumWidth(0)
        self.typeset_preview_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.typeset_preview_label.setStyleSheet(self._preview_label_qss())
        preview_layout.addWidget(self.typeset_preview_label)
        layout.addWidget(preview_group)

        # ── Recent Translations card ──
        recent_group = QGroupBox("Recent Translations")
        recent_layout = QVBoxLayout(recent_group)
        recent_layout.setContentsMargins(12, 10, 12, 12)
        
        recent_desc = QLabel("Click to apply recent translation to active text area.")
        recent_desc.setWordWrap(True)
        recent_desc.setStyleSheet(f"color: {theme.COLORS['muted']}; font-size: 8.5pt;")
        recent_layout.addWidget(recent_desc)
        
        self.typeset_recent_list = QListWidget()
        self.typeset_recent_list.setMaximumHeight(160)
        self.typeset_recent_list.setMinimumWidth(0)
        self.typeset_recent_list.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.typeset_recent_list.itemClicked.connect(self._on_recent_translation_clicked)
        recent_layout.addWidget(self.typeset_recent_list)
        layout.addWidget(recent_group)

        layout.addStretch(1)

        scroll.setWidget(container)

        selected_display = None
        if getattr(self, 'typeset_defaults', None):
            selected_display = self.typeset_defaults.get('font_display')
        self._populate_typeset_font_dropdown(selected_display)
        self._apply_typeset_defaults()
        self._refresh_outline_controls_enabled()

        return scroll

    def _create_typeset_area(self, rect, text, settings, polygon=None, original_text="", translation_style=None, manual_inpaint=None, is_manual=False):
        if not is_manual and isinstance(text, str) and text:
            processed_lines = []
            for line in text.splitlines():
                stripped = line.rstrip()
                if stripped.endswith('。'):
                    stripped = stripped[:-1].rstrip()
                elif stripped.endswith('.') and not stripped.endswith('..'):
                    stripped = stripped[:-1].rstrip()
                processed_lines.append(stripped)
            text = '\n'.join(processed_lines)

        area = TypesetArea(
            rect,
            text,
            settings['font'],
            settings['color'],
            polygon=polygon,
            orientation=settings.get('orientation_mode', 'horizontal'),
            effect=settings.get('text_effect', 'none'),
            effect_intensity=settings.get('effect_intensity', 20.0),
            bezier_points=settings.get('bezier_points'),
            bubble_enabled=settings.get('create_bubble', False),
            text_outline=settings.get('text_outline', False),
            text_outline_width=settings.get('outline_width', self.typeset_outline_width),
            text_outline_color=settings.get('outline_color', self.typeset_outline_color.name() if isinstance(self.typeset_outline_color, QColor) else '#000000'),
            text_outline_style=settings.get('outline_style', getattr(self, 'typeset_outline_style', 'stroke')),
            alignment=settings.get('alignment', 'center'),
            line_spacing=settings.get('line_spacing', 1.1),
            char_spacing=settings.get('char_spacing', 100.0),
            margins=settings.get('margins', {'top': 0, 'right': 0, 'bottom': 0, 'left': 0}),
            original_text=original_text,
            translation_style=translation_style if translation_style is not None else settings.get('translation_style', '')
        )
        cleanup_defaults = SETTINGS.get('cleanup', {})
        use_inpaint_value = bool(manual_inpaint) if manual_inpaint is not None else bool(settings.get('use_inpaint', cleanup_defaults.get('use_inpaint', True)))
        use_background_box_value = bool(settings.get('use_background_box', cleanup_defaults.get('use_background_box', True)))
        constrain_text_value = bool(settings.get('constrain_text', cleanup_defaults.get('constrain_text', True)))
        area.set_override('use_inpaint', use_inpaint_value)
        area.set_override('use_background_box', use_background_box_value)
        area.set_override('constrain_text', constrain_text_value)
        notes = area.review_notes if isinstance(area.review_notes, dict) else {}
        area.review_notes = notes
        if is_manual:
            area.review_notes['manual'] = True
        if manual_inpaint is not None:
            area.review_notes['manual_inpaint'] = bool(manual_inpaint)
        area.ensure_defaults()
        return area

    def _update_typeset_record(
        self,
        key,
        *,
        areas=None,
        redo=None,
        cleaned_image_png=None,
        remove_cleaned_image=False,
        pre_inpaint_image_png=None,
        remove_pre_inpaint_image=False,
    ):
        if not key:
            return {}
        record = self.all_typeset_data.get(key)
        if not isinstance(record, dict):
            record = {}
        if areas is not None:
            record['areas'] = areas
        else:
            record.setdefault('areas', [])
        if redo is not None:
            record['redo'] = redo
        else:
            record.setdefault('redo', [])
        if remove_cleaned_image:
            record.pop('cleaned_image_png', None)
        elif cleaned_image_png is not None:
            record['cleaned_image_png'] = cleaned_image_png
        if remove_pre_inpaint_image:
            record.pop('pre_inpaint_image_png', None)
        elif pre_inpaint_image_png is not None:
            record['pre_inpaint_image_png'] = pre_inpaint_image_png
        self.all_typeset_data[key] = record
        return record

    def _typeset_button_stylesheet(self):
        return (
            "QToolButton {"
            f" border: 1px solid {theme.COLORS['border']};"
            f" background-color: {theme.COLORS['card_alt']};"
            f" color: {theme.COLORS['text']};"
            " border-radius: 6px;"
            " padding: 4px;"
            " }"
            " QToolButton:hover {"
            f" border-color: {theme.COLORS['accent']};"
            f" background-color: {theme.COLORS['border']};"
            f" color: {theme.COLORS['accent']};"
            " }"
            " QToolButton:checked {"
            f" border-color: {theme.COLORS['accent']};"
            f" background-color: {theme.COLORS['border']};"
            f" color: {theme.COLORS['accent']};"
            " }"
        )

    def _create_initial_typeset_defaults(self):
        display = None
        if self.font_manager and isinstance(self.typeset_font, QFont):
            display = self.font_manager.display_name_for_font(self.typeset_font)
        if not display and self.font_manager:
            display = self.font_manager.default_display
        size_value = self.typeset_font.pointSizeF() or self.typeset_font.pointSize() or 24.0
        return {
            'font_display': display,
            'font_size': float(size_value),
            'line_spacing': float(self.typeset_line_spacing_value),
            'char_spacing': float(self.typeset_char_spacing_value),
            'bold': self.typeset_font.weight() >= QFont.Bold,
            'italic': self.typeset_font.italic(),
            'underline': self.typeset_font.underline(),
            'alignment': self.typeset_alignment,
            'orientation': self.typeset_orientation,
            'outline': bool(self.typeset_outline_enabled),
            'outline_width': float(self.typeset_outline_width),
            'outline_color': self.typeset_outline_color.name() if isinstance(self.typeset_outline_color, QColor) else '#000000',
            'outline_style': getattr(self, 'typeset_outline_style', 'stroke'),
            'color': self.typeset_color.name(),
            'gradient_enabled': getattr(self, 'typeset_gradient_enabled', False),
            'gradient_angle': getattr(self, 'typeset_gradient_angle', 0.0),
            'gradient_colors': getattr(self, 'typeset_gradient_colors', ["#FF0000", "#0000FF"]),
        }

    def _collect_current_typeset_defaults(self):
        if not getattr(self, 'font_dropdown', None):
            return self._create_initial_typeset_defaults()
        font_display = self.font_dropdown.currentText() or (self.font_manager.default_display if self.font_manager else 'System Default')
        return {
            'font_display': font_display,
            'font_size': float(self.font_size_spin.value() if getattr(self, 'font_size_spin', None) else 24.0),
            'line_spacing': float(self.typeset_line_spacing_value),
            'char_spacing': float(self.typeset_char_spacing_value),
            'bold': bool(self.bold_toggle.isChecked() if getattr(self, 'bold_toggle', None) else False),
            'italic': bool(self.italic_toggle.isChecked() if getattr(self, 'italic_toggle', None) else False),
            'underline': bool(self.underline_toggle.isChecked() if getattr(self, 'underline_toggle', None) else False),
            'alignment': self.typeset_alignment,
            'orientation': self.typeset_orientation,
            'outline': bool(self.typeset_outline_enabled),
            'outline_width': float(self.typeset_outline_width),
            'outline_color': self.typeset_outline_color.name() if isinstance(self.typeset_outline_color, QColor) else '#000000',
            'outline_style': getattr(self, 'typeset_outline_style', 'stroke'),
            'color': self.typeset_color.name() if isinstance(self.typeset_color, QColor) else '#000000',
            'gradient_enabled': bool(self.gradient_group.isChecked()) if getattr(self,'gradient_group',None) else False,
            'gradient_angle': float(self.grad_angle_spin.value()) if getattr(self,'grad_angle_spin',None) else 0.0,
            'gradient_colors': [self.grad_color_list.item(i).text() for i in range(self.grad_color_list.count())] if getattr(self,'grad_color_list',None) else ["#FF0000", "#0000FF"],
        }

    def _update_typeset_defaults_from_panel(self):
        if getattr(self, 'selected_typeset_area', None) is None:
            self.typeset_defaults = self._collect_current_typeset_defaults()

    def _handle_save_typeset_defaults(self):
        self.typeset_defaults = self._collect_current_typeset_defaults()
        status = self.statusBar() if hasattr(self, 'statusBar') else None
        if status:
            status.showMessage("Typeset defaults updated", 2500)

    def _handle_reset_typeset_defaults(self):
        self._apply_typeset_defaults()
        status = self.statusBar() if hasattr(self, 'statusBar') else None
        if status:
            status.showMessage("Defaults restored", 2000)

    def _apply_typeset_defaults(self):
        defaults = self.typeset_defaults or self._create_initial_typeset_defaults()
        self._apply_typeset_settings(defaults)

    def _on_typeset_line_spacing_changed(self, value):
        self._set_line_spacing_value(value)
        self._apply_active_typeset_to_selected()
        self._update_typeset_defaults_from_panel()
        self._update_typeset_preview()

    def _on_typeset_char_spacing_changed(self, value):
        self._set_char_spacing_value(value)
        self.typeset_font = self._build_current_font()
        self._apply_active_typeset_to_selected()
        self._update_typeset_defaults_from_panel()
        self._update_typeset_preview()

    def _on_typeset_style_changed(self, *_):
        self.typeset_font = self._build_current_font()
        self._apply_active_typeset_to_selected()
        self._update_typeset_defaults_from_panel()
        self._update_typeset_preview()

    def _on_typeset_outline_changed(self, checked):
        self.typeset_outline_enabled = bool(checked)
        self._refresh_outline_controls_enabled()
        self._persist_typeset_preferences()
        self._apply_active_typeset_to_selected()
        self._update_typeset_defaults_from_panel()
        self._update_typeset_preview()

    def _on_typeset_gradient_toggled(self, checked):
        self.typeset_gradient_enabled = bool(checked)
        self._on_typeset_gradient_changed()

    def _on_typeset_gradient_changed(self, *_):
        if hasattr(self, 'gradient_group'):
            self.typeset_gradient_enabled = bool(self.gradient_group.isChecked())
        if hasattr(self, 'grad_angle_spin'):
            self.typeset_gradient_angle = self.grad_angle_spin.value()

        self._persist_typeset_preferences()
        self._update_typeset_defaults_from_panel()
        self._update_typeset_preview()
        
        # Apply to selected area if any
        if self.selected_typeset_area:
            with QSignalBlocker(self.selected_typeset_area):
                self.selected_typeset_area.gradient_enabled = self.typeset_gradient_enabled
                self.selected_typeset_area.gradient_colors = list(self.typeset_gradient_colors)
                self.selected_typeset_area.gradient_angle = self.typeset_gradient_angle
            self.redraw_all_typeset_areas()

    def _persist_typeset_preferences(self):
        cfg = SETTINGS.setdefault('typeset', {})
        cfg['outline_enabled'] = bool(self.typeset_outline_enabled)
        cfg['outline_width'] = float(self.typeset_outline_width)
        cfg['outline_thickness'] = int(round(max(0.0, self.typeset_outline_width)))
        color = self.typeset_outline_color if isinstance(self.typeset_outline_color, QColor) else QColor(self.typeset_outline_color)
        if not color.isValid():
            color = QColor('#000000')
        cfg['outline_color'] = color.name()
        cfg['outline_style'] = getattr(self, 'typeset_outline_style', 'stroke')
        save_settings(SETTINGS)

    def _update_typeset_preview(self):
        try:
            if not getattr(self, 'typeset_preview_label', None):
                return
            self.typeset_font = self._build_current_font()
            self._update_font_preview_label()

            doc = QTextDocument()
            doc.setDocumentMargin(0)
            doc.setDefaultFont(self.typeset_font)

            sample_text = self.preview_sample_text
            if self.typeset_orientation == 'vertical':
                vertical_chars = [ch for ch in self.preview_sample_text if ch.strip()]
                sample_text = '\n'.join(vertical_chars)
            doc.setPlainText(sample_text)

            option = doc.defaultTextOption()
            align_map = {'left': Qt.AlignLeft, 'center': Qt.AlignHCenter, 'right': Qt.AlignRight}
            option.setAlignment(align_map.get(self.typeset_alignment, Qt.AlignHCenter))
            doc.setDefaultTextOption(option)

            cursor = QTextCursor(doc)
            cursor.select(QTextCursor.Document)
            block_format = QTextBlockFormat()
            block_format.setLineHeight(int(self.typeset_line_spacing_value * 100), QTextBlockFormat.ProportionalHeight)
            block_format.setAlignment(option.alignment())
            cursor.setBlockFormat(block_format)
            text_format = QTextCharFormat()
            text_format.setForeground(QBrush(self.typeset_color))
            cursor.mergeCharFormat(text_format)

            doc.setTextWidth(220)
            doc_size = doc.size()
            image_width = max(1, int(math.ceil(doc_size.width())))
            image_height = max(1, int(math.ceil(doc_size.height())))
            image = QImage(image_width, image_height, QImage.Format_ARGB32_Premultiplied)
            image.fill(Qt.transparent)
            painter = QPainter(image)
            doc.drawContents(painter)
            painter.end()

            if self.typeset_outline_enabled and (self.typeset_outline_width or 0) > 0:
                outline_color = self.typeset_outline_color if isinstance(self.typeset_outline_color, QColor) and self.typeset_outline_color.isValid() else self._outline_for_text_color(self.typeset_color)
                style = getattr(self, 'typeset_outline_style', 'stroke')
                if style == 'glow':
                    image = self._expand_with_outline(image, outline_color, radius=self.typeset_outline_width * 1.4, opacity=0.6)
                else:
                    image = self._expand_with_outline(image, outline_color, radius=self.typeset_outline_width)

            pixmap = QPixmap.fromImage(image)
            if self.typeset_orientation == 'vertical':
                transform = QTransform()
                transform.rotate(90)
                pixmap = pixmap.transformed(transform, Qt.SmoothTransformation)

            width = max(220, self.typeset_preview_label.width())
            height = max(160, self.typeset_preview_label.height())
            canvas = QPixmap(width, height)
            canvas.fill(Qt.transparent)
            scaled = pixmap.scaled(width - 24, height - 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            painter = QPainter(canvas)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.drawPixmap((width - scaled.width()) // 2, (height - scaled.height()) // 2, scaled)
            painter.end()
            self.typeset_preview_label.setPixmap(canvas)
        except Exception:
            traceback.print_exc()

    def redraw_all_typeset_areas(self, refresh_layers=True):
        if not self.original_pixmap: return
        # Protect pixmap assignment and painting from concurrent access
        if hasattr(self, 'deferred_typeset_timer'):
            try:
                self.deferred_typeset_timer.stop()
            except Exception:
                pass
        if getattr(self, '_compare_mode_active', False):
            self.paint_mutex.lock()
            try:
                self.typeset_pixmap = self.original_pixmap.copy()
            finally:
                self.paint_mutex.unlock()
            self.update_display()
            return
        self.paint_mutex.lock()
        try:
            settings = self.get_current_settings()
            use_preview = (
                self.is_transform_preview
                and self._transform_preview_pixmap is not None
                and self.selected_typeset_area in self.typeset_areas
            )

            if use_preview:
                base_pixmap = self._transform_preview_pixmap
                if (
                    base_pixmap is None
                    or base_pixmap.isNull()
                    or base_pixmap.size() != self.original_pixmap.size()
                ):
                    if not self._prepare_transform_preview_base():
                        base_pixmap = None
                    else:
                        base_pixmap = self._transform_preview_pixmap
                if base_pixmap is not None:
                    self.typeset_pixmap = base_pixmap.copy()
                    painter = QPainter(self.typeset_pixmap)
                    try:
                        self.draw_single_area(painter, self.selected_typeset_area, self.current_image_pil, settings=settings)
                    finally:
                        try:
                            painter.end()
                        except Exception:
                            pass
                else:
                    use_preview = False

            if not use_preview:
                self.typeset_pixmap = self.original_pixmap.copy()
                painter = QPainter(self.typeset_pixmap)
                try:
                    for area in list(self.typeset_areas):
                        if not getattr(area, 'visible', True):
                            continue
                        self.draw_single_area(painter, area, self.current_image_pil, settings=settings)
                finally:
                    try:
                        painter.end()
                    except Exception:
                        pass
        finally:
            self.paint_mutex.unlock()
        if refresh_layers and hasattr(self, '_refresh_layers_list'):
            self._refresh_layers_list()
        self.update_display()

    def schedule_typeset_redraw(self, delay_ms=30):
        try:
            timer = self.deferred_typeset_timer
        except AttributeError:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(self.redraw_all_typeset_areas)
            self.deferred_typeset_timer = timer
        try:
            now = time.monotonic()
            if now - getattr(self, '_last_redraw_request', 0.0) < 0.01:
                delay_ms = max(delay_ms, 45)
            self._last_redraw_request = now
            delay = max(1, int(delay_ms))
            if timer.isActive():
                remaining = timer.remainingTime()
                if remaining > 0 and remaining <= delay:
                    return
            timer.start(delay)
        except Exception:
            self.redraw_all_typeset_areas()

    def delete_typeset_area(self, area_to_delete):
        if area_to_delete in self.typeset_areas:
            # Push snapshot SEBELUM hapus agar bisa di-undo
            area_text = getattr(area_to_delete, 'text', '') or ''
            snippet = area_text[:20] + ('…' if len(area_text) > 20 else '')
            self._push_undo_snapshot(f"Delete: {snippet}" if snippet else "Delete Area")

            # Sync to Deleted History Scene
            history_id = getattr(area_to_delete, 'history_id', None)
            if history_id:
                self.move_entry_to_deleted_history(history_id)
            
            self.typeset_areas.remove(area_to_delete)
            if self.selected_typeset_area is area_to_delete:
                self.clear_selected_area()
            self.redo_stack.clear()
            self.redo_stack.append(area_to_delete)
            self.redraw_all_typeset_areas()
            self.update_undo_redo_buttons_state()

    def _serialize_typeset_map(self):
        serialized = {}
        for key, payload in self.all_typeset_data.items():
            if not isinstance(payload, dict):
                continue
            areas = payload.get('areas') or []
            redo = payload.get('redo') or []
            record = {
                'areas': [area.to_payload() if isinstance(area, TypesetArea) else area for area in areas],
                'redo': [area.to_payload() if isinstance(area, TypesetArea) else area for area in redo],
            }
            for image_state_key in ('cleaned_image_png', 'pre_inpaint_image_png'):
                if payload.get(image_state_key):
                    record[image_state_key] = payload.get(image_state_key)
            serialized[key] = record
        return serialized

    def _deserialize_typeset_map(self, serialized_map, fallback_font, fallback_color, project_dir=None):
        """Deserialize the typeset data map.

        Supports both schema v4 (basename keys, e.g. ``"2.webp"``) and legacy
        schema v1-v3 (absolute path keys).  When *project_dir* is provided and
        a key appears to be a basename (no directory separator), it is expanded
        to a full path by joining with *project_dir*.
        """
        result = {}
        warnings = []
        fallback_font = fallback_font or QFont('Arial', 9, QFont.Bold)
        fallback_color = fallback_color or QColor('#000000')
        for key, payload in (serialized_map or {}).items():
            if not isinstance(payload, dict):
                warnings.append(f"Ignored invalid typeset block for {key}.")
                continue

            # --- Schema v4: resolve basename key to full absolute path ---
            resolved_key = key
            if project_dir and os.path.basename(key) == key:
                # key is a bare filename; reconstruct the full path
                resolved_key = os.path.join(project_dir, key)

            areas = []
            for area_data in payload.get('areas') or []:
                try:
                    if isinstance(area_data, TypesetArea):
                        area_obj = area_data
                    else:
                        area_obj = TypesetArea.from_payload(area_data, fallback_font=fallback_font, fallback_color=fallback_color)
                    areas.append(area_obj)
                except Exception as exc:
                    warnings.append(f"Failed to load typeset area in {key}: {exc}")
            redo_items = []
            for redo_data in payload.get('redo') or []:
                try:
                    if isinstance(redo_data, TypesetArea):
                        redo_obj = redo_data
                    else:
                        redo_obj = TypesetArea.from_payload(redo_data, fallback_font=fallback_font, fallback_color=fallback_color)
                    redo_items.append(redo_obj)
                except Exception as exc:
                    warnings.append(f"Failed to load redo entry in {key}: {exc}")
            record = {'areas': areas, 'redo': redo_items}
            for image_state_key in ('cleaned_image_png', 'pre_inpaint_image_png'):
                if payload.get(image_state_key):
                    record[image_state_key] = payload.get(image_state_key)
            result[resolved_key] = record
        return result, warnings

    # ===================================================================
    # ======================= COPY / PASTE FEATURE ======================
    # ===================================================================
    def copy_selected_typeset_area(self):
        """Salin area typeset yang dipilih ke clipboard."""
        if not self.selected_typeset_area:
            return
        
        try:
            payload = self.selected_typeset_area.to_payload()
            container = {
                'type': 'manga_ocr_typeset',
                'data': payload
            }
            json_text = json.dumps(container, ensure_ascii=False)
            QApplication.clipboard().setText(json_text)
            self.show_toast("Copied", "Typeset area copied to clipboard.", kind="success", timeout_ms=2200)
        except Exception as e:
            self.show_banner("copy-typeset-error", "Copy failed", str(e), kind="error")

    def paste_typeset_area(self):
        """Tempel area typeset dari clipboard."""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if not text:
            return

        try:
            container = json.loads(text)
            if not isinstance(container, dict) or container.get('type') != 'manga_ocr_typeset':
                # Not our data, ignore or handle as plain text if needed
                return
            
            data = container.get('data')
            if not data:
                return

            # Buat area baru dari data
            new_area = TypesetArea.from_payload(data)
            
            # Geser sedikit agar tidak menumpuk persis di atas yang asli
            current_rect = new_area.rect
            new_rect = current_rect.translated(20, 20)
            
            # Clamp ke image size
            if self.original_pixmap:
                w, h = self.original_pixmap.width(), self.original_pixmap.height()
                if new_rect.left() > w or new_rect.top() > h:
                     new_rect.moveTo(20, 20)
                if new_rect.right() > w: new_rect.setWidth(max(10, w - new_rect.x()))
                if new_rect.bottom() > h: new_rect.setHeight(max(10, h - new_rect.y()))
            
            new_area.rect = new_rect
            # Juga update polygon/cleanup jika ada
            if new_area.polygon:
                new_area.polygon.translate(20, 20)
            if new_area.cleanup_rect:
                new_area.cleanup_rect.translate(20, 20)
            if new_area.cleanup_polygon:
                new_area.cleanup_polygon.translate(20, 20)

            # Assign new ID to avoid conflict if history tracking uses it
            new_area.history_id = None

            # Tambahkan ke list
            self.typeset_areas.append(new_area)
            self.set_selected_area(new_area)
            self.redraw_all_typeset_areas()
            self._refresh_layers_list()

            # Commit to cache immediately to prevent copy-paste loss
            if self.current_image_path:
                key = self.get_current_data_key()
                self._update_typeset_record(key, areas=list(self.typeset_areas), redo=list(self.redo_stack))

            self.show_toast("Pasted", "Typeset area pasted.", kind="success", timeout_ms=2200)

        except json.JSONDecodeError:
            pass # Bukan JSON valid
        except Exception as e:
            self.show_banner("paste-typeset-error", "Paste failed", str(e), kind="error")
            traceback.print_exc()
