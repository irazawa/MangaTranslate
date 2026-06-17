# Manga OCR & Typeset Tool v14.8.3
# ============================================================
# UnifiedHelpDialog — menggabungkan About, Project Stats,
# Pricing Editor, dan Session Analytics dalam satu dialog tab.
# ============================================================
import os
import copy
import csv

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QLabel,
    QPushButton, QScrollArea, QFrame, QGridLayout, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QDoubleSpinBox,
    QMessageBox, QFileDialog, QLineEdit, QSizePolicy, QSpacerItem,
    QListWidgetItem, QApplication
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor, QFont, QBrush

from src.core.app_info import APP_VERSION
from src.ui.texts import DialogText


_STYLE = """
QDialog {
    background-color: #090a0f;
    color: #cbd5e1;
    font-family: 'Outfit', 'Inter', 'Segoe UI', sans-serif;
    font-size: 9pt;
}
QTabWidget::pane {
    border: 1px solid #1e293b;
    border-radius: 6px;
    background: #0b0e17;
    top: -1px;
}
QTabBar::tab {
    background: #0e111a;
    color: #64748b;
    border: 1px solid #1e293b;
    border-bottom: none;
    padding: 6px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-size: 9pt;
}
QTabBar::tab:selected {
    background: #0b0e17;
    color: #38bdf8;
    border-bottom: 2px solid #38bdf8;
}
QTabBar::tab:hover:!selected { color: #94a3b8; }
QScrollArea { border: none; background: transparent; }
QWidget#tab_inner { background: transparent; }
QLabel { color: #cbd5e1; background: transparent; }
QLabel#section_title {
    color: #38bdf8;
    font-size: 10pt;
    font-weight: bold;
}
QFrame#sep {
    background: #1e293b;
    max-height: 1px;
    border: none;
}
QFrame#card {
    background: #0e111a;
    border: 1px solid #1e293b;
    border-radius: 8px;
}
QProgressBar {
    background: #1e293b;
    border: none;
    border-radius: 4px;
    height: 10px;
}
QProgressBar::chunk { border-radius: 4px; }
QPushButton {
    background: #1e293b;
    color: #94a3b8;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 5px 14px;
    font-size: 9pt;
}
QPushButton:hover {
    background: #334155;
    color: #f1f5f9;
    border-color: #38bdf8;
}
QPushButton#accent_btn {
    background: #0ea5e9;
    color: #f8fafc;
    border: none;
    font-weight: bold;
}
QPushButton#accent_btn:hover { background: #38bdf8; color: #0f172a; }
QPushButton#danger_btn {
    background: #7f1d1d;
    color: #fca5a5;
    border: 1px solid #b91c1c;
}
QPushButton#danger_btn:hover { background: #b91c1c; color: #fff; }
QTableWidget {
    background: #060810;
    color: #cbd5e1;
    border: 1px solid #1e293b;
    border-radius: 4px;
    gridline-color: #1e293b;
    selection-background-color: #1e3a5f;
    selection-color: #38bdf8;
}
QTableWidget QHeaderView::section {
    background: #0e111a;
    color: #64748b;
    border: none;
    border-bottom: 1px solid #1e293b;
    padding: 4px 8px;
    font-size: 8pt;
}
QDoubleSpinBox {
    background: #0e111a;
    color: #cbd5e1;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 2px 4px;
    font-size: 8pt;
}
QDoubleSpinBox:focus { border-color: #38bdf8; }
QScrollBar:vertical {
    background: #0e111a;
    width: 6px;
}
QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 3px;
}
"""

PROVIDER_COLORS = {
    'Gemini': '#4ade80',
    'OpenAI': '#60a5fa',
    'OpenRouter': '#f472b6',
}
DEFAULT_COLOR = '#94a3b8'
PRICE_DISPLAY_MULTIPLIER = 1_000_000.0


