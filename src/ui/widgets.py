# Manga OCR & Typeset Tool v14.8.8
# ==============================
# ?? Import modul bawaan Python
# ==============================
# (tidak ada impor yang dibutuhkan)

# ==============================
# ?? Library pihak ketiga
# ==============================
# (tidak ada impor pihak ketiga yang dibutuhkan)

# ==============================
# ?? PyQt5 (dibagi per kategori)
# ==============================
import numpy as np
from PyQt5.QtWidgets import (
    QHBoxLayout, QWidget, QComboBox, QLineEdit, QToolButton, QStyledItemDelegate, QStyle
)
from PyQt5.QtGui import (
    QKeySequence, QWheelEvent, QFont, QColor, QPainter, QPainterPath, QBrush, QPen
)
from PyQt5.QtCore import (
    Qt, pyqtSignal, QEvent, QSize, QPointF, QRectF
)

from src.utils.geometry import mouse_button_to_name, mouse_name_to_button

class ShortcutCaptureEdit(QWidget):
    """Shortcut field that can capture keyboard or mouse buttons (incl. extra/back/pen buttons)."""
    sequence_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sequence = ''
        self._capturing = False
        self._ignore_mouse_event = False
        self.setFocusPolicy(Qt.StrongFocus)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.display = QLineEdit(self)
        self.display.setReadOnly(True)
        self.display.setPlaceholderText("Capture keyboard or mouse (back/forward/middle/pen)")
        self.display.installEventFilter(self)
        layout.addWidget(self.display, 1)

        self.capture_btn = QToolButton(self)
        self.capture_btn.setText("Capture")
        self.capture_btn.clicked.connect(self.start_capture)
        layout.addWidget(self.capture_btn)

    def eventFilter(self, obj, event):
        if obj is self.display and event.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
            # Start capture when the field itself is clicked.
            if not self._capturing:
                self.start_capture()
            return True
        return super().eventFilter(obj, event)

    def start_capture(self):
        if self._capturing:
            return
        self._capturing = True
        self._ignore_mouse_event = True  # ignore the click that started capture
        self.display.setText("Listening...")
        try:
            self.setFocus()
        except Exception:
            pass
        try:
            self.grabKeyboard()
            self.grabMouse()
        except Exception:
            pass

    def stop_capture(self):
        if not self._capturing:
            return
        self._capturing = False
        self._ignore_mouse_event = False
        try:
            self.releaseKeyboard()
            self.releaseMouse()
        except Exception:
            pass
        if not self._sequence:
            self.display.clear()

    def mousePressEvent(self, event):
        if not self._capturing:
            self.start_capture()
            return
        if self._ignore_mouse_event:
            # swallow the click that triggered capture
            self._ignore_mouse_event = False
            return
        self._record_mouse_sequence('press', event.button())

    def mouseReleaseEvent(self, event):
        if not self._capturing:
            return super().mouseReleaseEvent(event)
        if self._ignore_mouse_event:
            self._ignore_mouse_event = False
            return
        self._record_mouse_sequence('release', event.button())

    def mouseDoubleClickEvent(self, event):
        if not self._capturing:
            return super().mouseDoubleClickEvent(event)
        if self._ignore_mouse_event:
            self._ignore_mouse_event = False
            return
        self._record_mouse_sequence('double', event.button())

    def keyPressEvent(self, event):
        if not self._capturing:
            return super().keyPressEvent(event)
        key = event.key()
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta, Qt.Key_unknown):
            return
        if key == Qt.Key_Escape:
            self.clear_sequence()
            self.stop_capture()
            return
        sequence = QKeySequence(event.modifiers() | key).toString(QKeySequence.PortableText)
        self.set_sequence(sequence)
        self.stop_capture()

    def focusOutEvent(self, event):
        self.stop_capture()
        return super().focusOutEvent(event)

    def _record_mouse_sequence(self, event_type: str, button: Qt.MouseButton):
        name = mouse_button_to_name(button)
        if not name or name == "Unknown":
            name = f"Button{int(button)}"
        self.set_sequence(f"MOUSE:{event_type}:{name}")
        self.stop_capture()

    def set_sequence(self, sequence: str):
        self._sequence = sequence.strip() if sequence else ''
        self._update_display()
        self.sequence_changed.emit(self._sequence)

    def clear_sequence(self):
        self._sequence = ''
        self.display.clear()
        self.sequence_changed.emit('')

    def clear(self):
        self.clear_sequence()

    def sequence(self) -> str:
        return self._sequence

    def _update_display(self):
        if not self._sequence:
            self.display.clear()
            return
        if self._sequence.upper().startswith('MOUSE:'):
            parts = self._sequence.split(':')
            if len(parts) >= 3:
                evt = parts[1].lower()
                btn = parts[2]
                btn_label = btn
                friendly = mouse_button_to_name(mouse_name_to_button(btn) or Qt.NoButton)
                if friendly and friendly != "Unknown":
                    btn_label = friendly
                evt_label = evt.capitalize()
                self.display.setText(f"Mouse {evt_label} · {btn_label}")
                return
        seq_obj = QKeySequence(self._sequence)
        rendered = seq_obj.toString(QKeySequence.NativeText)
        self.display.setText(rendered if rendered else self._sequence)

class ScrollableComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)  # Pastikan bisa menerima event scroll

    def wheelEvent(self, event: QWheelEvent):
        """Menangani event scroll mouse untuk mengganti item."""
        delta = event.angleDelta().y()
        current_index = self.currentIndex()
        count = self.count()

        if count == 0:
            return

        if delta > 0:  # Scroll ke atas
            next_index = (current_index - 1 + count) % count
            self.setCurrentIndex(next_index)
        elif delta < 0:  # Scroll ke bawah
            next_index = (current_index + 1) % count
            self.setCurrentIndex(next_index)

        event.accept()

class FontDelegate(QStyledItemDelegate):
    def __init__(self, font_manager, parent=None):
        super().__init__(parent)
        self.font_manager = font_manager

    def paint(self, painter: QPainter, option, index):
        painter.save()
        
        # State styling
        is_selected = option.state & QStyle.State_Selected
        is_hovered = option.state & QStyle.State_MouseOver
        
        # Premium Obsidian Slate Palette
        if is_selected:
            bg_color = QColor('#1e293b')  # Slate-800 selected
            text_color = QColor('#38bdf8')  # Sky-400 (Cyan) accent
            preview_color = QColor('#7dd3fc')
        elif is_hovered:
            bg_color = QColor('#0f172a')  # Slate-900 hover
            text_color = QColor('#f8fafc')
            preview_color = QColor('#94a3b8')
        else:
            bg_color = QColor('#0d1117')  # Obsidian dark background
            text_color = QColor('#cbd5e1')
            preview_color = QColor('#64748b')
            
        painter.fillRect(option.rect, bg_color)
        
        font_name = index.data(Qt.DisplayRole)
        
        # Padding margins
        margin = 12
        rect_text = option.rect.adjusted(margin, 0, -margin, 0)
        
        # 1. Paint Font Family Name (standard clean font on the left)
        painter.setPen(text_color)
        standard_font = QFont("Segoe UI", 10)
        standard_font.setWeight(QFont.Bold if is_selected else QFont.Normal)
        painter.setFont(standard_font)
        painter.drawText(rect_text, Qt.AlignVCenter | Qt.AlignLeft, font_name)
        
        # 2. Paint Real-Time Font Preview (in that actual font on the right)
        try:
            if self.font_manager:
                actual_font = self.font_manager.create_qfont(font_name)
                actual_font.setPointSize(11)
                painter.setFont(actual_font)
                painter.setPen(preview_color)
                painter.drawText(rect_text, Qt.AlignVCenter | Qt.AlignRight, "AaBb Preview")
        except Exception:
            pass
            
        # Draw a very subtle bottom border separator
        painter.setPen(QColor('#1e293b'))
        painter.drawLine(option.rect.bottomLeft(), option.rect.bottomRight())
        
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), 40)


