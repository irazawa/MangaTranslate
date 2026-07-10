"""Non-blocking in-app notifications for the main PyQt UI."""

from __future__ import annotations

from typing import Callable, Optional

from PyQt5.QtCore import QObject, QEvent, QTimer, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.ui.theme import COLORS, notification_frame_qss


_KIND_COLORS = {
    "info": "#38bdf8",
    "success": "#22c55e",
    "warning": "#f59e0b",
    "error": "#ef4444",
}


def _kind_color(kind: str) -> str:
    kind = (kind or "info").lower()
    if kind == "info":
        return COLORS["accent"]
    if kind == "success":
        return COLORS["success"]
    if kind == "warning":
        return COLORS["warning"]
    if kind == "error":
        return COLORS["danger"]
    return _KIND_COLORS.get(kind, COLORS["accent"])


class _NotificationFrame(QFrame):
    dismissed = pyqtSignal(object)

    def __init__(
        self,
        title: str,
        message: str = "",
        *,
        kind: str = "info",
        compact: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._closed = False
        self.kind = (kind or "info").lower()
        self.setObjectName("appNotification")
        self.setProperty("kind", self.kind)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        accent = _kind_color(self.kind)
        radius = 7 if compact else 8
        self.setStyleSheet(notification_frame_qss(accent, radius=radius))

        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 9 if compact else 10, 8, 9 if compact else 10)
        outer.setSpacing(10)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("notificationTitle")
        self.title_label.setWordWrap(True)
        text_layout.addWidget(self.title_label)

        self.message_label = QLabel(message)
        self.message_label.setObjectName("notificationMessage")
        self.message_label.setWordWrap(True)
        self.message_label.setVisible(bool(message))
        text_layout.addWidget(self.message_label)

        outer.addLayout(text_layout, 1)

        self.action_button: Optional[QPushButton] = None

        self.close_button = QPushButton("x")
        self.close_button.setObjectName("notificationClose")
        self.close_button.setToolTip("Dismiss")
        self.close_button.clicked.connect(self.close_notification)
        outer.addWidget(self.close_button, 0, Qt.AlignTop)

    def set_content(self, title: str, message: str = "", kind: Optional[str] = None):
        self.title_label.setText(title)
        self.message_label.setText(message)
        self.message_label.setVisible(bool(message))
        if kind and kind.lower() != self.kind:
            self.kind = kind.lower()
            self.setProperty("kind", self.kind)
            self.setStyleSheet(notification_frame_qss(_kind_color(self.kind)))

    def set_action(self, text: Optional[str], callback: Optional[Callable[[], None]]):
        if self.action_button is not None:
            self.layout().removeWidget(self.action_button)
            self.action_button.deleteLater()
            self.action_button = None

        if not text or callback is None:
            return

        self.action_button = QPushButton(text)
        self.action_button.setObjectName("notificationAction")
        self.action_button.clicked.connect(callback)
        self.layout().insertWidget(self.layout().count() - 1, self.action_button, 0, Qt.AlignTop)

    def close_notification(self):
        if self._closed:
            return
        self._closed = True
        self.dismissed.emit(self)


