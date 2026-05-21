# pro/media.py
import os
import shutil
import stat
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QFileDialog, QApplication
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QLinearGradient, QBrush, QPen, QFont
from assets import USER_GIFS_DIR, USER_SOUNDS_DIR

# ── Design tokens (matching app.py) ──────────────────
BG_0      = "#161514"
BG_1      = "#1c1b19"
ACCENT     = "#849d8a"
TEXT_HI    = "rgba(255,255,255,235)"
TEXT_MID   = "rgba(255,255,255,140)"
TEXT_LOW   = "rgba(255,255,255,76)"
BORDER     = "rgba(255,255,255,20)"

def remove_readonly(func, path, excinfo):
    """Clear the readonly bit and reattempt the file deletion."""
    os.chmod(path, stat.S_IWRITE)
    func(path)

class GifPackManager(QWidget):
    def __init__(self, is_pro: bool, parent=None):
        super().__init__(parent)
        self._is_pro = is_pro
        self.setFixedSize(420, 480)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build_ui()
        if self._is_pro:
            self._refresh_list()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # Title bar
        tb = QHBoxLayout()
        title = QLabel("gif packs")
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

        if not self._is_pro:
            lock = QLabel("🔒 unlock gif packs with pro")
            lock.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lock.setFont(QFont("DM Sans", 11))
            lock.setStyleSheet(f"color: {ACCENT}; background: rgba(132,157,138,25); padding: 20px; border-radius: 10px; border: 1px solid rgba(132,157,138,51);")
            root.addWidget(lock)
            root.addStretch()
            return

        self.list_w = QListWidget()
        self.list_w.setStyleSheet(f"""
            QListWidget {{ 
                background: rgba(255,255,255,8); 
                border: 1px solid {BORDER}; 
                border-radius: 10px; 
                padding: 6px; 
                color: {TEXT_MID}; 
                font-size: 12px;
                font-family: 'DM Sans';
            }}
            QListWidget::item {{ padding: 10px; border-bottom: 1px solid rgba(255,255,255,5); }}
            QListWidget::item:selected {{ background: rgba(132,157,138,38); color: {TEXT_HI}; border-radius: 6px; }}
        """)
        root.addWidget(self.list_w)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("+ add folder")
        btn_add.setFixedHeight(36)
        btn_add.setStyleSheet(f"QPushButton {{ background: rgba(132,157,138,38); color: {ACCENT}; border-radius: 10px; padding: 0 16px; font-size: 11px; font-family: 'DM Sans'; }} QPushButton:hover {{ background: rgba(132,157,138,64); color: white; }}")
        btn_add.clicked.connect(self._add_folder)
        
        btn_del = QPushButton("delete selected")
        btn_del.setFixedHeight(36)
        btn_del.setStyleSheet(f"QPushButton {{ background: rgba(255,255,255,13); color: {TEXT_LOW}; border-radius: 10px; padding: 0 16px; font-size: 11px; font-family: 'DM Sans'; }} QPushButton:hover {{ background: rgba(255,100,100,25); color: #ffaaaa; }}")
        btn_del.clicked.connect(self._delete_folder)
        
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_del)
        root.addLayout(btn_row)

    def _refresh_list(self):
        self.list_w.clear()
        if os.path.isdir(USER_GIFS_DIR):
            for item in os.listdir(USER_GIFS_DIR):
                if os.path.isdir(os.path.join(USER_GIFS_DIR, item)):
                    self.list_w.addItem(item)

    def _add_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder Containing GIFs")
        if not path: return
        folder_name = os.path.basename(path)
        dest = os.path.join(USER_GIFS_DIR, folder_name)
        if os.path.exists(dest): return
        try:
            shutil.copytree(path, dest)
            self._refresh_list()
        except Exception as e: print(f"[GIF Manager] Copy failed: {e}")

    def _delete_folder(self):
        selected = self.list_w.selectedItems()
        # Fallback: if nothing is "selected" but an item is "focused" (currentItem)
        if not selected and self.list_w.currentItem():
            selected = [self.list_w.currentItem()]
            
        if not selected: return
        for item in selected:
            target = os.path.join(USER_GIFS_DIR, item.text())
            try:
                if os.path.isdir(target):
                    shutil.rmtree(target, onerror=remove_readonly)
            except Exception as e: print(f"[GIF Manager] Delete failed: {e}")
        self._refresh_list()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.MouseButton.LeftButton and hasattr(self, '_drag_pos') and self._drag_pos:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e): self._drag_pos = None

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

