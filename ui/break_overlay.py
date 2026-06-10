# ui/break_overlay.py
import os
import random
import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt6.QtCore import Qt, QTimer, QSize, QUrl, QSettings, QRectF
from PyQt6.QtGui import QFont, QMovie, QPainter, QColor, QBrush, QLinearGradient, QPainterPath, QIcon, QPixmap, QPen
from controller import TimerController
from assets import ASSETS_DIR

try:
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False

# ── Design tokens (matching app.py) ──────────────────
BG_0      = "#0f0d0e"
BG_1      = "#171415"
ACCENT     = "#FB7185"
TEXT_HI    = "rgba(255,255,255,255)"
TEXT_MID   = "rgba(255,255,255,190)"
TEXT_LOW   = "rgba(255,255,255,120)"

# ──────────────────────────────────────────────
# BREAK OVERLAY
# ──────────────────────────────────────────────
BREAK_MESSAGES = {
    "Short Break": [
        ("short break", "step away from the screen"),
        ("breathe", "in through the nose, out through the mouth"),
        ("rest your eyes", "look at something distant"),
        ("quick reset", "shake out your hands and shoulders"),
    ],
    "Long Break": [
        ("long break", "you earned this one"),
        ("recharge", "step outside if you can"),
        ("move", "walk, stretch, hydrate"),
        ("rest", "no rush — take your time"),
    ],
}


PILATES_EXERCISES = [
    ("Neck Release", "Drop right ear to right shoulder for 10s. Repeat on left side to release desk strain."),
    ("Shoulder Roll", "Roll shoulders backward 5 times, then forward 5 times to loosen upper back muscles."),
    ("Seated Cat-Cow", "Inhale to arch back, look up. Exhale to round spine, look down. Repeat 5 times."),
    ("Seated Twist", "Inhale tall, exhale and twist torso to right. Hold for 10s. Repeat on left side."),
    ("Chest Opener", "Interlace fingers behind back, stretch arms straight, lift chest and look up."),
    ("Wrist Stretch", "Extend arm, pull fingers back gently. Repeat each hand to release keyboard strain."),
    ("Upper Trap Stretch", "Gently pull head towards shoulder with hand. Hold for 10s. Repeat on other side."),
    ("Seated Figure 4", "Cross right ankle over left knee. Lean forward gently to stretch hips. Hold for 15s."),
    ("Spine Stretch", "Sit tall, reach arms forward. Curve spine forward while exhaling to release back."),
    ("Side Bend Stretch", "Reach right arm overhead, bend torso to the left. Hold for 10s. Repeat other side.")
]


