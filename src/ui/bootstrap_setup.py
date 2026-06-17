"""First-run setup window for the packaged MangaTranslate launcher."""

import os
import shutil
import subprocess

from PyQt5.QtCore import QEventLoop, QObject, QSize, QThread, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.app_info import APP_NAME
from src.ui.texts import BootstrapText
from src.ui.theme import COLORS, FONT_FAMILY


class BootstrapWorker(QObject):
    statusChanged = pyqtSignal(str)
    logLine = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, base_dir):
        super().__init__()
        self.base_dir = os.path.abspath(base_dir)
        self.venv_dir = os.path.join(self.base_dir, "venv")
        self.requirements_path = os.path.join(self.base_dir, "requirements.txt")

    def run(self):
        try:
            self._run_setup()
        except Exception as exc:
            self.logLine.emit(f"[ERROR] {exc}")
            self.statusChanged.emit(BootstrapText.STATUS_FAILED)
            self.finished.emit(False, str(exc))

    def _run_setup(self):
        self.statusChanged.emit(BootstrapText.STATUS_CHECKING)
        self.logLine.emit(f"Project folder: {self.base_dir}")

        main_py = os.path.join(self.base_dir, "main.py")
        if not os.path.exists(main_py):
            raise RuntimeError(BootstrapText.MAIN_MISSING)
        if not os.path.exists(self.requirements_path):
            raise RuntimeError(BootstrapText.REQUIREMENTS_MISSING)

        python_cmd = self._find_system_python()
        self.logLine.emit("Python found: " + " ".join(python_cmd))

        venv_python = os.path.join(self.venv_dir, "Scripts", "python.exe")
        if not os.path.exists(venv_python):
            self.statusChanged.emit(BootstrapText.STATUS_CREATING_VENV)
            self._run_command(
                python_cmd + ["-m", "venv", self.venv_dir],
                "Creating virtual environment",
            )

        if not os.path.exists(venv_python):
            raise RuntimeError("venv Python was not created successfully.")

        self.statusChanged.emit(BootstrapText.STATUS_UPGRADING_PIP)
        self._run_command(
            [venv_python, "-m", "pip", "install", "--upgrade", "pip"],
            "Upgrading pip",
        )

        self.statusChanged.emit(BootstrapText.STATUS_INSTALLING_REQUIREMENTS)
        self._run_command(
            [venv_python, "-m", "pip", "install", "-r", self.requirements_path],
            "Installing requirements",
        )

        self.statusChanged.emit(BootstrapText.STATUS_READY)
        self.logLine.emit("[OK] Virtual environment is ready.")
        self.finished.emit(True, "")

    def _find_system_python(self):
        candidates = []
        if os.name == "nt":
            candidates.append(["py", "-3"])
        candidates.extend([["python"], ["python3"]])

        for command in candidates:
            executable = shutil.which(command[0])
            if not executable:
                continue
            probe = command + ["--version"]
            try:
                result = subprocess.run(
                    probe,
                    cwd=self.base_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=15,
                    creationflags=self._creation_flags(),
                )
            except Exception:
                continue
            if result.returncode == 0:
                version = (result.stdout or "").strip()
                if version:
                    self.logLine.emit(version)
                return command
        raise RuntimeError(BootstrapText.PYTHON_MISSING)

    def _run_command(self, command, label):
        self.logLine.emit("")
        self.logLine.emit(f"[{label}]")
        self.logLine.emit("> " + " ".join(command))

        env = os.environ.copy()
        bin_dir = os.path.join(self.base_dir, "bin")
        if os.path.isdir(bin_dir):
            env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")
        env["PYTHONUNBUFFERED"] = "1"
        env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

        proc = subprocess.Popen(
            command,
            cwd=self.base_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            creationflags=self._creation_flags(),
        )

        assert proc.stdout is not None
        for line in proc.stdout:
            clean = line.rstrip()
            if clean:
                self.logLine.emit(clean)

        return_code = proc.wait()
        if return_code != 0:
            raise RuntimeError(f"{label} failed with exit code {return_code}.")

    @staticmethod
    def _creation_flags():
        if os.name == "nt":
            return subprocess.CREATE_NO_WINDOW
        return 0


