"""Animated startup splash screen for MangaTranslate."""

from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from src.core.app_info import APP_NAME
from src.ui.texts import StartupText
from src.ui.theme import COLORS, FONT_FAMILY


class SpinnerWidget(QWidget):
    """Small indeterminate spinner used by the startup splash."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.setInterval(45)
        self._timer.timeout.connect(self._tick)
        self.setFixedSize(44, 44)

    def sizeHint(self):
        return QSize(44, 44)

    def start(self):
        if not self._timer.isActive():
            self._timer.start()

    def stop(self):
        self._timer.stop()

    def _tick(self):
        self._angle = (self._angle + 30) % 360
        self.update()

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center = self.rect().center()
        radius = min(self.width(), self.height()) / 2 - 6

        for index in range(12):
            painter.save()
            painter.translate(center)
            painter.rotate(self._angle + index * 30)
            alpha = int(45 + (index / 11) * 210)
            color = QColor(COLORS["accent"])
            color.setAlpha(alpha)
            pen = QPen(color, 3, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(pen)
            painter.drawLine(0, int(-radius), 0, int(-radius + 8))
            painter.restore()


class StartupSplash(QWidget):
    """Frameless loading window shown while the main application initializes."""

    def __init__(self, icon_path=None, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(460, 280)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        card = QFrame()
        card.setObjectName("startupCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 24, 28, 24)
        card_layout.setSpacing(14)

        header = QHBoxLayout()
        header.setSpacing(14)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(54, 54)
        self.icon_label.setAlignment(Qt.AlignCenter)
        if icon_path:
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                self.icon_label.setPixmap(
                    pixmap.scaled(52, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
        header.addWidget(self.icon_label)

        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        self.title_label = QLabel(APP_NAME)
        self.title_label.setObjectName("startupTitle")
        self.version_label = QLabel(StartupText.VERSION_LABEL)
        self.version_label.setObjectName("startupVersion")
        title_block.addWidget(self.title_label)
        title_block.addWidget(self.version_label)
        header.addLayout(title_block, 1)
        card_layout.addLayout(header)

        self.subtitle_label = QLabel(StartupText.SUBTITLE)
        self.subtitle_label.setObjectName("startupSubtitle")
        self.subtitle_label.setWordWrap(True)
        card_layout.addWidget(self.subtitle_label)

        middle = QHBoxLayout()
        middle.setSpacing(14)
        self.spinner = SpinnerWidget()
        middle.addWidget(self.spinner, 0, Qt.AlignVCenter)

        status_block = QVBoxLayout()
        status_block.setSpacing(8)
        self.status_label = QLabel(StartupText.STATUS_STARTING)
        self.status_label.setObjectName("startupStatus")
        self.status_label.setWordWrap(True)
        status_block.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        status_block.addWidget(self.progress)
        middle.addLayout(status_block, 1)
        card_layout.addLayout(middle)

        hint = QLabel(StartupText.HINT)
        hint.setObjectName("startupHint")
        hint.setWordWrap(True)
        card_layout.addWidget(hint)

        outer.addWidget(card)
        self.setStyleSheet(self._stylesheet())

    def show_centered(self):
        screen = QApplication.primaryScreen()
        if screen is not None:
            geometry = screen.availableGeometry()
            self.move(
                geometry.center().x() - self.width() // 2,
                geometry.center().y() - self.height() // 2,
            )
        self.spinner.start()
        self.show()
        self.raise_()
        QApplication.processEvents()

    def set_status(self, message):
        if message:
            self.status_label.setText(message)
        QApplication.processEvents()

    def finish(self, window=None):
        self.spinner.stop()
        if window is not None:
            window.raise_()
            window.activateWindow()
        self.close()
        QApplication.processEvents()

    def _stylesheet(self):
        return f"""
        QWidget {{
            font-family: {FONT_FAMILY};
            color: {COLORS["text"]};
            background: transparent;
        }}
        QFrame#startupCard {{
            background-color: {COLORS["panel"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 14px;
        }}
        QLabel#startupTitle {{
            color: #f8fafc;
            font-size: 18pt;
            font-weight: 800;
        }}
        QLabel#startupVersion {{
            color: {COLORS["accent"]};
            font-size: 10pt;
            font-weight: 700;
        }}
        QLabel#startupSubtitle {{
            color: {COLORS["text"]};
            font-size: 10pt;
        }}
        QLabel#startupStatus {{
            color: #e2e8f0;
            font-size: 10pt;
            font-weight: 600;
        }}
        QLabel#startupHint {{
            color: {COLORS["muted"]};
            font-size: 9pt;
        }}
        QProgressBar {{
            background-color: {COLORS["card_alt"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 4px;
        }}
        QProgressBar::chunk {{
            background-color: {COLORS["accent"]};
            border-radius: 4px;
        }}
        """
