"""Method domain layer, dipindahkan utuh dari main_window.py.

Fase 1 pemecahan monolit: isi method tidak diubah sama sekali.
Mixin ini hanya berguna sebagai bagian dari MangaOCRApp -- ia mengandalkan
atribut yang dibuat di MangaOCRApp.__init__.
"""

from src.ui.main_window_mixins._imports import *  # noqa: F401,F403


class LayerMixin:
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
                padding: 4px;
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
                "border-radius: 5px;"
            )
        border = theme.COLORS["accent"] if active else theme.COLORS["border"]
        color = theme.COLORS["accent"] if active else theme.COLORS["muted"]
        return (
            f"background-color: {theme.COLORS['card_alt']};"
            f"border: 1px solid {border};"
            f"color: {color};"
            "border-radius: 5px;"
        )

    def _create_layers_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(14)

        # Title/desc
        desc = QLabel("Canvas Layers Manager")
        desc.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {theme.COLORS['accent']};")
        layout.addWidget(desc)

        help_lbl = QLabel("Right-Click: Rename / Fast Opacity  |  Double-Click: Edit Text")
        help_lbl.setStyleSheet(f"font-size: 9pt; color: {theme.COLORS['muted']};")
        layout.addWidget(help_lbl)

        # Opacity Slider section
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("Opacity:"))
        self.layer_opacity_slider = QSlider(Qt.Horizontal)
        self.layer_opacity_slider.setRange(0, 100)
        self.layer_opacity_slider.setValue(100)
        self.layer_opacity_slider.setSingleStep(5)
        self.layer_opacity_slider.valueChanged.connect(self._on_opacity_slider_changed)
        opacity_layout.addWidget(self.layer_opacity_slider)
        self.layer_opacity_label = QLabel("100%")
        self.layer_opacity_label.setMinimumWidth(35)
        self.layer_opacity_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        opacity_layout.addWidget(self.layer_opacity_label)
        layout.addLayout(opacity_layout)

        # List Widget
        self.layers_list_widget = QListWidget()
        self.layers_list_widget.setObjectName("layers-list")
        self.layers_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.layers_list_widget.customContextMenuRequested.connect(self._show_layer_context_menu)
        self.layers_list_widget.setStyleSheet(self._layers_list_qss())
        self.layers_list_widget.itemSelectionChanged.connect(self._on_layer_selection_changed)
        layout.addWidget(self.layers_list_widget, 1)

        # Control row
        btn_row = QHBoxLayout()
        add_layer_btn = QPushButton("+ Add Layer")
        add_layer_btn.clicked.connect(self._add_new_manual_layer)
        add_layer_btn.setStyleSheet(theme.secondary_button_qss())
        
        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.clicked.connect(self._clear_all_layers)
        clear_all_btn.setStyleSheet(theme.danger_button_qss())
        
        btn_row.addWidget(add_layer_btn)
        btn_row.addWidget(clear_all_btn)
        layout.addLayout(btn_row)

        return tab

    def _refresh_layers_list(self):
        if not hasattr(self, 'layers_list_widget'):
            return
        if getattr(self, 'is_transform_preview', False):
            return
            
        # Block signals to prevent infinite loop
        self.layers_list_widget.blockSignals(True)
        self.layers_list_widget.clear()
        
        for idx, area in enumerate(list(self.typeset_areas)):
            # Create a list item
            item = QListWidgetItem()
            item.setSizeHint(QSize(100, 48))
            item.setData(Qt.UserRole, area)
            self.layers_list_widget.addItem(item)
            
            # Create custom widget
            w = QWidget()
            layout = QHBoxLayout(w)
            layout.setContentsMargins(6, 4, 6, 4)
            layout.setSpacing(8)
            
            # 1. Eye button (Visibility)
            visible = getattr(area, 'visible', True)
            eye_btn = QPushButton()
            eye_btn.setIcon(self._make_eye_icon(visible))
            eye_btn.setIconSize(QSize(20, 20))
            eye_btn.setFixedSize(28, 28)
            eye_btn.setToolTip("Toggle Visibility")
            eye_btn.setStyleSheet(self._small_layer_button_qss(active=visible))
            eye_btn.clicked.connect(partial(self._toggle_layer_visibility, area, eye_btn))
            layout.addWidget(eye_btn)
            
            # 2. Lock button (Lock)
            locked = getattr(area, 'locked', False)
            lock_btn = QPushButton()
            lock_btn.setIcon(self._make_lock_icon(locked))
            lock_btn.setIconSize(QSize(20, 20))
            lock_btn.setFixedSize(28, 28)
            lock_btn.setToolTip("Toggle Lock")
            lock_btn.setStyleSheet(self._small_layer_button_qss(danger=locked))
            lock_btn.clicked.connect(partial(self._toggle_layer_lock, area, lock_btn))
            layout.addWidget(lock_btn)
            
            # 3. Label text
            text_preview = getattr(area, 'layer_name', '')
            if not text_preview:
                text_preview = (area.text or "").strip()
                if len(text_preview) > 18:
                    text_preview = text_preview[:15] + "..."
                if not text_preview:
                    text_preview = f"Text Block #{idx+1}"
            
            label = QLabel(text_preview)
            label.setStyleSheet(
                f"color: {theme.COLORS['text']}; font-weight: bold;"
                if visible else
                f"color: {theme.COLORS['muted']}; text-decoration: line-through;"
            )
            layout.addWidget(label, 1)
            
            # 4. Reorder Buttons
            up_btn = QPushButton("▲")
            up_btn.setFixedSize(20, 20)
            up_btn.setStyleSheet(
                self._small_layer_button_qss()
                + "font-size: 8pt; font-family: 'Segoe UI Symbol', 'Segoe UI', sans-serif;"
            )
            up_btn.clicked.connect(partial(self._move_layer_up, area))
            layout.addWidget(up_btn)
            
            down_btn = QPushButton("▼")
            down_btn.setFixedSize(20, 20)
            down_btn.setStyleSheet(
                self._small_layer_button_qss()
                + "font-size: 8pt; font-family: 'Segoe UI Symbol', 'Segoe UI', sans-serif;"
            )
            down_btn.clicked.connect(partial(self._move_layer_down, area))
            layout.addWidget(down_btn)
            
            # 5. Delete Button
            del_btn = QPushButton()
            del_btn.setIcon(self._make_trash_icon())
            del_btn.setIconSize(QSize(16, 16))
            del_btn.setFixedSize(24, 24)
            del_btn.setStyleSheet(self._small_layer_button_qss(danger=True))
            del_btn.clicked.connect(partial(self._delete_layer, area))
            layout.addWidget(del_btn)
            
            self.layers_list_widget.setItemWidget(item, w)
            
            # Select the item if it matches the current active area
            if area is self.selected_typeset_area:
                item.setSelected(True)
                
        self.layers_list_widget.blockSignals(False)

    def _toggle_layer_visibility(self, area, btn):
        area.visible = not getattr(area, 'visible', True)
        self.redraw_all_typeset_areas()
        self.image_label.update()
        self._refresh_layers_list()

    def _toggle_layer_lock(self, area, btn):
        area.locked = not getattr(area, 'locked', False)
        self.image_label.update()
        self._refresh_layers_list()

    def _on_layer_selection_changed(self):
        selected_items = self.layers_list_widget.selectedItems()
        if selected_items:
            area = selected_items[0].data(Qt.UserRole)
            self.set_selected_area(area)

    def _move_layer_up(self, area):
        if area in self.typeset_areas:
            idx = self.typeset_areas.index(area)
            if idx > 0:
                self.typeset_areas.remove(area)
                self.typeset_areas.insert(idx - 1, area)
                self.redraw_all_typeset_areas()
                self._refresh_layers_list()

    def _move_layer_down(self, area):
        if area in self.typeset_areas:
            idx = self.typeset_areas.index(area)
            if idx < len(self.typeset_areas) - 1:
                self.typeset_areas.remove(area)
                self.typeset_areas.insert(idx + 1, area)
                self.redraw_all_typeset_areas()
                self._refresh_layers_list()

    def _delete_layer(self, area):
        self.delete_typeset_area(area)
        self._refresh_layers_list()

    def _add_new_manual_layer(self):
        self.ocr_lang_combo.setCurrentText("Manual Text (Rect)")
        from src.ui.canvas import TypesetArea
        rect = QRect(100, 100, 200, 80)
        from PyQt5.QtGui import QFont, QColor
        font = self._build_current_font()
        color = self.typeset_color if hasattr(self, 'typeset_color') and self.typeset_color else QColor("#000000")
        new_area = TypesetArea(rect, "SFX Text", font, color)
        self._push_undo_snapshot("New Layer")
        self.typeset_areas.append(new_area)
        self.set_selected_area(new_area)
        self.redraw_all_typeset_areas()
        self._refresh_layers_list()

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
            self.redraw_all_typeset_areas()
            self._refresh_layers_list()

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
        self.redraw_all_typeset_areas(refresh_layers=False)