class InteractiveCurveEditor(QWidget):
    """Canva-style interactive Bezier curve editor widget for sidebar bending/warping text."""
    curveChanged = pyqtSignal(float, float, float, float)  # cp1_x, cp1_y, cp2_x, cp2_y

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 140)
        self.cp1 = QPointF(0.25, 0.2)
        self.cp2 = QPointF(0.75, 0.2)
        self.active_point = None  # None, 1 for CP1, 2 for CP2
        self.setCursor(Qt.PointingHandCursor)

    def set_control_points(self, cp1x, cp1y, cp2x, cp2y):
        self.cp1 = QPointF(max(0.0, min(cp1x, 1.0)), max(0.0, min(cp1y, 1.0)))
        self.cp2 = QPointF(max(0.0, min(cp2x, 1.0)), max(0.0, min(cp2y, 1.0)))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        
        # Obsidian dark background with rounded corners
        painter.setPen(QPen(QColor("#1e293b"), 1))
        painter.setBrush(QBrush(QColor("#090a0f")))
        painter.drawRoundedRect(QRectF(0, 0, w, h), 8.0, 8.0)

        # 4x4 Grid lines
        grid_pen = QPen(QColor("#1e293b"), 1, Qt.DashLine)
        painter.setPen(grid_pen)
        for i in range(1, 4):
            dx = w * i / 4.0
            dy = h * i / 4.0
            painter.drawLine(QPointF(dx, 0), QPointF(dx, h))
            painter.drawLine(QPointF(0, dy), QPointF(w, dy))

        # Baseline horizontal middle line
        baseline_pen = QPen(QColor("#334155"), 1.5, Qt.SolidLine)
        painter.setPen(baseline_pen)
        painter.drawLine(QPointF(0, h * 0.5), QPointF(w, h * 0.5))

        # Start and end points of the curve
        p0 = QPointF(0, h * 0.5)
        p3 = QPointF(w, h * 0.5)
        
        # Scale normalized points
        cp1_px = QPointF(self.cp1.x() * w, self.cp1.y() * h)
        cp2_px = QPointF(self.cp2.x() * w, self.cp2.y() * h)

        # Draw handles
        handle_pen = QPen(QColor("#64748b"), 1.2, Qt.DashLine)
        painter.setPen(handle_pen)
        painter.drawLine(p0, cp1_px)
        painter.drawLine(p3, cp2_px)

        # Draw Bezier path
        path = QPainterPath()
        path.moveTo(p0)
        path.cubicTo(cp1_px, cp2_px, p3)
        curve_pen = QPen(QColor("#38bdf8"), 2.5, Qt.SolidLine)
        painter.setPen(curve_pen)
        painter.drawPath(path)

        # Draw knobs
        painter.setPen(Qt.NoPen)
        # Knob 1
        painter.setBrush(QBrush(QColor("rgba(56, 189, 248, 0.25)")))
        painter.drawEllipse(cp1_px, 8.0, 8.0)
        painter.setBrush(QBrush(QColor("#38bdf8")))
        painter.drawEllipse(cp1_px, 4.5, 4.5)

        # Knob 2
        painter.setBrush(QBrush(QColor("rgba(56, 189, 248, 0.25)")))
        painter.drawEllipse(cp2_px, 8.0, 8.0)
        painter.setBrush(QBrush(QColor("#38bdf8")))
        painter.drawEllipse(cp2_px, 4.5, 4.5)

    def mousePressEvent(self, event):
        pos = event.pos()
        w = self.width()
        h = self.height()
        cp1_px = QPointF(self.cp1.x() * w, self.cp1.y() * h)
        cp2_px = QPointF(self.cp2.x() * w, self.cp2.y() * h)

        d1 = (pos.x() - cp1_px.x())**2 + (pos.y() - cp1_px.y())**2
        d2 = (pos.x() - cp2_px.x())**2 + (pos.y() - cp2_px.y())**2

        if d1 < 196:  # 14 pixels radius squared
            self.active_point = 1
        elif d2 < 196:
            self.active_point = 2
        else:
            self.active_point = None

    def mouseMoveEvent(self, event):
        if self.active_point is None:
            return
        pos = event.pos()
        w = self.width()
        h = self.height()

        nx = max(0.0, min(pos.x() / float(w), 1.0))
        ny = max(0.0, min(pos.y() / float(h), 1.0))

        if self.active_point == 1:
            self.cp1 = QPointF(nx, ny)
        elif self.active_point == 2:
            self.cp2 = QPointF(nx, ny)

        self.update()
        self.curveChanged.emit(self.cp1.x(), self.cp1.y(), self.cp2.x(), self.cp2.y())

    def mouseReleaseEvent(self, event):
        self.active_point = None


