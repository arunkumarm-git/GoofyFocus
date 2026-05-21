import sys
import ctypes
import platform
import os
import json
import datetime

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

from ui.widgets import CircularTimer, DurationSpin
from ui.break_overlay import BreakOverlayWindow
from ui.feedback import FeedbackWindow

from pro.gate import UpgradeDialog
from pro.stats import StatsWindow
from pro.messages import CustomMessagesWindow
from pro.media import GifPackManager, SoundManagerWindow


# ── Design tokens ──────────────────────────────────────────────────────────────
BG_0      = "#161514"
BG_1      = "#1c1b19"
BG_2      = "#23211f"
BG_3      = "#2a2826"
SURFACE   = "rgba(255,255,255,10)"
SURFACE_H = "rgba(255,255,255,18)"
BORDER    = "rgba(255,255,255,20)"
BORDER_H  = "rgba(255,255,255,36)"

ACCENT     = "#849d8a"
ACCENT_2   = "#a1bfa8"
ACCENT_DIM = "rgba(132,157,138,38)"
ACCENT_BDR = "rgba(132,157,138,64)"

GREEN      = "#4ade9a"
BLUE       = "#60b8ff"

TEXT_HI    = "rgba(255,255,255,235)"
TEXT_MID   = "rgba(255,255,255,140)"
TEXT_LOW   = "rgba(255,255,255,76)"

# ── Helpers ────────────────────────────────────────────────────────────────────
def _lbl(text, size=11, color=TEXT_MID, bold=False, mono=False, low_contrast=False):
    l = QLabel(text)
    fw  = "font-weight:600;" if bold else ""
    # If low_contrast is True, we use a slightly brighter version for better legibility (accessibility tip)
    final_color = "rgba(255,255,255,160)" if low_contrast else color
    family = "'DM Mono', monospace" if mono else "'DM Sans', 'Segoe UI', sans-serif"
    l.setStyleSheet(
        f"color:{final_color};font-size:{size}px;font-family:{family};{fw}background:transparent;"
    )
    return l


def _divider(subtle=True):
    d = QFrame()
    d.setFrameShape(QFrame.Shape.HLine)
    opacity = 10 if subtle else 18
    d.setStyleSheet(f"background:rgba(255,255,255,{opacity});border:none;")
    d.setFixedHeight(1)
    return d


def _icon_btn(symbol, tooltip=""):
    """Small square icon button — no border, low-contrast ghost."""
    b = QPushButton(symbol)
    b.setFixedSize(28, 28)
    b.setToolTip(tooltip)
    b.setStyleSheet(
        f"QPushButton {{ background-color: transparent; color: {TEXT_LOW}; "
        "border: none; border-radius: 8px; font-size: 14px; font-family: 'Segoe UI'; } "
        f"QPushButton:hover {{ background-color: {SURFACE_H}; color: {TEXT_HI}; }} "
        f"QPushButton:pressed {{ background-color: {SURFACE}; }} "
    )
    return b


def _action_btn(text):
    """Clean, borderless text link-button for settings rows."""
    b = QPushButton(text)
    b.setFixedHeight(22)
    b.setStyleSheet(
        f"QPushButton{{background:transparent;color:{ACCENT};"
        "border:none;border-radius:6px;padding:2px 8px;"
        f"font-size:11px;font-family:'DM Sans';font-weight:500;}}"
        f"QPushButton:hover{{background:{ACCENT_DIM};color:white;}}"
    )
    return b