class BootstrapSetupWindow(QWidget):
    setupFinished = pyqtSignal(bool, str)

    def __init__(self, base_dir, icon_path=None, parent=None):
        super().__init__(parent)
        self.base_dir = base_dir
        self._running = False
        self._finished = False
        self._emitted = False
        self._success = False
        self._message = ""
        self._thread = None
        self._worker = None

        self.setWindowTitle(BootstrapText.TITLE)
        self.setWindowFlags(
            Qt.Window
            | Qt.CustomizeWindowHint
            | Qt.WindowTitleHint
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowSystemMenuHint
        )
        self.setMinimumSize(680, 500)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        card = QFrame()
        card.setObjectName("bootstrapCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        header = QHBoxLayout()
        header.setSpacing(14)
        icon_label = QLabel()
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)
        if icon_path and os.path.exists(icon_path):
            icon = QIcon(icon_path)
            icon_label.setPixmap(icon.pixmap(QSize(46, 46)))
            self.setWindowIcon(icon)
        header.addWidget(icon_label)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        title = QLabel(APP_NAME)
        title.setObjectName("bootstrapTitle")
        subtitle = QLabel(BootstrapText.SUBTITLE)
        subtitle.setObjectName("bootstrapSubtitle")
        subtitle.setWordWrap(True)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box, 1)
        layout.addLayout(header)

        self.status_label = QLabel(BootstrapText.STATUS_STARTING)
        self.status_label.setObjectName("bootstrapStatus")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        layout.addWidget(self.progress)

        hint = QLabel(BootstrapText.HINT)
        hint.setObjectName("bootstrapHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.log_output = QPlainTextEdit()
        self.log_output.setObjectName("bootstrapLog")
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumBlockCount(800)
        layout.addWidget(self.log_output, 1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        self.minimize_button = QPushButton("Minimize")
        self.minimize_button.clicked.connect(self.showMinimized)
        footer.addWidget(self.minimize_button)
        self.close_button = QPushButton("Close")
        self.close_button.setEnabled(False)
        self.close_button.clicked.connect(self._finish_from_button)
        footer.addWidget(self.close_button)
        layout.addLayout(footer)

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
        self.show()
        QApplication.processEvents()

    def start(self):
        if self._running:
            return
        self._running = True
        self.append_log(BootstrapText.STATUS_STARTING)

        self._thread = QThread(self)
        self._worker = BootstrapWorker(self.base_dir)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.statusChanged.connect(self.set_status)
        self._worker.logLine.connect(self.append_log)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def set_status(self, message):
        if message:
            self.status_label.setText(message)
            self.append_log(message)

    def append_log(self, line):
        if line is None:
            return
        self.log_output.appendPlainText(str(line))
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def closeEvent(self, event):
        if self._running and not self._finished:
            event.ignore()
            self.showMinimized()
            return
        if self._finished and not self._emitted:
            self._emit_finished(close_window=False)
        super().closeEvent(event)

    def _on_worker_finished(self, success, message):
        self._running = False
        self._finished = True
        self._success = bool(success)
        self._message = message or ""
        self.progress.setRange(0, 1)
        self.progress.setValue(1 if success else 0)
        self.close_button.setEnabled(True)
        if success:
            self.close_button.setText("Opening...")
            self.close_button.setEnabled(False)
            QTimer.singleShot(900, self._emit_finished)
        else:
            self.close_button.setText("Close")

    def _finish_from_button(self):
        if self._finished:
            self._emit_finished()

    def _emit_finished(self, close_window=True):
        if self._emitted:
            return
        self._emitted = True
        self.setupFinished.emit(self._success, self._message)
        if close_window:
            self.close()

    def _stylesheet(self):
        return f"""
        QWidget {{
            background-color: {COLORS["bg"]};
            color: {COLORS["text"]};
            font-family: {FONT_FAMILY};
            font-size: 10pt;
        }}
        QFrame#bootstrapCard {{
            background-color: {COLORS["panel"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 14px;
        }}
        QLabel {{
            background: transparent;
            color: {COLORS["text"]};
        }}
        QLabel#bootstrapTitle {{
            color: #f8fafc;
            font-size: 18pt;
            font-weight: 800;
        }}
        QLabel#bootstrapSubtitle {{
            color: {COLORS["text"]};
            font-size: 10pt;
        }}
        QLabel#bootstrapStatus {{
            color: #e2e8f0;
            font-size: 10pt;
            font-weight: 700;
        }}
        QLabel#bootstrapHint {{
            color: {COLORS["muted"]};
            font-size: 9pt;
        }}
        QPlainTextEdit#bootstrapLog {{
            background-color: {COLORS["card_alt"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 8px;
            color: #94a3b8;
            font-family: Consolas, 'Cascadia Mono', monospace;
            font-size: 9pt;
            padding: 8px;
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
        QPushButton {{
            background-color: {COLORS["border"]};
            color: {COLORS["text"]};
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: 600;
        }}
        QPushButton:hover:!disabled {{
            background-color: #334155;
            border-color: {COLORS["accent"]};
        }}
        QPushButton:disabled {{
            color: {COLORS["muted"]};
            background-color: #0f131a;
            border-color: {COLORS["border"]};
        }}
        """


def run_bootstrap_setup(base_dir, icon_path=None):
    window = BootstrapSetupWindow(base_dir, icon_path)
    loop = QEventLoop()
    result = {"success": False, "message": ""}

    def _finish(success, message):
        result["success"] = bool(success)
        result["message"] = message or ""
        loop.quit()

    window.setupFinished.connect(_finish)
    window.show_centered()
    window.start()
    loop.exec_()
    return result["success"], result["message"]
