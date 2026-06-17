import os
import subprocess
import sys
import time


def _base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _creation_flags():
    if os.name == "nt":
        return subprocess.CREATE_NO_WINDOW
    return 0


def _message_box(title, message):
    if os.name != "nt":
        print(f"{title}: {message}")
        return
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, str(message), str(title), 0x10)
    except Exception:
        print(f"{title}: {message}")


def _prepare_path(base_dir):
    os.chdir(base_dir)
    bin_dir = os.path.join(base_dir, "bin")
    if os.path.isdir(bin_dir):
        os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")


def _venv_python_paths(base_dir):
    scripts_dir = os.path.join(base_dir, "venv", "Scripts")
    return (
        os.path.join(scripts_dir, "python.exe"),
        os.path.join(scripts_dir, "pythonw.exe"),
    )


def _needs_first_run_setup(base_dir):
    python_exe, pythonw_exe = _venv_python_paths(base_dir)
    main_py = os.path.join(base_dir, "main.py")
    return not os.path.exists(main_py) or (
        not os.path.exists(python_exe) and not os.path.exists(pythonw_exe)
    )


def _run_first_run_setup(base_dir):
    icon_path = os.path.join(base_dir, "src", "icon.png")
    try:
        from PyQt5.QtWidgets import QApplication

        from src.ui.bootstrap_setup import run_bootstrap_setup
    except Exception as exc:
        _message_box(
            "MangaTranslate Setup",
            "Setup UI could not be loaded.\n\n"
            f"{exc}\n\n"
            "Pastikan file aplikasi lengkap dan PyQt5 tersedia di launcher EXE.",
        )
        return False

    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    success, message = run_bootstrap_setup(base_dir, icon_path if os.path.exists(icon_path) else None)
    if not success and message:
        _message_box("MangaTranslate Setup Failed", message)
    return success


def _start_inpainting(base_dir):
    inpainting_bat = os.path.join(base_dir, "Inpainting", "run.bat")
    if not os.path.exists(inpainting_bat):
        return None
    try:
        proc = subprocess.Popen(
            [inpainting_bat],
            cwd=os.path.dirname(inpainting_bat),
            creationflags=_creation_flags(),
        )
        time.sleep(3)
        return proc
    except Exception as exc:
        print(f"Gagal memulai inpainting server: {exc}")
        return None


def _stop_inpainting(proc):
    if proc is None:
        return
    try:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            creationflags=_creation_flags(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        try:
            proc.terminate()
        except Exception:
            pass


def _run_main_app(base_dir):
    python_exe, pythonw_exe = _venv_python_paths(base_dir)
    launcher_python = pythonw_exe if os.path.exists(pythonw_exe) else python_exe
    main_py = os.path.join(base_dir, "main.py")
    if not os.path.exists(launcher_python):
        _message_box("MangaTranslate", "Python venv tidak ditemukan. Setup awal belum berhasil.")
        return 1
    if not os.path.exists(main_py):
        _message_box("MangaTranslate", "main.py tidak ditemukan di folder aplikasi.")
        return 1

    inpainting_proc = _start_inpainting(base_dir)
    try:
        app_proc = subprocess.Popen([launcher_python, main_py], cwd=base_dir)
        return app_proc.wait()
    except Exception as exc:
        _message_box("MangaTranslate", f"Gagal menjalankan aplikasi utama:\n\n{exc}")
        return 1
    finally:
        _stop_inpainting(inpainting_proc)


def main():
    base_dir = _base_dir()
    _prepare_path(base_dir)

    if _needs_first_run_setup(base_dir):
        if not _run_first_run_setup(base_dir):
            return 1

    return _run_main_app(base_dir)


if __name__ == "__main__":
    sys.exit(main())
