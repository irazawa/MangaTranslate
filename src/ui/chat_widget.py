"""
AI Chat Widget — MangaTranslate
Provides a fully-featured chatbot tab inside the Tools & Workflows panel.

Features:
  - Multi-provider support: Gemini, OpenAI, OpenRouter, and local OpenAI-compatible providers
  - Conversation history stored under src/data/chat_history/ (JSON)
  - Multi-session: new / switch / delete chats
  - Background-thread streaming (non-blocking UI)
  - Premium dark-themed bubble chat UI
"""

from __future__ import annotations

import os
import sys
import json
import uuid
import time
import re
import traceback
import threading
import logging

from datetime import datetime
from typing import Optional, List, Dict, Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTextEdit, QComboBox, QSizePolicy,
    QMenu, QAction, QDialog, QListWidget, QListWidgetItem,
    QDialogButtonBox, QMessageBox, QAbstractItemView, QApplication,
    QToolButton, QLineEdit, QStackedWidget
)
from PyQt5.QtCore import (
    Qt, QObject, QThread, pyqtSignal, QTimer, QSize, QPropertyAnimation,
    QEasingCurve, QRect, QPoint
)
from PyQt5.QtGui import (
    QColor, QFont, QPalette, QTextCursor, QKeySequence, QPixmap,
    QIcon, QPainter, QBrush, QPen
)

from src.ui.notifications import notify_banner, notify_toast
from src.ui import theme

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.dirname(_HERE)
CHAT_HISTORY_DIR = os.path.join(_SRC_DIR, "data", "chat_history")
os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)

# Max messages sent as context to AI (most recent N messages)
MAX_CONTEXT_MESSAGES = 20

# ---------------------------------------------------------------------------
# ChatHistoryManager
# ---------------------------------------------------------------------------

class ChatHistoryManager:
    """Handles loading, saving, listing and deleting chat sessions from disk."""

    @staticmethod
    def _path(session_id: str) -> str:
        return os.path.join(CHAT_HISTORY_DIR, f"chat_{session_id}.json")

    @staticmethod
    def new_session(provider: str, model: str) -> dict:
        sid = uuid.uuid4().hex[:12]
        now = time.time()
        return {
            "id": sid,
            "title": "New Chat",
            "provider": provider,
            "model": model,
            "created_at": now,
            "updated_at": now,
            "messages": [],
        }

    @staticmethod
    def save(session: dict):
        try:
            path = ChatHistoryManager._path(session["id"])
            session["updated_at"] = time.time()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(session, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"ChatHistoryManager.save error: {e}")

    @staticmethod
    def load(session_id: str) -> Optional[dict]:
        path = ChatHistoryManager._path(session_id)
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"ChatHistoryManager.load error: {e}")
            return None

    @staticmethod
    def list_sessions() -> List[dict]:
        sessions = []
        try:
            for fname in sorted(os.listdir(CHAT_HISTORY_DIR), reverse=True):
                if not fname.startswith("chat_") or not fname.endswith(".json"):
                    continue
                fpath = os.path.join(CHAT_HISTORY_DIR, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    sessions.append({
                        "id": data.get("id", ""),
                        "title": data.get("title", "Untitled"),
                        "model": data.get("model", ""),
                        "provider": data.get("provider", ""),
                        "updated_at": data.get("updated_at", 0),
                        "msg_count": len(data.get("messages", [])),
                    })
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"ChatHistoryManager.list_sessions error: {e}")
        return sessions

    @staticmethod
    def delete(session_id: str):
        try:
            path = ChatHistoryManager._path(session_id)
            if os.path.isfile(path):
                os.remove(path)
        except Exception as e:
            logger.error(f"ChatHistoryManager.delete error: {e}")

    @staticmethod
    def generate_title(first_user_message: str) -> str:
        """Auto-generate a session title from the first user message."""
        text = first_user_message.strip()
        if len(text) > 50:
            text = text[:47].rstrip() + "..."
        return text or "New Chat"


# ---------------------------------------------------------------------------
# ChatStreamWorker  — runs in a QThread, emits chunks
# ---------------------------------------------------------------------------

