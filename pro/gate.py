# pro/gate.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QApplication, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QTimer, QRectF, QUrl, QObject, pyqtSignal, QLocale
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QLinearGradient, QBrush, QPen, QDesktopServices, QFont
from auth import get_supabase_client, save_cached_user
import requests
import os
import json
import urllib.request
import threading
from dotenv import load_dotenv
from assets import get_base_path
load_dotenv(os.path.join(get_base_path(), ".env"))

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
        self.setFixedSize(380, 550)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.resolved_currency = "USD"
        self.resolved_amount = 10.0
        
        # Soft premium drop shadow - stabilized to 15 blur / 3 offset to prevent UpdateLayeredWindowIndirect failure on Windows
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(15)
        self.shadow.setColor(QColor(0, 0, 0, 160))
        self.shadow.setOffset(0, 3)
        self.setGraphicsEffect(self.shadow)
        
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 24)
        root.setSpacing(10)

        # Title
        tb = QHBoxLayout()
        title = QLabel("support goofyfocus")
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

        # Description
        desc = QLabel(
            "GoofyFocus is now 100% free and open-source! All premium features are unlocked for everyone. "
            "If you love using this app, please consider supporting its development with a donation. "
            "Every contribution keeps the project alive and help us add more features! 💖"
        )
        desc.setWordWrap(True)
        desc.setFont(QFont("DM Sans", 10))
        desc.setStyleSheet(f"color: {TEXT_MID}; background: transparent; line-height: 1.4;")
        root.addWidget(desc)

        # Unlocked features list
        features_header = QLabel("Premium features are FREE:")
        features_header.setFont(QFont("DM Sans", 11, QFont.Weight.Bold))
        features_header.setStyleSheet(f"color: {ACCENT_2}; background: transparent; padding-top: 6px;")
        root.addWidget(features_header)

        features = [
            "✦ Focus stats dashboard",
            "✦ Session history sync",
            "✦ Custom break messages",
            "✦ Unlimited GIF packs",
            "✦ Custom ambient sounds",
            "✦ Session cycle control"
        ]
        for f in features:
            lbl = QLabel(f)
            lbl.setFont(QFont("DM Sans", 9))
            lbl.setStyleSheet(f"color: {TEXT_MID}; background: transparent; padding: 0px;")
            root.addWidget(lbl)

        root.addStretch()

        # Donation Selector Section
        don_sec = QVBoxLayout()
        don_sec.setSpacing(8)
        
        don_header = QLabel("Choose donation amount:")
        don_header.setFont(QFont("DM Sans", 10, QFont.Weight.Bold))
        don_header.setStyleSheet(f"color: {TEXT_LOW}; background: transparent;")
        don_sec.addWidget(don_header)
        
        # Row for input and currency
        input_row = QHBoxLayout()
        input_row.setSpacing(6)
        
        self.currency_lbl = QLabel("$")
        self.currency_lbl.setFont(QFont("DM Sans", 14, QFont.Weight.Bold))
        self.currency_lbl.setStyleSheet(f"color: {TEXT_HI}; background: transparent;")
        input_row.addWidget(self.currency_lbl)
        
        self.amount_input = QLineEdit("10.00")
        self.amount_input.setFixedHeight(36)
        self.amount_input.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(255, 255, 255, 13);
                border: 1px solid rgba(255, 255, 255, 31);
                border-radius: 8px;
                color: white;
                font-family: 'DM Mono', monospace;
                font-size: 14px;
                font-weight: bold;
                padding: 4px 10px;
            }}
            QLineEdit:hover, QLineEdit:focus {{
                border-color: {ACCENT};
                background: rgba(255, 255, 255, 20);
            }}
        """)
        # Allow numbers and decimals only - enforced with US locale to prevent dot/comma separators mixup
        from PyQt6.QtGui import QDoubleValidator
        validator = QDoubleValidator(1.0, 99999.0, 2, self)
        validator.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.amount_input.setValidator(validator)
        self.amount_input.textChanged.connect(lambda: self._update_donate_button_text())
        input_row.addWidget(self.amount_input, 1)
        don_sec.addLayout(input_row)
        
        # Row for quick select buttons
        quick_row = QHBoxLayout()
        quick_row.setSpacing(8)
        
        self.quick_amounts = [5, 10, 25, 50]
        self.quick_btns = []
        for val in self.quick_amounts:
            btn = QPushButton(f"${val}")
            btn.setFixedHeight(26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(255, 255, 255, 10);
                    color: {TEXT_MID};
                    border: 1px solid rgba(255, 255, 255, 15);
                    border-radius: 6px;
                    font-family: 'DM Sans';
                    font-size: 10px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background: rgba(255, 255, 255, 20);
                    color: white;
                    border-color: {ACCENT};
                }}
            """)
            btn.clicked.connect(lambda checked, v=val: self._set_quick_amount(v))
            quick_row.addWidget(btn)
            self.quick_btns.append(btn)
            
        don_sec.addLayout(quick_row)
        root.addLayout(don_sec)
        root.addSpacing(6)

        # Buy Button
        self.btn_buy = QPushButton("support goofyfocus — lifetime")
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
        self.btn_buy.clicked.connect(self._open_checkout)
        root.addWidget(self.btn_buy)

        self.status = QLabel("")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setFont(QFont("DM Mono", 10))
        self.status.setStyleSheet(f"color: {TEXT_LOW}; background: transparent;")
        root.addWidget(self.status)
        
        # Initialize default amount to $10.00
        self._set_quick_amount(10)

    def _set_quick_amount(self, value):
        self.amount_input.setText(f"{value:.2f}")
        self._update_donate_button_text()

    def _update_donate_button_text(self):
        amount_text = self.amount_input.text().strip()
        try:
            val = float(amount_text)
            self.btn_buy.setText(f"Donate ${val:.2f} via PayPal")
        except Exception:
            self.btn_buy.setText("Donate via PayPal")

    def _open_checkout(self):
        try:
            paypal_email = os.getenv("PAYPAL_BUSINESS_EMAIL")
            if not paypal_email:
                paypal_email = "your-paypal-business-email@example.com"
            
            paypal_mode = os.getenv("PAYPAL_MODE", "live").lower()
            base_url = "https://www.paypal.com/cgi-bin/webscr" if paypal_mode == "live" else "https://www.sandbox.paypal.com/cgi-bin/webscr"
            
            email = self.main_window._user_info.get("email") if self.main_window and self.main_window._user_info else ""
            sub = self.main_window._user_info.get("id") if self.main_window and self.main_window._user_info else ""
            
            currency = "USD"
            
            # Read amount from input field
            try:
                amount = float(self.amount_input.text().strip())
            except Exception:
                amount = 10.00
            
            amount_str = f"{amount:.2f}"
                
            import urllib.parse
            params = {
                "cmd": "_xclick",
                "business": paypal_email,
                "item_name": "GoofyFocus Support & Donation",
                "amount": amount_str,
                "currency_code": currency,
                "no_shipping": "1",
                "no_note": "1",
            }
            if sub:
                params["custom"] = sub
            if email:
                params["email"] = email
                
            supabase_url = os.getenv("SUPABASE_URL")
            if supabase_url:
                params["notify_url"] = f"{supabase_url}/functions/v1/paypal-webhook"
                
            url = base_url + "?" + urllib.parse.urlencode(params)
            print(f"[checkout] Opening URL: {url}")
            QDesktopServices.openUrl(QUrl(url))
        except Exception as e:
            print(f"[checkout error] Failed to open PayPal URL: {e}")
            import traceback
            traceback.print_exc()


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

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if e.position().y() < 40:
                self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            else:
                super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.MouseButton.LeftButton and hasattr(self, '_drag_pos') and self._drag_pos:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
        super().mouseReleaseEvent(e)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
