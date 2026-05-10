import sys
import ctypes
import platform
import os
import json

if platform.system() == "Windows":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ScreenBreak")

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QSystemTrayIcon, QMenu, QSizePolicy,
    QComboBox, QFrame
)
from PyQt6.QtCore import Qt, QTimer, QRectF, QSettings
from PyQt6.QtGui import (
    QFont, QPainter, QColor, QPen, QBrush, QLinearGradient,
    QPainterPath, QIcon, QAction, QPixmap
)

from controller import TimerController
from assets import LocalAssetPicker, ASSETS_DIR
from auth import perform_login, load_cached_user, logout_user

from ui.widgets import CircularTimer, Card, DurationSpin
from ui.break_overlay import BreakOverlayWindow
from ui.feedback import FeedbackWindow

from pro.gate import UpgradeDialog
from pro.stats import StatsWindow
from pro.messages import CustomMessagesWindow
from pro.media import GifPackManager, SoundManagerWindow


# ── Design tokens ──────────────────────────────────────────────────────────────
ACCENT      = "rgba(192,132,252,{a})"
TEXT_HI     = "rgba(255,255,255,245)" 
TEXT_MID    = "rgba(255,255,255,180)" 
TEXT_DIM    = "rgba(255,255,255,110)"


# ── Helpers ────────────────────────────────────────────────────────────────────
def _lbl(text, size=11, color=TEXT_MID, spacing=""):
    l = QLabel(text)
    ls = f"letter-spacing:{spacing};" if spacing else ""
    l.setStyleSheet(
        f"color:{color};font-size:{size}px;font-family:'Segoe UI';{ls}background:transparent;"
    )
    return l


def _pill_btn(text, primary=False):
    b = QPushButton(text)
    if primary:
        s = (
            "QPushButton{background:rgba(192,132,252,0.20);color:rgba(216,180,254,230);"
            "border:1px solid rgba(192,132,252,0.36);border-radius:14px;"
            "padding:8px 22px;font-size:11px;font-family:'Segoe UI';}"
            "QPushButton:hover{background:rgba(192,132,252,0.32);color:rgba(233,213,255,255);"
            "border-color:rgba(192,132,252,0.55);}"
            "QPushButton:pressed{background:rgba(192,132,252,0.24);}"
            "QPushButton:disabled{opacity:0.35;}"
        )
    else:
        s = (
            "QPushButton{background:rgba(255,255,255,6);color:rgba(255,255,255,165);"
            "border:1px solid rgba(255,255,255,13);border-radius:14px;"
            "padding:8px 18px;font-size:11px;font-family:'Segoe UI';}"
            "QPushButton:hover{background:rgba(255,255,255,11);color:rgba(255,255,255,220);"
            "border-color:rgba(255,255,255,22);}"
            "QPushButton:pressed{background:rgba(255,255,255,7);}"
            "QPushButton:disabled{opacity:0.35;}"
        )
    b.setStyleSheet(s)
    return b

def _action_btn(text):
    b = QPushButton(text)
    b.setFixedHeight(26)
    b.setStyleSheet("""
        QPushButton {
            background: transparent;
            color: rgba(192,132,252,180);
            border: 1px solid rgba(192,132,252,60);
            border-radius: 8px;
            padding: 2px 12px;
            font-size: 10px;
            font-family: 'Segoe UI';
        }
        QPushButton:hover {
            background: rgba(192,132,252,15);
            color: rgba(216,180,254,230);
            border-color: rgba(192,132,252,120);
        }
    """)
    return b

def _icon_btn(symbol, tooltip=""):
    b = QPushButton(symbol)
    b.setFixedSize(28, 28)
    b.setToolTip(tooltip)
    b.setStyleSheet(
        "QPushButton{background:transparent;color:rgba(255,255,255,48);"
        "border:none;border-radius:14px;font-size:13px;}"
        "QPushButton:hover{background:rgba(255,255,255,10);color:rgba(255,255,255,130);}"
        "QPushButton:pressed{background:rgba(255,255,255,6);}"
    )
    return b


