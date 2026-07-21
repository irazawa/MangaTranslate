"""Namespace impor bersama untuk mixin MangaOCRApp.

Berisi blok impor main_window.py PERSIS dalam urutan aslinya. Urutan penting:
main_window.py memakai tujuh star import, dan yang belakangan bisa menimpa nama
yang lebih dulu. Method yang dipindah ke mixin harus melihat namespace yang
sama persis seperti saat masih di main_window.py -- kalau tidak, nama seperti
SETTINGS (datang dari `from src.core.config import *`) hilang dan baru
ketahuan saat runtime.

Dihasilkan mengikuti main_window.py; kalau impor di sana berubah, samakan.
"""

# ruff: noqa: F401,F403

import os
import sys
import time
import json
import re
import hashlib
import configparser
import base64
from datetime import date, timedelta
from openai import OpenAI
import warnings
import subprocess
import importlib
import numpy as np
import cv2
import pytesseract
import requests
import fitz  # from PyMuPDF
import google.generativeai as genai
from PIL import Image
import io
from PIL import ImageFile
import math
import weakref
import traceback
import copy
import shutil
from functools import partial
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QWidget, QFileDialog, QTextEdit, QScrollArea, QComboBox, QMessageBox,
    QProgressBar, QShortcut, QListWidget, QListWidgetItem, QColorDialog, QFontDialog,
    QLineEdit, QAction, QDialog, QDialogButtonBox, QCheckBox, QStatusBar, QAbstractItemView, QSpinBox,
    QInputDialog,
    QTabWidget, QGroupBox, QGridLayout, QFrame, QSplitter, QRadioButton, QToolButton, QButtonGroup,
    QStackedWidget,
    QFormLayout,
    QFontComboBox, QDoubleSpinBox, QMenu, QTableWidget, QTableWidgetItem, QHeaderView, QSlider,
    QKeySequenceEdit, QSizePolicy, QAbstractScrollArea
)
from PyQt5.QtGui import (
    QPixmap, QPainter, QPen, QColor, QFont, QKeySequence, QPolygon,
    QPainterPath, QPolygonF, QImage, QIcon, QWheelEvent, QTextDocument,
    QTextCharFormat, QTextCursor, QBrush, QFontMetrics, QTransform, QTextBlockFormat,
    QFontDatabase, QPalette
)
from PyQt5.QtGui import QCursor
from PyQt5.QtCore import (
    Qt, QRect, QPoint, pyqtSignal, QTimer, QThread, QObject,
    QFileSystemWatcher, QRectF, QMutex, QPointF, QSignalBlocker, QSize, QEvent
)
from src.core.config import *
from src.core.workers import *
from src.core.fonts import *
from src.core.app_info import APP_VERSION, app_title
from src.ui.dialogs import *
from src.ui.canvas import *
from src.ui.notifications import NotificationCenter, notify_banner, notify_toast
from src.ui import theme
from src.ui.theme import app_stylesheet, compact_primary_button_qss, set_active_appearance, toggle_button_qss
from src.ui.texts import ActionText, DialogText, NavText, StartupText, WorkspaceText, about_html, welcome_subtitle_html
from src.utils.helpers import *
from src.utils.geometry import *
from src.core.models import EnhancedResult
