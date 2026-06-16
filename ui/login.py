# ui/login.py
import os
import threading
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QApplication, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QTimer, QRectF, pyqtSignal, QSize
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QLinearGradient, QBrush, QPen, QFont, QIcon
from auth import perform_login
from assets import ASSETS_DIR

# ── Design tokens (matching app.py) ──────────────────
BG_0      = "#0f0d0e"
BG_1      = "#171415"
ACCENT     = "#FB7185"
ACCENT_2   = "#A78BFA"
TEXT_HI    = "rgba(255,255,255,255)"
TEXT_MID   = "rgba(255,255,255,190)"
TEXT_LOW   = "rgba(255,255,255,120)"
BORDER     = "rgba(251, 113, 133, 40)"

class LoginDialog(QDialog):
    login_completed = pyqtSignal(dict)
    login_failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sign In to Goofy Focus")
        self.setFixedSize(360, 420)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(15)
        self.shadow.setColor(QColor(0, 0, 0, 160))
        self.shadow.setOffset(0, 3)
        self.setGraphicsEffect(self.shadow)
        
        self.user_info = None
        self._drag_pos = None
        self._build_ui()
        
        self.login_completed.connect(self._on_login_completed)
        self.login_failed.connect(self._on_login_failed)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 30, 30, 30)
        root.setSpacing(18)

        # Title / Header
        tb = QHBoxLayout()
        title = QLabel("goofy focus")
        title.setFont(QFont("DM Mono", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ACCENT}; background: transparent;")
        tb.addWidget(title)
        tb.addStretch()
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {TEXT_LOW}; border: none; font-size: 20px; }} "
            f"QPushButton:hover {{ color: {TEXT_HI}; }}")
        close_btn.clicked.connect(self.reject)
        tb.addWidget(close_btn)
        root.addLayout(tb)

        # Description
        desc_title = QLabel("Sync Focus Progress")
        desc_title.setFont(QFont("DM Sans", 14, QFont.Weight.Bold))
        desc_title.setStyleSheet(f"color: {TEXT_HI}; background: transparent;")
        root.addWidget(desc_title)

        desc_body = QLabel("Log in with your Google account to sync your focus sessions, settings, and track your stats across multiple devices. GoofyFocus is 100% free and all features are unlocked by default!")
        desc_body.setFont(QFont("DM Sans", 10))
        desc_body.setStyleSheet(f"color: {TEXT_MID}; background: transparent; line-height: 1.4;")
        desc_body.setWordWrap(True)
        root.addWidget(desc_body)

        root.addStretch()

        # Sign In Button (Google official styling - Jakob's Law)
        self.btn_login = QPushButton("Sign in with Google")
        self.btn_login.setFixedHeight(40)
        icon_path = os.path.join(ASSETS_DIR, "icons", "google.png")
        if os.path.exists(icon_path):
            self.btn_login.setIcon(QIcon(icon_path))
            self.btn_login.setIconSize(QSize(18, 18))
        self.btn_login.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #1F1F1F;
                border: 1px solid #747775;
                border-radius: 4px;
                font-size: 14px;
                font-family: 'Roboto', 'Segoe UI', sans-serif;
                font-weight: 500;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #F8F9FA;
                border-color: #747775;
            }
            QPushButton:pressed {
                background-color: #F1F3F4;
            }
            QPushButton:disabled {
                background-color: #FFFFFF;
                color: #1F1F1F;
                border-color: #E3E3E3;
                opacity: 0.38;
            }
        """)
        self.btn_login.clicked.connect(self._do_login)
        root.addWidget(self.btn_login)

        # Status text
        self.status = QLabel("")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setFont(QFont("DM Mono", 10))
        self.status.setStyleSheet(f"color: {TEXT_LOW}; background: transparent;")
        root.addWidget(self.status)

    def _do_login(self):
        self.btn_login.setText("opening browser...")
        self.btn_login.setEnabled(False)
        self.status.setText("Please complete login in the browser window.")
        
        def worker():
            try:
                info = perform_login()
                self.login_completed.emit(info)
            except Exception as e:
                self.login_failed.emit(str(e))
                
        threading.Thread(target=worker, daemon=True).start()

    def _on_login_completed(self, info: dict):
        self.user_info = info
        self.btn_login.setEnabled(True)
        self.btn_login.setText("Sign in with Google")
        self.status.setText("✓ Login successful!")
        QTimer.singleShot(800, self.accept)

    def _on_login_failed(self, error_msg: str):
        self.btn_login.setEnabled(True)
        self.btn_login.setText("Sign in with Google")
        self.status.setText("✗ Login failed. Please try again.")
        print(f"[LoginDialog] Error: {error_msg}")

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if e.position().y() < 40:
                self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            else:
                super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
        super().mouseReleaseEvent(e)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 16, 16)
        
        # Opaque dark gradient fill
        bg = QLinearGradient(0, 0, 0, self.height())
        bg.setColorAt(0, QColor("#1D1822"))
        bg.setColorAt(1, QColor("#110E14"))
        p.fillPath(path, QBrush(bg))
        
        # Glass double-highlight border
        border_grad = QLinearGradient(0, 0, self.width(), self.height())
        border_grad.setColorAt(0.0, QColor(255, 255, 255, 60))
        border_grad.setColorAt(1.0, QColor(255, 255, 255, 10))
        p.setPen(QPen(border_grad, 1.2))
        p.drawPath(path)
        p.end()
