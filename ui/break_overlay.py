# ui/break_overlay.py
import os
import random
import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QTimer, QSize, QUrl, QSettings
from PyQt6.QtGui import QFont, QMovie, QPainter, QColor, QBrush, QLinearGradient, QPainterPath, QIcon, QPixmap
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

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        # phase tag
        phase_tag = QLabel(self.controller.phase.upper())
        phase_tag.setFont(QFont("DM Mono", 10))
        phase_tag.setStyleSheet(f"color: {ACCENT}; font-weight: 500; background: transparent;")
        phase_tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(phase_tag)

        # headline
        hl = QLabel(self._headline)
        hl.setFont(QFont("DM Sans", 42, QFont.Weight.Light))
        hl.setStyleSheet(f"color: {TEXT_HI}; font-weight: 300; background: transparent;")
        hl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hl)

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
        layout.addWidget(self.gif_label)

        # countdown
        self.timer_label = QLabel("00:00")
        self.timer_label.setFont(QFont("DM Mono", 72, QFont.Weight.Light))
        if self.timer_label.font().exactMatch(): self.timer_label.font().setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -3)
        self.timer_label.setStyleSheet(f"color: {TEXT_HI}; font-weight: 300; background: transparent;")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.timer_label)

        # subtitle
        sub = QLabel(self._subtitle)
        sub.setFont(QFont("DM Sans", 14, QFont.Weight.Light))
        sub.setStyleSheet(f"color: {TEXT_MID}; font-weight: 300; background: transparent;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)

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

        hint = QLabel("esc · skip")
        hint.setFont(QFont("DM Mono", 11))
        hint.setStyleSheet(f"color: {TEXT_LOW}; background: transparent;")
        bottom.addWidget(hint)

        layout.addLayout(bottom)

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

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._stop_sound()
            try: self.controller.tick.disconnect(self._update_timer)
            except Exception: pass
            self.close()
            QTimer.singleShot(100, self.controller.skip)

    def closeEvent(self, event):
        self._stop_sound()
        try: self.controller.tick.disconnect(self._update_timer)
        except Exception: pass
        super().closeEvent(event)

