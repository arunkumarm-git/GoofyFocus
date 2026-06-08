import sys
import ctypes
import platform
import os
import json
import datetime
import threading

if platform.system() == "Windows":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("GoofyFocus")

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QSystemTrayIcon, QMenu, QSizePolicy,
    QComboBox, QFrame, QGraphicsDropShadowEffect, QStackedWidget,
    QScrollArea, QLineEdit, QGraphicsOpacityEffect, QAbstractButton
)
from PyQt6.QtCore import Qt, QTimer, QRectF, QSettings, QSize, QEvent, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal
from PyQt6.QtGui import (
    QFont, QPainter, QColor, QPen, QBrush, QLinearGradient,
    QPainterPath, QIcon, QAction, QPixmap
)

from controller import TimerController
from assets import LocalAssetPicker, ASSETS_DIR
from auth import perform_login, load_cached_user, logout_user, save_cached_user

from ui.widgets import CircularTimer, DurationSpin
from ui.break_overlay import BreakOverlayWindow
from ui.feedback import FeedbackWindow

from pro.gate import UpgradeDialog
from pro.stats import StatsWindow
from pro.messages import CustomMessagesWindow
from pro.media import GifPackManager, SoundManagerWindow

CURRENT_VERSION = "1.0.1"


# Helper to convert #AARRGGBB to rgba(r,g,b,a) for QSS stylesheets
def hex_to_rgba(hex_str):
    if hex_str.startswith("#") and len(hex_str) == 9:
        a = int(hex_str[1:3], 16)
        r = int(hex_str[3:5], 16)
        g = int(hex_str[5:7], 16)
        b = int(hex_str[7:9], 16)
        return f"rgba({r}, {g}, {b}, {a})"
    elif hex_str.startswith("#") and len(hex_str) == 7:
        r = int(hex_str[1:3], 16)
        g = int(hex_str[3:5], 16)
        b = int(hex_str[5:7], 16)
        return f"rgb({r}, {g}, {b})"
    return hex_str


# Helper to apply native windows drop shadow and glass blur-behind effects
def apply_blur_effect(hwnd_id):
    if platform.system() != "Windows":
        return
    import ctypes
    from ctypes import windll, byref, c_int, c_void_p, Structure, sizeof
    hwnd = c_void_p(hwnd_id)
    
    # 1. Enable native window drop shadow for frameless window
    try:
        class MARGINS(Structure):
            _fields_ = [
                ("cxLeftWidth", c_int),
                ("cxRightWidth", c_int),
                ("cyTopHeight", c_int),
                ("cyBottomHeight", c_int)
            ]
        windll.dwmapi.DwmExtendFrameIntoClientArea.argtypes = [c_void_p, ctypes.POINTER(MARGINS)]
        windll.dwmapi.DwmExtendFrameIntoClientArea.restype = c_int
        
        margins = MARGINS(1, 1, 1, 1)
        windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, byref(margins))
        print("[blur] Windows native shadow enabled")
    except Exception as e:
        print("[blur] Windows shadow extension failed:", e)

    # 2. Enable Windows 10/11 Accent Policy Acrylic/Blur-Behind
    try:
        class AccentPolicy(Structure):
            _fields_ = [
                ("AccentState", c_int),
                ("AccentFlags", c_int),
                ("GradientColor", c_int),
                ("AnimationId", c_int)
            ]
            
        class WindowCompositionAttributeData(Structure):
            _fields_ = [
                ("Attribute", c_int),
                ("Data", ctypes.c_void_p),
                ("SizeOfData", c_int)
            ]
            
        accent = AccentPolicy()
        # ACCENT_ENABLE_ACRYLICBLURBEHIND = 4 (available on Win10 1803+ and Win11)
        accent.AccentState = 4
        accent.AccentFlags = 2 # Draw borders if needed
        accent.GradientColor = 0x05151218 # Extremely translucent dark color wash (Alpha 0x05)
        accent.AnimationId = 0
        
        data = WindowCompositionAttributeData()
        data.Attribute = 19 # WCA_ACCENT_POLICY
        data.Data = ctypes.cast(byref(accent), ctypes.c_void_p)
        data.SizeOfData = sizeof(accent)
        
        windll.user32.SetWindowCompositionAttribute.argtypes = [c_void_p, ctypes.POINTER(WindowCompositionAttributeData)]
        windll.user32.SetWindowCompositionAttribute.restype = c_int
        
        res = windll.user32.SetWindowCompositionAttribute(hwnd, byref(data))
        if res == 0:
            # Fallback to standard blur behind (ACCENT_ENABLE_BLURBEHIND = 3)
            accent.AccentState = 3
            windll.user32.SetWindowCompositionAttribute(hwnd, byref(data))
            print("[blur] Windows Accent Policy BlurBehind enabled")
        else:
            print("[blur] Windows Accent Policy Acrylic enabled")
    except Exception as e:
        print("[blur] Windows Accent Policy failed:", e)

    # 3. Apply Windows 11 DWM System Backdrop Type (Acrylic)
    try:
        dwma_backdrop = 38 # DWMWA_SYSTEMBACKDROP_TYPE
        backdrop_type = c_int(2) # DWMSBT_MAINWINDOW = 2 (Mica - lighter, subtle blur)
        windll.dwmapi.DwmSetWindowAttribute.argtypes = [c_void_p, c_int, c_void_p, c_int]
        windll.dwmapi.DwmSetWindowAttribute.restype = c_int
        
        res = windll.dwmapi.DwmSetWindowAttribute(
            hwnd, dwma_backdrop, byref(backdrop_type), sizeof(backdrop_type)
        )
        print("[blur] Windows 11 DWM System Backdrop Type set:", res)
    except Exception as e:
        print("[blur] Windows 11 DWM Backdrop failed:", e)


# ── Design tokens (hex values for native QColor compatibility) ────────────────
BG_0      = "#0f0d0e"
BG_1      = "#171415"
BG_2      = "#201c1f"
BG_3      = "#2d262a"
SURFACE   = "rgba(255, 255, 255, 13)"
SURFACE_H = "rgba(255, 255, 255, 31)"
BORDER    = "rgba(255, 255, 255, 31)"
BORDER_H  = "rgba(255, 255, 255, 56)"

ACCENT     = "#FB7185"
ACCENT_2   = "#A78BFA"
ACCENT_DIM = "rgba(251, 113, 133, 46)"
ACCENT_BDR = "rgba(251, 113, 133, 102)"

GREEN      = "#34d399"
BLUE       = "#818cf8"

TEXT_HI    = "rgba(255,255,255,242)"
TEXT_MID   = "rgba(255,255,255,191)"
TEXT_LOW   = "rgba(255,255,255,115)"

# ── Helpers ────────────────────────────────────────────────────────────────────
def _lbl(text, size=11, color=TEXT_MID, bold=False, mono=False, low_contrast=False):
    l = QLabel(text)
    fw  = "font-weight:600;" if bold else ""
    final_color = "rgba(255,255,255,153)" if low_contrast else color
    family = "'DM Mono', monospace" if mono else "'DM Sans', 'Segoe UI', sans-serif"
    l.setStyleSheet(
        f"color:{final_color};font-size:{size}px;font-family:{family};{fw}background:transparent;"
    )
    return l


