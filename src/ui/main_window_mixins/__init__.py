"""Mixin hasil pemecahan MangaOCRApp (Fase 1).

Tiap mixin memuat method satu domain, dipindahkan utuh dari main_window.py
tanpa perubahan isi. Semuanya mengandalkan atribut yang dibuat di
MangaOCRApp.__init__, jadi tidak berguna berdiri sendiri -- pemisahan ini
untuk navigasi, bukan modularitas.
"""

from src.ui.main_window_mixins.font import FontMixin
from src.ui.main_window_mixins.batch import BatchMixin
from src.ui.main_window_mixins.layer import LayerMixin
from src.ui.main_window_mixins.inpaint import InpaintMixin
from src.ui.main_window_mixins.settings import SettingsMixin
from src.ui.main_window_mixins.history import HistoryMixin
from src.ui.main_window_mixins.detect import DetectMixin

__all__ = ["FontMixin", "BatchMixin", "LayerMixin", "InpaintMixin", "SettingsMixin", "HistoryMixin", "DetectMixin"]
