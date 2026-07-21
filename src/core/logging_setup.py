"""Logging ke file + crash handler. Stdlib saja, tanpa dependency baru.

Dipanggil sekali dari main.py sebelum apa pun yang bisa gagal.
"""

import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_PATH = os.path.join(_ROOT, "logs", "mangatranslate.log")

_log = logging.getLogger("mangatranslate")
_configured = False


class _StreamToLog:
    """File-like: meneruskan print() ke logger, sekaligus ke stream asli bila ada.

    ponytail: dipakai supaya 92 print() yang tersebar di main_window.py ikut
    tercatat tanpa menyentuh satu pun call site. Ceiling: tidak tahu modul asal
    pesan (semua tercatat sebagai 'stdout'). Kalau nanti butuh asal-usul yang
    tepat, ganti print() di jalur kritis jadi _log.info() satu per satu.
    """

    encoding = "utf-8"

    def __init__(self, level, passthrough):
        self._level = level
        self._passthrough = passthrough
        self._buf = ""

    def write(self, text):
        if self._passthrough is not None:
            try:
                self._passthrough.write(text)
            except Exception:
                pass
        self._buf += text
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            if line.strip():
                _log.log(self._level, line)

    def flush(self):
        if self._passthrough is not None:
            try:
                self._passthrough.flush()
            except Exception:
                pass

    def isatty(self):
        # tqdm & teman-temannya menanyakan ini sebelum menggambar progress bar.
        return False


def _log_uncaught(exc_type, exc, tb):
    _log.critical("Uncaught exception", exc_info=(exc_type, exc, tb))


def setup(level=logging.INFO):
    """Pasang file log berputar, arahkan print() ke sana, catat crash tak tertangani."""
    global _configured
    if _configured:
        return LOG_PATH

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    handler = RotatingFileHandler(
        LOG_PATH, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
    )
    _log.setLevel(level)
    _log.addHandler(handler)

    # Hanya handler file — jangan tambah StreamHandler ke stdout, karena stdout
    # di bawah ini diarahkan balik ke logger (akan jadi rekursi tak terbatas).
    sys.stdout = _StreamToLog(logging.INFO, sys.stdout)
    sys.stderr = _StreamToLog(logging.ERROR, sys.stderr)

    sys.excepthook = _log_uncaught
    threading.excepthook = lambda args: _log.critical(
        "Uncaught exception in thread %s", args.thread,
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )

    _configured = True
    _log.info("--- MangaTranslate start (pid %s) ---", os.getpid())
    return LOG_PATH


if __name__ == "__main__":
    # Self-check: print() dan crash benar-benar mendarat di file log.
    setup()
    print("halo dari print")
    try:
        raise ValueError("ledakan uji")
    except ValueError:
        _log_uncaught(*sys.exc_info())
    logging.shutdown()

    with open(LOG_PATH, encoding="utf-8") as f:
        content = f.read()
    assert "halo dari print" in content, "print() tidak sampai ke log"
    assert "ledakan uji" in content, "traceback tidak sampai ke log"
    assert "Traceback" in content, "exc_info tidak ikut tertulis"
    sys.__stdout__.write("self-check OK -> %s\n" % LOG_PATH)