def _ctrl_btn(text, primary=False):
    """Control-row button — flat, rounded rectangle."""
    b = QPushButton(text)
    b.setFixedHeight(28)
    if primary:
        b.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 rgba(132,157,138,76), stop:1 rgba(161,191,168,46)); "
            f"color: white; border: 1px solid {ACCENT_BDR}; border-radius: 8px; "
            f"padding: 0 12px; font-size: 11px; font-family: 'DM Sans'; font-weight: 500; }} "
            f"QPushButton:hover {{ background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 rgba(132,157,138,102), stop:1 rgba(161,191,168,64)); "
            f"border-color: rgba(132,157,138,128); }} "
            f"QPushButton:pressed {{ background: rgba(132,157,138,51); }} "
            f"QPushButton:disabled {{ color: {TEXT_LOW}; }}"
        )
    else:
        b.setStyleSheet(
            f"QPushButton{{background:{SURFACE};color:{TEXT_MID};"
            f"border:1px solid {BORDER};border-radius:8px;"
            f"padding:0 8px;font-size:10px;font-family:'DM Sans';}}"
            f"QPushButton:hover{{background:{SURFACE_H};color:{TEXT_HI};"
            f"border-color:{BORDER_H};}}"
            f"QPushButton:pressed{{background:{SURFACE};}}"
            f"QPushButton:disabled{{color:{TEXT_LOW};}}"
        )
    return b


def _setting_row(label, sublabel, right_widget):
    w = QWidget()
    w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    lay = QHBoxLayout(w)
    lay.setContentsMargins(16, 4, 16, 4)
    lay.setSpacing(12)

    col = QVBoxLayout()
    col.setSpacing(0)
    col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

    main_lbl = QLabel(label)
    main_lbl.setMinimumWidth(100)
    main_lbl.setWordWrap(False)
    main_lbl.setStyleSheet(
        f"color:{TEXT_HI};font-size:11px;font-family:'DM Sans';"
        "font-weight:500;background:transparent;"
    )
    col.addWidget(main_lbl)

    if sublabel:
        sub = _lbl(sublabel, size=9, low_contrast=True)
        sub.setMinimumWidth(100)
        col.addWidget(sub)

    lay.addLayout(col, 1)
    lay.addWidget(right_widget, 0, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
    return w


# ── Section header ─────────────────────────────────────────────────────────────
class SectionHeader(QWidget):
    """Title Case label + subtle fade rule (Tip 1: Less is more)."""
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 10, 16, 4)
        lay.setSpacing(10)

        lbl = QLabel(text.title())
        lbl.setStyleSheet(
            f"color:{ACCENT};font-size:11px;font-family:'DM Sans';"
            "font-weight:600;background:transparent;"
        )
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background:qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {ACCENT_BDR}, stop:1 transparent);border:none;")
        line.setFixedHeight(1)

        lay.addWidget(lbl)
        lay.addWidget(line, 1)


