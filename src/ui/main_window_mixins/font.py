"""Method domain font, dipindahkan utuh dari main_window.py.

Fase 1 pemecahan monolit: isi method tidak diubah sama sekali.
Mixin ini hanya berguna sebagai bagian dari MangaOCRApp -- ia mengandalkan
atribut yang dibuat di MangaOCRApp.__init__.
"""

from src.ui.main_window_mixins._imports import *  # noqa: F401,F403


class FontMixin:
    def _populate_typeset_font_dropdown(self, preferred_display=None, group: str | None = None):
        """Populate the typeset font dropdown. Optionally filter by a font group name.

        preferred_display: preferred font display name to select
        group: if provided, only fonts listed under self.font_groups[group] will be shown
        """
        if not hasattr(self, 'font_dropdown') or not self.font_manager:
            return
        fonts = self.font_manager.list_fonts()
        # If a group is supplied and we have a mapping, filter the fonts.
        if group and getattr(self, 'font_groups', None):
            allowed = set(self.font_groups.get(group, []) )
            # Keep only fonts that exist in the available fonts list
            fonts = [f for f in fonts if f in allowed]

        current_display = self.font_manager.display_name_for_font(getattr(self, 'typeset_font', None))
        target_display = preferred_display or current_display
        with QSignalBlocker(self.font_dropdown):
            self.font_dropdown.clear()
            for name in fonts:
                self.font_dropdown.addItem(name)
                preview_font = self.font_manager.create_qfont(name)
                preview_font.setPointSize(16)
                index = self.font_dropdown.count() - 1
                self.font_dropdown.setItemData(index, preview_font, Qt.FontRole)
        if target_display in fonts:
            with QSignalBlocker(self.font_dropdown):
                self.font_dropdown.setCurrentText(target_display)
        elif fonts:
            with QSignalBlocker(self.font_dropdown):
                self.font_dropdown.setCurrentIndex(0)

    def _build_current_font(self) -> QFont:
        display = None
        if getattr(self, 'font_dropdown', None):
            display = self.font_dropdown.currentText()
        if self.font_manager and display:
            font = self.font_manager.create_qfont(display)
        elif isinstance(self.typeset_font, QFont):
            font = QFont(self.typeset_font)
        else:
            font = QFont('Arial', 14)
        size_value = float(self.font_size_spin.value()) if getattr(self, 'font_size_spin', None) else 24.0
        if size_value <= 0:
            size_value = 12.0
        font.setPointSizeF(size_value)
        if getattr(self, 'bold_toggle', None):
            font.setBold(self.bold_toggle.isChecked())
        if getattr(self, 'italic_toggle', None):
            font.setItalic(self.italic_toggle.isChecked())
        if getattr(self, 'underline_toggle', None):
            font.setUnderline(self.underline_toggle.isChecked())
        font.setLetterSpacing(QFont.PercentageSpacing, self.typeset_char_spacing_value or 100.0)
        return font

    def _on_typeset_font_size_changed(self, value):
        self.typeset_font = self._build_current_font()
        self._apply_active_typeset_to_selected()
        self._update_typeset_defaults_from_panel()
        self._update_typeset_preview()

    def _on_font_group_changed(self, group_name: str):
        # Called when the font group selector changes. If 'All' selected, pass
        # no group so the full font list is shown.
        if group_name == 'All':
            self._populate_typeset_font_dropdown()
        else:
            self._populate_typeset_font_dropdown(group=group_name)
        # Refresh preview in case font selection affected it
        try:
            self.typeset_font = self._build_current_font()
            self._update_typeset_preview()
        except Exception:
            pass

    def _on_add_font_to_group_clicked(self):
        # Open a simple modal to add a font family to the currently selected group
        current_group = self.font_group_combo.currentText()
        if not current_group or current_group == 'All':
            self.show_toast("Select group", "Please select a specific group to add a font to.", kind="info")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Add Font to {current_group}")
        dialog.setModal(True)
        dlg_layout = QVBoxLayout(dialog)
        dlg_layout.addWidget(QLabel(f"Add a font family name to the group '{current_group}':"))
        font_input = QLineEdit()
        font_input.setPlaceholderText("Type font display name (e.g. 'Badaboom BB') or exact family name")
        dlg_layout.addWidget(font_input)

        # Also provide a dropdown of installed fonts to choose from
        installed_label = QLabel("Or choose from installed fonts:")
        installed_label.setStyleSheet("color: #9cb4d0; font-size: 11px;")
        dlg_layout.addWidget(installed_label)
        installed_combo = QComboBox()
        try:
            installed_fonts = self.font_manager.list_fonts() if getattr(self, 'font_manager', None) else []
            installed_combo.addItem("(none)")
            for f in installed_fonts:
                installed_combo.addItem(f)
        except Exception:
            installed_combo.addItem("(could not list)")
        dlg_layout.addWidget(installed_combo)

        btn_box = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        dlg_layout.addWidget(btn_box)

        if dialog.exec_() != QDialog.Accepted:
            return

        chosen = font_input.text().strip() or (installed_combo.currentText() if installed_combo.currentText() != "(none)" and installed_combo.currentText() != "(could not list)" else '')
        if not chosen:
            self.show_toast("No font selected", "No font was provided. Operation cancelled.", kind="info")
            return

        # Add to mapping and refresh UI
        if not getattr(self, 'font_groups', None):
            self.font_groups = {}
        self.font_groups.setdefault(current_group, [])
        if chosen not in self.font_groups[current_group]:
            self.font_groups[current_group].append(chosen)
        # refresh the font dropdown for the group
        self._populate_typeset_font_dropdown(group=current_group)
        # Persist font groups to settings
        try:
            SETTINGS.setdefault('font_groups', {})
            SETTINGS['font_groups'].update(copy.deepcopy(self.font_groups))
            save_settings(SETTINGS)
        except Exception:
            pass
        self.show_toast("Font group updated", f"'{chosen}' added to group '{current_group}'.", kind="success")

    def _on_add_font_group_clicked(self):
        name, ok = QInputDialog.getText(self, "Add Font Group", "Group name:")
        if not ok or not name.strip():
            return
        grp = name.strip()
        if not getattr(self, 'font_groups', None):
            self.font_groups = {}
        if grp in self.font_groups:
            self.show_toast("Group exists", f"Group '{grp}' already exists.", kind="info")
            return
        self.font_groups[grp] = []
        # update combo
        self.font_group_combo.addItem(grp)
        # persist
        try:
            SETTINGS.setdefault('font_groups', {})
            SETTINGS['font_groups'].update(copy.deepcopy(self.font_groups))
            save_settings(SETTINGS)
        except Exception:
            pass
        self.show_toast("Group created", f"Group '{grp}' created.", kind="success")

    def _on_remove_font_group_clicked(self):
        grp = self.font_group_combo.currentText()
        if not grp or grp == 'All':
            self.show_toast("Select group", "Please select a specific group to remove.", kind="info")
            return
        confirm = QMessageBox.question(self, "Remove Group", f"Remove group '{grp}' and all its entries?", QMessageBox.Yes | QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return
        try:
            if getattr(self, 'font_groups', None) and grp in self.font_groups:
                self.font_groups.pop(grp, None)
            # remove from combo
            idx = self.font_group_combo.findText(grp)
            if idx != -1:
                self.font_group_combo.removeItem(idx)
            # persist
            SETTINGS.setdefault('font_groups', {})
            SETTINGS['font_groups'] = copy.deepcopy(self.font_groups)
            save_settings(SETTINGS)
            self.show_toast("Group removed", f"Group '{grp}' removed.", kind="success")
        except Exception as e:
            self.show_banner("font-group-remove-error", "Failed to remove group", str(e), kind="error")

    def _update_font_preview_label(self):
        if not getattr(self, 'font_preview_label', None):
            return
        font = QFont(self.typeset_font)
        preview_size = max(12.0, min(font.pointSizeF() or font.pointSize() or 20.0, 28.0))
        font.setPointSizeF(preview_size)
        font.setLetterSpacing(QFont.PercentageSpacing, self.typeset_char_spacing_value)
        self.font_preview_label.setFont(font)
        self.font_preview_label.setText("AaBb123")
        if getattr(self, 'font_dropdown', None):
            self.font_preview_label.setToolTip(self.font_dropdown.currentText())

    def on_typeset_font_change(self, display_name):
        if not display_name or not self.font_manager:
            return
        self.typeset_font = self._build_current_font()
        self._apply_active_typeset_to_selected()
        self._update_typeset_defaults_from_panel()
        self._update_typeset_preview()

    def _on_auto_font_toggled(self, checked):
        if 'typeset' not in SETTINGS:
            SETTINGS['typeset'] = {}
        SETTINGS['typeset']['auto_font_enabled'] = checked
        save_settings(SETTINGS)
