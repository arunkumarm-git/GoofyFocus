# pro/messages.py
import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QLineEdit, QListWidgetItem, QApplication
from PyQt6.QtCore import Qt, QRectF, QSettings
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QLinearGradient, QBrush, QPen, QFont

# ── Design tokens (matching app.py) ──────────────────
BG_0      = "#161514"
BG_1      = "#1c1b19"
ACCENT     = "#849d8a"
TEXT_HI    = "rgba(255,255,255,235)"
TEXT_MID   = "rgba(255,255,255,140)"
TEXT_LOW   = "rgba(255,255,255,76)"
BORDER     = "rgba(255,255,255,20)"

class CustomMessagesWindow(QWidget):
    def __init__(self, is_pro: bool, parent=None):
        super().__init__(parent)
        self._is_pro = is_pro
        self.setFixedSize(540, 480)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build_ui()
        self._load_messages()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # Title bar
        tb = QHBoxLayout()
        title = QLabel("custom messages")
        title.setFont(QFont("DM Mono", 12))
        title.setStyleSheet(f"color: {TEXT_HI}; background: transparent;")
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

        columns = QHBoxLayout()
        self.short_list = self._build_column(columns, "Short Break")
        self.long_list  = self._build_column(columns, "Long Break")
        root.addLayout(columns)
        
        save_btn = QPushButton("save messages")
        save_btn.setFixedHeight(38)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(132,157,138,38);
                color: rgba(220,190,255,230);
                border: 1px solid rgba(132,157,138,64);
                border-radius: 10px;
                font-size: 12px;
                font-family: 'DM Sans';
                font-weight: 500;
            }}
            QPushButton:hover {{ background: rgba(132,157,138,64); color: white; }}
        """)
        save_btn.clicked.connect(self._save_messages)
        root.addWidget(save_btn)

    def _build_column(self, parent_layout, title_text):
        col = QVBoxLayout()
        col.setSpacing(8)
        
        lbl = QLabel(title_text)
        lbl.setFont(QFont("DM Mono", 9))
        lbl.setStyleSheet(f"color: {ACCENT}; background: transparent;")
        col.addWidget(lbl)

        list_w = QListWidget()
        list_w.setStyleSheet(f"""
            QListWidget {{ 
                background: rgba(255,255,255,8); 
                border: 1px solid {BORDER}; 
                border-radius: 8px; 
                padding: 4px; 
                color: {TEXT_MID}; 
                font-size: 11px;
                font-family: 'DM Sans';
            }}
            QListWidget::item {{ padding: 6px; border-bottom: 1px solid rgba(255,255,255,5); }}
            QListWidget::item:selected {{ background: rgba(132,157,138,38); color: {TEXT_HI}; border-radius: 4px; }}
        """)
        col.addWidget(list_w)

        input_style = f"background: rgba(255,255,255,13); border: 1px solid {BORDER}; border-radius: 6px; padding: 6px 10px; color: {TEXT_HI}; font-size: 11px; font-family: 'DM Sans';"
        head_input = QLineEdit()
        head_input.setPlaceholderText("Headline (e.g. stretch)")
        head_input.setStyleSheet(input_style)
        col.addWidget(head_input)

        sub_input = QLineEdit()
        sub_input.setPlaceholderText("Subtitle (e.g. touch toes)")
        sub_input.setStyleSheet(input_style)
        col.addWidget(sub_input)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("add" if self._is_pro else "🔒 pro")
        btn_add.setStyleSheet(f"QPushButton {{ background: rgba(132,157,138,38); color: {ACCENT}; border-radius: 6px; padding: 6px; font-size: 11px; font-family: 'DM Sans'; }} QPushButton:hover {{ background: rgba(132,157,138,64); }}")
        
        btn_del = QPushButton("delete")
        btn_del.setStyleSheet(f"QPushButton {{ background: rgba(255,255,255,13); color: {TEXT_LOW}; border-radius: 6px; padding: 6px; font-size: 11px; font-family: 'DM Sans'; }} QPushButton:hover {{ color: {TEXT_MID}; }}")
        
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_del)
        col.addLayout(btn_row)

        parent_layout.addLayout(col)

        if not self._is_pro:
            btn_add.setEnabled(False); btn_del.setEnabled(False)
            head_input.setEnabled(False); sub_input.setEnabled(False)
        else:
            btn_add.clicked.connect(lambda: self._add_msg(list_w, head_input, sub_input))
            btn_del.clicked.connect(lambda: self._del_msg(list_w))

        return list_w

    def _add_msg(self, list_w, h_input, s_input):
        h, s = h_input.text().strip(), s_input.text().strip()
        if h and s:
            item = QListWidgetItem(f"{h} | {s}")
            item.setData(Qt.ItemDataRole.UserRole, [h, s])
            list_w.addItem(item)
            h_input.clear(); s_input.clear()

    def _del_msg(self, list_w):
        for item in list_w.selectedItems():
            list_w.takeItem(list_w.row(item))

    def _load_messages(self):
        s = QSettings("ScreenBreak", "ScreenBreak")
        short_raw = s.value("custom_messages_short", "[]")
        long_raw  = s.value("custom_messages_long", "[]")
        try:
            for h, sub in json.loads(short_raw):
                item = QListWidgetItem(f"{h} | {sub}")
                item.setData(Qt.ItemDataRole.UserRole, [h, sub])
                self.short_list.addItem(item)
            for h, sub in json.loads(long_raw):
                item = QListWidgetItem(f"{h} | {sub}")
                item.setData(Qt.ItemDataRole.UserRole, [h, sub])
                self.long_list.addItem(item)
        except Exception: pass

    def _save_messages(self):
        short = []
        for i in range(self.short_list.count()):
            short.append(self.short_list.item(i).data(Qt.ItemDataRole.UserRole))
        long = []
        for i in range(self.long_list.count()):
            long.append(self.long_list.item(i).data(Qt.ItemDataRole.UserRole))
        
        s = QSettings("ScreenBreak", "ScreenBreak")
        s.setValue("custom_messages_short", json.dumps(short))
        s.setValue("custom_messages_long", json.dumps(long))
        self.close()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 20, 20)
        bg = QLinearGradient(0, 0, 0, self.height())
        bg.setColorAt(0, QColor(BG_1))
        bg.setColorAt(1, QColor(BG_0))
        p.fillPath(path, QBrush(bg))
        p.setPen(QPen(QColor(255, 255, 255, 20), 1))
        p.drawPath(path)
        p.end()
