"""Embedded Settings workspace for the main window."""

from __future__ import annotations

import copy
import os
from datetime import date, timedelta

from PyQt5.QtCore import Qt, QSize, pyqtSignal, QRect, QTimer
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.app_info import APP_VERSION
from src.ui import theme
from src.ui.dialogs import SettingsCenterDialog
from src.ui.notifications import notify_toast
from src.ui.texts import SettingsWorkspaceText, about_html
from src.ui.unified_help_dialog import UnifiedHelpDialog


APP_SETTINGS_KEYS = {
    "general",
    "cleanup",
    "appearance",
    "translation",
    "shortcuts",
    "api",
    "ocr_plugins",
    "media_tools",
    "glossary",
}

HELP_TAB_KEYS = {
    "usage": 2,
    "pricing": 1,
    "analytics": 2,
}


def _format_number(value) -> str:
    try:
        value = float(value or 0)
    except Exception:
        value = 0.0
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    if abs_value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs_value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{int(value):,}"


def _format_money(value) -> str:
    try:
        amount = float(value or 0.0)
    except Exception:
        amount = 0.0
    if amount >= 100:
        return f"${amount:,.2f}"
    return f"${amount:,.6f}"


def _format_duration(seconds) -> str:
    try:
        seconds = int(seconds or 0)
    except Exception:
        seconds = 0
    seconds = max(0, seconds)
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def _safe_date(value: str):
    try:
        return date.fromisoformat(str(value))
    except Exception:
        return None