class NotificationCenter(QObject):
    """Overlay manager for toast and banner notifications."""

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self._toasts = []
        self._banners = {}
        self._toast_host = self._make_host("toastHost", Qt.AlignTop | Qt.AlignRight)
        self._banner_host = self._make_host("bannerHost", Qt.AlignTop | Qt.AlignHCenter)
        self.window.installEventFilter(self)
        self.reposition()

    def _make_host(self, object_name: str, alignment: Qt.Alignment):
        host = QWidget(self.window)
        host.setObjectName(object_name)
        host.setAttribute(Qt.WA_StyledBackground, False)
        host.setStyleSheet("background: transparent;")
        host.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)

        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(alignment)
        host.hide()
        return host

    def eventFilter(self, watched, event):
        if watched is self.window and event.type() in (QEvent.Resize, QEvent.Show):
            QTimer.singleShot(0, self.reposition)
        return super().eventFilter(watched, event)

    def _top_offset(self) -> int:
        top = 12
        try:
            menu_bar = self.window.menuBar()
            if menu_bar and menu_bar.isVisible():
                top += menu_bar.height()
        except Exception:
            pass
        return top

    def reposition(self):
        if self.window is None:
            return

        width = max(320, self.window.width())
        height = max(160, self.window.height())
        margin = 16
        top = self._top_offset()

        banner_width = max(280, min(760, width - (margin * 2)))
        banner_height = min(
            max(1, self._banner_host.sizeHint().height()),
            max(56, height - top - 48),
        )
        self._banner_host.setGeometry(
            max(margin, (width - banner_width) // 2),
            top,
            banner_width,
            banner_height,
        )

        visible_banner_height = self._banner_host.sizeHint().height() if self._banners else 0
        toast_top = top + (min(visible_banner_height, 180) + 10 if visible_banner_height else 0)
        toast_width = max(280, min(380, width - (margin * 2)))
        toast_height = min(
            max(1, self._toast_host.sizeHint().height()),
            max(56, height - toast_top - margin),
        )
        self._toast_host.setGeometry(
            max(margin, width - toast_width - margin),
            toast_top,
            toast_width,
            toast_height,
        )

        self._banner_host.raise_()
        self._toast_host.raise_()

    def show_toast(self, title: str, message: str = "", *, kind: str = "info", timeout_ms: int = 3500):
        toast = _NotificationFrame(title, message, kind=kind, compact=True, parent=self._toast_host)
        toast.dismissed.connect(self._remove_toast)
        self._toasts.append(toast)
        self._toast_host.layout().insertWidget(0, toast)
        self._toast_host.show()
        self._toast_host.raise_()
        self.reposition()

        if timeout_ms and timeout_ms > 0:
            QTimer.singleShot(timeout_ms, toast.close_notification)
        return toast

    def _remove_toast(self, toast):
        if toast in self._toasts:
            self._toasts.remove(toast)
        toast.setParent(None)
        toast.deleteLater()
        if not self._toasts:
            self._toast_host.hide()
        self.reposition()

    def show_banner(
        self,
        key: str,
        title: str,
        message: str = "",
        *,
        kind: str = "warning",
        action_text: Optional[str] = None,
        action: Optional[Callable[[], None]] = None,
    ):
        if not key:
            key = f"{title}:{message}"

        banner = self._banners.get(key)
        if banner is None:
            banner = _NotificationFrame(title, message, kind=kind, compact=False, parent=self._banner_host)
            banner.dismissed.connect(lambda widget, banner_key=key: self.dismiss_banner(banner_key))
            self._banners[key] = banner
            self._banner_host.layout().addWidget(banner)
        else:
            banner.set_content(title, message, kind)

        banner.set_action(action_text, action)
        self._banner_host.show()
        self._banner_host.raise_()
        self.reposition()
        return banner

    def dismiss_banner(self, key: str):
        banner = self._banners.pop(key, None)
        if banner is None:
            return
        banner.setParent(None)
        banner.deleteLater()
        if not self._banners:
            self._banner_host.hide()
        self.reposition()


def _notification_center_for(widget) -> Optional[NotificationCenter]:
    if widget is None:
        return None

    try:
        top_window = widget.window() if hasattr(widget, "window") else widget
    except Exception:
        top_window = widget

    if top_window is not None:
        center = getattr(top_window, "notification_center", None)
        if center is not None:
            return center
        try:
            center = NotificationCenter(top_window)
            setattr(top_window, "notification_center", center)
            return center
        except Exception:
            pass

    current = widget
    seen = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        center = getattr(current, "notification_center", None)
        if center is not None:
            return center
        try:
            window = current.window()
        except Exception:
            window = None
        if window is not None and window is not current:
            current = window
        else:
            current = current.parentWidget() if hasattr(current, "parentWidget") else None
    return None


def _status_fallback(parent, title: str, message: str = "", timeout_ms: int = 4000):
    text = title if not message else f"{title}: {message}"
    try:
        window = parent.window() if hasattr(parent, "window") else parent
        status_bar = window.statusBar() if hasattr(window, "statusBar") else None
        if status_bar is not None:
            status_bar.showMessage(text, timeout_ms)
            return
    except Exception:
        pass
    print(text)


def notify_toast(parent, title: str, message: str = "", *, kind: str = "info", timeout_ms: int = 3500):
    center = _notification_center_for(parent)
    if center is not None:
        return center.show_toast(title, message, kind=kind, timeout_ms=timeout_ms)
    _status_fallback(parent, title, message, timeout_ms)
    return None


def notify_banner(
    parent,
    key: str,
    title: str,
    message: str = "",
    *,
    kind: str = "warning",
    action_text: Optional[str] = None,
    action: Optional[Callable[[], None]] = None,
):
    center = _notification_center_for(parent)
    if center is not None:
        return center.show_banner(
            key,
            title,
            message,
            kind=kind,
            action_text=action_text,
            action=action,
        )
    _status_fallback(parent, title, message, 5000)
    return None


def dismiss_banner(parent, key: str):
    center = _notification_center_for(parent)
    if center is not None:
        center.dismiss_banner(key)