class ChatStreamWorker(QObject):
    """
    Background worker that calls an AI API and emits text chunks.
    Supports: Gemini, OpenAI, OpenRouter, and local OpenAI-compatible providers.
    """
    chunk_received = pyqtSignal(str)   # incremental text chunk
    finished = pyqtSignal()            # all done
    error = pyqtSignal(str)            # error message

    def __init__(
        self,
        messages: List[Dict],
        provider: str,
        model_id: str,
        system_prompt: str,
        main_app=None,
    ):
        super().__init__()
        self.messages = messages          # list of {"role": ..., "content": ...}
        self.provider = provider
        self.model_id = model_id
        self.system_prompt = system_prompt
        self.main_app = main_app
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            if self.provider == "Gemini":
                self._call_gemini()
            elif self.provider == "OpenAI":
                self._call_openai()
            elif self.provider in ("OpenRouter", "9Router", "Ollama"):
                self._call_openrouter()
            else:
                self.error.emit(f"Unknown provider: {self.provider}")
        except Exception as e:
            if not self._cancelled:
                self.error.emit(str(e))
        finally:
            self.finished.emit()

    # --- Gemini ---
    def _call_gemini(self):
        try:
            import google.generativeai as genai
            from src.core.config import SETTINGS, get_active_key
        except ImportError as e:
            self.error.emit(f"Gemini import error: {e}")
            return

        api_key = get_active_key("gemini")
        if not api_key:
            self.error.emit("Gemini API key tidak dikonfigurasi. Silakan tambahkan di Settings.")
            return

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=self.model_id,
            system_instruction=self.system_prompt,
        )

        # Build Gemini-style history (alternating user/model)
        history = []
        for msg in self.messages[:-1]:  # all but last (user prompt)
            role = "user" if msg["role"] == "user" else "model"
            history.append({"role": role, "parts": [msg["content"]]})

        chat = model.start_chat(history=history)
        last_user_msg = self.messages[-1]["content"]

        try:
            response = chat.send_message(last_user_msg, stream=True)
            for chunk in response:
                if self._cancelled:
                    break
                if chunk.text:
                    self.chunk_received.emit(chunk.text)
        except Exception as e:
            self.error.emit(f"Gemini API error: {e}")

    # --- OpenAI ---
    def _call_openai(self):
        try:
            from src.core.config import get_active_key
            import openai as openai_lib
        except ImportError as e:
            self.error.emit(f"OpenAI import error: {e}")
            return

        api_key = get_active_key("openai")
        if not api_key:
            self.error.emit("OpenAI API key tidak dikonfigurasi. Silakan tambahkan di Settings.")
            return

        client = openai_lib.OpenAI(api_key=api_key)
        full_messages = [{"role": "system", "content": self.system_prompt}] + self.messages

        try:
            stream = client.chat.completions.create(
                model=self.model_id,
                messages=full_messages,
                stream=True,
                temperature=0.7,
            )
            for chunk in stream:
                if self._cancelled:
                    break
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    self.chunk_received.emit(delta)
        except Exception as e:
            self.error.emit(f"OpenAI API error: {e}")

    # --- OpenRouter ---
    def _call_openrouter(self):
        try:
            import requests as req_lib
            from src.core.config import (
                LOCAL_TRANSLATE_PROVIDERS,
                get_translate_provider_key,
                get_translate_provider_settings,
                get_openrouter_api_key,
            )
        except ImportError as e:
            self.error.emit(f"{self.provider} import error: {e}")
            return

        provider_key = get_translate_provider_key(self.provider)
        provider_meta = LOCAL_TRANSLATE_PROVIDERS.get(provider_key, {})
        provider_label = provider_meta.get('display', self.provider)
        provider_cfg = get_translate_provider_settings(provider_key)
        api_key = provider_cfg.get('api_key', '').strip()

        # Extra fallback: try centralized apis.openrouter.keys directly
        if provider_key == 'openrouter' and not api_key:
            api_key = get_openrouter_api_key()

        if not api_key and not provider_meta.get('api_key_optional'):
            self.error.emit(f"{provider_label} API key tidak dikonfigurasi. Silakan tambahkan di Settings > Translation.")
            return

        # Build URL the same way as translate_with_openrouter
        url = provider_cfg.get('url', '').strip() or provider_meta.get('url', "https://openrouter.ai/api/v1/chat/completions")
        if provider_key == 'openrouter' and url.startswith("http://") and not ('localhost' in url or '127.0.0.1' in url):
            url = "https://" + url[7:]

        full_messages = [{"role": "system", "content": self.system_prompt}] + self.messages

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        if provider_key == 'openrouter':
            headers["HTTP-Referer"] = "https://github.com/MangaTranslate"
            headers["X-Title"] = "MangaTranslate"
        payload = {
            "model": self.model_id,
            "messages": full_messages,
            "stream": True,
            "temperature": 0.7,
        }

        try:
            with req_lib.post(url, headers=headers, json=payload, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                for raw_line in resp.iter_lines():
                    if self._cancelled:
                        break
                    if not raw_line:
                        continue
                    line = raw_line.decode("utf-8", errors="replace")
                    if not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {}).get("content")
                        if delta:
                            self.chunk_received.emit(delta)
                    except Exception:
                        continue
        except Exception as e:
            self.error.emit(f"{provider_label} error: {e}")


# ---------------------------------------------------------------------------
# CodeBlock  — copyable code block widget (like ChatGPT)
# ---------------------------------------------------------------------------

