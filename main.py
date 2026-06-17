# Manga OCR & Typeset Tool v14.8.4
import os
import sys
import traceback
import warnings

# Tambahkan folder bin ke environment PATH agar system dependencies (FFmpeg & Deno) terdeteksi otomatis
root_dir = os.path.dirname(os.path.abspath(__file__))
bin_dir = os.path.join(root_dir, "bin")
if os.path.exists(bin_dir) and bin_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")

warnings.filterwarnings("ignore")

# CRITICAL: Import torch BEFORE cv2/PyQt5/anything else that loads DLLs.
# On Windows, OpenCV's DLLs conflict with PyTorch's c10.dll if cv2 is loaded
# first, causing [WinError 1114] during torch initialisation.
# Loading torch here pins its DLLs into the process before any other library
# can interfere.
try:
    import torch  # noqa: F401  — side-effect import to pre-load DLLs
except Exception:
    pass  # torch missing or broken — handled gracefully later in config.py

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMessageBox

from src.core.app_info import APP_VERSION
from src.ui.startup_splash import StartupSplash
from src.ui.texts import StartupText


def configure_windows_app_id():
    if os.name != 'nt':
        return
    try:
        import ctypes
        app_version_id = APP_VERSION.replace('.', '_')
        myappid = f'irazawa.mangatranslate.app.v{app_version_id}'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Mencegah aplikasi keluar premature saat dialog peringatan ditutup

    configure_windows_app_id()

    # Set icon untuk aplikasi global
    icon_path = os.path.join(root_dir, "src", "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    splash = StartupSplash(icon_path if os.path.exists(icon_path) else None)
    splash.show_centered()

    try:
        import fitz
    except ImportError:
        splash.close()
        QMessageBox.critical(None, "Dependency Missing", "PyMuPDF not installed. 'pip install PyMuPDF'.")
        return 1

    try:
        splash.set_status(StartupText.STATUS_IMPORTING_APP)
        from src.ui.main_window import MangaOCRApp
    except Exception as e:
        splash.close()
        traceback.print_exc()
        QMessageBox.critical(None, "Startup Error", f"Could not load application modules.\n\n{e}")
        return 1

    # Suppress initial warning dialogs for engines and API keys
    pass

    try:
        window = MangaOCRApp(startup_status_callback=splash.set_status)
        if os.path.exists(icon_path):
            window.setWindowIcon(QIcon(icon_path))
        window.showMaximized()
        splash.finish(window)
        app.setQuitOnLastWindowClosed(True)  # Kembalikan perilaku standar agar aplikasi keluar normal saat window utama ditutup
        return app.exec_()
    except Exception as e:
        splash.close()
        traceback.print_exc()
        QMessageBox.critical(None, "Startup Error", f"Could not start application.\n\n{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