def _divider():
    d = QFrame()
    d.setFrameShape(QFrame.Shape.HLine)
    d.setStyleSheet("background:rgba(255,255,255,9);border:none;")
    d.setFixedHeight(1)
    return d


# ── Glass card widget ──────────────────────────────────────────────────────────
class GlassCard(QWidget):
    def __init__(self, radius=14, border_color=None, parent=None):
        super().__init__(parent)
        self._radius = radius
        self._border_color = border_color or QColor(192, 132, 252, 45)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), self._radius, self._radius)
        p.fillPath(path, QBrush(QColor(40, 28, 65, 55))) 
        p.setPen(QPen(self._border_color, 1))
        p.drawPath(path)
        p.end()


# ── Custom session-dot widget ──────────────────────────────────────────────────
class SessionDots(QWidget):
    def __init__(self, total=4, parent=None):
        super().__init__(parent)
        self._total     = total
        self._completed = 0
        # Bumped height from 12 to 16 to accommodate the new glow radius
        self.setFixedHeight(16)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_state(self, completed: int, total: int):
        self._completed = completed
        self._total     = total
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r   = 5.5       # was 3.5
        gap = 14        # was 11
        n   = self._total
        tw  = n * r * 2 + (n - 1) * gap
        x0  = (self.width() - tw) / 2
        cy  = self.height() / 2

        for i in range(n):
            cx = x0 + i * (r * 2 + gap) + r
            if i < self._completed:
                # Glow halo
                p.setBrush(QBrush(QColor(192, 132, 252, 50)))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QRectF(cx - r - 3, cy - r - 3, (r+3)*2, (r+3)*2))
                # Solid dot
                p.setBrush(QBrush(QColor(192, 132, 252, 230)))
                p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
            else:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(QColor(255, 255, 255, 80), 1.5))   # was alpha 60
                p.drawEllipse(QRectF(cx - r + 0.5, cy - r + 0.5, r*2-1, r*2-1))
        p.end()


# ── Section header ─────────────────────────────────────────────────────────────
class SectionHeader(QWidget):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 6, 0, 2)
        lay.setSpacing(10)
        
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "color: #a78bda;"
            "font-size: 10px;"
            "font-family: 'Segoe UI';"
            "letter-spacing: 3px;"
            "font-weight: 700;"
            "background: transparent;"
        )
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background: rgba(167,139,218,50); border: none;")
        line.setFixedHeight(1)
        
        lay.addWidget(lbl)
        lay.addWidget(line, 1)


# ── Setting row helper ─────────────────────────────────────────────────────────
def _setting_row(label, sublabel, right_widget):
    w = QWidget()
    w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    lay = QHBoxLayout(w)
    lay.setContentsMargins(2, 5, 2, 5)
    lay.setSpacing(10)
    
    col = QVBoxLayout()
    col.setSpacing(1)
    
    main_lbl = QLabel(label)
    main_lbl.setStyleSheet(
        "color: #d4c8ed;"
        "font-size: 12px;"
        "font-family: 'Segoe UI';"
        "font-weight: 500;"
        "background: transparent;"
    )
    main_lbl.setMinimumWidth(140)
    
    if sublabel:
        sub = QLabel(sublabel)
        sub.setStyleSheet(
            "color: #7b6a9a;"
            "font-size: 10px;"
            "font-family: 'Segoe UI';"
            "background: transparent;"
        )
        col.addWidget(main_lbl)
        col.addWidget(sub)
    else:
        col.addWidget(main_lbl)
        
    lay.addLayout(col)
    lay.addStretch()
    lay.addWidget(right_widget)
    return w


