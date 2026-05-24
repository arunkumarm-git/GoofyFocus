# pro/stats.py
import datetime
import csv
import os
import json
from collections import defaultdict
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QApplication
from PyQt6.QtCore import Qt, QRectF, QTimer
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QLinearGradient, QBrush, QPen, QFont
from auth import get_supabase_client
from .dashboard import generate_dashboard

# ── Design tokens (matching app.py) ──────────────────
BG_0      = "#0f0d0e"
BG_1      = "#171415"
ACCENT     = "#FB7185"
ACCENT_DIM = "rgba(251, 113, 133, 45)"
ACCENT_BDR = "rgba(251, 113, 133, 100)"
TEXT_HI    = "rgba(255,255,255,255)"
TEXT_MID   = "rgba(255,255,255,190)"
TEXT_LOW   = "rgba(255,255,255,120)"
BORDER     = "rgba(251, 113, 133, 40)"

class StatsWindow(QWidget):
    def __init__(self, user_info: dict, is_pro: bool, active_elapsed_secs: int = 0, is_embedded: bool = False, parent=None):
        super().__init__(parent)
        self._user_info = user_info
        self._is_pro    = is_pro
        self._active_elapsed_secs = active_elapsed_secs
        self._is_embedded = is_embedded
        if not is_embedded:
            self.setFixedSize(320, 420)
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
            
            # Soft premium drop shadow
            self.shadow = QGraphicsDropShadowEffect(self)
            self.shadow.setBlurRadius(35)
            self.shadow.setColor(QColor(0, 0, 0, 160))
            self.shadow.setOffset(0, 8)
            self.setGraphicsEffect(self.shadow)
            
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build_ui()
        if is_pro:
            self._load_stats()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # Title bar
        if not self._is_embedded:
            tb = QHBoxLayout()
            title = QLabel("focus stats")
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

        # Stats Grid
        self.lbl_today  = self._add_stat_row(root, "Today", "-- min")
        self.lbl_week   = self._add_stat_row(root, "This week", "-- sessions")
        self.lbl_streak = self._add_stat_row(root, "Streak", "-- days")
        self.lbl_total  = self._add_stat_row(root, "Total focus", "-- hrs")

        root.addStretch()

        # Interactive Dashboard Button
        if self._is_pro:
            self.btn_dashboard = QPushButton("◈ view interactive dashboard")
            self.btn_dashboard.setFixedHeight(36)
            self.btn_dashboard.setStyleSheet(f"""
                QPushButton {{ 
                    background: {ACCENT_DIM}; 
                    color: white; 
                    border: 1px solid {ACCENT};
                    border-radius: 10px; 
                    padding: 6px; 
                    font-size: 11px;
                    font-family: 'DM Sans';
                    font-weight: 500;
                }}
                QPushButton:hover {{ background: rgba(251, 113, 133, 75); }}
            """)
            self.btn_dashboard.clicked.connect(self._show_interactive_dashboard)
            root.addWidget(self.btn_dashboard)

        # Pro Lock / Export Button
        if not self._is_pro:
            lock = QLabel("🔒 unlock with pro")
            lock.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lock.setFont(QFont("DM Sans", 11))
            lock.setStyleSheet(f"""
                color: {ACCENT}; background: rgba(251, 113, 133, 25); 
                padding: 12px; border-radius: 10px; border: 1px solid rgba(251, 113, 133, 51);
            """)
            root.addWidget(lock)
        else:
            self.btn_export = QPushButton("↓ export csv")
            self.btn_export.setFixedHeight(36)
            self.btn_export.setStyleSheet(f"""
                QPushButton {{ 
                    background: rgba(255,255,255,13); 
                    color: {TEXT_MID}; 
                    border: 1px solid {BORDER};
                    border-radius: 10px; 
                    padding: 6px; 
                    font-size: 11px;
                    font-family: 'DM Sans';
                }}
                QPushButton:hover {{ background: rgba(255,255,255,25); color: {TEXT_HI}; border-color: {ACCENT}; }}
            """)
            self.btn_export.clicked.connect(self._export_csv)
            root.addWidget(self.btn_export)

            self.status_lbl = QLabel("")
            self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.status_lbl.setFont(QFont("DM Mono", 10))
            self.status_lbl.setStyleSheet(f"color: {TEXT_LOW}; background: transparent;")
            root.addWidget(self.status_lbl)

    def _add_stat_row(self, layout, label, value):
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFont(QFont("DM Sans", 11))
        lbl.setStyleSheet(f"color: {TEXT_MID}; background: transparent;")
        val = QLabel(value)
        val.setFont(QFont("DM Mono", 11))
        val.setStyleSheet(f"color: {ACCENT}; background: transparent; font-weight: bold;")
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(val)
        layout.addLayout(row)
        return val

    def _load_stats(self):
        # Reset to 0 instead of --
        self.lbl_today.setText("0 min")
        self.lbl_week.setText("0 sess")
        self.lbl_total.setText("0 hrs")
        self.lbl_streak.setText("0 days")
        if self._is_pro:
            self.status_lbl.setText("loading local stats...")

        try:
            # 1. Load from Local JSON (Primary)
            from assets import USER_DATA_DIR
            local_db = os.path.join(USER_DATA_DIR, "sessions.json")
            data = []
            if os.path.exists(local_db):
                with open(local_db, "r") as f:
                    data = json.load(f)
                print(f"[stats] loaded {len(data)} rows from local sessions.json")
            else:
                # 2. Fallback to Supabase
                print(f"[stats] local db not found at {local_db}, trying cloud...")
                sb = get_supabase_client()
                if sb:
                    sub = self._user_info.get("id")
                    if sub:
                        res = sb.table("sessions").select("*").eq("google_sub", sub).execute()
                        data = res.data
                        print(f"[stats] fetched {len(data) if data else 0} rows from cloud")

            if not data and self._active_elapsed_secs == 0: 
                if self._is_pro: self.status_lbl.setText("no sessions recorded yet")
                return

            # Use local time for stats comparison
            now_local = datetime.datetime.now()
            today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start  = today_start - datetime.timedelta(days=7)
            
            today_secs = self._active_elapsed_secs
            week_count = 1 if self._active_elapsed_secs > 0 else 0
            total_secs = self._active_elapsed_secs
            
            parsed_dates = set()
            if self._active_elapsed_secs > 0:
                parsed_dates.add(now_local.date())

            for r in data:
                try:
                    raw_ts = r.get("completed_at")
                    if not raw_ts: continue
                    
                    # Convert UTC from DB to local time
                    clean_ts = raw_ts.replace("Z", "+00:00")
                    utc_ts = datetime.datetime.fromisoformat(clean_ts)
                    local_ts = utc_ts.astimezone(None).replace(tzinfo=None) # naive local
                    
                    parsed_dates.add(local_ts.date())
                    
                    dur = r.get("duration_secs", 0)
                    total_secs += dur
                    if local_ts >= today_start:
                        today_secs += dur
                    if local_ts >= week_start:
                        week_count += 1
                except Exception as e:
                    print(f"[stats] row error: {e}")
                    continue

            self.lbl_today.setText(f"{today_secs // 60} min")
            self.lbl_week.setText(f"{week_count} sess")
            self.lbl_total.setText(f"{total_secs // 3600} hrs")
            
            # Streak logic
            days = sorted(list(parsed_dates), reverse=True)
            streak = 0
            today = datetime.date.today()
            yesterday = today - datetime.timedelta(days=1)
            
            if days:
                start_day = None
                if days[0] == today: start_day = today
                elif days[0] == yesterday: start_day = yesterday
                
                if start_day:
                    streak = 0
                    curr = start_day
                    for d in days:
                        if d == curr:
                            streak += 1
                            curr -= datetime.timedelta(days=1)
                        elif d > curr: continue # multiple sessions same day
                        else: break

            self.lbl_streak.setText(f"{streak} days")
            if self._is_pro: self.status_lbl.setText(f"loaded {len(data)} local sessions")
            
        except Exception as e:
            print(f"[stats] load failed: {e}")
            if self._is_pro: self.status_lbl.setText(f"load error: {str(e)[:30]}")

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Sessions", f"goofyfocus_{datetime.date.today()}.csv", "CSV files (*.csv)")
        if not path: return
        self.btn_export.setText("exporting...")
        QApplication.processEvents()
        try:
            # 1. Load from Local JSON (Primary)
            from assets import USER_DATA_DIR
            local_db = os.path.join(USER_DATA_DIR, "sessions.json")
            rows = []
            if os.path.exists(local_db):
                with open(local_db, "r") as f:
                    rows = json.load(f)
            else:
                # 2. Fallback to Supabase
                sb = get_supabase_client()
                if sb:
                    sub = self._user_info.get("id")
                    if sub:
                        res = sb.table("sessions").select("completed_at, duration_secs, phase").eq("google_sub", sub).order("completed_at", desc=True).execute()
                        rows = res.data

            if rows:
                with open(path, 'w', newline='') as f:
                    # Filter keys to match CSV requirements
                    fieldnames = ["completed_at", "duration_secs", "phase"]
                    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                    writer.writeheader()
                    # Sort rows by completed_at descending (newest first)
                    rows.sort(key=lambda x: x.get("completed_at", ""), reverse=True)
                    writer.writerows(rows)
                self.status_lbl.setText("✓ exported successfully")
            else:
                self.status_lbl.setText("no data to export")
            self.btn_export.setText("↓ export csv")
            QTimer.singleShot(3000, lambda: self.status_lbl.setText(""))
        except Exception as e:
            self.status_lbl.setText("export failed")
            self.btn_export.setText("↓ export csv")
            print(f"[stats] export failed: {e}")

    def _show_interactive_dashboard(self):
        self.btn_dashboard.setText("generating...")
        QApplication.processEvents()
        success = generate_dashboard(self._user_info)
        if success:
            self.status_lbl.setText("✓ dashboard opened in browser")
        else:
            self.status_lbl.setText("no data for dashboard")
        self.btn_dashboard.setText("◈ view interactive dashboard")
        QTimer.singleShot(3000, lambda: self.status_lbl.setText(""))

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
        path.addRoundedRect(QRectF(self.rect()), 16, 16)
        if self._is_embedded:
            # Nested glass style
            p.fillPath(path, QBrush(QColor(255, 255, 255, 10)))
            p.setPen(QPen(QColor(255, 255, 255, 18), 1.0))
        else:
            # Floating dialog opaque gradient
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
