# pro/gate.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QApplication
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QLinearGradient, QBrush, QPen, QDesktopServices, QFont
from PyQt6.QtCore import QUrl
from auth import get_supabase_client, save_cached_user
import requests

# ── Design tokens (matching app.py) ──────────────────
BG_0      = "#0f0d0e"
BG_1      = "#171415"
ACCENT     = "#FB7185"
ACCENT_2   = "#A78BFA"
TEXT_HI    = "rgba(255,255,255,255)"
TEXT_MID   = "rgba(255,255,255,190)"
TEXT_LOW   = "rgba(255,255,255,120)"
BORDER     = "rgba(251, 113, 133, 40)"

class UpgradeDialog(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setFixedSize(360, 520)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Soft premium drop shadow
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(35)
        self.shadow.setColor(QColor(0, 0, 0, 160))
        self.shadow.setOffset(0, 8)
        self.setGraphicsEffect(self.shadow)
        
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 30, 30, 30)
        root.setSpacing(14)

        # Title
        tb = QHBoxLayout()
        title = QLabel("unlock pro")
        title.setFont(QFont("DM Mono", 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {ACCENT}; background: transparent;")
        tb.addWidget(title)
        tb.addStretch()
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {TEXT_LOW}; border: none; font-size: 20px; }} "
            f"QPushButton:hover {{ color: {TEXT_HI}; }}")
        close_btn.clicked.connect(self.close)
        tb.addWidget(close_btn)
        root.addLayout(tb)

        # Features List
        features = [
            "✦ Focus stats dashboard",
            "✦ Session history sync",
            "✦ Custom break messages",
            "✦ Unlimited GIF packs",
            "✦ Custom ambient sounds",
            "✦ Session cycle control",
            "✦ Early access to features"
        ]
        for f in features:
            lbl = QLabel(f)
            lbl.setFont(QFont("DM Sans", 11))
            lbl.setStyleSheet(f"color: {TEXT_MID}; background: transparent; padding: 2px 0px;")
            root.addWidget(lbl)

        root.addStretch()

        # Buy Button
        self.btn_buy = QPushButton("get pro — $9 lifetime")
        self.btn_buy.setFixedHeight(44)
        self.btn_buy.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 {ACCENT}, stop:1 {ACCENT_2});
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 13px;
                font-family: 'DM Sans';
                font-weight: 600;
            }}
            QPushButton:hover {{ background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1, stop:0 #ff8da1, stop:1 #bfa3ff); color: white; }}
        """)
        self.btn_buy.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://screenbreak.lemonsqueezy.com/checkout/buy/2d24af9e-4d6a-41b9-aa06-c37525f76955")))
        root.addWidget(self.btn_buy)

        # License Activation
        key_layout = QHBoxLayout()
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Already have a key?")
        self.key_input.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(255, 255, 255, 13);
                border: 1px solid rgba(255, 255, 255, 31);
                border-radius: 8px;
                padding: 8px 12px;
                color: {TEXT_HI};
                font-size: 11px;
                font-family: 'DM Sans';
            }}
            QLineEdit:focus {{ border-color: {ACCENT}; background: rgba(255, 255, 255, 20); }}
        """)
        key_layout.addWidget(self.key_input)

        self.btn_activate = QPushButton("activate")
        self.btn_activate.setFixedHeight(34)
        self.btn_activate.setStyleSheet(f"""
            QPushButton {{
                background: rgba(251, 113, 133, 20);
                color: {ACCENT};
                border: 1px solid rgba(255, 255, 255, 31);
                border-radius: 8px;
                padding: 0 16px;
                font-size: 11px;
                font-family: 'DM Sans';
                font-weight: 600;
            }}
            QPushButton:hover {{ background: rgba(251, 113, 133, 40); color: white; }}
        """)
        self.btn_activate.clicked.connect(self._try_activate)
        key_layout.addWidget(self.btn_activate)
        
        root.addLayout(key_layout)

        self.status = QLabel("")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setFont(QFont("DM Mono", 10))
        self.status.setStyleSheet(f"color: {TEXT_LOW}; background: transparent;")
        root.addWidget(self.status)

    def _try_activate(self):
        key = self.key_input.text().strip()
        sub = self.main_window._user_info.get("id") if self.main_window._user_info else None
        
        if not sub:
            self.status.setText("please log in first via the main window")
            return
            
        self.btn_activate.setText("...")
        QApplication.processEvents()
        
        try:
            # 1. Activate the key via LemonSqueezy API
            ls_url = "https://api.lemonsqueezy.com/v1/licenses/activate"
            payload = {
                "license_key": key,
                "instance_name": sub 
            }
            
            res = requests.post(ls_url, data=payload, headers={"Accept": "application/json"})
            data = res.json()
            
            # Check if successfully activated OR if they are re-entering a key they already activated
            if data.get("activated") or data.get("error") == "License key already activated.":
                
                # Update Supabase
                sb = get_supabase_client()
                sb.table("users").update({"is_pro": True}).eq("google_sub", sub).execute()
                
                # Update main window UI natively
                self.main_window._is_pro = True
                self.main_window._user_info["is_pro"] = True
                self.main_window._refresh_pro_badge()
                
                #Update the local cache so it survives app restart! <---
                save_cached_user(self.main_window._user_info)
                
                self.status.setStyleSheet("color: #34d399; font-size: 11px; font-weight: bold;")
                self.status.setText("✓ pro activated! welcome!")
                QTimer.singleShot(2000, self.close)
            else:
                self.btn_activate.setText("activate")
                self.status.setStyleSheet("color: #f87171; font-size: 10px;")
                self.status.setText(data.get("error", "invalid or already used key"))
                
        except Exception as e:
            self.btn_activate.setText("activate")
            self.status.setText("couldn't verify — check connection")
            print(f"[activate error] {e}")

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