# ── Main Window ────────────────────────────────────────────────────────────────
class MainWindow(QWidget):
    def __init__(self, controller: TimerController):
        super().__init__()
        self.controller       = controller
        self.overlay          = None
        self._overlay_closing = False
        self._drag_pos        = None
        self._muted           = False
        self._user_info       = {}
        self._is_pro          = False
        self._picker          = LocalAssetPicker()

        self.setWindowTitle("ScreenBreak")
        self.setFixedSize(520, 820)  
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowMinimizeButtonHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._build_ui()
        self._setup_tray()
        self._connect_signals()
        self._load_settings()
        self.controller.reset()
        self._picker.start(is_pro=self._is_pro)

    # ─────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 16)
        root.setSpacing(0)

        root.addLayout(self._build_titlebar())
        root.addSpacing(10)
        root.addLayout(self._build_session_row())
        root.addSpacing(2)

        # Circular timer
        self.circ = CircularTimer(self.controller)
        self.circ.setFixedSize(216, 216)
        tr = QHBoxLayout()
        tr.addWidget(self.circ, alignment=Qt.AlignmentFlag.AlignCenter)
        root.addLayout(tr)

        # Status label
        sl = QHBoxLayout()
        sl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label = QLabel("ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(
            "color:rgba(192,132,252,160);font-size:10px;font-family:'Segoe UI';"
            "background:transparent;letter-spacing:1px;"
        )
        sl.addWidget(self.status_label)
        root.addLayout(sl)
        root.addSpacing(12)

        root.addWidget(self._build_controls())
        root.addSpacing(16) 
        root.addWidget(self._build_settings())
        root.addStretch()

    # ── Title bar ─────────────────────────────────────────────────────────────
    def _build_titlebar(self):
        lay = QHBoxLayout()
        lay.setContentsMargins(2, 0, 2, 0)
        lay.setSpacing(6)

        logo = _lbl("screenbreak", size=12, color="rgba(255,255,255,165)", spacing="1.5px")

        self.pro_badge = QLabel("✦ pro")
        self.pro_badge.setStyleSheet(
            "color:rgba(192,132,252,210);font-size:8px;font-family:'Segoe UI';"
            "background:rgba(192,132,252,0.14);border:1px solid rgba(192,132,252,0.26);"
            "border-radius:6px;padding:1px 6px;"
        )
        self.pro_badge.hide()

        lay.addWidget(logo)
        lay.addWidget(self.pro_badge)
        lay.addStretch()

        self.btn_login = QPushButton("sign in")
        self.btn_login.setFixedHeight(26)
        self.btn_login.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,7);color:rgba(255,255,255,155);"
            "border:1px solid rgba(255,255,255,15);border-radius:13px;"
            "padding:0 14px;font-size:10px;font-family:'Segoe UI';}"
            "QPushButton:hover{background:rgba(255,255,255,13);color:rgba(255,255,255,220);}"
        )
        self.btn_login.clicked.connect(self._do_google_login)
        lay.addWidget(self.btn_login)

        self.btn_stats       = _icon_btn("◈", "Focus stats")
        self.btn_global_mute = _icon_btn("♪", "Toggle sound")
        self.btn_stats.clicked.connect(self._show_stats)
        self.btn_global_mute.clicked.connect(self._toggle_global_mute)
        lay.addWidget(self.btn_stats)
        lay.addWidget(self.btn_global_mute)

        lay.addSpacing(2)
        for sym, handler, danger in [("−", self._minimize_to_tray, False),
                                      ("×", self._quit_app, True)]:
            col = "rgba(252,100,100,160)" if danger else "rgba(255,255,255,110)"
            b   = QPushButton(sym)
            b.setFixedSize(24, 24)
            b.setStyleSheet(
                f"QPushButton{{background:rgba(255,255,255,7);color:{col};"
                f"border:1px solid rgba(255,255,255,13);border-radius:12px;font-size:14px;}}"
                f"QPushButton:hover{{background:rgba(255,255,255,15);color:white;}}"
            )
            b.clicked.connect(handler)
            lay.addWidget(b)
        return lay

    # ── Session row ───────────────────────────────────────────────────────────
    def _build_session_row(self):
        outer = QVBoxLayout()
        outer.setSpacing(5)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._session_dots = SessionDots(total=4)
        self._session_dots.setFixedWidth(180)

        self.session_label = _lbl("session 1 of 4", size=8, color=TEXT_DIM, spacing="0.8px")
        self.session_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        dr = QHBoxLayout(); dr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dr.addWidget(self._session_dots)
        lr = QHBoxLayout(); lr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lr.addWidget(self.session_label)

        outer.addLayout(dr)
        outer.addLayout(lr)
        return outer

    # ── Controls ──────────────────────────────────────────────────────────────
    def _build_controls(self):
        # Apply the warmer border color: rgba(192, 132, 252, 0.20)
        card = GlassCard(radius=16, border_color=QColor(192, 132, 252, 51))
        lay  = QHBoxLayout(card)
        lay.setContentsMargins(16, 11, 16, 11)
        lay.setSpacing(8)

        self.btn_start = _pill_btn("▶  start", primary=True)
        self.btn_pause = _pill_btn("⏸  pause")
        self.btn_skip  = _pill_btn("skip")
        self.btn_reset = _pill_btn("reset")
        self.btn_start.setMinimumWidth(90)
        self.btn_pause.hide()

        for b in (self.btn_start, self.btn_pause, self.btn_skip, self.btn_reset):
            lay.addWidget(b)
        return card

    # ── Settings ──────────────────────────────────────────────────────────────
    def _build_settings(self):
        card = GlassCard(radius=16)
        lay  = QVBoxLayout(card)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(2)

        # ── Durations ──
        lay.addWidget(SectionHeader("TIMER"))
        self._dur_spins = {}
        timer_items = [
            ("Work",        "work",  25*60, "focus duration"),
            ("Short break", "short",  5*60, "between sessions"),
            ("Long break",  "long",  15*60, "end of cycle"),
        ]
        
        for i, (label, key, default_s, hint) in enumerate(timer_items):
            ds = DurationSpin(default_s)
            self._dur_spins[key] = ds
            lay.addWidget(_setting_row(label, hint, ds))
            if i < len(timer_items) - 1:
                lay.addWidget(_divider())

        lay.addSpacing(4)

        # ── Behaviour ──
        lay.addWidget(SectionHeader("BEHAVIOUR"))

        self._flow_combo = QComboBox()
        self._flow_combo.addItems(["Auto  (4 short → long)", "Always short", "Always long"])
        self._flow_combo.setStyleSheet("""
            QComboBox {
                background: rgba(255,255,255,8);
                border: 1px solid rgba(192,132,252,80);
                border-radius: 8px; padding: 3px 10px;
                color: #d4c8ed; font-size: 11px; font-family: 'Segoe UI';
                min-width: 160px;
            }
            QComboBox::drop-down { border: none; width: 18px; }
            QComboBox QAbstractItemView {
                background: #1c1230; border: 1px solid rgba(192,132,252,60);
                color: #d4c8ed; selection-background-color: rgba(192,132,252,35);
                font-size: 11px;
            }
        """)
        lay.addWidget(_setting_row("Break flow", "session cycle pattern", self._flow_combo))
        lay.addWidget(_divider())

        # Sessions per cycle
        spc_w = QWidget()
        spc_w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        sl = QHBoxLayout(spc_w)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(6)
        self._spc_spin = QSpinBox()
        self._spc_spin.setRange(1, 12)
        self._spc_spin.setValue(4)
        self._spc_spin.setEnabled(False)
        self._spc_spin.setStyleSheet("""
            QSpinBox {
                background: rgba(255,255,255,8);
                border: 1px solid rgba(192,132,252,90);
                border-radius: 6px; padding: 2px 4px;
                color: #e8dff5; font-size: 12px; font-weight: 500;
                min-width: 32px; max-width: 38px;
            }
            QSpinBox:focus { border-color: rgba(192,132,252,200); }
            QSpinBox::up-button, QSpinBox::down-button { width: 0px; border: none; }
        """)
        self._spc_lock = QLabel("🔒")
        self._spc_lock.setStyleSheet("color:rgba(192,132,252,200);font-size:12px;background:transparent; padding-left: 2px;")
        sl.addWidget(self._spc_spin)
        sl.addWidget(self._spc_lock)
        lay.addWidget(_setting_row("Sessions per cycle", "work blocks before long break", spc_w))

        lay.addSpacing(4)

        # ── Personalise ──
        lay.addWidget(SectionHeader("PERSONALISE"))

        self.btn_custom_msgs   = _action_btn("edit")
        self.btn_custom_gifs   = _action_btn("manage")
        self.btn_custom_sounds = _action_btn("manage")

        self.btn_custom_msgs.clicked.connect(self._show_custom_msgs)
        self.btn_custom_gifs.clicked.connect(self._show_gif_manager)
        self.btn_custom_sounds.clicked.connect(self._show_sound_manager)

        lay.addWidget(_setting_row("Break messages", "text shown on rest screen", self.btn_custom_msgs))
        lay.addWidget(_divider())
        lay.addWidget(_setting_row("GIF packs", "animated break visuals", self.btn_custom_gifs))
        lay.addWidget(_divider())
        lay.addWidget(_setting_row("Sounds", "ambient break audio", self.btn_custom_sounds))
        
        lay.addSpacing(8)

        # ── Apply ──
        self.btn_apply = QPushButton("save settings")
        self.btn_apply.setFixedHeight(36)
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background: rgba(192,132,252,0.18);
                color: rgba(216,180,254,210);
                border: 1px solid rgba(192,132,252,0.28);
                border-radius: 10px;
                font-size: 11px; font-family: 'Segoe UI';
            }
            QPushButton:hover { background: rgba(192,132,252,0.28); color: rgba(233,213,255,240); }
        """)
        lay.addWidget(self.btn_apply)
        
        return card

    # ── Tray ──────────────────────────────────────────────────────────────────
    def _setup_tray(self):
        tray_icon = QIcon(os.path.join(ASSETS_DIR, "icon.png"))
        if tray_icon.isNull():
            px = QPixmap(32, 32)
            px.fill(Qt.GlobalColor.transparent)
            p = QPainter(px)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            grad = QLinearGradient(0, 0, 32, 32)
            grad.setColorAt(0, QColor("#c084fc"))
            grad.setColorAt(1, QColor("#f472b6"))
            p.setBrush(QBrush(grad))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(2, 2, 28, 28)
            p.end()
            tray_icon = QIcon(px)

        self.tray = QSystemTrayIcon(tray_icon, self)
        menu = QMenu()
        menu.setStyleSheet(
            "QMenu{background:#0f0d1a;color:rgba(255,255,255,170);"
            "border:1px solid rgba(255,255,255,14);border-radius:9px;padding:4px;}"
            "QMenu::item{padding:7px 20px;border-radius:5px;font-size:11px;}"
            "QMenu::item:selected{background:rgba(192,132,252,0.22);}"
        )
        act_show         = QAction("Show window", self);   act_show.triggered.connect(self._show_from_tray)
        act_stats        = QAction("Focus stats", self);   act_stats.triggered.connect(self._show_stats)
        self._act_toggle = QAction("Pause timer", self);   self._act_toggle.triggered.connect(self._tray_toggle_timer)
        act_feedback     = QAction("Send feedback", self); act_feedback.triggered.connect(self._open_feedback)
        act_quit         = QAction("Quit", self);          act_quit.triggered.connect(self._quit_app)

        menu.addActions([act_show, act_stats])
        menu.addSeparator()
        menu.addAction(self._act_toggle)
        menu.addSeparator()
        menu.addActions([act_feedback, act_quit])
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    # ── Signals ───────────────────────────────────────────────────────────────
    def _connect_signals(self):
        self.btn_start.clicked.connect(self._ui_start)
        self.btn_pause.clicked.connect(self._ui_pause)
        self.btn_skip.clicked.connect(self._ui_skip)
        self.btn_reset.clicked.connect(self._ui_reset)
        self.btn_apply.clicked.connect(self._apply_settings)
        self.controller.phase_changed.connect(self._on_phase_changed)
        self.controller.session_done.connect(self._on_session_done)
        self.controller.session_recorded.connect(self._save_session)

    def _save_session(self, duration_secs: int, phase: str):
        sub = self._user_info.get("id")
        if not sub:
            return
        try:
            from auth import get_supabase_client
            sb = get_supabase_client()
            if sb:
                sb.table("sessions").insert({
                    "google_sub": sub, "duration_secs": duration_secs, "phase": phase,
                }).execute()
        except Exception as e:
            print(f"[session] save failed: {e}")

    # ── Controls ──────────────────────────────────────────────────────────────
    def _set_status(self, text, color=None):
        c = color or "rgba(192,132,252,160)"
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"color:{c};font-size:10px;font-family:'Segoe UI';"
            "background:transparent;letter-spacing:1px;"
        )

    def _ui_start(self):
        self.btn_start.hide(); self.btn_pause.show()
        self._act_toggle.setText("Pause timer")
        self.controller.start()
        self._set_status("focusing", "rgba(192,132,252,140)")

    def _ui_pause(self):
        self.btn_pause.hide(); self.btn_start.show()
        self._act_toggle.setText("Resume timer")
        self.controller.pause()
        self._set_status("paused", TEXT_MID)

    def _ui_skip(self):
        self.btn_skip.setEnabled(False)
        self.controller.skip()
        QTimer.singleShot(500, lambda: self.btn_skip.setEnabled(True))

    def _ui_reset(self):
        self.btn_pause.hide(); self.btn_start.show()
        self._act_toggle.setText("Pause timer")
        self.controller.reset()
        spc = self.controller.sessions_per_cycle
        self._session_dots.set_state(0, spc)
        self.session_label.setText(f"session 1 of {spc}")
        self.session_label.setStyleSheet(
            f"color:{TEXT_DIM};font-size:8px;font-family:'Segoe UI';"
            "background:transparent;letter-spacing:0.8px;"
        )
        self._set_status("ready")

    # ── Overlay ───────────────────────────────────────────────────────────────
    def _close_overlay_safely(self):
        if self.overlay is None or self._overlay_closing:
            return
        self._overlay_closing = True
        try:
            try: self.overlay.controller.tick.disconnect(self.overlay._update_timer)
            except Exception: pass
            _ov = self.overlay; self.overlay = None; _ov.close()
        except Exception as e:
            print(f"[ERROR] Overlay close failed: {e}")
        finally:
            self._overlay_closing = False

    def _toggle_global_mute(self):
        self._muted = not self._muted
        self.btn_global_mute.setText("♬" if self._muted else "♪")
        if self.overlay and self._muted:
            self.overlay._stop_sound()
        QSettings("ScreenBreak", "ScreenBreak").setValue("muted", self._muted)

    def _tray_toggle_timer(self):
        self._ui_pause() if self.controller.is_running else self._ui_start()

    # ── Settings persistence ──────────────────────────────────────────────────
    def _apply_settings(self):
        self._close_overlay_safely()
        try:
            flow = {0: "auto", 1: "always_short", 2: "always_long"}.get(
                self._flow_combo.currentIndex(), "auto"
            )
            self.controller.update_settings(
                self._dur_spins["work"].value_secs(),
                self._dur_spins["short"].value_secs(),
                self._dur_spins["long"].value_secs(), flow,
            )
            s = QSettings("ScreenBreak", "ScreenBreak")
            if self._is_pro:
                self.controller.sessions_per_cycle = self._spc_spin.value()
                s.setValue("sessions_per_cycle", self._spc_spin.value())
            self.btn_pause.hide(); self.btn_start.show()
            self._act_toggle.setText("Pause timer")
            self._set_status("saved ✓", "rgba(52,211,153,150)")
            s.setValue("work_secs",  self._dur_spins["work"].value_secs())
            s.setValue("short_secs", self._dur_spins["short"].value_secs())
            s.setValue("long_secs",  self._dur_spins["long"].value_secs())
            s.setValue("break_flow", self._flow_combo.currentIndex())
            s.setValue("muted",      self._muted)
        except Exception:
            self._set_status("error saving", "rgba(248,113,113,160)")

    def _load_settings(self):
        s = QSettings("ScreenBreak", "ScreenBreak")
        self._dur_spins["work"]._min_spin.setValue(int(s.value("work_secs",  25*60)) // 60)
        self._dur_spins["work"]._sec_spin.setValue(int(s.value("work_secs",  25*60)) % 60)
        self._dur_spins["short"]._min_spin.setValue(int(s.value("short_secs", 5*60)) // 60)
        self._dur_spins["short"]._sec_spin.setValue(int(s.value("short_secs", 5*60)) % 60)
        self._dur_spins["long"]._min_spin.setValue(int(s.value("long_secs",  15*60)) // 60)
        self._dur_spins["long"]._sec_spin.setValue(int(s.value("long_secs",  15*60)) % 60)
        self._flow_combo.setCurrentIndex(int(s.value("break_flow", 0)))
        spc = int(s.value("sessions_per_cycle", 4))
        self._spc_spin.setValue(spc)
        if self._is_pro:
            self.controller.sessions_per_cycle = spc
        if s.value("muted", False) == "true":
            self._muted = True; self.btn_global_mute.setText("♬")
        self._load_saved_login()
        self._apply_settings()

    # ── Phase / session ───────────────────────────────────────────────────────
    def _on_phase_changed(self, phase: str):
        if self._overlay_closing:
            return
        if phase == "Work":
            self._close_overlay_safely()
            self._set_status("focusing", "rgba(192,132,252,130)")
            self._picker.start(is_pro=self._is_pro)
        else:
            self._close_overlay_safely()
            try:
                gif, sound = self._picker.pop()
                self.overlay = BreakOverlayWindow(
                    self.controller, is_pro=self._is_pro,
                    muted=self._muted, gif_path=gif, sound_path=sound,
                )
                self.overlay.showFullScreen()
                self.tray.showMessage(
                    "break time", f"{phase} — step away",
                    QSystemTrayIcon.MessageIcon.Information, 3000,
                )
            except Exception as e:
                print(f"[ERROR] Failed to create break overlay: {e}")

    def _on_session_done(self, count: int):
        spc = self.controller.sessions_per_cycle
        pos = count % spc or spc
        self._session_dots.set_state(pos, spc)
        self.session_label.setText(f"session {pos} of {spc}")
        self.session_label.setStyleSheet(
            "color:rgba(192,132,252,130);font-size:8px;font-family:'Segoe UI';"
            "background:transparent;letter-spacing:0.8px;"
        )

    # ── Pro / Auth ────────────────────────────────────────────────────────────
    def _refresh_pro_badge(self):
        if getattr(self, '_is_pro', False):
            self.pro_badge.show()
            self._spc_spin.setEnabled(True)
            self._spc_lock.hide()
        else:
            self.pro_badge.hide()
            self._spc_spin.setEnabled(False)
            self._spc_lock.show()

    def _show_stats(self):
        if not self._user_info:
            self._set_status("log in to view stats", TEXT_MID); return
        self._stats_win = StatsWindow(user_info=self._user_info, is_pro=self._is_pro)
        self._stats_win.show()

    def _show_custom_msgs(self):
        if not self._is_pro: return self._show_upgrade_dialog()
        self._msg_win = CustomMessagesWindow(is_pro=self._is_pro)
        self._msg_win.show()

    def _show_gif_manager(self):
        if not self._is_pro: return self._show_upgrade_dialog()
        self._gif_win = GifPackManager(is_pro=self._is_pro)
        self._gif_win.show()

    def _show_sound_manager(self):
        if not self._is_pro: return self._show_upgrade_dialog()
        self._sound_win = SoundManagerWindow(is_pro=self._is_pro)
        self._sound_win.show()

    def _show_upgrade_dialog(self):
        if not hasattr(self, '_upgrade_win') or not self._upgrade_win.isVisible():
            self._upgrade_win = UpgradeDialog(main_window=self)
            self._upgrade_win.show()

    def _open_feedback(self):
        self._feedback_win = FeedbackWindow(user_email=self._user_info.get("email", ""))
        self._feedback_win.show()

    def _load_saved_login(self):
        info = load_cached_user()
        if info:
            self._user_info = info
            self._is_pro    = info.get("is_pro", False)
            self._refresh_pro_badge()
            self.btn_login.setText(f"hi, {info.get('given_name', 'user').lower()}")
            self.btn_login.clicked.disconnect()
            self.btn_login.clicked.connect(self._show_logout_menu)

    def _do_google_login(self):
        self.btn_login.setText("signing in…")
        QApplication.processEvents()
        try:
            info            = perform_login()
            self._user_info = info
            self._is_pro    = info.get("is_pro", False)
            self._refresh_pro_badge()
            self.btn_login.setText(f"hi, {info.get('given_name', 'user').lower()}")
            self.btn_login.clicked.disconnect()
            self.btn_login.clicked.connect(self._show_logout_menu)
        except Exception as e:
            self.btn_login.setText("sign in")
            print(f"Auth error: {e}")

    def _show_logout_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu{background:#16131f;color:rgba(255,255,255,180);"
            "border:1px solid rgba(255,255,255,15);border-radius:8px;padding:4px;font-size:11px;}"
            "QMenu::item{padding:6px 18px;border-radius:5px;}"
            "QMenu::item:selected{background:rgba(192,132,252,0.22);}"
        )
        email = self._user_info.get("email", "")
        if email:
            lbl = QAction(email, self); lbl.setEnabled(False)
            menu.addAction(lbl); menu.addSeparator()
        act_up  = QAction("upgrade to pro ✦", self); act_up.triggered.connect(self._show_upgrade_dialog)
        act_fb  = QAction("send feedback", self);     act_fb.triggered.connect(self._open_feedback)
        act_out = QAction("log out", self);           act_out.triggered.connect(self._do_logout)
        menu.addActions([act_up, act_fb]); menu.addSeparator(); menu.addAction(act_out)
        menu.exec(self.btn_login.mapToGlobal(self.btn_login.rect().bottomLeft()))

    def _do_logout(self):
        logout_user()
        self._user_info = {}; self._is_pro = False
        self._refresh_pro_badge()
        self.btn_login.setText("sign in")
        self.btn_login.clicked.disconnect()
        self.btn_login.clicked.connect(self._do_google_login)

    # ── Window plumbing ───────────────────────────────────────────────────────
    def _minimize_to_tray(self):
        self.hide()
        self.tray.showMessage("ScreenBreak", "Running in tray — click to restore.",
                              QSystemTrayIcon.MessageIcon.Information, 2000)

    def _show_from_tray(self):
        self.showNormal(); self.activateWindow(); self.raise_()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e): self._drag_pos = None

    def changeEvent(self, event):
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.WindowStateChange and self.isMinimized():
            QTimer.singleShot(0, self._minimize_to_tray)
        super().changeEvent(event)

    def _quit_app(self): self.tray.hide(); QApplication.quit()
    def closeEvent(self, event): self.tray.hide(); event.accept(); QApplication.quit()

    # ── Paint ─────────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 20, 20)

        bg = QLinearGradient(0, 0, 0, self.height())
        # Richer purple-dark depth
        bg.setColorAt(0.0, QColor(22, 14, 38, 255))
        bg.setColorAt(1.0, QColor(10,  6, 20, 255))
        p.fillPath(path, QBrush(bg))

        # Accent top-glow line
        glow = QLinearGradient(0, 0, self.width(), 0)
        glow.setColorAt(0.0, QColor(192, 132, 252,  0))
        # Increased glow opacity to 55
        glow.setColorAt(0.5, QColor(192, 132, 252, 55))
        glow.setColorAt(1.0, QColor(244, 114, 182,  0))
        gp = QPainterPath()
        gp.addRoundedRect(QRectF(0, 0, self.width(), 2), 1, 1)
        p.fillPath(gp, QBrush(glow))

        # Border
        # Increased border opacity to 28
        p.setPen(QPen(QColor(255, 255, 255, 28), 1))
        p.drawPath(path)
        p.end()


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    icon_path = os.path.join(ASSETS_DIR, "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    controller = TimerController()
    window     = MainWindow(controller)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()