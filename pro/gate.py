# pro/gate.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QApplication, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QTimer, QRectF, QUrl, QObject, pyqtSignal
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

def currency_from_country(country_code):
    mapping = {
        "IN": "INR",
        "US": "USD",
        "GB": "GBP",
        "JP": "JPY",
        "CA": "CAD",
        "AU": "AUD",
        "NZ": "NZD",
        "SE": "SEK",
        "CH": "CHF",
        "CN": "CNY",
        "AT": "EUR", "BE": "EUR", "CY": "EUR", "EE": "EUR", "FI": "EUR", 
        "FR": "EUR", "DE": "EUR", "GR": "EUR", "IE": "EUR", "IT": "EUR", 
        "LV": "EUR", "LT": "EUR", "LU": "EUR", "MT": "EUR", "NL": "EUR", 
        "PT": "EUR", "SK": "EUR", "SI": "EUR", "ES": "EUR"
    }
    return mapping.get(country_code.upper(), "INR")

class CurrencyWorker(QObject):
    finished = pyqtSignal(str, float, str)  # currency_code, converted_value, formatted_text

    def __init__(self, base_price_inr=1080):
        super().__init__()
        self.base_price_inr = base_price_inr

    def run(self):
        currency_code = "INR"
        rate = 1.0
        symbol = "₹"
        
        # 1. Geolocation lookup to determine user currency
        # Try ip-api.com first as it does not return 403 blocks for standard client calls
        try:
            req = urllib.request.Request(
                "http://ip-api.com/json/",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode())
                country_code = data.get("countryCode", "IN")
                currency_code = currency_from_country(country_code)
        except Exception:
            # Silent fallback to ipapi.co
            try:
                req = urllib.request.Request(
                    "https://ipapi.co/json/",
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                with urllib.request.urlopen(req, timeout=3) as response:
                    data = json.loads(response.read().decode())
                    currency_code = data.get("currency", "INR")
            except Exception:
                currency_code = "INR"

        symbols = {
            "INR": "₹",
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "JPY": "¥",
            "CAD": "C$",
            "AUD": "A$",
            "CHF": "CHF ",
            "CNY": "¥",
            "SEK": "kr ",
            "NZD": "NZ$",
        }
        symbol = symbols.get(currency_code, currency_code + " ")

        # 2. Exchange rate fetch
        if currency_code != "INR":
            try:
                url = f"https://open.er-api.com/v6/latest/INR"
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                with urllib.request.urlopen(req, timeout=3) as response:
                    data = json.loads(response.read().decode())
                    if data.get("result") == "success":
                        rates = data.get("rates", {})
                        rate = rates.get(currency_code, 1.0)
            except Exception as e:
                print(f"[currency] Exchange rate fetch failed: {e}")
                # Common fallback rates if API is down
                fallbacks = {
                    "USD": 0.012,
                    "EUR": 0.011,
                    "GBP": 0.0094,
                    "CAD": 0.016,
                    "AUD": 0.018,
                }
                rate = fallbacks.get(currency_code, 1.0)
                if rate == 1.0:
                    currency_code = "INR"
                    symbol = "₹"

        converted = self.base_price_inr * rate
        
        # Nicely formatted currency output
        if currency_code == "INR":
            formatted = "₹1,080"
        elif currency_code == "USD":
            val = round(converted)
            if val < converted:
                val += 0.99
            else:
                val -= 0.01
            formatted = f"${val:.2f}"
        elif currency_code in ["EUR", "GBP", "CAD", "AUD"]:
            val = round(converted) - 0.01
            formatted = f"{symbol}{val:.2f}"
        else:
            formatted = f"{symbol}{round(converted):,}"

        self.finished.emit(currency_code, converted, formatted)

class UpgradeDialog(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setFixedSize(360, 420)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Default currency fallback until resolved
        self.resolved_currency = "INR"
        self.resolved_amount = 1080.0
        
        # Soft premium drop shadow
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(35)
        self.shadow.setColor(QColor(0, 0, 0, 160))
        self.shadow.setOffset(0, 8)
        self.setGraphicsEffect(self.shadow)
        
        self._build_ui()

        # Start currency worker thread
        self.currency_worker = CurrencyWorker(1080)
        self.currency_thread = threading.Thread(target=self.currency_worker.run)
        self.currency_worker.finished.connect(self._on_currency_resolved)
        self.currency_thread.start()

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
        self.btn_buy = QPushButton("get pro — ₹1,080 lifetime")
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

    def _on_currency_resolved(self, code, val, formatted_text):
        self.btn_buy.setText(f"get pro — {formatted_text} lifetime")
        self.resolved_currency = code
        self.resolved_amount = val

    def _open_checkout(self):
        try:
            paypal_email = os.getenv("PAYPAL_BUSINESS_EMAIL")
            if not paypal_email:
                paypal_email = "your-paypal-business-email@example.com"
            
            paypal_mode = os.getenv("PAYPAL_MODE", "live").lower()
            base_url = "https://www.paypal.com/cgi-bin/webscr" if paypal_mode == "live" else "https://www.sandbox.paypal.com/cgi-bin/webscr"
            
            email = self.main_window._user_info.get("email") if self.main_window and self.main_window._user_info else ""
            sub = self.main_window._user_info.get("id") if self.main_window and self.main_window._user_info else ""
            
            currency = getattr(self, "resolved_currency", "INR")
            amount = getattr(self, "resolved_amount", 1080.0)
            
            # PayPal does not support INR for standard checkouts. Convert to USD fallback.
            if currency == "INR":
                currency = "USD"
                amount = 12.99
                
            if currency == "JPY":
                amount_str = f"{int(round(amount))}"
            else:
                amount_str = f"{amount:.2f}"
                
            import urllib.parse
            params = {
                "cmd": "_xclick",
                "business": paypal_email,
                "item_name": "GoofyFocus Pro Lifetime",
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