def _divider(subtle=True):
    d = QFrame()
    d.setFrameShape(QFrame.Shape.HLine)
    opacity = 0.04 if subtle else 0.08
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
        f"QPushButton:hover {{ background-color: {hex_to_rgba(SURFACE_H)}; color: {TEXT_HI}; }} "
        f"QPushButton:pressed {{ background-color: {hex_to_rgba(SURFACE)}; }} "
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
    b.setFixedHeight(32)
    if primary:
        b.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 {ACCENT}, stop:1 {ACCENT_2}); "
            f"color: white; border: none; border-radius: 10px; "
            f"padding: 0 14px; font-size: 11px; font-family: 'DM Sans'; font-weight: 600; }} "
            f"QPushButton:hover {{ background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #ff8da1, stop:1 #bfa3ff); }} "
            f"QPushButton:pressed {{ background: rgba(251, 113, 133, 200); }} "
            f"QPushButton:disabled {{ color: {TEXT_LOW}; }}"
        )
    else:
        b.setStyleSheet(
            f"QPushButton{{background:{hex_to_rgba(SURFACE)};color:{TEXT_MID};"
            f"border:1px solid {hex_to_rgba(BORDER)};border-radius:10px;"
            f"padding:0 8px;font-size:10px;font-family:'DM Sans';}}"
            f"QPushButton:hover{{background:{hex_to_rgba(SURFACE_H)};color:{TEXT_HI};"
            f"border-color:{hex_to_rgba(BORDER_H)};}}"
            f"QPushButton:pressed{{background:{hex_to_rgba(SURFACE)};}}"
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
    """Rounded rectangle card with a nested glass styling to match main window."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 16, 16)
        
        # Subtle nested card background (10% white tint)
        p.fillPath(path, QBrush(QColor(255, 255, 255, 10)))
        
        # Subtle nested border
        p.setPen(QPen(QColor(255, 255, 255, 18), 1.0))
        p.drawPath(path)
        p.end()


class GlassCard(QWidget):
    """A premium glassmorphic panel with gradient border, shadow, and noise texture."""
    def __init__(self, border_radius=18, parent=None):
        super().__init__(parent)
        self.border_radius = border_radius
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Soft premium drop shadow
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(35)
        self.shadow.setColor(QColor(0, 0, 0, 110))
        self.shadow.setOffset(0, 8)
        self.setGraphicsEffect(self.shadow)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        
        # Clip to rounded rect
        path = QPainterPath()
        path.addRoundedRect(rect, self.border_radius, self.border_radius)
        p.setClipPath(path)
        
        # 1. Frosted light glass background
        # We use a semi-transparent light white tint so the warm room background shows through with high-density frosting
        glass_gradient = QLinearGradient(0, 0, 0, self.height())
        glass_gradient.setColorAt(0.0, QColor(255, 255, 255, 38))  # ~15% opacity white
        glass_gradient.setColorAt(0.5, QColor(255, 255, 255, 25))  # ~10% opacity white
        glass_gradient.setColorAt(1.0, QColor(245, 245, 250, 30))  # ~12% opacity soft light-blue/gray
        p.fillPath(path, QBrush(glass_gradient))
        
        # 2. Draw frosted glass noise/grain texture
        if hasattr(self.window(), 'noise_pixmap') and self.window().noise_pixmap:
            p.drawTiledPixmap(self.rect(), self.window().noise_pixmap)
            
        # Disable clipping for drawing the highlighted border
        p.setClipping(False)
        
        # 3. Fine double-highlight border (gradient from top-left to bottom-right)
        border_pen = QPen()
        border_pen.setWidthF(1.2)
        border_grad = QLinearGradient(0, 0, self.width(), self.height())
        border_grad.setColorAt(0.0, QColor(255, 255, 255, 75))  # High-contrast white highlight top-left
        border_grad.setColorAt(0.4, QColor(255, 255, 255, 25))
        border_grad.setColorAt(0.8, QColor(255, 255, 255, 10))
        border_grad.setColorAt(1.0, QColor(255, 255, 255, 35))  # Highlight bottom-right
        border_pen.setBrush(QBrush(border_grad))
        p.setPen(border_pen)
        p.drawPath(path)
        p.end()


class SidebarGlassCard(QWidget):
    """Sidebar glass panel with rounded left corners, straight right edge, 40% dark glass backdrop."""
    def __init__(self, border_radius=16, parent=None):
        super().__init__(parent)
        self.border_radius = border_radius
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Create path with rounded corners on left side only
        path = QPainterPath()
        r = self.border_radius
        path.moveTo(0, r)
        path.arcTo(QRectF(0, 0, r*2, r*2), 180, -90) # top-left
        path.lineTo(self.width(), 0) # straight to top-right
        path.lineTo(self.width(), self.height()) # straight to bottom-right
        path.lineTo(r, self.height())
        path.arcTo(QRectF(0, self.height() - r*2, r*2, r*2), 270, -90) # bottom-left
        path.closeSubpath()
        
        # 1. Paint background: rgba(0, 0, 0, 0.4)
        p.save()
        p.setClipPath(path)
        p.fillPath(path, QBrush(QColor(0, 0, 0, 50))) # 50 is ~20% opacity (highly transparent)
        
        # Tile the noise texture
        if hasattr(self.window(), 'noise_pixmap') and self.window().noise_pixmap:
            p.drawTiledPixmap(self.rect(), self.window().noise_pixmap)
        p.restore()
        
        # 2. Right border: 1px solid rgba(255, 255, 255, 0.05)
        border_pen = QPen(QColor(255, 255, 255, 13), 1.0) # 13 is 0.05 * 255
        p.setPen(border_pen)
        p.drawLine(self.width() - 1, 0, self.width() - 1, self.height())
        
        # 3. Outer boundary highlights (top-left rounded edge highlight)
        highlight_pen = QPen()
        highlight_pen.setWidthF(1.2)
        highlight_grad = QLinearGradient(0, 0, self.width(), self.height())
        highlight_grad.setColorAt(0.0, QColor(255, 255, 255, 60))
        highlight_grad.setColorAt(0.5, QColor(255, 255, 255, 10))
        highlight_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        highlight_pen.setBrush(QBrush(highlight_grad))
        p.setPen(highlight_pen)
        p.drawPath(path)
        p.end()


class ContentGlassCard(QWidget):
    """Content canvas glass panel with rounded right corners, straight left edge, 15% dark glass backdrop."""
    def __init__(self, border_radius=16, parent=None):
        super().__init__(parent)
        self.border_radius = border_radius
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Create path with rounded corners on right side only
        path = QPainterPath()
        r = self.border_radius
        path.moveTo(0, 0)
        path.lineTo(self.width() - r, 0)
        path.arcTo(QRectF(self.width() - r*2, 0, r*2, r*2), 90, -90) # top-right
        path.lineTo(self.width(), self.height() - r)
        path.arcTo(QRectF(self.width() - r*2, self.height() - r*2, r*2, r*2), 0, -90) # bottom-right
        path.lineTo(0, self.height())
        path.closeSubpath()
        
        # Paint background: rgba(0, 0, 0, 0.15)
        p.save()
        p.setClipPath(path)
        p.fillPath(path, QBrush(QColor(0, 0, 0, 25))) # 25 is ~10% opacity (very transparent)
        
        # Tile the noise texture
        if hasattr(self.window(), 'noise_pixmap') and self.window().noise_pixmap:
            p.drawTiledPixmap(self.rect(), self.window().noise_pixmap)
        p.restore()
        
        # Outer boundary highlights
        highlight_pen = QPen()
        highlight_pen.setWidthF(1.2)
        highlight_grad = QLinearGradient(0, 0, self.width(), self.height())
        highlight_grad.setColorAt(0.0, QColor(255, 255, 255, 45))
        highlight_grad.setColorAt(0.5, QColor(255, 255, 255, 10))
        highlight_grad.setColorAt(1.0, QColor(255, 255, 255, 20))
        highlight_pen.setBrush(QBrush(highlight_grad))
        p.setPen(highlight_pen)
        p.drawPath(path)
        p.end()


def is_startup_enabled() -> bool:
    if platform.system() != "Windows":
        return False
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "GoofyFocus"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, app_name)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def set_startup(enable: bool):
    if platform.system() != "Windows":
        return
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "GoofyFocus"
    
    if getattr(sys, 'frozen', False):
        cmd = f'"{sys.executable}"'
    else:
        script_path = os.path.abspath(sys.argv[0])
        cmd = f'"{sys.executable}" "{script_path}"'
        
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        if enable:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
            print(f"[startup] Enabled launch on startup: {cmd}")
        else:
            try:
                winreg.DeleteValue(key, app_name)
                print("[startup] Disabled launch on startup")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        print(f"[startup] Failed to edit startup registry: {e}")


class ToggleSwitch(QAbstractButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(38, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = False
        self._thumb_position = 2

    def setChecked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            target = 20 if checked else 2
            self.anim = QPropertyAnimation(self, b"thumb_position")
            self.anim.setDuration(150)
            self.anim.setStartValue(self._thumb_position)
            self.anim.setEndValue(target)
            self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
            self.anim.start()
            self.update()

    def isChecked(self) -> bool:
        return self._checked

    @pyqtProperty(int)
    def thumb_position(self):
        return self._thumb_position

    @thumb_position.setter
    def thumb_position(self, pos):
        self._thumb_position = pos
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
            self.clicked.emit(self._checked)
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 10, 10)
        
        if self._checked:
            track_color = QColor(ACCENT)
        else:
            track_color = QColor(255, 255, 255, 20)
            
        p.fillPath(path, QBrush(track_color))
        
        p.setPen(QPen(QColor(255, 255, 255, 30), 1.0))
        p.drawPath(path)
        
        p.setBrush(QBrush(QColor("#ffffff")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(self._thumb_position, 2, 16, 16))
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
                p.setBrush(QBrush(QColor(251, 113, 133, 80)))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QRectF(cx - r - 6, cy - r - 6, (r + 6) * 2, (r + 6) * 2))
                # Filled dot
                p.setBrush(QBrush(QColor(ACCENT)))
                p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
            elif i == self._completed:
                # Current dot - outline neon pink
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(QColor(ACCENT_2), 1.5))
                p.drawEllipse(QRectF(cx - r + 0.5, cy - r + 0.5, r * 2 - 1, r * 2 - 1))
            else:
                # Empty dot - outline dim
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(QColor(255, 255, 255, 40), 1.5))
                p.drawEllipse(QRectF(cx - r + 0.5, cy - r + 0.5, r * 2 - 1, r * 2 - 1))
        p.end()

# ── Profile Avatar Widget ──────────────────────────────────────────────────────
class ProfileAvatar(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._initials = "G"
        self.setStyleSheet("background: transparent; border: none;")
        
    def set_user(self, info):
        given_name = info.get("given_name", "Guest")
        self._initials = given_name[0].upper() if given_name else "G"
        self.update()
        
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = QRectF(self.rect())
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0, QColor("#FB7185"))
        grad.setColorAt(1, QColor("#A78BFA"))
        
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(rect)
        
        # Circle outline glow
        p.setPen(QPen(QColor(255, 255, 255, 60), 1.5))
        p.drawEllipse(rect.adjusted(0.75, 0.75, -0.75, -0.75))
        
        p.setPen(QColor(255, 255, 255))
        font = QFont("DM Sans", 10, QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._initials)
        p.end()


# ── Pro Custom Spinbox ────────────────────────────────────────────────────────
class ProSpinBox(QSpinBox):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window

    def mousePressEvent(self, event):
        if not self.main_window._is_pro:
            self.main_window._show_upgrade_dialog()
            event.accept()
        else:
            super().mousePressEvent(event)

    def stepBy(self, steps):
        if not self.main_window._is_pro:
            self.main_window._show_upgrade_dialog()
        else:
            super().stepBy(steps)

    def keyPressEvent(self, event):
        if not self.main_window._is_pro:
            self.main_window._show_upgrade_dialog()
            event.accept()
        else:
            super().keyPressEvent(event)


# ── Main Window ────────────────────────────────────────────────────────────────
class MainWindow(QWidget):
    update_detected = pyqtSignal(str, str)
    update_status   = pyqtSignal(bool, str)

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
        self._update_url      = None

        self.setWindowTitle("Goofy Focus")
        self.setFixedSize(750, 560)

        # Generate noise texture for frosted glass (optimized using QImage from raw bytes)
        import random
        from PyQt6.QtGui import QImage
        width, height = 128, 128
        img_data = bytearray(width * height * 4)
        for i in range(width * height):
            idx = i * 4
            # Format is ARGB32 (little-endian on Windows: B, G, R, A)
            img_data[idx] = 255      # B
            img_data[idx+1] = 255    # G
            img_data[idx+2] = 255    # R
            img_data[idx+3] = random.randint(0, 10) # A (0 to ~4% opacity)
        
        qimg = QImage(img_data, width, height, QImage.Format.Format_ARGB32)
        self.noise_pixmap = QPixmap.fromImage(qimg)

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
        self.update_detected.connect(self._notify_update)
        self.update_status.connect(self._on_update_status)
        self._check_updates()
        self._refresh_pro_badge()

    # ── Build UI ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Horizontal layout as main window container
        main_lay = QHBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # 1. Left Sidebar
        self.sidebar = SidebarGlassCard(border_radius=16)
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(74)
        
        sidebar_lay = QVBoxLayout(self.sidebar)
        sidebar_lay.setContentsMargins(0, 20, 0, 20)
        sidebar_lay.setSpacing(20)
        sidebar_lay.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # macOS style window controls (realistic spherical radial gradients with hover symbols)
        title_dots = QHBoxLayout()
        title_dots.setSpacing(8)
        title_dots.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_dot_close = QPushButton()
        btn_dot_close.setFixedSize(12, 12)
        btn_dot_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dot_close.setText("×")
        btn_dot_close.setStyleSheet("""
            QPushButton {
                background: qradialgradient(cx:0.35, cy:0.35, radius:0.5, fx:0.35, fy:0.35, stop:0 #ff7b72, stop:0.75 #ff3b30, stop:1 #b51c15);
                border: 1px solid rgba(0, 0, 0, 51);
                border-radius: 6px;
                color: transparent;
                font-size: 8px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-weight: bold;
                text-align: center;
                padding-bottom: 2px;
            }
            QPushButton:hover {
                color: rgba(0, 0, 0, 160);
            }
        """)
        btn_dot_close.clicked.connect(self._quit_app)
        
        btn_dot_min = QPushButton()
        btn_dot_min.setFixedSize(12, 12)
        btn_dot_min.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dot_min.setText("−")
        btn_dot_min.setStyleSheet("""
            QPushButton {
                background: qradialgradient(cx:0.35, cy:0.35, radius:0.5, fx:0.35, fy:0.35, stop:0 #ffeb99, stop:0.75 #ffcc00, stop:1 #b58900);
                border: 1px solid rgba(0, 0, 0, 51);
                border-radius: 6px;
                color: transparent;
                font-size: 8px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-weight: bold;
                text-align: center;
                padding-bottom: 2px;
            }
            QPushButton:hover {
                color: rgba(0, 0, 0, 160);
            }
        """)
        btn_dot_min.clicked.connect(self.showMinimized)
        
        btn_dot_max = QPushButton()
        btn_dot_max.setFixedSize(12, 12)
        btn_dot_max.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dot_max.setText("+")
        btn_dot_max.setStyleSheet("""
            QPushButton {
                background: qradialgradient(cx:0.35, cy:0.35, radius:0.5, fx:0.35, fy:0.35, stop:0 #9effb1, stop:0.75 #34c759, stop:1 #1b8535);
                border: 1px solid rgba(0, 0, 0, 51);
                border-radius: 6px;
                color: transparent;
                font-size: 8px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-weight: bold;
                text-align: center;
                padding-bottom: 2px;
            }
            QPushButton:hover {
                color: rgba(0, 0, 0, 160);
            }
        """)
        btn_dot_max.clicked.connect(self._toggle_maximized)
        
        title_dots.addWidget(btn_dot_close)
        title_dots.addWidget(btn_dot_min)
        title_dots.addWidget(btn_dot_max)
        sidebar_lay.addLayout(title_dots)
        sidebar_lay.addSpacing(12)

        # Navigation items
        self.sidebar_btns = []
        nav_items = [
            ("Analytics", "activity.svg"),
            ("Sessions",  "clock.svg"),
            ("Settings",  "settings.svg"),
            ("Account",   "user.svg"),
        ]
        
        for idx, (label, icon) in enumerate(nav_items):
            btn = self._create_sidebar_btn(label, icon)
            btn.clicked.connect(lambda checked, i=idx: self._switch_tab(i))
            sidebar_lay.addWidget(btn)
            self.sidebar_btns.append(btn)
            
        sidebar_lay.addStretch()

        # Global sound toggle button
        self.btn_global_mute = _icon_btn("")
        self.btn_global_mute.setIcon(QIcon(os.path.join(ASSETS_DIR, "icons", "volume-2.svg")))
        self.btn_global_mute.setIconSize(QSize(16, 16))
        self.btn_global_mute.setToolTip("Toggle sound")
        self.btn_global_mute.clicked.connect(self._toggle_global_mute)
        sidebar_lay.addWidget(self.btn_global_mute, alignment=Qt.AlignmentFlag.AlignCenter)
        sidebar_lay.addSpacing(4)

        # Profile avatar
        self.btn_avatar = ProfileAvatar()
        self.btn_avatar.clicked.connect(self._on_avatar_clicked)
        sidebar_lay.addWidget(self.btn_avatar, alignment=Qt.AlignmentFlag.AlignCenter)
        
        main_lay.addWidget(self.sidebar)

        # 2. Main content area
        self.content_container = ContentGlassCard(border_radius=16)
        self.content_container.setObjectName("content_container")
        content_lay = QVBoxLayout(self.content_container)
        content_lay.setContentsMargins(22, 22, 22, 22)
        content_lay.setSpacing(0)

        self.stack = QStackedWidget()
        self.stack.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # ── Tab 0: Dashboard Page ──
        self.dashboard_page = QWidget()
        self.dashboard_page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        dash_lay = QVBoxLayout(self.dashboard_page)
        dash_lay.setContentsMargins(0, 0, 0, 0)
        
        dash_header = QHBoxLayout()
        dash_title = _lbl("Focus Analytics", size=18, color=TEXT_HI, bold=True)
        dash_header.addWidget(dash_title)
        dash_header.addStretch()
        dash_lay.addLayout(dash_header)
        dash_lay.addSpacing(10)
        
        self.stats_widget = StatsWindow(user_info=self._user_info, is_pro=self._is_pro, active_elapsed_secs=0, is_embedded=True, parent=self)
        dash_lay.addWidget(self.stats_widget)
        self.stack.addWidget(self.dashboard_page)

        # ── Tab 1: Sessions Page ──
        self.sessions_page = QWidget()
        self.sessions_page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        sess_lay = QVBoxLayout(self.sessions_page)
        sess_lay.setContentsMargins(0, 0, 0, 0)
        sess_lay.setSpacing(14)

        header_v = QVBoxLayout()
        header_v.setSpacing(2)
        header_v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_row = QHBoxLayout()
        title_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_row.setSpacing(8)
        
        moon_icon = QLabel()
        moon_icon.setPixmap(QIcon(os.path.join(ASSETS_DIR, "icons", "moon.svg")).pixmap(18, 18))
        moon_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        moon_icon.setStyleSheet("background: transparent;")
        
        title_lbl = QLabel("Goofy Focus")
        title_lbl.setStyleSheet(f"color: {TEXT_HI}; font-size: 18px; font-family: 'DM Sans'; font-weight: 600; background: transparent;")
        
        title_row.addWidget(moon_icon)
        title_row.addWidget(title_lbl)
        header_v.addLayout(title_row)

        self.subtitle_lbl = _lbl("Pomodoro: Interval 1 of 4", size=10, color=ACCENT_2, mono=True)
        self.subtitle_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_v.addWidget(self.subtitle_lbl)
        sess_lay.addLayout(header_v)

        # Timer Circle
        self.circ = CircularTimer(self.controller)
        sess_lay.addWidget(self.circ, alignment=Qt.AlignmentFlag.AlignCenter)

        # Editable Task description
        task_row = QHBoxLayout()
        task_row.setSpacing(6)
        task_row.addStretch()
        
        task_prefix = QLabel("Current task:")
        task_prefix.setStyleSheet("color: rgba(255,255,255,140); font-family: 'DM Sans'; font-size: 11px; background: transparent;")
        
        self.task_input = QLineEdit("Studying about life...")
        self.task_input.setFixedWidth(130)
        self.task_input.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.task_input.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(255, 255, 255, 13);
                border: 1px solid rgba(255, 255, 255, 31);
                border-radius: 8px;
                color: white;
                font-family: 'DM Sans';
                font-size: 11px;
                padding: 4px 10px;
            }}
            QLineEdit:hover, QLineEdit:focus {{
                border-color: {ACCENT};
                background: rgba(255, 255, 255, 20);
            }}
        """)
        s = QSettings("GoofyFocus", "GoofyFocus")
        saved_task = s.value("current_task", "Studying about life...")
        if saved_task == "Design UI Mockups":
            saved_task = "Studying about life..."
            s.setValue("current_task", saved_task)
        self.task_input.setText(saved_task)
        self.task_input.textChanged.connect(lambda t: QSettings("GoofyFocus", "GoofyFocus").setValue("current_task", t))
        
        task_edit_icon = QLabel()
        task_edit_icon.setPixmap(QIcon(os.path.join(ASSETS_DIR, "icons", "edit.svg")).pixmap(10, 10))
        task_edit_icon.setStyleSheet("background: transparent;")
        op_edit = QGraphicsOpacityEffect(task_edit_icon)
        op_edit.setOpacity(0.45)
        task_edit_icon.setGraphicsEffect(op_edit)
        
        task_row.addWidget(task_prefix)
        task_row.addWidget(self.task_input)
        task_row.addWidget(task_edit_icon)
        task_row.addStretch()
        sess_lay.addLayout(task_row)
 
        # Quick Actions at the bottom
        pills_row = QHBoxLayout()
        pills_row.setSpacing(10)
        pills_row.addStretch()
        
        btn_pill_short = QPushButton("Break (5:00)")
        btn_pill_long = QPushButton("Long Break")
        btn_pill_end = QPushButton("End Session")
        
        pill_style = """
            QPushButton {
                background: rgba(255, 255, 255, 15);
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 14px;
                padding: 0px 18px;
                min-height: 28px;
                color: rgba(255, 255, 255, 217);
                font-family: 'DM Sans', sans-serif;
                font-size: 10px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 31);
                border-color: rgba(255, 255, 255, 38);
                color: white;
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 10);
            }
        """
        for b in (btn_pill_short, btn_pill_long, btn_pill_end):
            b.setStyleSheet(pill_style)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            pills_row.addWidget(b)
            
        btn_pill_short.clicked.connect(lambda: self._set_phase_and_start("Short Break"))
        btn_pill_long.clicked.connect(lambda: self._set_phase_and_start("Long Break"))
        btn_pill_end.clicked.connect(self._ui_reset)
        
        pills_row.addStretch()
        sess_lay.addLayout(pills_row)
        self.stack.addWidget(self.sessions_page)

        # ── Tab 2: Settings Page ──
        self.settings_page = QWidget()
        self.settings_page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        settings_lay = QVBoxLayout(self.settings_page)
        settings_lay.setContentsMargins(0, 0, 0, 0)
        
        settings_header = QHBoxLayout()
        settings_title = _lbl("Settings", size=18, color=TEXT_HI, bold=True)
        settings_header.addWidget(settings_title)
        
        self.settings_pro_badge = QLabel("✦ pro")
        self.settings_pro_badge.setStyleSheet(
            f"color:{ACCENT};font-size:9px;font-family:'DM Sans';"
            f"background:{ACCENT_DIM};border:1px solid {ACCENT_BDR};"
            "border-radius:8px;padding:2px 6px;font-weight:600;"
        )
        settings_header.addWidget(self.settings_pro_badge)
        
        self.update_badge = QPushButton("Update Available ⏳")
        self.update_badge.setStyleSheet(f"""
            QPushButton {{
                color: #ffffff;
                font-size: 9px;
                font-family: 'DM Sans';
                background: {ACCENT};
                border: none;
                border-radius: 8px;
                padding: 2px 8px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {ACCENT_2};
            }}
        """)
        self.update_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_badge.setVisible(False)
        self.update_badge.clicked.connect(self._start_auto_update)
        settings_header.addWidget(self.update_badge)
        
        settings_header.addStretch()
        
        settings_lay.addLayout(settings_header)
        settings_lay.addSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: transparent; }} 
            QScrollBar:vertical {{ width: 4px; background: transparent; }} 
            QScrollBar::handle:vertical {{ background: {BORDER_H}; border-radius: 2px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        """)

        self.settings_card = self._build_settings()
        scroll.setWidget(self.settings_card)
        settings_lay.addWidget(scroll)
        self.stack.addWidget(self.settings_page)

        # ── Tab 3: Analytics Page ──
        self.analytics_page = QWidget()
        self.analytics_page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        anal_lay = QVBoxLayout(self.analytics_page)
        anal_lay.setContentsMargins(0, 0, 0, 0)
        anal_lay.setSpacing(14)
        
        anal_header = QHBoxLayout()
        anal_title = _lbl("Account & Feedback", size=18, color=TEXT_HI, bold=True)
        anal_header.addWidget(anal_title)
        
        self.anal_pro_badge = QLabel("✦ pro")
        self.anal_pro_badge.setStyleSheet(
            f"color:{ACCENT};font-size:9px;font-family:'DM Sans';"
            f"background:{ACCENT_DIM};border:1px solid {ACCENT_BDR};"
            "border-radius:8px;padding:2px 6px;font-weight:600;"
        )
        anal_header.addWidget(self.anal_pro_badge)
        
        self.anal_update_badge = QPushButton("Update Available ⏳")
        self.anal_update_badge.setStyleSheet(f"""
            QPushButton {{
                color: #ffffff;
                font-size: 9px;
                font-family: 'DM Sans';
                background: {ACCENT};
                border: none;
                border-radius: 8px;
                padding: 2px 8px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {ACCENT_2};
            }}
        """)
        self.anal_update_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.anal_update_badge.setVisible(False)
        self.anal_update_badge.clicked.connect(self._start_auto_update)
        anal_header.addWidget(self.anal_update_badge)
        
        anal_header.addStretch()
        
        anal_lay.addLayout(anal_header)
        anal_lay.addSpacing(10)
        
        self.account_card = SettingsCard()
        acc_lay = QVBoxLayout(self.account_card)
        acc_lay.setContentsMargins(20, 20, 20, 20)
        acc_lay.setSpacing(16)
        
        self.user_title = _lbl("Account Status", size=13, color=TEXT_HI, bold=True)
        acc_lay.addWidget(self.user_title)
        
        self.user_email_lbl = _lbl("Logged in as Guest", size=11, color=TEXT_MID)
        acc_lay.addWidget(self.user_email_lbl)
        
        self.user_streak_lbl = _lbl("Connect to sync focus sessions", size=10, color=TEXT_LOW)
        acc_lay.addWidget(self.user_streak_lbl)
        
        btn_row_auth = QHBoxLayout()
        btn_row_auth.setSpacing(12)
        
        self.btn_auth_page = QPushButton("Sign In with Google")
        self.btn_auth_page.setFixedHeight(36)
        self.btn_auth_page.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_auth_page.setStyleSheet(f"""
            QPushButton {{
                background: rgba(251, 113, 133, 20);
                color: {ACCENT};
                border: 1px solid {BORDER};
                border-radius: 10px;
                padding: 0 16px;
                font-size: 11px;
                font-family: 'DM Sans';
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: rgba(251, 113, 133, 40);
                color: white;
            }}
        """)
        self.btn_auth_page.clicked.connect(self._do_google_login)
        btn_row_auth.addWidget(self.btn_auth_page)
        
        self.btn_sync_profile = QPushButton("Sync Profile")
        self.btn_sync_profile.setFixedHeight(36)
        self.btn_sync_profile.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sync_profile.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 10);
                border: 1px solid rgba(255, 255, 255, 15);
                border-radius: 10px;
                padding: 0 16px;
                color: rgba(255, 255, 255, 200);
                font-family: 'DM Sans';
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 18);
                color: white;
            }
        """)
        self.btn_sync_profile.clicked.connect(self._manual_sync_profile)
        self.btn_sync_profile.setVisible(False)
        btn_row_auth.addWidget(self.btn_sync_profile)
        
        self.btn_feedback_page = QPushButton("Send App Feedback")
        self.btn_feedback_page.setFixedHeight(36)
        self.btn_feedback_page.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_feedback_page.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 10);
                border: 1px solid rgba(255, 255, 255, 15);
                border-radius: 10px;
                padding: 0 16px;
                color: rgba(255, 255, 255, 200);
                font-family: 'DM Sans';
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 18);
                color: white;
            }
        """)
        self.btn_feedback_page.clicked.connect(self._open_feedback)
        btn_row_auth.addWidget(self.btn_feedback_page)
        
        acc_lay.addLayout(btn_row_auth)
        acc_lay.addStretch()
        
        anal_lay.addWidget(self.account_card)
        anal_lay.addStretch()
        self.stack.addWidget(self.analytics_page)

        content_lay.addWidget(self.stack)
        main_lay.addWidget(self.content_container, 1)

        # Default page: Sessions (Tab 1)
        self._switch_tab(1)

    def _switch_tab(self, index: int):
        self.stack.setCurrentIndex(index)
        
        # Style active / inactive sidebar buttons
        for i, btn in enumerate(self.sidebar_btns):
            text_lbl = btn.property("text_lbl")
            icon_lbl = btn.property("icon_lbl")
            op_effect = icon_lbl.property("opacity_effect")
            if i == index:
                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 46);
                        border: 1px solid rgba(255, 255, 255, 64);
                        border-radius: 12px;
                    }
                """)
                text_lbl.setStyleSheet("color: rgba(255, 255, 255, 242); font-size: 9px; font-family: 'DM Sans'; font-weight: 600; background: transparent;")
                if op_effect:
                    op_effect.setOpacity(0.95)
                # Apply a clean glass highlight drop shadow matching the light glass theme
                shadow = QGraphicsDropShadowEffect(btn)
                shadow.setBlurRadius(10)
                shadow.setColor(QColor(255, 255, 255, 45))
                shadow.setOffset(0, 0)
                btn.setGraphicsEffect(shadow)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: none;
                    }
                    QPushButton:hover {
                        background: rgba(255, 255, 255, 10);
                        border-radius: 12px;
                    }
                """)
                text_lbl.setStyleSheet("color: rgba(255, 255, 255, 128); font-size: 9px; font-family: 'DM Sans'; font-weight: 500; background: transparent;")
                if op_effect:
                    op_effect.setOpacity(0.50)
                btn.setGraphicsEffect(None)

    def _set_phase_and_start(self, phase: str):
        self.controller.set_phase(phase)
        self._ui_start()

    def _on_avatar_clicked(self):
        if self._user_info:
            self._show_logout_menu()
        else:
            self._switch_tab(3)

    def _create_sidebar_btn(self, text, icon_name):
        btn = QPushButton()
        btn.setFixedSize(50, 50)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        lay = QVBoxLayout(btn)
        lay.setContentsMargins(0, 6, 0, 6)
        lay.setSpacing(3)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(QIcon(os.path.join(ASSETS_DIR, "icons", icon_name)).pixmap(20, 20))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("background: transparent;")
        
        op = QGraphicsOpacityEffect(icon_lbl)
        op.setOpacity(0.50)
        icon_lbl.setGraphicsEffect(op)
        icon_lbl.setProperty("opacity_effect", op)
        
        txt_lbl = QLabel(text)
        txt_lbl.setStyleSheet("color: rgba(255, 255, 255, 128); font-size: 9px; font-family: 'DM Sans'; font-weight: 500; background: transparent;")
        txt_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lay.addWidget(icon_lbl)
        lay.addWidget(txt_lbl)
        
        btn.setProperty("text_lbl", txt_lbl)
        btn.setProperty("icon_lbl", icon_lbl)
        
        return btn


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
            f"QComboBox{{background:rgba(255,255,255,13);border:1px solid rgba(255,255,255,31);"
            f"border-radius:8px;padding:5px 10px;color:{TEXT_HI};font-size:11px;"
            "font-family:'DM Sans';font-weight:400;}"
            "QComboBox:hover, QComboBox:focus{border-color:" + ACCENT + ";}"
            "QComboBox::drop-down{border:none;width:14px;}"
            f"QComboBox QAbstractItemView{{background:#120E15;border:1px solid rgba(255,255,255,31);"
            f"color:{TEXT_HI};selection-background-color:rgba(255,255,255,20);font-size:11px;border-radius:6px;}}"
        )
        lay.addWidget(_setting_row("Break flow", "session cycle pattern", self._flow_combo))
        lay.addWidget(_divider())

        # Sessions per cycle (pro-gated)
        spc_w = QWidget()
        spc_w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        sl = QHBoxLayout(spc_w)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(5)

        self._spc_spin = ProSpinBox(self)
        self._spc_spin.setRange(1, 12)
        self._spc_spin.setValue(4)
        self._spc_spin.setFixedWidth(44)
        self._spc_spin.setStyleSheet(
            f"QSpinBox{{background:rgba(255,255,255,13);border:1px solid rgba(255,255,255,31);"
            f"border-radius:8px;padding:4px 6px;color:{TEXT_HI};font-size:11px;font-weight:400;}}"
            f"QSpinBox:focus{{border-color:{ACCENT};}}"
            "QSpinBox::up-button,QSpinBox::down-button{width:0px;border:none;}"
        )
        self._spc_lock = QLabel()
        self._spc_lock.setPixmap(QIcon(os.path.join(ASSETS_DIR, "icons", "lock.svg")).pixmap(16, 16))
        self._spc_lock.setStyleSheet("background: transparent;")
        op_lock = QGraphicsOpacityEffect(self._spc_lock)
        op_lock.setOpacity(0.45)
        self._spc_lock.setGraphicsEffect(op_lock)
        sl.addWidget(self._spc_spin)
        sl.addWidget(self._spc_lock)
        lay.addWidget(_setting_row("Sessions per cycle", "work blocks before long break", spc_w))
        lay.addWidget(_divider())

        # Launch on startup
        self._startup_toggle = ToggleSwitch()
        self._startup_toggle.setChecked(is_startup_enabled())
        lay.addWidget(_setting_row("Launch on startup", "start app automatically at login", self._startup_toggle))
        lay.addWidget(_divider())

        # ── PERSONALISE ────────────────────────────────────────────────────────
        lay.addWidget(SectionHeader("PERSONALISE"))

        self.btn_custom_msgs   = _action_btn("edit")
        self.btn_custom_gifs   = _action_btn("manage")
        self.btn_custom_sounds = _action_btn("manage")

        self.btn_custom_msgs.clicked.connect(self._show_custom_msgs)
        self.btn_custom_gifs.clicked.connect(self._show_gif_manager)
        self.btn_custom_sounds.clicked.connect(self._show_sound_manager)

        # Break messages layout with lock icon
        self._msgs_lock = QLabel()
        self._msgs_lock.setPixmap(QIcon(os.path.join(ASSETS_DIR, "icons", "lock.svg")).pixmap(16, 16))
        self._msgs_lock.setStyleSheet("background: transparent;")
        op_msgs_lock = QGraphicsOpacityEffect(self._msgs_lock)
        op_msgs_lock.setOpacity(0.45)
        self._msgs_lock.setGraphicsEffect(op_msgs_lock)
        
        msgs_w = QWidget()
        msgs_w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        msgs_lay = QHBoxLayout(msgs_w)
        msgs_lay.setContentsMargins(0, 0, 0, 0)
        msgs_lay.setSpacing(5)
        msgs_lay.addWidget(self._msgs_lock)
        msgs_lay.addWidget(self.btn_custom_msgs)

        # GIF packs layout with lock icon
        self._gifs_lock = QLabel()
        self._gifs_lock.setPixmap(QIcon(os.path.join(ASSETS_DIR, "icons", "lock.svg")).pixmap(16, 16))
        self._gifs_lock.setStyleSheet("background: transparent;")
        op_gifs_lock = QGraphicsOpacityEffect(self._gifs_lock)
        op_gifs_lock.setOpacity(0.45)
        self._gifs_lock.setGraphicsEffect(op_gifs_lock)
        
        gifs_w = QWidget()
        gifs_w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        gifs_lay = QHBoxLayout(gifs_w)
        gifs_lay.setContentsMargins(0, 0, 0, 0)
        gifs_lay.setSpacing(5)
        gifs_lay.addWidget(self._gifs_lock)
        gifs_lay.addWidget(self.btn_custom_gifs)

        # Sounds layout with lock icon
        self._sounds_lock = QLabel()
        self._sounds_lock.setPixmap(QIcon(os.path.join(ASSETS_DIR, "icons", "lock.svg")).pixmap(16, 16))
        self._sounds_lock.setStyleSheet("background: transparent;")
        op_sounds_lock = QGraphicsOpacityEffect(self._sounds_lock)
        op_sounds_lock.setOpacity(0.45)
        self._sounds_lock.setGraphicsEffect(op_sounds_lock)
        
        sounds_w = QWidget()
        sounds_w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        sounds_lay = QHBoxLayout(sounds_w)
        sounds_lay.setContentsMargins(0, 0, 0, 0)
        sounds_lay.setSpacing(5)
        sounds_lay.addWidget(self._sounds_lock)
        sounds_lay.addWidget(self.btn_custom_sounds)

        lay.addWidget(_setting_row("Break messages", "text shown on rest screen", msgs_w))
        lay.addWidget(_divider())
        lay.addWidget(_setting_row("GIF packs",      "animated break visuals",    gifs_w))
        lay.addWidget(_divider())
        lay.addWidget(_setting_row("Sounds",          "ambient break audio",       sounds_w))

        # ── Save button ────────────────────────────────────────────────────────
        lay.addSpacing(14)
        self.btn_apply = QPushButton("save settings")
        self.btn_apply.setFixedHeight(38)
        self.btn_apply.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {ACCENT}, stop:1 {ACCENT_2});
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 11px;
                font-family: 'DM Sans';
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff8da1, stop:1 #bfa3ff);
            }}
        """)
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
            grad.setColorAt(0, QColor("#00f0ff"))
            grad.setColorAt(1, QColor("#ff007f"))
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
            "QMenu::item:selected{background:rgba(0, 240, 255, 51);}"
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
        self.tray.messageClicked.connect(self._on_tray_message_clicked)
        self.tray.show()

    # ── Signals ────────────────────────────────────────────────────────────────
    def _connect_signals(self):
        self.circ.btn_start.clicked.connect(self._ui_start)
        self.circ.btn_pause.clicked.connect(self._ui_pause)
        self.circ.btn_skip.clicked.connect(self._ui_skip)
        self.circ.btn_reset.clicked.connect(self._ui_reset)
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
        
        # Reload stats widget to show newly saved session immediately
        if hasattr(self, 'stats_widget'):
            self.stats_widget._load_stats()
        QTimer.singleShot(5000, lambda: self._set_status("ready" if not self.controller.is_running else "focusing"))

    # ── UI control methods ─────────────────────────────────────────────────────
    def _set_status(self, text, color=ACCENT):
        print(f"[status] {text}")

    def _ui_start(self):
        self.circ.btn_start.hide(); self.circ.btn_pause.show(); self.circ.lbl_play_pause.setText("PAUSE")
        self._act_toggle.setText("Pause timer")
        self.controller.start()
        self._set_status("focusing")

    def _ui_pause(self):
        self.circ.btn_pause.hide(); self.circ.btn_start.show(); self.circ.lbl_play_pause.setText("START")
        self._act_toggle.setText("Resume timer")
        self.controller.pause()
        self._set_status("paused", TEXT_MID)

    def _ui_skip(self):
        self.circ.btn_skip.setEnabled(False)
        self.controller.skip()
        QTimer.singleShot(500, lambda: self.circ.btn_skip.setEnabled(True))

    def _ui_reset(self):
        self.circ.btn_pause.hide(); self.circ.btn_start.show(); self.circ.lbl_play_pause.setText("START")
        self._act_toggle.setText("Pause timer")
        self.controller.reset()
        spc = self.controller.sessions_per_cycle
        self.subtitle_lbl.setText(f"Pomodoro: Interval 1 of {spc}")
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
        icon_name = "volume-x.svg" if self._muted else "volume-2.svg"
        self.btn_global_mute.setIcon(QIcon(os.path.join(ASSETS_DIR, "icons", icon_name)))
        if self.overlay and self._muted:
            self.overlay._stop_sound()
        QSettings("GoofyFocus", "GoofyFocus").setValue("muted", self._muted)

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
            s = QSettings("GoofyFocus", "GoofyFocus")
            if self._is_pro:
                self.controller.sessions_per_cycle = self._spc_spin.value()
                s.setValue("sessions_per_cycle", self._spc_spin.value())
            
            startup_enabled = self._startup_toggle.isChecked()
            set_startup(startup_enabled)
            s.setValue("launch_on_startup", startup_enabled)
            
            self.circ.btn_pause.hide(); self.circ.btn_start.show(); self.circ.lbl_play_pause.setText("START")
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
        s = QSettings("GoofyFocus", "GoofyFocus")
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
        if s.value("muted", False) == "true" or s.value("muted", False) is True:
            self._muted = True
            self.btn_global_mute.setIcon(QIcon(os.path.join(ASSETS_DIR, "icons", "volume-x.svg")))
        self._startup_toggle.setChecked(is_startup_enabled())
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
        self.subtitle_lbl.setText(f"Pomodoro: Interval {pos} of {spc}")

    # ── Pro / Auth ─────────────────────────────────────────────────────────────
    def _refresh_pro_badge(self):
        is_pro = getattr(self, '_is_pro', False)
        self.settings_pro_badge.setVisible(is_pro)
        self.anal_pro_badge.setVisible(is_pro)
        
        # Configure self._spc_spin style and focus policy based on pro status
        self._spc_spin.setFocusPolicy(Qt.FocusPolicy.StrongFocus if is_pro else Qt.FocusPolicy.NoFocus)
        if is_pro:
            self._spc_spin.setStyleSheet(
                f"QSpinBox{{background:rgba(255,255,255,13);border:1px solid rgba(255,255,255,31);"
                f"border-radius:8px;padding:4px 6px;color:{TEXT_HI};font-size:11px;font-weight:400;}}"
                f"QSpinBox:focus{{border-color:{ACCENT};}}"
                "QSpinBox::up-button,QSpinBox::down-button{width:0px;border:none;}"
            )
        else:
            self._spc_spin.setStyleSheet(
                f"QSpinBox{{background:rgba(255,255,255,8);border:1px solid rgba(255,255,255,15);"
                f"border-radius:8px;padding:4px 6px;color:{TEXT_LOW};font-size:11px;font-weight:400;}}"
                "QSpinBox::up-button,QSpinBox::down-button{width:0px;border:none;}"
            )
        
        self._spc_lock.setVisible(not is_pro)
        
        if hasattr(self, '_msgs_lock'):
            self._msgs_lock.setVisible(not is_pro)
        if hasattr(self, '_gifs_lock'):
            self._gifs_lock.setVisible(not is_pro)
        if hasattr(self, '_sounds_lock'):
            self._sounds_lock.setVisible(not is_pro)
        
        # Sync stats widget
        if hasattr(self, 'stats_widget'):
            self.stats_widget._is_pro = is_pro
            self.stats_widget._load_stats()

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
        else:
            self._upgrade_win.raise_()
            self._upgrade_win.activateWindow()

    def _open_feedback(self):
        self._feedback_win = FeedbackWindow(user_email=self._user_info.get("email", ""))
        self._feedback_win.show()

    def _load_saved_login(self):
        info = load_cached_user()
        if info:
            self._user_info = info
            self._is_pro    = info.get("is_pro", False)
            self._refresh_pro_badge()
            self._set_login_state(info)
            self._sync_pro_status()

    def _do_google_login(self):
        self.btn_auth_page.setText("signing in…")
        QApplication.processEvents()
        try:
            info            = perform_login()
            self._user_info = info
            self._is_pro    = info.get("is_pro", False)
            self._refresh_pro_badge()
            self._set_login_state(info)
        except Exception as e:
            self.btn_auth_page.setText("Sign In with Google")
            self._set_status("auth failed", "rgba(248,113,113,160)")
            print(f"Auth error: {e}")

    def _set_login_state(self, info: dict):
        """Switch auth state and update UI components."""
        email = info.get("email", "")
        
        # Update sidebar avatar
        self.btn_avatar.set_user(info)
        
        # Update Analytics page labels
        self.user_email_lbl.setText(f"Logged in as {email}")
        self.user_streak_lbl.setText("Focus Streak: Connected ✓")
        
        # Update button to show Logout option on Analytics page
        self.btn_auth_page.setText("Sign Out")
        self.btn_auth_page.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255, 255, 255, 10);
                border: 1px solid rgba(255, 255, 255, 15);
                border-radius: 10px;
                padding: 0 16px;
                color: rgba(255, 255, 255, 200);
                font-family: 'DM Sans';
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 18);
                color: white;
            }}
        """)
        try:
            self.btn_auth_page.clicked.disconnect()
        except Exception:
            pass
        self.btn_auth_page.clicked.connect(self._do_logout)
        self.btn_sync_profile.setVisible(True)

    def _show_logout_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{BG_1};color:{TEXT_HI};"
            f"border:1px solid {BORDER};border-radius:9px;padding:4px;font-size:11px;}}"
            f"QMenu::item{{padding:6px 18px;border-radius:5px;}}"
            f"QMenu::item:selected{{background:rgba(251, 113, 133, 51);}}"
        )
        email = self._user_info.get("email", "")
        if email:
            lbl = QAction(email, self); lbl.setEnabled(False)
            menu.addAction(lbl); menu.addSeparator()
        if not self._is_pro:
            act_up  = QAction("upgrade to pro ✦", self)
            act_up.triggered.connect(self._show_upgrade_dialog)
            menu.addAction(act_up)
            menu.addSeparator()
        act_fb  = QAction("send feedback", self);     act_fb.triggered.connect(self._open_feedback)
        act_out = QAction("log out", self);           act_out.triggered.connect(self._do_logout)
        menu.addAction(act_fb)
        menu.addSeparator()
        menu.addAction(act_out)
        menu.exec(self.btn_avatar.mapToGlobal(self.btn_avatar.rect().topLeft()))

    def _do_logout(self):
        logout_user()
        self._user_info = {}
        self._is_pro    = False
        self._refresh_pro_badge()
        self.btn_sync_profile.setVisible(False)
        
        # Reset avatar
        self.btn_avatar.set_user({})
        
        # Reset Analytics labels
        self.user_email_lbl.setText("Logged in as Guest")
        self.user_streak_lbl.setText("Connect to sync focus sessions")
        
        # Reset auth button
        self.btn_auth_page.setText("Sign In with Google")
        self.btn_auth_page.setStyleSheet(f"""
            QPushButton {{
                background: rgba(251, 113, 133, 20);
                color: {ACCENT};
                border: 1px solid {BORDER};
                border-radius: 10px;
                padding: 0 16px;
                font-size: 11px;
                font-family: 'DM Sans';
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: rgba(251, 113, 133, 40);
                color: white;
            }}
        """)
        try:
            self.btn_auth_page.clicked.disconnect()
        except Exception:
            pass
        self.btn_auth_page.clicked.connect(self._do_google_login)

    def _sync_pro_status(self):
        """Asynchronously check user's Pro status from Supabase to sync purchase status."""
        sub = self._user_info.get("id") if self._user_info else None
        if not sub:
            return
        
        def worker():
            from auth import get_supabase_client
            sb = get_supabase_client()
            if not sb:
                return
            try:
                result = sb.table("users").select("is_pro").eq("google_sub", sub).execute()
                rows = result.data
                if rows:
                    db_is_pro = rows[0].get("is_pro", False)
                    QTimer.singleShot(0, lambda: self._apply_synced_pro_status(db_is_pro))
            except Exception as e:
                print(f"[sync_pro] Failed: {e}")
                
        threading.Thread(target=worker, daemon=True).start()

    def _apply_synced_pro_status(self, db_is_pro: bool):
        if self._user_info and self._user_info.get("is_pro") != db_is_pro:
            print(f"[sync_pro] Pro status updated from DB: {db_is_pro}")
            self._user_info["is_pro"] = db_is_pro
            self._is_pro = db_is_pro
            save_cached_user(self._user_info)
            self._refresh_pro_badge()

    def _manual_sync_profile(self):
        self.btn_sync_profile.setText("syncing...")
        QApplication.processEvents()
        
        sub = self._user_info.get("id") if self._user_info else None
        if not sub:
            self.btn_sync_profile.setText("Sync Profile")
            return
            
        from auth import get_supabase_client
        sb = get_supabase_client()
        if not sb:
            self.btn_sync_profile.setText("Sync Profile")
            self._set_status("sync failed", "rgba(248,113,113,160)")
            return
            
        try:
            result = sb.table("users").select("is_pro").eq("google_sub", sub).execute()
            rows = result.data
            if rows:
                db_is_pro = rows[0].get("is_pro", False)
                self._user_info["is_pro"] = db_is_pro
                self._is_pro = db_is_pro
                save_cached_user(self._user_info)
                self._refresh_pro_badge()
                
                # Update stats widget if it exists
                if hasattr(self, 'stats_widget'):
                    self.stats_widget._is_pro = db_is_pro
                    self.stats_widget._load_stats()
                
                if db_is_pro:
                    self._set_status("pro synced ✓", GREEN)
                else:
                    self._set_status("synced ✓", GREEN)
            else:
                self._set_status("user not found", "rgba(248,113,113,160)")
        except Exception as e:
            print(f"[sync_pro] Manual sync failed: {e}")
            self._set_status("sync failed", "rgba(248,113,113,160)")
            
        self.btn_sync_profile.setText("Sync Profile")

    # ── Window plumbing ────────────────────────────────────────────────────────
    def _minimize_to_tray(self):
        self.hide()
        self.tray.showMessage("Goofy Focus", "Running in tray — click to restore.",
                              QSystemTrayIcon.MessageIcon.Information, 2000)

    def _toggle_maximized(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _show_from_tray(self):
        self.showNormal(); self.activateWindow(); self.raise_()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()

    def _on_tray_message_clicked(self):
        if self._update_url:
            from PyQt6.QtGui import QDesktopServices
            from PyQt6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl(self._update_url))
            self._update_url = None

    def _check_updates(self):
        """Asynchronously check for updates from a public configuration JSON file."""
        def worker():
            import urllib.request
            import urllib.error
            url = "https://raw.githubusercontent.com/arunkumarm-git/GoofyFocus/main/version.json"
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    latest = data.get("latest_version")
                    download_url = data.get("download_url", "https://arun-mass.itch.io/goofy-focus")
                    update_zip_url = data.get("update_zip_url", "https://github.com/arunkumarm-git/GoofyFocus/archive/refs/heads/main.zip")
                    
                    self._update_url = download_url
                    self._update_zip_url = update_zip_url
                    
                    if latest:
                        curr_parts = [int(x) for x in CURRENT_VERSION.split(".")]
                        late_parts = [int(x) for x in latest.split(".")]
                        print(f"[update_check] Local: {curr_parts}, Remote: {late_parts}")
                        if late_parts > curr_parts:
                            self.update_detected.emit(latest, download_url)
            except Exception as e:
                print(f"[update_check] Failed to check for updates: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def _notify_update(self, latest: str, download_url: str):
        print(f"[update_check] Triggering tray message for v{latest}...")
        self._update_url = download_url
        
        if hasattr(self, 'update_badge'):
            self.update_badge.setText(f"Update Available: v{latest} ⏳")
            self.update_badge.setVisible(True)
        if hasattr(self, 'anal_update_badge'):
            self.anal_update_badge.setText(f"Update Available: v{latest} ⏳")
            self.anal_update_badge.setVisible(True)

        self.tray.showMessage(
            "Update Available ⏳",
            f"Goofy Focus v{latest} is now available! Click this message to download.",
            QSystemTrayIcon.MessageIcon.Information,
            10000
        )

    def _start_auto_update(self):
        self.update_badge.setText("Downloading...")
        self.update_badge.setEnabled(False)
        if hasattr(self, 'anal_update_badge'):
            self.anal_update_badge.setText("Downloading...")
            self.anal_update_badge.setEnabled(False)
            
        def worker():
            import urllib.request
            import zipfile
            import tempfile
            import shutil
            import subprocess
            
            zip_url = getattr(self, '_update_zip_url', "https://github.com/arunkumarm-git/GoofyFocus/archive/refs/heads/main.zip")
            
            try:
                temp_dir = tempfile.mkdtemp()
                zip_path = os.path.join(temp_dir, "update.zip")
                
                # Download update zip
                req = urllib.request.Request(zip_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=30) as response, open(zip_path, 'wb') as out_file:
                    out_file.write(response.read())
                
                # Extract zip file
                extract_dir = os.path.join(temp_dir, "extract")
                os.makedirs(extract_dir, exist_ok=True)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                # Find source dir (accounting for GitHub root folder inside zip)
                items = os.listdir(extract_dir)
                if len(items) == 1 and os.path.isdir(os.path.join(extract_dir, items[0])):
                    src_dir = os.path.join(extract_dir, items[0])
                else:
                    src_dir = extract_dir
                
                # Current running dir and batch file path
                current_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
                batch_path = os.path.join(temp_dir, "install_update.bat")
                
                # Build startup command
                if getattr(sys, 'frozen', False):
                    start_cmd = f'start "" "{sys.executable}"'
                else:
                    script_path = os.path.abspath(sys.argv[0])
                    start_cmd = f'start "" "{sys.executable}" "{script_path}"'
                
                # Write Windows update batch script
                with open(batch_path, "w") as f:
                    f.write(f"""@echo off
title Goofy Focus Updater
echo Waiting for Goofy Focus to close...
timeout /t 2 /nobreak > nul
echo Copying new files to {current_dir}...
xcopy /s /y /i "{src_dir}\\*" "{current_dir}\\"
echo Restarting Goofy Focus...
cd /d "{current_dir}"
{start_cmd}
echo Clean up...
rd /s /q "{src_dir}"
del "%~f0"
""")
                
                # Start batch script in background detached
                subprocess.Popen(["cmd.exe", "/c", batch_path], creationflags=subprocess.CREATE_NO_WINDOW)
                self.update_status.emit(True, "Updating...")
            except Exception as e:
                print(f"[auto_update] Error: {e}")
                self.update_status.emit(False, str(e))
                
        threading.Thread(target=worker, daemon=True).start()

    def _on_update_status(self, success: bool, message: str):
        if success:
            self.update_badge.setText("Restarting...")
            if hasattr(self, 'anal_update_badge'):
                self.anal_update_badge.setText("Restarting...")
            QTimer.singleShot(500, self._quit_app)
        else:
            self.update_badge.setText("Update Failed ❌")
            self.update_badge.setEnabled(True)
            if hasattr(self, 'anal_update_badge'):
                self.anal_update_badge.setText("Update Failed ❌")
                self.anal_update_badge.setEnabled(True)
            self._set_status(f"Update failed: {message}", "rgba(248,113,113,160)")

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e): self._drag_pos = None

    def changeEvent(self, event):
        super().changeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        try:
            apply_blur_effect(int(self.winId()))
        except Exception as e:
            print("[blur] showEvent failed to apply blur:", e)

    def _quit_app(self): self.tray.hide(); QApplication.quit()
    def closeEvent(self, event): self.tray.hide(); event.accept(); QApplication.quit()

    # ── Paint ──────────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 16, 16)

        # Clip all drawing to the rounded window path
        p.setClipPath(path)

        # 0. Translucent base glass gradient wash to let the desktop bleed through
        dark_glass = QLinearGradient(0, 0, 0, self.height())
        dark_glass.setColorAt(0.0, QColor(25, 20, 30, 30))    # ~11% opacity top
        dark_glass.setColorAt(1.0, QColor(15, 12, 18, 50))    # ~19% bottom
        p.fillPath(path, QBrush(dark_glass))

        # 1. Subtle diagonal glass highlight for depth
        glass_highlight = QLinearGradient(0, 0, self.width(), self.height())
        glass_highlight.setColorAt(0.0, QColor(255, 255, 255, 10))
        glass_highlight.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillPath(path, QBrush(glass_highlight))

        # 3. Draw frosted glass noise texture (visible grain)
        if hasattr(self, 'noise_pixmap') and self.noise_pixmap:
            p.drawTiledPixmap(self.rect(), self.noise_pixmap)

        # Disable clipping for edge-glow and border drawing
        p.setClipping(False)

        # 4. Subtle top-edge glow — accent fades in from centre
        glow = QLinearGradient(0, 0, self.width(), 0)
        glow.setColorAt(0.0, QColor(0, 0, 0, 0))
        glow.setColorAt(0.1, QColor(0, 0, 0, 0))
        glow.setColorAt(0.3, QColor(251, 113, 133, 140))
        glow.setColorAt(0.7, QColor(167, 139, 250, 90))
        glow.setColorAt(0.9, QColor(0, 0, 0, 0))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        
        gp = QPainterPath()
        gp.addRect(QRectF(self.width() * 0.1, 0, self.width() * 0.8, 1.2))
        p.fillPath(gp, QBrush(glow))

        # 5. Window border — subtle glass stroke commented out to remove blending corner artifacts
        # p.setPen(QPen(QColor(255, 255, 255, 45), 1.2))
        # p.drawPath(path)
        p.end()


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setOrganizationName("GoofyFocus")
    app.setApplicationName("GoofyFocus")
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

