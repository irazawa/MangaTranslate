from PyQt5.QtCore import Qt, QRectF, QPointF, QRect, QPoint
from PyQt5.QtGui import QPolygonF

def coerce_float(val, default=0.0, minimum=None, maximum=None):
    try:
        f = float(val)
        if minimum is not None:
            f = max(minimum, f)
        if maximum is not None:
            f = min(maximum, f)
        return f
    except (ValueError, TypeError):
        return default

def coerce_int(val, default=0, minimum=None, maximum=None):
    try:
        i = int(val)
        if minimum is not None:
            i = max(minimum, i)
        if maximum is not None:
            i = min(maximum, i)
        return i
    except (ValueError, TypeError):
        return default

def mouse_button_to_name(btn):
    mapping = {
        Qt.LeftButton: 'Left',
        Qt.RightButton: 'Right',
        Qt.MiddleButton: 'Middle',
        Qt.BackButton: 'Back',
        Qt.ForwardButton: 'Forward',
        Qt.TaskButton: 'Task',
        Qt.NoButton: 'None',
    }
    return mapping.get(btn, 'Unknown')

def mouse_name_to_button(name):
    mapping = {
        'Left': Qt.LeftButton,
        'Right': Qt.RightButton,
        'Middle': Qt.MiddleButton,
        'Back': Qt.BackButton,
        'Forward': Qt.ForwardButton,
        'Task': Qt.TaskButton,
        'None': Qt.NoButton,
    }
    return mapping.get(name, Qt.NoButton)

def rect_to_dict(rect):
    if rect is None:
        return None
    return {
        'x': rect.x(),
        'y': rect.y(),
        'width': rect.width(),
        'height': rect.height()
    }

def dict_to_rect(d):
    if not d:
        return None
    x = d.get('x', 0)
    y = d.get('y', 0)
    w = d.get('width', d.get('w', 0))
    h = d.get('height', d.get('h', 0))
    return QRectF(x, y, w, h)

def polygon_to_list(polygon, compact=True):
    """Serialize a polygon to a list.

    When *compact* is True (default, schema v4+), each point is stored as a
    two-element list ``[x, y]`` which is much more space-efficient than the
    legacy ``{"x": x, "y": y}`` object form.  The legacy form is retained for
    explicit opt-out (e.g. migration helpers).
    """
    if polygon is None:
        return []
    if compact:
        return [
            [int(polygon.at(i).x()), int(polygon.at(i).y())]
            for i in range(polygon.count())
        ]
    # Legacy format (schema v1–v3)
    return [
        {'x': polygon.at(i).x(), 'y': polygon.at(i).y()}
        for i in range(polygon.count())
    ]

def list_to_polygon(pts):
    """Deserialize a polygon from a list.

    Supports both the compact ``[[x, y], ...]`` format (schema v4+) and the
    legacy ``[{"x": x, "y": y}, ...]`` format (schema v1–v3) transparently.
    """
    if not pts:
        return QPolygonF()
    poly = QPolygonF()
    for pt in pts:
        if isinstance(pt, dict):
            # Legacy format: {"x": x, "y": y}
            poly.append(QPointF(pt.get('x', 0.0), pt.get('y', 0.0)))
        elif isinstance(pt, (list, tuple)) and len(pt) >= 2:
            # Compact format: [x, y]
            poly.append(QPointF(pt[0], pt[1]))
    return poly

def to_qrect(r):
    if r is None:
        return QRect()
    if isinstance(r, QRectF):
        return r.toRect()
    if isinstance(r, QRect):
        return r
    if isinstance(r, dict):
        try:
            return QRect(
                int(coerce_float(r.get('x', 0))),
                int(coerce_float(r.get('y', 0))),
                int(coerce_float(r.get('width', r.get('w', 0)))),
                int(coerce_float(r.get('height', r.get('h', 0))))
            )
        except Exception:
            return QRect()
    try:
        x = r.x() if callable(getattr(r, 'x', None)) else getattr(r, 'x', 0)
        y = r.y() if callable(getattr(r, 'y', None)) else getattr(r, 'y', 0)
        w = r.width() if callable(getattr(r, 'width', None)) else getattr(r, 'width', 0)
        h = r.height() if callable(getattr(r, 'height', None)) else getattr(r, 'height', 0)
        return QRect(int(x), int(y), int(w), int(h))
    except Exception:
        return QRect()