class TokenHeatmapWidget(QWidget):
    """Compact GitHub-style activity grid for token usage."""

    # Grid geometry — kept in sync with the values used in paintEvent so the
    # widget can size itself to fit the full grid (preventing the rightmost
    # weeks — the ones that actually carry recent activity — from being
    # clipped off the visible edge of the widget).
    WEEKS = 53
    SQUARE = 11
    GAP = 4
    LEFT_MARGIN = 42  # room for the Mon/Wed/Fri row labels
    RIGHT_PAD = 24

    @classmethod
    def _grid_width(cls) -> int:
        return cls.WEEKS * cls.SQUARE + (cls.WEEKS - 1) * cls.GAP

    @classmethod
    def _min_width(cls) -> int:
        return cls.LEFT_MARGIN + cls._grid_width() + cls.RIGHT_PAD

    def __init__(self, parent=None):
        super().__init__(parent)
        self._activity = {}
        self._mode = "daily"
        self._range_start = None
        self._range_end = None
        self._latest_active_date = None
        self.setMinimumHeight(154)
        self.setMinimumWidth(self._min_width())
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def sizeHint(self):
        return QSize(self._min_width(), 154)

    def set_activity(self, activity: dict, mode: str = "daily"):
        self._activity = activity or {}
        self._mode = mode or "daily"
        self._latest_active_date = self._latest_activity_date()
        self._range_start, self._range_end = self._grid_range()
        self.update()

    def _tokens_for_day(self, current: date) -> float:
        data = self._activity.get(current.isoformat(), {})
        if not isinstance(data, dict):
            return 0.0
        return float(data.get("input_tokens", 0) or 0) + float(data.get("output_tokens", 0) or 0)

    def _latest_activity_date(self):
        latest = None
        for key, data in (self._activity or {}).items():
            current = _safe_date(key)
            if current is None or not isinstance(data, dict):
                continue
            has_activity = False
            for field in ("input_tokens", "output_tokens", "cost_usd", "translated_count", "requests", "active_seconds"):
                try:
                    if float(data.get(field, 0) or 0) > 0:
                        has_activity = True
                        break
                except Exception:
                    continue
            if has_activity and (latest is None or current > latest):
                latest = current
        return latest

    def _grid_range(self):
        weeks = self.WEEKS
        today = date.today()
        latest = self._latest_active_date or self._latest_activity_date()
        end = max(today, latest) if latest is not None else today
        start = end - timedelta(days=((weeks - 1) * 7) + end.weekday())
        return start, end

    def range_summary(self) -> str:
        start, end = self._range_start, self._range_end
        if start is None or end is None:
            start, end = self._grid_range()
        return f"Through {end.strftime('%b')} {end.day}"

    def _day_value(self, current: date, weekly_cache: dict, cumulative_cache: dict) -> float:
        key = current.isoformat()
        if self._mode == "weekly":
            week_key = f"{current.isocalendar()[0]}-{current.isocalendar()[1]}"
            return weekly_cache.get(week_key, 0.0)
        if self._mode == "cumulative":
            return cumulative_cache.get(key, 0.0)
        return self._tokens_for_day(current)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("transparent"))

        weeks = self.WEEKS
        latest_activity = self._latest_active_date or self._latest_activity_date()
        start, end = self._range_start, self._range_end
        if start is None or end is None:
            start, end = self._grid_range()
        square = self.SQUARE
        gap = self.GAP
        grid_width = self._grid_width()
        # Anchor to the left label gutter so the full grid is always painted
        # within the widget's minimum width (no clipping of recent weeks).
        left = self.LEFT_MARGIN if self.width() >= self._min_width() else max(0, (self.width() - grid_width) // 2)
        top = 28

        weekly_cache = {}
        cumulative_cache = {}
        running_total = 0.0
        for day_offset in range(weeks * 7):
            current = start + timedelta(days=day_offset)
            key = current.isoformat()
            day_tokens = self._tokens_for_day(current)
            week_key = f"{current.isocalendar()[0]}-{current.isocalendar()[1]}"
            weekly_cache[week_key] = weekly_cache.get(week_key, 0.0) + day_tokens
            running_total += day_tokens
            cumulative_cache[key] = running_total

        values = []
        for day_offset in range(weeks * 7):
            current = start + timedelta(days=day_offset)
            if current > end:
                continue
            values.append(self._day_value(current, weekly_cache, cumulative_cache))
        max_value = max(values) if values else 1.0
        if max_value <= 0:
            max_value = 1.0

        colors = [
            QColor("#1f232b"),
            QColor("#1f5f7f"),
            QColor("#2788b2"),
            QColor("#32a6d4"),
            QColor(theme.COLORS.get("accent", "#38bdf8")),
        ]

        month_pen = QPen(QColor(theme.COLORS.get("muted", "#64748b")))
        painter.setPen(month_pen)
        month_marks = []
        previous_month = None
        for day_offset in range(weeks * 7):
            current = start + timedelta(days=day_offset)
            if current > end:
                continue
            month_key = (current.year, current.month)
            if month_key != previous_month:
                month_marks.append((current.strftime("%b"), day_offset // 7))
                previous_month = month_key
        for label, column in month_marks:
            x = left + column * (square + gap)
            painter.drawText(QRect(x, 4, 40, 18), Qt.AlignLeft | Qt.AlignVCenter, label)

        painter.setPen(QPen(QColor(theme.COLORS.get("muted", "#64748b"))))
        range_label = f"Through {end.strftime('%b')} {end.day}"
        painter.drawText(
            QRect(left + grid_width - 120, 4, 120, 18),
            Qt.AlignRight | Qt.AlignVCenter,
            range_label,
        )

        painter.setPen(Qt.NoPen)
        for day_offset in range(weeks * 7):
            current = start + timedelta(days=day_offset)
            if current > end:
                continue
            column = day_offset // 7
            row = current.weekday()
            value = self._day_value(current, weekly_cache, cumulative_cache)
            ratio = min(1.0, value / max_value) if max_value else 0.0
            level = 0 if value <= 0 else max(1, min(4, int(ratio * 4 + 0.999)))
            painter.setBrush(colors[level])
            x = left + column * (square + gap)
            y = top + row * (square + gap)
            painter.drawRoundedRect(x, y, square, square, 3, 3)
            if latest_activity is not None and current == latest_activity:
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(QColor(theme.COLORS.get("accent", "#38bdf8")), 1))
                painter.drawRoundedRect(x, y, square, square, 3, 3)
                painter.setPen(Qt.NoPen)

        painter.setPen(QPen(QColor(theme.COLORS.get("muted", "#64748b"))))
        painter.drawText(QRect(0, top + 2, 34, 18), Qt.AlignRight | Qt.AlignVCenter, "Mon")
        painter.drawText(QRect(0, top + 2 * (square + gap) + 2, 34, 18), Qt.AlignRight | Qt.AlignVCenter, "Wed")
        painter.drawText(QRect(0, top + 4 * (square + gap) + 2, 34, 18), Qt.AlignRight | Qt.AlignVCenter, "Fri")
        painter.end()


class SettingsWorkspace(QWidget):
    """Main-window settings surface with profile, usage, help, and settings."""

    back_requested = pyqtSignal()

    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self._nav_rows = []
        self._active_key = "profile"
        self._settings_dialog = None
        self._settings_loading = None
        self._settings_host_layout = None
        self._pending_settings_key = None
        self._help_dialog = None
        self._help_host_layout = None
        self._profile_labels = {}
        self._insight_labels = {}
        self._mode_buttons = {}
        self._heatmap_mode = "daily"
        self.setObjectName("settings-workspace")
        self._build_ui()
        self.refresh_theme()
        self.refresh()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("sw-sidebar")
        sidebar.setFixedWidth(292)
        side_v = QVBoxLayout(sidebar)
        side_v.setContentsMargins(8, 10, 8, 10)
        side_v.setSpacing(10)

        self.back_btn = QPushButton(SettingsWorkspaceText.BACK_TO_APP)
        self.back_btn.setObjectName("sw-back-btn")
        self.back_btn.clicked.connect(self.back_requested.emit)
        side_v.addWidget(self.back_btn)

        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("sw-search")
        self.search_edit.setPlaceholderText(SettingsWorkspaceText.SEARCH_PLACEHOLDER)
        self.search_edit.textChanged.connect(self._filter_nav)
        side_v.addWidget(self.search_edit)

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("sw-nav-list")
        self.nav_list.setFocusPolicy(Qt.NoFocus)
        self.nav_list.setSpacing(2)
        self.nav_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.nav_list.currentItemChanged.connect(self._on_nav_changed)
        side_v.addWidget(self.nav_list, 1)

        version = QLabel(f"MangaTranslate v{APP_VERSION}")
        version.setObjectName("sw-version")
        side_v.addWidget(version)

        root.addWidget(sidebar)

        self.stack = QStackedWidget()
        self.stack.setObjectName("sw-stack")
        root.addWidget(self.stack, 1)

        self.profile_page = self._build_profile_page()
        self.settings_page = self._build_settings_page()
        self.help_page = self._build_help_page()
        self.about_page = self._build_about_page()
        self.stack.addWidget(self.profile_page)
        self.stack.addWidget(self.settings_page)
        self.stack.addWidget(self.help_page)
        self.stack.addWidget(self.about_page)

        self._populate_nav()
        self.set_active_section("profile")

    def _populate_nav(self):
        self.nav_list.blockSignals(True)
        self.nav_list.clear()
        self._nav_rows = []
        for section, entries in SettingsWorkspaceText.NAV_SECTIONS:
            header = QListWidgetItem(section)
            header.setData(Qt.UserRole, {"section": True, "text": section.lower()})
            header.setFlags(Qt.NoItemFlags)
            header.setSizeHint(QSize(240, 28))
            self.nav_list.addItem(header)
            self._nav_rows.append(header)
            for entry in entries:
                key, label, desc = entry[:3]
                icon = entry[3] if len(entry) > 3 else "*"
                item = QListWidgetItem(f"{icon}  {label}\n    {desc}")
                item.setData(Qt.UserRole, {"key": key, "text": f"{label} {desc} {section}".lower()})
                item.setSizeHint(QSize(240, 50))
                self.nav_list.addItem(item)
                self._nav_rows.append(item)
        self.nav_list.blockSignals(False)

    def _build_profile_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("sw-scroll")

        inner = QWidget()
        inner.setObjectName("sw-profile-inner")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(30, 24, 30, 36)
        layout.setSpacing(22)

        top = QHBoxLayout()
        title = QLabel(SettingsWorkspaceText.PROFILE_TITLE)
        title.setObjectName("sw-page-kicker")
        top.addWidget(title)
        top.addStretch(1)
        refresh_btn = QPushButton(SettingsWorkspaceText.REFRESH)
        refresh_btn.setObjectName("sw-secondary-btn")
        refresh_btn.clicked.connect(self.refresh)
        top.addWidget(refresh_btn)
        layout.addLayout(top)

        identity = QWidget()
        identity.setObjectName("sw-identity")
        identity_l = QVBoxLayout(identity)
        identity_l.setContentsMargins(0, 48, 0, 24)
        identity_l.setSpacing(8)
        identity_l.setAlignment(Qt.AlignHCenter)

        self.avatar_label = QLabel("MT")
        self.avatar_label.setObjectName("sw-avatar")
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setFixedSize(84, 84)
        identity_l.addWidget(self.avatar_label, 0, Qt.AlignHCenter)

        self.profile_name_label = QLabel(SettingsWorkspaceText.PROFILE_NAME_FALLBACK)
        self.profile_name_label.setObjectName("sw-profile-name")
        self.profile_name_label.setAlignment(Qt.AlignCenter)
        identity_l.addWidget(self.profile_name_label)

        self.profile_handle_label = QLabel(SettingsWorkspaceText.PROFILE_HANDLE)
        self.profile_handle_label.setObjectName("sw-profile-handle")
        self.profile_handle_label.setAlignment(Qt.AlignCenter)
        identity_l.addWidget(self.profile_handle_label)
        layout.addWidget(identity)

        stats = QWidget()
        stats.setObjectName("sw-stat-strip")
        stats_l = QGridLayout(stats)
        stats_l.setContentsMargins(16, 14, 16, 14)
        stats_l.setHorizontalSpacing(0)
        stats_l.setVerticalSpacing(0)
        stat_defs = [
            ("lifetime_tokens", "Lifetime tokens"),
            ("input_tokens", "Input tokens"),
            ("output_tokens", "Output tokens"),
            ("cost", "Total cost"),
            ("longest_session", "Longest session"),
            ("current_streak", "Current streak"),
            ("longest_streak", "Longest streak"),
        ]
        for col, (key, label) in enumerate(stat_defs):
            cell = QWidget()
            cell.setObjectName("sw-stat-cell")
            cell_l = QVBoxLayout(cell)
            cell_l.setContentsMargins(14, 2, 14, 2)
            cell_l.setSpacing(2)
            value = QLabel("-")
            value.setObjectName("sw-stat-value")
            value.setAlignment(Qt.AlignCenter)
            caption = QLabel(label)
            caption.setObjectName("sw-stat-label")
            caption.setAlignment(Qt.AlignCenter)
            cell_l.addWidget(value)
            cell_l.addWidget(caption)
            stats_l.addWidget(cell, 0, col)
            self._profile_labels[key] = value
        layout.addWidget(stats)

        activity_header = QHBoxLayout()
        activity_title = QLabel(SettingsWorkspaceText.PROFILE_ACTIVITY)
        activity_title.setObjectName("sw-section-title")
        activity_header.addWidget(activity_title)
        self.heatmap_range_label = QLabel("")
        self.heatmap_range_label.setObjectName("sw-range-label")
        activity_header.addWidget(self.heatmap_range_label)
        activity_header.addStretch(1)
        for key, label in (
            ("daily", SettingsWorkspaceText.PROFILE_MODE_DAILY),
            ("weekly", SettingsWorkspaceText.PROFILE_MODE_WEEKLY),
            ("cumulative", SettingsWorkspaceText.PROFILE_MODE_CUMULATIVE),
        ):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setObjectName("sw-mode-btn")
            btn.clicked.connect(lambda checked=False, mode=key: self._set_heatmap_mode(mode))
            activity_header.addWidget(btn)
            self._mode_buttons[key] = btn
        layout.addLayout(activity_header)

        self.heatmap = TokenHeatmapWidget()
        self.heatmap.setObjectName("sw-heatmap")
        self.heatmap.setMaximumWidth(900)
        layout.addWidget(self.heatmap, 0, Qt.AlignHCenter)

        lower = QHBoxLayout()
        lower.setSpacing(26)
        insight_card = self._make_insight_card()
        model_card = self._make_model_card()
        lower.addWidget(insight_card, 1)
        lower.addWidget(model_card, 1)
        layout.addLayout(lower)
        layout.addStretch(1)

        scroll.setWidget(inner)
        return scroll

    def _make_insight_card(self):
        card = QFrame()
        card.setObjectName("sw-info-card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        title = QLabel(SettingsWorkspaceText.PROFILE_INSIGHTS)
        title.setObjectName("sw-section-title")
        layout.addWidget(title)
        for key, label in (
            ("today_tokens", "Today tokens"),
            ("today_cost", "Today cost"),
            ("translated", "Translated snippets"),
            ("project_pages", "Project pages"),
            ("most_active_day", "Most active day"),
        ):
            row = self._make_key_value_row(label)
            layout.addWidget(row)
            self._insight_labels[key] = row.findChild(QLabel, "sw-kv-value")
        return card

    def _make_model_card(self):
        card = QFrame()
        card.setObjectName("sw-info-card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        title = QLabel("Model usage")
        title.setObjectName("sw-section-title")
        layout.addWidget(title)
        for key, label in (
            ("top_provider", "Top provider"),
            ("top_model", "Top model"),
            ("daily_requests", "Requests today"),
            ("rpm_snapshot", "Current RPM"),
            ("data_since", "Data since"),
        ):
            row = self._make_key_value_row(label)
            layout.addWidget(row)
            self._insight_labels[key] = row.findChild(QLabel, "sw-kv-value")
        return card

    def _make_key_value_row(self, label_text):
        row = QWidget()
        row.setObjectName("sw-kv-row")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(label_text)
        label.setObjectName("sw-kv-label")
        value = QLabel("-")
        value.setObjectName("sw-kv-value")
        value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(label, 1)
        layout.addWidget(value, 1)
        return row

    def _build_settings_page(self):
        host = QWidget()
        host.setObjectName("sw-settings-host")
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Lightweight placeholder shown until the (heavy) SettingsCenterDialog
        # is materialized. Building the dialog eagerly blocks the UI thread for
        # the duration of all 9 tab constructions; deferring it lets the
        # workspace chrome and the default Profile page paint instantly.
        self._settings_loading = QLabel(SettingsWorkspaceText.LOADING_SETTINGS)
        self._settings_loading.setObjectName("sw-loading")
        self._settings_loading.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._settings_loading)

        self._settings_host_layout = layout
        self._settings_dialog = None
        self._pending_settings_key = None
        return host

    def _ensure_settings_dialog(self):
        """Build the embedded SettingsCenterDialog on demand, off the open path.

        Safe to call multiple times; only the first call does the heavy work.
        """
        if self._settings_dialog is not None:
            return self._settings_dialog

        dialog = SettingsCenterDialog(self.main_window)
        dialog.setWindowFlags(Qt.Widget)
        dialog.setModal(False)
        dialog.setMinimumSize(0, 0)
        dialog.setMaximumHeight(16777215)
        dialog.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        nav_panel = dialog.findChild(QWidget, "settings-nav-panel")
        if nav_panel is not None:
            nav_panel.hide()
            nav_panel.setMaximumWidth(0)
        splitter = dialog.findChild(QSplitter, "settings-splitter")
        if splitter is not None:
            splitter.setSizes([0, 1200])

        cancel_btn = getattr(dialog, "_cancel_btn", None)
        if cancel_btn is not None:
            try:
                cancel_btn.clicked.disconnect()
            except Exception:
                pass
            cancel_btn.setText(SettingsWorkspaceText.BACK_TO_APP)
            cancel_btn.clicked.connect(self.back_requested.emit)

        save_btn = getattr(dialog, "_save_btn", None)
        if save_btn is not None:
            try:
                save_btn.clicked.disconnect()
            except Exception:
                pass
            save_btn.clicked.connect(self._save_embedded_settings)

        if self._settings_loading is not None:
            self._settings_host_layout.removeWidget(self._settings_loading)
            self._settings_loading.deleteLater()
            self._settings_loading = None
        self._settings_host_layout.addWidget(dialog)
        self._settings_dialog = dialog

        try:
            dialog._apply_settings_styles()
        except Exception:
            pass

        pending = self._pending_settings_key
        self._pending_settings_key = None
        if pending:
            dialog.set_active_tab(pending)
        return dialog

    def _build_help_page(self):
        host = QWidget()
        host.setObjectName("sw-help-host")
        self._help_host_layout = QVBoxLayout(host)
        self._help_host_layout.setContentsMargins(0, 0, 0, 0)
        self._help_host_layout.setSpacing(0)
        self._rebuild_help_panel()
        return host

    def _build_about_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("sw-scroll")

        inner = QWidget()
        inner.setObjectName("sw-profile-inner")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(34, 28, 34, 36)
        layout.setSpacing(18)

        title = QLabel("Help & About")
        title.setObjectName("sw-page-kicker")
        layout.addWidget(title)

        about_card = QFrame()
        about_card.setObjectName("sw-content-card")
        about_layout = QVBoxLayout(about_card)
        about_layout.setContentsMargins(18, 16, 18, 16)
        about_layout.setSpacing(10)
        about_label = QLabel(about_html())
        about_label.setObjectName("sw-about-copy")
        about_label.setTextFormat(Qt.RichText)
        about_label.setWordWrap(True)
        about_layout.addWidget(about_label)
        layout.addWidget(about_card)

        project_card = QFrame()
        project_card.setObjectName("sw-content-card")
        project_layout = QVBoxLayout(project_card)
        project_layout.setContentsMargins(18, 16, 18, 16)
        project_layout.setSpacing(8)
        project_title = QLabel("Project Snapshot")
        project_title.setObjectName("sw-section-title")
        project_layout.addWidget(project_title)
        for label, value in self._about_project_rows():
            row = self._make_key_value_row(label)
            value_label = row.findChild(QLabel, "sw-kv-value")
            if value_label is not None:
                value_label.setText(value)
            project_layout.addWidget(row)
        layout.addWidget(project_card)
        layout.addStretch(1)

        scroll.setWidget(inner)
        return scroll

    def _about_project_rows(self):
        project_dir = getattr(self.main_window, "project_dir", None)
        image_files = getattr(self.main_window, "image_files", []) or []
        all_data = getattr(self.main_window, "all_typeset_data", {}) or {}
        page_count = len([f for f in image_files if "_typeset" not in str(f).lower()])
        area_count = 0
        text_count = 0
        for data in all_data.values():
            areas = data.get("areas", []) if isinstance(data, dict) else []
            area_count += len(areas)
            for area in areas:
                text = area.get("text", "") if isinstance(area, dict) else getattr(area, "text", "")
                if str(text or "").strip():
                    text_count += 1
        return [
            ("Folder", os.path.basename(project_dir) if project_dir else "No project loaded"),
            ("Pages", _format_number(page_count)),
            ("Text areas", _format_number(area_count)),
            ("Filled areas", _format_number(text_count)),
        ]

    def _rebuild_help_panel(self):
        if self._help_host_layout is None:
            return
        if self._help_dialog is not None:
            self._help_host_layout.removeWidget(self._help_dialog)
            self._help_dialog.deleteLater()
            self._help_dialog = None

        self._help_dialog = UnifiedHelpDialog(
            self.main_window,
            app_version=APP_VERSION,
            ai_providers=getattr(self.main_window, "AI_PROVIDERS", {}),
            openrouter_pricing_db=getattr(self.main_window, "openrouter_pricing_db", {}),
            usage_data=getattr(self.main_window, "usage_data", {}),
            total_cost=getattr(self.main_window, "total_cost", 0.0),
            usd_to_idr_rate=getattr(self.main_window, "usd_to_idr_rate", 16200.0),
            total_input_tokens=getattr(self.main_window, "total_input_tokens", 0),
            total_output_tokens=getattr(self.main_window, "total_output_tokens", 0),
            translated_count=getattr(self.main_window, "translated_count", 0),
            project_dir=getattr(self.main_window, "project_dir", None),
            image_files=getattr(self.main_window, "image_files", []),
            all_typeset_data=getattr(self.main_window, "all_typeset_data", {}),
            on_pricing_saved=getattr(self.main_window, "_on_unified_pricing_saved", None),
        )
        self._help_dialog.setWindowFlags(Qt.Widget)
        self._help_dialog.setModal(False)
        self._help_dialog.setProperty("embedded_settings_workspace", True)
        self._help_dialog.setMinimumSize(0, 0)
        self._help_dialog.setMaximumHeight(16777215)
        self._help_dialog.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        for btn in self._help_dialog.findChildren(QPushButton):
            if btn.text().strip().lower() == "close":
                btn.hide()
        self._help_host_layout.addWidget(self._help_dialog)

    def _on_nav_changed(self, current, previous):
        if current is None:
            return
        data = current.data(Qt.UserRole) or {}
        key = data.get("key")
        if key:
            self.set_active_section(key)

    def _filter_nav(self, text):
        needle = (text or "").strip().lower()
        for item in self._nav_rows:
            data = item.data(Qt.UserRole) or {}
            if data.get("section"):
                item.setHidden(False)
                continue
            haystack = data.get("text", "")
            item.setHidden(bool(needle and needle not in haystack))

    def _set_heatmap_mode(self, mode):
        self._heatmap_mode = mode
        for key, btn in self._mode_buttons.items():
            btn.setChecked(key == mode)
        snapshot = self._profile_snapshot()
        self.heatmap.set_activity(snapshot.get("activity_by_date", {}), mode=mode)
        if hasattr(self, "heatmap_range_label"):
            self.heatmap_range_label.setText(self.heatmap.range_summary())

    def set_active_section(self, key: str):
        key = key or "profile"
        key = {
            "help": "help_overview",
            "overview": "help_overview",
            "settings": "general",
            "apis": "api",
            "ocr": "ocr_plugins",
            "media": "media_tools",
        }.get(key, key)
        self._active_key = key

        if key == "profile":
            self.stack.setCurrentWidget(self.profile_page)
            self.refresh_profile()
        elif key in APP_SETTINGS_KEYS:
            self.stack.setCurrentWidget(self.settings_page)
            if self._settings_dialog is not None:
                self._settings_dialog.set_active_tab(key)
            else:
                # Dialog not yet built — materialize it now so the requested
                # tab is shown. Building happens once; subsequent opens reuse it.
                self._pending_settings_key = key
                QTimer.singleShot(0, self._ensure_settings_dialog)
        elif key == "help_overview":
            self.stack.setCurrentWidget(self.about_page)
        elif key in HELP_TAB_KEYS:
            self.stack.setCurrentWidget(self.help_page)
            if self._help_dialog is not None and hasattr(self._help_dialog, "tabs"):
                self._help_dialog.tabs.setCurrentIndex(HELP_TAB_KEYS[key])

        nav_key = "usage" if key in ("pricing", "analytics") else key
        self._select_nav_key(nav_key)

    def _select_nav_key(self, key):
        for row in range(self.nav_list.count()):
            item = self.nav_list.item(row)
            data = item.data(Qt.UserRole) or {}
            if data.get("key") == key:
                if self.nav_list.currentItem() is not item:
                    self.nav_list.blockSignals(True)
                    self.nav_list.setCurrentItem(item)
                    self.nav_list.blockSignals(False)
                return

    def refresh(self):
        self.refresh_profile()
        if self._active_key == "help_overview":
            old_about = self.about_page
            idx = self.stack.indexOf(old_about)
            self.about_page = self._build_about_page()
            self.stack.removeWidget(old_about)
            old_about.deleteLater()
            self.stack.insertWidget(idx, self.about_page)
            self.stack.setCurrentWidget(self.about_page)
        if self._active_key in HELP_TAB_KEYS:
            current_tab = HELP_TAB_KEYS.get(self._active_key, 0)
            self._rebuild_help_panel()
            if self._help_dialog is not None and hasattr(self._help_dialog, "tabs"):
                self._help_dialog.tabs.setCurrentIndex(current_tab)

    def refresh_profile(self):
        snapshot = self._profile_snapshot()
        display_name = snapshot.get("display_name") or SettingsWorkspaceText.PROFILE_NAME_FALLBACK
        initials = "".join(part[:1] for part in display_name.replace("_", " ").split()[:2]).upper() or "MT"
        self.avatar_label.setText(initials[:2])
        self.profile_name_label.setText(display_name)
        self.profile_handle_label.setText(
            f"{SettingsWorkspaceText.PROFILE_HANDLE} - {SettingsWorkspaceText.PROFILE_BADGE}"
        )

        lifetime_input = int(snapshot.get("lifetime_input_tokens", 0) or 0)
        lifetime_output = int(snapshot.get("lifetime_output_tokens", 0) or 0)
        lifetime_tokens = lifetime_input + lifetime_output
        values = {
            "lifetime_tokens": _format_number(lifetime_tokens),
            "input_tokens": _format_number(lifetime_input),
            "output_tokens": _format_number(lifetime_output),
            "cost": _format_money(snapshot.get("lifetime_cost_usd", 0.0)),
            "longest_session": _format_duration(snapshot.get("longest_session_seconds", 0)),
            "current_streak": f"{int(snapshot.get('current_streak', 0) or 0)} days",
            "longest_streak": f"{int(snapshot.get('longest_streak', 0) or 0)} days",
        }
        for key, value in values.items():
            label = self._profile_labels.get(key)
            if label is not None:
                label.setText(value)

        activity = snapshot.get("activity_by_date", {})
        today_key = date.today().isoformat()
        today = activity.get(today_key, {})
        today_tokens = int(today.get("input_tokens", 0) or 0) + int(today.get("output_tokens", 0) or 0)
        self._set_insight("today_tokens", _format_number(today_tokens))
        self._set_insight("today_cost", _format_money(today.get("cost_usd", 0.0)))
        self._set_insight("translated", _format_number(snapshot.get("translated_count", 0)))
        self._set_insight("project_pages", _format_number(snapshot.get("project_pages", 0)))
        self._set_insight("most_active_day", snapshot.get("most_active_day", "None"))
        self._set_insight("top_provider", snapshot.get("top_provider", "None"))
        self._set_insight("top_model", snapshot.get("top_model", "None"))
        self._set_insight("daily_requests", _format_number(snapshot.get("daily_requests", 0)))
        self._set_insight("rpm_snapshot", _format_number(snapshot.get("rpm_snapshot", 0)))
        self._set_insight("data_since", snapshot.get("first_seen", "-"))
        self._set_heatmap_mode(self._heatmap_mode)

    def _set_insight(self, key, value):
        label = self._insight_labels.get(key)
        if label is not None:
            label.setText(str(value))

    def _profile_snapshot(self):
        if hasattr(self.main_window, "get_profile_usage_snapshot"):
            try:
                return self.main_window.get_profile_usage_snapshot()
            except Exception:
                pass
        usage = copy.deepcopy(getattr(self.main_window, "usage_data", {}) or {})
        profile = usage.get("profile_usage", {}) if isinstance(usage, dict) else {}
        return dict(profile or {})

    def _save_embedded_settings(self):
        if self._settings_dialog is None:
            return
        if self._settings_dialog._commit_settings(close_dialog=False):
            notify_toast(self, "Settings saved", "Settings are active in the main window.", kind="success")
            self.refresh()

    def refresh_theme(self):
        self.setStyleSheet(_settings_workspace_qss())
        if self._settings_dialog is not None:
            try:
                self._settings_dialog._apply_settings_styles()
            except Exception:
                pass
        if self._help_dialog is not None:
            try:
                self._help_dialog.setStyleSheet(self._help_dialog.styleSheet())
            except Exception:
                pass


def _settings_workspace_qss() -> str:
    c = theme.COLORS
    radius = theme.RADIUS
    # Accent-tinted backgrounds derived from the active palette so every dark
    # theme preset (codex, catppuccin, nord, …) picks up the same soft glow.
    accent_soft = c["accent"]
    return f"""
    QWidget#settings-workspace {{
        background: {c["bg"]};
        color: {c["text"]};
        font-family: {theme.FONT_FAMILY};
    }}
    QWidget#sw-sidebar {{
        background: {c["panel"]};
        border-right: 1px solid {c["border"]};
    }}
    QPushButton#sw-back-btn {{
        background: transparent;
        border: none;
        border-left: 3px solid transparent;
        color: {c["muted"]};
        text-align: left;
        padding: 9px 12px 9px 13px;
        font-weight: 600;
    }}
    QPushButton#sw-back-btn:hover {{
        color: {c["text"]};
        background: {c["card_alt"]};
        border-left: 3px solid {c["muted"]};
        border-top-right-radius: {radius["sm"]}px;
        border-bottom-right-radius: {radius["sm"]}px;
    }}
    QLineEdit#sw-search {{
        background: {c["card_alt"]};
        border: 1px solid {c["border"]};
        border-radius: {radius["md"]}px;
        color: {c["text"]};
        padding: 9px 12px;
        selection-background-color: {c["accent"]};
    }}
    QLineEdit#sw-search:focus {{
        border: 1px solid {c["accent"]};
    }}
    QListWidget#sw-nav-list {{
        background: transparent;
        border: none;
        outline: none;
        color: {c["text"]};
    }}
    QListWidget#sw-nav-list::item {{
        color: {c["text"]};
        padding: 9px 12px;
        border-radius: {radius["md"]}px;
        border-left: 3px solid transparent;
    }}
    QListWidget#sw-nav-list::item:selected {{
        background: {c["card_alt"]};
        color: {c["accent"]};
        border-left: 3px solid {c["accent"]};
        font-weight: 600;
    }}
    QListWidget#sw-nav-list::item:hover:!selected {{
        background: {c["card_alt"]};
        color: {c["text"]};
    }}
    QLabel#sw-version {{
        color: {c["muted"]};
        padding: 8px 12px;
        font-size: 8.5pt;
    }}
    QStackedWidget#sw-stack,
    QScrollArea#sw-scroll,
    QWidget#sw-profile-inner,
    QWidget#sw-settings-host,
    QWidget#sw-help-host {{
        background: {c["bg"]};
        border: none;
    }}
    QLabel#sw-page-kicker {{
        color: {c["text"]};
        font-size: 11pt;
        font-weight: 800;
        letter-spacing: 0.2px;
    }}
    QLabel#sw-loading {{
        color: {c["muted"]};
        font-size: 11pt;
        padding: 48px;
    }}
    QLabel#sw-avatar {{
        background: {c["accent"]};
        color: #020617;
        border-radius: 42px;
        font-size: 23pt;
        font-weight: 800;
    }}
    QLabel#sw-profile-name {{
        color: {c["text"]};
        font-size: 17pt;
        font-weight: 800;
    }}
    QLabel#sw-profile-handle {{
        color: {c["muted"]};
        font-size: 9pt;
    }}
    QWidget#sw-stat-strip {{
        background: {c["panel"]};
        border: 1px solid {c["border"]};
        border-radius: {radius["lg"]}px;
    }}
    QWidget#sw-stat-cell {{
        background: transparent;
        border-right: 1px solid {c["border"]};
    }}
    QLabel#sw-stat-value {{
        color: {c["text"]};
        font-size: 11pt;
        font-weight: 800;
    }}
    QLabel#sw-stat-label,
    QLabel#sw-kv-label {{
        color: {c["muted"]};
        font-size: 9pt;
    }}
    QLabel#sw-section-title {{
        color: {c["text"]};
        font-size: 10.5pt;
        font-weight: 800;
    }}
    QLabel#sw-range-label {{
        color: {c["muted"]};
        font-size: 9pt;
        font-weight: 600;
        padding-left: 10px;
    }}
    QFrame#sw-info-card {{
        background: {c["panel"]};
        border: 1px solid {c["border"]};
        border-radius: {radius["lg"]}px;
    }}
    QFrame#sw-content-card {{
        background: {c["panel"]};
        border: 1px solid {c["border"]};
        border-radius: {radius["md"]}px;
    }}
    QLabel#sw-about-copy {{
        color: {c["text"]};
        line-height: 130%;
    }}
    QWidget#sw-kv-row {{
        background: transparent;
        min-height: 28px;
    }}
    QLabel#sw-kv-value {{
        color: {c["text"]};
        font-weight: 700;
    }}
    QPushButton#sw-mode-btn,
    QPushButton#sw-secondary-btn {{
        background: transparent;
        color: {c["muted"]};
        border: 1px solid {c["border"]};
        border-radius: {radius["sm"]}px;
        padding: 6px 12px;
        font-weight: 700;
    }}
    QPushButton#sw-mode-btn:hover,
    QPushButton#sw-secondary-btn:hover {{
        color: {c["text"]};
        background: {c["card_alt"]};
        border-color: {c["accent"]};
    }}
    QPushButton#sw-mode-btn:checked {{
        color: #020617;
        background: {c["accent"]};
        border-color: {c["accent"]};
    }}
    """