class CodeBlock(QFrame):
    """A styled code block with a language label and animated copy button."""

    def __init__(self, code: str, lang: str = "", parent=None):
        super().__init__(parent)
        self._code = code
        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setStyleSheet("""
            CodeBlock {
                background: #0a0d14;
                border: 1px solid #1e3a5f;
                border-radius: 8px;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- Header bar ----
        header = QFrame()
        header.setFrameShape(QFrame.NoFrame)
        header.setFixedHeight(30)
        header.setStyleSheet("""
            QFrame {
                background: #0f1a2a;
                border-radius: 8px 8px 0 0;
                border-bottom: 1px solid #1e3a5f;
            }
        """)
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(10, 0, 8, 0)

        lang_lbl = QLabel(lang if lang else "code")
        lang_lbl.setStyleSheet("color: #475569; font-size: 10px; font-family: monospace;")
        hlay.addWidget(lang_lbl)
        hlay.addStretch()

        self._copy_btn = QPushButton("⎘ Copy")
        self._copy_btn.setFixedHeight(22)
        self._copy_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #64748b;
                border: 1px solid #1e293b;
                border-radius: 4px;
                padding: 0 8px;
                font-size: 10px;
            }
            QPushButton:hover {
                background: #1e293b;
                color: #38bdf8;
                border-color: #38bdf8;
            }
        """)
        self._copy_btn.clicked.connect(self._copy_code)
        hlay.addWidget(self._copy_btn)
        root.addWidget(header)

        # ---- Code text area ----
        self._code_edit = QTextEdit()
        self._code_edit.setReadOnly(True)
        self._code_edit.setPlainText(code)
        self._code_edit.setLineWrapMode(QTextEdit.NoWrap)
        self._code_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self._code_edit.setMinimumHeight(40)
        self._code_edit.setMaximumHeight(400)
        self._code_edit.setStyleSheet("""
            QTextEdit {
                background: #0a0d14;
                color: #7dd3fc;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                border: none;
                border-radius: 0 0 8px 8px;
                padding: 10px 12px;
                selection-background-color: #1e3a5f;
            }
            QScrollBar:horizontal {
                background: #0f1a2a; height: 6px; border-radius: 3px;
            }
            QScrollBar::handle:horizontal { background: #1e3a5f; border-radius: 3px; }
        """)
        # Auto-resize height to content
        doc = self._code_edit.document()
        doc.contentsChanged.connect(self._adjust_height)
        root.addWidget(self._code_edit)
        QTimer.singleShot(0, self._adjust_height)

    def _adjust_height(self):
        doc_height = int(self._code_edit.document().size().height()) + 24
        self._code_edit.setFixedHeight(max(40, min(doc_height, 400)))

    def _copy_code(self):
        QApplication.clipboard().setText(self._code)
        self._copy_btn.setText("✓ Copied!")
        self._copy_btn.setStyleSheet("""
            QPushButton {
                background: #0f2d1a;
                color: #4ade80;
                border: 1px solid #166534;
                border-radius: 4px;
                padding: 0 8px;
                font-size: 10px;
            }
        """)
        QTimer.singleShot(2000, self._reset_copy_btn)

    def _reset_copy_btn(self):
        self._copy_btn.setText("⎘ Copy")
        self._copy_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #64748b;
                border: 1px solid #1e293b;
                border-radius: 4px;
                padding: 0 8px;
                font-size: 10px;
            }
            QPushButton:hover {
                background: #1e293b;
                color: #38bdf8;
                border-color: #38bdf8;
            }
        """)


# ---------------------------------------------------------------------------
# ChatBubble  — a single chat message widget
# ---------------------------------------------------------------------------

class ChatBubble(QFrame):
    """
    A styled bubble displaying one chat message (user or assistant).
    Fills the full panel width with a small side margin.
    Code blocks are rendered as copyable CodeBlock widgets.
    """

    # Regex to split text into (non-code, code) segments
    _CODE_RE = re.compile(r"```(\w*)\n?(.*?)```", re.DOTALL)

    def __init__(self, role: str, content: str = "", parent=None):
        super().__init__(parent)
        self.role = role  # "user" | "assistant"
        self._full_content = content

        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Outer layout: small indent on one side so bubbles don't go edge-to-edge
        outer = QHBoxLayout(self)
        outer.setContentsMargins(4, 3, 4, 3)
        outer.setSpacing(0)

        # Inner bubble frame — expands to fill available width
        self._bubble = QFrame()
        self._bubble.setFrameShape(QFrame.NoFrame)
        self._bubble.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        self._inner_layout = QVBoxLayout(self._bubble)
        self._inner_layout.setContentsMargins(12, 8, 12, 8)
        self._inner_layout.setSpacing(6)

        # Role label row (role name + copy-all button)
        role_name = "You" if role == "user" else "AI"
        role_color = "#38bdf8" if role == "user" else "#a78bfa"

        role_row = QHBoxLayout()
        role_row.setContentsMargins(0, 0, 0, 0)
        role_row.setSpacing(6)

        role_label = QLabel(role_name)
        role_label.setStyleSheet(
            f"font-size: 10px; font-weight: 700; color: {role_color};"
        )
        role_row.addWidget(role_label)
        role_row.addStretch()

        self._copy_all_btn = QPushButton("⎘")
        self._copy_all_btn.setFixedSize(20, 18)
        self._copy_all_btn.setToolTip("Copy message")
        self._copy_all_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #475569;
                border: none;
                font-size: 11px;
                border-radius: 3px;
            }
            QPushButton:hover { color: #38bdf8; background: rgba(56,189,248,0.1); }
        """)
        self._copy_all_btn.clicked.connect(self._copy_all)
        role_row.addWidget(self._copy_all_btn)

        self._inner_layout.addLayout(role_row)

        # Content area — populated by set_content()
        self._content_area = QVBoxLayout()
        self._content_area.setContentsMargins(0, 0, 0, 0)
        self._content_area.setSpacing(6)
        self._inner_layout.addLayout(self._content_area)


        if role == "user":
            self._bubble.setStyleSheet("""
                QFrame {
                    background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,
                        stop:0 #1e3a5f, stop:1 #1a2e4a);
                    border: 1px solid #2d5a8e;
                    border-radius: 16px 4px 16px 16px;
                }
            """)
            # User: small indent on the LEFT so bubble aligns right-ish
            outer.addSpacing(24)
            outer.addWidget(self._bubble)
        else:
            self._bubble.setStyleSheet("""
                QFrame {
                    background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,
                        stop:0 #1a1f2e, stop:1 #141824);
                    border: 1px solid #2a3350;
                    border-radius: 4px 16px 16px 16px;
                }
            """)
            # AI: small indent on the RIGHT so bubble aligns left-ish
            outer.addWidget(self._bubble)
            outer.addSpacing(24)

        if content:
            self.set_content(content)

    # ------------------------------------------------------------------
    # Content rendering
    # ------------------------------------------------------------------

    def _clear_content(self):
        while self._content_area.count():
            item = self._content_area.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _make_text_label(self, html: str) -> QLabel:
        lbl = QLabel()
        lbl.setWordWrap(True)
        lbl.setTextFormat(Qt.RichText)
        lbl.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        lbl.setOpenExternalLinks(True)
        color = "#d1e8ff" if self.role == "user" else "#cbd5e1"
        lbl.setStyleSheet(
            f"color: {color}; font-size: 13px; background: transparent;"
        )
        lbl.setText(html)
        return lbl

    def set_content(self, text: str):
        self._full_content = text
        self._clear_content()

        # Split into text/code segments
        segments = self._parse_segments(text)
        for seg_type, seg_content, seg_lang in segments:
            if seg_type == "code":
                self._content_area.addWidget(CodeBlock(seg_content.strip(), lang=seg_lang))
            else:
                stripped = seg_content.strip()
                if stripped:
                    html = self._inline_markdown(stripped)
                    self._content_area.addWidget(self._make_text_label(html))

    def append_chunk(self, chunk: str):
        self._full_content += chunk
        self.set_content(self._full_content)

    @staticmethod
    def _parse_segments(text: str):
        """
        Split text into a list of (type, content, lang) tuples.
        type is "text" or "code", lang is the language hint (may be empty).
        """
        segments = []
        last_end = 0
        for m in ChatBubble._CODE_RE.finditer(text):
            # Text before this code block
            before = text[last_end:m.start()]
            if before:
                segments.append(("text", before, ""))
            lang = m.group(1) or ""
            code = m.group(2)
            segments.append(("code", code, lang))
            last_end = m.end()
        # Remaining text after last code block
        tail = text[last_end:]
        if tail:
            segments.append(("text", tail, ""))
        return segments if segments else [("text", text, "")]

    @staticmethod
    def _inline_markdown(text: str) -> str:
        """Convert inline markdown (bold, italic, inline-code) and newlines to HTML."""
        import html as html_lib
        t = html_lib.escape(text)
        # Inline code
        t = re.sub(
            r"`([^`]+)`",
            r'<code style="background:#0f1420;padding:2px 5px;border-radius:4px;'
            r'color:#7dd3fc;font-family:monospace;font-size:12px;">\1</code>',
            t
        )
        # Bold
        t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
        # Italic
        t = re.sub(r"\*(.+?)\*", r"<i>\1</i>", t)
        # Newlines
        t = t.replace("\n", "<br>")
        return t

    def _copy_all(self):
        """Copy the entire raw message text to clipboard."""
        QApplication.clipboard().setText(self._full_content)
        self._copy_all_btn.setText("✓")
        self._copy_all_btn.setStyleSheet("""
            QPushButton {
                background: rgba(74,222,128,0.12);
                color: #4ade80;
                border: none;
                font-size: 11px;
                border-radius: 3px;
            }
        """)
        QTimer.singleShot(2000, self._reset_copy_all_btn)

    def _reset_copy_all_btn(self):
        self._copy_all_btn.setText("⎘")
        self._copy_all_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #475569;
                border: none;
                font-size: 11px;
                border-radius: 3px;
            }
            QPushButton:hover { color: #38bdf8; background: rgba(56,189,248,0.1); }
        """)

    def get_content(self) -> str:
        return self._full_content



# ---------------------------------------------------------------------------
# Typing indicator widget
# ---------------------------------------------------------------------------

class TypingIndicator(QFrame):
    """Animated three-dot typing indicator shown while AI is responding."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        bubble = QFrame()
        bubble.setFrameShape(QFrame.NoFrame)
        bubble.setStyleSheet("""
            QFrame {
                background: #1a1f2e;
                border: 1px solid #2a3350;
                border-radius: 4px 16px 16px 16px;
            }
        """)
        b_layout = QHBoxLayout(bubble)
        b_layout.setContentsMargins(14, 10, 14, 10)
        b_layout.setSpacing(6)

        self._dots = []
        for _ in range(3):
            dot = QLabel("●")
            dot.setStyleSheet("color: #475569; font-size: 10px;")
            b_layout.addWidget(dot)
            self._dots.append(dot)

        layout.addWidget(bubble)
        layout.addStretch(1)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._step = 0
        self._timer.start(350)

    def _animate(self):
        colors = ["#38bdf8", "#475569", "#475569"]
        for i, dot in enumerate(self._dots):
            color = colors[(i - self._step) % 3]
            dot.setStyleSheet(f"color: {color}; font-size: 10px;")
        self._step = (self._step + 1) % 3

    def stop(self):
        self._timer.stop()


# ---------------------------------------------------------------------------
# History Dialog
# ---------------------------------------------------------------------------

class HistoryDialog(QDialog):
    """Dialog to browse and select from past chat sessions."""

    session_selected = pyqtSignal(str)  # emits session id

    def __init__(self, sessions: List[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chat History")
        self.setMinimumSize(420, 360)
        self.setStyleSheet("""
            QDialog { background: #0e111a; color: #cbd5e1; }
            QListWidget { background: #0b0e16; border: 1px solid #1e293b; border-radius: 8px; color: #cbd5e1; }
            QListWidget::item { padding: 10px; border-bottom: 1px solid #1a2235; }
            QListWidget::item:selected { background: #1e3a5f; color: #38bdf8; }
            QPushButton { background: #1e293b; color: #cbd5e1; border: 1px solid #334155; border-radius: 8px; padding: 6px 14px; }
            QPushButton:hover { background: #38bdf8; color: #090a0f; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        header = QLabel("📜  Select a previous conversation")
        header.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: 700; padding: 4px;")
        layout.addWidget(header)

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SingleSelection)
        for s in sessions:
            dt = datetime.fromtimestamp(s["updated_at"]).strftime("%d %b %Y %H:%M")
            n = s.get("msg_count", 0)
            item = QListWidgetItem(f"💬 {s['title']}\n   {s['provider']} · {s['model']}  •  {n} msgs  •  {dt}")
            item.setData(Qt.UserRole, s["id"])
            self._list.addItem(item)
        self._list.itemDoubleClicked.connect(self._on_select)
        layout.addWidget(self._list)

        btns = QHBoxLayout()
        load_btn = QPushButton("Load")
        load_btn.clicked.connect(self._on_select)
        del_btn = QPushButton("Delete")
        del_btn.setStyleSheet("QPushButton { background: #4c1d1d; color: #f87171; border-color: #7f1d1d; } QPushButton:hover { background: #f87171; color: #0a0a0a; }")
        del_btn.clicked.connect(self._on_delete)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(load_btn)
        btns.addWidget(del_btn)
        btns.addStretch()
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    def _on_select(self):
        item = self._list.currentItem()
        if item:
            self.session_selected.emit(item.data(Qt.UserRole))
            self.accept()

    def _on_delete(self):
        item = self._list.currentItem()
        if not item:
            return
        sid = item.data(Qt.UserRole)
        reply = QMessageBox.question(
            self, "Delete Chat",
            "Hapus sesi chat ini secara permanen?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            ChatHistoryManager.delete(sid)
            self._list.takeItem(self._list.row(item))


# ---------------------------------------------------------------------------
# AIChatWidgetContent  — the main chatbot tab widget
# ---------------------------------------------------------------------------

class AIChatWidgetContent(QWidget):
    """
    Full-featured AI chatbot widget to be embedded as a tab inside
    the Tools & Workflows right panel.
    """

    def __init__(self, main_app=None, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        self._session: Optional[dict] = None
        self._worker: Optional[ChatStreamWorker] = None
        self._thread: Optional[QThread] = None
        self._current_ai_bubble: Optional[ChatBubble] = None
        self._typing_indicator: Optional[TypingIndicator] = None
        self._is_responding = False

        self._build_ui()
        self._new_chat(silent=True)

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- Top bar ----
        top_bar = QFrame()
        self._top_bar = top_bar
        top_bar.setFrameShape(QFrame.NoFrame)
        top_bar.setFixedHeight(48)
        top_bar.setStyleSheet("""
            QFrame {
                background: #0b0e16;
                border-bottom: 1px solid #1e293b;
            }
        """)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(10, 6, 10, 6)
        top_layout.setSpacing(6)

        ai_icon = QLabel("🤖")
        ai_icon.setStyleSheet("font-size: 18px;")
        top_layout.addWidget(ai_icon)

        self._title_label = QLabel("AI Chat")
        self._title_label.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: 700;")
        top_layout.addWidget(self._title_label)
        top_layout.addStretch(1)

        history_btn = self._make_icon_btn("📜", "Lihat History Chat", self._open_history)
        new_btn = self._make_icon_btn("✚", "Mulai Chat Baru", self._new_chat)
        clear_btn = self._make_icon_btn("🗑", "Hapus Chat Ini", self._clear_current_chat)
        top_layout.addWidget(history_btn)
        top_layout.addWidget(new_btn)
        top_layout.addWidget(clear_btn)
        root.addWidget(top_bar)

        # ---- Model selector row ----
        model_bar = QFrame()
        self._model_bar = model_bar
        model_bar.setFrameShape(QFrame.NoFrame)
        model_bar.setStyleSheet("QFrame { background: #090a0f; border-bottom: 1px solid #1a2235; }")
        model_layout = QHBoxLayout(model_bar)
        model_layout.setContentsMargins(10, 6, 10, 6)
        model_layout.setSpacing(8)

        model_lbl = QLabel("Model:")
        self._model_label = model_lbl
        model_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        model_layout.addWidget(model_lbl)

        self._model_combo = QComboBox()
        self._model_combo.setStyleSheet("""
            QComboBox {
                background: #0f131c;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 4px 8px;
                color: #cbd5e1;
                font-size: 11px;
                min-width: 180px;
            }
            QComboBox::drop-down { width: 20px; border-left: 1px solid #1e293b; }
            QComboBox QAbstractItemView {
                background: #0f131c;
                border: 1px solid #1e293b;
                color: #cbd5e1;
                selection-background-color: #1e3a5f;
            }
        """)
        self._model_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._model_combo.currentIndexChanged.connect(self._on_model_changed)
        model_layout.addWidget(self._model_combo)

        refresh_btn = self._make_icon_btn("⟳", "Refresh daftar model", self.refresh_models)
        refresh_btn.setFixedSize(28, 28)
        model_layout.addWidget(refresh_btn)
        root.addWidget(model_bar)

        # ---- Chat scroll area ----
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("""
            QScrollArea { background: #090a0f; border: none; }
            QScrollBar:vertical { background: #0b0e16; width: 6px; border-radius: 3px; }
            QScrollBar::handle:vertical { background: #1e293b; border-radius: 3px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        self._messages_container = QWidget()
        self._messages_container.setStyleSheet("background: #090a0f;")
        self._messages_layout = QVBoxLayout(self._messages_container)
        self._messages_layout.setContentsMargins(0, 12, 0, 12)
        self._messages_layout.setSpacing(4)
        self._messages_layout.addStretch(1)  # push messages to top initially

        self._scroll.setWidget(self._messages_container)
        root.addWidget(self._scroll, 1)

        # ---- Input area ----
        input_frame = QFrame()
        self._input_frame = input_frame
        input_frame.setFrameShape(QFrame.NoFrame)
        input_frame.setStyleSheet("""
            QFrame {
                background: #0b0e16;
                border-top: 1px solid #1e293b;
            }
        """)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(10, 10, 10, 10)
        input_layout.setSpacing(8)

        self._input_box = QTextEdit()
        self._input_box.setPlaceholderText("Ketik pesan di sini… (Enter = kirim, Shift+Enter = baris baru)")
        self._input_box.setMaximumHeight(100)
        self._input_box.setMinimumHeight(42)
        self._input_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._input_box.setStyleSheet("""
            QTextEdit {
                background: #0f1420;
                border: 1px solid #1e293b;
                border-radius: 12px;
                padding: 8px 12px;
                color: #e2e8f0;
                font-size: 13px;
            }
            QTextEdit:focus {
                border: 1px solid #38bdf8;
            }
        """)
        # Override key press to send on Enter
        self._input_box.installEventFilter(self)
        input_layout.addWidget(self._input_box)

        self._send_btn = QPushButton("➤")
        self._send_btn.setFixedSize(42, 42)
        self._send_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0284c7, stop:1 #38bdf8);
                color: #fff;
                border: none;
                border-radius: 21px;
                font-size: 16px;
                font-weight: 700;
            }
            QPushButton:hover { background: #38bdf8; }
            QPushButton:pressed { background: #0369a1; }
            QPushButton:disabled { background: #1e293b; color: #64748b; }
        """)
        self._send_btn.clicked.connect(self._on_send)
        input_layout.addWidget(self._send_btn)
        root.addWidget(input_frame)

        # ---- Status bar ----
        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet(
            "color: #475569; font-size: 10px; padding: 2px 10px 4px 10px; background: #090a0f;"
        )
        root.addWidget(self._status_label)

        # Populate models on first load
        self.refresh_models()
        self.refresh_theme()

    def refresh_theme(self):
        frame_qss = f"""
            QFrame {{
                background: {theme.COLORS['panel']};
                border-color: {theme.COLORS['border']};
            }}
        """
        for frame in (getattr(self, '_top_bar', None), getattr(self, '_model_bar', None), getattr(self, '_input_frame', None)):
            if frame is not None:
                frame.setStyleSheet(frame_qss)
        if getattr(self, '_title_label', None) is not None:
            self._title_label.setStyleSheet(f"color: {theme.COLORS['accent']}; font-size: 13px; font-weight: 700;")
        if getattr(self, '_model_label', None) is not None:
            self._model_label.setStyleSheet(f"color: {theme.COLORS['muted']}; font-size: 11px;")
        if getattr(self, '_model_combo', None) is not None:
            self._model_combo.setStyleSheet(f"""
                QComboBox {{
                    background: {theme.COLORS['card_alt']};
                    border: 1px solid {theme.COLORS['border']};
                    border-radius: 8px;
                    padding: 4px 8px;
                    color: {theme.COLORS['text']};
                    font-size: 11px;
                    min-width: 180px;
                }}
                QComboBox::drop-down {{ width: 20px; border-left: 1px solid {theme.COLORS['border']}; }}
                {theme.combo_popup_qss()}
            """)
        if getattr(self, '_scroll', None) is not None:
            self._scroll.setStyleSheet(f"""
                QScrollArea {{ background: {theme.COLORS['bg']}; border: none; }}
                QScrollBar:vertical {{ background: {theme.COLORS['panel']}; width: 6px; border-radius: 3px; }}
                QScrollBar::handle:vertical {{ background: {theme.COLORS['border']}; border-radius: 3px; }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            """)
        if getattr(self, '_messages_container', None) is not None:
            self._messages_container.setStyleSheet(f"background: {theme.COLORS['bg']};")
        if getattr(self, '_input_box', None) is not None:
            self._input_box.setStyleSheet(f"""
                QTextEdit {{
                    background: {theme.COLORS['card_alt']};
                    border: 1px solid {theme.COLORS['border']};
                    border-radius: 12px;
                    padding: 8px 12px;
                    color: {theme.COLORS['text']};
                    font-size: 13px;
                }}
                QTextEdit:focus {{
                    border: 1px solid {theme.COLORS['accent']};
                }}
            """)
        if getattr(self, '_send_btn', None) is not None:
            self._send_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {theme.COLORS['accent']};
                    color: {theme.COLORS['bg']};
                    border: none;
                    border-radius: 21px;
                    font-size: 16px;
                    font-weight: 700;
                }}
                QPushButton:hover {{ background: {theme.COLORS['accent_hover']}; }}
                QPushButton:disabled {{ background: {theme.COLORS['border']}; color: {theme.COLORS['muted']}; }}
            """)
        if getattr(self, '_status_label', None) is not None:
            self._status_label.setStyleSheet(
                f"color: {theme.COLORS['muted']}; font-size: 10px; padding: 2px 10px 4px 10px; background: {theme.COLORS['bg']};"
            )

    @staticmethod
    def _make_icon_btn(icon: str, tooltip: str, slot) -> QToolButton:
        btn = QToolButton()
        btn.setText(icon)
        btn.setToolTip(tooltip)
        btn.setFixedSize(32, 32)
        btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
                color: #64748b;
                font-size: 14px;
                border-radius: 6px;
            }
            QToolButton:hover { background: #1e293b; color: #38bdf8; }
        """)
        btn.clicked.connect(slot)
        return btn

    # ------------------------------------------------------------------
    # Event filter (Enter to send)
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event):
        from PyQt5.QtCore import QEvent
        from PyQt5.QtGui import QKeyEvent
        if obj is self._input_box and event.type() == QEvent.KeyPress:
            key = event.key()
            mods = event.modifiers()
            if key in (Qt.Key_Return, Qt.Key_Enter) and not (mods & Qt.ShiftModifier):
                self._on_send()
                return True
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------------
    # Model population
    # ------------------------------------------------------------------

    def refresh_models(self):
        """Repopulate the model combo from main_app.AI_PROVIDERS."""
        self._model_combo.blockSignals(True)
        current_data = self._model_combo.currentData(Qt.UserRole)
        self._model_combo.clear()

        if self.main_app and hasattr(self.main_app, "AI_PROVIDERS"):
            for provider, models in self.main_app.AI_PROVIDERS.items():
                for model_key, model_info in models.items():
                    if not model_info.get("active", True):
                        continue
                    display = f"[{provider}] {model_info.get('display', model_key)}"
                    idx = self._model_combo.count()
                    self._model_combo.addItem(display)
                    self._model_combo.setItemData(idx, (provider, model_key), Qt.UserRole)
        else:
            # Fallback minimal
            defaults = [
                ("Gemini", "gemini-2.5-flash", "Gemini 2.5 Flash"),
                ("Gemini", "gemini-2.5-pro", "Gemini 2.5 Pro"),
            ]
            for prov, mid, disp in defaults:
                self._model_combo.addItem(f"[{prov}] {disp}")
                self._model_combo.setItemData(self._model_combo.count() - 1, (prov, mid), Qt.UserRole)

        # Restore selection
        if current_data:
            for i in range(self._model_combo.count()):
                if self._model_combo.itemData(i, Qt.UserRole) == current_data:
                    self._model_combo.setCurrentIndex(i)
                    break

        self._model_combo.blockSignals(False)

    def _get_selected_model(self):
        """Returns (provider, model_id) for the currently selected combo item."""
        data = self._model_combo.currentData(Qt.UserRole)
        if data:
            return data  # (provider, model_id)
        # Fallback parse from text
        text = self._model_combo.currentText()
        m = re.match(r"\[(\w+)\]\s+(.+)", text)
        if m:
            return m.group(1), m.group(2).strip()
        return "Gemini", "gemini-2.5-flash"

    def _on_model_changed(self):
        if self._session:
            provider, model_id = self._get_selected_model()
            self._session["provider"] = provider
            self._session["model"] = model_id
            ChatHistoryManager.save(self._session)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def _new_chat(self, silent: bool = False):
        provider, model_id = self._get_selected_model()
        self._session = ChatHistoryManager.new_session(provider, model_id)
        self._clear_message_bubbles()
        self._title_label.setText("New Chat")
        self._status_label.setText("New conversation started.")
        if not silent:
            self._add_system_note("✨ Sesi chat baru dimulai. Silakan mulai bertanya!")

    def _open_history(self):
        sessions = ChatHistoryManager.list_sessions()
        if not sessions:
            notify_toast(self, "History", "Belum ada history chat.", kind="info")
            return
        dlg = HistoryDialog(sessions, self)
        dlg.session_selected.connect(self._load_session)
        dlg.exec_()

    def _load_session(self, session_id: str):
        data = ChatHistoryManager.load(session_id)
        if not data:
            notify_banner(self, "chat-load-session-failed", "Error", "Gagal memuat sesi chat.", kind="error")
            return
        self._session = data
        self._clear_message_bubbles()

        # Update model combo to match session
        prov = data.get("provider", "Gemini")
        mid = data.get("model", "")
        for i in range(self._model_combo.count()):
            d = self._model_combo.itemData(i, Qt.UserRole)
            if d and d[0] == prov and d[1] == mid:
                self._model_combo.setCurrentIndex(i)
                break

        # Render existing messages
        for msg in data.get("messages", []):
            bubble = ChatBubble(msg["role"], msg["content"])
            self._insert_bubble(bubble)

        title = data.get("title", "Chat")
        self._title_label.setText(title)
        self._status_label.setText(f"Loaded: {title} ({len(data.get('messages', []))} messages)")
        self._scroll_to_bottom()

    def _clear_current_chat(self):
        if not self._session:
            return
        reply = QMessageBox.question(
            self, "Clear Chat",
            "Hapus semua pesan di sesi ini?\n(File history akan dihapus juga)",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            ChatHistoryManager.delete(self._session["id"])
            self._new_chat()

    # ------------------------------------------------------------------
    # Message display helpers
    # ------------------------------------------------------------------

    def _clear_message_bubbles(self):
        # Remove all widgets except the stretch at index 0
        while self._messages_layout.count() > 1:
            item = self._messages_layout.takeAt(1)
            if item and item.widget():
                item.widget().deleteLater()
        self._current_ai_bubble = None
        self._typing_indicator = None

    def _insert_bubble(self, bubble: QWidget):
        """Insert before the trailing stretch (which keeps bubbles top-aligned)."""
        count = self._messages_layout.count()
        # The stretch is at index 0 initially; after first insert it moves
        # We just append — layout has stretch at index 0, rest are bubbles
        self._messages_layout.addWidget(bubble)

    def _add_system_note(self, text: str):
        note = QLabel(text)
        note.setAlignment(Qt.AlignCenter)
        note.setWordWrap(True)
        note.setStyleSheet(
            "color: #475569; font-size: 11px; padding: 8px 16px;"
        )
        self._insert_bubble(note)
        self._scroll_to_bottom()

    def _show_typing_indicator(self):
        if self._typing_indicator:
            return
        self._typing_indicator = TypingIndicator()
        self._insert_bubble(self._typing_indicator)
        self._scroll_to_bottom()

    def _hide_typing_indicator(self):
        if self._typing_indicator:
            self._typing_indicator.stop()
            self._messages_layout.removeWidget(self._typing_indicator)
            self._typing_indicator.deleteLater()
            self._typing_indicator = None

    def _scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

    # ------------------------------------------------------------------
    # Sending messages
    # ------------------------------------------------------------------

    def _on_send(self):
        if self._is_responding:
            self._cancel_response()
            return

        text = self._input_box.toPlainText().strip()
        if not text:
            return

        self._input_box.clear()

        # Ensure session exists
        if self._session is None:
            self._new_chat(silent=True)

        provider, model_id = self._get_selected_model()
        self._session["provider"] = provider
        self._session["model"] = model_id

        # Add user message
        user_msg = {"role": "user", "content": text, "timestamp": time.time()}
        self._session["messages"].append(user_msg)

        # Auto-title from first user message
        if len(self._session["messages"]) == 1:
            title = ChatHistoryManager.generate_title(text)
            self._session["title"] = title
            self._title_label.setText(title)

        # Show bubble
        bubble = ChatBubble("user", text)
        self._insert_bubble(bubble)
        self._scroll_to_bottom()

        # Save
        ChatHistoryManager.save(self._session)

        # Start AI response
        self._start_ai_response(provider, model_id)

    def _cancel_response(self):
        if self._worker:
            self._worker.cancel()
        self._send_btn.setText("➤")
        self._is_responding = False
        self._status_label.setText("Cancelled.")
        self._hide_typing_indicator()

    def _start_ai_response(self, provider: str, model_id: str):
        self._is_responding = True
        self._send_btn.setText("■")
        self._send_btn.setToolTip("Klik untuk membatalkan respons")
        self._status_label.setText(f"⏳  {provider} / {model_id} sedang merespons…")

        # Show typing indicator
        self._show_typing_indicator()

        # Build context messages (last MAX_CONTEXT_MESSAGES)
        history = self._session.get("messages", [])
        context = history[-MAX_CONTEXT_MESSAGES:]
        api_messages = [{"role": m["role"], "content": m["content"]} for m in context]

        system_prompt = self._build_system_prompt()

        # Spawn worker + thread
        self._thread = QThread()
        self._worker = ChatStreamWorker(
            messages=api_messages,
            provider=provider,
            model_id=model_id,
            system_prompt=system_prompt,
            main_app=self.main_app,
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.chunk_received.connect(self._on_chunk)
        self._worker.finished.connect(self._on_ai_finished)
        self._worker.error.connect(self._on_ai_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    # ------------------------------------------------------------------
    # Streaming handlers
    # ------------------------------------------------------------------

    def _on_chunk(self, chunk: str):
        if self._typing_indicator:
            self._hide_typing_indicator()

        if self._current_ai_bubble is None:
            self._current_ai_bubble = ChatBubble("assistant")
            self._insert_bubble(self._current_ai_bubble)

        self._current_ai_bubble.append_chunk(chunk)
        self._scroll_to_bottom()

    def _on_ai_finished(self):
        self._is_responding = False
        self._send_btn.setText("➤")
        self._send_btn.setToolTip("")
        self._hide_typing_indicator()

        # Save assistant message
        if self._current_ai_bubble and self._session is not None:
            content = self._current_ai_bubble.get_content()
            if content.strip():
                ai_msg = {
                    "role": "assistant",
                    "content": content,
                    "timestamp": time.time(),
                }
                self._session["messages"].append(ai_msg)
                ChatHistoryManager.save(self._session)

        self._current_ai_bubble = None
        provider = self._session.get("provider", "") if self._session else ""
        model = self._session.get("model", "") if self._session else ""
        self._status_label.setText(f"✓  {provider} / {model} — siap")
        self._scroll_to_bottom()

    def _on_ai_error(self, err: str):
        self._hide_typing_indicator()
        self._is_responding = False
        self._send_btn.setText("➤")
        self._current_ai_bubble = None

        err_bubble = ChatBubble("assistant", f"⚠️ **Error:** {err}")
        self._insert_bubble(err_bubble)
        self._status_label.setText(f"Error: {err[:80]}")
        self._scroll_to_bottom()

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    def _build_system_prompt(self) -> str:
        # Gather some lightweight context from the main app (no API keys exposed)
        context_lines = []
        try:
            if self.main_app:
                from src.core.config import SETTINGS
                provider = self._session.get("provider", "") if self._session else ""
                model = self._session.get("model", "") if self._session else ""
                ocr_lang = ""
                try:
                    ocr_lang = self.main_app.ocr_lang_combo.currentText()
                except Exception:
                    pass
                trans_to = ""
                try:
                    trans_to = self.main_app.translate_combo.currentText()
                except Exception:
                    pass
                gpu = ""
                try:
                    gpu = "active" if self.main_app.use_gpu_checkbox.isChecked() else "inactive"
                except Exception:
                    pass

                context_lines = [
                    f"- App: MangaTranslate (Manga OCR & Typeset Tool)",
                    f"- Current AI Provider: {provider}, Model: {model}",
                    f"- OCR Language: {ocr_lang}",
                    f"- Translate to: {trans_to}",
                    f"- GPU Acceleration: {gpu}",
                ]
        except Exception:
            pass

        context_block = "\n".join(context_lines)

        return (
            "You are a helpful AI assistant integrated into MangaTranslate — "
            "a desktop application for OCR, translation, and typesetting of manga pages.\n\n"
            "You can answer questions about:\n"
            "- How to use the MangaTranslate application\n"
            "- General programming or AI topics\n"
            "- Translation, OCR, image processing concepts\n"
            "- Any general knowledge topic\n\n"
            "Be concise but thorough. Use markdown for code blocks and formatting.\n\n"
            + (f"Current app context:\n{context_block}\n" if context_lines else "")
        )


# ---------------------------------------------------------------------------
# AIChatWidget  — wrapper that switches between AI Chat and Video Player
# ---------------------------------------------------------------------------

class AIChatWidget(QWidget):
    """
    A wrapper widget that hosts both the AI Chatbot and a Video Player,
    allowing the user to switch seamlessly between them without cluttering
    the right-panel tab bar.
    """

    def __init__(self, main_app=None, parent=None):
        super().__init__(parent)
        self.main_app = main_app
        
        # Build UI layout
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        # 1. Mode Switcher bar at the top
        self.switcher_bar = QFrame()
        self.switcher_bar.setFrameShape(QFrame.NoFrame)
        self.switcher_bar.setFixedHeight(40)
        self.switcher_bar.setStyleSheet("""
            QFrame {
                background: #090b10;
                border-bottom: 1px solid #1e293b;
            }
        """)
        switcher_layout = QHBoxLayout(self.switcher_bar)
        switcher_layout.setContentsMargins(10, 4, 10, 4)
        switcher_layout.setSpacing(6)

        # Sleek dropdown/selector to switch modes
        mode_lbl = QLabel("Mode:")
        self.mode_label = mode_lbl
        mode_lbl.setStyleSheet("color: #64748b; font-size: 11px; font-weight: bold; background: transparent;")
        switcher_layout.addWidget(mode_lbl)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["🤖 AI Chatbot", "🎬 Video Player"])
        self.mode_combo.setStyleSheet("""
            QComboBox {
                background: #0f131c;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 4px 8px;
                color: #38bdf8;
                font-size: 11px;
                font-weight: bold;
                min-width: 140px;
            }
            QComboBox::drop-down { width: 18px; border-left: 1px solid #1e293b; }
            QComboBox QAbstractItemView {
                background: #0f131c;
                border: 1px solid #1e293b;
                color: #cbd5e1;
                selection-background-color: #1e3a5f;
            }
        """)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        switcher_layout.addWidget(self.mode_combo)
        switcher_layout.addStretch(1)

        self.root_layout.addWidget(self.switcher_bar)

        # 2. Stacked widget for the content
        self.stack = QStackedWidget()
        
        # Load the chatbot content widget
        self.chat_content_widget = AIChatWidgetContent(main_app=self.main_app, parent=self)
        self.stack.addWidget(self.chat_content_widget)

        # Load the video player widget
        try:
            from src.ui.video_player_widget import VideoPlayerWidget
            self.video_player_widget = VideoPlayerWidget(main_app=self.main_app, parent=self)
            self.stack.addWidget(self.video_player_widget)
            self._video_ok = True
        except Exception as e:
            print(f"[VideoPlayerWidget] Failed to load: {e}")
            fallback = QWidget()
            flay = QVBoxLayout(fallback)
            flay.addWidget(QLabel(f"Error loading Video Player: {e}"))
            self.stack.addWidget(fallback)
            self._video_ok = False

        self.root_layout.addWidget(self.stack, 1)
        self.refresh_theme()

    def _on_mode_changed(self, idx: int):
        self.stack.setCurrentIndex(idx)
        # Pause video if switching away from player
        if idx != 1 and hasattr(self, 'video_player_widget'):
            try:
                self.video_player_widget.player.pause()
            except Exception:
                pass

    def refresh_theme(self):
        self.switcher_bar.setStyleSheet(f"""
            QFrame {{
                background: {theme.COLORS['panel']};
                border-bottom: 1px solid {theme.COLORS['border']};
            }}
        """)
        self.mode_label.setStyleSheet(
            f"color: {theme.COLORS['muted']}; font-size: 11px; font-weight: bold; background: transparent;"
        )
        self.mode_combo.setStyleSheet(f"""
            QComboBox {{
                background: {theme.COLORS['card_alt']};
                border: 1px solid {theme.COLORS['border']};
                border-radius: 6px;
                padding: 4px 8px;
                color: {theme.COLORS['accent']};
                font-size: 11px;
                font-weight: bold;
                min-width: 140px;
            }}
            QComboBox::drop-down {{ width: 18px; border-left: 1px solid {theme.COLORS['border']}; }}
            {theme.combo_popup_qss()}
        """)
        for child in (getattr(self, 'chat_content_widget', None), getattr(self, 'video_player_widget', None)):
            if child is not None and hasattr(child, 'refresh_theme'):
                child.refresh_theme()

    def refresh_models(self):
        """Forward refresh_models call to the active chatbot widget."""
        if hasattr(self, 'chat_content_widget'):
            self.chat_content_widget.refresh_models()

    def closeEvent(self, event):
        # Forward close event to children to clean up threads properly
        if hasattr(self, 'chat_content_widget'):
            try:
                self.chat_content_widget.closeEvent(event)
            except Exception:
                pass
        if hasattr(self, 'video_player_widget'):
            try:
                self.video_player_widget.closeEvent(event)
            except Exception:
                pass
        super().closeEvent(event)