class CurvesGraphWidget(QWidget):
    """Photoshop-style curves adjustment graph (0-255 input vs 0-255 output) with spline interpolation."""
    curveUpdated = pyqtSignal(np.ndarray)  # Emits computed LUT (256 uint8 array)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(256, 256)
        # Default control points: start (0,0) and end (255,255)
        # Coordinates mapped where (0,0) is bottom-left, (255,255) is top-right
        self.points = [QPointF(0, 0), QPointF(255, 255)]
        self.active_point_idx = None
        self.setCursor(Qt.CrossCursor)
        self.lut = np.arange(256, dtype=np.uint8)
        self.histogram_data = None  # Optional: normalized gray histogram values [0.0 - 1.0]

    def set_curves_points(self, points):
        if len(points) >= 2:
            self.points = sorted([QPointF(max(0.0, min(p[0], 255.0)), max(0.0, min(p[1], 255.0))) for p in points], key=lambda p: p.x())
            # Ensure p0 is at x=0, p_last is at x=255
            self.points[0].setX(0.0)
            self.points[-1].setX(255.0)
            self.recompute_spline()

    def get_curves_points(self):
        return [[p.x(), p.y()] for p in self.points]

    def set_histogram_data(self, hist):
        """Allows drawing a gray-shaded histogram behind the curves line."""
        if hist is not None and len(hist) == 256:
            max_val = float(np.max(hist))
            if max_val > 0:
                self.histogram_data = hist / max_val
            else:
                self.histogram_data = None
            self.update()

    def recompute_spline(self):
        # Math spline solver for 256 look-up values
        n = len(self.points)
        xs = [p.x() for p in self.points]
        ys = [p.y() for p in self.points]
        
        lut = np.zeros(256, dtype=np.uint8)
        
        if n == 2:
            x0, y0 = xs[0], ys[0]
            x1, y1 = xs[1], ys[1]
            dx = x1 - x0 if x1 != x0 else 1.0
            for x in range(256):
                if x <= x0:
                    y = y0
                elif x >= x1:
                    y = y1
                else:
                    y = y0 + (x - x0) * (y1 - y0) / dx
                lut[x] = max(0, min(255, int(round(y))))
        else:
            # Natural cubic spline interpolation solver
            h = [xs[i+1] - xs[i] for i in range(n-1)]
            for i in range(len(h)):
                if h[i] == 0: h[i] = 0.01  # Prevent divide by zero

            a = [0.0] * n
            b = [1.0] * n
            c = [0.0] * n
            d = [0.0] * n
            
            for i in range(1, n-1):
                a[i] = h[i-1] / 6.0
                b[i] = (xs[i+1] - xs[i-1]) / 3.0
                c[i] = h[i] / 6.0
                d[i] = (ys[i+1] - ys[i]) / h[i] - (ys[i] - ys[i-1]) / h[i-1]
                
            c_prime = [0.0] * n
            d_prime = [0.0] * n
            
            c_prime[0] = c[0] / b[0]
            d_prime[0] = d[0] / b[0]
            for i in range(1, n):
                denom = b[i] - a[i] * c_prime[i-1]
                if denom == 0: denom = 0.0001
                c_prime[i] = c[i] / denom
                d_prime[i] = (d[i] - a[i] * d_prime[i-1]) / denom
                
            m = [0.0] * n
            m[n-1] = d_prime[n-1]
            for i in range(n-2, -1, -1):
                m[i] = d_prime[i] - c_prime[i] * m[i+1]
                
            for x in range(256):
                if x <= xs[0]:
                    y = ys[0]
                elif x >= xs[-1]:
                    y = ys[-1]
                else:
                    idx = 0
                    for i in range(n-1):
                        if xs[i] <= x <= xs[i+1]:
                            idx = i
                            break
                    h_i = h[idx]
                    x_diff_next = xs[idx+1] - x
                    x_diff_prev = x - xs[idx]
                    
                    y = (m[idx] * (x_diff_next ** 3) + m[idx+1] * (x_diff_prev ** 3)) / (6.0 * h_i) + \
                        ((ys[idx] - m[idx] * (h_i ** 2) / 6.0) * x_diff_next + \
                         (ys[idx+1] - m[idx+1] * (h_i ** 2) / 6.0) * x_diff_prev) / h_i
                lut[x] = max(0, min(255, int(round(y))))
                
        self.lut = lut
        self.update()
        self.curveUpdated.emit(self.lut)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        
        # Dark Obsidian background
        painter.fillRect(self.rect(), QColor("#090a0f"))

        # Draw gray shaded histogram if available
        if self.histogram_data is not None:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("rgba(71, 85, 105, 0.25)"))) # Slate gray transparent
            for x in range(256):
                val = self.histogram_data[x]
                if val > 0:
                    px = x * w / 255.0
                    ph = val * h
                    painter.drawRect(QRectF(px, h - ph, w / 255.0, ph))

        # Fine Grid
        grid_pen = QPen(QColor("#1e293b"), 1, Qt.SolidLine)
        painter.setPen(grid_pen)
        for i in range(1, 4):
            dx = w * i / 4.0
            dy = h * i / 4.0
            painter.drawLine(QPointF(dx, 0), QPointF(dx, h))
            painter.drawLine(QPointF(0, dy), QPointF(w, dy))

        # Diagonal reference line
        ref_pen = QPen(QColor("#334155"), 1, Qt.DashLine)
        painter.setPen(ref_pen)
        painter.drawLine(0, h, w, 0)

        # Plot current spline curve
        path = QPainterPath()
        path.moveTo(0, h - (float(self.lut[0]) * h / 255.0))
        for x in range(1, 256):
            path.lineTo(x * w / 255.0, h - (float(self.lut[x]) * h / 255.0))
            
        curve_pen = QPen(QColor("#38bdf8"), 2.5, Qt.SolidLine)
        painter.setPen(curve_pen)
        painter.drawPath(path)

        # Draw border
        painter.setPen(QPen(QColor("#1e293b"), 1.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(0, 0, w, h)

        # Draw control points
        for i, p in enumerate(self.points):
            px = p.x() * w / 255.0
            py = h - (p.y() * h / 255.0)
            
            painter.setPen(Qt.NoPen)
            if i == self.active_point_idx:
                painter.setBrush(QBrush(QColor("rgba(56, 189, 248, 0.4)")))
                painter.drawEllipse(QPointF(px, py), 9.0, 9.0)
                painter.setBrush(QBrush(QColor("#38bdf8")))
                painter.drawEllipse(QPointF(px, py), 5.0, 5.0)
            else:
                painter.setBrush(QBrush(QColor("rgba(56, 189, 248, 0.25)")))
                painter.drawEllipse(QPointF(px, py), 7.0, 7.0)
                painter.setBrush(QBrush(QColor("#cbd5e1")))
                painter.drawEllipse(QPointF(px, py), 4.0, 4.0)

    def mousePressEvent(self, event):
        pos = event.pos()
        w = self.width()
        h = self.height()
        
        # Clicked points
        clicked_idx = None
        for i, p in enumerate(self.points):
            px = p.x() * w / 255.0
            py = h - (p.y() * h / 255.0)
            dist = (pos.x() - px)**2 + (pos.y() - py)**2
            if dist < 121:  # 11 px radius
                clicked_idx = i
                break
                
        if clicked_idx is not None:
            self.active_point_idx = clicked_idx
            self.update()
        else:
            # Double click to add point, or single click if they clicked exactly on the curve.
            # Let's add point if clicked close to the curve line.
            # Map click pos to 0-255 coordinate
            cx = pos.x() * 255.0 / float(w)
            cy = (h - pos.y()) * 255.0 / float(h)
            
            # Find insertion index based on sorted X
            insert_idx = 0
            for i, p in enumerate(self.points):
                if p.x() > cx:
                    insert_idx = i
                    break
            else:
                insert_idx = len(self.points)
                
            # Prevent points too close to neighbors
            prev_p = self.points[insert_idx - 1]
            next_p = self.points[insert_idx] if insert_idx < len(self.points) else None
            
            if (cx - prev_p.x() > 5.0) and (next_p is None or next_p.x() - cx > 5.0):
                new_point = QPointF(cx, cy)
                self.points.insert(insert_idx, new_point)
                self.active_point_idx = insert_idx
                self.recompute_spline()

    def mouseMoveEvent(self, event):
        if self.active_point_idx is None:
            return
        pos = event.pos()
        w = self.width()
        h = self.height()
        
        # Map back to 0-255 range
        cx = max(0.0, min(pos.x() * 255.0 / float(w), 255.0))
        cy = max(0.0, min((h - pos.y()) * 255.0 / float(h), 255.0))
        
        # Start and end points are constrained horizontally
        if self.active_point_idx == 0:
            cx = 0.0
        elif self.active_point_idx == len(self.points) - 1:
            cx = 255.0
        else:
            # Clamped between previous and next point X positions
            prev_x = self.points[self.active_point_idx - 1].x()
            next_x = self.points[self.active_point_idx + 1].x()
            cx = max(prev_x + 1.0, min(cx, next_x - 1.0))
            
        self.points[self.active_point_idx].setX(cx)
        self.points[self.active_point_idx].setY(cy)
        self.recompute_spline()

    def mouseReleaseEvent(self, event):
        self.active_point_idx = None
        self.update()

    def mouseDoubleClickEvent(self, event):
        # Avoid duplication, mousePressEvent handles click creation
        pass

    def contextMenuEvent(self, event):
        # Right-click deletes the active or selected intermediate point
        pos = event.pos()
        w = self.width()
        h = self.height()
        
        target_idx = None
        for i, p in enumerate(self.points):
            if i == 0 or i == len(self.points) - 1:
                continue # Cannot delete endpoints
            px = p.x() * w / 255.0
            py = h - (p.y() * h / 255.0)
            dist = (pos.x() - px)**2 + (pos.y() - py)**2
            if dist < 121:
                target_idx = i
                break
                
        if target_idx is not None:
            self.points.pop(target_idx)
            self.active_point_idx = None
            self.recompute_spline()

