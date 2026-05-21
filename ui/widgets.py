# ui/widgets.py
import math
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSpinBox, QSizePolicy
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QConicalGradient, QFont, QPainterPath, QLinearGradient
from controller import TimerController

# ──────────────────────────────────────────────
# PHASE COLOURS
# ──────────────────────────────────────────────
PHASE_COLORS = {
    "Work":        ("#00f0ff", "#ff00ff"),
    "Short Break": ("#4ade9a", "#22c55e"),
    "Long Break":  ("#60b8ff", "#3b82f6"),
}

# ── Design tokens (matching app.py) ──────────────────
ACCENT     = "#849d8a"
TEXT_HI    = "rgba(255,255,255,235)"
TEXT_MID   = "rgba(255,255,255,140)"
TEXT_LOW   = "rgba(255,255,255,76)"
ACCENT_BDR = "rgba(132,157,138,64)"

# ──────────────────────────────────────────────
# CIRCULAR TIMER WIDGET
# ──────────────────────────────────────────────
class CircularTimer(QWidget):
    def __init__(self, controller: TimerController, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setMinimumSize(110, 110)
        self.setMaximumSize(110, 110)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._phase     = "Work"
        self._progress  = 0.0
        self._time_text = "25:00"

        controller.tick.connect(self._on_tick)
        controller.phase_changed.connect(self._on_phase)

    def _on_tick(self, secs: int):
        m, s = divmod(secs, 60)
        self._time_text = f"{m:02d}:{s:02d}"
        self._progress  = self.controller.progress()
        self.update()

    def _on_phase(self, phase: str):
        self._phase    = phase
        self._progress = 0.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h   = self.width(), self.height()
        size   = min(w, h)
        margin = size * 0.08
        rect   = QRectF(
            margin + (w - size) / 2,
            margin + (h - size) / 2,
            size - 2 * margin,
            size - 2 * margin
        )
        cx, cy = w / 2, h / 2

        c1, c2 = PHASE_COLORS.get(self._phase, ("#849d8a", "#a1bfa8"))
        col1, col2 = QColor(c1), QColor(c2)

        # 1. Track - very faint
        track_pen = QPen(QColor(255, 255, 255, 12), size * 0.035)
        p.setPen(track_pen)
        p.drawEllipse(rect)

        # 2. Progress arc
        if self._progress > 0.001:
            span_deg = self._progress * 360
            span_val = -int(span_deg * 16)

            # Soft glow
            glow_pen = QPen(
                QColor(col1.red(), col1.green(), col1.blue(), 20),
                size * 0.075
            )
            glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(glow_pen)
            p.drawArc(rect, 90 * 16, span_val)

            # Gradient Arc
            conic = QConicalGradient(rect.center(), 90)
            conic.setColorAt(0.0,            col1)
            conic.setColorAt(self._progress, col2)
            conic.setColorAt(1.0,            col1)

            arc_pen = QPen(QBrush(conic), size * 0.035)
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(arc_pen)
            p.drawArc(rect, 90 * 16, span_val)

            # Tip dot
            angle_rad = math.radians(90 - span_deg)
            r_mid     = rect.width() / 2
            dot_x     = cx + r_mid * math.cos(angle_rad)
            dot_y     = cy - r_mid * math.sin(angle_rad)
            dot_r     = size * 0.024
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(col2))
            p.drawEllipse(QRectF(dot_x - dot_r, dot_y - dot_r, dot_r * 2, dot_r * 2))

        # 3. Time text
        font = QFont("DM Sans", int(size * 0.24), QFont.Weight.Normal)
        p.setFont(font)
        p.setPen(QColor(255, 255, 255, 235))
        p.drawText(QRectF(0, cy - size * 0.18, w, size * 0.30),
                Qt.AlignmentFlag.AlignCenter, self._time_text)

        # 4. Phase label
        lbl_font = QFont("DM Mono", int(size * 0.055), QFont.Weight.Medium)
        p.setFont(lbl_font)
        p.setPen(col1)
        p.drawText(QRectF(0, cy + size * 0.14, w, size * 0.10),
                Qt.AlignmentFlag.AlignCenter, self._phase.title())

        p.end()


# ──────────────────────────────────────────────
# DURATION SPIN (mocking redesign spin)
# ──────────────────────────────────────────────
class DurationSpin(QWidget):
    def __init__(self, default_secs: int, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        spin_style = f"""
            QSpinBox {{
                background: rgba(255,255,255,18);
                border: none;
                border-radius: 5px;
                padding: 1px 4px;
                color: rgba(255,255,255,230);
                font-size: 11px;
                font-family: 'DM Mono';
                min-width: 32px;
                min-height: 20px;
            }}
            QSpinBox:focus {{ background: rgba(255,255,255,24); }}
            QSpinBox::up-button, QSpinBox::down-button {{ width: 0px; border: none; }}
        """
        unit_style = (
            "color: rgba(255,255,255,140);"
            "font-size: 9px;"
            "font-family: 'DM Sans';"
            "background: transparent;"
        )

        default_m = default_secs // 60
        default_s = default_secs  % 60

        self._min_spin = QSpinBox()
        self._min_spin.setRange(0, 180)
        self._min_spin.setValue(default_m)
        self._min_spin.setStyleSheet(spin_style)

        lbl_m = QLabel("min")
        lbl_m.setStyleSheet(unit_style)

        self._sec_spin = QSpinBox()
        self._sec_spin.setRange(0, 59)
        self._sec_spin.setValue(default_s)
        self._sec_spin.setStyleSheet(spin_style)

        lbl_s = QLabel("sec")
        lbl_s.setStyleSheet(unit_style)

        layout.addWidget(self._min_spin)
        layout.addWidget(lbl_m)
        layout.addWidget(self._sec_spin)
        layout.addWidget(lbl_s)
        self.setFixedWidth(152)

    def value_secs(self) -> int:
        return self._min_spin.value() * 60 + self._sec_spin.value()