class UnifiedHelpDialog(QDialog):
    """
    Dialog terpadu Help / Usage yang menggabungkan:
      Tab 1 — 📋 Overview : About app + Project Statistics
      Tab 2 — 💰 Pricing   : Daftar model + harga per 1M token (bisa diedit user)
      Tab 3 — 📈 Analytics : Usage, biaya sesi, rate limit, export CSV
    """

    def __init__(self, parent=None, *,
                 app_version=APP_VERSION,
                 ai_providers=None,
                 openrouter_pricing_db=None,
                 usage_data=None,
                 total_cost=0.0,
                 usd_to_idr_rate=16200.0,
                 total_input_tokens=0,
                 total_output_tokens=0,
                 translated_count=0,
                 # project stats
                 project_dir=None,
                 image_files=None,
                 all_typeset_data=None,
                 # callback when pricing edited
                 on_pricing_saved=None):
        super().__init__(parent)
        self.app_version = app_version
        self.ai_providers = copy.deepcopy(ai_providers or {})
        self.openrouter_pricing_db = openrouter_pricing_db or {}
        self.usage_data = usage_data or {}
        self.total_cost = total_cost
        self.usd_to_idr_rate = usd_to_idr_rate
        self.total_input_tokens = total_input_tokens
        self.total_output_tokens = total_output_tokens
        self.translated_count = translated_count
        self.project_dir = project_dir
        self.image_files = image_files or []
        self.all_typeset_data = all_typeset_data or {}
        self.on_pricing_saved = on_pricing_saved   # callable(ai_providers_dict)

        self.setWindowTitle(DialogText.HELP_USAGE_TITLE)
        self.setModal(True)
        self.resize(820, 620)
        self.setStyleSheet(_STYLE)
        self._build_ui()

    # ─────────────────────────────────────────────────────────────────────────
    # Builder
    # ─────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = QWidget()
        hdr.setStyleSheet("background: #0e111a; border-bottom: 1px solid #1e293b;")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(20, 12, 20, 12)
        title = QLabel(DialogText.HELP_USAGE_HEADER)
        title.setStyleSheet("font-size:14pt; font-weight:bold; color:#38bdf8;")
        hl.addWidget(title)
        hl.addStretch(1)
        ver = QLabel(f"v{self.app_version}")
        ver.setStyleSheet("color:#475569; font-size:9pt;")
        hl.addWidget(ver)
        outer.addWidget(hdr)

        # ── Tabs ──────────────────────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setContentsMargins(8, 8, 8, 8)
        self.tabs.addTab(self._make_overview_tab(),  "📋  Overview")
        self.tabs.addTab(self._make_pricing_tab(),   "💰  Pricing")
        self.tabs.addTab(self._make_analytics_tab(), "📈  Analytics")

        tab_wrapper = QWidget()
        tw_layout = QVBoxLayout(tab_wrapper)
        tw_layout.setContentsMargins(12, 8, 12, 8)
        tw_layout.addWidget(self.tabs)
        outer.addWidget(tab_wrapper, 1)

        # ── Footer ────────────────────────────────────────────────────────────
        ftr = QWidget()
        ftr.setStyleSheet("background: #0e111a; border-top: 1px solid #1e293b;")
        fl = QHBoxLayout(ftr)
        fl.setContentsMargins(20, 8, 20, 8)
        fl.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(88)
        close_btn.clicked.connect(self.accept)
        fl.addWidget(close_btn)
        outer.addWidget(ftr)

    # ─────────────────────────────────────────────────────────────────────────
    # Helper widgets
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _scrollable(widget) -> QScrollArea:
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setFrameShape(QFrame.NoFrame)
        sa.setWidget(widget)
        return sa

    @staticmethod
    def _section(vbox, text):
        lbl = QLabel(text)
        lbl.setObjectName("section_title")
        vbox.addWidget(lbl)
        sep = QFrame()
        sep.setObjectName("sep")
        sep.setFixedHeight(1)
        vbox.addWidget(sep)

    @staticmethod
    def _row(vbox, label, value, value_color="#f1f5f9"):
        lbl = QLabel(
            f"<span style='color:#64748b;'>{label}</span>"
            f"  <b style='color:{value_color};'>{value}</b>"
        )
        lbl.setTextFormat(Qt.RichText)
        vbox.addWidget(lbl)

    # ─────────────────────────────────────────────────────────────────────────
    # Tab 1 — Overview
    # ─────────────────────────────────────────────────────────────────────────
    def _make_overview_tab(self) -> QWidget:
        inner = QWidget(); inner.setObjectName("tab_inner")
        vbox = QVBoxLayout(inner)
        vbox.setContentsMargins(16, 14, 16, 14)
        vbox.setSpacing(10)

        # About
        self._section(vbox, "ℹ️ About")
        about_lbl = QLabel(
            f"<b style='color:#f1f5f9;font-size:12pt;'>Manga OCR &amp; Typeset Tool</b>"
            f"<span style='color:#64748b;'> v{self.app_version}</span><br>"
            "<span style='color:#94a3b8;'>Aplikasi desktop untuk baca, OCR, terjemah, dan typeset teks manga/komik.<br>"
            "Powered by Python, PyQt5, dan berbagai AI API.</span>"
        )
        about_lbl.setTextFormat(Qt.RichText)
        about_lbl.setWordWrap(True)
        vbox.addWidget(about_lbl)
        vbox.addSpacing(8)

        # Session cost quick-view
        self._section(vbox, "💰 Session Cost")
        cost_idr = self.total_cost * self.usd_to_idr_rate
        self._row(vbox, "Estimasi Biaya (USD)", f"${self.total_cost:.6f}", "#4ade80")
        self._row(vbox, "Estimasi Biaya (IDR)", f"Rp {cost_idr:,.0f}", "#fbbf24")
        self._row(vbox, "Total Input Tokens",   f"{self.total_input_tokens:,}")
        self._row(vbox, "Total Output Tokens",  f"{self.total_output_tokens:,}")
        self._row(vbox, "Snippets Translated",  str(self.translated_count))
        vbox.addSpacing(8)

        # Project stats
        if self.project_dir:
            self._section(vbox, "📁 Project Statistics")
            total_pages = len([f for f in self.image_files if "_typeset" not in f.lower()])
            pages_done = 0; total_areas = 0; areas_text = 0; total_words = 0
            model_cnt: dict[str, int] = {}

            for data in self.all_typeset_data.values():
                areas = data.get('areas', [])
                if areas: pages_done += 1
                for area in areas:
                    total_areas += 1
                    txt = (area.text if hasattr(area, 'text') else area.get('text', '')) or ''
                    if txt.strip():
                        areas_text += 1
                        total_words += len(txt.split())
                    ml = None
                    if hasattr(area, 'review_notes') and isinstance(getattr(area, 'review_notes', None), dict):
                        ml = area.review_notes.get('ai_model')
                    elif isinstance(area, dict):
                        ml = area.get('ai_model_label') or area.get('ai_model')
                    if isinstance(ml, (list, tuple)) and len(ml) >= 2:
                        ml = f"{ml[0]} ({ml[1]})"
                    model_cnt[ml or 'Unknown'] = model_cnt.get(ml or 'Unknown', 0) + 1

            pct = round(pages_done / total_pages * 100, 1) if total_pages else 0
            self._row(vbox, "Folder",          os.path.basename(self.project_dir))
            self._row(vbox, "Total Halaman",   str(total_pages))
            self._row(vbox, "Halaman Selesai", f"{pages_done}  ({pct}%)")
            self._row(vbox, "Total Area",      str(total_areas))
            self._row(vbox, "Area dengan Teks",f"{areas_text}")
            self._row(vbox, "Total Kata",      f"{total_words:,}")

            if model_cnt:
                vbox.addSpacing(4)
                self._section(vbox, "🤖 Model Used (per area)")
                for m, c in sorted(model_cnt.items(), key=lambda x: -x[1]):
                    self._row(vbox, m, str(c))
        else:
            notice = QLabel("<i style='color:#475569;'>Buka folder/project untuk melihat statistik project.</i>")
            notice.setTextFormat(Qt.RichText)
            vbox.addWidget(notice)

        vbox.addStretch(1)
        return self._scrollable(inner)

    # ─────────────────────────────────────────────────────────────────────────
    # Tab 2 — Pricing Editor
    # ─────────────────────────────────────────────────────────────────────────
    def _make_pricing_tab(self) -> QWidget:
        outer_w = QWidget(); outer_w.setObjectName("tab_inner")
        outer_v = QVBoxLayout(outer_w)
        outer_v.setContentsMargins(12, 10, 12, 10)
        outer_v.setSpacing(8)

        info = QLabel(
            "<span style='color:#94a3b8;'>Harga di bawah digunakan untuk kalkulasi biaya sesi. "
            "Kolom <b style='color:#38bdf8;'>Input $/1M tok</b> dan <b style='color:#38bdf8;'>Output $/1M tok</b> "
            "bisa diedit langsung — klik sel, ubah nilainya, lalu tekan <b>💾 Simpan</b>.<br>"
            "Nilai internal tetap disimpan per token agar kalkulasi biaya tetap akurat. "
            "Harga OpenRouter diambil <i>otomatis</i> dari API mereka saat startup. "
            "Model dengan harga 0 berarti gratis atau belum diketahui.</span>"
        )
        info.setTextFormat(Qt.RichText)
        info.setWordWrap(True)
        outer_v.addWidget(info)

        # Tabel
        headers = ["Provider", "Model ID", "Display Name", "Input $/1M tok", "Output $/1M tok", "Limits RPM/RPD"]
        self._pricing_table = QTableWidget()
        self._pricing_table.setColumnCount(len(headers))
        self._pricing_table.setHorizontalHeaderLabels(headers)
        self._pricing_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._pricing_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self._pricing_table.setAlternatingRowColors(False)
        self._pricing_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._pricing_table.verticalHeader().setVisible(False)
        self._pricing_table.setEditTriggers(QTableWidget.NoEditTriggers)  # spin box handles edit
        self._pricing_table.setMinimumHeight(300)
        outer_v.addWidget(self._pricing_table, 1)

        self._populate_pricing_table()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        refresh_btn = QPushButton("🔄 Refresh dari OpenRouter")
        refresh_btn.clicked.connect(self._refresh_openrouter_prices)
        btn_row.addWidget(refresh_btn)

        btn_row.addStretch(1)

        reset_btn = QPushButton("↩ Reset ke Default")
        reset_btn.setObjectName("danger_btn")
        reset_btn.clicked.connect(self._reset_pricing_to_default)
        btn_row.addWidget(reset_btn)

        save_btn = QPushButton("💾  Simpan Perubahan")
        save_btn.setObjectName("accent_btn")
        save_btn.clicked.connect(self._save_pricing)
        btn_row.addWidget(save_btn)

        outer_v.addLayout(btn_row)

        note = QLabel(
            "<span style='color:#475569; font-size:8pt;'>* Perubahan harga hanya berlaku untuk sesi ini "
            "dan tidak mempengaruhi data usage yang sudah tersimpan.</span>"
        )
        note.setTextFormat(Qt.RichText)
        outer_v.addWidget(note)

        return outer_w

    def _populate_pricing_table(self):
        tbl = self._pricing_table
        tbl.setRowCount(0)

        # Gabungkan AI_PROVIDERS + openrouter_pricing_db
        all_entries = []
        for provider, models in self.ai_providers.items():
            for model_id, info in models.items():
                all_entries.append((provider, model_id, info))

        # Tambahkan OpenRouter models dari pricing_db yang belum ada di ai_providers
        or_existing = set(self.ai_providers.get('OpenRouter', {}).keys())
        for model_id, info in self.openrouter_pricing_db.items():
            if model_id not in or_existing:
                all_entries.append(('OpenRouter', model_id, info))

        tbl.setRowCount(len(all_entries))

        for row, (provider, model_id, info) in enumerate(all_entries):
            pricing = info.get('pricing', {'input': 0.0, 'output': 0.0})
            limits  = info.get('limits', {})
            display = info.get('display') or info.get('name') or model_id
            color   = PROVIDER_COLORS.get(provider, DEFAULT_COLOR)

            def _item(text, editable=False, align=Qt.AlignLeft | Qt.AlignVCenter):
                it = QTableWidgetItem(str(text))
                it.setTextAlignment(align)
                if not editable:
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                it.setForeground(QBrush(QColor('#cbd5e1')))
                return it

            prov_item = _item(provider)
            prov_item.setForeground(QBrush(QColor(color)))
            tbl.setItem(row, 0, prov_item)
            tbl.setItem(row, 1, _item(model_id))
            tbl.setItem(row, 2, _item(display))

            # Kolom Input $/1M tok — QDoubleSpinBox
            spin_in = QDoubleSpinBox()
            spin_in.setRange(0.0, 1_000_000.0)
            spin_in.setDecimals(6)
            spin_in.setSingleStep(0.01)
            spin_in.setValue(float(pricing.get('input', 0.0)) * PRICE_DISPLAY_MULTIPLIER)
            spin_in.setProperty('_provider', provider)
            spin_in.setProperty('_model', model_id)
            spin_in.setProperty('_field', 'input')
            spin_in.setStyleSheet("QDoubleSpinBox { background: #0e111a; color: #93c5fd; border: none; }")
            tbl.setCellWidget(row, 3, spin_in)

            # Kolom Output $/1M tok — QDoubleSpinBox
            spin_out = QDoubleSpinBox()
            spin_out.setRange(0.0, 1_000_000.0)
            spin_out.setDecimals(6)
            spin_out.setSingleStep(0.01)
            spin_out.setValue(float(pricing.get('output', 0.0)) * PRICE_DISPLAY_MULTIPLIER)
            spin_out.setProperty('_provider', provider)
            spin_out.setProperty('_model', model_id)
            spin_out.setProperty('_field', 'output')
            spin_out.setStyleSheet("QDoubleSpinBox { background: #0e111a; color: #86efac; border: none; }")
            tbl.setCellWidget(row, 4, spin_out)

            rpm = limits.get('rpm', '-')
            rpd = limits.get('rpd', '-')
            limits_str = f"{rpm}/{rpd}" if rpm != '-' else "—"
            tbl.setItem(row, 5, _item(limits_str, align=Qt.AlignCenter | Qt.AlignVCenter))

        tbl.resizeColumnsToContents()

    def _save_pricing(self):
        """Baca nilai dari semua spinbox, update self.ai_providers, panggil callback."""
        tbl = self._pricing_table
        for row in range(tbl.rowCount()):
            spin_in  = tbl.cellWidget(row, 3)
            spin_out = tbl.cellWidget(row, 4)
            if not spin_in or not spin_out:
                continue
            provider  = spin_in.property('_provider')
            model_id  = spin_in.property('_model')
            val_in    = spin_in.value() / PRICE_DISPLAY_MULTIPLIER
            val_out   = spin_out.value() / PRICE_DISPLAY_MULTIPLIER

            # Update di ai_providers
            if provider in self.ai_providers and model_id in self.ai_providers[provider]:
                self.ai_providers[provider][model_id].setdefault('pricing', {})['input']  = val_in
                self.ai_providers[provider][model_id].setdefault('pricing', {})['output'] = val_out
            else:
                # Model dari openrouter_pricing_db
                if model_id in self.openrouter_pricing_db:
                    self.openrouter_pricing_db[model_id].setdefault('pricing', {})['input']  = val_in
                    self.openrouter_pricing_db[model_id].setdefault('pricing', {})['output'] = val_out

        # Panggil callback agar parent bisa simpan ke AI_PROVIDERS
        if callable(self.on_pricing_saved):
            self.on_pricing_saved(self.ai_providers, self.openrouter_pricing_db)

        QMessageBox.information(self, "Tersimpan",
                                "Harga berhasil diperbarui.\n"
                                "Input tabel dibaca sebagai USD per 1M token; perhitungan biaya tetap memakai nilai per-token internal.")

    def _refresh_openrouter_prices(self):
        """Ambil ulang harga dari OpenRouter API dan refresh tabel."""
        parent = self.parent()
        if parent and hasattr(parent, 'fetch_openrouter_pricing_async'):
            QMessageBox.information(self, "Refresh",
                                    "Permintaan harga terbaru OpenRouter sedang diambil di latar belakang.\n"
                                    "Tutup dan buka kembali dialog ini setelah beberapa detik.")
            parent.fetch_openrouter_pricing_async()
        else:
            QMessageBox.warning(self, "Tidak Tersedia",
                                "Tidak dapat memanggil refresh dari konteks ini.")

    def _reset_pricing_to_default(self):
        """Reset semua harga editable ke nilai default di ai_providers asal."""
        reply = QMessageBox.question(self, "Reset Harga",
                                     "Reset semua harga ke nilai default aplikasi?\n"
                                     "(Harga OpenRouter yang sudah diambil otomatis tidak berubah.)",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._populate_pricing_table()
            QMessageBox.information(self, "Reset", "Harga sudah dikembalikan ke default.\nTekan Simpan untuk menerapkan.")

    # ─────────────────────────────────────────────────────────────────────────
    # Tab 3 — Analytics
    # ─────────────────────────────────────────────────────────────────────────
    def _make_analytics_tab(self) -> QWidget:
        inner = QWidget(); inner.setObjectName("tab_inner")
        vbox = QVBoxLayout(inner)
        vbox.setContentsMargins(16, 14, 16, 14)
        vbox.setSpacing(10)

        provider_usage = self.usage_data.get('provider_usage', {})

        # Tombol actions di atas
        act_row = QHBoxLayout()
        act_row.setSpacing(8)
        exp_btn = QPushButton("⬇  Export CSV")
        exp_btn.setObjectName("accent_btn")
        exp_btn.clicked.connect(self._export_csv)
        act_row.addWidget(exp_btn)
        act_row.addStretch(1)
        rst_btn = QPushButton("🗑  Reset Usage")
        rst_btn.setObjectName("danger_btn")
        rst_btn.clicked.connect(self._reset_usage)
        act_row.addWidget(rst_btn)
        vbox.addLayout(act_row)

        # Cost summary
        self._section(vbox, "💰 Cost Summary")
        cost_idr = self.total_cost * self.usd_to_idr_rate
        self._row(vbox, "Total Session Cost (USD)", f"${self.total_cost:.6f}", "#4ade80")
        self._row(vbox, "Estimasi IDR",             f"Rp {cost_idr:,.0f}",    "#fbbf24")
        self._row(vbox, "Total Input Tokens",       f"{self.total_input_tokens:,}")
        self._row(vbox, "Total Output Tokens",      f"{self.total_output_tokens:,}")
        self._row(vbox, "Tanggal Data",             self.usage_data.get('date', '-'), "#64748b")
        vbox.addSpacing(6)

        # Usage per model (bar chart)
        self._section(vbox, "📊 API Usage per Model (Daily)")
        all_counts = [
            m.get('daily_count', 0)
            for models in provider_usage.values()
            for m in models.values()
        ]
        global_max = max(all_counts) if all_counts else 1

        for provider in sorted(provider_usage.keys()):
            models = provider_usage[provider]
            if not models:
                continue
            color = PROVIDER_COLORS.get(provider, DEFAULT_COLOR)
            prov_lbl = QLabel(f"<b style='color:{color};font-size:10pt;'>▶ {provider}</b>")
            prov_lbl.setTextFormat(Qt.RichText)
            vbox.addWidget(prov_lbl)

            for model_name in sorted(models.keys()):
                mdata = models[model_name]
                daily = mdata.get('daily_count', 0)
                model_info = self.ai_providers.get(provider, {}).get(model_name, {})
                if not model_info:
                    model_info = self.openrouter_pricing_db.get(model_name, {})
                limits    = model_info.get('limits', {'rpm': 300, 'rpd': 1000})
                rpd_limit = limits.get('rpd', 1000)
                display   = model_info.get('display') or model_name
                if len(display) > 45:
                    display = display[:42] + "…"

                rw = QWidget()
                rl = QHBoxLayout(rw)
                rl.setContentsMargins(8, 2, 8, 2)
                rl.setSpacing(10)

                nm_lbl = QLabel(f"<span style='color:#cbd5e1;'>{display}</span>")
                nm_lbl.setTextFormat(Qt.RichText)
                nm_lbl.setMinimumWidth(220)
                nm_lbl.setMaximumWidth(260)
                rl.addWidget(nm_lbl)

                rpd_pct = int(min(daily / rpd_limit * 100, 100)) if rpd_limit > 0 else 0
                bar = QProgressBar()
                bar.setRange(0, 100)
                bar.setValue(rpd_pct)
                bar.setFixedHeight(10)
                bar.setTextVisible(False)
                chunk_c = "#ef4444" if rpd_pct >= 90 else ("#f59e0b" if rpd_pct >= 60 else color)
                bar.setStyleSheet(
                    f"QProgressBar{{background:#1e293b;border:none;border-radius:4px;}}"
                    f"QProgressBar::chunk{{background:{chunk_c};border-radius:4px;}}"
                )
                rl.addWidget(bar, 1)

                cnt_lbl = QLabel(f"<span style='color:#94a3b8;font-size:8pt;'>{daily}/{rpd_limit} daily</span>")
                cnt_lbl.setTextFormat(Qt.RichText)
                cnt_lbl.setMinimumWidth(100)
                rl.addWidget(cnt_lbl)

                vbox.addWidget(rw)

        vbox.addSpacing(6)

        # Rate limit status
        self._section(vbox, "⏱ Rate Limit Status (RPM saat ini)")
        has_any = False
        for provider in sorted(provider_usage.keys()):
            color = PROVIDER_COLORS.get(provider, DEFAULT_COLOR)
            for model_name, mdata in sorted(provider_usage[provider].items()):
                rpm   = mdata.get('minute_count', 0)
                daily = mdata.get('daily_count', 0)
                if rpm == 0 and daily == 0:
                    continue
                has_any = True
                model_info = self.ai_providers.get(provider, {}).get(model_name, {})
                if not model_info:
                    model_info = self.openrouter_pricing_db.get(model_name, {})
                limits    = model_info.get('limits', {'rpm': 60, 'rpd': 1000})
                rpm_limit = limits.get('rpm', 60)
                display   = model_info.get('display') or model_name
                if len(display) > 45:
                    display = display[:42] + "…"
                rpm_pct = int(min(rpm / rpm_limit * 100, 100)) if rpm_limit > 0 else 0
                icon = "🔴" if rpm_pct >= 100 else ("🟡" if rpm_pct >= 60 else "🟢")

                rw = QWidget()
                rl = QHBoxLayout(rw)
                rl.setContentsMargins(8, 2, 8, 2)
                rl.setSpacing(8)

                rl.addWidget(QLabel(icon))

                nm = QLabel(f"<span style='color:#cbd5e1;'>{display}</span>")
                nm.setTextFormat(Qt.RichText)
                nm.setMinimumWidth(220)
                nm.setMaximumWidth(260)
                rl.addWidget(nm)

                rpm_bar = QProgressBar()
                rpm_bar.setRange(0, 100)
                rpm_bar.setValue(rpm_pct)
                rpm_bar.setFixedHeight(8)
                rpm_bar.setTextVisible(False)
                chunk_c = "#ef4444" if rpm_pct >= 90 else ("#f59e0b" if rpm_pct >= 60 else color)
                rpm_bar.setStyleSheet(
                    f"QProgressBar{{background:#1e293b;border:none;border-radius:3px;}}"
                    f"QProgressBar::chunk{{background:{chunk_c};border-radius:3px;}}"
                )
                rl.addWidget(rpm_bar, 1)

                rpm_lbl = QLabel(f"<span style='color:#94a3b8;font-size:8pt;'>{rpm}/{rpm_limit} rpm</span>")
                rpm_lbl.setTextFormat(Qt.RichText)
                rpm_lbl.setMinimumWidth(90)
                rl.addWidget(rpm_lbl)

                vbox.addWidget(rw)

        if not has_any:
            nl = QLabel("<i style='color:#475569;'>Belum ada model yang digunakan sesi ini.</i>")
            nl.setTextFormat(Qt.RichText)
            vbox.addWidget(nl)

        vbox.addStretch(1)
        return self._scrollable(inner)

    # ─────────────────────────────────────────────────────────────────────────
    # Export CSV
    # ─────────────────────────────────────────────────────────────────────────
    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Analytics CSV", "session_analytics.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        provider_usage = self.usage_data.get('provider_usage', {})
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(["Date", "Provider", "Model", "Daily Count", "RPD Limit", "RPD %",
                             "RPM (last)", "RPM Limit", "Input $/1M tok", "Output $/1M tok"])
                date_str = self.usage_data.get('date', '-')
                for provider in sorted(provider_usage.keys()):
                    for model_id in sorted(provider_usage[provider].keys()):
                        mdata = provider_usage[provider][model_id]
                        mi = self.ai_providers.get(provider, {}).get(model_id) or \
                             self.openrouter_pricing_db.get(model_id, {})
                        limits = mi.get('limits', {'rpm': 60, 'rpd': 1000})
                        pr = mi.get('pricing', {'input': 0, 'output': 0})
                        daily = mdata.get('daily_count', 0)
                        rpm   = mdata.get('minute_count', 0)
                        rpd_l = limits.get('rpd', 1000)
                        rpm_l = limits.get('rpm', 60)
                        rpd_pct = round(daily / rpd_l * 100, 2) if rpd_l else 0
                        w.writerow([date_str, provider, model_id, daily, rpd_l, f"{rpd_pct}%",
                                    rpm, rpm_l,
                                    pr.get('input', 0) * PRICE_DISPLAY_MULTIPLIER,
                                    pr.get('output', 0) * PRICE_DISPLAY_MULTIPLIER])
                w.writerow([])
                w.writerow(["Total Cost (USD)", f"${self.total_cost:.6f}"])
                w.writerow(["Estimasi IDR", f"Rp {self.total_cost * self.usd_to_idr_rate:,.0f}"])
                w.writerow(["Input Tokens", self.total_input_tokens])
                w.writerow(["Output Tokens", self.total_output_tokens])
            QMessageBox.information(self, "Export Berhasil", f"Tersimpan ke:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Gagal", str(e))

    # ─────────────────────────────────────────────────────────────────────────
    # Reset usage
    # ─────────────────────────────────────────────────────────────────────────
    def _reset_usage(self):
        reply = QMessageBox.question(
            self, "Reset Usage",
            "Reset semua daily count dan minute count ke nol?\nTotal cost tidak direset.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        for provider in self.usage_data.get('provider_usage', {}).values():
            for mdata in provider.values():
                mdata['daily_count'] = 0
                mdata['minute_count'] = 0
        parent = self.parent()
        if parent and hasattr(parent, 'save_usage_data'):
            parent.save_usage_data()
        QMessageBox.information(self, "Reset", "Usage data berhasil direset.")
        self.accept()
