import os
import sys
import subprocess
import logging
import shutil
import time
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QSlider, QStackedWidget, QFrame,
    QProgressBar, QSizePolicy, QStyle, QMessageBox, QComboBox,
    QTabWidget, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal, QTimer
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor, QPixmap, QImage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_ffmpeg_executable() -> str:
    """Detect ffmpeg on the system or return empty string."""
    try:
        from src.core.config import SETTINGS, ROOT_DIR
        cfg_path = SETTINGS.get('ffmpeg_path', '').strip()
        if cfg_path and os.path.exists(cfg_path):
            return cfg_path
    except Exception:
        try:
            from src.core.config import ROOT_DIR
        except Exception:
            ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # 1. System PATH
    path = shutil.which('ffmpeg')
    if path:
        return path

    # 2. Common Windows paths + Local bin path
    candidates = [
        os.path.join(ROOT_DIR, "bin", "ffmpeg.exe"),
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        os.path.join(os.path.dirname(sys.executable), "ffmpeg.exe"),
        os.path.join(os.path.dirname(sys.executable), "Scripts", "ffmpeg.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return ""

def format_time(ms: int) -> str:
    """Format milliseconds to MM:SS."""
    s = ms // 1000
    m = s // 60
    s = s % 60
    return f"{m:02d}:{s:02d}"

# ---------------------------------------------------------------------------
# Background Threads
# ---------------------------------------------------------------------------

class YtdlDummyLogger:
    """A dummy logger to silence yt-dlp console output warnings."""
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass


class YouTubeUrlExtractor(QThread):
    """Fetches direct video/audio stream URLs or playlist entries from a YouTube link."""
    resolved = pyqtSignal(str, str, list) # video_url, audio_url, playlist_entries
    error = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            try:
                import yt_dlp
            except Exception:
                self.error.emit(
                    "yt-dlp belum terpasang. Buka Settings > Media Tools lalu klik Install Media Tools."
                )
                return
            dummy_logger = YtdlDummyLogger()
            
            # 1. Extract flat playlist metadata first
            ydl_opts_flat = {
                'extract_flat': True,
                'quiet': True,
                'no_warnings': True,
                'logger': dummy_logger,
                'skip_download': True,
            }
            playlist_entries = []
            with yt_dlp.YoutubeDL(ydl_opts_flat) as ydl:
                info = ydl.extract_info(self.url, download=False)
                if 'entries' in info:
                    for entry in info['entries']:
                        if entry:
                            playlist_entries.append({
                                'title': entry.get('title', 'Untitled Video'),
                                'url': f"https://www.youtube.com/watch?v={entry.get('id')}" if entry.get('id') else entry.get('url', ''),
                                'id': entry.get('id', '')
                            })
            
            # 2. Extract actual best stream URLs (first video or single video)
            ydl_opts = {
                'format': 'best',
                'quiet': True,
                'no_warnings': True,
                'logger': dummy_logger,
                'skip_download': True,
            }
            
            video_url = ""
            audio_url = ""
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                
                # Resolve video stream
                if 'entries' in info and info['entries']:
                    first_entry = info['entries'][0]
                    video_url = first_entry.get('url', '')
                else:
                    video_url = info.get('url', '')
                
                # Extract separate high-quality audio stream for OpenCV fallback
                formats = info.get('formats', []) if 'entries' not in info else info['entries'][0].get('formats', [])
                audio_formats = [f for f in formats if f.get('vcodec') == 'none' and f.get('acodec') != 'none']
                if audio_formats:
                    best_audio = sorted(audio_formats, key=lambda x: x.get('abr', 0) or 0, reverse=True)[0]
                    audio_url = best_audio.get('url', '')
                else:
                    audio_url = video_url
                    
            self.resolved.emit(video_url, audio_url, playlist_entries)
        except Exception as e:
            self.error.emit(str(e))


class FFmpegWorker(QThread):
    """Runs an FFmpeg process in a background thread and monitors it."""
    finished = pyqtSignal(bool, str) # success, output_path_or_error

    def __init__(self, ffmpeg_path: str, args: list, output_path: str):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path
        self.args = args
        self.output_path = output_path

    def run(self):
        if not self.ffmpeg_path or not os.path.exists(self.ffmpeg_path):
            self.finished.emit(False, "FFmpeg executable tidak ditemukan.")
            return

        cmd = [self.ffmpeg_path] + self.args
        try:
            startupinfo = None
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            proc = subprocess.Popen(
                cmd,
                startupinfo=startupinfo,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            stdout, stderr = proc.communicate()
            
            if proc.returncode == 0:
                self.finished.emit(True, self.output_path)
            else:
                self.finished.emit(False, stderr or stdout or f"Exit code: {proc.returncode}")
        except Exception as e:
            self.finished.emit(False, str(e))


# ---------------------------------------------------------------------------
# VideoPlayerWidget
# ---------------------------------------------------------------------------

class VideoPlayerWidget(QWidget):
    """A highly polished premium Video Player widget with local Media Library and YouTube Playlist support."""

    def __init__(self, main_app=None, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self._youtube_extractor = None
        self._ffmpeg_worker = None
        self._current_video_path = "" # Path to local video
        
        # Fallback OpenCV engine variables
        from src.core.config import SETTINGS
        preferred_engine = SETTINGS.get('video_player_engine', 'native')
        self.use_opencv_engine = (preferred_engine == 'opencv')
        self._cv_cap = None
        self._cv_fps = 30.0
        self._cv_duration_ms = 0
        self._cv_temp_audio = ""
        self._cv_is_playing = False
        
        # Playlists and Active Play index tracking
        self.youtube_playlist = []
        self.current_playlist_idx = -1
        
        self.opencv_timer = QTimer(self)
        self.opencv_timer.timeout.connect(self._on_opencv_timer_tick)
        
        self._setup_players()
        self._build_ui()
        
        # Scan local folder immediately on startup
        QTimer.singleShot(500, self.scan_local_library)

    def _setup_players(self):
        # 1. Native QMediaPlayer
        self.player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.player.positionChanged.connect(self._on_native_position_changed)
        self.player.durationChanged.connect(self._on_native_duration_changed)
        self.player.stateChanged.connect(self._on_native_state_changed)
        self.player.error.connect(self._on_player_error)

        # 2. Audio Player for OpenCV fallback
        self.audio_player = QMediaPlayer(None, QMediaPlayer.LowLatency)
        self.audio_player.positionChanged.connect(self._on_opencv_audio_position_changed)
        self.audio_player.durationChanged.connect(self._on_opencv_audio_duration_changed)
        self.audio_player.stateChanged.connect(self._on_opencv_audio_state_changed)

    def _build_ui(self):
        self.setObjectName("VideoPlayer")
        
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # 1. ---- Source Input Card ----
        input_card = QFrame()
        input_card.setFrameShape(QFrame.NoFrame)
        input_card.setStyleSheet("""
            QFrame {
                background: #0b0e16;
                border: 1px solid #1e293b;
                border-radius: 12px;
            }
        """)
        input_layout = QVBoxLayout(input_card)
        input_layout.setContentsMargins(12, 12, 12, 12)
        input_layout.setSpacing(8)

        # Header Row
        header_row = QHBoxLayout()
        lbl = QLabel("🎬  Media Source")
        lbl.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px; border: none; background: transparent;")
        header_row.addWidget(lbl)
        header_row.addStretch()

        engine_lbl = QLabel("Engine:")
        engine_lbl.setStyleSheet("color: #64748b; font-size: 11px; border: none; background: transparent;")
        header_row.addWidget(engine_lbl)

        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["Native (Windows Media)", "OpenCV (Codec-Free Fallback)"])
        self.engine_combo.setCurrentIndex(1 if self.use_opencv_engine else 0)
        self.engine_combo.setStyleSheet("""
            QComboBox {
                background: #0f131c;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 2px 8px;
                color: #cbd5e1;
                font-size: 11px;
            }
            QComboBox::drop-down { width: 16px; border-left: 1px solid #1e293b; }
        """)
        self.engine_combo.currentIndexChanged.connect(self._on_engine_changed)
        header_row.addWidget(self.engine_combo)
        input_layout.addLayout(header_row)

        # Row A: YouTube link
        yt_row = QHBoxLayout()
        yt_row.setSpacing(6)
        self.yt_input = QLineEdit()
        self.yt_input.setPlaceholderText("Paste YouTube Link atau Playlist URL di sini...")
        self.yt_input.setStyleSheet("""
            QLineEdit {
                background: #0f131c;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 6px 10px;
                color: #cbd5e1;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #38bdf8;
            }
        """)
        self.yt_play_btn = QPushButton("Load YouTube")
        self.yt_play_btn.clicked.connect(self._load_youtube_video)
        self.yt_play_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #1a6f50, stop:1 #248c66);
                border: none;
                border-radius: 8px;
                padding: 6px 12px;
                color: #e6f7f2;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #228c66, stop:1 #2ca67b);
            }
        """)
        yt_row.addWidget(self.yt_input)
        yt_row.addWidget(self.yt_play_btn)
        input_layout.addLayout(yt_row)

        root.addWidget(input_card)

        # 2. ---- Video Screen Stack ----
        self.screen_stack = QStackedWidget()
        self.screen_stack.setStyleSheet("""
            QStackedWidget {
                background: #04060a;
                border: 1px solid #1e293b;
                border-radius: 12px;
            }
        """)
        self.screen_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.screen_stack.setMinimumHeight(220)

        # Slide 0: Placeholder
        self.placeholder_widget = QFrame()
        self.placeholder_widget.setFrameShape(QFrame.NoFrame)
        place_layout = QVBoxLayout(self.placeholder_widget)
        place_layout.setAlignment(Qt.AlignCenter)
        place_layout.setSpacing(10)
        
        media_logo = QLabel("🎬")
        media_logo.setStyleSheet("font-size: 42px; background: transparent; border: none;")
        media_logo.setAlignment(Qt.AlignCenter)
        place_layout.addWidget(media_logo)

        self.placeholder_label = QLabel("Masukkan link YouTube atau pilih file video\nuntuk mulai memutar media.")
        self.placeholder_label.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 500; background: transparent; border: none;")
        self.placeholder_label.setWordWrap(True)
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        place_layout.addWidget(self.placeholder_label)

        self.screen_stack.addWidget(self.placeholder_widget)

        # Slide 1: Native Video screen
        self.video_widget = QVideoWidget()
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.screen_stack.addWidget(self.video_widget)
        self.player.setVideoOutput(self.video_widget)

        # Slide 2: OpenCV Fallback Screen (QLabel)
        self.opencv_screen = QLabel()
        self.opencv_screen.setAlignment(Qt.AlignCenter)
        self.opencv_screen.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.opencv_screen.setStyleSheet("background: #04060a; border-radius: 12px;")
        self.screen_stack.addWidget(self.opencv_screen)

        root.addWidget(self.screen_stack, 1)

        # 3. ---- Playback Control Panel ----
        ctrl_card = QFrame()
        ctrl_card.setFrameShape(QFrame.NoFrame)
        ctrl_card.setStyleSheet("""
            QFrame {
                background: #0b0e16;
                border: 1px solid #1e293b;
                border-radius: 12px;
            }
        """)
        ctrl_layout = QVBoxLayout(ctrl_card)
        ctrl_layout.setContentsMargins(12, 8, 12, 8)
        ctrl_layout.setSpacing(6)

        # Progress slider row
        progress_row = QHBoxLayout()
        progress_row.setSpacing(8)
        
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("color: #64748b; font-family: monospace; font-size: 11px; border: none; background: transparent;")
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderMoved.connect(self._on_slider_moved)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: #1e293b;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #38bdf8;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 1px solid #38bdf8;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::handle:horizontal:hover {
                background: #38bdf8;
            }
        """)
        progress_row.addWidget(self.slider)
        progress_row.addWidget(self.time_label)
        ctrl_layout.addLayout(progress_row)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.clicked.connect(self._toggle_play)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 5px 12px;
                color: #cbd5e1;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #334155;
                color: #38bdf8;
                border-color: #38bdf8;
            }
        """)
        
        # Playlist Next/Prev buttons
        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setToolTip("Video Sebelumnya")
        self.prev_btn.clicked.connect(self.play_prev_playlist_item)
        self.prev_btn.setStyleSheet("""
            QPushButton { background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 4px 10px; color: #cbd5e1; }
            QPushButton:hover { background: #334155; color: #38bdf8; }
        """)

        self.next_btn = QPushButton("⏭")
        self.next_btn.setToolTip("Video Berikutnya")
        self.next_btn.clicked.connect(self.play_next_playlist_item)
        self.next_btn.setStyleSheet("""
            QPushButton { background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 4px 10px; color: #cbd5e1; }
            QPushButton:hover { background: #334155; color: #38bdf8; }
        """)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.clicked.connect(self._stop_video)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 5px 12px;
                color: #cbd5e1;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #4c1d1d;
                color: #f87171;
                border-color: #f87171;
            }
        """)

        # Volume widgets
        vol_row = QHBoxLayout()
        vol_row.setSpacing(4)
        
        self.mute_btn = QPushButton("🔊")
        self.mute_btn.setFixedSize(24, 24)
        self.mute_btn.clicked.connect(self._toggle_mute)
        self.mute_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; color: #64748b; font-size: 12px; }
            QPushButton:hover { color: #38bdf8; }
        """)
        
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(70)
        self.vol_slider.setFixedWidth(50)
        self.vol_slider.valueChanged.connect(self._on_volume_changed)
        self.vol_slider.setStyleSheet("""
            QSlider::groove:horizontal { border: none; height: 3px; background: #1e293b; }
            QSlider::sub-page:horizontal { background: #cbd5e1; }
            QSlider::handle:horizontal { background: #cbd5e1; width: 6px; height: 6px; margin: -2px 0; border-radius: 3px; }
        """)

        vol_row.addWidget(self.mute_btn)
        vol_row.addWidget(self.vol_slider)

        btn_row.addWidget(self.play_btn)
        btn_row.addWidget(self.prev_btn)
        btn_row.addWidget(self.next_btn)
        btn_row.addWidget(self.stop_btn)
        btn_row.addStretch()
        btn_row.addLayout(vol_row)
        
        ctrl_layout.addLayout(btn_row)
        root.addWidget(ctrl_card)

        # 4. ---- Media Library & Playlist Tabs ----
        library_card = QFrame()
        library_card.setStyleSheet("""
            QFrame {
                background: #0b0e16;
                border: 1px solid #1e293b;
                border-radius: 12px;
            }
        """)
        library_layout = QVBoxLayout(library_card)
        library_layout.setContentsMargins(10, 10, 10, 10)
        library_layout.setSpacing(6)

        # Title bar for Library
        lib_title_row = QHBoxLayout()
        lib_title = QLabel("📂  Media Library")
        lib_title.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px; border: none;")
        lib_title_row.addWidget(lib_title)
        lib_title_row.addStretch()
        
        self.refresh_lib_btn = QPushButton("⟳ Refresh")
        self.refresh_lib_btn.clicked.connect(self.scan_local_library)
        self.refresh_lib_btn.setToolTip("Rescan folder src/ untuk video dan musik")
        self.refresh_lib_btn.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 3px 8px;
                color: #cbd5e1;
                font-size: 10px;
            }
            QPushButton:hover { background: #334155; color: #38bdf8; }
        """)
        lib_title_row.addWidget(self.refresh_lib_btn)
        library_layout.addLayout(lib_title_row)

        # QTabWidget to separate local videos, music, and youtube playlists
        self.library_tabs = QTabWidget()
        self.library_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #1e293b; background: #080a0f; border-radius: 8px; margin-top: -1px; }
            QTabBar::tab {
                background: transparent; color: #64748b; padding: 6px 12px; font-size: 11px; font-weight: 600;
                border-bottom: 2px solid transparent;
            }
            QTabBar::tab:selected { color: #38bdf8; border-bottom: 2px solid #38bdf8; }
        """)

        # List Widget Styles
        list_style = """
            QListWidget {
                background: #080a0f; border: none; color: #cbd5e1; font-size: 11px; padding: 4px;
            }
            QListWidget::item { padding: 6px 8px; border-bottom: 1px solid #121824; border-radius: 4px; }
            QListWidget::item:hover { background: #1e293b; color: #38bdf8; }
            QListWidget::item:selected { background: #1e3a5f; color: #38bdf8; }
        """

        # Tab A: Local Videos
        self.video_list = QListWidget()
        self.video_list.setStyleSheet(list_style)
        self.video_list.itemDoubleClicked.connect(self._on_local_video_selected)
        self.library_tabs.addTab(self.video_list, "🎬 Videos")

        # Tab B: Local Music
        self.music_list = QListWidget()
        self.music_list.setStyleSheet(list_style)
        self.music_list.itemDoubleClicked.connect(self._on_local_music_selected)
        self.library_tabs.addTab(self.music_list, "🎵 Music")

        # Tab C: YouTube Playlist
        self.playlist_list = QListWidget()
        self.playlist_list.setStyleSheet(list_style)
        self.playlist_list.itemDoubleClicked.connect(self._on_playlist_item_selected)
        self.library_tabs.addTab(self.playlist_list, "📜 YT Playlist")

        library_layout.addWidget(self.library_tabs)

        # status bar for library scanning
        self.lib_status = QLabel("Ready")
        self.lib_status.setStyleSheet("color: #475569; font-size: 10px; border: none;")
        library_layout.addWidget(self.lib_status)

        root.addWidget(library_card)

        # 5. ---- FFmpeg Status Card (Hidden by default unless running) ----
        self.ffmpeg_card = QFrame()
        self.ffmpeg_card.setStyleSheet("""
            QFrame {
                background: #0b0e16;
                border: 1px solid #1e293b;
                border-radius: 12px;
            }
        """)
        ffmpeg_layout = QVBoxLayout(self.ffmpeg_card)
        ffmpeg_layout.setContentsMargins(10, 8, 10, 8)
        ffmpeg_layout.setSpacing(6)

        ff_title = QLabel("🎬  FFmpeg Power Tools")
        ff_title.setStyleSheet("color: #a78bfa; font-weight: bold; font-size: 11px; border: none;")
        ffmpeg_layout.addWidget(ff_title)

        ff_btns = QHBoxLayout()
        ff_btns.setSpacing(6)
        
        self.ff_audio_btn = QPushButton("Extract Audio (MP3)")
        self.ff_audio_btn.clicked.connect(self._ffmpeg_extract_audio)
        self.ff_audio_btn.setEnabled(False)
        self.ff_audio_btn.setStyleSheet("""
            QPushButton { background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px; color: #cbd5e1; font-size: 10px; }
            QPushButton:hover:enabled { background: #1e1b4b; color: #a78bfa; border-color: #a78bfa; }
            QPushButton:disabled { color: #475569; background: #090b10; border: none; }
        """)

        self.ff_snap_btn = QPushButton("Screenshot Frame")
        self.ff_snap_btn.clicked.connect(self._ffmpeg_screenshot)
        self.ff_snap_btn.setEnabled(False)
        self.ff_snap_btn.setStyleSheet("""
            QPushButton { background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px; color: #cbd5e1; font-size: 10px; }
            QPushButton:hover:enabled { background: #1e1b4b; color: #a78bfa; border-color: #a78bfa; }
            QPushButton:disabled { color: #475569; background: #090b10; border: none; }
        """)

        ff_btns.addWidget(self.ff_audio_btn)
        ff_btns.addWidget(self.ff_snap_btn)
        ffmpeg_layout.addLayout(ff_btns)

        self.ff_progress = QProgressBar()
        self.ff_progress.setFixedHeight(4)
        self.ff_progress.setRange(0, 0)
        self.ff_progress.setVisible(False)
        self.ff_progress.setStyleSheet("QProgressBar { background: #0f131c; border: none; } QProgressBar::chunk { background: #a78bfa; }")
        ffmpeg_layout.addWidget(self.ff_progress)

        self.ff_status = QLabel("FFmpeg siap.")
        self.ff_status.setStyleSheet("color: #64748b; font-size: 10px; border: none;")
        ffmpeg_layout.addWidget(self.ff_status)

        root.addWidget(self.ffmpeg_card)

        # Initialize FFmpeg path checks
        self._check_ffmpeg_availability()

    # ------------------------------------------------------------------
    # Library Scanner & Selector
    # ------------------------------------------------------------------

    def scan_local_library(self):
        """Scans src/data/video/ and src/data/music/ for media files."""
        self.video_list.clear()
        self.music_list.clear()
        
        try:
            from src.core.config import ROOT_DIR
            data_dir = os.path.join(ROOT_DIR, "src", "data")
        except Exception:
            root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(root, "src", "data")

        video_dir = os.path.join(data_dir, "video")
        music_dir = os.path.join(data_dir, "music")

        # Automatically create directories if they do not exist
        os.makedirs(video_dir, exist_ok=True)
        os.makedirs(music_dir, exist_ok=True)

        self.lib_status.setText("Scanning src/data/...")
        
        video_exts = (".mp4", ".mkv", ".avi", ".mov", ".wmv")
        music_exts = (".mp3", ".wav", ".m4a", ".flac", ".ogg")

        v_count = 0
        m_count = 0

        # Scan video directory
        for root_path, dirs, files in os.walk(video_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in video_exts:
                    rel_path = os.path.relpath(os.path.join(root_path, file), video_dir)
                    abs_path = os.path.join(root_path, file)
                    item = QListWidgetItem(f"🎬  {rel_path}")
                    item.setData(Qt.UserRole, abs_path)
                    self.video_list.addItem(item)
                    v_count += 1

        # Scan music directory
        for root_path, dirs, files in os.walk(music_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in music_exts:
                    rel_path = os.path.relpath(os.path.join(root_path, file), music_dir)
                    abs_path = os.path.join(root_path, file)
                    item = QListWidgetItem(f"🎵  {rel_path}")
                    item.setData(Qt.UserRole, abs_path)
                    self.music_list.addItem(item)
                    m_count += 1

        self.lib_status.setText(f"Scan selesai: {v_count} video di video/, {m_count} musik di music/.")

    def _on_local_video_selected(self, item):
        path = item.data(Qt.UserRole)
        self.library_tabs.setCurrentIndex(0) # Keep on video tab
        self._load_local_video(path)

    def _on_local_music_selected(self, item):
        path = item.data(Qt.UserRole)
        self.library_tabs.setCurrentIndex(1) # Keep on music tab
        self._load_local_music(path)

    def _load_local_music(self, path: str):
        self._current_video_path = path
        self.screen_stack.setCurrentIndex(0) # Switch to placeholder view (music has no video stream)
        self.placeholder_label.setText(f"🎵  Memutar Musik:\n{os.path.basename(path)}")
        
        self._stop_video()
        
        # Play directly via audio player
        self.audio_player.setMedia(QMediaContent(QUrl.fromLocalFile(path)))
        self.audio_player.play()
        
        # Mimic play state in play buttons
        self.play_btn.setText("⏸ Pause")
        self._update_ffmpeg_buttons_state()

    # ------------------------------------------------------------------
    # YouTube Playlist / List Selection
    # ------------------------------------------------------------------

    def _on_playlist_item_selected(self, item):
        idx = self.playlist_list.row(item)
        self.play_playlist_item(idx)

    def play_playlist_item(self, idx: int):
        if idx < 0 or idx >= len(self.youtube_playlist):
            return
            
        self.current_playlist_idx = idx
        self.playlist_list.setCurrentRow(idx)
        
        item_data = self.youtube_playlist[idx]
        self.placeholder_label.setText(f"Menghubungi YouTube via yt-dlp...\n{item_data['title']}")
        self.screen_stack.setCurrentIndex(0)
        self._stop_video()

        # Extract streams in background
        if self._youtube_extractor and self._youtube_extractor.isRunning():
            self._youtube_extractor.terminate()
            self._youtube_extractor.wait()

        self._youtube_extractor = YouTubeUrlExtractor(item_data['url'])
        self._youtube_extractor.resolved.connect(self._on_playlist_item_resolved)
        self._youtube_extractor.error.connect(self._on_youtube_error)
        self._youtube_extractor.start()

    def _on_playlist_item_resolved(self, video_url: str, audio_url: str, entries: list):
        self._current_video_path = ""
        self._youtube_extractor = None
        
        if self.use_opencv_engine:
            # OpenCV Fallback - plays video + plays direct high-quality audio stream synchronously!
            self._start_opencv_playback_urls(video_url, audio_url)
        else:
            # Native Player
            self.screen_stack.setCurrentIndex(1)
            self.player.setMedia(QMediaContent(QUrl(video_url)))
            self.player.play()

    def _start_opencv_playback_urls(self, video_url: str, audio_url: str):
        self._stop_opencv_playback()
        
        # Load Video using OpenCV
        import cv2
        self._cv_cap = cv2.VideoCapture(video_url)
        if not self._cv_cap.isOpened():
            QMessageBox.critical(self, "OpenCV Error", "Gagal membuka video stream menggunakan OpenCV.")
            return

        self._cv_fps = self._cv_cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = self._cv_cap.get(cv2.CAP_PROP_FRAME_COUNT)
        self._cv_duration_ms = int((total_frames / self._cv_fps) * 1000)

        # Setup slider ranges (if total duration is available, otherwise default to 3 mins placeholder)
        if self._cv_duration_ms <= 0:
            self._cv_duration_ms = 180000 # 3 mins
        self.slider.setRange(0, self._cv_duration_ms)

        # Switch to Slide 2 (OpenCV screen label)
        self.screen_stack.setCurrentIndex(2)

        # Play network audio directly via audio player (native m4a stream)
        if audio_url:
            self.audio_player.setMedia(QMediaContent(QUrl(audio_url)))
            self.audio_player.play()
            self._cv_temp_audio = "STREAM" # flag to indicate network audio stream
            self.ff_status.setText("Engine: OpenCV + Stream Audio aktif.")
            self.ff_status.setStyleSheet("color: #4ade80; font-size: 11px; border: none; background: transparent;")
        else:
            self.ff_status.setText("Engine: OpenCV aktif (Tanpa Audio).")

        self._resume_opencv_playback()

    def play_next_playlist_item(self):
        if len(self.youtube_playlist) == 0:
            return
        next_idx = (self.current_playlist_idx + 1) % len(self.youtube_playlist)
        self.play_playlist_item(next_idx)

    def play_prev_playlist_item(self):
        if len(self.youtube_playlist) == 0:
            return
        prev_idx = (self.current_playlist_idx - 1 + len(self.youtube_playlist)) % len(self.youtube_playlist)
        self.play_playlist_item(prev_idx)

    # ------------------------------------------------------------------
    # Playing Video Methods
    # ------------------------------------------------------------------

    def _on_engine_changed(self, idx: int):
        self.use_opencv_engine = (idx == 1)
        self._stop_video()
        
        # Save preference to settings.json
        from src.core.config import SETTINGS, save_settings
        SETTINGS['video_player_engine'] = 'opencv' if self.use_opencv_engine else 'native'
        save_settings(SETTINGS)
        
        if self.use_opencv_engine:
            self.ff_status.setText("Engine: OpenCV Codec-Free aktif.")
        else:
            self.ff_status.setText("Engine: Native aktif.")

    def _load_youtube_video(self):
        url = self.yt_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Masukkan link YouTube terlebih dahulu!")
            return

        self.placeholder_label.setText("Menghubungi YouTube via yt-dlp...\nHarap tunggu sebentar.")
        self.screen_stack.setCurrentIndex(0)
        self._stop_video()

        # Stop existing extractor thread
        if self._youtube_extractor and self._youtube_extractor.isRunning():
            self._youtube_extractor.terminate()
            self._youtube_extractor.wait()

        self._youtube_extractor = YouTubeUrlExtractor(url)
        self._youtube_extractor.resolved.connect(self._on_youtube_resolved)
        self._youtube_extractor.error.connect(self._on_youtube_error)
        self._youtube_extractor.start()

    def _on_youtube_resolved(self, video_url: str, audio_url: str, entries: list):
        self._current_video_path = ""
        self._youtube_extractor = None
        
        # 1. Populate Playlist view if it's a playlist
        self.youtube_playlist = entries
        self.playlist_list.clear()
        
        if entries:
            for i, entry in enumerate(entries):
                self.playlist_list.addItem(f"{i+1:02d}.  {entry['title']}")
            self.library_tabs.setCurrentIndex(2) # Switch to Playlist tab view
            self.play_playlist_item(0) # Play first item immediately
            return

        # 2. Otherwise play the single resolved video
        if self.use_opencv_engine:
            # OpenCV Fallback - plays video + plays direct high-quality audio stream synchronously!
            self._start_opencv_playback_urls(video_url, audio_url)
        else:
            # Native Player
            self.screen_stack.setCurrentIndex(1)
            self.player.setMedia(QMediaContent(QUrl(video_url)))
            self.player.play()
            
        self._update_ffmpeg_buttons_state()

    def _on_youtube_error(self, err_msg: str):
        self.placeholder_label.setText("Gagal memuat YouTube.\n" + err_msg)
        self.screen_stack.setCurrentIndex(0)
        QMessageBox.critical(self, "YouTube Load Error", f"Terjadi kesalahan saat mengekstrak link YouTube:\n\n{err_msg}")
        self._youtube_extractor = None
        self._update_ffmpeg_buttons_state()

    def _browse_local_video(self):
        from src.core.config import ROOT_DIR
        default_dir = os.path.join(ROOT_DIR, "src")
        if not os.path.exists(default_dir):
            default_dir = ROOT_DIR

        path, _ = QFileDialog.getOpenFileName(
            self, "Pilih Video Lokal", default_dir,
            "Video Files (*.mp4 *.avi *.mkv *.wmv *.mov);;All Files (*)"
        )
        if path:
            self._load_local_video(path)

    def _load_local_video(self, path=None):
        if not path:
            path = self._current_video_path
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Invalid File", "File video tidak ditemukan! Periksa path kembali.")
            return

        self._current_video_path = path
        
        if self.use_opencv_engine:
            self._start_opencv_playback(path, has_audio=True)
        else:
            self.screen_stack.setCurrentIndex(1)
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(path)))
            self.player.play()
            
        self._update_ffmpeg_buttons_state()

    def _toggle_play(self):
        if self.use_opencv_engine:
            if self._cv_is_playing:
                self._pause_opencv_playback()
            else:
                self._resume_opencv_playback()
        else:
            # For local music, player uses audio_player
            if self.screen_stack.currentIndex() == 0 and self.audio_player.mediaStatus() != QMediaPlayer.NoMedia:
                if self.audio_player.state() == QMediaPlayer.PlayingState:
                    self.audio_player.pause()
                    self.play_btn.setText("▶ Play")
                else:
                    self.audio_player.play()
                    self.play_btn.setText("⏸ Pause")
            else:
                if self.player.state() == QMediaPlayer.PlayingState:
                    self.player.pause()
                else:
                    self.player.play()

    def _stop_video(self):
        if self.use_opencv_engine:
            self._stop_opencv_playback()
        else:
            self.player.stop()
            self.audio_player.stop()
            
        self.screen_stack.setCurrentIndex(0)
        self.placeholder_label.setText("Masukkan link YouTube atau pilih file video\nuntuk mulai memutar media.")
        self.play_btn.setText("▶ Play")

    def _toggle_mute(self):
        if self.use_opencv_engine or self.audio_player.mediaStatus() != QMediaPlayer.NoMedia:
            is_muted = self.audio_player.isMuted()
            self.audio_player.setMuted(not is_muted)
            self.mute_btn.setText("🔇" if not is_muted else "🔊")
        else:
            is_muted = self.player.isMuted()
            self.player.setMuted(not is_muted)
            self.mute_btn.setText("🔇" if not is_muted else "🔊")

    def _on_volume_changed(self, val: int):
        self.player.setVolume(val)
        self.audio_player.setVolume(val)
        if val == 0:
            self.mute_btn.setText("🔇")
        else:
            self.mute_btn.setText("🔊")

    # ------------------------------------------------------------------
    # Native Player Events
    # ------------------------------------------------------------------

    def _on_native_position_changed(self, pos: int):
        if not self.use_opencv_engine:
            self.slider.blockSignals(True)
            self.slider.setValue(pos)
            self.slider.blockSignals(False)
            
            dur = self.player.duration()
            self.time_label.setText(f"{format_time(pos)} / {format_time(dur)}")

    def _on_native_duration_changed(self, dur: int):
        if not self.use_opencv_engine:
            self.slider.setRange(0, dur)
            self.time_label.setText(f"00:00 / {format_time(dur)}")

    def _on_native_state_changed(self, state: QMediaPlayer.State):
        if not self.use_opencv_engine:
            if state == QMediaPlayer.PlayingState:
                self.play_btn.setText("⏸ Pause")
            else:
                self.play_btn.setText("▶ Play")

    def _on_player_error(self):
        if self.use_opencv_engine:
            return
            
        err = self.player.errorString()
        reply = QMessageBox.question(
            self, "Playback Error (DirectShow Codec)",
            f"Windows Media Player gagal memutar berkas ini.\n\nDetail: {err}\n\n"
            "Apakah Anda ingin beralih otomatis ke Mesin Pemutar OpenCV (Bebas Codec) untuk memutar berkas ini?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.engine_combo.setCurrentIndex(1) # Switch to OpenCV
            if self._current_video_path:
                self._load_local_video()
            elif self.yt_input.text().strip():
                self._load_youtube_video()

    def _on_slider_moved(self, pos: int):
        if self.use_opencv_engine:
            if self._cv_cap and self._cv_cap.isOpened():
                target_frame = int((pos / 1000.0) * self._cv_fps)
                self._cv_cap.set(1, target_frame)
                if self._cv_temp_audio:
                    self.audio_player.setPosition(pos)
                self._render_opencv_frame()
        else:
            if self.audio_player.mediaStatus() != QMediaPlayer.NoMedia:
                self.audio_player.setPosition(pos)
            else:
                self.player.setPosition(pos)

    # ------------------------------------------------------------------
    # OpenCV Playback Engine Implementation
    # ------------------------------------------------------------------

    def _start_opencv_playback(self, source: str, has_audio: bool = True):
        self._stop_opencv_playback()
        
        # Load Video using OpenCV
        import cv2
        self._cv_cap = cv2.VideoCapture(source)
        if not self._cv_cap.isOpened():
            QMessageBox.critical(self, "OpenCV Error", "Gagal membuka video menggunakan mesin OpenCV.")
            return

        self._cv_fps = self._cv_cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = self._cv_cap.get(cv2.CAP_PROP_FRAME_COUNT)
        self._cv_duration_ms = int((total_frames / self._cv_fps) * 1000)

        # Setup slider ranges
        self.slider.setRange(0, self._cv_duration_ms)
        self.time_label.setText(f"00:00 / {format_time(self._cv_duration_ms)}")

        # Switch screen stack to Slide 2 (OpenCV screen label)
        self.screen_stack.setCurrentIndex(2)

        # Extract Audio using FFmpeg if it's a local video
        if has_audio and self._current_video_path:
            self.ff_status.setText("⏳  Mengekstrak audio untuk pemutaran...")
            self.ff_status.setStyleSheet("color: #38bdf8; font-size: 11px; border: none; background: transparent;")
            
            ffmpeg_bin = find_ffmpeg_executable()
            if ffmpeg_bin and os.path.exists(ffmpeg_bin):
                from src.core.config import ROOT_DIR
                temp_audio_wav = os.path.join(ROOT_DIR, "bin", "temp_playback_audio.wav")
                
                # Command to extract audio very fast (uncompressed PCM WAV)
                cmd = [ffmpeg_bin, "-y", "-i", self._current_video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "44100", temp_audio_wav]
                try:
                    startupinfo = None
                    if sys.platform == 'win32':
                        startupinfo = subprocess.STARTUPINFO()
                        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    
                    proc = subprocess.Popen(cmd, startupinfo=startupinfo, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    proc.communicate()
                    
                    if os.path.exists(temp_audio_wav):
                        self._cv_temp_audio = temp_audio_wav
                        self.audio_player.setMedia(QMediaContent(QUrl.fromLocalFile(self._cv_temp_audio)))
                        self.ff_status.setText("Engine: OpenCV + Audio aktif.")
                        self.ff_status.setStyleSheet("color: #4ade80; font-size: 11px; border: none; background: transparent;")
                except Exception as ex:
                    logger.error(f"Audio extraction failed: {ex}")
            else:
                self.ff_status.setText("Engine: OpenCV aktif (Tanpa Audio - FFmpeg tidak dikonfigurasi).")

        self._resume_opencv_playback()

    def _resume_opencv_playback(self):
        if not self._cv_cap or not self._cv_cap.isOpened():
            return

        self._cv_is_playing = True
        self.play_btn.setText("⏸ Pause")
        
        # Start Audio
        if self._cv_temp_audio:
            self.audio_player.play()

        # Start Video grab timer
        interval_ms = int(1000.0 / self._cv_fps)
        self.opencv_timer.start(interval_ms)

    def _pause_opencv_playback(self):
        self._cv_is_playing = False
        self.play_btn.setText("▶ Play")
        self.opencv_timer.stop()
        if self._cv_temp_audio:
            self.audio_player.pause()

    def _stop_opencv_playback(self):
        self._cv_is_playing = False
        self.play_btn.setText("▶ Play")
        self.opencv_timer.stop()
        self.audio_player.stop()
        
        if self._cv_cap:
            self._cv_cap.release()
            self._cv_cap = None

        # Clean up temporary audio file
        if self._cv_temp_audio and self._cv_temp_audio != "STREAM":
            self.audio_player.setMedia(QMediaContent()) # Unload media
            try:
                if os.path.exists(self._cv_temp_audio):
                    os.remove(self._cv_temp_audio)
            except Exception:
                pass
        self._cv_temp_audio = ""

        self.slider.setValue(0)
        self.time_label.setText("00:00 / 00:00")
        self.opencv_screen.clear()

    def _on_opencv_timer_tick(self):
        if not self._cv_cap or not self._cv_cap.isOpened():
            return

        # Synchronize Video Frame index with Audio Player Position if audio exists
        if self._cv_temp_audio:
            audio_pos_ms = self.audio_player.position()
            current_frame_pos = self._cv_cap.get(1) # cv2.CAP_PROP_POS_FRAMES = 1
            expected_frame = int((audio_pos_ms / 1000.0) * self._cv_fps)
            
            # Sync if drift is larger than 2 frames
            if abs(current_frame_pos - expected_frame) > 2:
                self._cv_cap.set(1, expected_frame)

        self._render_opencv_frame()

    def _render_opencv_frame(self):
        if not self._cv_cap or not self._cv_cap.isOpened():
            return

        ret, frame = self._cv_cap.read()
        if not ret:
            self._stop_opencv_playback()
            self.screen_stack.setCurrentIndex(0)
            return

        import cv2
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        
        qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        
        self.opencv_screen.setPixmap(pixmap.scaled(
            self.opencv_screen.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))

        # Update slider
        if not self.slider.isSliderDown():
            current_frame = self._cv_cap.get(1)
            current_ms = int((current_frame / self._cv_fps) * 1000.0)
            
            self.slider.blockSignals(True)
            self.slider.setValue(current_ms)
            self.slider.blockSignals(False)
            
            self.time_label.setText(f"{format_time(current_ms)} / {format_time(self._cv_duration_ms)}")

    def _on_opencv_audio_position_changed(self, pos: int):
        # Sync slider for music playback only
        if self.screen_stack.currentIndex() == 0 and self.audio_player.mediaStatus() != QMediaPlayer.NoMedia:
            self.slider.blockSignals(True)
            self.slider.setValue(pos)
            self.slider.blockSignals(False)
            
            dur = self.audio_player.duration()
            self.time_label.setText(f"{format_time(pos)} / {format_time(dur)}")

    def _on_opencv_audio_duration_changed(self, dur: int):
        if self.screen_stack.currentIndex() == 0 and self.audio_player.mediaStatus() != QMediaPlayer.NoMedia:
            self.slider.setRange(0, dur)
            self.time_label.setText(f"00:00 / {format_time(dur)}")

    def _on_opencv_audio_state_changed(self, state: QMediaPlayer.State):
        pass

    # ------------------------------------------------------------------
    # FFmpeg Power Tools Implementation
    # ------------------------------------------------------------------

    def _check_ffmpeg_availability(self):
        path = find_ffmpeg_executable()
        if path:
            self.ff_status.setText(f"FFmpeg terdeteksi: {os.path.basename(path)}")
            self.ff_status.setStyleSheet("color: #4ade80; font-size: 11px; border: none; background: transparent;")
            return True
        else:
            self.ff_status.setText("FFmpeg tidak terdeteksi. Silakan unduh/konfigurasi FFmpeg untuk membuka Power Tools.")
            self.ff_status.setStyleSheet("color: #f87171; font-size: 11px; border: none; background: transparent;")
            return False

    def _update_ffmpeg_buttons_state(self):
        has_ffmpeg = bool(find_ffmpeg_executable())
        has_local = bool(self._current_video_path and os.path.exists(self._current_video_path))
        
        self.ff_audio_btn.setEnabled(has_ffmpeg and has_local)
        self.ff_snap_btn.setEnabled(has_ffmpeg and has_local)

    def _configure_ffmpeg_path(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Pilih executable ffmpeg.exe", "",
            "FFmpeg Executable (ffmpeg.exe ffmpeg);;All Files (*)"
        )
        if path:
            try:
                from src.core.config import SETTINGS, save_settings
                SETTINGS['ffmpeg_path'] = path
                save_settings(SETTINGS)
                self._check_ffmpeg_availability()
                self._update_ffmpeg_buttons_state()
                QMessageBox.information(self, "FFmpeg Configured", f"FFmpeg path telah berhasil disimpan:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal menyimpan path FFmpeg: {e}")

    def _ffmpeg_extract_audio(self):
        if not self._current_video_path:
            return
        
        ffmpeg_bin = find_ffmpeg_executable()
        if not ffmpeg_bin:
            return

        base, _ = os.path.splitext(self._current_video_path)
        out_path = base + "_audio.mp3"
        args = ["-y", "-i", self._current_video_path, "-vn", "-acodec", "libmp3lame", "-q:a", "2", out_path]
        
        self._run_ffmpeg_job(ffmpeg_bin, args, out_path, "Mengekstrak audio ke MP3...")

    def _ffmpeg_screenshot(self):
        if not self._current_video_path:
            return
        
        ffmpeg_bin = find_ffmpeg_executable()
        if not ffmpeg_bin:
            return

        # Get current playback position in seconds
        if self.use_opencv_engine:
            current_frame = self._cv_cap.get(1) if self._cv_cap else 0
            pos_sec = current_frame / self._cv_fps
        else:
            pos_sec = self.player.position() / 1000.0
        
        base, _ = os.path.splitext(self._current_video_path)
        out_path = f"{base}_snap_{int(pos_sec)}s.png"
        args = ["-y", "-ss", f"{pos_sec:.3f}", "-i", self._current_video_path, "-vframes", "1", "-f", "image2", out_path]
        
        self._run_ffmpeg_job(ffmpeg_bin, args, out_path, f"Mengambil screenshot pada detik {pos_sec:.1f}...")

    def _run_ffmpeg_job(self, ffmpeg_bin: str, args: list, out_path: str, message: str):
        self.ff_status.setText(message)
        self.ff_status.setStyleSheet("color: #38bdf8; font-size: 11px; border: none; background: transparent;")
        self.ff_progress.setVisible(True)
        self._set_ffmpeg_buttons_enabled(False)

        # Cancel any active worker
        if self._ffmpeg_worker and self._ffmpeg_worker.isRunning():
            self._ffmpeg_worker.terminate()
            self._ffmpeg_worker.wait()

        self._ffmpeg_worker = FFmpegWorker(ffmpeg_bin, args, out_path)
        self._ffmpeg_worker.finished.connect(self._on_ffmpeg_finished)
        self._ffmpeg_worker.start()

    def _on_ffmpeg_finished(self, success: bool, result: str):
        self.ff_progress.setVisible(False)
        self._set_ffmpeg_buttons_enabled(True)
        
        if success:
            self.ff_status.setText(f"Selesai! File disimpan di: {os.path.basename(result)}")
            self.ff_status.setStyleSheet("color: #4ade80; font-size: 11px; border: none; background: transparent;")
            QMessageBox.information(
                self, "FFmpeg Job Selesai",
                f"Proses FFmpeg berhasil diselesaikan!\n\nFile hasil:\n{result}"
            )
            # Scan again to show newly generated file in media list!
            self.scan_local_library()
        else:
            self.ff_status.setText("Proses gagal. Lihat detail log error.")
            self.ff_status.setStyleSheet("color: #f87171; font-size: 11px; border: none; background: transparent;")
            QMessageBox.critical(
                self, "FFmpeg Error",
                f"Proses FFmpeg mengalami kesalahan:\n\n{result}"
            )
        
        self._ffmpeg_worker = None

    def _set_ffmpeg_buttons_enabled(self, val: bool):
        self.ff_audio_btn.setEnabled(val)
        self.ff_snap_btn.setEnabled(val)
        self.ff_settings_btn.setEnabled(val)
        self.yt_play_btn.setEnabled(val)
        self.local_play_btn.setEnabled(val)
        self.local_browse_btn.setEnabled(val)

    def closeEvent(self, event):
        # Defensively clean up running threads and files on exit
        if self._youtube_extractor and self._youtube_extractor.isRunning():
            self._youtube_extractor.terminate()
            self._youtube_extractor.wait()
        if self._ffmpeg_worker and self._ffmpeg_worker.isRunning():
            self._ffmpeg_worker.terminate()
            self._ffmpeg_worker.wait()
        
        self.player.stop()
        self._stop_opencv_playback()
        super().closeEvent(event)
