# ui/widgets.py
import math
import os
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QSpinBox, QSizePolicy, QPushButton, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QRectF, QSize
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QConicalGradient, QRadialGradient, QFont, QPainterPath, QLinearGradient, QIcon
from controller import TimerController
from assets import ASSETS_DIR

# ──────────────────────────────────────────────
# PHASE COLOURS
# ──────────────────────────────────────────────
PHASE_COLORS = {
    "Work":        ("#FB7185", "#A78BFA"),
    "Short Break": ("#A78BFA", "#818CF8"),
    "Long Break":  ("#A7F3D0", "#34D399"),
}

# ── Design tokens (matching app.py) ──────────────────
ACCENT     = "#FB7185"
ACCENT_2   = "#A78BFA"
TEXT_HI    = "rgba(255,255,255,255)"
TEXT_MID   = "rgba(255,255,255,190)"
TEXT_LOW   = "rgba(255,255,255,120)"
ACCENT_BDR = "rgba(251, 113, 133, 120)"

# ──────────────────────────────────────────────
# CIRCULAR TIMER WIDGET
# ──────────────────────────────────────────────
class CircularTimer(QWidget):
    def __init__(self, controller: TimerController, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setMinimumSize(300, 300)
        self.setMaximumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._phase     = "Work"
        self._progress  = 0.0

        # Create Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # Top stretch to center contents vertically inside the circle
        layout.addStretch(1)

        # Time label
        self.lbl_time = QLabel("25:00")
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_time.setFont(QFont("DM Sans", 44, QFont.Weight.Light))
        self.lbl_time.setStyleSheet("""
            color: #ffffff;
            background: transparent;
        """)
        layout.addWidget(self.lbl_time)

        # Phase label
        self.lbl_phase = QLabel("FOCUS SESSION")
        self.lbl_phase.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_phase.setStyleSheet("""
            color: rgba(255, 255, 255, 200);
            font-family: 'DM Sans', sans-serif;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1px;
            background: transparent;
            margin-top: 1px;
        """)
        layout.addWidget(self.lbl_phase)

        # Sub label
        self.lbl_sub = QLabel("WORK MODE")
        self.lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_sub.setStyleSheet("""
            color: #FB7185;
            font-family: 'DM Mono', monospace;
            font-size: 9px;
            font-weight: 500;
            background: transparent;
            margin-top: 1px;
        """)
        layout.addWidget(self.lbl_sub)

        layout.addSpacing(12)

        # Controls Grid Layout
        controls_grid = QGridLayout()
        controls_grid.setContentsMargins(20, 0, 20, 0)
        controls_grid.setVerticalSpacing(4)
        controls_grid.setHorizontalSpacing(16)
        controls_grid.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 1. Skip control
        self.btn_skip = QPushButton(self)
        self.btn_skip.setFixedSize(34, 34)
        self.btn_skip.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_skip.setIcon(QIcon(os.path.join(ASSETS_DIR, "icons", "skip-forward.svg")))
        self.btn_skip.setIconSize(QSize(18, 18))
        self.btn_skip.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 12);
                border-radius: 17px;
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 6);
            }
        """)
        self.lbl_skip = QLabel("SKIP", self)
        self.lbl_skip.setStyleSheet("""
            color: rgba(255, 255, 255, 180);
            font-family: 'DM Sans', sans-serif;
            font-size: 9px;
            font-weight: 600;
            background: transparent;
        """)
        self.lbl_skip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        controls_grid.addWidget(self.btn_skip, 0, 0, Qt.AlignmentFlag.AlignCenter)
        controls_grid.addWidget(self.lbl_skip, 1, 0, Qt.AlignmentFlag.AlignCenter)

        # 2. Play/Pause control (Large center circle)
        self.btn_start = QPushButton(self)
        self.btn_start.setFixedSize(50, 50)
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.setIcon(QIcon(os.path.join(ASSETS_DIR, "icons", "play.svg")))
        self.btn_start.setIconSize(QSize(20, 20))
        self.btn_start.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #FB7185, stop:1 #FDA4AF);
                border: 1px solid rgba(255, 255, 255, 51);
                border-radius: 25px;
            }}
            QPushButton:hover {{
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #ff8da1, stop:1 #fecdd3);
            }}
        """)
        # Add drop shadow glow behind Play button
        shadow_start = QGraphicsDropShadowEffect(self.btn_start)
        shadow_start.setBlurRadius(25)
        shadow_start.setColor(QColor(251, 113, 133, 210))
        shadow_start.setOffset(0, 0)
        self.btn_start.setGraphicsEffect(shadow_start)

        self.btn_pause = QPushButton(self)
        self.btn_pause.setFixedSize(50, 50)
        self.btn_pause.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pause.setIcon(QIcon(os.path.join(ASSETS_DIR, "icons", "pause.svg")))
        self.btn_pause.setIconSize(QSize(20, 20))
        self.btn_pause.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #FB7185, stop:1 #FDA4AF);
                border: 1px solid rgba(255, 255, 255, 51);
                border-radius: 25px;
            }}
            QPushButton:hover {{
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #ff8da1, stop:1 #fecdd3);
            }}
        """)
        self.btn_pause.hide()
        # Add drop shadow glow behind Pause button
        shadow_pause = QGraphicsDropShadowEffect(self.btn_pause)
        shadow_pause.setBlurRadius(25)
        shadow_pause.setColor(QColor(251, 113, 133, 210))
        shadow_pause.setOffset(0, 0)
        self.btn_pause.setGraphicsEffect(shadow_pause)

        self.lbl_play_pause = QLabel("START", self)
        self.lbl_play_pause.setStyleSheet("""
            color: rgba(255, 255, 255, 180);
            font-family: 'DM Sans', sans-serif;
            font-size: 9px;
            font-weight: 600;
            background: transparent;
        """)
        self.lbl_play_pause.setAlignment(Qt.AlignmentFlag.AlignCenter)

        controls_grid.addWidget(self.btn_start, 0, 1, Qt.AlignmentFlag.AlignCenter)
        controls_grid.addWidget(self.btn_pause, 0, 1, Qt.AlignmentFlag.AlignCenter)
        controls_grid.addWidget(self.lbl_play_pause, 1, 1, Qt.AlignmentFlag.AlignCenter)

        # 3. Reset control
        self.btn_reset = QPushButton(self)
        self.btn_reset.setFixedSize(34, 34)
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setIcon(QIcon(os.path.join(ASSETS_DIR, "icons", "rotate-ccw.svg")))
        self.btn_reset.setIconSize(QSize(18, 18))
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 12);
                border-radius: 17px;
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 6);
            }
        """)
        self.lbl_reset = QLabel("RESET", self)
        self.lbl_reset.setStyleSheet("""
            color: rgba(255, 255, 255, 180);
            font-family: 'DM Sans', sans-serif;
            font-size: 9px;
            font-weight: 600;
            background: transparent;
        """)
        self.lbl_reset.setAlignment(Qt.AlignmentFlag.AlignCenter)
        controls_grid.addWidget(self.btn_reset, 0, 2, Qt.AlignmentFlag.AlignCenter)
        controls_grid.addWidget(self.lbl_reset, 1, 2, Qt.AlignmentFlag.AlignCenter)

        layout.addLayout(controls_grid)
        
        # Bottom stretch to center contents vertically inside the circle
        layout.addStretch(1)

        controller.tick.connect(self._on_tick)
        controller.phase_changed.connect(self._on_phase)

    def _on_tick(self, secs: int):
        m, s = divmod(secs, 60)
        self.lbl_time.setText(f"{m:02d}:{s:02d}")
        self._progress  = self.controller.progress()
        self.update()

    def _on_phase(self, phase: str):
        self._phase    = phase
        self._progress = 0.0
        
        # Update text labels
        phase_str = "FOCUS SESSION" if phase == "Work" else "BREAK SESSION"
        sub_str = "WORK MODE" if phase == "Work" else ("LONG REST" if phase == "Long Break" else "SHORT REST")
        
        self.lbl_phase.setText(phase_str)
        self.lbl_sub.setText(sub_str)
        
        # Update sub label color
        c1, c2 = PHASE_COLORS.get(phase, ("#FB7185", "#A78BFA"))
        self.lbl_sub.setStyleSheet(f"""
            color: {c1};
            font-family: 'DM Mono', monospace;
            font-size: 9px;
            font-weight: 500;
            background: transparent;
            margin-top: 1px;
        """)
        
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

        c1, c2 = PHASE_COLORS.get(self._phase, ("#FB7185", "#A78BFA"))
        col1, col2 = QColor(c1), QColor(c2)

        # 1. Subtle radial dark vignette behind text to increase contrast and depth
        # This replaces the muddy solid-white disk, creating a sleek glass integration
        radial = QRadialGradient(cx, cy, rect.width() / 2)
        radial.setColorAt(0.0, QColor(0, 0, 0, 35))   # Soft dark center for high text readability
        radial.setColorAt(0.85, QColor(0, 0, 0, 12))  # Very smooth fading
        radial.setColorAt(1.0, QColor(0, 0, 0, 0))    # Blends into the card
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(radial))
        p.drawEllipse(rect)

        # 2. Draw frosted glass noise grain texture inside the ring area (if available)
        if hasattr(self.window(), 'noise_pixmap') and self.window().noise_pixmap:
            p.save()
            cp = QPainterPath()
            cp.addEllipse(rect)
            p.setClipPath(cp)
            p.drawTiledPixmap(self.rect(), self.window().noise_pixmap)
            p.restore()

        # 3. Track - Super thin, clean outline (2px thick, very elegant and glassmorphic)
        p.setPen(QPen(QColor(255, 255, 255, 25), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(rect)

        # Helper for color interpolation
        def interpolate_color(color_a, color_b, factor):
            r = int(color_a.red() + (color_b.red() - color_a.red()) * factor)
            g = int(color_a.green() + (color_b.green() - color_a.green()) * factor)
            b = int(color_a.blue() + (color_b.blue() - color_a.blue()) * factor)
            a = int(color_a.alpha() + (color_b.alpha() - color_a.alpha()) * factor)
            return QColor(r, g, b, a)

        # Helper to get exact color along conical gradient stops
        def get_conical_color(color_a, color_b, factor):
            # Stops matching the conical gradient stops:
            # 0.0: color_b, 0.25: color_a, 0.5: color_a, 0.75: color_b, 1.0: color_b
            if factor <= 0.25:
                f = factor / 0.25
                return interpolate_color(color_b, color_a, f)
            elif factor <= 0.50:
                return color_a
            elif factor <= 0.75:
                f = (factor - 0.50) / 0.25
                return interpolate_color(color_a, color_b, f)
            else:
                return color_b

        # 4. Progress arc representing remaining time (countdown style: full at start)
        fraction = 1.0 - self._progress
        if fraction > 0.001:
            span_deg = fraction * 360
            span_val = int(span_deg * 16)

            glow_caps = Qt.PenCapStyle.RoundCap
            
            # Helper to generate conical gradient for glow with specific alpha
            def make_glow_gradient(alpha):
                g = QConicalGradient(rect.center(), 90)
                g.setColorAt(0.0, QColor(col2.red(), col2.green(), col2.blue(), alpha))
                g.setColorAt(0.25, QColor(col1.red(), col1.green(), col1.blue(), alpha))
                g.setColorAt(0.5, QColor(col1.red(), col1.green(), col1.blue(), alpha))
                g.setColorAt(0.75, QColor(col2.red(), col2.green(), col2.blue(), alpha))
                g.setColorAt(1.0, QColor(col2.red(), col2.green(), col2.blue(), alpha))
                return g

            # Soft ambient halo (subtle glow, low opacity)
            glow_pen = QPen(QBrush(make_glow_gradient(45)), size * 0.04) # thin, soft halo
            glow_pen.setCapStyle(glow_caps)
            p.setPen(glow_pen)
            p.drawArc(rect, 90 * 16, span_val)

            # Main sharp progress arc (fully opaque gradient, 3px thick)
            conic = QConicalGradient(rect.center(), 90)
            conic.setColorAt(0.0, col2)
            conic.setColorAt(0.25, col1)
            conic.setColorAt(0.5, col1)
            conic.setColorAt(0.75, col2)
            conic.setColorAt(1.0, col2)

            arc_pen = QPen(QBrush(conic), 3.0)
            arc_pen.setCapStyle(glow_caps)
            p.setPen(arc_pen)
            p.drawArc(rect, 90 * 16, span_val)

            # 5. Glowing Tip dot (placed precisely at the end of the arc)
            tip_col = get_conical_color(col1, col2, fraction)
            angle_rad = math.radians(90 + span_deg)
            r_mid     = rect.width() / 2
            dot_x     = cx + r_mid * math.cos(angle_rad)
            dot_y     = cy - r_mid * math.sin(angle_rad)
            dot_r     = 3.0
            
            # Outer glow for the tip dot
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(tip_col.red(), tip_col.green(), tip_col.blue(), 120)))
            p.drawEllipse(QRectF(dot_x - dot_r * 2.0, dot_y - dot_r * 2.0, dot_r * 4.0, dot_r * 4.0))
            
            # Crisp white center dot
            p.setBrush(QBrush(QColor("#ffffff")))
            p.drawEllipse(QRectF(dot_x - dot_r * 0.8, dot_y - dot_r * 0.8, dot_r * 1.6, dot_r * 1.6))

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
                background: rgba(255, 255, 255, 13);
                border: 1px solid rgba(255, 255, 255, 31);
                border-radius: 8px;
                padding: 3px 6px;
                color: rgba(255, 255, 255, 240);
                font-size: 12px;
                font-family: 'DM Mono';
                min-width: 32px;
                min-height: 22px;
            }}
            QSpinBox:hover, QSpinBox:focus {{
                border-color: #FB7185;
                background: rgba(255, 255, 255, 20);
            }}
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