class SoundManagerWindow(QWidget):
    def __init__(self, is_pro: bool, parent=None):
        super().__init__(parent)
        self._is_pro = is_pro
        self.setFixedSize(420, 480)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build_ui()
        if self._is_pro:
            self._refresh_list()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        tb = QHBoxLayout()
        title = QLabel("ambient sounds")
        title.setFont(QFont("DM Mono", 12))
        title.setStyleSheet(f"color: {TEXT_HI}; background: transparent;")
        tb.addWidget(title)
        tb.addStretch()
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {TEXT_LOW}; border: none; font-size: 20px; }} QPushButton:hover {{ color: {TEXT_HI}; }}")
        close_btn.clicked.connect(self.close)
        tb.addWidget(close_btn)
        root.addLayout(tb)

        if not self._is_pro:
            lock = QLabel("🔒 unlock custom sounds with pro")
            lock.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lock.setFont(QFont("DM Sans", 11))
            lock.setStyleSheet(f"color: {ACCENT}; background: rgba(132,157,138,25); padding: 20px; border-radius: 10px; border: 1px solid rgba(132,157,138,51);")
            root.addWidget(lock)
            root.addStretch()
            return

        self.list_w = QListWidget()
        self.list_w.setStyleSheet(f"""
            QListWidget {{ 
                background: rgba(255,255,255,8); 
                border: 1px solid {BORDER}; 
                border-radius: 10px; 
                padding: 6px; 
                color: {TEXT_MID}; 
                font-size: 12px;
                font-family: 'DM Sans';
            }}
            QListWidget::item {{ padding: 10px; border-bottom: 1px solid rgba(255,255,255,5); }}
            QListWidget::item:selected {{ background: rgba(132,157,138,38); color: {TEXT_HI}; border-radius: 6px; }}
        """)
        root.addWidget(self.list_w)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("+ add .mp3")
        btn_add.setFixedHeight(36)
        btn_add.setStyleSheet(f"QPushButton {{ background: rgba(132,157,138,38); color: {ACCENT}; border-radius: 10px; padding: 0 16px; font-size: 11px; font-family: 'DM Sans'; }} QPushButton:hover {{ background: rgba(132,157,138,64); color: white; }}")
        btn_add.clicked.connect(self._add_file)
        
        btn_del = QPushButton("delete selected")
        btn_del.setFixedHeight(36)
        btn_del.setStyleSheet(f"QPushButton {{ background: rgba(255,255,255,13); color: {TEXT_LOW}; border-radius: 10px; padding: 0 16px; font-size: 11px; font-family: 'DM Sans'; }} QPushButton:hover {{ background: rgba(255,100,100,25); color: #ffaaaa; }}")
        btn_del.clicked.connect(self._delete_file)
        
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_del)
        root.addLayout(btn_row)

    def _refresh_list(self):
        self.list_w.clear()
        if os.path.isdir(USER_SOUNDS_DIR):
            for item in os.listdir(USER_SOUNDS_DIR):
                if item.endswith(".mp3"):
                    self.list_w.addItem(item)

    def _add_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select MP3 File", "", "Audio Files (*.mp3)")
        if not path: return
        dest = os.path.join(USER_SOUNDS_DIR, os.path.basename(path))
        try:
            shutil.copy2(path, dest)
            self._refresh_list()
        except Exception: pass

    def _delete_file(self):
        selected = self.list_w.selectedItems()
        if not selected and self.list_w.currentItem():
            selected = [self.list_w.currentItem()]
            
        if not selected: return
        for item in selected:
            target = os.path.join(USER_SOUNDS_DIR, item.text())
            try:
                if os.path.isfile(target):
                    os.remove(target)
            except Exception: pass
        self._refresh_list()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.MouseButton.LeftButton and hasattr(self, '_drag_pos') and self._drag_pos:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e): self._drag_pos = None

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