class ExerciseCard(QWidget):
    def __init__(self, title, exercises, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(280, 260) # Fixed size to prevent layout squishing and text clipping
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 26, 22, 26)
        lay.setSpacing(16)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        header = QLabel(title)
        header.setFont(QFont("DM Mono", 11, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {ACCENT}; background: transparent; text-transform: uppercase; letter-spacing: 1.5px;")
        header.setAlignment(Qt.AlignmentFlag.AlignLeft)
        lay.addWidget(header)
        
        lay.addSpacing(6)
        
        for name, desc in exercises:
            elay = QVBoxLayout()
            elay.setSpacing(3)
            
            ename = QLabel(name)
            ename.setFont(QFont("DM Sans", 11, QFont.Weight.Bold))
            ename.setStyleSheet(f"color: {TEXT_HI}; background: transparent;")
            ename.setWordWrap(True)
            elay.addWidget(ename)
            
            edesc = QLabel(desc)
            edesc.setFont(QFont("DM Sans", 9))
            edesc.setStyleSheet(f"color: {TEXT_MID}; background: transparent;")
            edesc.setWordWrap(True)
            elay.addWidget(edesc)
            
            lay.addLayout(elay)
            
            # small divider
            div = QFrame()
            div.setFrameShape(QFrame.Shape.HLine)
            div.setStyleSheet("background: rgba(255, 255, 255, 12); height: 1px; border: none;")
            lay.addWidget(div)
            
        # Remove the last divider if we added one
        if lay.count() > 0:
            item = lay.itemAt(lay.count() - 1)
            w = item.widget()
            if w:
                w.deleteLater()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 18, 18)
        
        # Semi-transparent frosted glass gradient
        bg = QLinearGradient(0, 0, 0, self.height())
        bg.setColorAt(0.0, QColor(255, 255, 255, 12))
        bg.setColorAt(1.0, QColor(255, 255, 255, 5))
        p.fillPath(path, QBrush(bg))
        
        # Subtle glass highlight border
        border_grad = QLinearGradient(0, 0, self.width(), self.height())
        border_grad.setColorAt(0.0, QColor(255, 255, 255, 30))
        border_grad.setColorAt(1.0, QColor(255, 255, 255, 5))
        p.setPen(QPen(border_grad, 1.2))
        p.drawPath(path)
        p.end()


class BreakOverlayWindow(QWidget):
    def __init__(self, controller: TimerController, is_pro: bool = False, muted: bool = False,
                 gif_path: str | None = None, sound_path: str | None = None):
        super().__init__()
        self.controller  = controller
        self._is_pro     = is_pro          
        self.muted       = muted
        self._gif_path   = gif_path
        self._sound_path = sound_path
        self._player     = None
        self._audio_out  = None
        self._pick_message()
        self._init_ui()
        self.controller.tick.connect(self._update_timer)
        self._update_timer(self.controller.remaining_secs)

        if not self.muted and self._sound_path:
            self._play_sound()

    # ── helpers ───────────────────────────────
    def _pick_message(self):
        s = QSettings("GoofyFocus", "GoofyFocus")
        if getattr(self, '_is_pro', False):
            short_raw = s.value("custom_messages_short", "[]")
            long_raw  = s.value("custom_messages_long",  "[]")
            try:
                custom_short = json.loads(short_raw) if short_raw else []
                custom_long  = json.loads(long_raw)  if long_raw  else []
            except Exception: custom_short = custom_long = []
        else:
            custom_short = custom_long = []

        pool_short = custom_short if custom_short else BREAK_MESSAGES["Short Break"]
        pool_long  = custom_long  if custom_long  else BREAK_MESSAGES["Long Break"]
        
        msgs = pool_long if self.controller.phase == "Long Break" else pool_short
        if not msgs: msgs = BREAK_MESSAGES["Short Break"]
            
        self._headline, self._subtitle = random.choice(msgs)

    def _play_sound(self):
        if not HAS_AUDIO or not self._sound_path:
            return
        try:
            self._player    = QMediaPlayer(self)
            self._audio_out = QAudioOutput(self)
            self._player.setAudioOutput(self._audio_out)
            self._audio_out.setVolume(0.7)
            self._player.setSource(QUrl.fromLocalFile(os.path.abspath(self._sound_path)))
            self._player.play()
        except Exception: pass

    def _stop_sound(self):
        if self._player:
            try: self._player.stop()
            except Exception: pass

    # ── build ─────────────────────────────────
    def _init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Main horizontal layout to hold left stretching cards, center timer/GIF, and right stretching cards
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(60, 40, 60, 40)
        main_layout.setSpacing(50)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Randomly choose 4 unique exercises from the pool of 10
        selected_exercises = random.sample(PILATES_EXERCISES, 4)
        left_exercises = selected_exercises[:2]
        right_exercises = selected_exercises[2:]

        # Left Panel (Stretch breaks)
        self.left_panel = ExerciseCard("stretch breaks", left_exercises, self)
        main_layout.addWidget(self.left_panel, 0, Qt.AlignmentFlag.AlignVCenter)

        # Center Widget (Pomodoro timer content)
        center_widget = QWidget()
        center_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        center_layout = QVBoxLayout(center_widget)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.setSpacing(20)
        center_layout.setContentsMargins(0, 0, 0, 0)

        # phase tag
        phase_tag = QLabel(self.controller.phase.upper())
        phase_tag.setFont(QFont("DM Mono", 10))
        phase_tag.setStyleSheet(f"color: {ACCENT}; font-weight: 500; background: transparent;")
        phase_tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(phase_tag)

        # headline
        hl = QLabel(self._headline)
        hl.setFont(QFont("DM Sans", 42, QFont.Weight.Light))
        hl.setStyleSheet(f"color: {TEXT_HI}; font-weight: 300; background: transparent;")
        hl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(hl)

        # GIF
        self.gif_label = QLabel()
        if self._gif_path and os.path.exists(self._gif_path):
            self.movie = QMovie(self._gif_path)
            self.movie.setScaledSize(QSize(360, 360))
            self.gif_label.setMovie(self.movie)
            self.movie.start()
            self.gif_label.setStyleSheet("""
                QLabel {
                    background: rgba(255, 255, 255, 8);
                    border: 1px solid rgba(255, 255, 255, 26);
                    border-radius: 20px;
                    padding: 10px;
                }
            """)
        else:
            self.gif_label.setText("◡")
            self.gif_label.setFont(QFont("DM Sans", 80, QFont.Weight.Light))
            self.gif_label.setStyleSheet(f"color: {TEXT_LOW}; background: transparent;")
        self.gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(self.gif_label)

        # countdown
        self.timer_label = QLabel("00:00")
        self.timer_label.setFont(QFont("DM Mono", 72, QFont.Weight.Light))
        if self.timer_label.font().exactMatch(): self.timer_label.font().setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -3)
        self.timer_label.setStyleSheet(f"color: {TEXT_HI}; font-weight: 300; background: transparent;")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(self.timer_label)

        # subtitle
        sub = QLabel(self._subtitle)
        sub.setFont(QFont("DM Sans", 14, QFont.Weight.Light))
        sub.setStyleSheet(f"color: {TEXT_MID}; font-weight: 300; background: transparent;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(sub)

        # bottom row — mute toggle + skip hint
        bottom = QHBoxLayout()
        bottom.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom.setSpacing(32)

        self.btn_mute = QPushButton(" mute" if not self.muted else " unmute")
        icon_name = "volume-x.svg" if self.muted else "volume-2.svg"
        self.btn_mute.setIcon(QIcon(os.path.join(ASSETS_DIR, "icons", icon_name)))
        self.btn_mute.setIconSize(QSize(16, 16))
        self.btn_mute.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255, 255, 255, 13);
                color: {TEXT_MID};
                border: 1px solid rgba(255, 255, 255, 31);
                border-radius: 18px;
                padding: 8px 24px;
                font-size: 12px;
                font-family: 'DM Sans';
            }}
            QPushButton:hover {{ 
                background: rgba(255, 255, 255, 26); 
                border-color: {ACCENT}; 
                color: {TEXT_HI}; 
            }}
        """)
        self.btn_mute.clicked.connect(self._toggle_mute)
        bottom.addWidget(self.btn_mute)

        self.btn_skip = QPushButton(" skip (esc)")
        self.btn_skip.setIcon(QIcon(os.path.join(ASSETS_DIR, "icons", "skip-forward.svg")))
        self.btn_skip.setIconSize(QSize(16, 16))
        self.btn_skip.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_skip.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255, 255, 255, 13);
                color: {TEXT_MID};
                border: 1px solid rgba(255, 255, 255, 31);
                border-radius: 18px;
                padding: 8px 24px;
                font-size: 12px;
                font-family: 'DM Sans';
            }}
            QPushButton:hover {{ 
                background: rgba(255, 255, 255, 26); 
                border-color: {ACCENT}; 
                color: {TEXT_HI}; 
            }}
        """)
        self.btn_skip.clicked.connect(self._skip_break)
        bottom.addWidget(self.btn_skip)

        center_layout.addLayout(bottom)
        main_layout.addWidget(center_widget, 1, Qt.AlignmentFlag.AlignCenter)

        # Right Panel (Pilates stretches)
        self.right_panel = ExerciseCard("pilates stretches", right_exercises, self)
        main_layout.addWidget(self.right_panel, 0, Qt.AlignmentFlag.AlignVCenter)

    def _toggle_mute(self):
        self.muted = not self.muted
        if self.muted:
            self._stop_sound()
            self.btn_mute.setText(" unmute")
            self.btn_mute.setIcon(QIcon(os.path.join(ASSETS_DIR, "icons", "volume-x.svg")))
        else:
            self.btn_mute.setText(" mute")
            self.btn_mute.setIcon(QIcon(os.path.join(ASSETS_DIR, "icons", "volume-2.svg")))
            self._play_sound()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Paint a rich, solid dark gradient background (no bad bg_bokeh picture)
        tint = QLinearGradient(0, 0, 0, self.height())
        if self.controller.phase == "Long Break":
            # Elegant deep green-tinted dark gradient
            tint.setColorAt(0.0, QColor(10, 18, 14))
            tint.setColorAt(1.0, QColor(5, 8, 6))
        else:
            # Elegant deep purple/violet-tinted dark gradient
            tint.setColorAt(0.0, QColor(16, 11, 20))
            tint.setColorAt(1.0, QColor(8, 5, 10))
        p.fillRect(self.rect(), QBrush(tint))
        
        # 2. Draw frosted noise texture grain
        if not hasattr(self, 'noise_pixmap'):
            self.noise_pixmap = QPixmap(128, 128)
            self.noise_pixmap.fill(Qt.GlobalColor.transparent)
            pn = QPainter(self.noise_pixmap)
            import random
            for x in range(128):
                for y in range(128):
                    val = random.randint(0, 255)
                    pn.setPen(QColor(255, 255, 255, int(val * 0.03))) # Very low opacity noise grain
                    pn.drawPoint(x, y)
            pn.end()
            
        p.drawTiledPixmap(self.rect(), self.noise_pixmap)
        p.end()

    def _update_timer(self, secs: int):
        try:
            if not self.isVisible(): return
            m, s = divmod(secs, 60)
            self.timer_label.setText(f"{m:02d}:{s:02d}")
        except Exception: pass

    def _skip_break(self):
        if getattr(self, '_skipped', False):
            return
        self._skipped = True
        self._stop_sound()
        try: self.controller.tick.disconnect(self._update_timer)
        except Exception: pass
        self.close()
        QTimer.singleShot(100, self.controller.skip)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._skip_break()

    def closeEvent(self, event):
        self._stop_sound()
        try: self.controller.tick.disconnect(self._update_timer)
        except Exception: pass
        super().closeEvent(event)
        if not getattr(self, '_skipped', False):
            self._skipped = True
            if self.controller.phase != "Work":
                QTimer.singleShot(100, self.controller.skip)

