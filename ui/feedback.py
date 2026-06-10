# ui/feedback.py
import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QApplication, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QLinearGradient, QBrush, QPen, QFont
from auth import get_supabase_client

# ── Design tokens (matching app.py) ──────────────────
BG_0      = "#0f0d0e"
BG_1      = "#171415"
ACCENT     = "#FB7185"
ACCENT_2   = "#A78BFA"
TEXT_HI    = "rgba(255,255,255,255)"
TEXT_MID   = "rgba(255,255,255,190)"
TEXT_LOW   = "rgba(255,255,255,120)"
BORDER     = "rgba(251, 113, 133, 40)"

# ──────────────────────────────────────────────
# FEEDBACK WINDOW
# ──────────────────────────────────────────────
class FeedbackWindow(QWidget):
    def __init__(self, user_email: str = "", parent=None):
        super().__init__(parent)
        self.user_email = user_email
        self.setWindowTitle("Send Feedback")
        self.setFixedSize(380, 420)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._rating = 0
        
        # Soft premium drop shadow
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(35)
        self.shadow.setColor(QColor(0, 0, 0, 160))
        self.shadow.setOffset(0, 8)
        self.setGraphicsEffect(self.shadow)
        
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # Title bar
        tb = QHBoxLayout()
        title = QLabel("feedback")
        title.setFont(QFont("DM Mono", 12))
        title.setStyleSheet(f"color: {TEXT_HI}; background: transparent;")
        tb.addWidget(title)
        tb.addStretch()
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {TEXT_LOW}; border: none; font-size: 18px; }} "
            f"QPushButton:hover {{ color: {TEXT_HI}; }}")
        close_btn.clicked.connect(self.close)
        tb.addWidget(close_btn)
        root.addLayout(tb)

        # Star rating
        rating_lbl = QLabel("how's your experience?")
        rating_lbl.setFont(QFont("DM Sans", 11))
        rating_lbl.setStyleSheet(f"color: {TEXT_MID}; background: transparent;")
        root.addWidget(rating_lbl)

        stars_row = QHBoxLayout()
        self._star_btns = []
        for i in range(1, 6):
            s = QPushButton("☆")
            s.setFixedSize(40, 40)
            s.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {TEXT_LOW}; border: none; font-size: 24px; }} "
                f"QPushButton:hover {{ color: {ACCENT_2}; }}")
            s.clicked.connect(lambda _, r=i: self._set_rating(r))
            stars_row.addWidget(s)
            self._star_btns.append(s)
        stars_row.addStretch()
        root.addLayout(stars_row)

        # Message box
        msg_lbl = QLabel("tell us more (optional)")
        msg_lbl.setFont(QFont("DM Sans", 11))
        msg_lbl.setStyleSheet(f"color: {TEXT_MID}; background: transparent;")
        root.addWidget(msg_lbl)

        self.msg_box = QTextEdit()
        self.msg_box.setPlaceholderText("what could be better?")
        self.msg_box.setFixedHeight(120)
        self.msg_box.setStyleSheet(f"""
            QTextEdit {{
                background: rgba(255, 255, 255, 13);
                border: 1px solid rgba(255, 255, 255, 31);
                border-radius: 10px;
                padding: 10px;
                color: {TEXT_HI};
                font-size: 12px;
                font-family: 'DM Sans';
            }}
            QTextEdit:focus {{ border-color: {ACCENT}; background: rgba(255, 255, 255, 20); }}
        """)
        root.addWidget(self.msg_box)
 
        # Submit button
        self.btn_submit = QPushButton("send feedback")
        self.btn_submit.setFixedHeight(40)
        self.btn_submit.setStyleSheet(f"""
            QPushButton {{
                background: rgba(251, 113, 133, 20);
                color: {ACCENT};
                border: 1px solid rgba(255, 255, 255, 31);
                border-radius: 12px;
                padding: 8px;
                font-size: 13px;
                font-family: 'DM Sans';
                font-weight: 600;
            }}
            QPushButton:hover {{ background: rgba(251, 113, 133, 40); color: white; border-color: {ACCENT_2}; }}
        """)
        self.btn_submit.clicked.connect(self._submit)
        root.addWidget(self.btn_submit)

        self.status_lbl = QLabel("")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setFont(QFont("DM Mono", 10))
        self.status_lbl.setStyleSheet(f"color: {TEXT_LOW}; background: transparent;")
        root.addWidget(self.status_lbl)

    def _set_rating(self, rating: int):
        self._rating = rating
        for i, btn in enumerate(self._star_btns):
            btn.setText("★" if i < rating else "☆")
            btn.setStyleSheet(
                f"QPushButton {{ background: transparent; border: none; font-size: 24px; "
                f"color: {'#FB7185' if i < rating else 'rgba(255,255,255,51)'}; }}"
                f"QPushButton:hover {{ color: #A78BFA; }}"
            )

    def _submit(self):
        if self._rating == 0:
            self.status_lbl.setText("please select a rating ★")
            return

        self.btn_submit.setText("sending...")
        QApplication.processEvents()

        try:
            sb = get_supabase_client()
            if not sb:
                self.status_lbl.setText("couldn't connect")
                self.btn_submit.setText("send feedback")
                return

            sb.table("feedback").insert({
                "email":   self.user_email or "anonymous",
                "rating":  self._rating,
                "message": self.msg_box.toPlainText().strip(),
            }, returning="minimal").execute()

            self.status_lbl.setText("✓ thanks for your feedback!")
            self.btn_submit.setText("sent!")
            QTimer.singleShot(2000, self.close)

        except Exception as e:
            self.status_lbl.setText("error sending")
            self.btn_submit.setText("send feedback")
            print(f"Feedback error: {e}")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 20, 20)
        
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