# ── Settings card ──────────────────────────────────────────────────────────────
class SettingsCard(QWidget):
    """Rounded rectangle card with a slightly lighter fill than the window bg."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 18, 18)
        p.fillPath(path, QBrush(QColor(BG_2)))
        p.setPen(QPen(QColor(255, 255, 255, 12), 1))
        p.drawPath(path)
        p.end()


# ── Custom session-dot widget ──────────────────────────────────────────────────
class SessionDots(QWidget):
    def __init__(self, total=4, parent=None):
        super().__init__(parent)
        self._total     = total
        self._completed = 0
        self.setFixedHeight(14)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_state(self, completed: int, total: int):
        self._completed = completed
        self._total     = total
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r   = 4
        gap = 10
        n   = self._total
        tw  = n * r * 2 + (n - 1) * gap
        x0  = (self.width() - tw) / 2
        cy  = self.height() / 2

        for i in range(n):
            cx = x0 + i * (r * 2 + gap) + r
            if i < self._completed:
                # Soft glow halo
                p.setBrush(QBrush(QColor(132, 157, 138, 50)))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QRectF(cx - r - 4, cy - r - 4, (r + 4) * 2, (r + 4) * 2))
                # Filled dot
                p.setBrush(QBrush(QColor(ACCENT)))
                p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
            elif i == self._completed:
                # Current dot - outline accent
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(QColor(ACCENT), 1.5))
                p.drawEllipse(QRectF(cx - r + 0.5, cy - r + 0.5, r * 2 - 1, r * 2 - 1))
            else:
                # Empty dot - outline dim
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(QColor(255, 255, 255, 60), 1.5))
                p.drawEllipse(QRectF(cx - r + 0.5, cy - r + 0.5, r * 2 - 1, r * 2 - 1))
        p.end()


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
        
        # Responsive size logic
        screen = QApplication.primaryScreen().availableGeometry()
        sw, sh = screen.width(), screen.height()
        target_w = 380
        if sw > 2000: target_w = 400
        target_h = 780
        if sh < 850: target_h = min(sh - 60, 720)
        self.setFixedSize(target_w, target_h)

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

    # ── Build UI ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(0)

        # 1. Title bar
        root.addLayout(self._build_titlebar())
        root.addSpacing(2)

        # 2. Session progress
        root.addLayout(self._build_session_row())
        root.addSpacing(2)

        # 3. Timer
        self.circ = CircularTimer(self.controller)
        tr = QHBoxLayout()
        tr.addWidget(self.circ, alignment=Qt.AlignmentFlag.AlignCenter)
        root.addLayout(tr)

        # 4. Status pill
        sl = QHBoxLayout()
        sl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_container = QWidget()
        self.status_container.setStyleSheet(f"background: transparent;")
        sl_inner = QHBoxLayout(self.status_container)
        sl_inner.setContentsMargins(10, 0, 10, 0)
        sl_inner.setSpacing(4)
        
        self.status_dot = QWidget()
        self.status_dot.setFixedSize(5, 5)
        self.status_dot.setStyleSheet(f"background: {ACCENT}; border-radius: 2px;")
        
        self.status_label = _lbl("ready", size=10, color=ACCENT, mono=True)
        
        sl_inner.addWidget(self.status_dot)
        sl_inner.addWidget(self.status_label)
        sl.addWidget(self.status_container)
        root.addLayout(sl)
        root.addSpacing(4)

        # 5. Controls
        root.addLayout(self._build_controls())
        root.addSpacing(6)

        # 6. Settings
        root.addWidget(self._build_settings())
        root.addStretch()

    # ── Title bar ──────────────────────────────────────────────────────────────
    def _build_titlebar(self):
        lay = QHBoxLayout()
        lay.setContentsMargins(14, 6, 14, 2)
        lay.setSpacing(6)

        # Logo
        logo = _lbl("screenbreak", size=13, color=TEXT_HI, bold=True)
        lay.addWidget(logo)

        # Pro badge
        self.pro_badge = QLabel("✦ pro")
        self.pro_badge.setStyleSheet(
            f"color:{ACCENT};font-size:9px;font-family:'DM Sans';"
            f"background:{ACCENT_DIM};border:1px solid {ACCENT_BDR};"
            "border-radius:10px;padding:1px 6px;font-weight:600;"
        )
        self.pro_badge.hide()
        lay.addWidget(self.pro_badge)

        lay.addStretch()

        # ── USER AUTH CHIP (Moved to right) ──
        self.btn_login = QPushButton("sign in")
        self.btn_login.setFixedHeight(20)
        self.btn_login.setStyleSheet(
            f"QPushButton{{background:rgba(255,255,255,15);color:{TEXT_MID};"
            "border:none;border-radius:10px;font-size:10px;font-family:'DM Sans';font-weight:500;"
            "padding: 0 10px;}" 
            f"QPushButton:hover{{background:rgba(255,255,255,25);color:white;}}"
        )
        self.btn_login.clicked.connect(self._do_google_login)
        lay.addWidget(self.btn_login)

        self.streak_lbl = _lbl("", size=10, color=TEXT_LOW, mono=True)
        lay.addWidget(self.streak_lbl)

        # Actions
        self.btn_stats       = _icon_btn("◈", "Focus stats")
        self.btn_global_mute = _icon_btn("🔊", "Toggle sound")
        self.btn_stats.clicked.connect(self._show_stats)
        self.btn_global_mute.clicked.connect(self._toggle_global_mute)
        lay.addWidget(self.btn_stats)
        lay.addWidget(self.btn_global_mute)

        # Vertical separator
        sep = QFrame()
        sep.setFixedSize(1, 12)
        sep.setStyleSheet(f"background:rgba(255,255,255,20);border:none;")
        lay.addWidget(sep)

        # Window controls
        btn_min = QPushButton("−")
        btn_min.setFixedSize(18, 18)
        btn_min.setStyleSheet(
            f"QPushButton{{background:{SURFACE_H};color:{TEXT_LOW};"
            "border:none;border-radius:9px;font-size:10px;}"
            f"QPushButton:hover{{background:{BORDER_H};color:{TEXT_MID};}}"
        )
        btn_min.clicked.connect(self._minimize_to_tray)

        btn_close = QPushButton("×")
        btn_close.setFixedSize(18, 18)
        btn_close.setStyleSheet(
            "QPushButton{background:rgba(255,80,80,38);color:rgba(255,100,100,178);"
            "border:none;border-radius:9px;font-size:10px;}"
            "QPushButton:hover{background:rgba(255,80,80,64);color:rgba(255,100,100,230);}"
        )
        btn_close.clicked.connect(self._quit_app)

        lay.addWidget(btn_min)
        lay.addWidget(btn_close)
        return lay

    # (Removed _build_auth_strip)

    # ── Session progress row ───────────────────────────────────────────────────
    def _build_session_row(self):
        outer = QVBoxLayout()
        outer.setSpacing(6)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._session_dots = SessionDots(total=4)
        self._session_dots.setFixedWidth(160)

        self.session_label = _lbl("session 3 of 4", size=10, color=TEXT_LOW, mono=True)
        self.session_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        dr = QHBoxLayout(); dr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dr.addWidget(self._session_dots)
        lr = QHBoxLayout(); lr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lr.addWidget(self.session_label)

        outer.addLayout(dr)
        outer.addLayout(lr)
        return outer

    # ── Controls ───────────────────────────────────────────────────────────────
    def _build_controls(self):
        """
        Flat inline row — no GlassCard wrapper.
        Primary CTA takes all spare space; secondary buttons are fixed width.
        """
        lay = QHBoxLayout()
        lay.setContentsMargins(2, 0, 2, 0)
        lay.setSpacing(10)

        self.btn_start = _ctrl_btn("▶  start", primary=True)
        self.btn_pause = _ctrl_btn("⏸︎  pause", primary=True)
        self.btn_skip  = _ctrl_btn("skip")
        self.btn_reset = _ctrl_btn("↺")

        # Primary CTA fills available space; secondary buttons are compact
        self.btn_start.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_pause.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_skip.setFixedWidth(60)
        self.btn_reset.setFixedWidth(44)

        self.btn_pause.hide()

        for b in (self.btn_start, self.btn_pause, self.btn_skip, self.btn_reset):
            lay.addWidget(b)

        return lay

    # ── Settings card ──────────────────────────────────────────────────────────
    def _build_settings(self):
        card = SettingsCard()
        card.setMinimumHeight(520) # Prevent squishing in ScrollArea
        lay  = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        # ── TIMER ──────────────────────────────────────────────────────────────
        lay.addWidget(SectionHeader("TIMER"))

        self._dur_spins = {}
        timer_items = [
            ("Work",        "work",  25 * 60, "focus duration"),
            ("Short break", "short",  5 * 60, "between sessions"),
            ("Long break",  "long",  15 * 60, "end of cycle"),
        ]
        for i, (label, key, default_s, hint) in enumerate(timer_items):
            ds = DurationSpin(default_s)
            self._dur_spins[key] = ds
            lay.addWidget(_setting_row(label, hint, ds))
            # divider after every row including the last (section boundary)
            lay.addWidget(_divider())

        # ── BEHAVIOUR ──────────────────────────────────────────────────────────
        lay.addWidget(SectionHeader("BEHAVIOUR"))

        self._flow_combo = QComboBox()
        self._flow_combo.addItems(["Auto (4 short → long)", "Always short", "Always long"])
        self._flow_combo.setFixedWidth(160)
        self._flow_combo.setStyleSheet(
            f"QComboBox{{background:rgba(255,255,255,12);border:1px solid {ACCENT_BDR};"
            f"border-radius:6px;padding:4px 10px;color:rgba(220,200,255,198);font-size:11px;"
            "font-family:'DM Sans';font-weight:400;}"
            "QComboBox::drop-down{border:none;width:14px;}"
            "QComboBox QAbstractItemView{background:#1a1b26;border:1px solid rgba(132,157,138,51);"
            "color:rgba(220,200,255,198);selection-background-color:rgba(132,157,138,25);font-size:11px;}"
        )
        lay.addWidget(_setting_row("Break flow", "session cycle pattern", self._flow_combo))
        lay.addWidget(_divider())

        # Sessions per cycle (pro-gated)
        spc_w = QWidget()
        spc_w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        sl = QHBoxLayout(spc_w)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(5)

        self._spc_spin = QSpinBox()
        self._spc_spin.setRange(1, 12)
        self._spc_spin.setValue(4)
        self._spc_spin.setEnabled(False)
        self._spc_spin.setFixedWidth(44)
        self._spc_spin.setStyleSheet(
            f"QSpinBox{{background:rgba(255,255,255,12);border:1px solid {ACCENT_BDR};"
            "border-radius:6px;padding:3px 6px;color:rgba(220,200,255,198);font-size:11px;font-weight:400;}"
            f"QSpinBox:focus{{border-color:rgba(185,142,245,150);}}"
            "QSpinBox::up-button,QSpinBox::down-button{width:0px;border:none;}"
        )
        self._spc_lock = QLabel("🔒")
        self._spc_lock.setStyleSheet(
            f"color:{ACCENT};font-size:11px;background:transparent;"
        )
        sl.addWidget(self._spc_spin)
        sl.addWidget(self._spc_lock)
        lay.addWidget(_setting_row("Sessions per cycle", "work blocks before long break", spc_w))
        lay.addWidget(_divider())

        # ── PERSONALISE ────────────────────────────────────────────────────────
        lay.addWidget(SectionHeader("PERSONALISE"))

        self.btn_custom_msgs   = _action_btn("edit")
        self.btn_custom_gifs   = _action_btn("manage")
        self.btn_custom_sounds = _action_btn("manage")

        self.btn_custom_msgs.clicked.connect(self._show_custom_msgs)
        self.btn_custom_gifs.clicked.connect(self._show_gif_manager)
        self.btn_custom_sounds.clicked.connect(self._show_sound_manager)

        lay.addWidget(_setting_row("Break messages", "text shown on rest screen", self.btn_custom_msgs))
        lay.addWidget(_divider())
        lay.addWidget(_setting_row("GIF packs",      "animated break visuals",    self.btn_custom_gifs))
        lay.addWidget(_divider())
        lay.addWidget(_setting_row("Sounds",          "ambient break audio",       self.btn_custom_sounds))

        # ── Save button ────────────────────────────────────────────────────────
        lay.addSpacing(14)
        self.btn_apply = QPushButton("save settings")
        self.btn_apply.setFixedHeight(38)
        self.btn_apply.setStyleSheet(
            f"QPushButton{{background:{ACCENT_DIM};color:rgba(220,195,255,219);"
            f"border:1px solid {ACCENT_BDR};border-radius:10px;"
            "font-size:11px;font-family:'DM Sans';font-weight:500;}}"
            "QPushButton:hover{background:rgba(185,142,245,56);border-color:rgba(185,142,245,102);color:rgba(235,220,255,255);}"
        )
        save_row = QHBoxLayout()
        save_row.setContentsMargins(16, 0, 16, 14)
        save_row.addWidget(self.btn_apply)
        lay.addLayout(save_row)

        return card

    # ── Tray ───────────────────────────────────────────────────────────────────
    def _setup_tray(self):
        tray_icon = QIcon(os.path.join(ASSETS_DIR, "icon.png"))
        if tray_icon.isNull():
            px = QPixmap(32, 32)
            px.fill(Qt.GlobalColor.transparent)
            p = QPainter(px)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            grad = QLinearGradient(0, 0, 32, 32)
            grad.setColorAt(0, QColor("#849d8a"))
            grad.setColorAt(1, QColor("#a1bfa8"))
            p.setBrush(QBrush(grad))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(2, 2, 28, 28)
            p.end()
            tray_icon = QIcon(px)

        self.tray = QSystemTrayIcon(tray_icon, self)
        menu = QMenu()
        menu.setStyleSheet(
            f"QMenu{{background:{BG_1};color:rgba(255,255,255,170);"
            "border:1px solid rgba(255,255,255,12);border-radius:9px;padding:4px;font-size:11px;}"
            "QMenu::item{padding:7px 20px;border-radius:5px;}"
            "QMenu::item:selected{background:rgba(132,157,138,51);}"
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

    # ── Signals ────────────────────────────────────────────────────────────────
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
        sub = self._user_info.get("id", "guest")
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        payload = {
            "google_sub": sub, 
            "duration_secs": duration_secs, 
            "phase": phase,
            "completed_at": now_iso
        }
        
        # 1. Save Locally (Primary)
        from assets import USER_DATA_DIR
        local_db = os.path.join(USER_DATA_DIR, "sessions.json")
        try:
            sessions = []
            if os.path.exists(local_db):
                with open(local_db, "r") as f:
                    sessions = json.load(f)
            sessions.append(payload)
            with open(local_db, "w") as f:
                json.dump(sessions, f, indent=2)
            print(f"[session] saved locally to {local_db}")
        except Exception as e:
            print(f"[session] local save failed: {e}")

        # 2. Sync to Supabase (Background/Secondary)
        try:
            from auth import get_supabase_client
            sb = get_supabase_client()
            if sb and sub != "guest":
                sb.table("sessions").insert(payload).execute()
                print("[session] synced to Supabase")
        except Exception as e:
            print(f"[session] cloud sync failed (expected if RLS/offline): {e}")
            
        self._set_status("session saved ✓", GREEN)
        QTimer.singleShot(5000, lambda: self._set_status("ready" if not self.controller.is_running else "focusing"))

    # ── UI control methods ─────────────────────────────────────────────────────
    def _set_status(self, text, color=ACCENT):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"color:{color};font-size:10px;font-family:'DM Mono';"
            "background:transparent;font-weight:400;"
        )
        self.status_dot.setStyleSheet(f"background: {color}; border-radius: 2px;")

    def _ui_start(self):
        self.btn_start.hide(); self.btn_pause.show()
        self._act_toggle.setText("Pause timer")
        self.controller.start()
        self._set_status("focusing")

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
        self._set_status("ready")

    # ── Overlay ────────────────────────────────────────────────────────────────
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
        self.btn_global_mute.setText("🔇" if self._muted else "🔊")
        if self.overlay and self._muted:
            self.overlay._stop_sound()
        QSettings("ScreenBreak", "ScreenBreak").setValue("muted", self._muted)

    def _tray_toggle_timer(self):
        self._ui_pause() if self.controller.is_running else self._ui_start()

    # ── Settings persistence ───────────────────────────────────────────────────
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
            self._set_status("saved ✓", GREEN)
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
            self._muted = True; self.btn_global_mute.setText("🔇")
        self._load_saved_login()
        self._apply_settings()

    # ── Phase / session ────────────────────────────────────────────────────────
    def _on_phase_changed(self, phase: str):
        if self._overlay_closing:
            return
        if phase == "Work":
            self._close_overlay_safely()
            self._set_status("focusing")
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

    # ── Pro / Auth ─────────────────────────────────────────────────────────────
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
            self._set_status("log in for stats", TEXT_MID); return
            
        active_elapsed = 0
        if self.controller.phase == "Work" and self.controller.is_running:
            active_elapsed = self.controller.work_secs - self.controller.remaining_secs
            
        self._stats_win = StatsWindow(user_info=self._user_info, is_pro=self._is_pro, active_elapsed_secs=active_elapsed)
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
            self._set_login_state(info.get("given_name", "user"))

    def _do_google_login(self):
        self.btn_login.setText("signing in…")
        QApplication.processEvents()
        try:
            info            = perform_login()
            self._user_info = info
            self._is_pro    = info.get("is_pro", False)
            self._refresh_pro_badge()
            self._set_login_state(info.get("given_name", "user"))
        except Exception as e:
            self.btn_login.setText("sign in")
            self._set_status("auth failed", "rgba(248,113,113,160)")
            print(f"Auth error: {e}")

    def _set_login_state(self, given_name: str):
        """Switch btn_login to show the user's name as a chip."""
        self.btn_login.setText(f"hi, {given_name.lower()}")
        self.btn_login.setStyleSheet(
            f"QPushButton{{background:{ACCENT_DIM};color:{ACCENT};"
            f"border:1px solid {ACCENT_BDR};border-radius:10px;"
            "padding:0 12px;font-size:10px;font-family:'DM Sans';font-weight:500;}}"
            f"QPushButton:hover{{background:rgba(132,157,138,51);color:white;}}"
        )
        try:
            self.btn_login.clicked.disconnect()
        except Exception:
            pass
        self.btn_login.clicked.connect(self._show_logout_menu)

    def _show_logout_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{BG_1};color:{TEXT_HI};"
            f"border:1px solid {BORDER};border-radius:9px;padding:4px;font-size:11px;}}"
            f"QMenu::item{{padding:6px 18px;border-radius:5px;}}"
            "QMenu::item:selected{background:rgba(132,157,138,51);}"
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
        self.btn_login.setStyleSheet(
            f"QPushButton{{background:transparent;color:{TEXT_LOW};"
            f"border:1px solid {BORDER};border-radius:12px;"
            "padding:0 12px;font-size:11px;font-family:'DM Sans';}"
            f"QPushButton:hover{{border-color:{BORDER_H};color:{TEXT_MID};}}"
        )
        try:
            self.btn_login.clicked.disconnect()
        except Exception:
            pass
        self.btn_login.clicked.connect(self._do_google_login)

    # ── Window plumbing ────────────────────────────────────────────────────────
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

    # ── Paint ──────────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 24, 24)

        # Background gradient — dark purple-black
        bg = QLinearGradient(0, 0, 0, self.height())
        bg.setColorAt(0.0, QColor(BG_1))
        bg.setColorAt(1.0, QColor(BG_0))
        p.fillPath(path, QBrush(bg))

        # Subtle top-edge glow — accent fades in from centre, pink fades out
        glow = QLinearGradient(0, 0, self.width(), 0)
        glow.setColorAt(0.0, QColor(0, 0, 0, 0))
        glow.setColorAt(0.1, QColor(0, 0, 0, 0))
        glow.setColorAt(0.3, QColor(132, 157, 138, 128))
        glow.setColorAt(0.7, QColor(161, 191, 168, 76))
        glow.setColorAt(0.9, QColor(0, 0, 0, 0))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        
        gp = QPainterPath()
        gp.addRect(QRectF(self.width() * 0.1, 0, self.width() * 0.8, 1))
        p.fillPath(gp, QBrush(glow))

        # Window border — very subtle
        p.setPen(QPen(QColor(255, 255, 255, 20), 1))
        p.drawPath(path)
        p.end()


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setOrganizationName("ScreenBreak")
    app.setApplicationName("ScreenBreak")
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

